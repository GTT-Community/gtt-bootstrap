#!/usr/bin/env bash
# Full logical rehearsal on a DISPOSABLE COPY of the real working tree.
# It reuses the orchestrator's own code blocks (extracted with sed) wherever that does not
# amount to running the promotion scripts, and replicates the rest command for command.
# Scenarios: S1 success, S2 'no' at ratification, S3 injected failure, S4 L0 changes while
# waiting (D4), S5 baseline failure output, S7 CRLF preflight.
export PYTHONDONTWRITEBYTECODE=1
S=/c/Users/Haibu/AppData/Local/Temp/claude/C--griott-GTT-gtt-bootstrap/9af2a6e4-ddc1-46d8-8681-13b8934f4ae7/scratchpad
R=/c/griott/GTT/gtt-bootstrap
ORCH=$R/gtt/proposals/apply-scaffold-restructure.sh
ADR=$R/gtt/proposals/apply-ADR-003-scaffold-restructure.sh
PASS=0; FAILN=0
ok()   { echo "  PASS  $*"; PASS=$((PASS+1)); }
bad()  { echo "  FAIL  $*"; FAILN=$((FAILN+1)); }
chk()  { if [ "$1" = "0" ]; then ok "$2"; else bad "$2"; fi; }

sha_lf() { tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1; }
snap() {  # sha of every file outside .git + git status + frozen
  find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1
}
pass_names() { grep -E '^PASS' "$1" | sed -E 's/[[:space:]]+\[.*$//; s/[[:space:]]+$//' | sort; }

# The orchestrator's own rollback function, verbatim (used by S2/S3/S4)
ROLLBACK_SRC="$S/rollback_fn.sh"
sed -n '/^rollback() {/,/^}/p' "$ORCH" > "$ROLLBACK_SRC"

fresh() { bash $S/mkcopy.sh "$1" >/dev/null 2>&1; cd "$S/$1" || exit 1; }

