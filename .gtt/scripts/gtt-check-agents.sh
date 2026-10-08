#!/usr/bin/env bash
# GTT - agent contract gate.
#
# Some ADEs read only the beginning of AGENTS.md: Codex caps project docs at 32 KiB
# and cuts the rest without saying so. An ADE with no pre-write hook has nothing but
# these instructions in real time, so the whole contract must fit in what every ADE
# reads, with the rules first.
#
# Fails when:
#   - AGENTS.md is larger than 24 KiB (room is left for nested AGENTS.md files, which
#     Codex adds to the same budget);
#   - `## Non-negotiable rules` starts after the first 8 KiB;
#   - one of the governance sections is missing;
#   - a section points at a detail file under .gtt/docs/agents/ that does not exist.
#
# Usage:
#   .gtt/scripts/gtt-check-agents.sh [<file>]     # default: AGENTS.md
#
# Exit 0 = pass, 1 = violation, 2 = cannot determine.

set -uo pipefail

FILE="${1:-AGENTS.md}"
MAX=24576
RULES_BY=8192

if [ ! -f "$FILE" ]; then
  echo "gtt-check-agents: cannot determine - $FILE not found." >&2
  exit 2
fi

FAIL=0
SIZE="$(wc -c < "$FILE" | tr -d ' ')"
if [ "$SIZE" -gt "$MAX" ]; then
  echo "gtt-check-agents: FAILED - $FILE is $SIZE bytes, over the $MAX-byte cap." >&2
  echo "  An ADE that reads only the beginning of the file (Codex: 32 KiB, shared with nested files) loses the rest." >&2
  echo "  Keep the rules here and move detail to .gtt/docs/agents/, leaving the section heading and a pointer." >&2
  FAIL=1
fi

while IFS= read -r section; do
  offset="$(LC_ALL=C grep -b -m1 -x -F -- "## $section" "$FILE" | cut -d: -f1)"
  if [ -z "$offset" ]; then
    echo "gtt-check-agents: FAILED - $FILE has no section \`## $section\`." >&2
    FAIL=1
  elif [ "$section" = "Non-negotiable rules" ] && [ "$offset" -gt "$RULES_BY" ]; then
    echo "gtt-check-agents: FAILED - \`## $section\` starts at byte $offset of $FILE, after the first $RULES_BY bytes." >&2
    FAIL=1
  fi
done <<'SECTIONS'
Non-negotiable rules
Human Promotion Boundary
Governed regime
Protected context
Conflict policy
Change requests
SECTIONS

while IFS= read -r pointed; do
  [ -z "$pointed" ] && continue
  if [ ! -f "$pointed" ]; then
    echo "gtt-check-agents: FAILED - $FILE points at $pointed, which does not exist." >&2
    FAIL=1
  fi
done < <(LC_ALL=C grep -o '^In `\.gtt/docs/agents/[^`]*`' "$FILE" | sed 's/^In `//; s/`$//' | sort -u)

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
echo "gtt-check-agents: OK - $FILE is $SIZE bytes (cap $MAX), rules first, every pointed file present."
