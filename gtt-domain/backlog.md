# Project Backlog

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

This file is the project's plan of work: **what is going to be built, in what
order, and where it stands today.** It is written to be read by a person; you
do not need to know GTT to follow it.

It answers three questions:

- **What do we want?** The *Epics*: each one is a result the project wants.
- **How is it being built?** The *Stories* inside each Epic: the steps of the work.
- **Where are we right now?** *Current Focus*, *Next Work* and *Blocked*.

It is a plan, not the design. What the system *is* — its architecture, its
technology, its limits — lives in `gtt-domain/context/`. When the plan and
the design disagree, the design wins (see *When the plan and the design
disagree*, at the end).

**Last verified:** `<date>` — run the `gtt-audit` skill to reconcile against defined requirements.

---

## Development Line

<what phase, release, or milestone this backlog currently represents — one or two sentences. Leave empty rather than inventing one.>

---

## How to read this file

### The two kinds of entry

| | Epic | Story |
|---|---|---|
| **What it is** | A result the project wants, and where it stops | One step of the work towards that result |
| **Who writes it** | You — or the AI assistant, as a suggestion for you | The AI assistant doing the work (the *ADE*) |
| **Who decides** | **You.** An Epic stays `Proposed` until you approve it | Nobody has to approve it. The assistant writes, changes and closes Stories as it works |
| **How much detail** | Short: goal, what is in, what is out | A pointer to the Epic's design, and how one knows it is done |

### What an Epic says

| Field | Meaning | Who writes it |
|---|---|---|
| `Status` | Where the Epic stands (table below) | You when you approve it; the assistant as work advances |
| `Goal` | The result this Epic delivers, in one or two sentences | You |
| `Scope` | What is included | You |
| `Out of Scope` | What is deliberately left out | You |
| `Design` | The file with the full detail of this Epic: data, rules, flows, interfaces, examples | Written when you approve |
| `Approved` | Who approved the Epic and when | Written when you approve — never by the assistant |

### What a Story says

| Field | Meaning |
|---|---|
| `Status` | Where the Story stands (table below) |
| `Implements` | Which parts of the Epic's design this Story builds |
| `Context` | Five lines at most: what one needs to know to build it, taken from the design |
| `Done when` | The example from the design that must work, and the test that proves it |
| `Closed` | Once finished: the date, the commit or pull request, and the tests that passed |

### Statuses

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

### What you can change here

This file is yours to edit. Nothing in it is locked.

- **An Epic's goal and scope are your decision.** Write them, change them,
  add an Epic or drop one. The assistant never does that on its own: it
  suggests, and the Epic stays `Proposed` until you approve it.
- **To approve an Epic**, run `bash .gtt/scripts/gtt-approve.sh EPIC-NNN`. It
  shows you the Epic and its design, asks you to confirm, and then writes
  `Approved` and `Design` and moves the Epic to `Planned`. An Epic and its
  design are approved together.
- **Stories are the assistant's working plan**, so expect it to rewrite them.
  You may edit them too, whenever you want.
- **Development Line, Current Focus, Next Work and Blocked** are plain notes:
  edit them freely.
- **Work you ask for directly needs no Epic first.** It is done, and noted
  under *General Development Work*, or as a Story when it is worth resuming.

---

## Epics

> Example only — replace it with your own Epics and Stories, or delete it. Nothing here is a real
> requirement.

### EPIC-001 — <Epic title (example)>

**Status:** Proposed
**Goal:** <the outcome this Epic delivers, in one or two sentences>
**Scope:** <what is included>
**Out of Scope:** <what is deliberately excluded>
**Design:** gtt-domain/context/design/EPIC-NNN.md
**Approved:** <who> — <YYYY-MM-DD>

#### Stories

##### STORY-001 — <Story title (example)>

- **Status:** Planned
- **Implements:** design/EPIC-NNN#R-2, #F-1, #E-1 · ADR-NNN
- **Context:** <5 lines at most, distilled from the design; each line ends with its design anchor (#R-2)>
- **Done when:** E-1 passes (Given … when … then …) · <test file>
- **Closed:** <YYYY-MM-DD> — <commit or PR> — <tests passed>

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

## Reference

The rules behind this file, for whoever maintains it — a person or the
assistant. The full text is in `AGENTS.md` → *Backlog*.

### Where the detail lives

The backlog stays short on purpose. The full specification of an Epic is its
design file, `gtt-domain/context/design/EPIC-NNN.md`: everything the project's
documents say about that Epic — data, rules, flows, interfaces, examples —
carried over in full and cited, not summarised.

A Story points at that design and never decides anything itself:

- `Implements` names the parts it builds, by their ids in the design
  (`design/EPIC-NNN#R-2, #F-1`: rule 2, flow 1).
- `Context` distils at most five lines, each ending with the id it comes from.
- `Done when` names an example of the design (`E-1`) and the test that proves it.

A Story never cites a source document directly, and a design decision is
never written in this file. What the design does not define is a gap
(`[VACÍO]`) to ask about, not something to fill in here.

### When the plan and the design disagree

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

Each level yields to the one above it. A Story never silently overrides
architecture: a Story that contradicts the design is a mistake in the plan,
and the plan is corrected. An Epic that contradicts it is yours to resolve.
What the ADE does in each case: `AGENTS.md` → *Backlog* (*Precedence*).

### What keeps it honest

Stories are not approved in advance. What protects the design is
*observation* (`.gtt/scripts/gtt-observe.sh`): if the work crosses a boundary
of the frozen design — a new core technology, a changed contract — GTT
reports it, whatever the Story said.

`.gtt/scripts/gtt-check-backlog.sh` keeps the structure sound: unique ids,
the status vocabulary, an Epic that is `Planned`, `In Progress` or
`Completed` carries its `Goal` and its `Approved`, an Epic is `Completed`
only when its Stories are, and every reference to a design resolves. It
reports — without failing — a `Done` Story with no `Closed`, and Stories
being worked under an Epic that is still `Proposed`. It approves nothing.

---
Governance: an Epic — its goal and its scope — is the human's decision.
Stories, their status, and the *Current Focus* / *Next Work* / *Blocked*
lists are the working plan and are edited freely. See `AGENTS.md` →
*Backlog* for the full rule and precedence relative to L0/ADRs.
