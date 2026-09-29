#!/usr/bin/env bash
# Full logical rehearsal of the ADR-004 migration on DISPOSABLE COPIES of the real working tree.
# It reuses the orchestrator's own code blocks (extracted with sed) wherever that does not amount to
# running the promotion scripts, and replicates the rest command for command (the agent never runs
# apply-*.sh; the human smoke test runs the real thing on a copy).
# Scenarios: S1 success (+ functional checks of every engine component at its new path), S2 'no' at
# ratification, S3 injected failure, S4 L0 changes while the prompt waits, S5 baseline failure output,
# S6 the promotion-script guard on the pre-migration layout, S7 CRLF preflight, S8 idempotent re-run.
#   GTT_REHEARSAL_DIR (copies)   GTT_REPO (the real repository, only READ)
export PYTHONDONTWRITEBYTECODE=1
S="${GTT_REHEARSAL_DIR:-${TMPDIR:-/tmp}/gtt-rehearsal}"; mkdir -p "$S"
R="${GTT_REPO:-/c/griott/GTT/gtt-bootstrap}"
H="$R/proposals/gtt-domain-migration/rehearsal-harness"
ORCH="$R/proposals/apply-gtt-domain-migration.sh"
ADRSC="$R/proposals/apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh"
PASS=0; FAILN=0
ok()   { echo "  PASS  $*"; PASS=$((PASS+1)); }
bad()  { echo "  FAIL  $*"; FAILN=$((FAILN+1)); }
chk()  { if [ "$1" = "0" ]; then ok "$2"; else bad "$2"; fi; }

sha_lf() { tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1; }
snap() { find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1; }
pass_names() { grep -E '^PASS' "$1" | sed -E 's/[[:space:]]+\[.*$//; s/[[:space:]]+$//' | sort; }

# The orchestrator's own rollback function, verbatim (used by S2/S3/S4)
ROLLBACK_SRC="$S/rollback_fn.sh"
sed -n '/^rollback() {/,/^}/p' "$ORCH" > "$ROLLBACK_SRC"

# The real working tree carries the ADR-003 result uncommitted; the orchestrator (like the ADR-003 one) demands
# a committed tree, so the copy starts from what the operator's own commit produces.
fresh() {
  GTT_REHEARSAL_DIR="$S" GTT_REPO="$R" bash "$H/mkcopy.sh" "$1" >/dev/null 2>&1; cd "$S/$1" || exit 1
  git add -A >/dev/null 2>&1; git commit -qm "state before the ADR-004 migration (the operator's commit of the ADR-003 result)" >/dev/null 2>&1
}
PYX=python      # settings.json says python3; on this workstation python3 is the Microsoft Store stub, so the harness uses python

ADRLIST=(ADR-DRAFT-gtt-domain-and-dot-gtt-engine.md apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh
  context-architecture-adr-004.md context-constraints-adr-004.md context-glossary-adr-004.md
  context-principles-adr-004.md context-solution-vision-adr-004.md context-stack-adr-004.md)
stage_from_real() {  # what the orchestrator's re-exec does
  STAGE=$(mktemp -d); cp -r proposals/gtt-domain-migration "$STAGE/pkg"; mkdir "$STAGE/adr"
  for f in "${ADRLIST[@]}"; do cp "proposals/$f" "$STAGE/adr/$f"; done
  PKG=$STAGE/pkg; ADRPKG=$STAGE/adr
}

identity_dump() { python - "$1" <<'E'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
for e in sorted(d["artifacts"],key=lambda a:a["id"]): print(e["id"],e.get("status","active"),e["path"])
E
}

preflight_blocks() {  # orchestrator's real preflight blocks: STALE_L0 and DIRTY
  ( ADRPKG="$1"
    eval "$(sed -n '/^STALE_L0=""/,/^fi$/p' "$ORCH" | sed 's/^  exit 1$/  exit 11/')"
    echo "stale-l0: none" )
  local rc=$?
  [ $rc -eq 0 ] || return $rc
  ( eval "$(sed -n '/^DIRTY=""/,/^git diff --cached --quiet/p' "$ORCH" | sed 's/^  exit 1$/  exit 12/; s/|| { echo "There are staged.*$/|| exit 13/')"
    echo "dirty: none" )
}

