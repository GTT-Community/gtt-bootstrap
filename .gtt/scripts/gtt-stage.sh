#!/usr/bin/env bash
# GTT - prepare a promotion set under gtt-domain/proposals/staged/ (applies nothing).
#
# A thin wrapper: the logic is in gtt_flow.py (stage). See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-stage.sh [arguments]

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_flow.py" stage "$@"
