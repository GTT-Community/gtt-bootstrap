#!/usr/bin/env bash
# GTT - Method Governance: the development method is declared at setup, ratified as the Method Lock at
# freeze and verified afterwards. The Method Packs (.gtt/methods/) are the single source of each method.
#
# A thin wrapper: the logic is in gtt_method.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-method.sh catalog | list | show <id> | select | get | lock | check [--pre-freeze] | rules
#
# Exit 0 = ok (warnings allowed), 1 = violation or refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_method.py" "$@"
