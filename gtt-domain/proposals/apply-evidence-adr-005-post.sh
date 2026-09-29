#!/usr/bin/env bash
# GTT - append the ADR-005 POST-promotion evidence entry to .gtt/docs/evidence.md
#
# Human execution required. Prepared by an agent; never run by one.
# Append-only: adds ONE entry at the end of .gtt/docs/evidence.md (nothing existing is rewritten),
# stamps its timestamp, refuses to add it twice, re-registers the derived index and restores the
# file if that fails. Requires ADR-005 to be ratified already (the entry describes that state).
# The earlier pre-ratification entry is history and is not edited.
#
# Usage (from the project root, in an interactive terminal):
#   bash gtt-domain/proposals/apply-evidence-adr-005-post.sh

set -euo pipefail

FILE=".gtt/docs/evidence.md"
TITLE="ADR-005 promoted (Multi-ADE, Initial Design Questionnaire): post-ratification checks"
die() { echo "apply-evidence-adr-005-post: $*" >&2; exit 1; }

[ -f "$FILE" ] && [ -f .gtt/scripts/gtt-index.sh ] || die "run from the project root."
ls gtt-domain/adr/ADR-005*.md >/dev/null 2>&1 || die "ADR-005 is not ratified yet; this entry describes the promoted tree."
if grep -qF "$TITLE" "$FILE"; then die "this entry is already in $FILE - nothing to do."; fi

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
  echo "apply-evidence-adr-005-post: failed - $FILE and the index were restored." >&2
  exit 1
}

sed "s|^## Entry <YYYY-MM-DDTHH:MM> |## Entry $TS |" >> "$FILE" <<'EOF_ENTRY'

---

## Entry <YYYY-MM-DDTHH:MM> — ADR-005 promoted (Multi-ADE, Initial Design Questionnaire): post-ratification checks

**State:** branch `main`, HEAD `5ef21f6` (nothing committed since the earlier entry); working tree carries the promoted, uncommitted changes plus untracked files. ADR-005 `Status: Accepted`, ratified by the Solution Designer executing `apply-ADR-005-bootstrap-integration-contracts.sh` on 2026-09-29 (output of that run: 26 files written, `gtt-index` OK with 61 artifacts, `gtt-validate: OK`). This entry follows the pre-ratification entry above, which is history. Platform: Windows 11, Git Bash, Python 3.13.

### 1. What was run on the promoted tree

| Command | Result | Type |
|---|---|---|
| The promotion script's own post-validation (`gtt-validate.sh`), as printed by the run | `gtt-check-backlog` PASS; `gtt-check-adapter` SKIPPED (catalog, no `.gtt/ade.json`); `gtt-check-protection` PASS; `gtt-check-stack` PASS; `gtt-check-markdown` PASS; `gtt-check-integrity` PASS; session-adapter checks PASS for claude, codex, copilot, kiro; `gtt-validate: OK` | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-validate.sh` (re-run afterwards) | identical: every line PASS or the one SKIPPED adapter check; `gtt-validate: OK` | RUNTIME VERIFIED |
| `python gtt-domain/proposals/adr-005-package/rehearse-multi-ade.py --catalog .` | `103/103 checks held` (temporary copy of the promoted tree; `gtt-check-stack` CANNOT-DETERMINE there, outside a checkout) | RUNTIME VERIFIED (engine, in a copy) |
| `bash .gtt/scripts/gtt-ade.sh state` | `ADE state: not configured (no .gtt/ade.json ...)` — expected: this repository is the catalog | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-template.sh list` | `initial-design-questionnaire  ok  .gtt/scaffold/templates/gtt-initial-design-questionnaire.md` | RUNTIME VERIFIED |
| ADR-005 header | `Status: Accepted`, `Date: 2026-09-29`, `Approved by: Solution Designer (mgriott) - ratified by executing apply-ADR-005-...sh` | RUNTIME VERIFIED |
| `git status --short` | modified: the 15 machinery/instruction/documentation files, the 5 L0 context files, `.gtt/docs/evidence.md` and `gtt-completion.md` (appends), the derived index and `session.md`; new: the 5 engine files, ADR-005, the questionnaire folder. `gtt-domain/.frozen`, `backlog.md`, `change-request.md`, `SOURCE-BRIEF.*`, hooks and settings not modified | RUNTIME VERIFIED |

### 2. Still not verified

| Claim | Status | Type |
|---|---|---|
| `gtt-ade.sh install/adopt/update/remove` against a real installed project (only temporary copies were used) | not run | NO EVIDENCE |
| Linux and macOS | not run | NO EVIDENCE |
| Codex, GitHub Copilot and Kiro runtimes; `enforcement: ci-gate` | restates the compatibility matrix | DOCUMENTED ONLY |
| An ADE following the questionnaire's Operating Contract | instruction plane only | NO EVIDENCE |
| `apply-session-adapters.sh` record step on a real install | rehearsed piecewise only; the script was never run | NO EVIDENCE |

The staged package files, the backlog proposal (`PROPOSAL-backlog-epic-multi-ade-questionnaire.md`) and the ADE state for this repository remain undecided; nothing here records them as done.
EOF_ENTRY

bash .gtt/scripts/gtt-index.sh || restore
rm -f "$BACKUP" "$BACKUP.a" "$BACKUP.t"
echo
echo "Post-promotion entry appended to $FILE and the index regenerated."
echo "Review with: git diff .gtt/docs/evidence.md"
