#!/usr/bin/env bash
# Post-mortem of the smoke test, on the disposable copy rh_user (read-only apart from the
# project's own check scripts). The real repository is only READ (reference hashes).
export PYTHONDONTWRITEBYTECODE=1
S=/c/Users/Haibu/AppData/Local/Temp/claude/C--griott-GTT-gtt-bootstrap/9af2a6e4-ddc1-46d8-8681-13b8934f4ae7/scratchpad
R=/c/griott/GTT/gtt-bootstrap
cd "$S/rh_user" || exit 1
PASS=0; FAILN=0
ok()  { echo "  PASS  $*"; PASS=$((PASS+1)); }
bad() { echo "  FAIL  $*"; FAILN=$((FAILN+1)); }
chk() { if [ "$1" = "0" ]; then ok "$2"; else bad "$2"; fi; }
sha_lf() { tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1; }

echo "== 1. structure (Engine / Governance / Docs / ADE overlay)"
for d in context adr proposals docs gtt/scripts gtt/index gtt/protection gtt/session-adapters gtt/scaffold .claude .kiro .copilot; do [ -d "$d" ] || bad "missing dir $d"; done; ok "layer directories present"
for f in backlog.md change-request.md session.md .frozen AGENTS.md readme-gtt.md readme-gtt.es.md .gitignore gtt/scaffold/manifest.yaml docs/index.md docs/installation.md docs/installation.es.md docs/usage.md docs/usage.es.md docs/gtt-completion.md docs/evidence.md docs/docs.md docs/session-adapter-contract.md; do [ -f "$f" ] || bad "missing file $f"; done; ok "governance/docs/entry-point files present at their new paths"
OLD=0; for p in gtt/context gtt/adr gtt/proposals gtt/docs gtt/.frozen gtt/backlog.md gtt/CHANGE-REQUEST.md gtt/SESSION.md gtt/INDEX.md gtt/INSTALLATION.md gtt/USAGE.md gtt/GTT-COMPLETION.md gtt/EVIDENCE.md README-GTT.md README-GTT.es.md; do ls -d "$p" >/dev/null 2>&1 && { echo "    old path still present: $p"; OLD=1; }; done
# case-insensitive FS: README-GTT.md would resolve to readme-gtt.md, so check the real spelling
[ "$(ls | grep -c '^README-GTT')" = "0" ] || OLD=1
chk $OLD "no old-layout path remains (incl. real spelling of README-GTT*)"
echo "  gtt/ now holds: $(ls gtt | tr '\n' ' ')"
echo "  root now holds: $(ls -A | grep -v '^.git$' | tr '\n' ' ')"

echo "== 2. .frozen"
WANT=715ce1435f127639b1e0570f74c0f5ac392987310c4d5210b6b10cb8e1b12782
[ "$(sha256sum .frozen | cut -d' ' -f1)" = "$WANT" ]; chk $? ".frozen sha256 == pre-migration value"
[ "$(sha256sum "$R/gtt/.frozen" | cut -d' ' -f1)" = "$WANT" ]; chk $? "real repo's gtt/.frozen has the same bytes (reference)"
cat .frozen | head -2

echo "== 3. L0 (context/) and ADR-003"
BAD=0
for n in architecture glossary principles solution-vision stack; do
  [ "$(sha_lf context/$n.md)" = "$(sha_lf proposals/context-$n-adr-003.md)" ] || { echo "    differs from staged draft: $n"; BAD=1; }
done; chk $BAD "5 changed L0 files == their staged full drafts (hash by hash)"
[ "$(sha_lf context/constraints.md)" = "$(sha_lf $R/gtt/context/constraints.md)" ]; chk $? "context/constraints.md == real repo's original (untouched)"
sed -n 1,9p adr/ADR-003-scaffold-restructure.md | cut -c1-150
grep -q '^- Status: Accepted$' adr/ADR-003-scaffold-restructure.md; chk $? "ADR-003 Status: Accepted"
grep -q '^- Approved by: Solution Designer (Rehearsal) - ratified by executing apply-ADR-003-scaffold-restructure.sh on ' adr/ADR-003-scaffold-restructure.md; chk $? "Approved by stamped by the ratification (git user + date)"
[ ! -e proposals/ADR-DRAFT-scaffold-restructure.md ]; chk $? "ADR draft consumed (not left as an applied draft)"
grep -c '^| .* | ADR-003 |' context/stack.md | grep -q '^1$'; chk $? "stack.md change-log row for ADR-003 present exactly once"
grep -q '^| Scaffold |' context/glossary.md; chk $? "glossary has the Scaffold term"
[ "$(sha_lf adr/ADR-001-context-governance.md)" = "$(sha_lf $R/gtt/adr/ADR-001-context-governance.md)" ]; chk $? "ADR-001 untouched"
grep -c 'ADR-003' context/stack.md | head -1 >/dev/null

echo "== 4. artifact identities (real manifest 'before' vs the copy 'after')"
python - "$R/gtt/index/artifacts.json" gtt/index/artifacts.json <<'E'
import json,os,sys
b={e["id"]:e for e in json.load(open(sys.argv[1],encoding="utf-8"))["artifacts"]}
a={e["id"]:e for e in json.load(open(sys.argv[2],encoding="utf-8"))["artifacts"]}
lost=[i for i in b if i not in a]
deact=[i for i in b if i in a and b[i].get("status","active")=="active" and a[i].get("status","active")!="active"]
new=[i for i in a if i not in b]
ids=[e["id"] for e in json.load(open(sys.argv[2],encoding="utf-8"))["artifacts"]]
nofile=[i for i,e in a.items() if e.get("status","active")=="active" and not os.path.isfile(e["path"])]
moved_ok=all(b[i]["path"] in a[i].get("history",[]) for i in b if i in a and b[i].get("status","active")=="active" and a[i]["path"]!=b[i]["path"])
print("  before/after:",len(b),len(a),"| lost:",lost,"| deactivated:",deact,"| new:",new,"| duplicate ids:",len(ids)-len(set(ids)),"| active without file:",nofile,"| old path kept in history for every moved artifact:",moved_ok)
sys.exit(0 if not lost and set(deact)=={"PROP-ADR-DRAFT-SCAFFOLD-RESTRUCTURE"} and set(new)=={"ADR-003"} and len(ids)==len(set(ids)) and not nofile and moved_ok else 1)
E
chk $? "identities: none lost, only the consumed draft retired, only ADR-003 new, no duplicates, history kept"

