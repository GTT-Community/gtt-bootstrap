#!/usr/bin/env bash
# GTT backlog - check, summary and the human's `set` of gtt-domain/backlog.md. A thin wrapper: the logic is in gtt_backlog.py.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-backlog.sh check [--json] | summary | json | reorder [--apply]
#   .gtt/scripts/gtt-backlog.sh set REF --sha SHA --fields '{"Estimate": "1h"}' [--via sonar] [--apply]   (the human's act)
#
# Exit 0 = ok, 1 = refused, 2 = cannot run, 3 = the block changed since it was shown.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_backlog.py" "$@"
