#!/usr/bin/env bash
# GTT - stack map freshness gate.
#
# The instruction layer asks agents to keep gtt-domain/context/stack.md current.
# This makes it deterministic: if a change adds or edits an ADR without
# touching the map, the build fails.
#
# Usage:
#   scripts/gtt-check-stack.sh              # compare against origin/main
#   scripts/gtt-check-stack.sh <base-ref>   # compare against another ref
#
# It also guards the freeze itself. There is no unfreeze: if the base ref was
# frozen, the change under review must still be frozen, and the baseline the base
# recorded must still be there - as the current baseline or in the history of
# earlier freezes. This is the one check that holds for an ADE with no hooks, and
# for a write no hook can see (an interpreter, Git plumbing).
#
# Exit 0 = pass, 1 = violation, 2 = cannot determine.

set -euo pipefail

BASE="${1:-origin/main}"
MAP="gtt-domain/context/stack.md"

MARKER="gtt-domain/.frozen"

# --- the freeze marker is never removed and its history is never rewritten ---
# Looked at before the "not frozen yet" exit below on purpose: a tree whose marker
# was deleted looks exactly like a project that was never frozen.
if git rev-parse --verify --quiet "$BASE" >/dev/null 2>&1 && git cat-file -e "$BASE:$MARKER" 2>/dev/null; then
  if [ ! -f "$MARKER" ]; then
    echo "gtt-check-stack: FAILED - freeze marker removed — there is no unfreeze." >&2
    echo "  $BASE has $MARKER and this tree does not. A governed change is completed by a" >&2
    echo "  new freeze (gtt-freeze.sh, run by the human), never by removing the marker." >&2
    exit 1
  fi
  BASE_AT="$(git show "$BASE:$MARKER" | head -1)"
  BASE_DIGEST="$(git show "$BASE:$MARKER" | sed -n '/^#/q;s/^Governed digest:[[:space:]]*//p' | head -1)"
  if ! git show "$BASE:$MARKER" | cmp -s - "$MARKER"; then
    if ! grep -qF -- "$BASE_AT" "$MARKER" || { [ -n "$BASE_DIGEST" ] && ! grep -qF -- "$BASE_DIGEST" "$MARKER"; }; then
      echo "gtt-check-stack: FAILED - freeze history rewritten." >&2
      echo "  The baseline $BASE recorded ($BASE_AT) is no longer in $MARKER, neither as the" >&2
      echo "  current baseline nor under '# earlier freezes'. A new freeze keeps the earlier one." >&2
      exit 1
    fi
  fi
fi

if [ ! -f "$MARKER" ]; then
  echo "gtt-check-stack: project is not frozen yet, nothing to enforce."
  exit 0
fi

# --- referential integrity: every ADR cited in the map must exist ---
# Runs unconditionally (governed regime, any invocation) - a dangling
# citation is wrong regardless of whether this diff touched an ADR.
MISSING=""
while read -r adr; do
  [ -z "$adr" ] && continue
  if ! ls "gtt-domain/adr/${adr}"*.md >/dev/null 2>&1; then
    MISSING="$MISSING  $adr\n"
  fi
done < <(grep -oE 'ADR-[0-9]{3}' "$MAP" | sort -u)

if [ -n "$MISSING" ]; then
  echo "gtt-check-stack: FAILED - the map cites ADRs that do not exist:" >&2
  printf "%b" "$MISSING" >&2
  echo "A citation to a file nobody can open is not governance." >&2
  exit 1
fi

# --- boundaries block presence (gtt-boundaries; gtt-drift-signals is its earlier name) ---
if ! grep -qE '^```gtt-(boundaries|drift-signals)' "$MAP"; then
  echo "gtt-check-stack: NOTE - $MAP declares no gtt-boundaries block."
  echo "                  Observation then knows only the built-in boundaries"
  echo "                  (the governed context itself and @GTTGuard artifacts)."
fi

if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  echo "gtt-check-stack: cannot resolve base ref '$BASE'" >&2
  exit 2
fi

CHANGED="$(git diff --name-only "$BASE"...HEAD)"

ADR_CHANGED="$(echo "$CHANGED" | grep -E '^gtt-domain/adr/ADR-[0-9]+' || true)"
MAP_CHANGED="$(echo "$CHANGED" | grep -Fx "$MAP" || true)"

if [ -z "$ADR_CHANGED" ]; then
  echo "gtt-check-stack: no ADR changes, nothing to enforce."
  exit 0
fi

if [ -n "$MAP_CHANGED" ]; then
  echo "gtt-check-stack: ADR change accompanied by a map update."
  echo "$ADR_CHANGED" | sed 's/^/  ADR: /'
  exit 0
fi

cat >&2 <<MSG
gtt-check-stack: FAILED

These ADRs changed without updating $MAP:

$(echo "$ADR_CHANGED" | sed 's/^/  /')

An architectural decision that is not reflected in the stack map is invisible to
everyone who reads the map to understand the system - which is everyone.

Update the map's affected rows and append a row to its change log. If the
decision genuinely does not alter the map, say so in the ADR and add a change
log row recording that.
MSG
exit 1
