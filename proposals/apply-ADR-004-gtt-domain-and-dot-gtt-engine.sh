#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

# GTT GOVERNED CHANGE
# Proposal: PROPOSAL-gtt-domain-and-dot-gtt-engine
# ADR: ADR-004-gtt-domain-and-dot-gtt-engine
# Human execution required: YES
#
# Review the proposal, the ADR draft, and this script before running it.
# This script must not be executed automatically by an AI agent.
#
# Ratifies ADR-004 and applies the governed-context (L0) changes it records. It is
# the ONLY place where the ADR and the text of gtt-domain/context/ change for this
# decision. It works against the MIGRATED layout (.gtt/ Engine, gtt-domain/ domain):
# the ADR-004 migration script relocates the directories, moves the L0 files without
# editing them, and calls this script as the last governed step; after the migration
# it can also be run on its own, from the project root:
#
#   bash gtt-domain/proposals/apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh
#
# It refuses to run against the current (pre-migration) layout.
#
# Answering 'yes' is the ratification: the draft's Status becomes Accepted and its
# Approved by line is stamped with your git user name and today's date. Answering 'no'
# changes nothing (when the orchestrator called this script, it then restores the whole
# pre-migration state).

HERE="$(cd "$(dirname "$0")" && pwd)"    # the staged drafts sit next to this script
SLUG="gtt-domain-and-dot-gtt-engine"
ADR_DRAFT="$HERE/ADR-DRAFT-$SLUG.md"
ADR_TARGET="gtt-domain/adr/ADR-004-$SLUG.md"

# target | staged full draft | sha256 the target must have right now
# (line-ending-insensitive; it is the file as it was when the drafts were prepared)
CHANGES=(
  "gtt-domain/context/architecture.md|context-architecture-adr-004.md|f7b5f29475a18957c3915aa5a3cf2bc270963df57952a8ec6273b0cbcd9ec5a5"
  "gtt-domain/context/constraints.md|context-constraints-adr-004.md|de8c6eac82cc2c7fbec6b1cc2b7fc5b7a3ed07a08a2d9f695ab3a683e1b8f21a"
  "gtt-domain/context/glossary.md|context-glossary-adr-004.md|d7e20afb92c9f57adb439ce3cc397e1b856e11e4d9f32e4e4f6e099d4fd4b05b"
  "gtt-domain/context/principles.md|context-principles-adr-004.md|2f0103ad2677812135c48a27ac8cca534255a241fbf5ebf816377dfabe0e7a3f"
  "gtt-domain/context/solution-vision.md|context-solution-vision-adr-004.md|b0559b1366b86055d61f6b8f48b7293217d8284730e4f96c715a62656befeca0"
  "gtt-domain/context/stack.md|context-stack-adr-004.md|d30a073e7ee7d935966a7c5f6a15126f544aef102229bc115516a235b40e55f7"
)

sha_lf() { tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1; }
fail() { echo "ERROR: $*" >&2; exit 2; }

[ -f gtt-domain/.frozen ] && [ -d gtt-domain/context ] && [ -d gtt-domain/adr ] \
  || fail "run from the project root of the migrated layout (gtt-domain/context, gtt-domain/adr and gtt-domain/.frozen present). Run the ADR-004 migration script; it calls this one."
[ -f "$ADR_DRAFT" ] || fail "ADR draft missing: $ADR_DRAFT"
[ ! -e "$ADR_TARGET" ] || fail "$ADR_TARGET already exists"
ls gtt-domain/adr/ADR-004*.md >/dev/null 2>&1 && fail "an ADR-004 already exists in gtt-domain/adr/" || true
for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  [ -f "$HERE/$staged" ] || fail "staged draft missing: $HERE/$staged"
  [ -f "$target" ] || fail "target missing: $target"
  [ "$(sha_lf "$target")" = "$want" ] \
    || fail "$target changed since the drafts were prepared - refusing to overwrite it (re-stage with gtt-adr)"
done

echo "GTT governed change"
echo "Proposal: PROPOSAL-gtt-domain-and-dot-gtt-engine"
echo "ADR: ADR-004-$SLUG"
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
  echo "FAILED - restoring gtt-domain/context/ and removing the partial ADR" >&2
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
    -v ap="- Approved by: Solution Designer ($WHO) - ratified by executing apply-ADR-004-$SLUG.sh on $(date -u +%Y-%m-%d)" \
    '/^- Status: /   && !s { print st; s=1; next }
     /^- Approved by: / && !a { print ap; a=1; next }
     { print }' "$ADR_TARGET" > "$BK/adr.new"
cp "$BK/adr.new" "$ADR_TARGET"

for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  cp "$HERE/$staged" "$target"
done

bash .gtt/scripts/gtt-check-stack.sh

trap - ERR INT TERM HUP
rm -rf "$BK"
# The draft is consumed (this is the 'mv' of the standard promotion shape). When the
# orchestrator ran this script from a temporary copy, remove the moved copy too.
rm -f "$ADR_DRAFT" "gtt-domain/proposals/ADR-DRAFT-$SLUG.md"

echo ""
echo "Promoted. ADR-004-$SLUG is now in gtt-domain/adr/ and gtt-domain/context/ reflects it."
echo "You can now delete the staged drafts in gtt-domain/proposals/ for this change:"
for c in "${CHANGES[@]}"; do
  IFS='|' read -r target staged want <<<"$c"
  echo "  gtt-domain/proposals/$staged"
done
