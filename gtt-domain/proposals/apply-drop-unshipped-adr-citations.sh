#!/usr/bin/env bash
# GTT - PROMOTION SCRIPT (human execution required)
#
# Status: Draft - not a decision. Prepared by an agent; never run by one.
#
# Proposal: drop the citations of ADRs the product does not ship (ADR-003,
# ADR-004) from two files that are write-protected for agents:
#
#   .claude/skills/gtt-bootstrap/SKILL.md   one line of prose
#   .claude/hooks/protect-l0.py             three lines of the module docstring
#
# Text and comments only: no behaviour changes, no governed context is touched,
# no ADR is needed. It prints the exact diff and asks before writing. Every
# anchor is checked first: if a file is not what this script expects, nothing is
# written. If the second file cannot be written, the first is restored.
#
# Usage (from the project root):
#   bash gtt-domain/proposals/apply-drop-unshipped-adr-citations.sh
#
# Once it has run, delete this script: the product ships with no pending proposal.

set -euo pipefail

[ -f .claude/skills/gtt-bootstrap/SKILL.md ] && [ -f .claude/hooks/protect-l0.py ] \
  || { echo "run from the project root: the gtt-bootstrap skill or protect-l0.py not found" >&2; exit 2; }

echo "=================================================================="
echo " GTT promotion: drop unshipped ADR citations   (HUMAN EXECUTION)"
echo "=================================================================="

exec python3 - <<'PY'
import difflib
import os
import sys

SKILL = ".claude/skills/gtt-bootstrap/SKILL.md"
HOOK = ".claude/hooks/protect-l0.py"

EDITS = {
    SKILL: [
        ("- layout of ADR-003 (v2.1 after the scaffold restructure, before ADR-004): the Engine in",
         "- v2.1 layout after the scaffold restructure, before the move to `.gtt/` and `gtt-domain/`: the Engine in"),
    ],
    HOOK: [
        ("change-request.md (in gtt-domain/ since ADR-004), and\n",
         "change-request.md (in gtt-domain/), and\n"),
        ("Root-anchored paths (ADR-004): the governed directories moved from the\n"
         "project root (ADR-003) to gtt-domain/context/ and gtt-domain/adr/, and\n",
         "Root-anchored paths: the governed directories moved from the\n"
         "project root to gtt-domain/context/ and gtt-domain/adr/, and\n"),
    ],
}


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


old, new = {}, {}
for path, edits in EDITS.items():
    old[path] = text = read(path)
    for before, after in edits:
        if text.count(before) != 1:
            sys.exit(f"REFUSED: {path} is not what this script expects "
                     f"(anchor found {text.count(before)} time(s), expected 1):\n  {before.strip()[:90]}\n"
                     "Nothing was written.")
        text = text.replace(before, after)
    new[path] = text

for path in EDITS:
    print()
    sys.stdout.writelines(difflib.unified_diff(old[path].splitlines(True), new[path].splitlines(True),
                                               path, path + " (proposed)"))

print()
try:
    with open("/dev/tty") as tty:
        sys.stdout.write("Type 'apply' to write these two files (anything else aborts): ")
        sys.stdout.flush()
        answer = tty.readline().strip()
except OSError:
    sys.exit("no terminal to confirm on - nothing was written.")
if answer != "apply":
    sys.exit("aborted - nothing was written.")


def write(path, text):
    mode = os.stat(path).st_mode
    tmp = path + ".gtt-tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


done = []
try:
    for path in EDITS:
        write(path, new[path])
        done.append(path)
except OSError as exc:
    for path in done:
        write(path, old[path])
    sys.exit(f"failed writing ({exc}) - every file was restored; nothing changed.")

for path in done:
    print(f"written: {path}")
print("Next: bash .gtt/scripts/gtt-maintain.sh")
print("Then delete gtt-domain/proposals/apply-drop-unshipped-adr-citations.sh - it has done its job.")
PY
