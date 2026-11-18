#!/usr/bin/env python3
"""GTT - activity log (PostToolUse hook).

After a tool call, writes one line to `.gtt/local/activity.jsonl`: when, which ADE, which tool, which path and which Stories were
In Progress. It never keeps content or arguments (a shell command keeps its first word only). It prints nothing, except the single
line, once per session, that says code has been changing for 15 minutes with no Story In Progress. No model, no tokens.

The journal is written only here and by `.gtt/scripts/gtt_activity.py`; the agent has no way to edit it (protected like the delivery log).
Exit 0 always: a broken hook must never block a tool call.
"""
import os
import subprocess
import sys


def main():
    script = ".gtt/scripts/gtt-activity.sh"
    if not os.path.isfile(script):
        return 0
    try:
        subprocess.run(["bash", script, "log", "--ade", "claude"], stdin=sys.stdin, timeout=20)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
