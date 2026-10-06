#!/usr/bin/env bash
# GTT - Git pre-commit hook: the first control every ADE shares.
#
# An ADE's own hooks differ, and most are unverified. Git is the same for all
# of them: whatever agent or person made the change, it reaches the repository
# through a commit. This installs a pre-commit hook that runs observation
# (gtt-observe.sh check) so that the only things that stop a commit are the ones
# the governed state says must stop - a boundary ratified as BLOCKING, or an
# observation the human rejected. Everything else is recorded and the commit
# goes through: this is not an approval step.
#
# It is the first shared control, not the guaranteed one: a local pre-commit
# hook is skipped by `git commit --no-verify`. The guaranteed layer is CI -
# gtt-validate.sh and gtt-check-stack.sh on the pull request. Where an ADE has a
# pre-tool hook, GTT denies an agent that bypass while this hook is installed.
#
# Installing or removing it is the human's choice: nothing does it for them, and
# an agent never runs `install --apply` or `remove --apply`. It never replaces a
# pre-commit hook GTT did not write.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-git-hook.sh status
#   .gtt/scripts/gtt-git-hook.sh install [--apply]     # a dry run without --apply
#   .gtt/scripts/gtt-git-hook.sh remove  [--apply]
#
# Exit 0 = ok, 1 = conflict (a hook GTT did not write is in the way), 2 = cannot run.

set -euo pipefail

MARK="# gtt-git-hook: installed by .gtt/scripts/gtt-git-hook.sh"
CMD="${1:-status}"
APPLY="${2:-}"

GITDIR="$(git rev-parse --git-dir 2>/dev/null)" || { echo "gtt-git-hook: not a Git repository." >&2; exit 2; }
[ -d .gtt ] || { echo "gtt-git-hook: run from the project root (no .gtt/ directory here)." >&2; exit 2; }
HOOK="$GITDIR/hooks/pre-commit"

ours() { [ -f "$HOOK" ] && grep -qF "$MARK" "$HOOK"; }

case "$CMD" in
  status)
    if ours; then echo "installed: $HOOK runs gtt-observe.sh check before each commit."
    elif [ -f "$HOOK" ]; then echo "not installed: $HOOK exists and is not GTT's."
    else echo "not installed."; fi
    ;;
  install)
    if [ -f "$HOOK" ] && ! ours; then
      echo "gtt-git-hook: $HOOK already exists and GTT did not write it - not replaced." >&2
      echo "              Add this line to it yourself:  bash .gtt/scripts/gtt-observe.sh check || exit 1" >&2
      exit 1
    fi
    echo "INSTALL  $HOOK  (runs: bash .gtt/scripts/gtt-observe.sh check)"
    if [ "$APPLY" != "--apply" ]; then echo "(dry run - nothing written; re-run with --apply)"; exit 0; fi
    mkdir -p "$GITDIR/hooks"
    cat > "$HOOK" <<EOF
#!/usr/bin/env bash
$MARK
# Stops a commit only on what the governed state says must stop (a BLOCKING
# boundary, or an observation the human rejected). Remove with:
#   bash .gtt/scripts/gtt-git-hook.sh remove --apply
if [ ! -f .gtt/scripts/gtt-observe.sh ]; then
  echo "gtt pre-commit: .gtt/scripts/gtt-observe.sh is missing - this commit was NOT checked against the frozen design." >&2
  exit 0
fi
bash .gtt/scripts/gtt-observe.sh check || exit 1
EOF
    chmod +x "$HOOK"
    echo "gtt-git-hook: installed."
    ;;
  remove)
    if ! ours; then echo "gtt-git-hook: no GTT pre-commit hook to remove."; exit 0; fi
    echo "REMOVE   $HOOK"
    if [ "$APPLY" != "--apply" ]; then echo "(dry run - nothing written; re-run with --apply)"; exit 0; fi
    rm -f "$HOOK"
    echo "gtt-git-hook: removed."
    ;;
  *)
    echo "usage: gtt-git-hook.sh status | install [--apply] | remove [--apply]" >&2
    exit 2
    ;;
esac
