#!/usr/bin/env bash
# GTT - keep the disk from filling when agents work in parallel (work copies, ADE folders, free space).
#
# A thin wrapper: the logic is in gtt_disk.py. See that file for the usage.
#
# Usage (from the project root or any work copy):
#   .gtt/scripts/gtt-disk.sh check [--json] | status [--json] | prune [PATH...] [--apply] | set [--max-copies N] [--max-gb N] [--min-free-gb N] | --off | --default [--apply]
#
# Exit 0 = ok (a check never fails for what it finds), 1 = refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_disk.py" "$@"
