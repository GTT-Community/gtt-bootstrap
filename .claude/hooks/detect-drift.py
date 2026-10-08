#!/usr/bin/env python3
"""GTT - observation after a write (PostToolUse hook).

The Work plane on Claude Code. The implementation is free by design - nothing here
approves a change or asks for one - but a change in the code can cross a boundary of
the frozen design. After a Write / Edit / NotebookEdit this runs the observation
engine (.gtt/scripts/gtt-observe.sh observe) and hands whatever is NEW to the agent as
context, so it can say it in one line and keep working.

A burst of edits costs one observation, not one per edit: the engine is asked to do nothing if it
ran less than 20 seconds ago. What a skipped run would have seen, the next one sees.

It holds no logic of its own: which boundaries exist, what level each one has and
whether anything is new are the engine's answers, computed from Git, the filesystem
and the freeze baseline. The engine is idempotent and silent by default, so this hook
adds nothing to a session in which nothing new happened - and it never repeats a
signal the governance backlog already holds.

It never blocks: it always exits 0. A BLOCKING observation reaches the agent as the
same context, marked STOP, and is enforced where enforcement belongs - the PreToolUse
hook for a BLOCKING path boundary, `gtt-observe.sh check` in validation, CI and the
Git pre-commit hook. Only runs once the project is frozen: before that there is no
governed state to observe against.

Shell mutations are not seen here (PostToolUse fires for the file tools only); the
engine sees them the next time it runs - at the next write, at session start through
gtt-status.sh, in validation and at commit.
"""

import json
import os
import subprocess
import sys

FROZEN_MARKER = "gtt-domain/.frozen"
ENGINE = os.path.join(".gtt", "scripts", "gtt-observe.sh")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    if event.get("tool_name", "") not in ("Write", "Edit", "NotebookEdit"):
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not os.path.exists(os.path.join(root, FROZEN_MARKER)) or not os.path.isfile(os.path.join(root, ENGINE)):
        return 0
    try:
        proc = subprocess.run(["bash", ENGINE, "observe", "--debounce", "20"], cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return 0
    signal = proc.stdout.strip()
    if not signal:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": signal + "\n\nThis is an observation, not an instruction to stop: unless a line says "
                                      "STOP, tell the human in one line and continue the work.",
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