echo "== 5. validations (re-run independently in the copy)"
bash gtt/scripts/gtt-check-integrity.sh 2>&1 | tail -1
bash gtt/scripts/gtt-check-integrity.sh >/dev/null 2>&1; chk $? "gtt-check-integrity"
bash gtt/scripts/gtt-check-protection.sh >/dev/null 2>&1; chk $? "gtt-check-protection"
for a in claude codex copilot kiro; do bash gtt/scripts/gtt-check-session-adapter.sh $a >/dev/null 2>&1; chk $? "gtt-check-session-adapter $a"; done
bash gtt/scripts/gtt-check-markdown.sh >/dev/null 2>&1; chk $? "gtt-check-markdown"
bash gtt/scripts/gtt-check-backlog.sh >/dev/null 2>&1; chk $? "gtt-check-backlog"
bash gtt/scripts/gtt-check-stack.sh >/dev/null 2>&1; chk $? "gtt-check-stack"
bash gtt/scripts/gtt-validate.sh > "$S/v_smoke.out" 2>&1; chk $? "gtt-validate"; grep -E 'SKIPPED|CANNOT|FAIL' "$S/v_smoke.out" | cut -c1-70
python proposals/scaffold-restructure/migrate.py verify >/dev/null 2>&1; chk $? "migrate verify (gtt/scaffold/manifest.yaml vs repository)"
python proposals/scaffold-restructure/migrate.py oldrefs > "$S/or_smoke.out" 2>&1; chk $? "oldrefs"; tail -1 "$S/or_smoke.out"
python - <<'E'
import re
t=open("gtt/scaffold/manifest.yaml",encoding="utf-8").read()
print("  manifest entries:",len(re.findall(r"^\s*-\s*\{",t,re.M)),"| version line:",re.search(r"^\s*version:.*$",t,re.M).group(0).strip())
E
bash gtt/scripts/gtt-query.sh "scaffold" 2>/dev/null | head -2 | cut -c1-120
bash gtt/scripts/gtt-session-context.sh >/dev/null 2>&1; chk $? "session memory service regenerates session.md (gtt-session-context.sh)"
grep -q '^frozen (' session.md; chk $? "session.md reports frozen"; sed -n 12,14p session.md

echo "== 6. protection hook installed in the copy"
h() { printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "$1" "$2" | python .claude/hooks/protect-l0.py >/dev/null 2>&1; echo $?; }
[ "$(h Write "$PWD/context/stack.md")" = 2 ] && [ "$(h Write "$PWD/adr/x.md")" = 2 ] && [ "$(h Write "$PWD/change-request.md")" = 2 ] && [ "$(h Write "$PWD/src/context/a.ts")" = 0 ] && [ "$(h Write "$PWD/proposals/x.md")" = 0 ]; chk $? "hook: governed paths denied, host code and proposals/ allowed"
cmp -s .claude/hooks/protect-l0.py "$R/gtt/proposals/scaffold-restructure/overlay/claude-hooks/protect-l0.py"; chk $? "installed hook == staged overlay (D3 version)"
grep -q '/change-request.md' .claude/settings.json && ! grep -q 'gtt/CHANGE-REQUEST' .claude/settings.json; chk $? "settings.json static deny points at /change-request.md"

echo "== 7. leftovers"
find . -name __pycache__ -not -path './.git/*' | grep -q . && bad "__pycache__: $(find . -name __pycache__ -not -path './.git/*' | tr '\n' ' ')" || ok "no __pycache__ anywhere"
find . -not -path './.git/*' \( -name '*.pyc' -o -name '*.bak' -o -name '*.orig' -o -name '*.rej' -o -name '*.gtt-restructure-tmp' \) | grep -q . && bad "temp/bytecode files" || ok "no temp/bytecode files in the tree"
[ ! -d gtt/proposals ] && ok "gtt/proposals gone" || bad "gtt/proposals present"
git status --short --ignored | grep '^!!' | head -3
echo "  git status summary (the copy): $(git status --short | cut -c1-2 | sort | uniq -c | tr '\n' ' ')"
echo "  staged renames: $(git diff --cached --name-status -M | grep -c '^R')"
tail -14 docs/gtt-completion.md | head -12
echo "  temp dir kept by design: $(ls -d /tmp/tmp.QLwazpyFAr 2>/dev/null) -> $(ls /tmp/tmp.QLwazpyFAr 2>/dev/null | tr '\n' ' ')"
tar -tf /tmp/tmp.QLwazpyFAr/backup.tar >/dev/null 2>&1; chk $? "backup archive present and readable"

echo "== 8. the REAL repository was not touched by the smoke test"
cd "$R" && [ -e gtt/context/stack.md ] && [ ! -e context ] && [ ! -e adr ] && [ -e gtt/.frozen ] && [ ! -e .frozen ]; chk $? "real repo still in the pre-migration layout"
echo "  real git status lines: $(git status --short | wc -l)"

echo; echo "SMOKE VERIFICATION: PASS=$PASS FAIL=$FAILN"
