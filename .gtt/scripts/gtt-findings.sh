#!/usr/bin/env bash
# GTT findings - everything GTT detects, in one shape, stuck to a reference (an Epic, a Story, a gap, an entry).
# A thin wrapper: the logic is in gtt_findings.py, which joins what the scripts that own each fact emit. It changes nothing.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-findings.sh list [--json] [--plane P] [--owner O] [--level L] [--ref REF]
#   .gtt/scripts/gtt-findings.sh ready [REF] [--json]
#   .gtt/scripts/gtt-findings.sh line
#
# Exit 0 always: a finding never stops anything.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_findings.py" "$@"
