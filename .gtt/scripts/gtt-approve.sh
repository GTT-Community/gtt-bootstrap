#!/usr/bin/env bash
# GTT - approve an Epic and its design together - run by the human, never by an agent.
#
# A thin wrapper: the logic is in gtt_design.py (approve). See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-approve.sh [arguments]

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_design.py" approve "$@"
