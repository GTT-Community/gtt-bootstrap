#!/usr/bin/env bash
# GTT - the change flow during development: request a change, follow its proposals, step back.
#
# A thin wrapper: the logic is in gtt_change.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-change.sh request | state | next-action | proposals | show <name> | withdraw <name> | last | undo [<name>]
#
# Exit 0 = ok, 1 = refused or a violation, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_change.py" "$@"
