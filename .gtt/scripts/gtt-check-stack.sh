#!/usr/bin/env bash
# GTT - stack map freshness gate.
#
# The instruction layer asks agents to keep gtt-domain/context/stack.md current.
# This makes it deterministic: if a change adds or edits an ADR without
# touching the map, the build fails.
#
# Usage:
#   scripts/gtt-check-stack.sh              # resolve the base ref (see below)
#   scripts/gtt-check-stack.sh <base-ref>   # compare against that ref
#   scripts/gtt-check-stack.sh --ci [<base-ref>]   # CI mode even when CI is unset
#
# It also guards the freeze itself. There is no unfreeze: if the base ref was
# frozen, the change under review must still be frozen, and the baseline the base
# recorded must still be there - as the current baseline or in the history of
# earlier freezes. This is the one check that holds for an ADE with no hooks, and
# for a write no hook can see (an interpreter, Git plumbing).
#
# The base ref, first one that resolves:
#   1. the argument;
#   2. the pull request's target branch as the CI system exposes it -
#      GITHUB_BASE_REF (GitHub Actions), CI_MERGE_REQUEST_TARGET_BRANCH_NAME
#      (GitLab CI), SYSTEM_PULLREQUEST_TARGETBRANCH (Azure DevOps);
#   3. the remote's default branch (origin/HEAD);
#   4. origin/main.
#
# Without a base ref a tree whose marker was deleted looks exactly like a project
# that was never frozen, so the check never passes in silence there: in CI
# (CI=true, TF_BUILD=True, or --ci) it exits 2; anywhere else it prints a NOTE
# that the check did not run and goes on.
#
# Exit 0 = pass, 1 = violation, 2 = cannot determine.

set -euo pipefail

IN_CI=0
case "${CI:-}${TF_BUILD:-}" in *[Tt]rue*|*1*) IN_CI=1 ;; esac
EXPLICIT=""
for arg in "$@"; do
  case "$arg" in
    --ci) IN_CI=1 ;;
    *) EXPLICIT="$arg" ;;
  esac
done

MAP="gtt-domain/context/stack.md"

MARKER="gtt-domain/.frozen"

resolves() { git rev-parse --verify --quiet "$1^{commit}" >/dev/null 2>&1; }

# A branch name from a CI variable: the remote-tracking ref first, then the name itself.
from_branch() {
  local name="${1#refs/heads/}"
  [ -n "$name" ] || return 1
  if resolves "origin/$name"; then echo "origin/$name"; return 0; fi
  if resolves "$name"; then echo "$name"; return 0; fi
  return 1
}

resolve_base() {
  local candidate
  if [ -n "$EXPLICIT" ]; then
    resolves "$EXPLICIT" && { echo "$EXPLICIT"; return 0; }
    return 1
  fi
  for candidate in "${GITHUB_BASE_REF:-}" "${CI_MERGE_REQUEST_TARGET_BRANCH_NAME:-}" "${SYSTEM_PULLREQUEST_TARGETBRANCH:-}"; do
    from_branch "$candidate" && return 0
  done
  candidate="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  [ -n "$candidate" ] && resolves "$candidate" && { echo "$candidate"; return 0; }
  resolves origin/main && { echo origin/main; return 0; }
  return 1
}

WANTED="${EXPLICIT:-${GITHUB_BASE_REF:-${CI_MERGE_REQUEST_TARGET_BRANCH_NAME:-${SYSTEM_PULLREQUEST_TARGETBRANCH:-origin/HEAD or origin/main}}}}"
BASE="$(resolve_base || true)"

if [ -z "$BASE" ]; then
  if [ "$IN_CI" -eq 1 ]; then
    echo "gtt-check-stack: cannot determine — base ref not available ($WANTED); fetch full history." >&2
    echo "  Without it a removed freeze marker cannot be told from a project that was never frozen." >&2
    echo "  Check out with full history (fetch-depth: 0) or pass the base ref as the argument." >&2
    exit 2
  fi
  echo "gtt-check-stack: NOTE - base ref not available ($WANTED): the freeze-marker check did NOT run." >&2
  echo "                  A removed marker cannot be told from a project that was never frozen." >&2
fi

# --- the freeze marker is never removed and its history is never rewritten ---
# Looked at before the "not frozen yet" exit below on purpose: a tree whose marker
# was deleted looks exactly like a project that was never frozen.
if [ -n "$BASE" ] && git cat-file -e "$BASE:$MARKER" 2>/dev/null; then
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

if [ -z "$BASE" ]; then
  echo "gtt-check-stack: cannot resolve base ref ($WANTED)" >&2
  exit 2
fi

if ! CHANGED="$(git diff --name-only "$BASE"...HEAD 2>/dev/null)"; then
  echo "gtt-check-stack: cannot determine — no merge base between $BASE and HEAD; fetch full history." >&2
  exit 2
fi

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
