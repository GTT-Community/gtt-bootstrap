#!/usr/bin/env bash
# GTT - hand a human act over: ONE message, the command built and checked by this script.
#
# A thin wrapper: the logic is in gtt_handoff.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-handoff.sh promote <set> | approve <EPIC-NNN> | accept|reject|defer <OBS-NNNN> | freeze | run <n> [--json]
#
# Exit 0 = the message to show, 1 = the act cannot be handed over (what is wrong is said), 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_handoff.py" "$@"
