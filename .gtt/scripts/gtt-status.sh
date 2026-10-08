#!/usr/bin/env bash
# GTT - status. Deterministic snapshot of current/governed/pending/proposed/
# blocked/frozen state, derived from repository artifacts rather than any
# ADE's private conversation memory - so the same project resumes the same
# way whichever ADE picks it up. It describes GTT's operational state only and
# names no ADE: anything specific to an ADE lives in its adapter.
#
# Also regenerates gtt-domain/session.md with the same content. That file is a
# DERIVED artifact, like .gtt/protection/registry.yaml: never hand-edited,
# safe to regenerate at any time, and never loaded automatically by any
# agent - it is operational context, not architectural authority, evidence,
# or a substitute for an ADR/decision record.
#
# The file opens with the review block (gtt-review.sh): the handoff between
# sessions and the human's review are one surface, not two reports. It is only
# rewritten when something other than its `Generated` line changed, so a session
# that changes nothing leaves the working tree alone.
#
# Usage:
#   .gtt/scripts/gtt-status.sh            print the state and refresh gtt-domain/session.md
#   .gtt/scripts/gtt-status.sh --check    only prove the state can be derived; writes nothing
#
# Exit 0 always (a status report that could fail to run would defeat its
# own purpose - if something below is missing, the report says so). With
# --check: 0 = the state was derived, 1 = it could not be.

set -uo pipefail

OUT="gtt-domain/session.md"
CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

if [ -f "gtt-domain/.frozen" ]; then
  FREEZE_LINE="frozen ($(head -1 gtt-domain/.frozen 2>/dev/null)) - the design is the authority; the implementation is free"
else
  FREEZE_LINE="pre-freeze (gtt-domain/context/ and gtt-domain/adr/ are agent-writable)"
fi

# Observation: what the work has done against the frozen governed state. Running
# it here is what keeps the governance backlog current in every ADE, with or
# without a hook: a session that starts by reading this file has just observed.
# Derived from Git, the filesystem and the freeze baseline - never from a model.
OBSERVATION="not available (.gtt/scripts/gtt-observe.sh not found)"
if [ -f ".gtt/scripts/gtt-observe.sh" ]; then
  if [ "$CHECK" -eq 1 ]; then
    bash .gtt/scripts/gtt-observe.sh observe --dry-run >/dev/null 2>&1 || true
  else
    bash .gtt/scripts/gtt-observe.sh observe >/dev/null 2>&1 || true
  fi
  OBSERVATION="$(bash .gtt/scripts/gtt-observe.sh baseline 2>&1 || true)
$(bash .gtt/scripts/gtt-observe.sh summary 2>&1 || true)
$(bash .gtt/scripts/gtt-observe.sh backlog 2>&1 | grep -E '^[^ ]' | head -20 || true)"
fi

IN_PROGRESS=""
BLOCKED=""
BACKLOG_LINE="not available (.gtt/scripts/gtt_backlog.py not found)"
if [ -f "gtt-domain/backlog.md" ]; then
  if [ -f ".gtt/scripts/gtt_backlog.py" ] && [ -f ".gtt/scripts/gtt-run-python.sh" ]; then
    BACKLOG_LINE="$(bash .gtt/scripts/gtt-run-python.sh .gtt/scripts/gtt_backlog.py summary 2>&1 || true)"
  fi
  IN_PROGRESS="$(grep -B2 -E '^\s*-\s*\*\*Status:\*\*\s*In Progress\s*$' gtt-domain/backlog.md 2>/dev/null | grep -oE '^##### STORY-[0-9]+.*' || true)"
  BLOCKED="$(grep -B2 -E '^\s*-\s*\*\*Status:\*\*\s*Blocked\s*$' gtt-domain/backlog.md 2>/dev/null | grep -oE '^##### STORY-[0-9]+.*' || true)"
fi

PENDING_PROPOSALS="$(cd gtt-domain/proposals 2>/dev/null && find . -maxdepth 1 -type f ! -name 'README.md' | sed 's|^\./||' || true)"

CR_STATE="no gtt-domain/change-request.md found"
if [ -f "gtt-domain/change-request.md" ]; then
  if grep -qE '^Change: <' gtt-domain/change-request.md 2>/dev/null; then
    CR_STATE="empty (still template placeholders)"
  else
    CR_STATE="FILLED IN - review it, a change request is waiting"
  fi
fi

ADRS=""
if [ -d "gtt-domain/adr" ]; then
  ADRS="$(grep -H '^- Status:' gtt-domain/adr/ADR-[0-9]*.md 2>/dev/null | sed -E 's#gtt-domain/adr/##; s#:- Status:# - Status:#' || true)"
fi

GUARD_COUNT=0
if [ -f ".gtt/protection/registry.yaml" ]; then
  GUARD_COUNT="$(grep -cE '^\s*-\s*artifact:' .gtt/protection/registry.yaml 2>/dev/null)"
  GUARD_COUNT="${GUARD_COUNT:-0}"
fi

# ADE integration state (Multi-ADE): which ADEs the human chose to have
# participate, which one is Primary, and whether each integration is intact.
# Read from .gtt/ade.json through the ADE-independent service; this script
# names no ADE. Workflow state only - the Primary ADE holds no authority.
ADE_STATE="not configured (.gtt/scripts/gtt-ade.sh not found)"
if [ -f ".gtt/scripts/gtt-ade.sh" ]; then
  ADE_STATE="$(bash .gtt/scripts/gtt-ade.sh state 2>&1 || true)"
fi

