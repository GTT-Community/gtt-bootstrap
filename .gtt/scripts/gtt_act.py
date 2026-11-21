#!/usr/bin/env python3
"""One rule for every human act: 0 done, 2 already done (a success), 1 refused - with the reason.

Every act that ends in a freeze (approve, promote, undo, apply) asks here, so they all read the freeze's
answer the same way, and ask it BEFORE the human is asked to confirm: after the confirmation only the
disk or git may fail.

DATA-FREE HELPER. It decides nothing about GTT; it only runs gtt-freeze.sh and reads its exit code.
"""
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from gtt_bash import bash_executable

FREEZE = os.path.join(".gtt", "scripts", "gtt-freeze.sh")
FROZEN = os.path.join("gtt-domain", ".frozen")

DONE, ALREADY, REFUSED = 0, 2, 1


def ok(code):
    """The single outcome rule: 0 and 2 are both a success."""
    return code in (DONE, ALREADY)


def _run(check):
    cmd = [bash_executable(), FREEZE] + (["--check"] if check else [])
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return done.returncode, (done.stdout + done.stderr).rstrip()


def freeze_check():
    """Everything the freeze would verify, writing nothing. (code, text); None when there is nothing to freeze."""
    if not os.path.isfile(FROZEN) or not os.path.isfile(FREEZE):
        return None
    return _run(True)


def freeze_now():
    """Record the freeze. (code, text); an already-recorded state is a success (2)."""
    return _run(False)


# --- the human act, told to the sentinel ------------------------------------------------------------------------------------------------
# A promotion, an undo, an approval and a freeze are the human's and write governed files for a few seconds (apply, freeze, put back when
# the freeze refuses). The Claude sentinel (.claude/hooks/governed-sentinel.py) puts back any governed change made while an agent's command
# runs, so a human act that overlapped an agent command in flight was read as the agent's: reverted, archived under withdrawn/, and the
# project was left half promoted with no backup. The act now records its window where the sentinel keeps its own state (outside the
# project); the sentinel lets pass only the paths changed INSIDE that window and still puts back every other.

def sentinel_dir(root=None):
    """Where the sentinel keeps its copy: the same formula as the hook, outside the project."""
    root = root or os.getcwd()
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "gtt", "sentinel", hashlib.sha256(os.path.realpath(root).encode()).hexdigest()[:16])


