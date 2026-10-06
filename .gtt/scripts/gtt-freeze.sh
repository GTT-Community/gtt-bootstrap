#!/usr/bin/env bash
# GTT - freeze. The act of ratification.
#
# Run by the Solution Designer, never by an agent. Freeze does not mean "the
# code cannot change": it means "the design the human approved is now the
# authority". It validates that the governed context holds real content, then
# records the governance baseline - when, by whom, the commit and a digest of the
# governed state - that observation (gtt-observe.sh) compares the work against.
#
# The implementation stays free. What is frozen is intent and boundaries.
#
# There is no unfreeze. When a governed change has been promoted, the governed
# state has moved and this script is run again: it records a NEW baseline and
# keeps the earlier one as history. Run on an unchanged governed state it does
# nothing.
#
# Exit 0 = frozen (first freeze or a new baseline), 1 = validation failed,
#      2 = already frozen and the governed state has not changed.

set -euo pipefail

MARKER="gtt-domain/.frozen"
CTX="gtt-domain/context"
REQUIRED=(stack.md architecture.md solution-vision.md principles.md constraints.md glossary.md)
HERE="$(cd "$(dirname "$0")" && pwd)"

DIGEST="$(bash "$HERE/gtt-observe.sh" digest)" || { echo "gtt-freeze: cannot compute the governed digest." >&2; exit 1; }

REFREEZE=0
if [ -f "$MARKER" ]; then
  RECORDED="$(sed -n '/^#/q;s/^Governed digest:[[:space:]]*//p' "$MARKER" | head -1)"
  if [ "$RECORDED" = "$DIGEST" ]; then
    echo "gtt-freeze: already frozen ($MARKER exists, written $(head -1 "$MARKER")) and the governed" >&2
    echo "             state has not changed since. Nothing to do." >&2
    exit 2
  fi
  REFREEZE=1
fi

fail=0
for f in "${REQUIRED[@]}"; do
  path="$CTX/$f"
  if [ ! -f "$path" ]; then
    echo "gtt-freeze: missing $path" >&2
    fail=1
    continue
  fi
  lines="$(grep -cve '^\s*$' "$path" || true)"
  if [ "$lines" -le 5 ]; then
    echo "gtt-freeze: $path has $lines non-empty lines - still effectively empty" >&2
    fail=1
  fi
  if grep -qE 'TODO|PLACEHOLDER|REPLACE ME|<[a-z][^>]*>' "$path"; then
    echo "gtt-freeze: $path still contains template placeholders" >&2
    fail=1
  fi
done

if ! ls gtt-domain/adr/ADR-001*.md >/dev/null 2>&1; then
  echo "gtt-freeze: ADR-001 not found under gtt-domain/adr/" >&2
  fail=1
fi

# Provenance / gap / source rules: a pending BLOCKING gap, an unresolved
# [CONFLICTO], a [PROPUESTA] inside governed context or a malformed source manifest
# refuse the freeze. A valid OPEN gap does not: it is known, scoped and visible.
if [ -f "$HERE/gtt-check-provenance.sh" ]; then
  if ! bash "$HERE/gtt-check-provenance.sh" --pre-freeze >&2; then
    echo "gtt-freeze: provenance / gap / source rules do not hold (see above)" >&2
    fail=1
  fi
fi

# The boundaries the freeze ratifies must be well formed, and a new baseline is not
# drawn over a governance observation nobody has decided: accept, reject or defer it
# first. (The governed state having moved is the very reason for a new freeze, so that
# one observation is not a reason to refuse it.)
if ! bash "$HERE/gtt-observe.sh" boundaries >/dev/null; then
  echo "gtt-freeze: the gtt-boundaries block of $CTX/stack.md is malformed (bash .gtt/scripts/gtt-observe.sh boundaries)" >&2
  fail=1
fi
if [ "$REFREEZE" -eq 1 ] && ! bash "$HERE/gtt-observe.sh" check --strict --for-freeze >&2; then
  echo "gtt-freeze: undecided observations remain in the governance backlog (see above)" >&2
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  cat >&2 <<'MSG'

gtt-freeze: FAILED

Freezing is a ratification, not a file move. Context that is still template
text would be ratified as if it were a decision. Fix what is listed above, or
run the gtt-bootstrap skill, then try again.
MSG
  exit 1
fi

COMMIT="$(git rev-parse HEAD 2>/dev/null || echo none)"
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
HISTORY=""
if [ "$REFREEZE" -eq 1 ]; then
  PREV_AT="$(head -1 "$MARKER")"
  PREV_BY="$(sed -n '/^#/q;s/^Frozen by:[[:space:]]*//p' "$MARKER" | head -1)"
  PREV_COMMIT="$(sed -n '/^#/q;s/^Baseline commit:[[:space:]]*//p' "$MARKER" | head -1)"
  HISTORY="$(printf '%s | %s | %s | %s\n' "$PREV_AT" "${PREV_BY:-unknown}" "${PREV_COMMIT:-none}" "${RECORDED:-none}"; sed -n '/^# earlier freezes/,$p' "$MARKER" | tail -n +2)"
fi

{
  echo "$NOW"
  echo "Frozen by: ${USER:-unknown}"
  echo "Baseline commit: $COMMIT"
  echo "Governed digest: $DIGEST"
  if [ -n "$HISTORY" ]; then
    echo "# earlier freezes (when | by | baseline commit | governed digest) - history, newest first"
    echo "$HISTORY"
  fi
} > "$MARKER"

if [ -d "gtt-domain/proposals/bootstrap" ]; then
  rm -rf gtt-domain/proposals/bootstrap
  echo "gtt-freeze: removed gtt-domain/proposals/bootstrap (superseded by ratified context)."
fi

if [ "$COMMIT" = "none" ]; then
  echo "gtt-freeze: NOTE - no Git commit to record as the baseline: path and dependency boundaries"
  echo "            cannot be observed until a freeze is taken on a committed repository."
elif [ -n "$(git status --porcelain -- . ':!gtt-domain' 2>/dev/null)" ]; then
  echo "gtt-freeze: NOTE - there are uncommitted changes outside gtt-domain/. They will be observed"
  echo "            as changes since this freeze. Commit before freezing for a clean baseline."
fi

if [ "$REFREEZE" -eq 1 ]; then
  cat <<'MSG'
gtt-freeze: DONE - new governance baseline

The governed state that was promoted is now the authority, and observation
compares the work against it from here. The earlier freeze is kept as history
in gtt-domain/.frozen. Commit gtt-domain/.frozen.
MSG
else
  cat <<'MSG'
gtt-freeze: DONE

The design is now the authority: gtt-domain/context/ and gtt-domain/adr/ change
only through gtt-domain/change-request.md -> gtt-domain/proposals/ -> you apply
-> a new freeze. The implementation stays free: the ADE works on its own inside
these boundaries and GTT observes (bash .gtt/scripts/gtt-observe.sh observe).

Commit gtt-domain/.frozen. It is versioned on purpose: a clone of a frozen project
stays frozen.
MSG
fi
