#!/usr/bin/env bash
# GTT - PROMOTION SCRIPT (human execution required)
#
# Proposal: gtt/proposals/PROPOSAL-artifact-identity-followups.md
# Applies, in one run:
#   1. AGENTS.md: adds the "Artifact identity and technical index" section
#      before "## Validation".
#   2. .claude/hooks/session-start.py: new SessionStart hook (warm start).
#   3. .claude/settings.json: registers that hook.
#   4. Rebuilds the derived index (AGENTS.md is an indexed artifact),
#      regenerates gtt/SESSION.md, and runs gtt-validate.sh.
#
# This script was prepared by an agent and MUST be run by you, from the
# project root. The agent never executes it. Generating it is not approval.
#
# Usage:
#   bash gtt/proposals/apply-artifact-identity-followups.sh

set -euo pipefail

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
[ -n "$PY" ] || { echo "no working Python 3 interpreter found" >&2; exit 2; }

for f in AGENTS.md .claude/settings.json gtt/scripts/gtt_artifacts.py; do
  [ -f "$f" ] || { echo "run from the project root: $f not found" >&2; exit 2; }
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# ---- stage the new contents (nothing is written to the project yet) -------

cat > "$STAGE/agents-section.md" <<'EOF'
## Artifact identity and technical index

Every governed Markdown artifact has a stable identity (`gtt/index/artifacts.json`)
independent of its path: a move or rename is reconciled, never treated as delete
+ create. Reference an artifact as `[[ID]]` (e.g. `[[ADR-007]]`) so the reference
survives moves. `gtt/index/technical-index.json` is a DERIVED accelerator - for
locating concepts and sections (`gtt/scripts/gtt-query.sh`) - never a source of
truth, never evidence in itself; the Markdown it points to is authoritative.
Regenerate it with `gtt/scripts/gtt-index.sh`; never hand-edit it. After any move
run `gtt/scripts/gtt-reconcile.sh` (dry-run first). `gtt/scripts/gtt-check-integrity.sh`
(part of `gtt-validate.sh`) fails on unreconciled moves, duplicate logical identity,
broken or old-path references, unresolved `[[ID]]`, and a stale index. Agents
operate through these scripts and MUST NOT own an artifact's identity or authority,
and never rewrite frozen `gtt/context/` or `gtt/adr/` files to fix a reference.

EOF

cat > "$STAGE/session-start.py" <<'EOF'
#!/usr/bin/env python3
"""SessionStart: regenerate and surface gtt/SESSION.md (derived, non-authoritative)."""
import json
import subprocess
import sys

try:
    subprocess.run(["bash", "gtt/scripts/gtt-status.sh"], capture_output=True, timeout=30)
    text = open("gtt/SESSION.md", encoding="utf-8").read()
except Exception:
    sys.exit(0)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "GTT session state (derived, operational only - NOT authority, "
                         "evidence, or a decision record):\n" + text}}))
EOF

"$PY" - "$STAGE" <<'EOF'
import json, sys
stage = sys.argv[1]

def rd(p):
    return open(p, encoding="utf-8", newline="").read()

# AGENTS.md
s = rd("AGENTS.md")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")
section = rd(f"{stage}/agents-section.md")
if "## Artifact identity and technical index" in s:
    new = s
elif "\n## Validation\n" not in s:
    sys.exit("AGENTS.md has no '## Validation' anchor; refusing to guess an insertion point")
else:
    new = s.replace("\n## Validation\n", "\n" + section + "## Validation\n", 1)
open(f"{stage}/AGENTS.md", "w", encoding="utf-8", newline="").write(
    new.replace("\n", "\r\n") if crlf else new)

# settings.json
raw = rd(".claude/settings.json")
cfg = json.loads(raw)
hook = {"hooks": [{"type": "command", "command":
        "python3 -c '' >/dev/null 2>&1 && python3 .claude/hooks/session-start.py "
        "|| python .claude/hooks/session-start.py"}]}
hooks = cfg.setdefault("hooks", {})
if "SessionStart" not in hooks:
    hooks["SessionStart"] = [hook]
out = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
if "\r\n" in raw:
    out = out.replace("\n", "\r\n")
open(f"{stage}/settings.json", "w", encoding="utf-8", newline="").write(out)
EOF

# ---- review -----------------------------------------------------------------

echo "=================================================================="
echo " GTT promotion: artifact identity follow-ups   (HUMAN EXECUTION)"
echo "=================================================================="
echo
echo "--- diff: AGENTS.md ---"
diff -u AGENTS.md "$STAGE/AGENTS.md" || true
echo
echo "--- diff: .claude/settings.json ---"
diff -u .claude/settings.json "$STAGE/settings.json" || true
echo
echo "--- new file: .claude/hooks/session-start.py ---"
if [ -f .claude/hooks/session-start.py ]; then
  diff -u .claude/hooks/session-start.py "$STAGE/session-start.py" || true
else
  cat "$STAGE/session-start.py"
fi
echo
echo "Then: rebuild gtt/index/, regenerate gtt/SESSION.md, run gtt-validate.sh."
echo
printf "Type 'apply' to write these changes (anything else aborts): "
read -r ANSWER
[ "$ANSWER" = "apply" ] || { echo "aborted - nothing was written."; exit 1; }

# ---- apply (stops on the first failure) ---------------------------------------

cp AGENTS.md "$STAGE/AGENTS.md.bak"
cp .claude/settings.json "$STAGE/settings.json.bak"

cp "$STAGE/AGENTS.md" AGENTS.md
mkdir -p .claude/hooks
cp "$STAGE/session-start.py" .claude/hooks/session-start.py
cp "$STAGE/settings.json" .claude/settings.json

if ! { bash gtt/scripts/gtt-index.sh && bash gtt/scripts/gtt-status.sh >/dev/null \
       && bash gtt/scripts/gtt-validate.sh; }; then
  echo "validation failed - restoring AGENTS.md and settings.json" >&2
  cp "$STAGE/AGENTS.md.bak" AGENTS.md
  cp "$STAGE/settings.json.bak" .claude/settings.json
  rm -f .claude/hooks/session-start.py
  bash gtt/scripts/gtt-index.sh >/dev/null 2>&1 || true
  exit 1
fi

echo
echo "Done. Review with 'git diff', commit when satisfied."
echo "You may now delete gtt/proposals/PROPOSAL-artifact-identity-followups.md"
echo "and this script (then run gtt/scripts/gtt-index.sh)."
