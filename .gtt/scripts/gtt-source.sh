#!/usr/bin/env bash
# GTT - design sources - copy, version, register and verify them (docs/sources/); a source is immutable once registered.
#
# A thin wrapper: the logic is in gtt_design.py (source). See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-source.sh [arguments]

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_design.py" source "$@"