echo "=================== S1  success path (real manifest) ==================="
fresh rh1
BEFORE_SNAP=$(snap); FROZEN_BEFORE=$(sha256sum .frozen | cut -d' ' -f1)
identity_dump .gtt/index/artifacts.json > /dev/null 2>&1
identity_dump gtt/index/artifacts.json > "$S/id_before.txt"
for f in architecture constraints glossary principles solution-vision stack; do echo "$f $(sha_lf context/$f.md)"; done > "$S/l0_before.txt"
stage_from_real
python "$PKG/migrate.py" preflight --pkg "$PKG" >/dev/null; chk $? "migrate preflight ok on the copy (incl. CRLF scan)"
preflight_blocks "$ADRPKG" ; chk $? "orchestrator STALE_L0 + DIRTY blocks pass (real code)"
bash gtt/scripts/gtt-validate.sh > "$S/base.out" 2>&1; chk $? "baseline gtt-validate exit 0"
pass_names "$S/base.out" > "$S/base.txt"
# behaviour of the pre-migration engine, captured to compare with the migrated engine
bash gtt/scripts/gtt-freeze.sh > "$S/freeze_pre.out" 2>&1; echo $? > "$S/freeze_pre.rc"
BACKUP=$STAGE/backup.tar; tar --exclude=./.git -cf "$BACKUP" . && tar -tf "$BACKUP" >/dev/null; chk $? "backup created and readable"
python "$PKG/migrate.py" apply --pkg "$PKG" > "$S/apply.out" 2>&1; chk $? "migrate apply (moves+rewrite+patches+overlays; L0 text untouched)"
tail -2 "$S/apply.out"
ALLSAME=0; while read -r f h; do [ "$(sha_lf gtt-domain/context/$f.md)" = "$h" ] || ALLSAME=1; done < "$S/l0_before.txt"
chk $ALLSAME "L0 files moved with text untouched (hashes == original) BEFORE ratification"
# ---- ratification effects, replicating the ADR script (incl. the re-check after 'yes')
grep -E '^  "gtt-domain/context/' "$ADRPKG/apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh" > "$S/changes.txt"
[ "$(wc -l < "$S/changes.txt" | tr -d ' ')" = 6 ]; chk $? "ADR script lists the six L0 files"
BADH=0; while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; [ "$(sha_lf "$t")" = "$w" ] || BADH=1; done < "$S/changes.txt"
chk $BADH "ADR script pre-prompt hash check passes (6/6)"
BADH=0; while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; [ "$(sha_lf "$t")" = "$w" ] || BADH=1; done < "$S/changes.txt"
chk $BADH "re-check after 'yes' passes (6/6)"
cp "$ADRPKG/ADR-DRAFT-gtt-domain-and-dot-gtt-engine.md" gtt-domain/adr/ADR-004-gtt-domain-and-dot-gtt-engine.md
grep -q '^- Status: Proposed' gtt-domain/adr/ADR-004-gtt-domain-and-dot-gtt-engine.md; chk $? "ADR-004 is Proposed before the stamp (not Accepted early)"
awk -v st="- Status: Accepted" -v ap="- Approved by: Solution Designer (Rehearsal) - ratified on $(date -u +%Y-%m-%d)" '/^- Status: /&&!s{print st;s=1;next} /^- Approved by: /&&!a{print ap;a=1;next}{print}' gtt-domain/adr/ADR-004-gtt-domain-and-dot-gtt-engine.md > "$S/adr.new"; cp "$S/adr.new" gtt-domain/adr/ADR-004-gtt-domain-and-dot-gtt-engine.md
while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; cp "$ADRPKG/$s" "$t"; done < "$S/changes.txt"
bash .gtt/scripts/gtt-check-stack.sh > "$S/stack.out" 2>&1; chk $? "gtt-check-stack (ADR cited in the map exists)"
! grep -qi 'not frozen yet' "$S/stack.out"; chk $? "gtt-check-stack is NOT vacuous (it sees gtt-domain/.frozen)"
rm -f "gtt-domain/proposals/ADR-DRAFT-gtt-domain-and-dot-gtt-engine.md"
SAME=0; while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; [ "$(sha_lf "$t")" = "$(sha_lf "$ADRPKG/$s")" ] || SAME=1; done < "$S/changes.txt"
chk $SAME "L0 after ratification == staged full drafts (hash by hash, 6/6)"
# ---- identity of the consumed draft
bash .gtt/scripts/gtt-index.sh > "$S/idx_without.out" 2>&1; echo "  (without reconcile, gtt-index exit=$?  <- expected non-zero)"
bash .gtt/scripts/gtt-reconcile.sh --apply --retire PROP-ADR-DRAFT-GTT-DOMAIN-AND-DOT-GTT-ENGINE > "$S/reconcile.out" 2>&1; chk $? "reconcile --apply --retire exits 0"
bash .gtt/scripts/gtt-index.sh > "$S/idx.out" 2>&1; chk $? "gtt-index after reconcile"
bash .gtt/scripts/gtt-guard-sync.sh >/dev/null 2>&1; chk $? "gtt-guard-sync (registry at .gtt/protection/)"
bash .gtt/scripts/gtt-status.sh >/dev/null 2>&1; chk $? "gtt-status (gtt-domain/session.md)"
bash .gtt/scripts/gtt-index.sh >/dev/null 2>&1
bash .gtt/scripts/gtt-check-integrity.sh > "$S/integ.out" 2>&1; chk $? "gtt-check-integrity"; tail -1 "$S/integ.out"
bash .gtt/scripts/gtt-check-protection.sh >/dev/null 2>&1; chk $? "gtt-check-protection"
bash .gtt/scripts/gtt-check-session-adapter.sh claude >/dev/null 2>&1; chk $? "gtt-check-session-adapter claude"
bash .gtt/scripts/gtt-check-markdown.sh >/dev/null 2>&1; chk $? "gtt-check-markdown"
bash .gtt/scripts/gtt-validate.sh > "$S/after.out" 2>&1; chk $? "gtt-validate after"
pass_names "$S/after.out" > "$S/after.txt"
[ -z "$(comm -23 "$S/base.txt" "$S/after.txt")" ]; chk $? "no check that passed at baseline regressed ($(wc -l < "$S/after.txt") PASS vs $(wc -l < "$S/base.txt"))"
grep -E 'SKIPPED|CANNOT' "$S/after.out" | cut -c1-60
python "$PKG/migrate.py" verify --pkg "$PKG" >/dev/null 2>&1; chk $? "migrate verify (.gtt/scaffold/manifest.yaml v2 vs repository)"
python "$PKG/migrate.py" oldrefs --pkg "$PKG" > "$S/oldrefs.out" 2>&1; chk $? "oldrefs (no ERROR/STALE)"; tail -1 "$S/oldrefs.out"
[ "$(sha256sum gtt-domain/.frozen | cut -d' ' -f1)" = "$FROZEN_BEFORE" ]; chk $? "gtt-domain/.frozen byte-identical (sha256 $FROZEN_BEFORE)"
[ ! -e .frozen ] && [ ! -e gtt ]; chk $? "old .frozen and the whole old gtt/ directory are gone"
for d in context adr proposals docs; do [ ! -e $d ] || bad "old root directory still present: $d"; done; ok "no old root directory (context adr proposals docs) remains"
grep -q '^- Status: Accepted' gtt-domain/adr/ADR-004-gtt-domain-and-dot-gtt-engine.md; chk $? "ADR-004 Accepted after 'yes'"
grep -q '^- Status: Accepted' gtt-domain/adr/ADR-003-scaffold-restructure.md; chk $? "ADR-003 still Accepted, untouched"
[ "$(sha_lf gtt-domain/adr/ADR-003-scaffold-restructure.md)" = "$(sha_lf "$R/adr/ADR-003-scaffold-restructure.md")" ]; chk $? "ADR-003 byte-identical to the real repo's"
[ "$(sha_lf gtt-domain/adr/ADR-001-context-governance.md)" = "$(sha_lf "$R/adr/ADR-001-context-governance.md")" ]; chk $? "ADR-001 untouched"
grep -c '^| .* | ADR-004 |' gtt-domain/context/stack.md | grep -q '^1$'; chk $? "stack.md change-log row for ADR-004 present exactly once"
grep -c '^| .* | ADR-003 |' gtt-domain/context/stack.md | grep -q '^1$'; chk $? "stack.md change-log row for ADR-003 still present exactly once"
python - "$R/gtt/index/artifacts.json" .gtt/index/artifacts.json <<'E'
import json,os,sys
b={e["id"]:e for e in json.load(open(sys.argv[1],encoding="utf-8"))["artifacts"]}
raw=json.load(open(sys.argv[2],encoding="utf-8"))["artifacts"]
a={e["id"]:e for e in raw}
lost=[i for i in b if i not in a]
deact=[i for i in b if i in a and b[i].get("status","active")=="active" and a[i].get("status","active")!="active"]
new=[i for i in a if i not in b]
ids=[e["id"] for e in raw]
nofile=[i for i,e in a.items() if e.get("status","active")=="active" and not os.path.isfile(e["path"])]
moved_ok=all(b[i]["path"] in a[i].get("history",[]) for i in b if i in a and b[i].get("status","active")=="active" and a[i]["path"]!=b[i]["path"])
print("  identities before/after:",len(b),len(a),"| lost:",lost,"| deactivated:",deact,"| new:",new,"| dup ids:",len(ids)-len(set(ids)),"| active w/o file:",nofile,"| history kept:",moved_ok)
sys.exit(0 if not lost and set(deact)=={"PROP-ADR-DRAFT-GTT-DOMAIN-AND-DOT-GTT-ENGINE"} and set(new)=={"ADR-004"} and len(ids)==len(set(ids)) and not nofile and moved_ok else 1)
E
chk $? "identities: none lost; only the consumed ADR draft retired; only ADR-004 new; no duplicates; old path kept in history"
find . -name __pycache__ -not -path './.git/*' | grep -q . && bad "__pycache__ present: $(find . -name __pycache__ -not -path './.git/*' | head -3 | tr '\n' ' ')" || ok "no __pycache__ anywhere in the tree"
find . -not -path './.git/*' \( -name '*.pyc' -o -name '*.bak' -o -name '*.orig' -o -name '*.rej' \) | grep -q . && bad "temp/bytecode files present" || ok "no temporary or bytecode files in the tree"