# Evidence / governance state: sources, gaps, conflicts, provenance tags, working
# agreements - counted from the governed artifacts by the provenance engine. Derived state,
# never agent notes and never authority.
GOV_STATE="not available (.gtt/scripts/gtt_provenance.py not found)"
if [ -f ".gtt/scripts/gtt_provenance.py" ] && [ -f ".gtt/scripts/gtt-run-python.sh" ]; then
  GOV_STATE="$(bash .gtt/scripts/gtt-run-python.sh .gtt/scripts/gtt_provenance.py summary 2>&1 || true)"
fi

# Bootstrap release identity and Method Plan (Bootstrap 1.0 contracts). The full structured
# view is `gtt-project.sh status --json`; this is the human-readable line.
BOOTSTRAP_STATE="not available (.gtt/scripts/gtt-contract.sh not found)"
if [ -f ".gtt/scripts/gtt-contract.sh" ] && [ -f ".gtt/scripts/gtt-project.sh" ]; then
  BOOTSTRAP_STATE="$(bash .gtt/scripts/gtt-contract.sh release 2>&1 || true)
$(bash .gtt/scripts/gtt-project.sh profile get 2>&1 || true)"
fi

# The review surface: what changed, what it touches, what the human must decide. One
# block, computed from the repository, shared by the session handoff and the review.
REVIEW="not available (.gtt/scripts/gtt-review.sh not found)"
if [ -f ".gtt/scripts/gtt-review.sh" ]; then
  REVIEW="$(bash .gtt/scripts/gtt-review.sh 2>&1 || true)"
fi

# Artifact identity/index state and repository resume hints. Both are derived
# from the repository (manifest, index, git) - never from ADE memory.
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
ARTIFACT_STATE="cannot determine (no working Python 3 interpreter)"
if [ -n "$PY" ] && [ -f ".gtt/scripts/gtt_artifacts.py" ]; then
  ARTIFACT_STATE="$("$PY" .gtt/scripts/gtt_artifacts.py summary 2>&1 || true)"
fi

GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "not a git repository")"
GIT_DIRTY="$(git status --porcelain -- . ':(exclude)gtt-domain/session.md' 2>/dev/null | wc -l | tr -d ' ')"
GIT_RECENT="$(git log -5 --format='%h %s' 2>/dev/null || true)"

CONTENT="$({
  echo "# GTT Session State"
  echo "#"
  echo "# Generated by .gtt/scripts/gtt-status.sh. Derived, like a lockfile -"
  echo "# never hand-edited; re-run the script to refresh."
  echo "#"
  echo "# operational-only. NOT authority, NOT evidence, NOT a decision record,"
  echo "# NOT a grounding source, NOT a substitute for an ADR. Governed context"
  echo "# (gtt-domain/context/, gtt-domain/adr/) and gtt-domain/backlog.md prevail over this file."
  echo "#"
  echo "# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo
  echo "## Review (computed from the repository - what to look at first; never a decision)"
  echo "${REVIEW}"
  echo
  echo "## Freeze state"
  echo "${FREEZE_LINE}"
  echo
  echo "## Current work (Stories In Progress)"
  if [ -n "$IN_PROGRESS" ]; then echo "$IN_PROGRESS"; else echo "none"; fi
  echo
  echo "## Blocked (Stories Blocked)"
  if [ -n "$BLOCKED" ]; then echo "$BLOCKED"; else echo "none"; fi
  echo
  echo "## Backlog (Epics are approved intent; Stories are the working plan and need no approval)"
  echo "${BACKLOG_LINE}"
  echo
  echo "## Observation (the work against the frozen governed state - signals, never decisions)"
  echo "${OBSERVATION}"
  echo
  echo "## Pending proposals (gtt-domain/proposals/, excluding README.md)"
  if [ -n "$PENDING_PROPOSALS" ]; then echo "$PENDING_PROPOSALS"; else echo "none"; fi
  echo
  echo "## Change request"
  echo "${CR_STATE}"
  echo
  echo "## ADRs"
  if [ -n "$ADRS" ]; then echo "$ADRS"; else echo "none"; fi
  echo
  echo "## GTTGuard"
  echo "${GUARD_COUNT} protected artifact(s) in .gtt/protection/registry.yaml"
  echo
  echo "## ADE integration (workflow state only - the Primary ADE holds no authority)"
  echo "${ADE_STATE}"
  echo
  echo "## Evidence / Governance (derived state - never agent notes, never authority)"
  echo "${GOV_STATE}"
  echo
  echo "## Bootstrap and methodology (contracts in .gtt/contract/ - data, never authority)"
  echo "${BOOTSTRAP_STATE}"
  echo
  echo "## Artifact identity and technical index"
  echo "${ARTIFACT_STATE}"
  echo
  echo "## Repository (resume hints)"
  echo "branch: ${GIT_BRANCH}; uncommitted paths: ${GIT_DIRTY}"
  if [ -n "$GIT_RECENT" ]; then echo "recent commits:"; echo "$GIT_RECENT"; fi
})"

if [ "$CHECK" -eq 1 ]; then
  if printf '%s\n' "$CONTENT" | grep -q '^## Repository (resume hints)'; then
    echo "gtt-status: OK - the session state can be derived from the repository."
    exit 0
  fi
  echo "gtt-status: FAILED - the session state could not be derived." >&2
  exit 1
fi

# Rewritten only when something other than the `Generated` line changed.
if [ ! -f "$OUT" ] || [ "$(grep -v '^# Generated: ' "$OUT" 2>/dev/null)" != "$(printf '%s\n' "$CONTENT" | grep -v '^# Generated: ')" ]; then
  printf '%s\n' "$CONTENT" > "$OUT"
fi
printf '%s\n' "$CONTENT"

exit 0
