#!/usr/bin/env python3
"""GTT - delivery log (PostToolUse hook).

After a write that can have changed gtt-domain/backlog.md, records the status changes of Stories and Epics
(`gtt-delivery.sh log`). The time is the hook's own clock and the content is what the backlog says: the agent
never writes the log and has no argument to it. Deterministic, no model, no tokens.

File tools are filtered by path; a shell command may have edited the backlog anywhere, so for those the log
comparison itself (a cheap read of the backlog) decides whether anything is written.

Exit 0 always. A broken hook must never block a tool call.
"""

import json
import os
import subprocess
import sys

BACKLOG = "backlog.md"


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    tool = event.get("tool_name", "")
    target = str((event.get("tool_input") or {}).get("file_path") or (event.get("tool_input") or {}).get("path") or "")
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit") and os.path.basename(target) != BACKLOG:
        return 0
    if not os.path.isfile(".gtt/scripts/gtt-delivery.sh") or not os.path.isfile("gtt-domain/backlog.md"):
        return 0
    try:
        subprocess.run(["bash", ".gtt/scripts/gtt-delivery.sh", "log"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
