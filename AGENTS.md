# AGENTS.md — GTT Bootstrap Agent Contract

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

This file defines the portable agent-facing contract for GTT Bootstrap.

## Mission

When asked to bootstrap GTT into a project, establish the GTT workspace contract without destroying, moving, guessing, or silently overwriting host-project content.

The governing principle is:

> **Context is the Source of Truth.**

## Non-negotiable rules

- Never guess architecture.
- Never map a design below the minimum floor (stack and datastore decided) into governed context, and never let a confirmation that it is finished lift the floor.
- Never rewrite the human's design documents, never write a stack option or recommendation as a decision, and never recommend a stack that does not follow from what the project's own documents state.
- Never select, infer, raise or lower the THINK Depth on the human's behalf - not from the Method Plan, not from the project's size - and never treat a depth as permission to skip the floor, a provenance tag, a human decision or the freeze.
- Never choose between several design documents, or between consolidating them and keeping them as sources, on the human's behalf.
- Never silently overwrite.
- Never silently move GTT artifacts.
- Never claim a decision was approved when it was not.
- Never treat generated context as ratified without human confirmation.
- Never run a promotion (`gtt-promote.sh`, or a promotion script), or apply its changes by any
  other means, on the agent's own initiative — see *Human Promotion Boundary*.
- Never treat a drafted proposal, ADR, or promotion set as approval for the
  next one; each governed promotion requires its own explicit human decision.
- Never delete `AGENTS.md`.
- Never bypass governed protection after freeze.
- Never treat a detected ADE as installed, authorized, governed or participating; only the human's explicit choice makes an ADE participate.
- Never install an adapter for an ADE the human did not choose, and never reintroduce one a prior run excluded unless the human says so.
- Never infer the participating or Primary ADE from the underlying model, from adapter files that merely happen to exist, or from a binary on the PATH; ask if it cannot be established with confidence.
- Never give the Primary ADE, or any ADE, authority over a governed artifact, and never introduce an ADE hierarchy, agent voting or arbitration.
- Never write a `[PROPUESTA]` inside governed context, never leave a `[VACÍO]` unclassified there, and never use an OPEN gap — or the precedence of a source — as authorisation to change a frozen design or to hide a `[CONFLICTO]`.
- Never let a working preference override governed context, never author your own preferences, and never commit `.gtt/local/preferences.md`.
- Never treat an instruction file or ADE overlay (`AGENTS.md`, `.claude/`, `.kiro/`, `.github/instructions/`, `.codex/`, ADE memory or session history) as governance authority.
- Never hand-edit `.gtt/ade.json`; write it only through `.gtt/scripts/gtt-ade.sh`. Never remove an ADE path GTT did not install.
- Never copy the Initial Design Questionnaire, or its methodology, out of the Bootstrap, and never write a `[PROPUESTA]` or an ADE inference as a confirmed decision.
- Never select, default, infer or change the Method Plan on the human's behalf; never present a plan as a quality level; never report the unselected fallback as a choice; and never treat any plan as weakening an invariant or as permission to skip a human confirmation.
- Never turn deterministic work into a question, never stop at an intermediate mechanical step, and never use lower friction as a reason to skip a human confirmation, a gate or the Human Promotion Boundary.
- Never raise a question, a confirmation, a questionnaire turn, a proposal, an authorization request or a report on behalf of GTT without opening it with `@gtt · <what this is>`; never put the marker on ordinary work; and never treat the marker as a decision, an approval or evidence.
- Never ask for approval of ordinary work - implementation, refactors, tests, Stories - and never turn it into a proposal, a confirmation or a change request.
- Never stop work for an observation that is not `BLOCKING`, and never treat anything as blocking without an explicit governance basis you can name.
- Never decide an observation and never freeze: `gtt-observe.sh accept | reject | defer` and `gtt-freeze.sh` are the human's.
- Never establish by judgment a fact a script can compute, and never act as the governance supervisor of another agent.
- Never read freeze as "the code cannot change", and never look for an unfreeze: a governed change is completed by a new freeze.
- Never invent Epics and present them as user-defined requirements, never write an Epic's `Approved`, and never add or remove an Epic or change its goal or scope without the human's decision.
- Never let an Epic or a Story in `gtt-domain/backlog.md` silently override governed context or an accepted ADR.
- Never copy governed context into the backlog, and never treat the backlog as a source of architecture.
- Never write a Story's closure you did not verify, and never mark an Epic `Completed` while one of its Stories is open.
- Never generate a scaffold artifact (`gtt-domain/change-request.md`, `gtt-domain/backlog.md`, `gtt-domain/session.md`, or the files under `.gtt/docs/`) at a temporary location and move it into place afterward — write it where `.gtt/scaffold/manifest.yaml` places it, directly.
- Never bypass a GTTGuard-protected artifact's approval requirement — not by renaming or removing its marker without authorization, not by editing around the enforcing hook, and not by hand-editing `.gtt/protection/registry.yaml`.
- Never treat approval of one GTTGuard proposal as authorization for a different protected artifact, and never confuse its lightweight, in-conversation promotion with the L0/L1 Human Promotion Boundary.

