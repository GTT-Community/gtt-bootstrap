#!/usr/bin/env bash
# GTT - PROMOTION SCRIPT (human execution required)
#
# ADR      : ADR-006 - Provenance, gaps (OPEN/BLOCKING), source manifest and working agreements
#            (draft: gtt-domain/proposals/ADR-DRAFT-provenance-gaps-sources-agreements.md)
#
# Status: Draft - not a decision. Prepared by an agent; NEVER run by one.
#
# RUNNING THIS SCRIPT IS THE RATIFICATION OF ADR-006. It writes the ADR as Accepted, replaces
# five governed L0 files (gtt-domain/context/), and places the machinery, instruction and
# documentation files the decision needs. Read the proposal, the ADR draft and the diffs it
# offers before you type 'ratify'. Generating this package was never approval of it.
#
# What it does, in order:
#   1. Refuses to start unless every file it will replace is byte-identical to the file the
#      drafts were prepared against (sha256), and every file it will create does not exist.
#   2. Shows the summary, and on request the ADR text and the exact diff of any file.
#   3. Asks for an explicit 'ratify' (anything else aborts and writes nothing), then re-checks.
#   4. Applies everything in one run with a backup; on ANY failure it restores every file.
#   5. Appends the completion record, registers the new artifacts (gtt-index.sh), runs
#      gtt-validate.sh and restores everything if it introduces a FAIL it did not start with.
#
# It never runs an ADE, never touches gtt-domain/.frozen, backlog.md, change-request.md,
# SOURCE-BRIEF.*, hooks or settings, and never deletes anything of yours.
#
# Usage (from the project root):
#   bash gtt-domain/proposals/apply-ADR-006-bootstrap-integration-contracts.sh

set -eEuo pipefail

SLUG="provenance-gaps-sources-agreements"
SCRIPT_NAME="apply-ADR-006-${SLUG}.sh"
PROPOSALS="gtt-domain/proposals"
ADR_DRAFT="${PROPOSALS}/ADR-DRAFT-${SLUG}.md"
COMPLETION=".gtt/docs/gtt-completion.md"

die() { echo "apply-ADR-006: $*" >&2; exit 1; }

# ---------------------------------------------------------------- preconditions
[ -f .gtt/scaffold/manifest.yaml ] && [ -f gtt-domain/backlog.md ] \
  || die "run this from the project root (.gtt/scaffold/manifest.yaml not found)."
ls gtt-domain/adr/ADR-004*.md >/dev/null 2>&1 \
  || die "ADR-004 not found: this package builds on the .gtt/ + gtt-domain/ layout."
ls gtt-domain/adr/ADR-005*.md >/dev/null 2>&1 \
  || die "ADR-005 is not ratified: this package builds on the Multi-ADE / questionnaire contracts."
if ls gtt-domain/adr/ADR-006*.md >/dev/null 2>&1; then
  die "an ADR-006 already exists under gtt-domain/adr/ - nothing to do."
fi
[ -f "$ADR_DRAFT" ] || die "the ADR draft is missing: $ADR_DRAFT"

if command -v sha256sum >/dev/null 2>&1; then
  sha() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
  sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
  die "neither sha256sum nor shasum is available."
fi

TODAY="$(date -u +%Y-%m-%d)"
WHO="$(git config user.name 2>/dev/null || true)"
WHO="${WHO:-${USER:-${USERNAME:-unknown}}}"
WHO="$(printf '%s' "$WHO" | tr -d '|&\134')"
APPROVED_BY="Solution Designer (${WHO}) - ratified by executing ${SCRIPT_NAME} on ${TODAY}"

# --------------------------------------------------------------------- the plan
# KIND | target | staged source | sha256 of the file the draft was prepared against
#   MOD  replace an existing file (staged copy is the complete new text)
#   L0   replace a governed context file (dates are stamped at ratification)
#   NEW  create a file that must not exist yet
#   ADR  create the ADR (Status/Date/Approved-by stamped at ratification)
KINDS=(); TARGETS=(); SOURCES=(); PRES=()
while IFS='|' read -r kind target source pre; do
  [ -z "$kind" ] && continue
  KINDS+=("$kind"); TARGETS+=("$target"); SOURCES+=("$source"); PRES+=("$pre")