echo "  -- functional checks: every engine component at its new path"
grep -q '^frozen (' gtt-domain/session.md; chk $? "gtt-status reports frozen from gtt-domain/.frozen"
bash .gtt/scripts/gtt-session-context.sh > "$S/sctx.out" 2>&1; chk $? "gtt-session-context.sh runs"
grep -q 'GTT-SESSION-CONTEXT' "$S/sctx.out" && grep -q 'precedence: gtt-domain/context/' "$S/sctx.out"; chk $? "session context header names the new L0 location"
bash .gtt/scripts/gtt-freeze.sh > "$S/freeze_post.out" 2>&1; echo $? > "$S/freeze_post.rc"
[ "$(cat "$S/freeze_pre.rc")" = "$(cat "$S/freeze_post.rc")" ] && [ "$(cat "$S/freeze_post.rc")" = 2 ]; chk $? "gtt-freeze.sh still refuses an already-frozen project (exit $(cat "$S/freeze_post.rc"), same as before)"
[ "$(sha256sum gtt-domain/.frozen | cut -d' ' -f1)" = "$FROZEN_BEFORE" ]; chk $? "...and it did not touch the marker"
bash .gtt/scripts/gtt-query.sh "scaffold" > "$S/query.out" 2>&1; chk $? "gtt-query.sh answers from .gtt/index/"
bash .gtt/scripts/gtt-reconcile.sh > "$S/recon_dry.out" 2>&1; chk $? "gtt-reconcile.sh dry-run clean (nothing moved unreconciled)"
bash .gtt/scripts/gtt-check-backlog.sh >/dev/null 2>&1; chk $? "gtt-check-backlog reads gtt-domain/backlog.md by default"
bash .gtt/scripts/gtt-check-backlog.sh gtt-domain/backlog.md >/dev/null 2>&1; chk $? "gtt-check-backlog with an explicit path"
# GTTGuard end to end at the new registry path
mkdir -p src; printf '# @GTTGuard reason="rehearsal"\ndef locked():\n    return 1\n\n\ndef free():\n    return 2\n' > src/guarded.py
bash .gtt/scripts/gtt-guard-sync.sh >/dev/null 2>&1; grep -q 'src/guarded.py' .gtt/protection/registry.yaml; chk $? "guard-sync registers a marker into .gtt/protection/registry.yaml"
bash .gtt/scripts/gtt-check-protection.sh >/dev/null 2>&1; chk $? "check-protection agrees with the regenerated registry"
gh() { printf '{"tool_name":"Edit","tool_input":{"file_path":"%s","old_string":"%s"}}' "$PWD/src/guarded.py" "$1" | python .claude/hooks/protect-guard.py >/dev/null 2>&1; echo $?; }
[ "$(gh 'return 1')" = 2 ]; chk $? "protect-guard.py blocks an edit of the protected symbol (registry read from .gtt/)"
[ "$(gh 'return 2')" = 0 ]; chk $? "protect-guard.py leaves the unprotected neighbour editable"
# a host project's own docs/ and context/ are no longer excluded from the marker scan
mkdir -p docs context; printf '# @GTTGuard\ndef host_docs():\n    return 1\n' > docs/host.py; printf '# @GTTGuard\ndef host_ctx():\n    return 1\n' > context/host.py
bash .gtt/scripts/gtt-guard-sync.sh >/dev/null 2>&1; grep -q 'docs/host.py' .gtt/protection/registry.yaml && grep -q 'context/host.py' .gtt/protection/registry.yaml; chk $? "a host project's own docs/ and context/ ARE scanned now (ADR-004: no name collision)"
mkdir -p gtt-domain/proposals/x; printf '# @GTTGuard\ndef ignored():\n    return 1\n' > gtt-domain/proposals/x/ignored.py
bash .gtt/scripts/gtt-guard-sync.sh >/dev/null 2>&1; ! grep -q 'ignored.py' .gtt/protection/registry.yaml; chk $? "gtt-domain/ is excluded from the marker scan"
rm -rf src docs/host.py context gtt-domain/proposals/x; rmdir docs 2>/dev/null
bash .gtt/scripts/gtt-guard-sync.sh >/dev/null 2>&1; bash .gtt/scripts/gtt-check-protection.sh >/dev/null 2>&1; chk $? "registry back to empty and consistent"
# hooks other than the two protection hooks
echo '{"tool_name":"Write","tool_input":{"file_path":"'"$PWD"'/gtt-domain/context/stack.md"}}' | $PYX .claude/hooks/detect-drift.py > "$S/drift.out" 2>&1; chk $? "detect-drift.py runs (post-tool hook)"
echo '{}' | $PYX .claude/hooks/notify-change-request.py > "$S/notify.out" 2>&1; chk $? "notify-change-request.py runs"
# a filled-in change request must be noticed at its new location
cp gtt-domain/change-request.md "$S/cr.bak"
sed -i -E 's/^(Change|Reason|Trigger|Scope|Impact|Risk|Priority): <.*>$/\1: filled in/' gtt-domain/change-request.md
echo '{}' | $PYX .claude/hooks/notify-change-request.py > "$S/notify2.out" 2>&1; grep -qi 'change-request' "$S/notify2.out"; chk $? "notify-change-request.py notices a filled-in gtt-domain/change-request.md"
cp "$S/cr.bak" gtt-domain/change-request.md
bash .gtt/scripts/gtt-run-python.sh .claude/hooks/session-start.py > "$S/ss.out" 2>&1; chk $? "session-start.py runs through .gtt/scripts/gtt-run-python.sh (the settings.json command)"
grep -q 'GTT SESSION MEMORY' "$S/ss.out"; chk $? "session-start delivers the session memory"
python - <<'E'
import json
s=json.load(open(".claude/settings.json",encoding="utf-8"))
cmd=s["hooks"]["SessionStart"][0]["hooks"][0]["command"]
deny=s["permissions"]["deny"]
ok=cmd.startswith("bash .gtt/scripts/") and "Edit(/gtt-domain/change-request.md)" in deny and "Write(/gtt-domain/change-request.md)" in deny and not any(d.endswith("(/change-request.md)") for d in deny)
print("  settings.json:", cmd, "|", [d for d in deny if "change-request" in d])
import sys; sys.exit(0 if ok else 1)
E
chk $? "settings.json: SessionStart command and static deny follow the new layout"
grep -q '^@../gtt-domain/context/constraints.md' .claude/CLAUDE.md; chk $? ".claude/CLAUDE.md imports @../gtt-domain/context/constraints.md"
[ -f gtt-domain/context/constraints.md ] && [ "$(sha_lf gtt-domain/context/constraints.md)" != "$(grep '^constraints ' "$S/l0_before.txt" | cut -d' ' -f2)" ]; chk $? "the import target exists (constraints.md, updated by ADR-004)"
echo "  hook smoke (post-migration hook, MSYS paths):"
HH=0; h() { printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "$1" "$2" | python .claude/hooks/protect-l0.py >/dev/null 2>&1; echo $?; }
[ "$(h Write "$PWD/gtt-domain/context/stack.md")" = 2 ] || HH=1; [ "$(h Edit "$PWD/gtt-domain/adr/ADR-001-context-governance.md")" = 2 ] || HH=1
[ "$(h Write "$PWD/gtt-domain/change-request.md")" = 2 ] || HH=1; [ "$(h Write "$PWD/.claude/settings.json")" = 2 ] || HH=1
[ "$(h Write "$PWD/gtt-domain/proposals/PROPOSAL-x.md")" = 0 ] || HH=1; [ "$(h Write "$PWD/src/context/example.ts")" = 0 ] || HH=1
[ "$(h Write "$PWD/.gtt/docs/usage.md")" = 0 ] || HH=1
chk $HH "orchestrator's hook smoke test cases"
python "$H/hooktest.py" > "$S/hooktest.out" 2>&1; chk $? "full hook battery (Windows/MSYS paths, PowerShell, Bash, pre-freeze): $(tail -1 "$S/hooktest.out")"
grep -E '^FAIL' "$S/hooktest.out" | head
python "$H/posix_hook_test.py" "$R/proposals/gtt-domain-migration/overlay/claude-hooks/protect-l0.py" > "$S/posix.out" 2>&1; chk $? "hook on a POSIX root + NT regression: $(tail -1 "$S/posix.out")"
cmp -s .claude/hooks/protect-l0.py "$R/proposals/gtt-domain-migration/overlay/claude-hooks/protect-l0.py"; chk $? "installed hook == staged overlay"
cp .claude/hooks/protect-l0.py "$S/hook_final.py"

