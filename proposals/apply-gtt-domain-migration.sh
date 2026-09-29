#!/usr/bin/env bash
# GTT - PROMOTION SCRIPT (human execution required)  -  ORCHESTRATOR
#
# Proposal : proposals/PROPOSAL-gtt-domain-and-dot-gtt-engine.md
# ADR      : ADR-004 (draft: proposals/ADR-DRAFT-gtt-domain-and-dot-gtt-engine.md)
# Status   : Draft - not a decision. Prepared by an agent; never run by one.
#            Running this script is YOUR decision; generating it is not approval.
#
# One governed operation, two distinct human acts, in this order:
#
#   1. MIGRATION (this script): move the scaffold to the ADR-004 layout
#        .gtt/        Engine: index protection scaffold scripts session-adapters + docs/
#        gtt-domain/  the governed domain: context adr proposals backlog.md
#                     change-request.md session.md .frozen
#      by moving files with `git mv`, rewriting every path reference and relative
#      link OUTSIDE governed context, replacing the protection hook, re-registering
#      artifact identity (same ids, new paths) and installing manifest layout v2.
#      Governed context (context/, adr/) is MOVED here; its text is NOT touched.
#
#   2. RATIFICATION (apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh, called by this script):
#      the gtt-adr promotion mechanism. It shows you the ADR and the exact diff of
#      every L0 file, and only on your 'yes' promotes ADR-004 (Status: Accepted) and
#      overwrites the L0 files from the staged full drafts (context-*-adr-004.md).
#      Answering 'no' there cancels the whole operation: this script then restores
#      the pre-migration state from its backup.
#
# It never freezes, commits, or pushes, and it preserves .frozen byte for byte (it ends
# up at gtt-domain/.frozen). It refuses to start unless the repository is in exactly the
# expected pre-migration state (or reports that it is already migrated and stops with
# exit 0 - idempotent). It takes a verified backup first; if ANY step or validation
# fails, or you interrupt it, it restores the backup and exits non-zero, so nothing is
# left half-migrated. No deterministic check that passed before may fail after.
#
# Usage (from the project root):
#   bash proposals/apply-gtt-domain-migration.sh

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1     # no __pycache__ from any check this run starts

# ---------------------------------------------------------------- arguments
for a in "$@"; do
  case "$a" in
    -h|--help) sed -n '2,38p' "$0"; exit 0 ;;
    *) echo "unknown argument '$a'" >&2; exit 2 ;;
  esac
done

# ------------------------------------------- run from a copy outside the tree
# This script and its package live in proposals/, which the migration moves.
# Re-exec from a temporary copy so nothing we are executing or reading moves.
ADR_FILES=(
  ADR-DRAFT-gtt-domain-and-dot-gtt-engine.md
  apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh
  context-architecture-adr-004.md
  context-constraints-adr-004.md
  context-glossary-adr-004.md
  context-principles-adr-004.md
  context-solution-vision-adr-004.md
  context-stack-adr-004.md
)
if [ -z "${GTT_DOMAIN_MIGRATION_STAGED:-}" ]; then
  [ -f gtt/scripts/gtt-validate.sh ] && [ -d .git ] \
    || { echo "run from the project root of the GTT checkout (pre-migration layout)" >&2; exit 2; }
  SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
  [ -d "$SRC_DIR/gtt-domain-migration" ] || { echo "package directory missing next to the script" >&2; exit 2; }
  for f in "${ADR_FILES[@]}"; do
    [ -f "$SRC_DIR/$f" ] || { echo "ADR-004 promotion package incomplete: $f is missing" >&2; exit 2; }
  done
  STAGE="$(mktemp -d)"
  cp -r "$SRC_DIR/gtt-domain-migration" "$STAGE/pkg"
  mkdir "$STAGE/adr"
  for f in "${ADR_FILES[@]}"; do cp "$SRC_DIR/$f" "$STAGE/adr/$f"; done
  cp "$0" "$STAGE/apply.sh"
  GTT_DOMAIN_MIGRATION_STAGED="$STAGE" exec bash "$STAGE/apply.sh" "$@"
fi
STAGE="$GTT_DOMAIN_MIGRATION_STAGED"
PKG="$STAGE/pkg"
ADRPKG="$STAGE/adr"

