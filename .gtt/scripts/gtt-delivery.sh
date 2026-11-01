#!/usr/bin/env bash
# GTT - Delivery Planning: who builds, how many fronts, for when; the plan, the forecast and the real time.
# A thin wrapper: the logic is in gtt_delivery.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-delivery.sh questions | select | get | plan [--lanes] | report | check [--pre-freeze] | log | summary
#
# Exit 0 = ok (warnings allowed), 1 = violation or refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_delivery.py" "$@"
