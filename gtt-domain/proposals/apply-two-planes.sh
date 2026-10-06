#!/usr/bin/env bash
# GTT - promotion script: the two-plane architecture (Governance / Observation).
#
# Source:  GTT-Architecture-Governance-Observation.md
# Staged:  gtt-domain/proposals/AGENTS-two-planes.patch
#          gtt-domain/proposals/claude-adapter/protect-l0.py
#          gtt-domain/proposals/claude-adapter/detect-drift.py
#
# HUMAN EXECUTION REQUIRED. The agent contract and the Claude Code hooks are owned
# by the Solution Designer; an agent prepares this script and never runs it. Run it
# from the project root:
#
#   bash gtt-domain/proposals/apply-two-planes.sh
#
# It changes exactly three files and nothing else:
#
#   AGENTS.md                      the contract: the two planes, observation, Epics
#                                  governed / Stories free, freeze as a baseline
#   .claude/hooks/protect-l0.py    blocks only on an explicit basis: adds the human-only
#                                  acts and BLOCKING path boundaries, removes two false
#                                  positives, closes a redirect hole on the contract file
#   .claude/hooks/detect-drift.py  runs the observation engine after a write and hands
#                                  what is new to the agent; never blocks
#
# .claude/settings.json is not touched: both hooks are already registered there.

set -euo pipefail

PATCH="gtt-domain/proposals/AGENTS-two-planes.patch"
STAGED="gtt-domain/proposals/claude-adapter"
HOOKS=".claude/hooks"

fail() { echo "apply-two-planes: $*" >&2; exit 1; }

[ -d .gtt ] && [ -f AGENTS.md ] || fail "run from the project root (no .gtt/ or AGENTS.md here)."
command -v git >/dev/null || fail "git is required."
[ -f .gtt/scripts/gtt-observe.sh ] || fail ".gtt/scripts/gtt-observe.sh is missing: the engine must be in place before the contract describes it."
for f in "$PATCH" "$STAGED/protect-l0.py" "$STAGED/detect-drift.py"; do [ -f "$f" ] || fail "$f not found."; done
[ -d "$HOOKS" ] || fail "$HOOKS not found (is Claude Code a participating ADE here?)."
git apply --check "$PATCH" || fail "the patch does not apply to the current AGENTS.md; it must be regenerated."
python3 -c "import ast,sys; [ast.parse(open(f).read()) for f in sys.argv[1:]]" "$STAGED/protect-l0.py" "$STAGED/detect-drift.py" \
  || fail "a staged hook is not valid Python."

echo "This will change three files."
echo
echo "=== AGENTS.md"
git apply --stat "$PATCH"
for hook in protect-l0.py detect-drift.py; do
  echo
  echo "=== $HOOKS/$hook"
  diff -u "$HOOKS/$hook" "$STAGED/$hook" | sed -n '1,400p' || true
done
echo
echo "The full contract diff is in $PATCH (review it before confirming)."
printf "Apply these changes? Type 'apply' to confirm: "
read -r answer
[ "$answer" = "apply" ] || fail "not confirmed; nothing was written."

git apply "$PATCH" || fail "git apply failed; nothing was changed."
cp "$STAGED/protect-l0.py" "$HOOKS/protect-l0.py" || fail "could not install protect-l0.py (AGENTS.md was already patched)."
cp "$STAGED/detect-drift.py" "$HOOKS/detect-drift.py" || fail "could not install detect-drift.py (AGENTS.md and protect-l0.py were already changed)."

echo "apply-two-planes: done. Now run: bash .gtt/scripts/gtt-maintain.sh"
