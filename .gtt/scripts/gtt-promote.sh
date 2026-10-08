#!/usr/bin/env bash
# GTT - apply a staged promotion set - run by the human, never by an agent.
#
# A thin wrapper: the logic is in gtt_flow.py (promote). See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-promote.sh [arguments]

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_flow.py" promote "$@"
