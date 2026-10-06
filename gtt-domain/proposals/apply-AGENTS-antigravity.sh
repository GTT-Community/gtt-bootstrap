#!/usr/bin/env bash
# GTT - promotion script: AGENTS.md mentions of the Antigravity overlay.
#
# Proposal: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md
# Patch:    gtt-domain/proposals/AGENTS-antigravity.patch
#
# HUMAN EXECUTION REQUIRED. AGENTS.md is owned by the Solution Designer; an agent
# prepares this script and never runs it. Run it from the project root:
#
#   bash gtt-domain/proposals/apply-AGENTS-antigravity.sh
#
# It changes one file, AGENTS.md (21 insertions, 12 deletions), and nothing else.
# It records no ADR: the change adds an ADE overlay to the agent contract and
# touches neither gtt-domain/context/ nor gtt-domain/adr/.

set -euo pipefail

PATCH="gtt-domain/proposals/AGENTS-antigravity.patch"

fail() { echo "apply-AGENTS-antigravity: $*" >&2; exit 1; }

[ -d .gtt ] && [ -f AGENTS.md ] || fail "run from the project root (no .gtt/ or AGENTS.md here)."
[ -f "$PATCH" ] || fail "$PATCH not found."
command -v git >/dev/null || fail "git is required."
git diff --quiet -- AGENTS.md || fail "AGENTS.md has uncommitted changes; commit or discard them first."
grep -q "id: antigravity" .gtt/scaffold/manifest.yaml \
  || fail "the registry has no \`antigravity\` overlay yet; apply this after the overlay is implemented (STORY-001)."
git apply --check "$PATCH" || fail "the patch does not apply to the current AGENTS.md; it must be regenerated."

echo "This will change AGENTS.md as follows:"
echo
git apply --stat "$PATCH"
echo
cat "$PATCH"
echo
printf "Apply this change to AGENTS.md? Type 'apply' to confirm: "
read -r answer
[ "$answer" = "apply" ] || fail "not confirmed; nothing was written."

git apply "$PATCH" || fail "git apply failed; AGENTS.md was not changed."
echo "apply-AGENTS-antigravity: AGENTS.md updated. Now run: bash .gtt/scripts/gtt-maintain.sh"
