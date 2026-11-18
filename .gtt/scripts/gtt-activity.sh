#!/usr/bin/env bash
# GTT activity - the fixed-size journal of what the agent does (.gtt/local/activity.jsonl), and what is going on now.
# A thin wrapper: the logic is in gtt_activity.py. The journal never keeps content or arguments.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-activity.sh log [--ade ADE]      a PostToolUse hook: reads the tool event on stdin, writes one line
#   .gtt/scripts/gtt-activity.sh now [--json]          the Story in progress, its active hours, the last files and how long ago
#   .gtt/scripts/gtt-activity.sh hours STORY [--json]  the active hours of one Story
#
# Exit 0 always: a broken hook must never stop a tool call.

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_activity.py" "$@"
