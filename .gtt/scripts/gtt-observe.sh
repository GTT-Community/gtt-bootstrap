#!/usr/bin/env bash
# GTT - Observation (the Work plane).
#
# Governance decides what the system is supposed to be; observation reports what
# is actually happening. This compares the project with the frozen governed state
# - Git, the filesystem, dependency manifests, the GTTGuard registry, the freeze
# baseline: computed facts, never a model's opinion - and keeps every meaningful
# deviation in the governance backlog (gtt-domain/governance-backlog.json), so
# nothing is lost and nothing is reported twice.
#
# It never approves work and never asks for approval. Only a boundary the human
# ratified as BLOCKING, or an observation the human rejected, stops anything.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-observe.sh observe            # silent unless something is new
#   .gtt/scripts/gtt-observe.sh observe --debounce 20   # the same, at most once every 20 seconds (hooks)
#   .gtt/scripts/gtt-observe.sh check [--strict]   # for CI, freeze and promotion
#   .gtt/scripts/gtt-observe.sh backlog [--all]    # what is still open
#   .gtt/scripts/gtt-observe.sh accept|reject|defer OBS-NNNN --by NAME [--apply]
#   .gtt/scripts/gtt-observe.sh baseline | boundaries | summary | show OBS-NNNN
#
# accept / reject / defer are the human's decisions: an agent never runs them.
#
# Exit 0 = nothing that must stop, 1 = a BLOCKING condition or a failed check, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_observe.py" "$@"
