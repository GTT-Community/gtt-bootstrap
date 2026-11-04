#!/usr/bin/env bash
# GTT - pending events: one small file per thing the human must attend, only in gtt-domain/pending/.
# A thin wrapper: the logic is in gtt_pending.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-pending.sh ask | decide | list | record | done | clean | check | notice
#   (`answer` is the human's act: gtt answer <n> <answer>)
#
# Exit 0 = ok, 1 = violation or refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_pending.py" "$@"
