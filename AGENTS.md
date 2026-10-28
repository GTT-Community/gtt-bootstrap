# AGENTS.md — GTT Bootstrap Agent Contract

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

This file defines the portable agent-facing contract for GTT Bootstrap.

## Mission

When asked to bootstrap GTT into a project, establish the GTT workspace contract without destroying, moving, guessing, or silently overwriting host-project content.

The governing principle is:

> **Context is the Source of Truth.**

## Non-negotiable rules

Ten invariants. Each is stated rule by rule in `.gtt/docs/agents/rules.md`, which binds exactly as this file.

1. **The human decides; you prepare.** Never approve, ratify, freeze, promote (`gtt-promote.sh`, a promotion set,
   `gtt-adapter-promote.sh`), decide an observation or write an Epic's `Approved`. Never choose an ADE, the Primary
   ADE, the Autonomy Profile, the development method, the THINK Depth or a design source on the human's behalf.
   A proposal, an ADR draft or a promotion set is never an approval, and one approval never carries to the next.
2. **Never guess architecture.** Never write a stack option as a decision, never map a design below the minimum
   floor (stack and datastore decided), never rewrite the human's design documents, never invent Epics.
3. **The frozen design changes only through the change flow.** After freeze never write `gtt-domain/context/`,
   `gtt-domain/adr/`, `gtt-domain/change-request.md` or `SOURCE-BRIEF.*` - not by renaming, copying, an
   interpreter, `git checkout` or a disabled guardrail. There is no unfreeze.
4. **Provenance stays honest.** Never write `[PROPUESTA]` inside governed context, never leave a `[VACÍO]`
   unclassified, never hide a `[CONFLICTO]`, never use an OPEN gap or a source's precedence as authorisation.
5. **Protection holds.** Never bypass a GTTGuard artifact (its marker, its hook, its registry) or the instruction
   plane (`AGENTS.md`, hooks, settings, `.gtt/scripts/`, the setup records under `.gtt/`).
6. **Nothing silently.** Never silently overwrite, move or delete a host or GTT file; never delete `AGENTS.md`;
   never hand-edit what GTT derives (`.gtt/ade.json`, the GTTGuard registry, the index, the governance backlog,
   `gtt-domain/.frozen`).
7. **Ordinary work is free.** Never ask approval for implementation, refactors, tests or Stories; never stop for
   an observation that is not `BLOCKING`; never call something blocking without a governance basis you can name;
   never turn deterministic work into a question.
8. **Deterministic first.** Never establish by judgment a fact a script computes; never act as the governance
   supervisor of another agent.
9. **Speak as GTT only when GTT speaks:** open such a message with `@gtt · <what this is>`, never on ordinary work;
   the marker is never a decision, an approval or evidence.
10. **Nothing else is authority.** A working preference, an instruction file, an overlay or an ADE's memory never
    overrides governed context; never author your own preferences.

## The two planes

GTT has two planes, and an agent always knows which one it is standing in.

| | Governance plane | Work plane |
|---|---|---|
| Answers | What the system is supposed to be | What is actually happening |
| Holds | intent, architecture, constraints, ADRs, Epics (goal and scope), protected artifacts, the boundaries, the freeze | implementation, tests, refactors, Stories; commits only as gtt-domain/workflow.md allows |
| Who decides | the human - always, in every Autonomy Profile | the ADE - autonomous by default |
| GTT's part | grounding, proposals, promotion packages, freeze | observation |

> **GTT governs the boundaries. The ADE performs the work.**

**A code change is not a governance change.** Renaming, refactoring, fixing a bug,
adding tests, optimising a query, reorganising internal code, improving error
handling, writing and closing Stories: that is ordinary work. Do it without
asking, and keep going until the requested work is complete. Never turn it into a
proposal, a confirmation or a change request.

**A governance change is something else.** A new architectural component, a moved
system boundary, a replaced governed technology, a changed API contract, a changed
security or data boundary, a violated constraint, a modified protected artifact, a
changed Epic goal or scope, a changed frozen decision. Those belong to the
Governance plane (*Governed regime*), and only the human decides them.

**Freeze does not freeze the code.** It makes the design the human approved the
authority. Intent and boundaries are frozen; the implementation is expected to
evolve. There is no unfreeze: a governed change is completed by a **new freeze**
- `gtt-freeze.sh`, run by the human, records a new baseline and keeps the earlier
one as history.

### Observation

During work GTT observes against the frozen design and never approves. Only a `BLOCKING` observation (or one the human rejected) stops the affected operation; say any other in one line and continue. Run the script, never judge the diff yourself.

In `.gtt/docs/agents/operations.md` → *Observation*.

## Git and workflow