## The two planes

GTT has two planes, and an agent always knows which one it is standing in.

| | Governance plane | Work plane |
|---|---|---|
| Answers | What the system is supposed to be | What is actually happening |
| Holds | intent, architecture, constraints, ADRs, Epics (goal and scope), protected artifacts, the boundaries, the freeze | implementation, tests, refactors, Stories; commits only as gtt-domain/workflow.md allows |
| Who decides | the human - always, in every Method Plan | the ADE - autonomous by default |
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

During work GTT observes; it does not approve. `.gtt/scripts/gtt-observe.sh`
compares the project with the frozen governed state - Git, the filesystem,
dependency manifests, the GTTGuard registry, the freeze baseline: computed facts,
never a model's opinion - and keeps every meaningful deviation in the governance
backlog (`gtt-domain/governance-backlog.json`). The boundaries it watches are
declared in the `gtt-boundaries` block of `gtt-domain/context/stack.md`, which the
human ratifies at freeze.

| Level | What it is | What you do |
|---|---|---|
| `NOTICE` | informational | nothing - it is recorded |
| `WARNING` | meaningful drift | say it in one line and keep working |
| `GOVERNANCE` | a boundary of the design was crossed | say it and keep working; if the design itself must change, draft the proposal |
| `BLOCKING` | a state the governed design prohibits | stop the affected operation, fix it or tell the human; everything else continues |

The levels are named, never numbered: L0 and L1 already mean the governed context
and the ADRs.

- **Continue unless blocking.** Only a `BLOCKING` observation, or one the human
  explicitly rejected, interrupts work. An observation that is not blocking is
  never a reason to stop, to ask for approval or to wait.
- **Blocking is explicit.** Something stops only because the governed state says
  so - a boundary declared `BLOCKING`, a rejected observation, a governed path, a
  GTTGuard artifact - and the block names its rule. Never treat something as
  blocking because it looks unusual.
- **Run it; do not reason it.** Observe by running the script - after a meaningful
  change, and it also runs whenever `gtt-status.sh` does - never by judging the
  diff yourself. A fact a script can compute is not established by an agent's
  opinion, and no agent supervises another agent as governance.
- **Silent by default.** No signal, no message. Report an observation once, when
  it is new.
- **The decisions are the human's.** `gtt-observe.sh accept | reject | defer`,
  `gtt-freeze.sh` and `gtt-git-hook.sh install | remove --apply` are run by the human,
  never by an agent, and an agent never writes `gtt-domain/.frozen` or
  `gtt-domain/governance-backlog.json` itself. Accepting an observation
  ratifies nothing: if the governed design must change, that is still a change
  request and a new freeze.
- **A proposal is not an approval request.** Write one when something may need a
  governance decision - never to ask permission for ordinary work.

