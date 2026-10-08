#!/usr/bin/env bash
# GTT - the solution design of each Epic - scaffold it, check it is complete, see what no Story builds yet.
#
# A thin wrapper: the logic is in gtt_design.py (design). See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-design.sh [arguments]

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_design.py" design "$@"