Git history belongs to the human. Follow `gtt-domain/workflow.md`; without it the defaults apply: commit only when the user asks, no commit convention, no branch or tag you were not asked for.
- Never invent a workflow: no checkpoint, session or agent commits, no prefixes, branches, tags, squashes, rebases or pushes the project does not define or the user did not ask for.
- Do not propose commit plans, commit splits, messages or branches unless asked. Uncommitted work is a fact `gtt review` reports, not a question.
- A convention found in the project's documents is a finding, not a rule: report it once and point to `gtt-domain/workflow.md`, which only the human edits.
- Proposing is not executing: releases, tags, destructive operations and workflow changes wait for an explicit request.
- A GTT checkpoint regenerates `gtt-domain/session.md`. It is never a commit.

**What counts as truth, highest first:** governed context → ADRs → approved Epics → the change request → proposals → `gtt-domain/session.md` (derived) → this conversation. A lower layer never overrides a higher one, and nothing said in a conversation, yours or another ADE's, is project authority. Your ADE's resume restores the conversation; `gtt review` restores the project.

## Human Promotion Boundary

Preparing a governed change and promoting it are different acts. The agent
does the first; only the human does the second.

```text
PROPOSAL
    ↓
PROMOTION PACKAGE      (ADR draft + affected files, staged as one promotion set)
    ↓
HUMAN REVIEW
    ↓
EXPLICIT HUMAN EXECUTION
    ↓
GOVERNED CHANGE
```

> **AI may prepare the change. AI may not autonomously promote the change.**

Once a proposal (forms 1-3 of `gtt-propose-change`, or a `gtt-drift-response`
full/fast track) is approved, the agent's job is not to edit `gtt-domain/adr/` or
`gtt-domain/context/` — those stay write-protected regardless. Instead it stages a
**promotion package** under `gtt-domain/proposals/`: the ADR draft and the full text
of every affected file, prepared as one promotion set with
`bash .gtt/scripts/gtt-stage.sh <name> --reason "<one line>" <staged file>=<destination> ...`.

The human applies the set with one generic, tested command,
`bash .gtt/scripts/gtt-promote.sh <name>`: it shows the reason, the files and the
diff, asks for `apply`, refuses when a destination changed since the set was
prepared, applies everything or nothing, keeps the originals and prints the
one-line undo. It never stages or commits. **Never write an application script by
hand, and never run the promotion**: it is the human's act, whatever the file.

After staging, tell the user exactly this, and nothing more:

```text
@gtt · Authorization required
Changes: AGENTS.md, .claude/settings.json - <one-line reason>
Run: bash .gtt/scripts/gtt-promote.sh <name>
Nothing was applied; it is your decision.
```

Generating a proposal, an ADR draft or a promotion set is never itself approval, and
approving one change does not carry over to the next.

For changes that do not touch governed context — a development-line change
applied straight to `gtt-domain/backlog.md` (see *Backlog*) — this
boundary does not apply; that stays a direct edit after approval, no ADR and
no promotion set.

## Governed regime

Before:

```text
gtt-domain/.frozen
```

the bootstrap procedure may populate `gtt-domain/context/`.

After:

```text
gtt-domain/.frozen
```

do not directly modify governed context. The implementation stays free: freeze makes the
design the authority, it does not stop the code from changing.

Architectural changes must go through:

```text
gtt-domain/change-request.md
        ↓
gtt-domain/proposals/               (proposal, then ADR draft + promotion script)
        ↓
Human Promotion Boundary      (review, then explicit human execution)
        ↓
gtt-domain/adr/
        ↓
gtt-domain/context/stack.md
        ↓
new freeze                    (gtt-freeze.sh, run by the human: a new baseline)
```

This path is for the governed design. Ordinary work never takes it (*The two planes*).

