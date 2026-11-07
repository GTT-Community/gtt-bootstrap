#!/usr/bin/env python3
"""GTT - simple execution: a versioned, sealed script the human runs with one command.

When the human has to execute something, the agent writes a PLAN (a few facts and a `gtt-run` block) and
GTT generates the script from a fixed template, reviews it, seals it and runs it only when the human says so.

  gtt_run.py new SLUG [--apply] [--json]       a plan skeleton, gtt-domain/run/RUN-NNN-SLUG.md (an agent may run this)
  gtt_run.py generate RUN [--apply] [--json]   the script, from the plan, with the plan's sha256 as its seal (an agent may run this)
  gtt_run.py check [RUN|--all] [--rehearse] [--json]
                                               the review, rules RUN-01 to RUN-12 (.gtt/contract/run.json); --rehearse also runs
                                               the script in a throwaway copy of the project (generate --apply always does)
  gtt_run.py list [--json]                     the pending runs, one line each
  gtt_run.py execute RUN --confirmed-by-human [--confirmed]
                                               run the script (the human runs this, never an agent): checks it first,
                                               asks once when it changes something, logs it, archives it in done/

RUN is `3`, `003` or `RUN-003`. Nothing here creates a commit, a branch or a tag; the generated script contains no
command that writes Git history unless gtt-domain/workflow.md declares `commits: allowed`.

Exit 0 = ok (warnings allowed), 1 = violation or refused, 2 = cannot run.
"""

import argparse
import datetime
import getpass
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

from gtt_bash import bash_executable  # noqa: E402
import gtt_flow  # noqa: E402

CONTRACT = ".gtt/contract/run.json"
REGISTRY = ".gtt/protection/registry.yaml"
CHANGES = ("none", "environment", "data", "code")
GOVERNED = ("gtt-domain/context/", "gtt-domain/adr/", ".gtt/")
TEMP_DIRS = {"tmp", "temp", ".tmp", ".cache", "build", "dist", "node_modules", "target"}
NETWORK = re.compile(r"\b(?:curl|wget|git\s+(?:clone|fetch|pull)|npm\s+(?:install|ci|i)|pnpm\s+(?:install|i)|yarn\s+(?:install|add)|pip3?\s+install|"
                     r"docker\s+(?:pull|compose\s+pull)|apt(?:-get)?\s+(?:install|update)|brew\s+install|go\s+(?:get|install)|cargo\s+(?:install|fetch))\b")
REHEARSAL_SECONDS = 120
# What a throwaway copy reproduces faithfully: the project's own scripts and the basic file utilities. Any other tool
# (npm, docker, a compiler, a test runner) may need what a copy lacks - dependencies, services, secrets - and a failure
# there would say nothing about the plan, so it is not rehearsed and never blocks.
REHEARSABLE = {"echo", "printf", "mkdir", "cp", "mv", "rm", "touch", "cat", "ls", "test", "[", "cd", "chmod", "grep", "sed", "sort", "wc"}
REHEARSAL_MAX_BYTES = 300 * 1024 * 1024
LOCAL_FILE = re.compile(r"^(?:\./|\.\./)?[A-Za-z0-9_.][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_.-]+)+\.(?:sh|py|json|ya?ml|md)$")
SEPARATORS = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")


def read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


def read_json(path):
    try:
        return json.loads(read(path) or "")
    except ValueError:
        return None


def contract():
    data = read_json(CONTRACT)
    if not isinstance(data, dict):
        print(f"gtt-run: {CONTRACT} is missing or unreadable; this Bootstrap does not carry simple execution.", file=sys.stderr)
        sys.exit(2)
    return data


def now():
    return os.environ.get("GTT_NOW") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def language():
    value = (read_json(".gtt/methodology.json") or {}).get("language")
    return value if value in ("en", "es") else "en"


