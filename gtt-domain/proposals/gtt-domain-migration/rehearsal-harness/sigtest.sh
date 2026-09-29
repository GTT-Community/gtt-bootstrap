#!/usr/bin/env bash
# Interruption tests. The parent uses the orchestrator's REAL rollback() function and its REAL
# trap lines (extracted with sed); the "child" stands for the ratification prompt (blocking).
# The migration step is the real migrate.py. Everything runs in disposable copies.
export PYTHONDONTWRITEBYTECODE=1
set -m      # job control: background jobs keep SIGINT enabled, as in an interactive terminal
S="${GTT_REHEARSAL_DIR:-${TMPDIR:-/tmp}/gtt-rehearsal}"; mkdir -p "$S"
R="${GTT_REPO:-/c/griott/GTT/gtt-bootstrap}"
H="$R/proposals/gtt-domain-migration/rehearsal-harness"
ORCH="$R/proposals/apply-gtt-domain-migration.sh"
sed -n '/^rollback() {/,/^}/p' "$ORCH" > "$S/rollback_fn.sh"
sed -n '/^trap rollback/p' "$ORCH" > "$S/trap_lines.sh"
echo "trap lines under test:"; cat "$S/trap_lines.sh"
snap() { find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1; }
PASS=0; FAILN=0
ok()  { echo "  PASS  $*"; PASS=$((PASS+1)); }
bad() { echo "  FAIL  $*"; FAILN=$((FAILN+1)); }

cat > "$S/child_block.sh" <<'E'
echo $$ > "$SIG_DIR/child.pid"
exec sleep 300
E

cat > "$S/parent_mock.sh" <<'E'
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
echo $$ > "$SIG_DIR/parent.pid"
STAGE=$(mktemp -d); cp -r proposals/gtt-domain-migration "$STAGE/pkg"
BACKUP="$STAGE/backup.tar"
tar --exclude=./.git -cf "$BACKUP" .
FROZEN_BEFORE="$(sha256sum .frozen | cut -d' ' -f1)"
. "$SIG_DIR/rollback_fn.sh"
. "$SIG_DIR/trap_lines.sh"
python "$STAGE/pkg/migrate.py" apply --pkg "$STAGE/pkg" > "$SIG_DIR/apply.out" 2>&1
: > "$SIG_DIR/migrated.marker"
bash "$SIG_DIR/child_block.sh"           # the ratification prompt
echo "REACHED-THE-END-WITHOUT-ROLLBACK" > "$SIG_DIR/end.marker"
E

run_case() {  # <name> <how>
  local name="$1" how="$2"
  echo; echo "--- $name"
  GTT_REHEARSAL_DIR="$S" GTT_REPO="$R" bash "$H/mkcopy.sh" sig >/dev/null 2>&1; cd "$S/sig" || exit 1
  export SIG_DIR="$S/sigdir"; rm -rf "$SIG_DIR"; mkdir -p "$SIG_DIR"; cp "$S/rollback_fn.sh" "$S/trap_lines.sh" "$S/child_block.sh" "$S/parent_mock.sh" "$SIG_DIR/"
  local BEFORE FZ; BEFORE=$(snap); FZ=$(sha256sum .frozen | cut -d' ' -f1)
  bash "$SIG_DIR/parent_mock.sh" > "$SIG_DIR/parent.out" 2>&1 &
  local PP=$!
  for i in $(seq 1 120); do [ -e "$SIG_DIR/child.pid" ] && break; sleep 1; done
  [ -e "$SIG_DIR/child.pid" ] || { bad "$name: migration did not reach the blocking step"; return; }
  [ -d gtt-domain/context ] && [ -d .gtt/scripts ] && ok "$name: interrupted while the tree was in the migrated state" || bad "$name: tree was not migrated at the blocking step"
  local PARENT CHILD; PARENT=$(cat "$SIG_DIR/parent.pid"); CHILD=$(cat "$SIG_DIR/child.pid")
  case "$how" in
    int-both)   kill -INT "$CHILD"; kill -INT "$PARENT" ;;
    int-parent) kill -INT "$PARENT"; sleep 2; kill -TERM "$CHILD" ;;
    term-parent) kill -TERM "$PARENT"; sleep 2; kill -TERM "$CHILD" ;;
    hup-parent)  kill -HUP "$PARENT"; sleep 2; kill -TERM "$CHILD" ;;
    child-dies)  kill -INT "$CHILD" ;;
  esac
  for i in $(seq 1 60); do kill -0 "$PP" 2>/dev/null || break; sleep 1; done
  kill -0 "$PP" 2>/dev/null && { kill -9 "$PP" 2>/dev/null; bad "$name: parent still running after 60s"; return; }
  wait "$PP" 2>/dev/null; local RC=$?
  cd "$S/sig"
  [ ! -e "$SIG_DIR/end.marker" ] && ok "$name: the run did not continue past the interruption (exit $RC)" || bad "$name: continued to the end"
  [ "$(snap)" = "$BEFORE" ] && ok "$name: tree identical to the pre-migration state" || bad "$name: tree differs after rollback"
  [ "$(sha256sum .frozen | cut -d' ' -f1)" = "$FZ" ] && [ ! -e gtt-domain ] && [ ! -e .gtt ] && ok "$name: .frozen restored byte-identical; no .gtt/ or gtt-domain/ left" || bad "$name: .frozen not restored / leftovers"
  grep -q "restoring the pre-migration state" "$SIG_DIR/parent.out" && ok "$name: rollback message printed" || bad "$name: no rollback message"
}

run_case "Ctrl-C (SIGINT to prompt and orchestrator)" int-both
run_case "SIGINT to the orchestrator only" int-parent
run_case "SIGTERM to the orchestrator" term-parent
run_case "SIGHUP (terminal closed)" hup-parent
run_case "the ratification prompt dies by SIGINT (ERR path)" child-dies
echo; echo "SIGNALS RESULT: PASS=$PASS FAIL=$FAILN"
