#!/usr/bin/env bash
# GTT - PROMOTION SCRIPT (human execution required)
#
# Proposal : gtt-domain/proposals/PROPOSAL-multi-ade-overlays-primary-ade.md
# ADR      : ADR-005 - Bootstrap integration contracts: Multi-ADE with one Primary ADE,
#            and the Initial Design Questionnaire
#            (draft: gtt-domain/proposals/ADR-DRAFT-bootstrap-integration-contracts.md)
#
# Status: Draft - not a decision. Prepared by an agent; NEVER run by one.
#
# RUNNING THIS SCRIPT IS THE RATIFICATION OF ADR-005. It writes the ADR as Accepted, replaces
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
#   bash gtt-domain/proposals/apply-ADR-005-bootstrap-integration-contracts.sh

set -eEuo pipefail

SLUG="bootstrap-integration-contracts"
SCRIPT_NAME="apply-ADR-005-${SLUG}.sh"
PROPOSALS="gtt-domain/proposals"
ADR_DRAFT="${PROPOSALS}/ADR-DRAFT-${SLUG}.md"
COMPLETION=".gtt/docs/gtt-completion.md"

die() { echo "apply-ADR-005: $*" >&2; exit 1; }

# ---------------------------------------------------------------- preconditions
[ -f .gtt/scaffold/manifest.yaml ] && [ -f gtt-domain/backlog.md ] \
  || die "run this from the project root (.gtt/scaffold/manifest.yaml not found)."
ls gtt-domain/adr/ADR-004*.md >/dev/null 2>&1 \
  || die "ADR-004 not found: this package builds on the .gtt/ + gtt-domain/ layout."
