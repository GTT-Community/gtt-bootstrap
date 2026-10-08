---
name: gtt-propose-change
description: Produce a GTT change proposal instead of applying a governance change directly. Use when the user says to process the change request, when an architectural change is required, when a governed context file under gtt-domain/context/ is wrong or outdated, when implementation code conflicts with the governed context, when an Epic must be added, removed or its goal or scope materially changed, or when a change is requested to a GTTGuard-protected file/class/method. Triggers on any request to change architecture, paradigm, module boundaries, frameworks, cloud services, or infrastructure tooling, on any request to change an Epic, and whenever a permission denial points at gtt-domain/context/, gtt-domain/adr/, gtt-domain/change-request.md, or a GTTGuard-protected artifact. NOT for ordinary work - implementing, refactoring, testing, or writing and closing Stories needs no proposal and no approval.
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# GTT change proposal

> **Speaking for GTT.** Every message this skill raises to the human — a
> question, a confirmation, a proposal, a finding, a request for
> authorization, a report — opens with `@gtt · <what this is>`
> (e.g. `@gtt · Proposal`). The marker says who is speaking; it is never a decision.

Governed context is owned by the Solution Designer. You produce proposals; a
human decides. Do not implement the change, do not partially apply it, and do
not create the ADR yourself.

## First: is this governance at all?

A proposal means "this may need a governance decision". It is never a request
for permission to do ordinary work (`AGENTS.md` → *The two planes*).

| The change | What to do |
|---|---|
| Implementation: a refactor, a bug fix, tests, an internal reorganisation, an optimisation | Do it. No proposal. |
| A Story: creating, splitting, rewriting, closing one | Edit `gtt-domain/backlog.md`. No proposal. |
| The governed design: architecture, a boundary, a governed technology, an API contract, a constraint, an Epic's goal or scope, a protected artifact | A proposal - this skill. |

If you are about to write a proposal for the first two rows, stop: you would be
putting the human back into the loop of ordinary work.

## Where the request comes from

If the user says "process the change request", read `gtt-domain/change-request.md`
first. It holds the Solution Designer's stated intent. If
the request block is empty or unchanged from the template, say so and stop —
do not invent one.

The request block may be filled in tersely or as a raw paragraph pasted
straight from the Solution Designer's own document — both are valid input.
Read a pasted excerpt for what it actually decides; do not ask them to
compress it into the template's fields first.

Otherwise the request is whatever the user just described.

## Where the output goes

Write the proposal to `gtt-domain/proposals/PROPOSAL-<short-kebab-summary>.md`. That
directory is the only governed place you may write.

Do not edit `gtt-domain/change-request.md` — not to clear it, not to mark it
processed, not to tidy it. It is the Solution Designer's desk.

## Before writing

Read what the change actually touches: `gtt-domain/context/stack.md` always, plus the
relevant context files and any ADR the affected stack rows point to in their
"Locked by" column. A proposal that ignores the decision it overturns is not a
proposal.

If the request is about an Epic instead - a new one, removing one, or a
material change to its goal or scope - read `gtt-domain/backlog.md` first, and
check whether it contradicts governed context or an accepted ADR before
drafting (see *Precedence* in `AGENTS.md` → *Backlog*). Stories are not a change
request at all: they are the working plan and are edited directly.

If the request is a change to a file, class, or method carrying a
`@GTTGuard` marker — check `.gtt/protection/registry.yaml` — use Form 5
below; it is neither an architecture change nor a backlog change.

## Forms

Pick the one that matches the situation.

## 1. Architecture change

Use when the solution needs a different architectural direction, style,
paradigm, module boundary, integration strategy, deployment strategy, framework,
runtime, datastore, or cloud service.

```text
Proposed Architecture Change

Current decision:
Suggested change:
Reason:
Impact:
Risk:
Affected files:
Alternatives considered:

Status: Requires Architect approval
```

## 2. Context change

Use when a file under `gtt-domain/context/` is inaccurate, stale, or contradicts
reality — and the fix is to the document, not the code.

```text
Proposed Context Change

File:
Current statement:
Suggested change:
Reason:
Impact:
Risk:

Status: Requires Solution Designer approval
```

## 3. Context conflict

Use when implementation and governed context disagree and you cannot tell which
one is correct. Do not resolve it yourself and do not pick the code by default.

```text
Context Conflict Detected

Context file:
What the context says:
What the implementation does:
Where they diverge:
Possible resolutions:

Status: Requires human review
```

## 4. Epic change