echo; echo "=================== S2  'no' at ratification -> full rollback ==================="
fresh rh2; BEFORE=$(snap); FZ=$(sha256sum .frozen | cut -d' ' -f1); STAT=$(git status --porcelain --untracked-files=all | sort); ST_BEFORE=$(git diff --cached --name-only | wc -l)
stage_from_real; BACKUP=$STAGE/backup.tar; FROZEN_BEFORE=$FZ
tar --exclude=./.git -cf "$BACKUP" .
python "$PKG/migrate.py" apply --pkg "$PKG" >/dev/null 2>&1; chk $? "migration applied (pre-ratification state)"
[ -d gtt-domain/context ] && [ ! -d context ] && [ -d .gtt/scripts ] && [ ! -d gtt ]; chk $? "tree is in the migrated state"
( . "$ROLLBACK_SRC"; rollback ) > "$S/rb2.out" 2>&1; RC=$?
[ $RC -eq 1 ]; chk $? "rollback exits 1 ($RC)"
[ "$(snap)" = "$BEFORE" ]; chk $? "every file identical to before (sha of the whole tree)"
[ "$(git status --porcelain --untracked-files=all | sort)" = "$STAT" ]; chk $? "git status identical to before"
[ "$(git diff --cached --name-only | wc -l)" = "$ST_BEFORE" ]; chk $? "index restored (nothing staged by the migration)"
[ "$(sha256sum .frozen | cut -d' ' -f1)" = "$FZ" ] && [ ! -e gtt-domain ] && [ ! -e .gtt ]; chk $? ".frozen restored byte-identical; neither .gtt/ nor gtt-domain/ left behind"
grep -q 'Restored. .frozen is identical' "$S/rb2.out"; chk $? "rollback reports the freeze marker identical"

