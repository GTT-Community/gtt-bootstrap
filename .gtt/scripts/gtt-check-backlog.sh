#!/usr/bin/env bash
# GTT - backlog structural integrity gate.
#
# gtt-domain/backlog.md is not architecture (see AGENTS.md "Backlog"). It holds
# two kinds of entry, governed differently:
#
#   Epic   intent and scope - the human approves it;
#   Story  the operating plan of whoever does the work - the ADE creates,
#          splits, rewrites, implements and closes Stories with no approval.
#
# This gate keeps the structure tooling and people rely on: Epic and Story
# identifiers stay unique, status values stay inside the agreed vocabulary,
# an Epic that is Planned / In Progress / Completed carries its Goal and its
# `Approved`, and an Epic is Completed only when all its Stories are. The Epic
# rules live in gtt_backlog.py.
#
# It approves nothing and judges nothing: whether a Story is well written is
# not its business, and what the work does to the governed design is watched
# by observation (gtt-observe.sh), not by gating Stories in advance.
#
# Usage:
#   .gtt/scripts/gtt-check-backlog.sh [path-to-backlog.md]
#
# Exit 0 = pass, 1 = violation, 2 = cannot determine.

set -euo pipefail

BACKLOG="${1:-gtt-domain/backlog.md}"

if [ ! -f "$BACKLOG" ]; then
  echo "gtt-check-backlog: $BACKLOG not found." >&2
  exit 2
fi

EPIC_STATUSES="Proposed|Planned|In Progress|Completed|Cancelled"
# Planned is the vocabulary; Proposed / Undesigned / Ready are read as Planned (earlier versions).
STORY_STATUSES="Planned|In Progress|Blocked|Done|Cancelled|Proposed|Undesigned|Ready"
FAIL=0
CANNOT=0

# --- duplicate Epic IDs ---
DUP_EPICS="$(grep -oE '^### EPIC-[0-9]+' "$BACKLOG" | sed 's/^### //' | sort | uniq -d || true)"
if [ -n "$DUP_EPICS" ]; then
  echo "gtt-check-backlog: FAILED - duplicate Epic IDs:" >&2
  echo "$DUP_EPICS" | sed 's/^/  /' >&2
  FAIL=1
fi

# --- duplicate Story IDs (unique project-wide, not just per-Epic) ---
DUP_STORIES="$(grep -oE '^##### STORY-[0-9]+' "$BACKLOG" | sed 's/^##### //' | sort | uniq -d || true)"
if [ -n "$DUP_STORIES" ]; then
  echo "gtt-check-backlog: FAILED - duplicate Story IDs:" >&2
  echo "$DUP_STORIES" | sed 's/^/  /' >&2
  FAIL=1
fi

# --- Epic status vocabulary ---
BAD_EPIC_STATUS="$(grep -A2 '^### EPIC-' "$BACKLOG" | grep -E '^\*\*Status:\*\*' | grep -vE "^\*\*Status:\*\* ($EPIC_STATUSES)[[:space:]]*\$" || true)"
if [ -n "$BAD_EPIC_STATUS" ]; then
  echo "gtt-check-backlog: FAILED - Epic status outside {$EPIC_STATUSES}:" >&2
  echo "$BAD_EPIC_STATUS" | sed 's/^/  /' >&2
  FAIL=1
fi

# --- Story status vocabulary ---
BAD_STORY_STATUS="$(grep -A2 '^##### STORY-' "$BACKLOG" | grep -E '^[[:space:]]*- \*\*Status:\*\*' | grep -vE "^[[:space:]]*- \*\*Status:\*\* ($STORY_STATUSES)[[:space:]]*\$" || true)"
if [ -n "$BAD_STORY_STATUS" ]; then
  echo "gtt-check-backlog: FAILED - Story status outside {$STORY_STATUSES}:" >&2
  echo "$BAD_STORY_STATUS" | sed 's/^/  /' >&2
  FAIL=1
fi

# --- Epics with zero Stories (warning only - a freshly proposed Epic is legitimate) ---
EMPTY_EPICS="$(awk '
  /^### EPIC-/     { if (epic != "" && count == 0) print epic; epic=$0; count=0; next }
  /^##### STORY-/  { count++ }
  /^## /           { if (epic != "" && count == 0) print epic; epic=""; count=0 }
  END              { if (epic != "" && count == 0) print epic }
' "$BACKLOG" || true)"
if [ -n "$EMPTY_EPICS" ]; then
  echo "gtt-check-backlog: WARNING - Epics with no Stories yet:"
  echo "$EMPTY_EPICS" | sed 's/^/  /'
fi

# --- Epics are approved intent; an Epic is Completed only when its Stories are ---
HERE="$(cd "$(dirname "$0")" && pwd)"
READY_RC=0
bash "$HERE/gtt-run-python.sh" "$HERE/gtt_backlog.py" check "$BACKLOG" || READY_RC=$?
case "$READY_RC" in
  0) ;;
  1) FAIL=1 ;;
  *) echo "gtt-check-backlog: the Epic rules could not be determined (gtt_backlog.py did not run)." >&2; CANNOT=1 ;;
esac

if [ "$FAIL" -ne 0 ]; then
  cat >&2 <<MSG

gtt-check-backlog: FAILED

Structural integrity violations found above. An Epic ID must be unique, a
Story ID must be unique project-wide, and status values must stay inside
the agreed vocabulary so tooling and agents can rely on them without
re-parsing free text. An Epic is intent: once it is Planned, In Progress or
Completed it carries its Goal and who approved it and when - leave it
Proposed until the human has. An Epic is Completed only when every one of
its Stories is Done or Cancelled. Stories themselves need no approval.
MSG
  exit 1
fi

[ "$CANNOT" -ne 0 ] && exit 2

echo "gtt-check-backlog: OK"
