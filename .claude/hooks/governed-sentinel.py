#!/usr/bin/env python3
"""GTT - the governed-state sentinel (PreToolUse + PostToolUse hook, Claude Code).

protect-l0.py refuses a write to the frozen design before it happens, but it reads a
shell command statically: a `cd` first, a variable, a glob, a string built in pieces,
`find -exec`, an archive, `git stash pop`, a script that writes on the agent's behalf
or an MCP tool it cannot read can still reach what it protects - or run the human's
own promotion through a spelling it does not recognise. This hook does not try to
read the command. It looks at what the command did:

  pre   records what it watches (one hash per file) and keeps a copy outside the
        project, refreshed only when it changed between the agent's commands (the
        human's own work);
  post  compares. Nothing an agent's command may do changes the frozen design, the
        freeze marker or the protection machinery: a promotion, its undo and a freeze
        are the human's, run in their own terminal or after `!` in the prompt, where
        no hook runs. So any such change during the agent's command is put back, what
        the command wrote is kept under gtt-domain/proposals/withdrawn/ (archived,
        never lost), and the agent and the human are told.

Watched: gtt-domain/context/, gtt-domain/adr/, gtt-domain/.frozen, .claude/settings.json,
.claude/hooks/, .gtt/scripts/. Not watched, because they change legitimately while an
agent works: .claude/settings.local.json (Claude Code records a permission the human
grants there), .gtt/ade.json and Python's __pycache__.

It decides nothing about the work: ordinary commands change none of this, so for them
it is two hashes and silence. Only once frozen. A broken sentinel never blocks a
session: unexpected input exits 0, and a file it cannot restore is reported.
"""

import hashlib
import json
import os
import shutil
import sys
import time

FROZEN = "gtt-domain/.frozen"
WATCHED_DIRS = ("gtt-domain/context", "gtt-domain/adr", ".claude/hooks", ".gtt/scripts")
WATCHED_FILES = (FROZEN, ".claude/settings.json")
ARCHIVE = "gtt-domain/proposals/withdrawn"


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def state(root):
    """{rel: hash} of every watched file that exists."""
    out = {}
    for rel in WATCHED_FILES:
        if os.path.isfile(os.path.join(root, rel)):
            out[rel] = digest(os.path.join(root, rel))
    for directory in WATCHED_DIRS:
        for dirpath, dirnames, names in os.walk(os.path.join(root, directory)):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in names:
                full = os.path.join(dirpath, name)
                out[os.path.relpath(full, root).replace("\\", "/")] = digest(full)
    return out


def shadow(root):
    """The copy lives outside the project: nothing in the repository, and not where the agent works."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "gtt", "sentinel", hashlib.sha256(os.path.realpath(root).encode()).hexdigest()[:16])


def load(where):
    try:
        with open(os.path.join(where, "state.json"), encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def keep(root, where, now):
    tree = os.path.join(where, "tree")
    shutil.rmtree(tree, ignore_errors=True)
    for rel in now:
        os.makedirs(os.path.dirname(os.path.join(tree, rel)), exist_ok=True)
        shutil.copy2(os.path.join(root, rel), os.path.join(tree, rel))
    with open(os.path.join(where, "state.json"), "w", encoding="utf-8") as handle:
        json.dump(now, handle)


def pre(root):
    now = state(root)
    if FROZEN not in now:
        return
    where = shadow(root)
    if load(where) != now:
        os.makedirs(where, exist_ok=True)
        keep(root, where, now)


def restore(root, where, before, now):
    """Puts every watched file back; returns (changed paths, archive folder, paths it could not restore)."""
    tree = os.path.join(where, "tree")
    changed = sorted(rel for rel in set(before) | set(now) if before.get(rel) != now.get(rel))
    archive = stamp = f"{ARCHIVE}/{time.strftime('%Y-%m-%dT%H%M%S')}-reverted"
    count = 1
    while os.path.exists(os.path.join(root, archive)):       # two in one second never share a folder
        count += 1
        archive = f"{stamp}-{count}"
    missed = []
    for rel in changed:
        current, saved = os.path.join(root, rel), os.path.join(tree, rel)
        if os.path.isfile(current):                          # what the command wrote is archived, never lost
            os.makedirs(os.path.dirname(os.path.join(root, archive, rel)), exist_ok=True)
            shutil.copy2(current, os.path.join(root, archive, rel))
        if rel not in before:                                # a file the command added
            os.remove(current)
        elif os.path.isfile(saved) and digest(saved) == before[rel]:
            os.makedirs(os.path.dirname(current), exist_ok=True)
            shutil.copy2(saved, current)
        else:
            missed.append(rel)
    return changed, archive, missed


def post(root, event):
    where = shadow(root)
    before = load(where)
    if not before or FROZEN not in before:
        return None
    now = state(root)
    if now == before:
        return None
    changed, archive, missed = restore(root, where, before, now)
    names = ", ".join(changed[:6]) + (f" and {len(changed) - 6} more" if len(changed) > 6 else "")
    agent = (f"GTT governance (sentinel): that command changed what only the human changes ({names}) - the frozen "
             f"design, the freeze or the protection itself. GTT put it back; what the command wrote is kept in "
             f"{archive}/. A promotion, an undo and a freeze are the human's, in their own terminal: give them the "
             "command. If the design must change, use the gtt-propose-change skill, and never look for another way "
             "in. Continue with the rest of the work.")
    human = (f"GTT: an agent command changed the frozen design or its protection ({names}); it was put back, and its "
             f"version is kept in {archive}/. If you promoted, undid or froze in another terminal while the agent was "
             "running, run it again.")
    if FROZEN in changed:
        agent += (" If it applied a promotion set, the set was consumed: stage it again (gtt-stage.sh) and give the "
                  "human the `gtt promote` command.")
    if missed:
        agent += f" These could not be restored (no verified copy): {', '.join(missed)} - tell the human."
        human += f" NOT restored: {', '.join(missed)}."
    if event.get("hook_event_name") == "PostToolUseFailure":
        return {"systemMessage": human, "hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": agent}}
    return {"decision": "block", "reason": agent, "systemMessage": human}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if mode == "pre":
        pre(root)
    elif mode == "post":
        out = post(root, event if isinstance(event, dict) else {})
        if out:
            print(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:                               # a broken sentinel never blocks a session
        print(f"GTT sentinel: {error}", file=sys.stderr)
        sys.exit(0)
