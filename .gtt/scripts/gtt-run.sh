#!/usr/bin/env bash
# GTT - simple execution: a plan the agent writes, a sealed script GTT generates, one command the human runs.
# A thin wrapper: the logic is in gtt_run.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-run.sh new <slug> | generate <RUN> | check [<RUN>] | list | execute <RUN> --confirmed-by-human
#
# Exit 0 = ok (warnings allowed), 1 = violation or refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_run.py" "$@"
