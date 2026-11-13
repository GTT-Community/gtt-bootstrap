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
LOG = "gtt-domain/delivery-log.jsonl"


def log_size():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def notice(before):
    """A Story that just moved to Done is a cut point: one line says what waits for triage in the inbox. Nothing is
    printed when nothing is new, so it costs no tokens; the agent decides what to do with it."""
    try:
        with open(LOG, encoding="utf-8") as handle:
            handle.seek(before)
            rows = [json.loads(line) for line in handle.read().splitlines() if line.strip()]
        if not any(r.get("kind") == "story" and r.get("to") == "Done" for r in rows):
            return
        if not os.path.isfile(".gtt/scripts/gtt-project.sh") or not os.path.isfile(".gtt/contract/inbox.json"):
            return
        done = subprocess.run(["bash", ".gtt/scripts/gtt-project.sh", "inbox-line", "--triage"], capture_output=True, text=True, timeout=20)
        line = done.stdout.strip()
        if line:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": line}}))
    except Exception:
        pass


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
    before = log_size()
    try:
        subprocess.run(["bash", ".gtt/scripts/gtt-delivery.sh", "log"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        pass
    if log_size() > before and os.path.isfile(".gtt/scripts/gtt-inbox.sh") and os.path.isfile(".gtt/contract/inbox.json"):
        # A Story or an Epic changed state: the inbox writes down what that closes (deterministic, no model, no tokens).
        try:
            subprocess.run(["bash", ".gtt/scripts/gtt-inbox.sh", "reconcile"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        except Exception:
            pass
    notice(before)
    return 0


if __name__ == "__main__":
    sys.exit(main())