# ------------------------------------------------------------------ helpers
pick_python() {
  local c
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c '' >/dev/null 2>&1; then echo "$c"; return 0; fi
  done
  return 1
}
PY="$(pick_python)" || { echo "no working Python 3 on PATH" >&2; exit 2; }
MIGRATE=("$PY" "$PKG/migrate.py")

sha_lf() { tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1; }

pass_names() {  # <validate-output-file>: names of the checks that PASS, normalised
  grep -E '^PASS' "$1" | sed -E 's/[[:space:]]+\[.*$//; s/[[:space:]]+$//' | sort
}

# ---------------------------------------------------------------- preflight
echo "=================================================================="
echo " GTT promotion: .gtt/ + gtt-domain/ migration + ADR-004   (HUMAN EXECUTION REQUIRED)"
echo "=================================================================="

set +e
"${MIGRATE[@]}" preflight --pkg "$PKG"
RC=$?
set -e
if [ "$RC" -eq 3 ]; then echo "Nothing to do (already migrated). Exit 0."; exit 0; fi
[ "$RC" -eq 0 ] || { echo "Pre-migration state does not match. Nothing was changed." >&2; exit 1; }

# The L0 files must still be exactly what the ADR-004 drafts were prepared from,
# otherwise ratification would overwrite changes it never showed you. Before the
# migration they still sit at context/<name>; the ADR script names them gtt-domain/context/<name>.
STALE_L0=""
while IFS= read -r line; do
  line="${line#  \"}"; line="${line%\"}"
  IFS='|' read -r target staged want <<<"$line"
  current="${target#gtt-domain/}"
  [ -f "$current" ] || { STALE_L0="$STALE_L0  $current (missing)"$'\n'; continue; }
  [ "$(sha_lf "$current")" = "$want" ] || STALE_L0="$STALE_L0  $current"$'\n'
done < <(grep -E '^  "gtt-domain/context/' "$ADRPKG/apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh")
if [ -n "$STALE_L0" ]; then
  echo "Governed context changed since the ADR-004 drafts were prepared; re-stage them with gtt-adr:" >&2
  printf "%s" "$STALE_L0" >&2
  exit 1
fi

