#!/usr/bin/env python3
"""One rule for every human act: 0 done, 2 already done (a success), 1 refused - with the reason.

Every act that ends in a freeze (approve, promote, undo, apply) asks here, so they all read the freeze's
answer the same way, and ask it BEFORE the human is asked to confirm: after the confirmation only the
disk or git may fail.

DATA-FREE HELPER. It decides nothing about GTT; it only runs gtt-freeze.sh and reads its exit code.
"""
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile

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


SKIP = shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target", ".next")


@contextlib.contextmanager
def rehearsal():
    """A throwaway copy of the project as the working directory. The act is applied there first, so the
    freeze check sees the state the act would leave, not the state before it. Yields None when the copy
    cannot be made (then the act is not rehearsed, and that never blocks it)."""
    root = os.getcwd()
    tmp = tempfile.mkdtemp(prefix=".gtt-rehearsal.")
    try:
        copy = os.path.join(tmp, "p")
        try:
            shutil.copytree(root, copy, ignore=SKIP, symlinks=True)
        except (OSError, shutil.Error):
            yield None
            return
        os.chdir(copy)
        try:
            yield copy
        finally:
            os.chdir(root)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def refuse_before_asking(act, prepare=None):
    """Verify, before the prompt, that the freeze after the act will not refuse it. `prepare` applies the act's
    writes inside a throwaway copy. Returns True (after printing why) when the act must stop."""
    if not os.path.isfile(FROZEN) or not os.path.isfile(FREEZE):
        return False
    with rehearsal() as copy:
        if copy is None:
            check = freeze_check()
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
