#!/usr/bin/env bash
# GTT code - what was built and whether it respects the architecture: the modules of stack.md 5 against the real imports of the code.
# A thin wrapper: the logic is in gtt_code.py. It reads files and the activity journal; it changes nothing outside .gtt/local/ (a derived index).
#
# Usage (from the project root):
#   .gtt/scripts/gtt-code.sh map [--epic EPIC-n | --story STORY-n] [--since freeze|yesterday|<ref>] [--json] [--cached]
#   .gtt/scripts/gtt-code.sh refresh [--quiet]     rebuild the index (the Sonar watcher calls it; a snapshot never does)
#
# Exit 0 always.

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_code.py" "$@"
