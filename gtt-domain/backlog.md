# Project Backlog

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> The project's development line. It holds two kinds of entry, and they are
> not governed alike: **Epics** are intent and scope — the human approves
> them; **Stories** are the working plan of whoever does the work — the ADE
> writes and runs them on its own. This is a planning artifact, not
> architecture: see *Precedence* below.

**Last verified:** `<date>` — run the `gtt-audit` skill to reconcile against defined requirements.

---

## Development Line

<what phase, release, or milestone this backlog currently represents — one or two sentences. Leave empty rather than inventing one.>

## Precedence

```text
Governed Context / L0
        v
ADR / governed decisions
        v
Epics (approved intent and scope)
        v
Stories (the working plan)
        v
Implementation work
```

If a Story appears to contradict governed context or an accepted ADR, that
is a finding, not a resolution. Raise it through `gtt-domain/change-request.md` —
a Story never silently overrides architecture.

---

## Epics and Stories

**An Epic is governed.** It says what is wanted and where it stops: its
`Goal`, its `Scope` and its `Out of Scope`. The human approves it —
`**Approved:** who — YYYY-MM-DD` — and only then does it leave `Proposed`.
Adding or removing an Epic, or materially changing its goal or scope, is the
human's decision.

**A Story is not governed.** Stories are how the work inside an approved
Epic is organised. The ADE creates them, splits them, rewrites them,
implements them and closes them without asking — nobody approves a Story.
What keeps Stories honest is not a signature but observation
(`.gtt/scripts/gtt-observe.sh`): if the work crosses a boundary of the
frozen design, GTT reports it, whatever the Story said.

A Story is worth writing when it helps the next session pick the work up:
what it delivers, how one knows it is done, and — once done — what closed it.
Nothing else is required.

| Epic status | Meaning |
|---|---|
| `Proposed` | Suggested; nobody has approved its scope yet |
| `Planned` | Approved, not started |
| `In Progress` | Approved, being worked |
| `Completed` | Every one of its Stories is `Done` or `Cancelled` |
| `Cancelled` | Dropped |

| Story status | Meaning |
|---|---|
| `Planned` | In the plan, not started |
| `In Progress` | Being worked |
| `Blocked` | Cannot continue; say why |
| `Done` | Finished; `Closed` says when and with what |
| `Cancelled` | Dropped |

`.gtt/scripts/gtt-check-backlog.sh` keeps the structure sound: unique ids,
the status vocabulary, an Epic that is `Planned`, `In Progress` or
`Completed` carries its `Goal` and its `Approved`, and an Epic is
`Completed` only when its Stories are. It reports — without failing — a
`Done` Story with no `Closed`, and Stories being worked under an Epic that
is still `Proposed`. It approves nothing.

Work the human asks for directly needs no Epic first: do it, and record it
under *General Development Work* or as a Story if it is worth resuming.

---

## Epics

> Example only — replace it with your own Epics and Stories, or delete it. Nothing here is a real
> requirement.

### EPIC-001 — <Epic title (example)>

**Status:** Proposed
**Goal:** <the outcome this Epic delivers, in one or two sentences>
**Scope:** <what is included>
**Out of Scope:** <what is deliberately excluded>
**Approved:** <who> — <YYYY-MM-DD>

#### Stories

##### STORY-001 — <Story title (example)>

- **Status:** Planned
- **Description:** <what this Story delivers>
- **Done when:** <how one knows it is finished — criteria, tests>
- **Closed:** <YYYY-MM-DD> — <commit or PR> — <tests passed>
- **Notes:** <optional>

---

## General Development Work

Work tracked here that is not tied to a specific Story.

- None

## Current Focus

What is actively being worked on right now.

- None

## Next Work

What comes after Current Focus.

- None

## Blocked

- None

---
Governance: an Epic — its goal and its scope — is the human's decision.
Stories, their status, and the *Current Focus* / *Next Work* / *Blocked*
lists are the working plan and are edited freely. See `AGENTS.md` →
*Backlog* for the full rule and precedence relative to L0/ADRs.
