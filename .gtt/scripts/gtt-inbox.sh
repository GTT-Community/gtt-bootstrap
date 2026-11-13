#!/usr/bin/env bash
# GTT - Inbox: one pipeline for everything that asks the design to change. A thin wrapper: the logic is in gtt_inbox.py.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-inbox.sh add "<text>" | --file PATH [--now] [--apply]                       (human) F1
#   .gtt/scripts/gtt-inbox.sh add --type solicitud --change "..." --reason "..." [--apply]        (human) F2
#   .gtt/scripts/gtt-inbox.sh adr-new "<title>" [--file PATH] [--apply]                           (human) F4
#   .gtt/scripts/gtt-inbox.sh adr-adopt gtt-domain/adr/ADR-NNN-x.md [--apply]                     (human) F5
#   .gtt/scripts/gtt-inbox.sh propose --file DRAFT --level arch|spec|scope|non-goal --form N [--origin IDEA-n] [--apply]
#   .gtt/scripts/gtt-inbox.sh supersede PROP-n --file DRAFT --level L --form N [--apply]
#   .gtt/scripts/gtt-inbox.sh triage IDEA-n --result work|covered|spec|arch|scope|non-goal|ask|incorporated --to REF [--apply]
#   .gtt/scripts/gtt-inbox.sh park|reopen|reject|drop REF [--apply] | priority REF urgent|normal|low [--apply]   (human)
#   .gtt/scripts/gtt-inbox.sh migrate [--apply]                                                  (human) 1.22 -> 1.23, called by gtt update
#   .gtt/scripts/gtt-inbox.sh reconcile [--session] [--json] [--dry-run] | adr-hand [--json]      (deterministic, no model; writes what the repo shows)
#   .gtt/scripts/gtt-inbox.sh list [--json] [--all] [--origin human|agent] | show REF [--json] | transitions [--json]
#
# Every act that changes something is a dry run until --apply. Exit 0 = ok, 1 = refused, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_inbox.py" "$@"