`.gtt/scripts/gtt-git-hook.sh install` (the human's choice) runs the same check
before each commit: Git is the first control every ADE shares, whatever hooks an
ADE has or lacks. It is not the guaranteed one - a local pre-commit hook is skipped
with `git commit --no-verify`, which an agent never does while the hook is installed.
The guaranteed layer is CI: `gtt-validate.sh` and `gtt-check-stack.sh` on the pull
request, which also fail when the freeze marker was removed or its history rewritten.

The architecture as data: `.gtt/contract/profiles.json` -> `two_planes`.

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

Generating a proposal, an ADR draft or a promotion set is never itself approval —
each governed promotion needs its own explicit human decision, and approving one
change does not carry over to the next.

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

If a host project already contains:

- `AGENTS.md`
- `readme-gtt.md`
- `readme-gtt.es.md`
- `SOURCE-BRIEF.*`
- `.gtt/` (the Engine: scripts, index, protection, session-adapters, `docs/`, `scaffold/manifest.yaml`)
- `gtt-domain/` (`context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen`)

- `.claude/`
- `.kiro/`
- `.github/instructions/gtt.instructions.md`
- `.cursor/rules/gtt.mdc`, `.cursor/rules/gtt-implementation.mdc`, `.cursor/hooks.json`
- `.agents/skills/gtt/SKILL.md`, `.openhands/hooks.json`
- `.agents/rules/gtt.md`, `.agents/rules/gtt-implementation.md`, `.agents/hooks.json`

inspect before changing.

Report conflicts explicitly.

Do not silently overwrite.

Preserve the host project's existing source structure.

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

**What keeps Stories honest is observation, not approval.** If the work behind a
Story crosses a boundary of the frozen design - a new backbone technology, a
changed contract - observation reports it whatever the Story said, and that is
where governance enters (*The two planes*).

**Work the human asks for directly needs no Epic first.** Do it, and record it
under *General Development Work*, or as a Story if it is worth resuming. If
defined Epics exist elsewhere (a requirements document, an issue tracker) but
are missing from the backlog, report the gap. Never invent business Epics and
present them as user-defined requirements: a proposed Epic stays `Proposed`
until the human approves it.

An Epic is `Completed` only when every one of its Stories is `Done` or
`Cancelled`. `.gtt/scripts/gtt-check-backlog.sh` keeps the structure sound -
unique ids, the status vocabulary, an Epic that is `Planned`, `In Progress` or
`Completed` carries its `Goal` and its `Approved`, a `Completed` Epic has no
open Story - and reports, without failing, a `Done` Story with no `Closed` and
Stories being worked under an Epic that is still `Proposed`. It approves
nothing; whether an Epic is real and current is a judgment for the `gtt-audit`
skill.

## Agent roles and the evidence boundary

GTT distinguishes four responsibilities. No skill or script may collapse
them into one:

| Role | Does | Never does | This repo's mechanism |
|---|---|---|---|
| Grounding | Retrieves and exposes governed evidence faithfully | Decide architecture | `gtt-bootstrap`, `gtt-audit` reading `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/backlog.md` |
| Reasoning | Analyzes evidence, drafts gtt-domain/proposals/ADRs | Authorize its own draft | `gtt-propose-change`, `gtt-adr`, `gtt-drift-response` |
| Validation | Runs deterministic structural checks | Make an architectural judgment | `.gtt/scripts/gtt-check-*.sh`, `gtt-validate.sh` |
| Observation | Computes what the work did against the frozen governed state and records it | Approve, decide or block without an explicit rule | `.gtt/scripts/gtt-observe.sh` |

The chain is: Sources → Grounding → Evidence Dossier (governed context as
read) → Reasoning → Proposal → Human Decision → Freeze. A reasoning step
must never receive raw sources "for context" in a way that bypasses
grounding — read `.gtt/docs/docs.md` → *Governance model* for the full
rationale. Producing output, of any kind, never grants an agent decision
authority.

## The rest of the contract

The sections below are part of this contract and bind exactly as the ones above. Their full text
lives in `.gtt/docs/agents/`, so that this file stays small enough for every ADE to read whole.
Read the one a task needs before doing that task.

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

## Method Plans

In `.gtt/docs/agents/bootstrap.md` → *Method Plans*.

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