if ls gtt-domain/adr/ADR-005*.md >/dev/null 2>&1; then
  die "an ADR-005 already exists under gtt-domain/adr/ - nothing to do."
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
MOD|.gtt/scaffold/manifest.yaml|gtt-domain/proposals/adr-005-package/tree/.gtt/scaffold/manifest.yaml.staged|9d59969947e86c8781cb63b2c714259ab038362b9265d267514e54a6b756d541
MOD|.gtt/scripts/gtt-check-adapter.sh|gtt-domain/proposals/adr-005-package/tree/.gtt/scripts/gtt-check-adapter.sh.staged|7f1bba5f632e97d5d62e9e114759e664547be4331b750acbca0b22566c604e1a
MOD|.gtt/scripts/gtt-validate.sh|gtt-domain/proposals/adr-005-package/tree/.gtt/scripts/gtt-validate.sh.staged|c8b2e2af03a1f98ebaec69b9d4b46716cf12e8ca5c07ef00c866fc176654d63a
MOD|.gtt/scripts/gtt-status.sh|gtt-domain/proposals/adr-005-package/tree/.gtt/scripts/gtt-status.sh.staged|d873c03bbea5b28dea02d878370ce1e914ede8348cc3736ed805a577ec7d27a4
MOD|AGENTS.md|gtt-domain/proposals/adr-005-package/tree/AGENTS.md.staged|6a1f61dbfe9d48b65feb9c68f03009faa2c99b9f5eb937dca27c41993be7c248
MOD|.claude/skills/gtt-bootstrap/SKILL.md|gtt-domain/proposals/adr-005-package/tree/.claude/skills/gtt-bootstrap/SKILL.md.staged|a61a3eda8b27d2588315a1e645f9540852d68107eca0a1223c829da05e476a25
MOD|readme-gtt.md|gtt-domain/proposals/adr-005-package/tree/readme-gtt.md.staged|669068b41e6015151c2781717becb95b12a1937df7867d5ee6eeeb8fcef15b39
MOD|readme-gtt.es.md|gtt-domain/proposals/adr-005-package/tree/readme-gtt.es.md.staged|02852466ba15bb4c4e3755dfe10f40a284c549ceda66221adbf53c188dbc4be2
MOD|.gtt/docs/installation.md|gtt-domain/proposals/adr-005-package/tree/.gtt/docs/installation.md.staged|2dad7e558530aaa9a8d4960df0baaeb42b2082c95c9d785e6e61828987c638c3
MOD|.gtt/docs/installation.es.md|gtt-domain/proposals/adr-005-package/tree/.gtt/docs/installation.es.md.staged|25191c26e273bb0f2e50413a0e1b6cd722639391c5e24c3c788c14996ff42d4e
MOD|.gtt/docs/usage.md|gtt-domain/proposals/adr-005-package/tree/.gtt/docs/usage.md.staged|2c20671436ff5c6c54f8dcb0448062e40c1346006a6c78c0fae3d68eec352a80
MOD|.gtt/docs/usage.es.md|gtt-domain/proposals/adr-005-package/tree/.gtt/docs/usage.es.md.staged|abde5712fdcb6fd8a6ffedb9ea4326d1025680e26d6b13717d510c0d51b020f2
MOD|.gtt/docs/docs.md|gtt-domain/proposals/adr-005-package/tree/.gtt/docs/docs.md.staged|19e8ea31d352b3789e5c10010afcd9b324513bd1411fa820104d510eb0d38b68
MOD|.gtt/docs/index.md|gtt-domain/proposals/adr-005-package/tree/.gtt/docs/index.md.staged|7546ca8fcdb59f48f81e8ddaceec2d02ddc26ae188d0e3fa7dcf10f835869f25
MOD|.gtt/scaffold/templates/gtt-initial-design-questionnaire.md|gtt-domain/proposals/adr-005-package/tree/.gtt/scaffold/templates/gtt-initial-design-questionnaire.md.staged|4f2e0e8afa03e20dd290f33e9186803ad73154c9dfee463c4ec562e46c391b20
NEW|.gtt/scripts/gtt-ade.sh|gtt-domain/proposals/adr-005-package/tree/.gtt/scripts/gtt-ade.sh.staged|
NEW|.gtt/scripts/gtt_ade.py|gtt-domain/proposals/adr-005-package/tree/.gtt/scripts/gtt_ade.py.staged|
NEW|.gtt/scripts/gtt_manifest.py|gtt-domain/proposals/adr-005-package/tree/.gtt/scripts/gtt_manifest.py.staged|
NEW|.gtt/scripts/gtt-template.sh|gtt-domain/proposals/adr-005-package/tree/.gtt/scripts/gtt-template.sh.staged|
NEW|.gtt/scripts/gtt_template.py|gtt-domain/proposals/adr-005-package/tree/.gtt/scripts/gtt_template.py.staged|
L0|gtt-domain/context/stack.md|gtt-domain/proposals/context-stack-adr-005.md|dc5681fe89e0fab03a21c99c0df53a10f0b401c3a5f693293639aaae47d2d3d1
L0|gtt-domain/context/architecture.md|gtt-domain/proposals/context-architecture-adr-005.md|e7424955345b99a9e08a4a391c4538721180e85d0c08c74f0f09a72b306cfcb5
L0|gtt-domain/context/glossary.md|gtt-domain/proposals/context-glossary-adr-005.md|1f00668d5631c154c279d01159c2edd519cfb0f478359aae9af92b917ea5b8a3
L0|gtt-domain/context/constraints.md|gtt-domain/proposals/context-constraints-adr-005.md|0a4c7fe1197722dce144cf3b09040de302062205e5d71307415910be820b7944
L0|gtt-domain/context/principles.md|gtt-domain/proposals/context-principles-adr-005.md|11234ee03559c9aa70696fb9fd6d64301713e00f0e76fdc75611bb8552895f99
ADR|gtt-domain/adr/ADR-005-bootstrap-integration-contracts.md|gtt-domain/proposals/ADR-DRAFT-bootstrap-integration-contracts.md|
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
echo " GTT promotion: ADR-005 - Multi-ADE + Initial Design Questionnaire"
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
  echo "apply-ADR-005: FAILURE - restoring every file it touched." >&2
  local f
  for f in "${CREATED[@]:-}"; do [ -n "$f" ] && rm -f "$f"; done
  for f in "${BACKED[@]:-}"; do [ -n "$f" ] && cp -p "$BACKUP/$f" "$f"; done
  echo "apply-ADR-005: restored. Nothing of ADR-005 is in effect. Backup kept at $BACKUP" >&2
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
  echo "## Bootstrap integration contracts (Multi-ADE and Initial Design Questionnaire) - $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo '```text'
  echo "GTT Bootstrap contracts applied (ADR-005)"
  echo
  echo "Decided:"
  echo "- Multi-ADE: one overlay per participating ADE, exactly one Primary ADE (a workflow identifier; no authority)"
  echo "- Detection is not participation; state in .gtt/ade.json (written only by gtt-ade.sh); registry in the manifest overlays:"
  echo "- The Initial Design Questionnaire is a Bootstrap-owned template (manifest templates:, gtt-template.sh); source material, not governed architecture"
  echo
  echo "Created: .gtt/scripts/gtt-ade.sh gtt_ade.py gtt_manifest.py gtt-template.sh gtt_template.py; gtt-domain/adr/ADR-005-${SLUG}.md"
  echo "Replaced: gtt-domain/context/{stack,architecture,glossary,constraints,principles}.md; AGENTS.md; manifest.yaml; gtt-check-adapter.sh gtt-validate.sh gtt-status.sh;"
  echo "          the gtt-bootstrap skill; the questionnaire (answer-slot syntax only); both READMEs; installation, usage (EN/ES), docs, index"
  echo "Unchanged: freeze regime, GTTGuard, identity/index contracts, Session Memory adapters, ADR-001/003/004, backlog.md"
  echo
  echo "ADR: ADR-005 ratified by executing ${SCRIPT_NAME} on ${TODAY} (L0 text changed only through it)"
  echo "Verification: static + rehearsal in a disposable copy only (Windows / Git Bash / Python 3.13). NOT run on Linux or macOS."
  echo "              No Codex, Copilot or Kiro runtime was exercised; 'enforcement' values restate the compatibility matrix (documented, not runtime-verified)."
  echo "Human action required: review 'git status', commit; decide the staged backlog proposal (PROPOSAL-backlog-epic-multi-ade-questionnaire.md);"
  echo "                       delete the staged package (see the closing message)"
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
  echo "apply-ADR-005: gtt-validate.sh now FAILS where it did not before:" >&2
  printf '%s' "$NEW_FAILS" >&2
  rollback
