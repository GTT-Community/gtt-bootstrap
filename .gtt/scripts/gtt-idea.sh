#!/usr/bin/env bash
# GTT - Ideas: the human's loose ideas, one file each in docs/ideas/. A thin wrapper: the logic is in gtt_idea.py.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-idea.sh add "<text>" | --file PATH [--apply]      (human) write the idea as is
#   .gtt/scripts/gtt-idea.sh triage IDEA-NNN --result covered|converted|non-goal|ask --to REF [--apply]
#   .gtt/scripts/gtt-idea.sh park IDEA-NNN [--apply] | drop IDEA-NNN [--apply]   (human)
#   .gtt/scripts/gtt-idea.sh list [--json] [--all]
#
# Exit 0 = ok, 1 = refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_idea.py" "$@"
