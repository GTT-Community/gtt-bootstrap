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

## Epics

> Example only — replace it with your own Epics and Stories, or delete it. Nothing here is a real
> requirement. Structural changes (adding or removing an Epic or Story, or materially changing one)
> go through `gtt-domain/change-request.md`; status and focus updates are direct edits.

### EPIC-001 — <Epic title (example)>

**Status:** Proposed
**Goal:** <the outcome this Epic delivers, in one or two sentences>

#### Stories

##### STORY-001 — <Story title (example)>

- **Status:** Proposed
- **Priority:** Medium
- **Description:** <what this story delivers>
- **Acceptance Criteria:**
  - <criterion>
  - <criterion>
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
scope or acceptance criteria, goes through `gtt-domain/change-request.md` ->
`gtt-domain/proposals/` -> Solution Designer decision — the same funnel as an
architecture change. Updating a Story's status, or the *Current Focus* /
*Next Work* / *Blocked* lists, as part of already-approved implementation
work does not need a change request. See `AGENTS.md` → *Backlog governance*
for the full rule and precedence relative to L0/ADRs.
