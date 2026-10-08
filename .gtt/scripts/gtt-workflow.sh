#!/usr/bin/env bash
# GTT - the Git policy the human declared in gtt-domain/workflow.md (read-only).
#
# A thin wrapper: the logic is in gtt_flow.py (workflow). See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-workflow.sh [arguments]

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_flow.py" workflow "${@:-get}"