def emit(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ----------------------------------------------------------------------------- locations and ids

def folder(c=None):
    return (c or contract())["locations"]["directory"]


def parse_ref(ref):
    found = re.fullmatch(r"(?:RUN-)?0*(\d+)", str(ref).strip(), re.IGNORECASE)
    return int(found.group(1)) if found else None


def rid(number):
    return f"RUN-{number:03d}"


def plans(where):
    """{number: path} of the plans in a folder."""
    out = {}
    try:
        names = os.listdir(where)
    except OSError:
        return out
    for name in names:
        found = re.fullmatch(r"RUN-(\d+)-[a-z0-9][a-z0-9-]*\.md", name)
        if found:
            out[int(found.group(1))] = os.path.join(where, name).replace(os.sep, "/")
    return out


def taken(c):
    numbers = set(plans(folder(c))) | set(plans(c["locations"]["done"]))
    for entry in log_entries(c):
        found = parse_ref(entry.get("id", ""))
        if found:
            numbers.add(found)
    return numbers


def log_entries(c):
    out = []
    for line in (read(c["locations"]["log"]) or "").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def script_of(plan_path):
    return plan_path[:-3] + ".sh"


# ----------------------------------------------------------------------------- the plan

def parse_plan(text, c):
    """{what, why, changes, checks, steps, next, problems}. Never raises: a bad plan is reported by RUN-06."""
    plan = {"title": "", "what": None, "why": None, "changes": None, "checks": [], "steps": [], "next": None, "problems": []}
    clean = re.sub(r"<!--.*?-->", "", text or "", flags=re.DOTALL)
    head = re.search(r"^#\s+(.+)$", clean, re.MULTILINE)
    plan["title"] = head.group(1).strip() if head else ""
    body = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    for field in c["plan"]["fields"]:
        for label in field["labels"]:
            found = re.search(rf"^\s*[-*]\s*\*\*{re.escape(label)}:\*\*\s*(\S.*?)\s*$", body, re.MULTILINE | re.IGNORECASE)
            if found:
                plan[field["key"]] = found.group(1).strip()
                break
    block = re.search(r"```" + re.escape(c["plan"]["block"]) + r"[ \t]*\r?\n(.*?)```", clean, re.DOTALL)
    for number, raw in enumerate((block.group(1) if block else "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or not value:
            plan["problems"].append(f"block line {number}: `{line[:60]}` is not `check:`, `step:` or `next:` with a value")
        elif key == "check":
            plan["checks"].append(value)
        elif key == "step":
            title, bar, command = value.partition(" | ")
            if not bar or not title.strip() or not command.strip():
                plan["problems"].append(f"block line {number}: a step is `step: <title> | <command>`")
            else:
                plan["steps"].append((title.strip(), command.strip()))
        elif key == "next":
            plan["next"] = value
        else:
            plan["problems"].append(f"block line {number}: unknown key `{key}` (check, step, next)")
    if not block:
        plan["problems"].append("the plan has no ```gtt-run block")
    return plan


def plan_problems(plan, c):
    problems = list(plan["problems"])
    for field in c["plan"]["fields"]:
        if not plan[field["key"]]:
            problems.append(f"the plan does not say `{field['labels'][0]}`")
    if plan["changes"] and plan["changes"] not in CHANGES:
        problems.append(f"`Changes: {plan['changes']}` is not one of {' | '.join(CHANGES)}")
    if not plan["steps"]:
        problems.append("the plan has no `step:` line")
    return problems


def one_line(text):
    return " ".join(str(text).split())


def render_script(plan, plan_id, digest, c):
    """The fixed template. The same plan always gives the same bytes: that is the seal."""
    q = shlex.quote
    total = len(plan["steps"])
    out = ["#!/usr/bin/env bash",
           f"# GTT run script {plan_id} - generated by gtt-run.sh generate from its plan. Do not edit: the plan is the source,",
           "# and a script that differs from what the plan generates is refused (RUN-05).",
           f"# What it does: {one_line(plan['what'])}",
           f"# Why: {one_line(plan['why'])}",
           f"# Changes: {plan['changes']}",
           f"# Plan sha256: {digest}",
           f"# Generator: {c['generator']}",
           "set -euo pipefail",
           'cd "$(dirname "$0")/../.."',
           "STEP_N=0",
           "STEP_T=",
           f'trap \'echo "[{plan_id}] stopped at step $STEP_N: $STEP_T" >&2\' ERR',
           f"echo {q(f'[{plan_id}] ' + one_line(plan['what']))}"]
    for command in plan["checks"]:
        out += [f"echo {q('check: ' + one_line(command))}",
                f"( {command} ) >/dev/null 2>&1 || {{ echo {q('[' + plan_id + '] required check failed: ' + one_line(command))} >&2; exit 1; }}"]
    for index, (title, command) in enumerate(plan["steps"], 1):
        out += [f"STEP_N={index}", f"STEP_T={q(one_line(title))}", f"echo {q(f'[{index}/{total}] ' + one_line(title))}", command]
    out += ["STEP_N=0", "STEP_T=", f"echo {q(f'[{plan_id}] done in ')}\"${{SECONDS}}s\""]
    if plan["next"]:
        out.append(f"echo {q('Next: ' + one_line(plan['next']))}")
    return "\n".join(out) + "\n"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------------- the review (RUN-01 to RUN-09)

def protected_paths():
    out = set()
    for entry in re.findall(r"^\s*-\s*artifact:\s*(\S+)", read(REGISTRY) or "", re.MULTILINE):
        out.add(entry.split("::")[0].split("#")[0].strip().replace("\\", "/"))
    return out


def norm(token):
    token = token.strip("\"'").replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    return os.path.normpath(token).replace("\\", "/") if token else token


def is_governed(token, extra):
    path = norm(token)
    if path.startswith(("/", "~")) and not path.startswith(os.getcwd().replace("\\", "/")):
        return False
    path = path.replace(os.getcwd().replace("\\", "/") + "/", "", 1)
    return any(path == g.rstrip("/") or path.startswith(g) for g in GOVERNED) or path in extra


def split_words(segment):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def writes_governed(command, extra):
    """The governed path a command writes, or None. Only what is written counts: reading one is free."""
    for redirect in re.finditer(r">>?\s*([^\s;&|<>]+)", command):
        if is_governed(redirect.group(1), extra):
            return redirect.group(1)
    for segment in SEPARATORS.split(command):
        words = split_words(segment)
        while words and (words[0] in ("sudo", "command", "env", "exec", "time") or re.fullmatch(r"\w+=\S*", words[0])):
            words = words[1:]
        if not words:
            continue
        head, args = os.path.basename(words[0]), [w for w in words[1:] if not w.startswith("-")]
        if head in ("cp", "mv", "install", "ln", "rsync"):
            targets = args[-1:]
            if head == "mv":
                targets = args                      # a moved source disappears
        elif head in ("tee", "rm", "truncate", "unlink", "shred", "touch", "mkdir", "rmdir", "chmod", "chown"):
            targets = args
        elif head == "sed" and any(re.match(r"^(?:-[A-Za-z]*i|--in-place)", w) for w in words[1:]):
            targets = args
        elif head == "dd":
            targets = [w[3:] for w in words[1:] if w.startswith("of=")]
        else:
            continue
        for target in targets:
            if is_governed(target, extra):
                return target
    return None


def rm_rf_outside(command):
    """A `rm -rf` target that is not inside a temporary folder, or None."""
    for segment in SEPARATORS.split(command):
        words = split_words(segment)
        while words and words[0] in ("sudo", "command", "env", "exec", "time"):
            words = words[1:]
        if not words or os.path.basename(words[0]) != "rm":
            continue
        flags = "".join(w.lstrip("-") for w in words[1:] if w.startswith("-") and not w.startswith("--"))
        recursive = "r" in flags.lower() or any(w in ("--recursive",) for w in words[1:])
        if not recursive:
            continue
        targets = [w for w in words[1:] if not w.startswith("-")]
        if not targets:
            return "(no target)"
        for target in targets:
            path = target.replace("\\", "/")
            if any(ch in path for ch in "$`*?~") and not re.fullmatch(r"(?:\./)?[\w./-]*\*?", path):
                return target
            absolute = path.startswith("/")
            full = os.path.normpath(path if absolute else os.path.join(os.getcwd(), path)).replace("\\", "/")
            root = os.getcwd().replace("\\", "/")
            system_tmp = os.path.realpath(tempfile.gettempdir()).replace("\\", "/")
            inside = full.startswith(root + "/")
            if inside:
                if TEMP_DIRS & set(full[len(root) + 1:].split("/")):
                    continue
                return target
            if full.startswith(system_tmp + "/") or full.startswith("/tmp/"):
                continue
            return target
    return None


def check_lines(plan, workflow_commits, extra):
    """[(rule, level, where, message)] for every command of the plan."""
    findings = []
    commands = [("check", i, cmd) for i, cmd in enumerate(plan["checks"], 1)] + \
               [("step", i, cmd) for i, (_t, cmd) in enumerate(plan["steps"], 1)]
    for kind, index, command in commands:
        where = f"{kind} {index}"
        hit = writes_governed(command, extra)
        if hit:
            findings.append(("RUN-01", "fail", where, f"writes `{hit}`, which GTT governs: `{command[:80]}`"))
        if workflow_commits != "allowed" and gtt_flow.SH_GIT.search(command):
            findings.append(("RUN-02", "fail", where, f"writes Git history and gtt-domain/workflow.md says `commits: {workflow_commits}`: `{command[:80]}`"))
        out = rm_rf_outside(command)
        if out:
            findings.append(("RUN-03", "fail", where, f"`rm -r` on `{out}`, outside the project's temporary folders: `{command[:80]}`"))
        if re.search(r"\b(?:curl|wget)\b[^|]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b", command):
            findings.append(("RUN-04", "fail", where, f"pipes a download into a shell: `{command[:80]}`"))
        if re.search(r"(?:^|[;&|(]\s*)sudo\b", command):
            findings.append(("RUN-07", "warn", where, f"uses sudo: `{command[:80]}`"))
        if NETWORK.search(command):
            findings.append(("RUN-08", "warn", where, f"needs the network: `{command[:80]}`"))
    return findings


def missing_files(plan):
    """[(where, path)] of the local scripts a command RUNS or LOADS that do not exist (RUN-11).
    Files a step creates (redirects, mkdir, cp targets) are not checked: only what is executed, sourced or fed to an interpreter."""
    out = []
    interpreters = {"bash", "sh", "zsh", "python", "python3", "source", "."}
    commands = [("check", i, cmd) for i, cmd in enumerate(plan["checks"], 1)] + \
               [("step", i, cmd) for i, (_t, cmd) in enumerate(plan["steps"], 1)]
    for kind, index, command in commands:
        for segment in SEPARATORS.split(command):
            try:
                words = shlex.split(segment, posix=True)
            except ValueError:
                continue
            while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]):
                words = words[1:]
            if not words:
                continue
            target = None
            if words[0] in interpreters:
                rest = [w for w in words[1:] if not w.startswith("-")]
                target = rest[0] if rest else None
            elif "/" in words[0]:
                target = words[0]
            if target and LOCAL_FILE.match(target) and not os.path.exists(target):
                out.append((f"{kind} {index}", target))
    return out



def not_rehearsable(plan):
    """The first thing in the plan a copy cannot stand in for, or None."""
    for command in [c for _t, c in plan["steps"]] + list(plan["checks"]):
        if "$(" in command or "`" in command or "<(" in command:
            return "a command substitution"
        for segment in SEPARATORS.split(command):
            try:
                words = shlex.split(segment, posix=True)
            except ValueError:
                return "a command it cannot read"
            while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]):
                words = words[1:]
            if not words:
                continue
            first = words[0]
            if first in ("bash", "sh"):
                rest = [w for w in words[1:] if not w.startswith("-")]
                if not rest or not os.path.isfile(rest[0]) or "-c" in words[1:2]:
                    return f"`{first} -c` or a script that is not a file of the project"
            elif first in REHEARSABLE or (("/" in first) and os.path.isfile(first)):
                continue
            else:
                return f"`{first}`"
    return None


