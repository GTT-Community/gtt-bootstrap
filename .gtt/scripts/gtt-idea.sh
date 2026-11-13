#!/usr/bin/env bash
# GTT - Ideas: the old name of the inbox. An alias of gtt-inbox.sh with the ideas' own commands and list format.
# The logic is in gtt_inbox.py (--as-ideas); an idea is an IDEA-NNN entry of the inbox (.gtt/contract/inbox.json).
#
# Usage (from the project root):
#   .gtt/scripts/gtt-idea.sh add "<text>" | --file PATH [--apply]      (human) write the idea as is
#   .gtt/scripts/gtt-idea.sh triage IDEA-NNN --result covered|converted|non-goal|ask --to REF [--apply]
#   .gtt/scripts/gtt-idea.sh park IDEA-NNN [--apply] | drop IDEA-NNN [--apply]   (human)
#   .gtt/scripts/gtt-idea.sh list [--json] [--all]
# The whole inbox (proposals, requests, ADR drafts, priorities) is gtt-inbox.sh.
#
# Exit 0 = ok, 1 = refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_inbox.py" --as-ideas "$@"