done <<'ITEMS'
MOD|.gtt/scripts/gtt-query.sh|gtt-domain/proposals/adr-006-package/tree/.gtt/scripts/gtt-query.sh.staged|d1bd002feb6cb65c0160797085e1581830a4d106c8cb1f38d01dded59b126b4c
MOD|.gtt/scripts/gtt-freeze.sh|gtt-domain/proposals/adr-006-package/tree/.gtt/scripts/gtt-freeze.sh.staged|d1ca52c9fdb3b5180efebc570db7123077221c39a87c9626e0dc326b9ac0441c
MOD|.gtt/scripts/gtt-validate.sh|gtt-domain/proposals/adr-006-package/tree/.gtt/scripts/gtt-validate.sh.staged|a599622ddbf7758ae42ee514e8d7d4ec7996344a1fda53a1b2ac51b596ae211e
MOD|.gtt/scripts/gtt-status.sh|gtt-domain/proposals/adr-006-package/tree/.gtt/scripts/gtt-status.sh.staged|9411b968747a06b1bb342868ec0c992058521a77c5fa635095c8fcb8bc3a5c61
MOD|.gtt/scaffold/manifest.yaml|gtt-domain/proposals/adr-006-package/tree/.gtt/scaffold/manifest.yaml.staged|da0713a49827ffabfc79159a13c623e3a5d9082980be3fd0f768fa754f248f63
MOD|AGENTS.md|gtt-domain/proposals/adr-006-package/tree/AGENTS.md.staged|a1e3fb644a9f0b460debe66a1b2227471c388680a15c789e67ede1b7a1ff16c2
MOD|.claude/skills/gtt-bootstrap/SKILL.md|gtt-domain/proposals/adr-006-package/tree/.claude/skills/gtt-bootstrap/SKILL.md.staged|baac500347e7a45ce40714f8d417b9f987247e2dc975d22bd87ec6dee0a33f27
MOD|.gtt/docs/docs.md|gtt-domain/proposals/adr-006-package/tree/.gtt/docs/docs.md.staged|9c259b82b5ea405f8298e8b467ee25bcc3e5c4be3d13f915d1b8e298f0909d94
MOD|.gtt/docs/index.md|gtt-domain/proposals/adr-006-package/tree/.gtt/docs/index.md.staged|e0b19c9a7e9416f36ff9e250ed8bdf45d4272293a16a7aed8185889d77640795
NEW|.gtt/scripts/gtt_provenance.py|gtt-domain/proposals/adr-006-package/tree/.gtt/scripts/gtt_provenance.py.staged|
NEW|.gtt/scripts/gtt-check-provenance.sh|gtt-domain/proposals/adr-006-package/tree/.gtt/scripts/gtt-check-provenance.sh.staged|
NEW|.gtt/scaffold/templates/gtt-sources-manifest.md|gtt-domain/proposals/adr-006-package/tree/.gtt/scaffold/templates/gtt-sources-manifest.md.staged|
NEW|.gtt/scaffold/templates/gtt-working-agreements.md|gtt-domain/proposals/adr-006-package/tree/.gtt/scaffold/templates/gtt-working-agreements.md.staged|
L0|gtt-domain/context/stack.md|gtt-domain/proposals/context-stack-adr-006.md|48ed60e0b5798e76657a0d2ef275d144d4251394790b1cb96ca42f894a4fac66
L0|gtt-domain/context/architecture.md|gtt-domain/proposals/context-architecture-adr-006.md|811b38e950841868920e4fb18fbd71feaf7d4345d04ccde8a1354682b14e20d0
L0|gtt-domain/context/glossary.md|gtt-domain/proposals/context-glossary-adr-006.md|70d2e102649d92cb4d6d527a52f5c9436fc31587fc955b8d8c9f9cdf1b6d7066
L0|gtt-domain/context/constraints.md|gtt-domain/proposals/context-constraints-adr-006.md|00663a7463381b067c3afff0c1c93901d58aae7c9a5b0ffe17dff53fa09eb41e
L0|gtt-domain/context/principles.md|gtt-domain/proposals/context-principles-adr-006.md|85ce27a01ffb37058956b1419cf83c1821c8cb01224ad3edda712e4ae7d3b7eb
ADR|gtt-domain/adr/ADR-006-provenance-gaps-sources-agreements.md|gtt-domain/proposals/ADR-DRAFT-provenance-gaps-sources-agreements.md|
ITEMS

