# Project Backlog

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> The project's living development line — Epics, Stories, and the work
> currently expected to be built. This is a development-planning artifact,
> not architecture: see *Precedence* below. It answers "what exists, what's
> next, what's blocked" — not "how may it be built" or "what decisions are
> authoritative."

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
This backlog
        v
Implementation work
```

If a Story appears to contradict governed context or an accepted ADR, that
is a finding, not a resolution. Raise it through `gtt-domain/change-request.md` —
a Story never silently overrides architecture.

---

## Story Ready

A title is not a design. A Story may be `Ready`, `In Progress` or `Done` only
when its design is **written here and approved by the Solution Designer** —
so that another session, or another person, can implement it from this file
alone, never from a conversation.

| Field | Must contain |
|---|---|
| **Description** | What the Story delivers; every statement carries its origin |
| **Scope** | What is included; every item carries its origin |
| **Out of Scope** | What is deliberately excluded (`None` is an answer; it still carries its origin) |
| **Acceptance Criteria** | Verifiable criteria; every criterion carries its origin |
| **Tests** | The tests that close the Story |
| **Sources** | The sources the design was derived from, or `None` |
| **Governed by** | The governed decisions that apply — ADR ids, sections of `gtt-domain/context/` — or `None`. A reference, never a copy: the context stays the single place where architecture is written |
| **Design Approved** | Who approved the written design, and the date (`YYYY-MM-DD`) |
| **Closed** | Only for `Done`: the date (`YYYY-MM-DD`) and what closed it — commit or PR, tests passed |

Origin of each statement — one of:

| Tag | Meaning |
|---|---|
| `[FUENTE: ref]` | It comes from a source: a declared source id (`id:loc`) or a repo path (`path:line`) |
| `[HUMANO]` | The Solution Designer decided it (optionally `[HUMANO: who, date]`) |
| `[PROPUESTA]` | The agent proposed it; approving the Story is what accepts it, and the tag stays so the origin remains visible |

A `[VACÍO]` or `[CONFLICTO]` inside a Story means a point is still undecided:
the Story is not designed yet.

Story status:

| Status | Meaning |
|---|---|
| `Proposed` | Suggested, not yet accepted into the development line |
| `Undesigned` | Accepted into the line, but only a title (or an incomplete design) exists — **not implementable** |
| `Ready` | Designed and approved: every field above is written and `Design Approved` is set |
| `In Progress` / `Blocked` / `Cancelled` | As named. `In Progress` keeps the full definition |
| `Done` | Implemented and closed: the full definition plus `Closed` |

An Epic is `Completed` only when every one of its Stories is `Done` or
`Cancelled`.

`.gtt/scripts/gtt-check-backlog.sh` fails when a `Ready`, `In Progress` or
`Done` Story is missing a field or an origin, when a `Done` Story has no
`Closed`, when `Governed by` cites an ADR that does not exist, and when a
`Completed` Epic still has open Stories. Implementation is done only
against what is written here: if something that is not written turns out to
be needed, stop and update the Story first.

---

## Epics

> Example only — replace it with your own Epics and Stories, or delete it. Nothing here is a real
> requirement. Structural changes (adding or removing an Epic or Story, or materially changing one —
> which includes writing or changing a Story's design) go through `gtt-domain/change-request.md`;
> status and focus updates are direct edits.

### EPIC-001 — <Epic title (example)>

**Status:** Proposed
**Goal:** <the outcome this Epic delivers, in one or two sentences>

#### Stories

##### STORY-001 — <Story title (example)>

- **Status:** Undesigned
- **Priority:** Medium
- **Description:**
  - <what this story delivers> [FUENTE: <source-id:section or path:line>]
- **Scope:**
  - <what is included> [FUENTE: <ref>]
- **Out of Scope:**
  - <what is deliberately excluded> [HUMANO]
- **Acceptance Criteria:**
  - <criterion> [FUENTE: <ref>]
  - <criterion> [PROPUESTA]
- **Tests:**
  - <the test that closes each criterion>
- **Sources:** <source ids or paths the design was derived from, or None>
- **Governed by:** <ADR-NNN, context file and section, or None>
- **Design Approved:** <who> — <YYYY-MM-DD>
- **Closed:** <YYYY-MM-DD> — <commit or PR> — <tests passed>
- **Dependencies:** None
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
Governance: adding or removing an Epic/Story, or materially changing its
scope or acceptance criteria — including writing its design — goes through `gtt-domain/change-request.md` ->
`gtt-domain/proposals/` -> Solution Designer decision — the same funnel as an
architecture change. Updating a Story's status, or the *Current Focus* /
*Next Work* / *Blocked* lists, as part of already-approved implementation
work does not need a change request. See `AGENTS.md` → *Backlog governance*
for the full rule and precedence relative to L0/ADRs.
