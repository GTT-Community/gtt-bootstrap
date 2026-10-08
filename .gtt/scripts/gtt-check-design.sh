#!/usr/bin/env bash
# GTT - design gate. Every Epic's solution design is complete, the same in every Method
# Plan and at every THINK Depth: eight sections, every listed source section cited,
# every rule and flow in an example, and nothing left unbuilt when the Epic closes.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-check-design.sh [EPIC-NNN] [--pre-freeze]
#
# Exit 0 = pass (warnings allowed), 1 = violation, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_design.py" design check "$@"
