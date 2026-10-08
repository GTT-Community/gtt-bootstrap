---
name: gtt-adr
description: Draft an Architecture Decision Record — and its promotion package — for a change the Solution Designer has already approved. Use when the user says a proposal is approved, asks to record or document a decision, asks to write an ADR, or asks to update the ADR index. Do not use for proposing changes that are not yet approved.
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Draft an ADR and its promotion package

> **Speaking for GTT.** Every message this skill raises to the human — a
> question, a confirmation, a proposal, a finding, a request for
> authorization, a report — opens with `@gtt · <what this is>`
> (e.g. `@gtt · Authorization required`). The marker says who is speaking; it is never a decision.

Only draft an ADR for a decision a human has explicitly approved. If approval is
unclear, ask. An ADR records a decision that was made — it is not a place to
argue for one.

`gtt-domain/adr/` and `gtt-domain/context/` are write-protected. You never write into them
directly. Instead you stage a complete **promotion package** under
`gtt-domain/proposals/` — the ADR draft, the full text of every affected context
file, and an executable script — and the human runs the script. This is the
Human Promotion Boundary (`AGENTS.md`): you prepare, they promote. Generating
this package is not itself approval, and approving one change never carries
over to the next.

If a proposal for this change exists in `gtt-domain/proposals/`, base the ADR on it
rather than restating the reasoning from scratch.

## First: does this change need an ADR?

An ADR is for architecture only. Apply the rule before drafting anything - it is deterministic:

- The change touches `architecture.md` or `constraints.md`, sections 1 to 5 or 7 of `stack.md`, or a
  `BLOCKING` gap → it is **architectural**: draft the ADR, as below.
- It touches only an Epic's design (`gtt-domain/context/design/`), `glossary.md`, `solution-vision.md` or
  another detail → it is a **specification change**: stage the set **without an ADR**
  (`bash .gtt/scripts/gtt-stage.sh <name> --reason "…" <draft>=<destination> …`) and say so in one line. The
  promotion records it as `CHANGE-<date>-<name>` in the map change log and takes the new freeze in the
  same confirmation.

You may still propose an ADR for a specification change that had real alternatives; the human chooses.

## Numbering

Take the number from `bash .gtt/scripts/gtt-project.sh next-id --kind adr` - deterministic, and it never
reuses a retired id. Do not ask the human which number to use; they see it when they review the package.
Target filename: `ADR-NNN-short-kebab-title.md`. Write the draft itself to
`gtt-domain/proposals/ADR-DRAFT-short-kebab-title.md` — never into `gtt-domain/adr/`.

## Template

```markdown
# ADR-NNN — <Title>

- Status: Accepted
- Date: YYYY-MM-DD
- Approved by: <Solution Designer>
- Supersedes: <ADR-NNN, or none>

## Context

What forced this decision. The constraint, the problem, the trigger. Written so
that someone reading it in a year understands the situation without asking.

## Decision

The decision, stated in one or two sentences, in the active voice.

## Alternatives considered

| Option | Why it lost |
|---|---|

## Consequences

What this makes easy. What this makes hard. What is now locked in.

## Risks

What could make this decision wrong later, and what signal would reveal it.

## Stack map delta

The exact rows this decision changes in `gtt-domain/context/stack.md`, as before/after
pairs. Write `No change to the map` only if that is literally true.

| Section | Row | Before | After |
|---|---|---|---|

Plus the line to append to the map change log:

| YYYY-MM-DD | ADR-NNN | <what changed> |

## Affected context

Which other files under `gtt-domain/context/` this decision changes, and how —
staged as full drafts alongside the ADR (see *Stage the affected context
files* below). The Solution Designer runs the script that applies them; you
do not edit them directly.
```

## After drafting

An ADR without a stack map delta is incomplete. `gtt-domain/context/stack.md` is the
one artifact everyone reads to understand the system; a decision recorded in an
ADR but absent from the map is invisible in practice.

## Stage the affected context files

For every file the ADR's *Affected context* section names — `stack.md` always,
plus any others — write the file's **full new content**, not a diff, to
`gtt-domain/proposals/context-<basename>.md` (for example
`gtt-domain/proposals/context-stack.md`). The promotion will copy each one
straight over its target, so the staged draft must be the complete file exactly
as it should read after promotion, changelog row included.

## Stage the promotion set

Never write an application script by hand. Stage the ADR draft and every affected
context file as one set, named after the ADR:

```bash
bash .gtt/scripts/gtt-stage.sh ADR-NNN-<slug> --reason "<what the decision changes, one line>" \
  gtt-domain/proposals/ADR-DRAFT-<slug>.md=gtt-domain/adr/ADR-NNN-<slug>.md \
  gtt-domain/proposals/context-stack.md=gtt-domain/context/stack.md
```

One `source=destination` pair per file. The command copies them into
`gtt-domain/proposals/staged/ADR-NNN-<slug>/` and records what each destination
looked like, so the promotion refuses to run if one changes in the meantime. You
may delete the drafts once they are staged. You never run the promotion.

## Tell the user

Exactly this, and nothing more:

```text
@gtt · Authorization required
Changes: gtt-domain/adr/ADR-NNN-<slug>.md, gtt-domain/context/stack.md - <one-line reason>
Run: bash .gtt/scripts/gtt-promote.sh ADR-NNN-<slug>
Nothing was applied; it is your decision.
```

The promotion shows the reason, the files and the diff before it asks for `apply`,
applies everything or nothing, prints its undo and validates the result. A governed
change is then completed by a new freeze, which is also the human's.
