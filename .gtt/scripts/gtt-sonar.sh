#!/usr/bin/env bash
# GTT Sonar - the read-only view of the project: a snapshot (JSON) and the page built from it.
# A thin wrapper: the logic is in gtt_sonar.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-sonar.sh snapshot [--json] | render [--quiet] | start | watch | prefs [--open-on-start on|off] [--watch on|off]
#
# Exit 0 = ok, 1 = refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_sonar.py" "$@"
