#!/usr/bin/env python3
"""GTT - session context for ADEs whose session-start hook answers in JSON (Cursor, OpenHands).

A Session Memory adapter, under .gtt/docs/session-adapter-contract.md. It holds no logic of its
own: the service (gtt-session-context.sh) produces the context and this script only wraps it in
the field the ADE reads. If the service fails, this fails where it can be seen - a message on
stderr and exit 1, never 2, which some ADEs take as "block the session".

  gtt_session_hook.py cursor       {"additional_context": ...}
  gtt_session_hook.py openhands    {"additionalContext": ...}
"""

import json
import os
import subprocess
import sys

FIELDS = {"cursor": "additional_context", "openhands": "additionalContext"}
WRAPPER = os.path.join(".gtt", "scripts", "gtt-session-context.sh")


def fail(message):
    print(f"GTT session hook: {message}", file=sys.stderr)
    sys.exit(1)


def main(argv):
    if len(argv) != 2 or argv[1] not in FIELDS:
        fail("usage: gtt_session_hook.py " + "|".join(sorted(FIELDS)))
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        proc = subprocess.run(["bash", WRAPPER], cwd=root, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
    except FileNotFoundError:
        fail("`bash` not found on PATH; cannot run " + WRAPPER)
    except subprocess.TimeoutExpired:
        fail(WRAPPER + " timed out after 60s")
    if proc.returncode != 0:
        fail(f"{WRAPPER} failed (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip() or 'no output'}")
    if not proc.stdout.strip():
        fail(WRAPPER + " produced no output")
    print(json.dumps({FIELDS[argv[1]]: proc.stdout}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