echo; echo "=================== S3  failure inside the migration -> rollback ==================="
fresh rh3
python - <<'E'
p="AGENTS.md"; t=open(p,encoding="utf-8",newline="").read()
a="The scaffold has four layers, and the layout keeps them apart:"
assert a in t
open(p,"w",encoding="utf-8",newline="").write(t.replace(a,"The scaffold has four layers (drift), and the layout keeps them apart:"))
E
git add AGENTS.md >/dev/null 2>&1; git commit -qm "drift" >/dev/null 2>&1
BEFORE=$(snap); FZ=$(sha256sum .frozen | cut -d' ' -f1); STAT=$(git status --porcelain --untracked-files=all | sort)
stage_from_real; BACKUP=$STAGE/backup.tar; FROZEN_BEFORE=$FZ; tar --exclude=./.git -cf "$BACKUP" .
python "$PKG/migrate.py" preflight --pkg "$PKG" >/dev/null 2>&1; chk $? "preflight passes (drift is not visible to it)"
python "$PKG/migrate.py" apply --pkg "$PKG" > "$S/apply3.out" 2>&1; RC=$?
[ $RC -ne 0 ]; chk $? "apply fails on the mismatching patch (exit $RC): $(tail -1 "$S/apply3.out" | cut -c1-90)"
( . "$ROLLBACK_SRC"; rollback ) > "$S/rb3.out" 2>&1
[ "$(snap)" = "$BEFORE" ]; chk $? "rollback: tree identical to before the failed apply"
[ "$(git status --porcelain --untracked-files=all | sort)" = "$STAT" ]; chk $? "rollback: git status identical"
[ "$(sha256sum .frozen | cut -d' ' -f1)" = "$FZ" ]; chk $? "rollback: .frozen identical"