def rehearsal(script, plan):
    """(level, message) or None. Runs the sealed script in a throwaway copy of the project, then the project's own
    validation, and reports what the human would have met. Never touches the real project."""
    text = " ".join(c for _t, c in plan["steps"]) + " " + " ".join(plan["checks"])
    if plan["changes"] in ("environment", "data"):
        return ("note", f"not rehearsed: it changes {plan['changes']}, which a copy cannot stand in for")
    if NETWORK.search(text) or re.search(r"\bsudo\b", text) or gtt_flow.SH_GIT.search(text) or re.search(r"\bgit\b", text):
        return ("note", "not rehearsed: it uses the network, sudo or Git, which a copy cannot stand in for")
    blocker = not_rehearsable(plan)
    if blocker:
        return ("note", f"not rehearsed: it uses {blocker}, which a copy of the project may not reproduce (dependencies, services, secrets)")
    total = 0
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
        if total > REHEARSAL_MAX_BYTES:
            return ("note", "not rehearsed: the project is too large to copy")
    box = tempfile.mkdtemp(prefix="gtt-rehearsal-")
    try:
        copy = os.path.join(box, "p")
        shutil.copytree(".", copy, symlinks=True, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
        validate = os.path.join(copy, ".gtt", "scripts", "gtt-validate.sh")
        if not os.path.isfile(validate):
            return ("note", "not rehearsed: this project has no gtt-validate.sh")
        env = dict(os.environ, GTT_NONINTERACTIVE="1")

        def run(argv):
            return subprocess.run(argv, cwd=copy, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  timeout=REHEARSAL_SECONDS, env=env, stdin=subprocess.DEVNULL)

        # The index is derived data and goes stale on every plan edit; refresh it in the copy so the baseline is
        # about the project, not about that.
        index = os.path.join(copy, ".gtt", "scripts", "gtt-index.sh")
        if os.path.isfile(index):
            run([bash_executable(), index])
        before = run([bash_executable(), validate]).returncode
        done = run([bash_executable(), os.path.join(copy, script)])
        if done.returncode != 0:
            tail = " | ".join((done.stderr or done.stdout).strip().splitlines()[-3:])[:200]
            return ("fail", f"in a copy of the project the script stopped with exit {done.returncode}: {tail}")
        after = run([bash_executable(), validate])
        if after.returncode != 0:
            lines = [l.strip() for l in after.stdout.splitlines() if "FAIL" in l][:3]
            if before == 0:
                return ("fail", "in a copy, the script ran but left validation failing: " + " | ".join(lines)[:260])
            return ("warn", "the project already fails validation before this script, and still does after: " + " | ".join(lines)[:220])
        return ("note", "rehearsed in a copy of the project: the script ran and validation passes")
    except subprocess.TimeoutExpired:
        return ("warn", f"the rehearsal took more than {REHEARSAL_SECONDS}s and was stopped; the script was not verified")
    except OSError as error:
        return ("note", f"not rehearsed: {error}")
    finally:
        shutil.rmtree(box, ignore_errors=True)


def review(number, c, rehearse=False):
    """The review of one pending run: {id, path, plan, findings, ok}."""
    path = plans(folder(c)).get(number)
    entry = {"id": rid(number), "path": path, "findings": [], "ok": False, "plan": None}
    if not path:
        entry["findings"].append(("RUN-06", "fail", "plan", f"there is no pending plan {rid(number)} in {folder(c)}/"))
        return entry
    text = read(path) or ""
    plan = parse_plan(text, c)
    entry["plan"] = plan
    for problem in plan_problems(plan, c):
        entry["findings"].append(("RUN-06", "fail", "plan", problem))
    values = gtt_flow.workflow()[0]
    if not plan_problems(plan, c):
        entry["findings"] += check_lines(plan, values.get("commits", "on-request"), protected_paths())
    script = script_of(path)
    expected = render_script(plan, rid(number), sha(text), c) if not plan_problems(plan, c) else None
    actual = read_bytes(script)
    if actual is None:
        entry["findings"].append(("RUN-05", "fail", "script", f"{script} does not exist: run `gtt-run.sh generate {rid(number)} --apply`"))
    elif expected is not None and actual != expected.encode("utf-8"):
        entry["findings"].append(("RUN-05", "fail", "script", f"{script} is not what its plan generates (edited by hand, or the plan changed): fix the plan and generate again"))
    if actual is not None:
        syntax = subprocess.run([bash_executable(), "-n", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if syntax.returncode != 0:
            entry["findings"].append(("RUN-10", "fail", "script", "bash cannot parse it: " + (syntax.stderr.strip().splitlines() or ["syntax error"])[-1][:140]))
    if plan and not plan_problems(plan, c):
        for where, missing in missing_files(plan):
            entry["findings"].append(("RUN-11", "fail", where, f"`{missing}` does not exist in the project"))
    if rehearse and actual is not None and plan and not plan_problems(plan, c) \
            and not any(f[1] == "fail" for f in entry["findings"]):
        result = rehearsal(script, plan)
        if result:
            level = {"fail": "fail", "warn": "warn", "note": "note"}[result[0]]
            entry["findings"].append(("RUN-12", level, "rehearsal", result[1]))
    if actual is not None and shutil.which("shellcheck"):
        done = subprocess.run(["shellcheck", "-f", "gcc", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
        for line in done.stdout.splitlines()[:5]:
            entry["findings"].append(("RUN-09", "warn", "script", line.strip()[:120]))
    entry["ok"] = not any(f[1] == "fail" for f in entry["findings"])
    return entry


def read_bytes(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def finding_dicts(entry):
    return [{"rule": r, "level": lv, "where": w, "message": m} for r, lv, w, m in entry["findings"]]


# ----------------------------------------------------------------------------- the hand-over

def handover(number, plan, c):
    texts = c["message"].get(language(), c["message"]["en"])
    effect = texts["none"] if plan["changes"] == "none" else "(" + texts["changes"].get(plan["changes"], plan["changes"]) + ")"
    return c["message"]["template"].format(heading=texts["heading"], what=one_line(plan["what"] or plan["title"]), effect=effect, n=number)


# ----------------------------------------------------------------------------- commands

def canonical_line(c):
    """The canonical-reference line every GTT .md carries, taken from the run folder's own README so the generation follows the project."""
    found = re.search(r"^>\s*\*\*Canonical reference:\*\*.*$", read(os.path.join(folder(c), "README.md")) or "", re.MULTILINE)
    return found.group(0) if found else \
        "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md"


def register_artifacts():
    """A new file under gtt-domain/ must be in the artifact index, or the integrity gate fails on it. Best effort, silent."""
    index = os.path.join(HERE, "gtt-index.sh")
    if os.path.isfile(index):
        subprocess.run([bash_executable(), index], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)


def cmd_new(args):
    c = contract()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.slug):
        print(f"gtt-run: `{args.slug}` is not a slug (lowercase letters, digits, dashes).", file=sys.stderr)
        return 1
    number = max(taken(c), default=0) + 1
    path = f"{folder(c)}/{rid(number)}-{args.slug}.md"
    text = (f"# {rid(number)} — {args.slug.replace('-', ' ').capitalize()}\n\n"
            f"{canonical_line(c)}\n\n"
            "- **What it does:** <one line: what running this does>\n"
            "- **Why:** <the Story or reason, e.g. STORY-007>\n"
            "- **Changes:** none   <!-- none | environment | data | code -->\n\n"
            "```gtt-run\n"
            "check: <a tool that must exist, e.g. docker --version>\n"
            "step: <title> | <one command>\n"
            "next: <what the human does after it ends>\n"
            "```\n")
    out = {"schema": 1, "id": rid(number), "number": number, "path": path, "applied": bool(args.apply)}
    if args.apply:
        os.makedirs(folder(c), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        register_artifacts()
    if args.json:
        emit(out)
    else:
        print(f"gtt-run: {'created' if args.apply else 'dry run - would create'} {path}")
        if args.apply:
            print(f"Fill in the plan, then: bash .gtt/scripts/gtt-run.sh generate {rid(number)} --apply")
        else:
            print("(nothing written; re-run with --apply)")
    return 0


def resolve(ref, c):
    number = parse_ref(ref)
    if number is None:
        print(f"gtt-run: `{ref}` is not a run (3 or RUN-003).", file=sys.stderr)
        return None
    return number


def cmd_generate(args):
    c = contract()
    number = resolve(args.run, c)
    if number is None:
        return 1
    path = plans(folder(c)).get(number)
    if not path:
        print(f"gtt-run: there is no pending plan {rid(number)} in {folder(c)}/.", file=sys.stderr)
        return 1
    text = read(path) or ""
    plan = parse_plan(text, c)
    problems = plan_problems(plan, c)
    if problems:
        print(f"gtt-run: {path} is not a valid plan (RUN-06):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    script = render_script(plan, rid(number), sha(text), c)
    target = script_of(path)
    if args.apply:
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
    entry = review(number, c, rehearse=True) if args.apply else None
    ok = entry["ok"] if entry else True
    if args.json:
        emit({"schema": 1, "id": rid(number), "script": target, "applied": bool(args.apply), "ok": ok,
              "findings": finding_dicts(entry) if entry else [], "handover": handover(number, plan, c)})
    else:
        print(f"gtt-run: {'generated' if args.apply else 'dry run - would generate'} {target}")
        if entry:
            for f in entry["findings"]:
                print(f"  {f[1].upper():4} {f[0]} ({f[2]}): {f[3]}")
        if not args.apply:
            print("(nothing written; re-run with --apply)")
        elif ok:
            print("\nHand this to the human, word for word, and nothing more:\n")
            print(handover(number, plan, c))
        else:
            print("The review failed: fix the plan and generate again. Do not hand it over.")
    return 0 if ok else 1


def cmd_check(args):
    c = contract()
    if args.run:
        number = resolve(args.run, c)
        if number is None:
            return 1
        numbers = [number]
    else:
        numbers = sorted(plans(folder(c)))
    entries = [review(n, c, rehearse=args.rehearse) for n in numbers]
    ok = all(e["ok"] for e in entries)
    if args.json:
        emit({"schema": 1, "ok": ok, "runs": [{"id": e["id"], "ok": e["ok"], "findings": finding_dicts(e)} for e in entries]})
    else:
        if not entries:
            print("gtt-run: no pending runs.")
        for e in entries:
            print(f"{e['id']}: {'ok' if e['ok'] else 'FAILED'}")
            for f in e["findings"]:
                print(f"  {f[1].upper():4} {f[0]} ({f[2]}): {f[3]}")
    return 0 if ok else 1


def listing(c):
    rows = []
    for number, path in sorted(plans(folder(c)).items()):
        plan = parse_plan(read(path) or "", c)
        entry = review(number, c)
        generated = os.path.isfile(script_of(path))
        state = "ready" if entry["ok"] else ("not generated" if not generated else "review failed")
        rows.append({"id": rid(number), "number": number, "path": path, "title": plan["title"], "what": plan["what"], "why": plan["why"],
                     "changes": plan["changes"], "checks": plan["checks"], "steps": [{"title": t, "command": cmd} for t, cmd in plan["steps"]],
                     "next": plan["next"], "generated": generated, "state": state, "ok": entry["ok"],
                     "findings": finding_dicts(entry)})
    return rows


def cmd_list(args):
    c = contract()
    rows = listing(c)
    if args.json:
        emit({"schema": 1, "runs": rows, "threshold": c["threshold"]})
    elif not rows:
        print("No pending runs.")
    else:
        for r in rows:
            print(f"gtt run {r['number']:<3} {r['id']}  {r['what'] or r['title']}  [changes: {r['changes'] or '?'}; {r['state']}]")
    return 0


def archive(number, c):
    """Move the plan and its script to done/ and keep the last `retention.done`."""
    done = c["locations"]["done"]
    os.makedirs(done, exist_ok=True)
    path = plans(folder(c)).get(number)
    for source in (path, script_of(path)):
        if os.path.isfile(source):
            shutil.move(source, os.path.join(done, os.path.basename(source)))
    kept = sorted(plans(done))
    for old in kept[:-c["retention"]["done"]]:
        for source in (plans(done)[old], script_of(plans(done)[old])):
            if os.path.isfile(source):
                os.remove(source)


def cmd_execute(args):
    c = contract()
    if not args.confirmed_by_human:
        print("gtt-run: executing a run is the human's act. It needs --confirmed-by-human; an agent never runs it: "
              "tell the human `gtt run <n>`.", file=sys.stderr)
        return 1
    number = resolve(args.run, c)
    if number is None:
        return 1
    entry = review(number, c)
    if not entry["ok"]:
        print(f"gtt-run: {entry['id']} is refused; nothing was run:", file=sys.stderr)
        for f in entry["findings"]:
            if f[1] == "fail":
                print(f"  {f[0]} ({f[2]}): {f[3]}", file=sys.stderr)
        return 1
    plan, path = entry["plan"], entry["path"]
    print(f"{entry['id']} - {plan['what']}")
    print(f"Why: {plan['why']}")
    for command in plan["checks"]:
        print(f"  check  {command}")
    for index, (title, command) in enumerate(plan["steps"], 1):
        print(f"  {index}. {title}   $ {command}")
    print(f"Changes: {plan['changes']}")
    for f in entry["findings"]:
        print(f"  {f[1].upper()} {f[0]}: {f[3]}")
    if plan["changes"] != "none" and not args.confirmed:
        if not sys.stdin.isatty():
            print(f"gtt-run: {entry['id']} changes {plan['changes']}; it needs an interactive confirmation and there is no terminal. "
                  "Nothing was run.", file=sys.stderr)
            return 1
        if input("Run it now? [y/N] ").strip().lower() not in ("y", "yes", "s", "si", "sí"):
            print("gtt-run: cancelled; nothing was run.")
            return 1
    started = time.time()
    code = subprocess.call([bash_executable(), script_of(path)])
    seconds = round(time.time() - started, 1)
    try:
        who = getpass.getuser()
    except Exception:
        who = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    record = {"id": entry["id"], "at": now(), "seconds": seconds, "exit": code, "by": who, "changes": plan["changes"]}
    os.makedirs(os.path.dirname(c["locations"]["log"]), exist_ok=True)
    with open(c["locations"]["log"], "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    if code == 0:
        archive(number, c)
        print(f"gtt-run: {entry['id']} finished in {seconds}s and moved to {c['locations']['done']}/.")
        return 0
    print(f"gtt-run: {entry['id']} stopped with exit {code}; it stays pending so it can be run again once fixed.", file=sys.stderr)
    return 1


def main(argv):
    parser = argparse.ArgumentParser(description="GTT simple execution")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("slug"); p.add_argument("--apply", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("generate"); p.add_argument("run"); p.add_argument("--apply", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("check"); p.add_argument("run", nargs="?"); p.add_argument("--all", action="store_true"); p.add_argument("--rehearse", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("list"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("execute"); p.add_argument("run"); p.add_argument("--confirmed-by-human", action="store_true")
    p.add_argument("--confirmed", action="store_true")
    args = parser.parse_args(argv)
    return {"new": cmd_new, "generate": cmd_generate, "check": cmd_check, "list": cmd_list, "execute": cmd_execute}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
