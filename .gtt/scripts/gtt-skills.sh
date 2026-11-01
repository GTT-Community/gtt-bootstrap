#!/usr/bin/env bash
# GTT - skill mirrors: the Claude Code skill is the source; Codex, Copilot and Kiro get a generated copy where
# each one reads skills. A thin wrapper: the logic is in gtt_skills.py.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-skills.sh sync [--apply] | check
#
# Exit 0 = ok, 1 = drift or a missing mirror, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_skills.py" "$@"