Use when `gtt-domain/backlog.md` needs an Epic added, removed, or its goal or
scope materially changed. An Epic is intent and scope - the one part of the
backlog the human decides. Not for Stories: those are the working plan and are
never proposed or approved.

```text
Proposed Epic Change

Kind: <new Epic / remove / material change of goal or scope>
Epic ID: <EPIC-NNN, or "new" if not yet assigned>
Current state: <what gtt-domain/backlog.md says today, or "none" if new>
Goal:
Scope:
Out of Scope:
Reason:
Contradicts governed context or an ADR?: <no / yes — cite file:line>
Impact:
Risk:

Status: Requires Solution Designer approval
```

If the request would contradict governed context or an accepted ADR, say so
explicitly rather than quietly aligning the Epic to the architecture - that
contradiction is exactly what the Solution Designer needs to see and decide.

Write the Epic into `gtt-domain/backlog.md` as `Proposed`, with
`**Design:** gtt-domain/context/design/EPIC-NNN.md`, and draft that design
(`bash .gtt/scripts/gtt-design.sh scaffold EPIC-NNN --apply`): the complete specification of the
Epic, carried over from the sources and cited. After the freeze the draft lands under
`gtt-domain/proposals/` and reaches its place through a promotion set - a specification change, no ADR.
The human approves the Epic and its design together with `bash .gtt/scripts/gtt-approve.sh EPIC-NNN`;
you never write `Approved`. The Stories under it are yours and need no approval, in this format:

```markdown
##### STORY-NNN — <title>
- **Status:** Planned
- **Implements:** design/EPIC-NNN#R-2, #F-1, #E-1 · ADR-NNN
- **Context:** <5 lines at most, distilled from the design; each line ends with its design anchor (#R-2)>
- **Done when:** E-1 passes (Given … when … then …) · <test file>
```

A Story cites the design; it never cites a source directly and never decides.

## 5. Protected artifact change (GTTGuard)

Use when the requested change touches a file, class, or method that
`.gtt/protection/registry.yaml` lists with `protection: HUMAN_APPROVAL`.
This is not an architecture change and not a backlog change — GTTGuard is a
sibling mechanism protecting L3 code the developer opted into protecting,
not `gtt-domain/context/` or `gtt-domain/adr/`. See `AGENTS.md` → *Protected artifacts
(GTTGuard)* before using this form.

```text
Protected Artifact Change

Artifact: <file path>
Symbol: <ClassName, ClassName.method, or "whole file">
Current behavior:
Suggested change:
Reason:
Source (if any, e.g. an ADR or ticket the protection traces to):
Impact:
Risk:
Alternatives considered:

Status: Requires Solution Designer approval
```

**Promotion is lighter here than Forms 1-3.** There is no ADR and no
promotion set — GTTGuard is deliberately not a second, unrelated
approval model; it reuses this proposal mechanism, nothing heavier. Once
the Solution Designer approves
**in conversation**, implement the change directly, update or remove the
`@GTTGuard` marker as appropriate, and run `.gtt/scripts/gtt-guard-sync.sh`
so the registry reflects it. Do not treat this approval as covering any
other protected artifact, and do not confuse this with the L0/L1 Human
Promotion Boundary — that one still requires the Solution Designer to run a
script themselves, this one does not.

## Quality bar

A proposal is only useful if it can be decided without a follow-up question.

- Name the specific decision being changed, not the general area.
- Impact means blast radius: which modules, which interfaces, which deployments.
- Risk means what breaks if this is wrong, and how it would be detected.
- List at least one alternative and say why it loses.
- If you cannot fill a field honestly, say so rather than inventing it.

## After writing

State the file path you wrote and summarize the proposal in two or three lines
in chat, so the decision can be made without opening the file. Then stop.

Once an architecture, context, or conflict proposal (forms 1-3) is approved,
the decision is recorded with the `gtt-adr` skill, which stages the ADR, the
affected context files, and an executable promotion script together (the governed
change is then completed by a new freeze, which the human runs) — the
Solution Designer reviews and runs it; the agent never applies the change
itself (the Human Promotion Boundary, `AGENTS.md`). An Epic proposal (form 4)
is not an architectural decision: once approved it is written straight into
`gtt-domain/backlog.md`, no script and no ADR unless it also happens to touch
governed context. A protected-artifact proposal (form 5) is approved in conversation
— once the Solution Designer says so, implement it directly, update the
marker, and re-sync the registry; no ADR, no script, and never treat it as
approval for a different protected artifact.
