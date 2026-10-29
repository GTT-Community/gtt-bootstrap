> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

@../AGENTS.md

## Claude Code specifics

Use these skills instead of improvising the format:

| Situation | Skill |
|---|---|
| First time populating `gtt-domain/context/`, or `gtt-domain/context/` still holds template placeholders | `gtt-bootstrap` |
| "process the change request" | `gtt-propose-change` |
| Architectural or context change needed | `gtt-propose-change` |
| A change was approved and needs recording | `gtt-adr` |
| Verify the governed context still matches the code | `gtt-audit` |
| Ordinary work: implementing, refactoring, testing, writing and closing Stories | none - do it; nobody approves it (`AGENTS.md` → *The two planes*) |
| An Epic must be added, removed, or its goal or scope materially changed | `gtt-propose-change` (form 4) |
| The ratified development method (Method Lock) must change | `gtt-propose-change` (form 6) - never `gtt-method.sh select`, which is refused after the freeze |
| Observation reported drift (`@gtt · Observation`, or the user asks whether a change contradicts the design) | `gtt-drift-response` |
| Reconcile `gtt-domain/backlog.md` against defined Epics/Stories | `gtt-audit` |
| Mark/unmark a file, class, or method as GTTGuard-protected | `gtt-guard` |
| A change is requested to a GTTGuard-protected artifact | `gtt-propose-change` (form 5) |

`gtt-domain/change-request.md` and `SOURCE-BRIEF.*` are always blocked, at the
permission layer and by a PreToolUse hook; `gtt-domain/context/` and
`gtt-domain/adr/` are writable before the freeze (the `gtt-bootstrap` skill
writes them) and blocked by the hook once `gtt-domain/.frozen` exists. A denial
there is the system working as designed — write to `gtt-domain/proposals/` instead, and
never look for another way to reach a blocked path. `gtt-domain/backlog.md` is not
blocked: Stories are your working plan and you edit them freely; only an Epic's
goal and scope are the human's decision (see `AGENTS.md` → *Backlog*).

A shell or MCP command that reaches the frozen design, the freeze or the
protection itself anyway (through a `cd`, a variable, a script, a promotion run
under another spelling) is caught by `governed-sentinel.py` after it runs: it is
put back, what the command wrote is archived under
`gtt-domain/proposals/withdrawn/`, and you are told. Take it as a denial.

The `gtt` CLI's human acts (`promote`, `undo`, `freeze`, `change`, `proposals
withdraw`, `clean`...) are denied to you too, `--yes` included: give the human
the exact command; in Claude Code they can type it after `!` in the prompt.

After a write, `detect-drift.py` runs the observation engine
(`.gtt/scripts/gtt-observe.sh`). What it hands you is a signal, not an order to
stop: say it in one line and continue, unless a line says STOP. Accepting,
rejecting or deferring an observation, and freezing, are the human's.

A GTTGuard-protected file/class/method is a separate, live-resolved block by
a different PreToolUse hook (`protect-guard.py`), driven by
`.gtt/protection/registry.yaml` rather than a fixed path list. A denial there
is the same kind of signal — use `gtt-propose-change` (form 5), never look
for another way in. `.claude/hooks/` and `.claude/settings.json` are
themselves machinery and permission-denied like any other governance file;
if a change needs to land there, stage it under `gtt-domain/proposals/` and tell
the Solution Designer to move it into place.

When you speak on behalf of GTT — a question the method needs answered, a
confirmation or choice, the Initial Design Questionnaire, a proposal, a
finding, a request for authorization, a report — open the message with
`@gtt · <what this is>` (for example `@gtt · Autonomy Profile`,
`@gtt · Initial Design Questionnaire`, `@gtt · Report`). Ordinary work GTT
did not raise carries no marker. The marker says who is speaking; it is
never a decision, an approval or evidence. See `AGENTS.md` → *Working
without unnecessary interruption*.

Hard constraints, always in context:

@../gtt-domain/context/constraints.md
