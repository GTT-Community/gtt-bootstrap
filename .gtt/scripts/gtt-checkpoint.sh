#!/usr/bin/env bash
# GTT - checkpoint. Refreshes the derived session state when the work changed.
#
# A checkpoint is never a commit. It regenerates gtt-domain/session.md (through
# gtt-status.sh) and notes, locally, the state it did that for. An ADE's end-of-turn
# hook calls it, so the next session - in any ADE - starts from what the repository
# says and not from a conversation.
#
# If HEAD and `git status` are what they were at the last checkpoint, it does nothing
# and returns at once. It never stages, commits, branches, tags or stashes, and it
# always exits 0: a checkpoint that could fail would get in the way of the work.
#
# Usage (from anywhere inside the project):
#   .gtt/scripts/gtt-checkpoint.sh [--quiet]

set -uo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

cd "$(dirname "$0")/../.." || exit 0
NOTE=".gtt/local/checkpoint.json"

HEAD_AT="$(git rev-parse --verify --quiet HEAD 2>/dev/null || echo none)"
# session.md is what a checkpoint rewrites: it is left out, or every checkpoint would call for another.
STATE="$HEAD_AT:$(git status --porcelain -- . ':(exclude)gtt-domain/session.md' 2>/dev/null | cksum | tr -d ' ')"

if [ -f "$NOTE" ] && grep -qF "\"state\": \"$STATE\"" "$NOTE" 2>/dev/null; then
  exit 0
fi

[ -f .gtt/scripts/gtt-status.sh ] && bash .gtt/scripts/gtt-status.sh >/dev/null 2>&1

mkdir -p .gtt/local 2>/dev/null || exit 0
[ -f .gtt/local/.gitignore ] || printf '# Local GTT state: never committed.\n*\n' > .gtt/local/.gitignore
printf '{\n  "schema": 1,\n  "head": "%s",\n  "state": "%s",\n  "at": "%s"\n}\n' \
  "$HEAD_AT" "$STATE" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "$NOTE" 2>/dev/null

[ "$QUIET" -eq 1 ] || echo "gtt-checkpoint: session state refreshed (gtt-domain/session.md). Nothing was committed."
exit 0