stage_from_real() {  # what the orchestrator's re-exec does
  STAGE=$(mktemp -d); cp -r gtt/proposals/scaffold-restructure "$STAGE/pkg"; mkdir "$STAGE/adr"
  for f in ADR-DRAFT-scaffold-restructure.md apply-ADR-003-scaffold-restructure.sh context-architecture-adr-003.md context-glossary-adr-003.md context-principles-adr-003.md context-solution-vision-adr-003.md context-stack-adr-003.md; do cp gtt/proposals/$f "$STAGE/adr/$f"; done
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

migrate_and_check_l0() {
  python "$PKG/migrate.py" apply --pkg "$PKG" > "$S/apply.out" 2>&1; return $?
}

echo "=================== S1  success path (real manifest) ==================="
fresh rh1
BEFORE_SNAP=$(snap); FROZEN_BEFORE=$(sha256sum gtt/.frozen | cut -d' ' -f1)
identity_dump gtt/index/artifacts.json > "$S/id_before.txt"
for f in architecture constraints glossary principles solution-vision stack; do echo "$f $(sha_lf gtt/context/$f.md)"; done > "$S/l0_before.txt"
stage_from_real
python "$PKG/migrate.py" preflight --pkg "$PKG" >/dev/null; chk $? "migrate preflight ok on the copy (incl. CRLF scan)"
preflight_blocks "$ADRPKG" ; chk $? "orchestrator STALE_L0 + DIRTY blocks pass (real code)"
bash gtt/scripts/gtt-validate.sh > "$S/base.out" 2>&1; chk $? "baseline gtt-validate exit 0"
pass_names "$S/base.out" > "$S/base.txt"
BACKUP=$STAGE/backup.tar; tar --exclude=./.git -cf "$BACKUP" . && tar -tf "$BACKUP" >/dev/null; chk $? "backup created and readable"
python "$PKG/migrate.py" apply --pkg "$PKG" > "$S/apply.out" 2>&1; chk $? "migrate apply (moves+rewrite; L0 text untouched)"
tail -2 "$S/apply.out"
# L0 hashes after migration must equal the ORIGINAL hashes (text untouched)
ALLSAME=0; while read -r f h; do [ "$(sha_lf context/$f.md)" = "$h" ] || ALLSAME=1; done < "$S/l0_before.txt"
chk $ALLSAME "L0 files moved with text untouched (hashes == original) BEFORE ratification"
# ---- ratification effects, replicating the ADR script (incl. D4 re-check)
grep -E '^  "context/' "$ADRPKG/apply-ADR-003-scaffold-restructure.sh" > "$S/changes.txt"
BADH=0; while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; [ "$(sha_lf "$t")" = "$w" ] || BADH=1; done < "$S/changes.txt"
chk $BADH "ADR script pre-prompt hash check passes (5/5)"
BADH=0; while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; [ "$(sha_lf "$t")" = "$w" ] || BADH=1; done < "$S/changes.txt"
chk $BADH "D4 re-check after 'yes' passes (5/5)"
cp "$ADRPKG/ADR-DRAFT-scaffold-restructure.md" adr/ADR-003-scaffold-restructure.md
grep -q '^- Status: Proposed' adr/ADR-003-scaffold-restructure.md; chk $? "ADR-003 is Proposed before the stamp (not Accepted early)"
awk -v st="- Status: Accepted" -v ap="- Approved by: Solution Designer (Rehearsal) - ratified on $(date -u +%Y-%m-%d)" '/^- Status: /&&!s{print st;s=1;next} /^- Approved by: /&&!a{print ap;a=1;next}{print}' adr/ADR-003-scaffold-restructure.md > "$S/adr.new"; cp "$S/adr.new" adr/ADR-003-scaffold-restructure.md
while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; cp "$ADRPKG/$s" "$t"; done < "$S/changes.txt"
bash gtt/scripts/gtt-check-stack.sh > "$S/stack.out" 2>&1; chk $? "gtt-check-stack (ADR cited in the map exists)"
rm -f "proposals/ADR-DRAFT-scaffold-restructure.md"
# L0 after ratification must equal the staged drafts
SAME=0; while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; [ "$(sha_lf "$t")" = "$(sha_lf "$ADRPKG/$s")" ] || SAME=1; done < "$S/changes.txt"
chk $SAME "L0 after ratification == staged full drafts (hash by hash)"
[ "$(sha_lf context/constraints.md)" = "$(grep '^constraints ' "$S/l0_before.txt" | cut -d' ' -f2)" ]; chk $? "context/constraints.md untouched"
# ---- D1: identity of the consumed draft
python - <<'E'
import json
d=json.load(open("gtt/index/artifacts.json",encoding="utf-8"))
e=[x for x in d["artifacts"] if x["id"]=="PROP-ADR-DRAFT-SCAFFOLD-RESTRUCTURE"]
print("  (draft identity registered in the real manifest:", bool(e), "path:", e[0]["path"] if e else None, ")")
E
bash gtt/scripts/gtt-index.sh > "$S/idx_without.out" 2>&1; echo "  (without reconcile, gtt-index exit=$?  <- the D1 failure)"
bash gtt/scripts/gtt-reconcile.sh --apply --retire PROP-ADR-DRAFT-SCAFFOLD-RESTRUCTURE > "$S/reconcile.out" 2>&1; chk $? "D1 fix: reconcile --apply --retire exits 0"
bash gtt/scripts/gtt-index.sh > "$S/idx.out" 2>&1; chk $? "gtt-index after reconcile"
bash gtt/scripts/gtt-guard-sync.sh >/dev/null 2>&1; chk $? "gtt-guard-sync"
bash gtt/scripts/gtt-status.sh >/dev/null 2>&1; chk $? "gtt-status (session.md)"
bash gtt/scripts/gtt-index.sh >/dev/null 2>&1
bash gtt/scripts/gtt-check-integrity.sh > "$S/integ.out" 2>&1; chk $? "gtt-check-integrity"; tail -1 "$S/integ.out"
bash gtt/scripts/gtt-check-protection.sh >/dev/null 2>&1; chk $? "gtt-check-protection"
bash gtt/scripts/gtt-check-session-adapter.sh claude >/dev/null 2>&1; chk $? "gtt-check-session-adapter claude"
bash gtt/scripts/gtt-check-markdown.sh >/dev/null 2>&1; chk $? "gtt-check-markdown"
bash gtt/scripts/gtt-validate.sh > "$S/after.out" 2>&1; chk $? "gtt-validate after"
pass_names "$S/after.out" > "$S/after.txt"
[ -z "$(comm -23 "$S/base.txt" "$S/after.txt")" ]; chk $? "no check that passed at baseline regressed ($(wc -l < "$S/after.txt") PASS vs $(wc -l < "$S/base.txt"))"
grep -E 'SKIPPED|CANNOT' "$S/after.out" | cut -c1-60
python "$PKG/migrate.py" verify --pkg "$PKG" >/dev/null 2>&1; chk $? "migrate verify (manifest.yaml vs repository)"
python "$PKG/migrate.py" oldrefs --pkg "$PKG" > "$S/oldrefs.out" 2>&1; chk $? "oldrefs (no ERROR/STALE)"; tail -1 "$S/oldrefs.out"
[ "$(sha256sum .frozen | cut -d' ' -f1)" = "$FROZEN_BEFORE" ]; chk $? ".frozen byte-identical (sha256 $FROZEN_BEFORE)"
[ ! -e gtt/.frozen ]; chk $? "old gtt/.frozen gone"
grep -q '^- Status: Accepted' adr/ADR-003-scaffold-restructure.md; chk $? "ADR-003 Accepted after 'yes'"
# identity verification
identity_dump gtt/index/artifacts.json > "$S/id_after.txt"
python - "$S/id_before.txt" "$S/id_after.txt" <<'E'
import sys
def load(p):
    d={}
    for l in open(p,encoding="utf-8"):
        i,s,path=l.rstrip("\n").split(" ",2); d[i]=(s,path)
    return d
b,a=load(sys.argv[1]),load(sys.argv[2])
lost=[i for i in b if i not in a]
flip=[i for i in b if i in a and b[i][0]=="active" and a[i][0]!="active"]
new=[i for i in a if i not in b]
ids=[l.split()[0] for l in open(sys.argv[2],encoding="utf-8")]
dups=len(ids)-len(set(ids))
import os
missing=[i for i,(s,p) in a.items() if s=="active" and not os.path.isfile(p)]
print("  identities before/after:",len(b),len(a),"| lost:",lost,"| deactivated:",flip,"| new:",new,"| dup ids:",dups,"| active w/o file:",missing)
sys.exit(1 if lost or dups or missing or set(flip)-{"PROP-ADR-DRAFT-SCAFFOLD-RESTRUCTURE"} else 0)
E
chk $? "artifact identities: none lost, no duplicates, every active id has its file; only the consumed draft retired"
# leftovers
find . -name __pycache__ -not -path './.git/*' | grep -q . && bad "__pycache__ present: $(find . -name __pycache__ -not -path './.git/*' | head -3 | tr '\n' ' ')" || ok "no __pycache__ anywhere in the tree"
find . -not -path './.git/*' \( -name '*.pyc' -o -name '*.bak' -o -name '*.orig' -o -name '*.gtt-restructure-tmp' -o -name '*.rej' \) | grep -q . && bad "temp/bytecode files present" || ok "no temporary or bytecode files in the tree"
[ ! -e gtt/proposals ] && ok "old gtt/proposals removed"|| bad "gtt/proposals still exists"
[ ! -e proposals/ADR-DRAFT-scaffold-restructure.md ] && ok "moved ADR draft consumed (not left as an applied draft)" || bad "ADR draft left in proposals/"
git status --short --ignored | grep -E '^!!' | head -3
echo "  hook smoke (post-migration hook, 6 cases):"
H=0
h() { printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "$1" "$2" | python .claude/hooks/protect-l0.py >/dev/null 2>&1; echo $?; }
[ "$(h Write "$PWD/context/stack.md")" = 2 ] || H=1; [ "$(h Edit "$PWD/adr/ADR-001-context-governance.md")" = 2 ] || H=1
[ "$(h Write "$PWD/change-request.md")" = 2 ] || H=1; [ "$(h Write "$PWD/.claude/settings.json")" = 2 ] || H=1
[ "$(h Write "$PWD/proposals/PROPOSAL-x.md")" = 0 ] || H=1; [ "$(h Write "$PWD/src/context/example.ts")" = 0 ] || H=1
chk $H "orchestrator's hook smoke test (MSYS paths)"
cp .claude/hooks/protect-l0.py "$S/hook_final.py"

echo; echo "=================== S2  'no' at ratification -> full rollback ==================="
fresh rh2; BEFORE=$(snap); FZ=$(sha256sum gtt/.frozen | cut -d' ' -f1); STAT=$(git status --porcelain --untracked-files=all | sort); ST_BEFORE=$(git diff --cached --name-only | wc -l)
stage_from_real; BACKUP=$STAGE/backup.tar; FROZEN_BEFORE=$FZ
tar --exclude=./.git -cf "$BACKUP" .
python "$PKG/migrate.py" apply --pkg "$PKG" >/dev/null 2>&1; chk $? "migration applied (pre-ratification state)"
[ -d context ] && [ ! -d gtt/context ]; chk $? "tree is in the migrated state"
# the operator answered 'no' -> the ADR script exits 1 -> ERR trap -> rollback() (verbatim function)
( . "$ROLLBACK_SRC"; rollback ) > "$S/rb2.out" 2>&1; RC=$?
[ $RC -eq 1 ]; chk $? "rollback exits 1 ($RC)"
[ "$(snap)" = "$BEFORE" ]; chk $? "every file identical to before (sha of the whole tree)"
[ "$(git status --porcelain --untracked-files=all | sort)" = "$STAT" ]; chk $? "git status identical to before"
[ "$(git diff --cached --name-only | wc -l)" = "$ST_BEFORE" ]; chk $? "index restored (nothing staged by the migration)"
[ "$(sha256sum gtt/.frozen | cut -d' ' -f1)" = "$FZ" ] && [ ! -e .frozen ]; chk $? ".frozen restored byte-identical at gtt/.frozen"
grep -q 'Restored. gtt/.frozen is identical' "$S/rb2.out"; chk $? "rollback reports the freeze marker identical"

echo; echo "=================== S3  failure inside the migration -> rollback ==================="
fresh rh3
# commit a change to AGENTS.md in the copy so the tree stays clean but the exact-text patches no longer match
python - <<'E'
p="AGENTS.md"; t=open(p,encoding="utf-8",newline="").read()
t=t.replace("Tool-specific integration directories remain at their required locations.","Tool-specific integration directories remain at their required locations. (drift)")
open(p,"w",encoding="utf-8",newline="").write(t)
E
git add AGENTS.md >/dev/null 2>&1; git commit -qm "drift" >/dev/null 2>&1
BEFORE=$(snap); FZ=$(sha256sum gtt/.frozen | cut -d' ' -f1); STAT=$(git status --porcelain --untracked-files=all | sort)
stage_from_real; BACKUP=$STAGE/backup.tar; FROZEN_BEFORE=$FZ; tar --exclude=./.git -cf "$BACKUP" .
python "$PKG/migrate.py" preflight --pkg "$PKG" >/dev/null 2>&1; chk $? "preflight passes (drift is not visible to it)"
python "$PKG/migrate.py" apply --pkg "$PKG" > "$S/apply3.out" 2>&1; RC=$?
[ $RC -ne 0 ]; chk $? "apply fails on the mismatching patch (exit $RC): $(tail -1 "$S/apply3.out" | cut -c1-90)"
( . "$ROLLBACK_SRC"; rollback ) > "$S/rb3.out" 2>&1
[ "$(snap)" = "$BEFORE" ]; chk $? "rollback: tree identical to before the failed apply"
[ "$(git status --porcelain --untracked-files=all | sort)" = "$STAT" ]; chk $? "rollback: git status identical"
[ "$(sha256sum gtt/.frozen | cut -d' ' -f1)" = "$FZ" ]; chk $? "rollback: .frozen identical"

echo; echo "=================== S4  L0 changes while the ratification prompt waits (D4) ==================="
fresh rh4; stage_from_real; BACKUP=$STAGE/backup.tar; FROZEN_BEFORE=$(sha256sum gtt/.frozen | cut -d' ' -f1); BEFORE=$(snap); tar --exclude=./.git -cf "$BACKUP" .
python "$PKG/migrate.py" apply --pkg "$PKG" >/dev/null 2>&1
grep -E '^  "context/' "$ADRPKG/apply-ADR-003-scaffold-restructure.sh" > "$S/changes.txt"
echo "tamper" >> context/glossary.md          # someone edits L0 between the first check and 'yes'
CAUGHT=1; while IFS= read -r line; do line="${line#  \"}"; line="${line%\"}"; IFS='|' read -r t s w <<<"$line"; [ "$(sha_lf "$t")" = "$w" ] || CAUGHT=0; done < "$S/changes.txt"
[ $CAUGHT = 0 ]; chk $? "D4 re-check detects the changed file before anything is written"
[ ! -e adr/ADR-003-scaffold-restructure.md ]; chk $? "nothing was written (no ADR-003, staged drafts not copied)"
( . "$ROLLBACK_SRC"; rollback ) >/dev/null 2>&1
[ "$(snap)" = "$BEFORE" ]; chk $? "orchestrator rollback afterwards restores everything"

echo; echo "=================== S5  baseline failure shows its output (improvement 1) ==================="
fresh rh5
python - <<'E'
import re
t=open("backlog.md",encoding="utf-8",newline="").read() if False else open("gtt/backlog.md",encoding="utf-8",newline="").read()
m=re.search(r"^##### (STORY-\d+)[^\n]*\n",t,re.M)
t=t.replace(m.group(0), m.group(0)+"\n"+m.group(0), 1)
open("gtt/backlog.md","w",encoding="utf-8",newline="").write(t)
E
git add -A >/dev/null 2>&1; git commit -qm "dup story" >/dev/null 2>&1
eval "$(sed -n '/^BASELINE_OUT=/,/^pass_names "\$BASELINE_OUT"/p' "$ORCH" | sed '$d' | sed 's/^  exit 1$/  echo "[would exit 1]"/')" 2>&1 | tee "$S/s5.out" | tail -8
grep -q 'FAIL' "$S/s5.out"; chk $? "the failing check's FAIL line is printed (not sent to /dev/null)"
STAGE=$(mktemp -d)

echo; echo "=================== S7  CRLF preflight (improvement 2) ==================="
fresh rh7; stage_from_real
python - <<'E'
p="gtt/scripts/gtt-freeze.sh"; b=open(p,"rb").read(); open(p,"wb").write(b.replace(b"\n",b"\r\n"))
E
git add -A >/dev/null 2>&1; git commit -qm crlf >/dev/null 2>&1
python "$PKG/migrate.py" preflight --pkg "$PKG" > "$S/s7.out" 2>&1; RC=$?
[ $RC -ne 0 ] && grep -q 'CRLF line endings in gtt/scripts.gtt-freeze.sh' "$S/s7.out"; chk $? "preflight rejects and names the file: $(head -1 "$S/s7.out" | cut -c1-110)"

echo; echo "RESULT: PASS=$PASS FAIL=$FAILN"
