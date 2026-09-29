#!/usr/bin/env bash
# Disposable copy of the REAL working tree (incl. .git, uncommitted state, real identity
# manifest, staged package). Everything the rehearsal does happens in the copy.
S=/c/Users/Haibu/AppData/Local/Temp/claude/C--griott-GTT-gtt-bootstrap/9af2a6e4-ddc1-46d8-8681-13b8934f4ae7/scratchpad
R=/c/griott/GTT/gtt-bootstrap
NAME="${1:-rh}"
rm -rf "$S/$NAME"
mkdir -p "$S/$NAME"
( cd "$R" && tar -cf - . ) | ( cd "$S/$NAME" && tar -xf - )
cd "$S/$NAME" || exit 1
git config user.email t@t; git config user.name "Rehearsal"
# make the copy's remote-tracking ref self-contained (no network is ever used)
echo "copy: $S/$NAME  HEAD=$(git rev-parse --short HEAD)  origin/main=$(git rev-parse --short origin/main 2>/dev/null)"
echo "dirty (expected: SESSION, index, 1 script):"; git status --short | head -6
