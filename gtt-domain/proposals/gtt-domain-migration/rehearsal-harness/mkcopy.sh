#!/usr/bin/env bash
# Disposable copy of the REAL working tree (incl. .git, uncommitted state, real identity
# manifest, staged package). Everything the rehearsal does happens in the copy.
#   GTT_REHEARSAL_DIR  where copies live (default: a temp dir)   GTT_REPO  the real repository
S="${GTT_REHEARSAL_DIR:-${TMPDIR:-/tmp}/gtt-rehearsal}"
R="${GTT_REPO:-/c/griott/GTT/gtt-bootstrap}"
NAME="${1:-rh}"
rm -rf "$S/$NAME"
mkdir -p "$S/$NAME"
( cd "$R" && tar -cf - . ) | ( cd "$S/$NAME" && tar -xf - )
cd "$S/$NAME" || exit 1
git config user.email t@t; git config user.name "Rehearsal"
echo "copy: $S/$NAME  HEAD=$(git rev-parse --short HEAD)"
