@../AGENTS.md

## Claude Code specifics

Use these skills instead of improvising the format:

| Situation | Skill |
|---|---|
| First time populating `gtt/context/`, or `gtt/context/` still holds template placeholders | `gtt-bootstrap` |
| "process the change request" | `gtt-propose-change` |
| Architectural or context change needed | `gtt-propose-change` |
| A change was approved and needs recording | `gtt-adr` |
| Verify the governed context still matches the code | `gtt-audit` |
| `gtt/backlog.md` needs an Epic/Story added, removed, or materially changed | `gtt-propose-change` (form 4) |
| Reconcile `gtt/backlog.md` against defined Epics/Stories | `gtt-audit` |

`gtt/context/`, `gtt/adr/`, `gtt/CHANGE-REQUEST.md`, and `SOURCE-BRIEF.*`
are blocked at the permission layer and by a PreToolUse hook. A denial there
is the system working as designed — write to `gtt/proposals/` instead, and
never look for another way to reach a blocked path. `gtt/backlog.md` is not
blocked the same way — routine Story status/focus updates are direct edits;
only structural changes go through the flow above (see `AGENTS.md` →
*Backlog governance*).

Hard constraints, always in context:

@../gtt/context/constraints.md
