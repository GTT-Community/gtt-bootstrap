#!/usr/bin/env python3
"""GTT Sonar - regenerate the page (PostToolUse hook).

After a write that can have changed what Sonar shows (gtt-domain/**, the ideas folder), or a shell command that
names one of them, regenerates .gtt/local/sonar.html and sonar.json with `gtt-sonar.sh render --quiet`.

It reads nothing itself, prints nothing and never blocks: gtt-sonar.sh takes a short lock, so a render that is
already running is not repeated. The page is derived and disposable; this hook only keeps it fresh.

Exit 0 always. A broken hook must never block a tool call.
"""

import json
import os
import subprocess
import sys

WATCHED = ("gtt-domain/", "docs/ideas/")
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def relevant(event):
    tool = event.get("tool_name", "")
    data = event.get("tool_input") or {}
    if tool in FILE_TOOLS:
        target = str(data.get("file_path") or data.get("path") or data.get("notebook_path") or "").replace("\\", "/")
        return any(mark in target for mark in WATCHED)
    command = str(data.get("command") or "").replace("\\", "/")
    return any(mark in command for mark in WATCHED) or ".gtt/scripts/gtt-" in command or "gtt " in command


def main():
    try:
        event = json.load(sys.stdin)
        if not relevant(event) or not os.path.isfile(".gtt/scripts/gtt-sonar.sh"):
            return 0
        subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "render", "--quiet"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