verify() {
  local i bad=0 src
  for i in "${!TARGETS[@]}"; do
    src="${SOURCES[$i]}"
    if [ ! -f "$src" ]; then echo "  MISSING STAGED FILE: $src" >&2; bad=1; continue; fi
    case "${KINDS[$i]}" in
      MOD|L0)
        if [ ! -f "${TARGETS[$i]}" ]; then
          echo "  MISSING (expected to exist): ${TARGETS[$i]}" >&2; bad=1
        elif [ "$(sha "${TARGETS[$i]}")" != "${PRES[$i]}" ]; then
          echo "  CHANGED SINCE THE DRAFTS WERE PREPARED: ${TARGETS[$i]}" >&2; bad=1
        fi ;;
      NEW|ADR)
        if [ -e "${TARGETS[$i]}" ]; then
          echo "  CONFLICT (exists; never overwritten): ${TARGETS[$i]}" >&2; bad=1
        fi ;;
    esac
  done
  return "$bad"
}

# The final text of item $1, written to stdout.
render() {
  local src="${SOURCES[$1]}"
  case "${KINDS[$1]}" in
    L0)  sed -e "s|{{RATIFIED_ON}}|${TODAY}|g" "$src" ;;
    ADR) sed -e '/^> Draft staged by an agent/,/^> at the moment the Solution Designer ratifies/d' \
             -e "s|{{RATIFIED_ON}}|${TODAY}|g" \
             -e "s|{{RATIFIED_BY}}|${APPROVED_BY}|g" \
             -e 's|^- Status: Proposed$|- Status: Accepted|' "$src" ;;
    *)   cat "$src" ;;
  esac
}

show_diff() {
  local tmp; tmp="$(mktemp)"
  render "$1" > "$tmp"
  if [ -f "${TARGETS[$1]}" ]; then
    diff -u --label "a/${TARGETS[$1]}" --label "b/${TARGETS[$1]}" "${TARGETS[$1]}" "$tmp" || true
  else
    echo "(new file) ${TARGETS[$1]} - $(wc -l < "$tmp" | tr -d ' ') lines"
  fi
  rm -f "$tmp"
}

echo "=================================================================="
echo " GTT promotion: ADR-006 - provenance, gaps, sources, agreements"
echo " HUMAN EXECUTION REQUIRED - running this ratifies the ADR"
echo "=================================================================="
echo
echo "Checking the drafts against the current tree ..."
if ! verify; then
  echo >&2
  die "the tree no longer matches what the drafts were prepared against; nothing was written. Ask for the package to be re-staged."
fi
echo "  OK - every file to replace is unchanged, every file to create is absent."
echo
echo "Will change ${#TARGETS[@]} files:"
for i in "${!TARGETS[@]}"; do
  case "${KINDS[$i]}" in
    NEW|ADR) printf '  %-4s %s\n' "${KINDS[$i]}" "${TARGETS[$i]}" ;;
    *)
      tmp="$(mktemp)"; render "$i" > "$tmp"
      add="$(diff "${TARGETS[$i]}" "$tmp" | grep -c '^>' || true)"
      del="$(diff "${TARGETS[$i]}" "$tmp" | grep -c '^<' || true)"
      rm -f "$tmp"
      printf '  %-4s %-58s +%s -%s\n' "${KINDS[$i]}" "${TARGETS[$i]}" "$add" "$del" ;;
  esac
