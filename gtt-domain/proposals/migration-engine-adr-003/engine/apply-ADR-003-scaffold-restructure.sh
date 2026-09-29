#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

# GTT GOVERNED CHANGE
# Proposal: PROPOSAL-scaffold-restructure
# ADR: ADR-003-scaffold-restructure
# Human execution required: YES
#
# Review the proposal, the ADR draft, and this script before running it.
# This script must not be executed automatically by an AI agent.
#
# Ratifies ADR-003 and applies the governed-context (L0) changes it records. It is
# the ONLY place where the ADR and the text of context/ change for this decision.
# It works against the layout created by apply-scaffold-restructure.sh (context/ and
# adr/ at the project root). That orchestrator calls it as the last governed step of
# the migration; after the migration it can also be run on its own, from the project
# root:
#
#   bash proposals/apply-ADR-003-scaffold-restructure.sh
#
# Answering 'yes' is the ratification: the draft's Status becomes Accepted and its
# Approved by line is stamped with your git user name and today's date. Answering 'no'
# changes nothing (when the orchestrator called this script, it then restores the whole
# pre-migration state).

HERE="$(cd "$(dirname "$0")" && pwd)"    # the staged drafts sit next to this script
SLUG="scaffold-restructure"
ADR_DRAFT="$HERE/ADR-DRAFT-$SLUG.md"
ADR_TARGET="adr/ADR-003-$SLUG.md"

# target | staged full draft | sha256 the target must have right now
# (line-ending-insensitive; it is the file as it was when the drafts were prepared)
CHANGES=(
  "context/architecture.md|context-architecture-adr-003.md|72ba92dd8a326480ce0eece0b36689565129be4f496444112b27f961aff46dec"
  "context/glossary.md|context-glossary-adr-003.md|2b1125f6ab077091ae624d31ce23607acf181187de6119441e56bb68ede55cc2"
  "context/principles.md|context-principles-adr-003.md|e0ab445a55bdba3e6e29598bcb6ba2011ef118e8498111ba5057866e4dfe2b3d"
  "context/solution-vision.md|context-solution-vision-adr-003.md|09ac6954e9df9c8866a054f5ee0b9048cac947589e98c1b9436df2f766e3a3a7"
  "context/stack.md|context-stack-adr-003.md|cab695e31d775c190fc7f78b5339d5d955f5ede78bf6425d77c3d8347a20ee28"
)

sha_lf() { tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1; }
fail() { echo "ERROR: $*" >&2; exit 2; }

[ -f .frozen ] && [ -d context ] && [ -d adr ] \
  || fail "run from the project root of the layout created by apply-scaffold-restructure.sh (context/ and adr/ at the root, .frozen present). Run that script; it calls this one."
[ -f "$ADR_DRAFT" ] || fail "ADR draft missing: $ADR_DRAFT"
[ ! -e "$ADR_TARGET" ] || fail "$ADR_TARGET already exists"
ls adr/ADR-003*.md >/dev/null 2>&1 && fail "an ADR-003 already exists in adr/" || true
for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  [ -f "$HERE/$staged" ] || fail "staged draft missing: $HERE/$staged"
  [ -f "$target" ] || fail "target missing: $target"
  [ "$(sha_lf "$target")" = "$want" ] \
    || fail "$target changed since the drafts were prepared - refusing to overwrite it (re-stage with gtt-adr)"
done

echo "GTT governed change"
echo "Proposal: PROPOSAL-scaffold-restructure"
echo "ADR: ADR-003-$SLUG"
echo ""
echo "This will apply:"
echo "  ADR-DRAFT-$SLUG.md  ->  $ADR_TARGET   (new file; Status becomes Accepted on 'yes')"
for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  echo "  $staged  ->  $target   (overwrite)"
done
echo ""

while true; do
    read -r -p "Review the change, or approve it? [view/yes/no]: " choice
    case "$choice" in
        view|v)
            echo ""
            echo "===== ADR-DRAFT-$SLUG.md (new ADR) ====="
            cat "$ADR_DRAFT"
            echo ""
            for c in "${CHANGES[@]}"; do
              IFS='|' read -r target staged want <<<"$c"
              echo "===== $target: current -> staged ====="
              diff -u --strip-trailing-cr "$target" "$HERE/$staged" || true
              echo ""
            done
            ;;
        yes|y)
            break
            ;;
        no|n)
            echo "Change not promoted."
            exit 1
            ;;
        *)
            echo "Please answer view, yes, or no."
            ;;
    esac
done

# Re-verify right before writing: the check above ran before you read the diffs, and
# the files may have changed while this prompt waited. Nothing has been written yet.
for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  [ "$(sha_lf "$target")" = "$want" ] \
    || fail "$target changed while waiting for your answer - nothing was written (re-stage with gtt-adr)"
done
[ ! -e "$ADR_TARGET" ] || fail "$ADR_TARGET appeared while waiting - nothing was written"

# Fail fast, and put everything back if any step fails.
BK="$(mktemp -d)"
for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  cp "$target" "$BK/$staged"
done
restore() {
  trap - ERR
  set +e
  echo "FAILED - restoring context/ and removing the partial ADR" >&2
  for c in "${CHANGES[@]}"; do
    IFS='|' read -r target staged want <<<"$c"
    cp "$BK/$staged" "$target"
  done
  rm -f "$ADR_TARGET"
  rm -rf "$BK"
  exit 1
}
trap restore ERR INT TERM HUP

cp "$ADR_DRAFT" "$ADR_TARGET"
WHO="$(git config user.name 2>/dev/null || echo 'Solution Designer')"
awk -v st="- Status: Accepted" \
    -v ap="- Approved by: Solution Designer ($WHO) - ratified by executing apply-ADR-003-$SLUG.sh on $(date -u +%Y-%m-%d)" \
    '/^- Status: /   && !s { print st; s=1; next }
     /^- Approved by: / && !a { print ap; a=1; next }
     { print }' "$ADR_TARGET" > "$BK/adr.new"
cp "$BK/adr.new" "$ADR_TARGET"

for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  cp "$HERE/$staged" "$target"
done

bash gtt/scripts/gtt-check-stack.sh

trap - ERR INT TERM HUP
rm -rf "$BK"
# The draft is consumed (this is the 'mv' of the standard promotion shape). When the
# orchestrator ran this script from a temporary copy, remove the moved copy too.
rm -f "$ADR_DRAFT" "proposals/ADR-DRAFT-$SLUG.md"

echo ""
echo "Promoted. ADR-003-$SLUG is now in adr/ and context/ reflects it."
echo "You can now delete the staged drafts in proposals/ for this change:"
for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  echo "  proposals/$staged"
done
