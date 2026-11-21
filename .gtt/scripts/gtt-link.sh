#!/usr/bin/env bash
# GTT - the Sonar link of an Epic, a Story, a proposal, a review, a decision or a gap: so that a report to the human can carry it.
#
# A thin wrapper: the logic is in gtt_link.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-link.sh REF [REF ...] [--json]
#
# Exit 0 always (a ref that has no place in Sonar is left out; with nothing to link, it prints nothing).

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_link.py" "$@"
