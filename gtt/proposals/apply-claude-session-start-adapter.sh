#!/usr/bin/env bash
# GTT - PROMOTION SCRIPT (human execution required)
#
# Status: Draft - not a decision. Prepared by an agent; never run by one.
# Proposal: gtt/proposals/PROPOSAL-artifact-identity-followups.md
#
# Applies, in one run, the Claude Code adapter for the GTT Session Memory
# Service:
#   1. Replaces the Claude hook script for SessionStart with a thin adapter
#      (staged at gtt/proposals/claude-adapter/session-start.py). It calls
#      gtt/scripts/gtt-session-context.sh, emits SessionStart additionalContext,
#      and reports failures visibly.
#   2. Changes ONLY the SessionStart command in the Claude settings file so
#      Python is resolved by gtt/scripts/gtt-run-python.sh (one probe, no
#      `|| fallback` after the script has started).
# No other hook or setting is modified.
#
# Usage (from the project root):
#   bash gtt/proposals/apply-claude-session-start-adapter.sh

set -euo pipefail

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
[ -n "$PY" ] || { echo "no working Python 3 interpreter found" >&2; exit 2; }

SRC="gtt/proposals/claude-adapter/session-start.py"
HOOK=".claude/hooks/session-start.py"
SETTINGS=".claude/settings.json"
for f in "$SRC" "$SETTINGS" gtt/scripts/gtt-run-python.sh gtt/scripts/gtt-session-context.sh; do
  [ -f "$f" ] || { echo "run from the project root: $f not found" >&2; exit 2; }
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

"$PY" - "$STAGE" "$SETTINGS" <<'EOF'
import json, sys
stage, path = sys.argv[1], sys.argv[2]
raw = open(path, encoding="utf-8", newline="").read()
cfg = json.loads(raw)
groups = cfg.get("hooks", {}).get("SessionStart")
if not groups:
    sys.exit("no SessionStart registration found; refusing to guess")
touched = 0
for g in groups:
    for h in g.get("hooks", []):
        if "session-start.py" in h.get("command", ""):
            h["command"] = "bash gtt/scripts/gtt-run-python.sh .claude/hooks/session-start.py"
            touched += 1
if touched != 1:
    sys.exit(f"expected exactly one session-start.py command, found {touched}")
out = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
if "\r\n" in raw:
    out = out.replace("\n", "\r\n")
open(f"{stage}/settings.json", "w", encoding="utf-8", newline="").write(out)
EOF

echo "=================================================================="
echo " GTT promotion: Claude Code SessionStart adapter   (HUMAN EXECUTION)"
echo "=================================================================="
echo
echo "--- diff: $SETTINGS (SessionStart command only) ---"
diff -u "$SETTINGS" "$STAGE/settings.json" || true
echo
echo "--- diff: $HOOK ---"
if [ -f "$HOOK" ]; then diff -u "$HOOK" "$SRC" || true; else cat "$SRC"; fi
echo
printf "Type 'apply' to write these changes (anything else aborts): "
read -r ANSWER
[ "$ANSWER" = "apply" ] || { echo "aborted - nothing was written."; exit 1; }

cp "$SETTINGS" "$STAGE/settings.json.bak"
[ -f "$HOOK" ] && cp "$HOOK" "$STAGE/session-start.py.bak"

cp "$SRC" "$HOOK"
cp "$STAGE/settings.json" "$SETTINGS"

restore() {
  echo "verification failed - restoring previous hook and settings" >&2
  cp "$STAGE/settings.json.bak" "$SETTINGS"
  if [ -f "$STAGE/session-start.py.bak" ]; then cp "$STAGE/session-start.py.bak" "$HOOK"; else rm -f "$HOOK"; fi
  exit 1
}

# Run the hook exactly as registered, and check the JSON contract.
CMD="$("$PY" -c "import json;print([h['command'] for g in json.load(open('$SETTINGS'))['hooks']['SessionStart'] for h in g['hooks']][0])")"
OUT="$(bash -c "$CMD")" || restore
printf '%s' "$OUT" | "$PY" -c "
import json, sys
o = json.load(sys.stdin)['hookSpecificOutput']
c = o['additionalContext']
assert o['hookEventName'] == 'SessionStart'
for s in ('operational-only', 'NOT authority', 'NOT evidence', 'NOT a decision record',
          'NOT a grounding source', 'GTT-SESSION-CONTEXT'):
    assert s in c, 'missing: ' + s
print('SessionStart JSON OK (%d chars of additionalContext)' % len(c))
" || restore

bash gtt/scripts/gtt-validate.sh || restore

echo
echo "Done. Review with 'git diff'; commit when satisfied."
echo "Start a NEW Claude Code session to see the warm start take effect."