echo; echo "=================== S4  L0 changes while the ratification prompt waits ==================="
fresh rh4; stage_from_real; BACKUP=$STAGE/backup.tar; FROZEN_BEFORE=$(sha256sum .frozen | cut -d' ' -f1); BEFORE=$(snap); tar --exclude=./.git -cf "$BACKUP" .
python "$PKG/migrate.py" apply --pkg "$PKG" >/dev/null 2>&1
grep -E '^  "gtt-domain/context/' "$ADRPKG/apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh" > "$S/changes.txt"
echo "tamper" >> gtt-domain/context/glossary.md          # someone edits L0 between the first check and 'yes'
CAUGHT=1; while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; [ "$(sha_lf "$t")" = "$w" ] || CAUGHT=0; done < "$S/changes.txt"
[ $CAUGHT = 0 ]; chk $? "re-check detects the changed file before anything is written"
[ ! -e gtt-domain/adr/ADR-004-gtt-domain-and-dot-gtt-engine.md ]; chk $? "nothing was written (no ADR-004, staged drafts not copied)"
( . "$ROLLBACK_SRC"; rollback ) >/dev/null 2>&1
[ "$(snap)" = "$BEFORE" ]; chk $? "orchestrator rollback afterwards restores everything"

echo; echo "=================== S5  baseline failure shows its output ==================="
fresh rh5
python - <<'E'
import re
p="backlog.md"
t=open(p,encoding="utf-8",newline="").read()
m=re.search(r"^##### (STORY-\d+)[^\n]*\n",t,re.M)
t=t.replace(m.group(0), m.group(0)+"\n"+m.group(0), 1)
open(p,"w",encoding="utf-8",newline="").write(t)
E
git add -A >/dev/null 2>&1; git commit -qm "dup story" >/dev/null 2>&1
eval "$(sed -n '/^BASELINE_OUT=/,/^pass_names "\$BASELINE_OUT"/p' "$ORCH" | sed '$d' | sed 's/^  exit 1$/  echo "[would exit 1]"/')" 2>&1 | tee "$S/s5.out" | tail -8
grep -q 'FAIL' "$S/s5.out"; chk $? "the failing check's FAIL line is printed (not sent to /dev/null)"
STAGE=$(mktemp -d)