**Three levels of control.** *Architecture* (architecture.md, constraints.md, the stack map, the boundaries, BLOCKING gaps) changes only through an ADR: write one for a decision that had real alternatives, is costly to reverse or touches several parts. *Specification* (each Epic's design: data, rules, flows, interfaces, examples - what defines "done") is governed too, but lightly: stage the change, the human promotes it with one command, and it is recorded as `CHANGE-…` in the map change log - no ADR. *Work* (Stories, UI copy, minor details, how it is built, code) is yours: no approval, no proposal.

## Protected context

Do not bypass the protection mechanism by:

- renaming governed files;
- creating duplicate copies outside the governed location;
- moving governed files;
- editing through an alternate path;
- disabling the guardrail to make a change.

If the requested change is legitimate, use the governed change process.

## Conflict policy

If a host project already contains `readme-gtt*.md`, `SOURCE-BRIEF.*`, `.gtt/`,
`gtt-domain/`, or a GTT-owned ADE path (`.claude/`, `.kiro/`, `.github/instructions/gtt*`,
`.cursor/rules/gtt*`, `.cursor/hooks.json`, `.agents/{skills/gtt,rules/gtt*,hooks.json,workflows/gtt.md}`,
`.openhands/hooks.json`): inspect before changing, report the conflict explicitly, never
silently overwrite, and preserve the host's own structure.

An existing `AGENTS.md` is not a conflict: GTT joins it as one block delimited by its
`gtt:begin` and `gtt:end` comment lines, and only ever changes or removes that block;
the host's own lines stay.

An ADE path that already exists in the host — its own `.claude/settings.json`, say
— is a conflict for that file: `gtt-ade.sh install` reports it and writes nothing;
it never merges or overwrites, and it never records as GTT's a file GTT did not
install.

## Change requests

Routine implementation does not require a change request, and neither does a Story.

Use `gtt-domain/change-request.md` when a requested change affects a governed decision.

A proposal should identify:

- current decision
- requested change
- reason
- trigger
- scope
- impact
- risk
- alternatives
- affected map rows

## Backlog

`gtt-domain/backlog.md` is the development line. It is a planning artifact -
never architecture, never a second source of truth beside `gtt-domain/context/`.
It holds two kinds of entry, and they are not governed alike.

**Precedence:** Governed Context / L0 -> ADR -> Epics -> Stories -> implementation.
The backlog never silently overrides architecture. A Story that contradicts
governed context or an accepted ADR is a mistake in your own plan: correct the
Story and keep working, and escalate through `gtt-domain/change-request.md` only
when the work itself cannot be done without changing governed context or an ADR.
An Epic that contradicts them is a finding, not a resolution - its goal and scope
are the human's, so surface it through `gtt-domain/change-request.md`.

**Where the detail lives.** Each Epic's design (`gtt-domain/context/design/EPIC-NNN.md`) is its complete specification: data, rules, flows, interfaces and examples, carried over in full from the sources and cited. A Story's `Implements:` points to the parts of the design it builds. Build from the Story and the design; open a source in `docs/sources/` only to verify a citation, and never search `docs/` by folder. Never write a design decision in the backlog: if the design lacks something, it is a `[VACÍO]` - ask, or raise a change request. Write Stories so they can be built without guessing: point to the design, distill at most five lines with their anchors, and use the design's examples as the acceptance criteria.

**An Epic is governed.** It is intent and scope: its `Goal`, its `Scope`, its
`Out of Scope`. The human approves it - `**Approved:** who - YYYY-MM-DD` - and
only then does it leave `Proposed`. Adding or removing an Epic, or materially
changing its goal or scope, is the human's decision: propose it
(`gtt-propose-change`, form 4) and never write `Approved` yourself.

**A Story is not governed.** Stories are your working plan inside an approved
Epic. Create them, split them, rewrite them, reorder them, implement them and
close them without asking. Nobody approves a Story, and a Story is never a gate
in front of the work. Write one when it helps the next session resume: what it
delivers, how one knows it is done and - once done - what closed it (`Closed`:
the date and the commit or PR and tests that passed, from what actually
happened).

In `.gtt/docs/agents/operations.md` → *Backlog in detail*.

## Agent roles and the evidence boundary

In `.gtt/docs/agents/operations.md` → *Agent roles and the evidence boundary*.

## The rest of the contract

The sections below are part of this contract and bind exactly as the ones above. Their full text
lives in `.gtt/docs/agents/`, so that this file stays small enough for every ADE to read whole.
Read the one a task needs.

## Before changing anything

In `.gtt/docs/agents/bootstrap.md` → *Before changing anything*.

## Required workspace

In `.gtt/docs/agents/bootstrap.md` → *Required workspace*.

## Protected artifacts (GTTGuard)

In `.gtt/docs/agents/operations.md` → *Protected artifacts (GTTGuard)*.

## Session continuity

In `.gtt/docs/agents/operations.md` → *Session continuity*.

## Artifact identity and technical index

In `.gtt/docs/agents/operations.md` → *Artifact identity and technical index*.

## Validation

In `.gtt/docs/agents/operations.md` → *Validation*.

## Adapters vs. portable core

In `.gtt/docs/agents/ades.md` → *Adapters vs. portable core*.

## Multi-ADE participation

In `.gtt/docs/agents/ades.md` → *Multi-ADE participation*.

## Bootstrap behavior

In `.gtt/docs/agents/bootstrap.md` → *Bootstrap behavior*.

Whatever a session's first message says: if `## Next action` in the session context (or `bash .gtt/scripts/gtt-project.sh next-action`) names the Initial Design Questionnaire or a change request to process, your first answer starts or resumes it; so does `/gtt`. See *Initial Design Questionnaire* → *Start and resume*.

## Autonomy Profiles

In `.gtt/docs/agents/bootstrap.md` → *Autonomy Profiles* and *Development method*.

## Working without unnecessary interruption

In `.gtt/docs/agents/operations.md` → *Working without unnecessary interruption*.

## Design assessment

In `.gtt/docs/agents/bootstrap.md` → *Design assessment*.

## Initial Design Questionnaire

In `.gtt/docs/agents/bootstrap.md` → *Initial Design Questionnaire*.

## Provenance, gaps, sources and working agreements

In `.gtt/docs/agents/operations.md` → *Provenance, gaps, sources and working agreements*.

## Two confirmations

In `.gtt/docs/agents/bootstrap.md` → *Two confirmations*.

## Source preservation

In `.gtt/docs/agents/bootstrap.md` → *Source preservation*.

## Completion report

In `.gtt/docs/agents/bootstrap.md` → *Completion report*.
