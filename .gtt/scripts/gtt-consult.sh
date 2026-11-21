#!/usr/bin/env bash
# GTT - the consultation thread: the questions that need thinking go to ONE conversation in Claude web.
#
# A thin wrapper: the logic is in gtt_consult.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-consult.sh status | seed | batch [REF] | set URL | clear | seen | answers [--text T] [--apply]
#
# Exit 0 = ok, 1 = refused (a URL that is not a Claude web conversation, an answer that cannot be recorded), 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_consult.py" "$@"