echo; echo "=================== S6  the ADR script refuses the pre-migration layout ==================="
fresh rh6; BEFORE=$(snap)
( bash "$S/rh6/proposals/apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh" < /dev/null > "$S/s6.out" 2>&1 ); RC=$?
[ $RC -eq 2 ] && grep -q 'migrated layout' "$S/s6.out"; chk $? "apply-ADR-004 (run inside the throw-away copy) refuses before the migration (exit $RC)"
[ "$(snap)" = "$BEFORE" ] && [ -d context ] && [ ! -e gtt-domain ]; chk $? "tree untouched by the refused run"

echo; echo "=================== S7  CRLF preflight ==================="
fresh rh7; stage_from_real
python - <<'E'
p="gtt/scripts/gtt-freeze.sh"; b=open(p,"rb").read(); open(p,"wb").write(b.replace(b"\n",b"\r\n"))
E
git add -A >/dev/null 2>&1; git commit -qm crlf >/dev/null 2>&1
python "$PKG/migrate.py" preflight --pkg "$PKG" > "$S/s7.out" 2>&1; RC=$?
[ $RC -ne 0 ] && grep -q 'CRLF line endings in gtt/scripts.gtt-freeze.sh' "$S/s7.out"; chk $? "preflight rejects and names the file: $(head -1 "$S/s7.out" | cut -c1-110)"