done
echo
echo "Also: appends a record to ${COMPLETION}, regenerates the derived index, runs gtt-validate.sh."
echo "The ADR will read:  Status: Accepted; Date: ${TODAY}; Approved by: ${APPROVED_BY}"
echo

while true; do
  printf "[adr] read the ADR   [l0] diffs of the L0 files   [all] every diff   [ratify] apply   (anything else aborts) > "
  read -r ANSWER || ANSWER=""
  case "$ANSWER" in
    adr) cat "$ADR_DRAFT" ;;
    l0)  for i in "${!TARGETS[@]}"; do if [ "${KINDS[$i]}" = L0 ]; then show_diff "$i"; fi; done ;;
    all) for i in "${!TARGETS[@]}"; do show_diff "$i"; done ;;
    ratify) break ;;
    *) echo "aborted - nothing was written."; exit 1 ;;
  esac
done

verify || die "the tree changed while you were reviewing; nothing was written."

# -------------------------------------------------------------------- apply
# Validation failures already present before this run are not this change's fault.
PRE_FAILS="$( (bash .gtt/scripts/gtt-validate.sh 2>&1 || true) | grep -E '^FAIL ' | grep -v 'gtt-check-integrity.sh' || true)"

BACKUP="$(mktemp -d)"
CREATED=(); BACKED=()

backup_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  mkdir -p "$BACKUP/$(dirname "$f")"
  cp -p "$f" "$BACKUP/$f"
  BACKED+=("$f")
}

rollback() {
  echo "apply-ADR-006: FAILURE - restoring every file it touched." >&2
  local f
  for f in "${CREATED[@]:-}"; do [ -n "$f" ] && rm -f "$f"; done
  for f in "${BACKED[@]:-}"; do [ -n "$f" ] && cp -p "$BACKUP/$f" "$f"; done
  echo "apply-ADR-006: restored. Nothing of ADR-006 is in effect. Backup kept at $BACKUP" >&2
  exit 1
}
trap 'rollback' ERR

for f in "${TARGETS[@]}"; do backup_file "$f"; done
backup_file "$COMPLETION"
backup_file .gtt/index/artifacts.json
backup_file .gtt/index/technical-index.json
backup_file gtt-domain/session.md

for i in "${!TARGETS[@]}"; do
  target="${TARGETS[$i]}"
  case "${KINDS[$i]}" in NEW|ADR) CREATED+=("$target") ;; esac
  mkdir -p "$(dirname "$target")"
  tmp="$(mktemp)"
  render "$i" > "$tmp"
  cp "$tmp" "$target"
  rm -f "$tmp"
  case "$target" in
    *.sh) chmod +x "$target" 2>/dev/null || true ;;
    *) case "${KINDS[$i]}" in NEW|ADR) chmod 644 "$target" 2>/dev/null || true ;; esac ;;
  esac
  echo "  wrote ${target}"
done