# Uncommitted work would be indistinguishable from migration output afterwards.
# Line endings alone do not count: with a different core.autocrlf than the one the
# files were checked out with, git reports every CRLF file as modified although the
# content is identical. Those are compared ignoring CR-at-EOL.
DIRTY=""
while IFS= read -r line; do
  st="${line:0:2}"
  path="${line:3}"
  case "$path" in
    proposals/*|session.md|gtt/index/*|TASK-*) continue ;;
  esac
  if [ "$st" != "??" ] && git diff --quiet --ignore-cr-at-eol -- "$path" 2>/dev/null \
     && git diff --cached --quiet -- "$path" 2>/dev/null; then
    continue
  fi
  DIRTY="$DIRTY$line"$'\n'
done < <(git status --porcelain --untracked-files=all)
if [ -n "$DIRTY" ]; then
  echo "Uncommitted changes outside the staged package - commit or stash them first:" >&2
  echo "$DIRTY" >&2
  exit 1
fi
git diff --cached --quiet || { echo "There are staged changes; commit or unstage them first." >&2; exit 1; }

echo
echo "Baseline: running gtt-validate.sh before touching anything ..."
BASELINE_OUT="$STAGE/baseline-validate.txt"
BASELINE_FILE="$STAGE/baseline.txt"
if ! bash gtt/scripts/gtt-validate.sh > "$BASELINE_OUT" 2>&1; then
  echo "The repository already fails gtt-validate.sh; fix that before migrating. Its output:" >&2
  echo "------------------------------------------------------------------" >&2
  cat "$BASELINE_OUT" >&2
  echo "------------------------------------------------------------------" >&2
  exit 1
fi
pass_names "$BASELINE_OUT" > "$BASELINE_FILE"
echo "  $(wc -l < "$BASELINE_FILE" | tr -d ' ') check(s) PASS at baseline; none may regress."

# ------------------------------------------------------------ human decision
while true; do
  echo
  echo "Type 'plan' to list every move/rewrite, 'view' to read the proposal's summary,"
  echo "'apply' to migrate (you will then be asked to ratify ADR-004), anything else to abort."
  printf "> "
  read -r ANSWER
  case "$ANSWER" in
    plan) "${MIGRATE[@]}" plan --pkg "$PKG" ;;
    view) sed -n '1,60p' proposals/PROPOSAL-gtt-domain-and-dot-gtt-engine.md ;;
    apply) break ;;
    *) echo "aborted - nothing was written."; exit 1 ;;
  esac
done

# ------------------------------------------------------------------- backup
BACKUP="$STAGE/backup.tar"
echo
echo "Backup: $BACKUP"
tar --exclude=./.git -cf "$BACKUP" .
tar -tf "$BACKUP" >/dev/null || { echo "backup unreadable - aborting before any change" >&2; exit 1; }
FROZEN_BEFORE="$(sha256sum .frozen | cut -d' ' -f1)"

rollback() {
  trap - ERR INT TERM HUP
  set +e
  echo >&2
  echo "FAILED, cancelled or interrupted - restoring the pre-migration state from the backup ..." >&2
  git reset -q 2>/dev/null
  find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} + 2>/dev/null
  tar -xf "$BACKUP"
  git reset -q 2>/dev/null
  if [ -f .frozen ] && [ "$(sha256sum .frozen | cut -d' ' -f1)" = "$FROZEN_BEFORE" ]; then
    echo "Restored. .frozen is identical to before. Nothing was migrated." >&2
  else
    echo "RESTORE INCOMPLETE - the backup is at $BACKUP; extract it manually." >&2
  fi
  exit 1
}
trap rollback ERR
# Ctrl-C, kill, or a closed terminal: an interrupted run is a failed run. (While a
# child such as the ratification prompt is running, the ERR trap above already covers
# the child dying; these cover the interruption reaching this script itself.)
trap rollback INT TERM HUP

# ---------------------------------------------- 1. migration (moves, rewrites)
echo
"${MIGRATE[@]}" apply --pkg "$PKG"

# ------------------------------- 2. ratification (the gtt-adr promotion script)
echo
echo "------------------------------------------------------------------"
echo " Ratification of ADR-004 (the migration above is not final until 'yes')"
echo "------------------------------------------------------------------"
bash "$ADRPKG/apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh"

# The ratification consumed the moved copy of the ADR draft, which the identity
# manifest still lists (it was registered while staged). Retire that identity with
# the official mechanism, or gtt-index.sh refuses to run ("manifest paths are
# missing on disk"). Nothing to reconcile = exit 0.
bash .gtt/scripts/gtt-reconcile.sh --apply --retire PROP-ADR-DRAFT-GTT-DOMAIN-AND-DOT-GTT-ENGINE

# Durable record (append-only completion log).
{
  echo
  echo "---"
  echo
  echo "## Layout migration to .gtt/ and gtt-domain/ — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo '```text'
  echo "GTT layout migration applied (layout version 2)"
  echo
  echo "Moved:"
  echo "- Engine to .gtt/: index protection scaffold scripts session-adapters (from gtt/), README.md, and GTT documentation to .gtt/docs/ (from docs/)"
  echo "- Governed domain to gtt-domain/: context adr proposals backlog.md change-request.md session.md .frozen"
  echo "Unchanged: AGENTS.md, readme-gtt*.md, SOURCE-BRIEF.*, .claude/ .kiro/ .copilot/"
  echo
  echo "ADR: ADR-004 ratified by executing apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh (L0 text changed only through it)"
  echo "Freeze: .frozen preserved byte-for-byte at gtt-domain/.frozen; gtt-freeze.sh was not run"
  echo "Human action required: review 'git status', commit, then delete the staged package in gtt-domain/proposals/ (see the ADR script's closing message and gtt-domain/proposals/gtt-domain-migration/CLEANUP.md)"
  echo '```'
} >> .gtt/docs/gtt-completion.md

# ----------------------------------------------- reconcile derived artifacts
echo
echo "Regenerating derived state ..."
bash .gtt/scripts/gtt-index.sh
bash .gtt/scripts/gtt-guard-sync.sh
bash .gtt/scripts/gtt-status.sh >/dev/null
bash .gtt/scripts/gtt-index.sh >/dev/null

# --------------------------------------------------------------- validation
echo
echo "Validating ..."
# A stack check that says "not frozen yet" would pass vacuously: it would mean the
# script no longer sees the freeze marker at its new location.
STACK_OUT="$STAGE/stack-check.txt"
bash .gtt/scripts/gtt-check-stack.sh > "$STACK_OUT" 2>&1 || { cat "$STACK_OUT" >&2; false; }
if grep -qi 'not frozen yet' "$STACK_OUT"; then
  echo "gtt-check-stack.sh does not see gtt-domain/.frozen (it reports 'not frozen yet')" >&2
  cat "$STACK_OUT" >&2
  false
fi
bash .gtt/scripts/gtt-check-integrity.sh
bash .gtt/scripts/gtt-check-protection.sh
bash .gtt/scripts/gtt-check-session-adapter.sh claude
AFTER_OUT="$STAGE/after-validate.txt"
AFTER_FILE="$STAGE/after.txt"
if ! bash .gtt/scripts/gtt-validate.sh > "$AFTER_OUT" 2>&1; then
  cat "$AFTER_OUT" >&2
  false
fi
cat "$AFTER_OUT"
pass_names "$AFTER_OUT" > "$AFTER_FILE"
LOST="$(comm -23 "$BASELINE_FILE" "$AFTER_FILE" || true)"
if [ -n "$LOST" ]; then
  echo "These checks PASSED before the migration and do not now:" >&2
  echo "$LOST" >&2
  false
fi
echo "  no check regressed ($(wc -l < "$AFTER_FILE" | tr -d ' ') PASS, was $(wc -l < "$BASELINE_FILE" | tr -d ' '))."

"${MIGRATE[@]}" verify --pkg "$PKG"
"${MIGRATE[@]}" oldrefs --pkg "$PKG"

[ "$(sha256sum gtt-domain/.frozen | cut -d' ' -f1)" = "$FROZEN_BEFORE" ] \
  || { echo "gtt-domain/.frozen differs from .frozen before the migration" >&2; false; }
[ -f gtt-domain/adr/ADR-004-gtt-domain-and-dot-gtt-engine.md ] \
  && grep -q '^- Status: Accepted' gtt-domain/adr/ADR-004-gtt-domain-and-dot-gtt-engine.md \
  || { echo "ADR-004 is not in gtt-domain/adr/ with Status: Accepted" >&2; false; }

# The protection hook is the one component whose logic changed: prove it still
# blocks governed paths after freeze and still leaves the project's own code alone.
hook() {  # hook <tool> <path> -> exit code of the PreToolUse hook
  printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "$1" "$2" \
    | "$PY" .claude/hooks/protect-l0.py >/dev/null 2>&1
  return $?
}
expect() {  # expect <want> <tool> <path>
  local got=0
  hook "$2" "$3" || got=$?
  [ "$got" -eq "$1" ] || { echo "protect-l0.py: $2 $3 -> $got, expected $1" >&2; false; }
}
expect 2 Write "$PWD/gtt-domain/context/stack.md"
expect 2 Edit  "$PWD/gtt-domain/adr/ADR-001-context-governance.md"
expect 2 Write "$PWD/gtt-domain/change-request.md"
expect 2 Write "$PWD/.claude/settings.json"
expect 0 Write "$PWD/gtt-domain/proposals/PROPOSAL-x.md"
expect 0 Write "$PWD/src/context/example.ts"
expect 0 Write "$PWD/.gtt/docs/usage.md"
echo "  protection hook: governed paths blocked, project code, .gtt/docs and gtt-domain/proposals/ untouched."

trap - ERR INT TERM HUP

echo
echo "=================================================================="
echo " Layout migrated, ADR-004 ratified, everything validated."
echo "=================================================================="
echo "Nothing was committed, pushed, or frozen; the freeze marker is unchanged (gtt-domain/.frozen)."
echo "Review:   git status && git diff --stat -M HEAD"
echo "Then commit it yourself. Afterwards delete the staged package in gtt-domain/proposals/"
echo "and retire its identities with gtt-reconcile.sh --retire: see"
echo "gtt-domain/proposals/gtt-domain-migration/CLEANUP.md."
echo "Backup kept at: $BACKUP"