echo; echo "=================== S8  idempotent re-run on a migrated tree ==================="
cd "$S/rh1" || exit 1
python "$PKG/migrate.py" preflight --pkg "$PKG" > "$S/s8.out" 2>&1; RC=$?
[ $RC -eq 3 ] && grep -q 'already migrated' "$S/s8.out"; chk $? "preflight on the migrated copy: 'already migrated', exit 3"
BEFORE=$(snap); python "$PKG/migrate.py" apply --pkg "$PKG" > "$S/s8b.out" 2>&1; RC=$?
[ $RC -eq 0 ] && [ "$(snap)" = "$BEFORE" ]; chk $? "apply on the migrated copy is a no-op (exit $RC, tree identical)"

echo; echo "=================== S9  the migration never touches the real repository ==================="
cd "$R" || exit 1
[ -d context ] && [ -d adr ] && [ -f .frozen ] && [ ! -e .gtt ] && [ ! -e gtt-domain ] && [ -d gtt/scripts ]; chk $? "real repo still in the ADR-003 layout (no .gtt/, no gtt-domain/)"
[ "$(sha256sum .frozen | cut -d' ' -f1)" = "715ce1435f127639b1e0570f74c0f5ac392987310c4d5210b6b10cb8e1b12782" ]; chk $? "real .frozen sha256 unchanged"

echo; echo "RESULT: PASS=$PASS FAIL=$FAILN"
