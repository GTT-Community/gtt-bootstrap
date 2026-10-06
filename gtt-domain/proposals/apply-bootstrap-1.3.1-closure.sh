#!/usr/bin/env bash
# GTT - promotion script: Bootstrap 1.3.1 closure (Governance / Observation).
#
# Proposal: gtt-domain/proposals/PROPOSAL-bootstrap-1.3.1-closure.md
# Staged:   gtt-domain/proposals/closure-1.3.1/closure-1.3.1.patch
#           gtt-domain/proposals/closure-1.3.1/claude-adapter/protect-l0.py
#
# HUMAN EXECUTION REQUIRED. The agent contract, the change-request front door and
# the Claude Code hooks and permissions are owned by the Solution Designer; an
# agent prepares this script and never runs it. Run it from the project root:
#
#   bash gtt-domain/proposals/apply-bootstrap-1.3.1-closure.sh
#
# It changes exactly four files and nothing else:
#
#   AGENTS.md                      the Antigravity overlay (the five modifications of
#                                  PROPOSAL-antigravity-ade-support.md); the Git hook as the
#                                  first shared control, with CI as the guaranteed layer; the
#                                  human-only acts the enforcement now covers
#   gtt-domain/change-request.md   the front door is for governance and Epics; Stories are
#                                  out of it; vocabulary `Planned`
#   .claude/settings.json          deny Edit / Write on gtt-domain/.frozen and on
#                                  gtt-domain/governance-backlog.json
#   .claude/hooks/protect-l0.py    the decision core shared with gtt_protect.py: freeze marker,
#                                  governance ledger, promotion scripts and staged patches in
#                                  any spelling, human-only acts, Git-hook bypass, and a
#                                  visible warning when BLOCKING cannot be evaluated
#
# It records no ADR: it touches neither gtt-domain/context/ nor gtt-domain/adr/.
# It applies everything or nothing.
#
# It replaces gtt-domain/proposals/apply-AGENTS-antigravity.sh: the Antigravity changes
# are part of this patch. Do not run that script after this one.

set -euo pipefail

PATCH="gtt-domain/proposals/closure-1.3.1/closure-1.3.1.patch"
STAGED_HOOK="gtt-domain/proposals/closure-1.3.1/claude-adapter/protect-l0.py"
HOOK=".claude/hooks/protect-l0.py"

fail() { echo "apply-bootstrap-1.3.1-closure: $*" >&2; exit 1; }

[ -d .gtt ] && [ -f AGENTS.md ] || fail "run from the project root (no .gtt/ or AGENTS.md here)."
command -v git >/dev/null || fail "git is required."
for f in "$PATCH" "$STAGED_HOOK" "$HOOK" gtt-domain/change-request.md .claude/settings.json; do
  [ -f "$f" ] || fail "$f not found."
done
grep -q "id: antigravity" .gtt/scaffold/manifest.yaml \
  || fail "the registry has no \`antigravity\` overlay: the contract must not describe one that does not exist."
grep -q ">>> gtt-decision-core >>>" .gtt/scripts/gtt_protect.py \
  || fail ".gtt/scripts/gtt_protect.py does not carry the decision core this hook shares with it."
if git apply --check --reverse "$PATCH" 2>/dev/null; then
  fail "this package is already applied (the patch reverses cleanly). Nothing to do."
fi
# The destinations may carry uncommitted work (the closure is a single commit by decision of the
# Solution Designer), so the precondition is that the patch applies exactly, not that they are clean.
git apply --check "$PATCH" || fail "the patch does not apply to the current files; it must be regenerated."
python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$STAGED_HOOK" || fail "the staged hook is not valid Python."
python3 -c "import json,sys; json.load(open(sys.argv[1]))" .claude/settings.json || fail ".claude/settings.json is not valid JSON."

echo "This will change four files."
echo
echo "=== AGENTS.md, gtt-domain/change-request.md, .claude/settings.json"
git apply --stat "$PATCH"
echo
cat "$PATCH"
echo
echo "=== $HOOK (installed -> staged)"
diff -u "$HOOK" "$STAGED_HOOK" || true
echo
printf "Apply these changes? Type 'apply' to confirm: "
read -r answer
[ "$answer" = "apply" ] || fail "not confirmed; nothing was written."

BACKUP="$(mktemp)"
cp "$HOOK" "$BACKUP" || fail "could not back up $HOOK; nothing was written."
git apply "$PATCH" || { rm -f "$BACKUP"; fail "git apply failed; nothing was changed."; }
if ! cp "$STAGED_HOOK" "$HOOK"; then
  cp "$BACKUP" "$HOOK" 2>/dev/null || true
  git apply --reverse "$PATCH" || true
  rm -f "$BACKUP"
  fail "could not install the hook; the patch was reverted. Nothing was changed."
fi
python3 -c "import json,sys; json.load(open(sys.argv[1]))" .claude/settings.json || {
  cp "$BACKUP" "$HOOK"; git apply --reverse "$PATCH" || true; rm -f "$BACKUP"
  fail ".claude/settings.json is not valid JSON after the patch; everything was reverted."
}
rm -f "$BACKUP"

cat <<'MSG'
apply-bootstrap-1.3.1-closure: done - four files changed.

Now run, in this order:
  bash .gtt/scripts/gtt-maintain.sh
  python3 .gtt/tests/bootstrap-acceptance.py
  bash .gtt/scripts/gtt-validate.sh
MSG