fi
printf '%s\n' "$POST_OUT" | grep -E '^(PASS|SKIPPED|CANNOT-DETERMINE|FAIL|gtt-validate)' || true
bash .gtt/scripts/gtt-status.sh >/dev/null || true

cat <<MSG

==================================================================
 ADR-005 ratified and applied.   ($(date -u +%Y-%m-%dT%H:%M:%SZ))
==================================================================
 ADR:        gtt-domain/adr/ADR-005-${SLUG}.md   (Status: Accepted)
 Backup:     ${BACKUP}   (safe to delete once you are satisfied)

 Validate it yourself (nothing below writes to the project):
   bash .gtt/scripts/gtt-validate.sh
   python gtt-domain/proposals/adr-005-package/rehearse-multi-ade.py --catalog .
   bash .gtt/scripts/gtt-ade.sh list ; bash .gtt/scripts/gtt-ade.sh detect ; bash .gtt/scripts/gtt-ade.sh state
   bash .gtt/scripts/gtt-template.sh list ; bash .gtt/scripts/gtt-template.sh show initial-design-questionnaire
   git status ; git diff --stat

 Then: review, commit. This repository is the catalog: it has no .gtt/ade.json, so the adapter
 check stays SKIPPED here exactly as before; installed projects get it from 'gtt-ade.sh install|adopt'.

 Staged files you can now delete (this script did not delete them; then run
 .gtt/scripts/gtt-reconcile.sh - dry run first - to retire their identities):
   ${ADR_DRAFT}
   ${PROPOSALS}/context-{stack,architecture,glossary,constraints,principles}-adr-005.md
   ${PROPOSALS}/adr-005-package/
   ${PROPOSALS}/PROPOSAL-multi-ade-overlays-primary-ade.md   (once you have read it)
   ${PROPOSALS}/${SCRIPT_NAME}

 Still yours to do: decide the staged backlog proposal (PROPOSAL-backlog-epic-multi-ade-questionnaire.md,
 keep it until then); update .gtt/docs/evidence.md.
 The agent did not run this script and has not promoted anything on its own.
MSG