def _write_lease(where, record):
    os.makedirs(where, exist_ok=True)
    tmp = os.path.join(where, "human-act.json.tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(record, handle)
    os.replace(tmp, os.path.join(where, "human-act.json"))


def begin_act(act, pid=None):
    """Start the window. Nested acts (the promotion runs the freeze) share the outer window: the inner one does nothing.
    `pid` is the process that owns the act (a shell script passes its own: this helper exits at once)."""
    if os.environ.get("GTT_HUMAN_ACT"):
        return False
    try:
        _write_lease(sentinel_dir(), {"pid": int(pid or os.getpid()), "act": act, "started": time.time(), "ended": None})
    except (OSError, ValueError):
        return False                       # an act is never blocked by the bookkeeping
    os.environ["GTT_HUMAN_ACT"] = act
    return True


def end_act(owner=True):
    if not owner:
        return
    os.environ.pop("GTT_HUMAN_ACT", None)
    where = sentinel_dir()
    try:
        with open(os.path.join(where, "human-act.json"), encoding="utf-8") as handle:
            record = json.load(handle)
        record["ended"] = time.time()
        _write_lease(where, record)
    except (OSError, ValueError):
        pass


@contextlib.contextmanager
def human_act(act):
    owner = begin_act(act)
    try:
        yield
    finally:
        end_act(owner)


SKIP = shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target", ".next")

# What the freeze reads AND may write while it checks: the GTT kit. These are copied. Everything else in the project (the code, the
# sources, the database volumes) is only READ by the freeze, so the rehearsal links to it instead of copying it: a project of
# 1.3 GB took 11 s to copy, and one unreadable folder (a database volume owned by root) made the copy fail and the rehearsal
# silently disappear, so the check ran on the state BEFORE the act and passed what the freeze then refused after the confirmation.
KIT = (".gtt", "gtt-domain", ".claude", ".kiro", ".github", ".cursor", ".agents", ".openhands")
ROOT_FILE_LIMIT = 2 * 1024 * 1024


def _copy_tolerant(src, dst):
    """Copy a file or a folder; whatever cannot be read (a root-owned volume, a dangling link) is left out and the rest is kept.
    Returns the number of entries it could not copy."""
    try:
        if os.path.isdir(src) and not os.path.islink(src):
            shutil.copytree(src, dst, ignore=SKIP, symlinks=True, ignore_dangling_symlinks=True)
        else:
            shutil.copy2(src, dst, follow_symlinks=False)
        return 0
    except shutil.Error as error:
        return len(error.args[0]) if error.args and isinstance(error.args[0], list) else 1
    except OSError:
        return 1


def light_copy(root, copy, writes=()):
    """A copy of the project to rehearse an act in: the kit and the top-level folders the act writes into are real copies,
    every other top-level entry is a link to the real one (read only). The act writes nothing there."""
    real = set(KIT) | {str(w).replace("\\", "/").split("/")[0] for w in writes if w}
    os.makedirs(copy)
    skipped = 0
    for name in sorted(os.listdir(root)):
        if name == ".git" or name in ("node_modules", "__pycache__", ".venv", "venv", ".next"):
            continue
        src, dst = os.path.join(root, name), os.path.join(copy, name)
        small_file = os.path.isfile(src) and not os.path.islink(src) and os.path.getsize(src) <= ROOT_FILE_LIMIT
        if name in real or small_file and name.lower() in ("agents.md", "readme-gtt.md", "readme-gtt.es.md") or name.startswith("SOURCE-BRIEF"):
            skipped += _copy_tolerant(src, dst)
        else:
            try:
                os.symlink(src, dst)
            except OSError:
                skipped += _copy_tolerant(src, dst)
    return skipped


@contextlib.contextmanager
def rehearsal(writes=()):
    """A throwaway copy of the project as the working directory. The act is applied there first, so the
    freeze check sees the state the act would leave, not the state before it. Yields None only when no copy could
    be made at all (then the caller says so: the act is not rehearsed, and that never blocks it)."""
    root = os.getcwd()
    tmp = tempfile.mkdtemp(prefix=".gtt-rehearsal.")
    try:
        copy = os.path.join(tmp, "p")
        try:
            light_copy(root, copy, writes)
        except OSError:
            yield None
            return
        os.chdir(copy)
        try:
            yield copy
        finally:
            os.chdir(root)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def refuse_before_asking(act, prepare=None, writes=()):
    """Verify, before the prompt, that the freeze after the act will not refuse it. `prepare` applies the act's
    writes inside a throwaway copy. Returns True (after printing why) when the act must stop."""
    if not os.path.isfile(FROZEN) or not os.path.isfile(FREEZE):
        return False
    with rehearsal(writes) as copy:
        if copy is None:
            print(f"{act}: could not rehearse the freeze (no copy could be made); it is verified as the act is applied, and everything is put back if it refuses.", file=sys.stderr)
            return False
        else:
            try:
                if prepare:
                    prepare()
            except ValueError as error:         # the act itself says it cannot be done
                print(f"{act}: {error}. Nothing was asked and nothing was written.", file=sys.stderr)
                return True
            except Exception as error:          # an act that cannot be rehearsed is not blocked by it
                print(f"{act}: could not rehearse ({error}); it will be checked as it is applied.", file=sys.stderr)
                return False
            check = freeze_check()
    if check is None or ok(check[0]):
        if check and "will add the canonical reference" in check[1]:
            print("\n".join(l for l in check[1].splitlines() if "canonical reference" in l))
        return False
    print(check[1], file=sys.stderr)
    print(f"{act}: the freeze that follows would be refused (see above). Nothing was asked and nothing was written.", file=sys.stderr)
    return True


if __name__ == "__main__":
    # for the shell scripts: `gtt_act.py begin <act>` / `gtt_act.py end` (the freeze, which is bash)
    if len(sys.argv) >= 2 and sys.argv[1] == "begin":
        begin_act(sys.argv[2] if len(sys.argv) > 2 else "act", sys.argv[3] if len(sys.argv) > 3 else None)
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "end":
        end_act(True)
        sys.exit(0)
