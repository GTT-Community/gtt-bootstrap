#!/usr/bin/env bash
# GTT - append the ADR-005 pre-ratification evidence entry to .gtt/docs/evidence.md
#
# Human execution required. Prepared by an agent; never run by one.
# Source of the text: gtt-domain/proposals/PROPOSAL-evidence-entry-adr-005.md
#
# Append-only: it adds ONE entry at the end of .gtt/docs/evidence.md (existing text is never
# rewritten), stamps the entry's timestamp, refuses to add it twice, re-registers the derived
# index (gtt-index.sh) and restores the file if that fails. It does not run, ratify or touch
# ADR-005 or anything else. Run it BEFORE the ADR-005 promotion script: the entry states that
# ADR-005 is not yet ratified.
#
# Usage (from the project root):
#   bash gtt-domain/proposals/apply-evidence-adr-005.sh

set -euo pipefail

FILE=".gtt/docs/evidence.md"
TITLE="ADR-005 package (Multi-ADE, Initial Design Questionnaire): pre-ratification checks"
die() { echo "apply-evidence-adr-005: $*" >&2; exit 1; }

[ -f "$FILE" ] && [ -f .gtt/scripts/gtt-index.sh ] || die "run from the project root."
if grep -qF "$TITLE" "$FILE"; then die "this entry is already in $FILE - nothing to do."; fi
if ls gtt-domain/adr/ADR-005*.md >/dev/null 2>&1; then
  die "ADR-005 is already ratified; this entry describes the state before it. Ask for a post-promotion entry instead."
fi

TS="$(date +%Y-%m-%dT%H:%M)"
BACKUP="$(mktemp)"
cp -p "$FILE" "$BACKUP"
cp -p .gtt/index/artifacts.json "$BACKUP.a"
cp -p .gtt/index/technical-index.json "$BACKUP.t"

echo "Will append to $FILE an entry headed:"
echo "  ## Entry $TS - $TITLE"
printf "Type 'append' to proceed (anything else aborts): "
read -r ANSWER || ANSWER=""
[ "$ANSWER" = "append" ] || { echo "aborted - nothing was written."; exit 1; }

restore() {
  cp -p "$BACKUP" "$FILE"
  cp -p "$BACKUP.a" .gtt/index/artifacts.json
  cp -p "$BACKUP.t" .gtt/index/technical-index.json
  echo "apply-evidence-adr-005: failed - $FILE and the index were restored." >&2
  exit 1
}

sed "s|^## Entry <YYYY-MM-DDTHH:MM> |## Entry $TS |" >> "$FILE" <<'EOF_ENTRY'

---

## Entry <YYYY-MM-DDTHH:MM> — ADR-005 package (Multi-ADE, Initial Design Questionnaire): pre-ratification checks

**State:** branch `main`, HEAD `5ef21f6`; working tree has uncommitted changes (`gtt-domain/session.md` modified; untracked package files under `gtt-domain/proposals/`, `.gtt/scaffold/templates/`, the task file). Project frozen. ADR-005 is **not ratified** and `apply-ADR-005-bootstrap-integration-contracts.sh` has **not been executed by anyone**. Platform: Windows 11, Git Bash, Python 3.13. Nothing below is evidence about the promoted tree.

### 1. What was run

| Command | Result | Type |
|---|---|---|
| `python gtt-domain/proposals/adr-005-package/rehearse-multi-ade.py --project .` | `103/103 checks held` (exit 0). Runs on a **temporary copy** of the project overlaid with the staged package: registry, init, re-run, status/inspect/resume, validate failures, primary, update, clean/export, migration, record, questionnaire, Core neutrality, `gtt-index.sh` + `gtt-validate.sh` (no FAIL) | RUNTIME VERIFIED (of the staged code in a copy, not of the repository) |
| `bash -n` on `apply-ADR-005-bootstrap-integration-contracts.sh` and `apply-session-adapters.sh` | exit 0 for both (syntax only; neither was run) | STATIC VERIFIED |
| `sha256sum` of each of the 20 MOD/L0 targets vs the hash table embedded in the promotion script | 20 of 20 identical | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-check-markdown.sh` | `gtt-check-markdown: OK` | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-validate.sh` (baseline, before the package, real repo) | PASS except `gtt-check-integrity.sh` FAIL: unregistered artifacts (questionnaire, staged drafts) + 2 pre-existing `readme-gtt.es.md` anchor WARNs; adapter check `SKIPPED` (catalog) | RUNTIME VERIFIED |
| `git status --short` after the package was built | only `gtt-domain/proposals/**` (new/edited), plus `.gtt/scaffold/templates/`, the task file and `__pycache__` untracked and `gtt-domain/session.md` modified — all present before the package. No governed file (`context/`, `adr/`, `.frozen`, `backlog.md`, `change-request.md`, `AGENTS.md`, hooks, settings) changed | RUNTIME VERIFIED |
| Diff of the questionnaire ignoring `{=html}` fences and blank lines, before vs. staged | empty (53 answer slots normalised to `<!-- ADE populates this section -->`) | RUNTIME VERIFIED |

### 2. What was not verified

| Claim | Status | Type |
|---|---|---|
| The promotion script's behaviour (prompt, backup, rollback, stamping, post-validation) | never executed; only `bash -n`, its hash table and its `sed` expressions were checked in isolation | NO EVIDENCE |
| Behaviour on Linux or macOS | not run | NO EVIDENCE |
| Codex, GitHub Copilot and Kiro runtimes | not exercised; `enforcement: ci-gate` restates `.gtt/docs/docs.md` | DOCUMENTED ONLY |
| An ADE following the questionnaire's Operating Contract | instruction plane only; no script can prove it | NO EVIDENCE |
| `gtt-check-stack.sh` against `origin/main` on the promoted tree | not determinable in the temporary copy (`CANNOT-DETERMINE`) | NO EVIDENCE |
| Claude Code hooks against the promoted tree | untouched by the package; not re-run | NO EVIDENCE |

No FAIL was hidden: the only non-PASS lines are the baseline `gtt-check-integrity.sh` (expected, resolved by `gtt-index.sh` in the rehearsal) and the catalog `SKIPPED` adapter check.
EOF_ENTRY

bash .gtt/scripts/gtt-index.sh || restore
rm -f "$BACKUP" "$BACKUP.a" "$BACKUP.t"
echo
echo "Entry appended to $FILE and the index regenerated."
echo "Next: review with 'git diff .gtt/docs/evidence.md', then run the ADR-005 promotion script yourself:"
echo "  bash gtt-domain/proposals/apply-ADR-005-bootstrap-integration-contracts.sh"
