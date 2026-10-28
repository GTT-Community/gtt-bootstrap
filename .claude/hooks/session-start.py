#!/usr/bin/env python3
"""Claude Code adapter for the GTT Session Memory Service.

Contains no GTT logic. It calls the ADE-independent wrapper
.gtt/scripts/gtt-session-context.sh, and translates its stdout into the
SessionStart JSON Claude Code consumes. Any failure is reported on stderr
with a non-zero exit (a visible, non-blocking hook error) - never swallowed.
"""
import json
import os
import subprocess
import sys

WRAPPER = ".gtt/scripts/gtt-session-context.sh"

# The bash to run GTT scripts with: on Windows a program started by name is
# found in the system directory first, and that is the WSL launcher.
sys.path.insert(0, os.path.join(".gtt", "scripts"))
try:
    from gtt_bash import bash_executable
except ImportError:  # an Engine without the resolver: the PATH decides
    def bash_executable():
        return "bash"

# The service's own GTT-SESSION-CONTEXT header carries every non-authority marker; repeating them here
# only spends the agent's context on every session.
BANNER = ""


def fail(message):
    print(f"GTT session-start hook: {message}", file=sys.stderr)
    sys.exit(1)


try:
    proc = subprocess.run(
        [bash_executable(), WRAPPER],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
except FileNotFoundError:
    fail("`bash` not found on PATH; cannot run " + WRAPPER)
except subprocess.TimeoutExpired:
    fail(WRAPPER + " timed out after 60s")

if proc.returncode != 0:
    detail = (proc.stderr or proc.stdout).strip() or "no output"
    fail(f"{WRAPPER} failed (exit {proc.returncode}): {detail}")
if not proc.stdout.strip():
    fail(WRAPPER + " produced no output")

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": BANNER + proc.stdout,
    }
}))
