#!/usr/bin/env bash
# GTT - the review surface - what changed, what it touches, what the human must decide (read-only).
#
# A thin wrapper: the logic is in gtt_flow.py (review). See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-review.sh [arguments]

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_flow.py" review "$@"
