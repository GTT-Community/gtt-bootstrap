#!/usr/bin/env bash
# GTT - cleanup of the staged ADR-005 / ADR-006 promotion packages (human execution required)
#
# Prepared by an agent; never run by one. Both ADRs are ratified; the staged drafts, promotion
# scripts and rehearsal packages have served their purpose (they stay in git history).
#
# Removes ONLY these, nothing else:
#   gtt-domain/proposals/ADR-DRAFT-{bootstrap-integration-contracts,provenance-gaps-sources-agreements}.md
#   gtt-domain/proposals/context-*-adr-005.md  and  context-*-adr-006.md
#   gtt-domain/proposals/adr-005-package/  and  adr-006-package/
#   gtt-domain/proposals/apply-ADR-005-*.sh  and  apply-ADR-006-*.sh
#   gtt-domain/proposals/apply-evidence-adr-005.sh, PROPOSAL-evidence-entry-adr-005.md,
#   PROPOSAL-multi-ade-overlays-primary-ade.md
#   gtt-domain/proposals/apply-evidence-adr-005-post.sh   (only if its evidence entry is already in evidence.md)
#   .gtt/scripts/__pycache__/                              (untracked build artefact)
# KEPT: PROPOSAL-backlog-epic-multi-ade-questionnaire.md (undecided), apply-session-adapters.sh,
#   every older proposal, and everything outside gtt-domain/proposals/ (including the untracked
#   GTT-CDAD-CONVERGENCE-WORKPLAN.md and GTT-BOOTSTRAP-RECIPE.md, and gtt-domain/session.md).
#
# Then it retires the removed artifacts' identities (gtt-reconcile.sh --retire ... --apply),
# regenerates the derived index and runs gtt-validate.sh. On a validation failure it restores
# every removed file and the index. It does not commit.
#
# Usage (from the project root, interactive terminal):
#   bash gtt-domain/proposals/cleanup-adr-005-006.sh            # lists what it would do, then asks
#   Commit the ratified work FIRST if you want the package preserved as a commit of its own.

set -euo pipefail

P="gtt-domain/proposals"
die() { echo "cleanup-adr-005-006: $*" >&2; exit 1; }
[ -f .gtt/scaffold/manifest.yaml ] && [ -d "$P" ] || die "run from the project root."
ls gtt-domain/adr/ADR-005*.md gtt-domain/adr/ADR-006*.md >/dev/null 2>&1 || die "ADR-005 and ADR-006 must both be ratified first."

TARGETS=()
add() { local f; for f in "$@"; do [ -e "$f" ] && TARGETS+=("$f"); done; return 0; }
add "$P"/ADR-DRAFT-bootstrap-integration-contracts.md "$P"/ADR-DRAFT-provenance-gaps-sources-agreements.md
add "$P"/context-*-adr-005.md "$P"/context-*-adr-006.md
add "$P"/adr-005-package "$P"/adr-006-package
add "$P"/apply-ADR-005-*.sh "$P"/apply-ADR-006-*.sh
add "$P"/apply-evidence-adr-005.sh "$P"/PROPOSAL-evidence-entry-adr-005.md "$P"/PROPOSAL-multi-ade-overlays-primary-ade.md
if grep -qF "ADR-005 promoted (Multi-ADE, Initial Design Questionnaire): post-ratification checks" .gtt/docs/evidence.md; then
  add "$P"/apply-evidence-adr-005-post.sh
else
  echo "note: apply-evidence-adr-005-post.sh is KEPT - its evidence entry is not in evidence.md yet."
fi
[ -d .gtt/scripts/__pycache__ ] && TARGETS+=(.gtt/scripts/__pycache__)
[ "${#TARGETS[@]}" -gt 0 ] || die "nothing to clean."

echo "Will remove:"
printf '  %s\n' "${TARGETS[@]}"
echo "Kept: $P/PROPOSAL-backlog-epic-multi-ade-questionnaire.md, apply-session-adapters.sh, older proposals, everything outside proposals/."
printf "Type 'clean' to proceed (anything else aborts): "
read -r ANSWER || ANSWER=""
[ "$ANSWER" = "clean" ] || { echo "aborted - nothing was removed."; exit 1; }

BACKUP="$(mktemp -d)"
for t in "${TARGETS[@]}"; do
  mkdir -p "$BACKUP/$(dirname "$t")"
  cp -Rp "$t" "$BACKUP/$t"
done
cp -p .gtt/index/artifacts.json "$BACKUP/artifacts.json"
cp -p .gtt/index/technical-index.json "$BACKUP/technical-index.json"

# identities of the Markdown artifacts about to disappear
IDS="$(python - "${TARGETS[@]}" <<'PYEOF'
import json, sys
paths = set()
import os
for t in sys.argv[1:]:
    if os.path.isdir(t):
        for d, _, fs in os.walk(t):
            paths |= {os.path.join(d, f).replace("\\", "/") for f in fs if f.endswith(".md")}
    elif t.endswith(".md"):
        paths.add(t.replace("\\", "/"))
data = json.load(open(".gtt/index/artifacts.json", encoding="utf-8"))
for a in data["artifacts"]:
    if a["path"] in paths:
        print(a["id"])
PYEOF
)"

restore() {
  echo "cleanup-adr-005-006: FAILED - restoring everything." >&2
  for t in "${TARGETS[@]}"; do rm -rf "$t"; mkdir -p "$(dirname "$t")"; cp -Rp "$BACKUP/$t" "$t"; done
  cp -p "$BACKUP/artifacts.json" .gtt/index/artifacts.json
  cp -p "$BACKUP/technical-index.json" .gtt/index/technical-index.json
  echo "restored. Backup kept at $BACKUP" >&2
  exit 1
}
trap 'restore' ERR

rm -rf "${TARGETS[@]}"
for id in $IDS; do
  bash .gtt/scripts/gtt-reconcile.sh --retire "$id" --apply >/dev/null
done
bash .gtt/scripts/gtt-index.sh >/dev/null
trap - ERR

OUT="$(bash .gtt/scripts/gtt-validate.sh 2>&1 || true)"
if printf '%s\n' "$OUT" | grep -qE '^FAIL '; then
  printf '%s\n' "$OUT" >&2
  restore
fi
printf '%s\n' "$OUT" | grep -E '^(PASS|SKIPPED|CANNOT-DETERMINE|gtt-validate)' || true

echo
echo "Cleaned. Retired identities: $(printf '%s\n' "$IDS" | grep -c . || true). Backup: $BACKUP (safe to delete)."
echo "Review with 'git status', then commit the removal. Nothing outside the list above was touched."