{
  echo
  echo "---"
  echo
  echo "## Provenance, gaps, sources and working agreements - $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo '```text'
  echo "GTT Bootstrap contracts applied (ADR-006)"
  echo
  echo "Decided:"
  echo "- Canonical provenance tags in governed context; [PROPUESTA] never inside it"
  echo "- Gap register in stack.md (section 8): BLOCKING refuses freeze; OPEN is scoped, visible, crosses freeze and authorises nothing"
  echo "- Source manifest gtt-domain/context/sources.md (domain, optional): authority, unambiguous precedence; SOURCE-BRIEF is evidence after freeze"
  echo "- Working agreements (team file, local user file) below governed context, outside Session Memory"
  echo "- One gate: gtt-check-provenance.sh (tags, gaps, sources, preferences); wired into validate, freeze, status and query --governance"
  echo
  echo "Created: .gtt/scripts/gtt_provenance.py gtt-check-provenance.sh; templates gtt-sources-manifest.md gtt-working-agreements.md; gtt-domain/adr/ADR-006-${SLUG}.md"
  echo "Replaced: gtt-domain/context/{stack,architecture,glossary,constraints,principles}.md; AGENTS.md; manifest.yaml; gtt-validate.sh gtt-status.sh gtt-query.sh gtt-freeze.sh;"
  echo "          the gtt-bootstrap skill; docs.md; index.md"
  echo "Unchanged: freeze regime, GTTGuard, identity/index, Session Memory and adapters, Multi-ADE (ADR-005), backlog.md, READMEs"
  echo
  echo "ADR: ADR-006 ratified by executing ${SCRIPT_NAME} on ${TODAY} (L0 text changed only through it)"
  echo "Verification: static + rehearsal in a disposable copy only (Windows / Git Bash / Python 3.13). NOT run on Linux or macOS, on an installed project,"
  echo "              or with an ADE following the new bootstrap instructions. The gate is lexical/structural: it cannot judge whether a [FUENTE] supports a claim."
  echo "Human action required: review 'git status', commit; add a post-promotion entry to .gtt/docs/evidence.md; delete the staged package (see the closing message)"
  echo '```'
} >> "$COMPLETION"

trap - ERR
bash .gtt/scripts/gtt-index.sh || rollback
POST_OUT="$( (bash .gtt/scripts/gtt-validate.sh 2>&1 || true) )"
NEW_FAILS=""
while IFS= read -r line; do
  [ -z "$line" ] && continue
  case "$line" in FAIL\ *) ;; *) continue ;; esac
  if [ -n "$PRE_FAILS" ] && printf '%s\n' "$PRE_FAILS" | grep -qxF "$line"; then continue; fi
  NEW_FAILS="${NEW_FAILS}${line}"$'\n'
done <<< "$POST_OUT"
if [ -n "$NEW_FAILS" ]; then
  printf '%s\n' "$POST_OUT" >&2
  echo "apply-ADR-006: gtt-validate.sh now FAILS where it did not before:" >&2
  printf '%s' "$NEW_FAILS" >&2
  rollback
fi
printf '%s\n' "$POST_OUT" | grep -E '^(PASS|SKIPPED|CANNOT-DETERMINE|FAIL|gtt-validate)' || true
bash .gtt/scripts/gtt-status.sh >/dev/null || true

cat <<MSG

==================================================================
 ADR-006 ratified and applied.   ($(date -u +%Y-%m-%dT%H:%M:%SZ))
==================================================================
 ADR:        gtt-domain/adr/ADR-006-${SLUG}.md   (Status: Accepted)
 Backup:     ${BACKUP}   (safe to delete once you are satisfied)

 Validate it yourself (nothing below writes to the project):
   bash .gtt/scripts/gtt-validate.sh
   bash .gtt/scripts/gtt-check-provenance.sh
   python gtt-domain/proposals/adr-006-package/rehearse-provenance.py --catalog .
   bash .gtt/scripts/gtt-query.sh --governance open ; bash .gtt/scripts/gtt-query.sh --governance sources
   bash .gtt/scripts/gtt-status.sh   (see the Evidence / Governance section)
   git status ; git diff --stat

 Adopting it in a project is optional: bash .gtt/scripts/gtt-template.sh materialize source-manifest --apply
 (moved to gtt-domain/context/sources.md before freeze) and materialize working-agreements --apply.

 Staged files you can now delete (this script did not delete them; then run
 .gtt/scripts/gtt-reconcile.sh - dry run first - to retire their identities):
   ${ADR_DRAFT}
   ${PROPOSALS}/context-{stack,architecture,glossary,constraints,principles}-adr-006.md
   ${PROPOSALS}/adr-006-package/
   ${PROPOSALS}/${SCRIPT_NAME}

 Still yours to do: a post-promotion entry in .gtt/docs/evidence.md; the README/EN-ES mentions of these
 capabilities were deliberately not touched. The agent did not run this script and has not promoted anything on its own.
MSG
