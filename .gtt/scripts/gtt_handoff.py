#!/usr/bin/env python3
"""GTT - hand a human act over with ONE message and a command that was built and checked, not typed.

  gtt_handoff.py ACT [ARGUMENT...] [--json]

ACT is one of the acts in .gtt/contract/handoff.json (promote, approve, accept, reject, defer, freeze, run). The message
always has the same shape, in the project's language:

  @gtt · Para ti
  Qué:     what is being asked
  Cambia:  what it changes
  Bloquea: what waits for it (only when something does)
  Ejecuta:
    <the exact command>

The command comes from the contract with the arguments filled in; before the message is shown, this script checks that
what it names exists (the promotion set, the Epic, the observation, the run plan, the script) and that the script
parses. A command that cannot work is never shown: the problem is said instead, and the exit is 1.

Deterministic: no model writes the command, the wording or the order. An agent shows this output and adds nothing.

Exit 0 = the message, 1 = the act cannot be handed over, 2 = cannot run.
"""

import getpass
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

from gtt_bash import bash_executable  # noqa: E402

CONTRACT = ".gtt/contract/handoff.json"
STAGED = "gtt-domain/proposals/staged"
LEDGER = "gtt-domain/governance-backlog.json"
RUN_DIR = "gtt-domain/run"
BACKLOG = "gtt-domain/backlog.md"


def read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


def load():
    try:
        return json.loads(read(CONTRACT) or "")
    except ValueError:
        print(f"gtt-handoff: {CONTRACT} is missing or unreadable; this Bootstrap does not carry the hand-over format.", file=sys.stderr)
        sys.exit(2)


def language():
    try:
        value = json.loads(read(".gtt/methodology.json") or "{}").get("language")
    except ValueError:
        value = None
    return value if value in ("en", "es") else "en"


def who():
    try:
        done = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
        if done.returncode == 0 and done.stdout.strip():
            return done.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER") or os.environ.get("USERNAME") or "me"


# ----------------------------------------------------------------------------- checks: what the command names must exist

def epic_title(epic):
    found = re.search(rf"^###\s+{re.escape(epic)}\s+[—-]\s+(.+?)\s*$", read(BACKLOG) or "", re.MULTILINE)
    return found.group(1) if found else None


def run_number(text):
    found = re.fullmatch(r"(?:RUN-)?0*(\d+)", text.strip(), re.IGNORECASE)
    return int(found.group(1)) if found else None


def check(kind, values):
    """(problem or None, extra values)."""
    extra = {}
    if kind == "staged-set":
        name = values["set"]
        spec = None
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
            try:
                spec = json.loads(read(os.path.join(STAGED, name, "promote.json")) or "")
            except ValueError:
                spec = None
        if not isinstance(spec, dict) or not spec.get("files"):
            sets = sorted(d for d in (os.listdir(STAGED) if os.path.isdir(STAGED) else [])
                          if os.path.isfile(os.path.join(STAGED, d, "promote.json")))
            return f"there is no promotion set `{name}` in {STAGED}/" + (f" (there is: {', '.join(sets)})" if sets else ""), extra
        gone = [f["from"] for f in spec["files"] if not os.path.isfile(os.path.join(STAGED, name, str(f.get("from", ""))))]
        if gone:
            return f"the set `{name}` is incomplete: {', '.join(gone)} is missing", extra
        extra["reason"] = str(spec.get("reason") or "").strip() or name
        extra["files"] = ", ".join(str(f["to"]) for f in spec["files"])
    elif kind == "epic":
        epic = values["epic"]
        title = epic_title(epic) if re.fullmatch(r"EPIC-\d+", epic) else None
        if title is None:
            return f"`{epic}` is not an Epic in {BACKLOG}", extra
        extra["title"] = f" ({title})"
    elif kind == "observation":
        obs = values["observation"]
        try:
            items = json.loads(read(LEDGER) or "{}").get("items", [])
        except ValueError:
            items = []
        found = [i for i in items if i.get("id") == obs]
        if not found:
            ids = [i["id"] for i in items if i.get("status") in ("open", "deferred")][:6]
            return f"there is no observation `{obs}`" + (f" (open: {', '.join(ids)})" if ids else " (none is open)"), extra
        if found[0].get("status") not in ("open", "deferred"):
            return f"{obs} is already {found[0].get('status')}; there is nothing left to decide", extra
    elif kind == "run":
        number = run_number(values["run"])
        pending = [n for n in (re.fullmatch(r"RUN-(\d+)-.*\.md", f) for f in (os.listdir(RUN_DIR) if os.path.isdir(RUN_DIR) else [])) if n]
        if number is None or number not in {int(m.group(1)) for m in pending}:
            return f"there is no pending run `{values['run']}` in {RUN_DIR}/", extra
        values["run"] = f"RUN-{number:03d}"
        values["n"] = str(number)
    return None, extra


def command_problem(command):
    """The script a `bash .gtt/scripts/...` command runs must exist and parse. `gtt ...` is the installed CLI."""
    words = shlex.split(command)
    if words[:1] == ["bash"] and len(words) > 1:
        script = words[1]
        if not os.path.isfile(script):
            return f"`{script}` does not exist in this project"
        done = subprocess.run([bash_executable(), "-n", script], capture_output=True, text=True)
        if done.returncode != 0:
            return f"`{script}` does not parse: {(done.stderr.strip().splitlines() or ['syntax error'])[-1][:120]}"
    return None


# ----------------------------------------------------------------------------- the message

def build(act_name, arguments, contract):
    acts = contract["acts"]
    if act_name not in acts:
        return None, f"`{act_name}` is not a human act (one of: {', '.join(acts)})"
    act = acts[act_name]
    if len(arguments) != len(act["args"]):
        usage = " ".join(f"<{a}>" for a in act["args"])
        return None, f"usage: gtt-handoff.sh {act_name} {usage}".rstrip()
    values = dict(zip(act["args"], arguments))
    problem, extra = check(act["check"], values) if act["check"] else (None, {})
    if problem:
        return None, problem
    values.update(extra)
    values.setdefault("title", "")
    values["by"] = who().replace('"', "")
    template = act["command"]
    if act.get("script") and not shutil.which("gtt"):
        template = act["script"]
    command = template.format(**values)
    problem = command_problem(command)
    if problem:
        return None, problem
    lang = language()
    labels = contract["labels"][lang]
    lines = [contract["heading"][lang],
             f"{labels['what']}: {act['what'][lang].format(**values)}",
             f"{labels['changes']}: {act['changes'][lang].format(**values)}"]
    if act.get("blocks"):
        lines.append(f"{labels['blocks']}: {act['blocks'][lang].format(**values)}")
    lines += [f"{labels['run']}:", f"  {command}"]
    if act.get("optional"):
        lines.append(f"({labels['optional']}: {act['optional'][lang]})")
    return {"act": act_name, "command": command, "message": "\n".join(lines)}, None


def main(argv):
    contract = load()
    args = [a for a in argv if a != "--json"]
    if not args:
        print("usage: gtt-handoff.sh " + " | ".join(contract["acts"]) + " [arguments] [--json]", file=sys.stderr)
        return 2
    built, problem = build(args[0], args[1:], contract)
    if problem:
        print(f"gtt-handoff: cannot hand this over - {problem}.", file=sys.stderr)
        return 1
    if "--json" in argv:
        print(json.dumps({"schema": 1, **built}, indent=2, ensure_ascii=False))
    else:
        print(built["message"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
