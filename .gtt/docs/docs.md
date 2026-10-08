# GTT — Reference Docs

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

This document is for humans. It is deliberately outside the agent's context
window: an agent does not need to understand GTT to comply with it, and every
token spent explaining the methodology is a token not spent on the problem.

Three topics, one file — methodology, tool portability, and upgrading from v1.
None of it loads automatically in any tool, so merging costs nothing and saves
a file.

- [Methodology](#methodology) — the model itself: layers, enforcement planes, the change flow
- [Portability: Claude Code, Kiro, Codex, Copilot, Cursor, OpenHands, Antigravity](#portability-claude-code-kiro-codex-copilot-cursor-openhands-antigravity) — what each tool enforces and how to adapt
- [Migrating from GTT v1](#migrating-from-gtt-v1) — file mapping and upgrade steps

---

## Methodology

> When context doesn't govern AI, AI governs the solution.

### The premise

AI accelerates implementation. Humans govern context and architecture.

The failure mode GTT addresses is not bad code — agents write reasonable code.
It is **architectural drift**: a sequence of individually defensible changes that
collectively move the solution somewhere nobody decided to go. Drift is invisible
at the commit level and only visible at the architecture level, which is exactly
the level nobody is reviewing.

### Context layers

| Layer | Contents | Policy | Who edits |
|---|---|---|---|
| L0 | `gtt-domain/context/` — the map, vision, architecture, principles, constraints | propose only | Solution Designer |
| L1 | `gtt-domain/adr/` — accepted decisions | propose with review | Solution Designer |
| L2 | `.gtt/docs/` — diagrams, specifications | editable with review | anyone |
| L3 | `src/`, `tests/`, pipelines, infrastructure code | editable | agents and humans |

The layer determines two things: **who may edit** and **when it loads into
context**. Earlier versions of GTT only defined the first, which is what made
the model expensive — every layer loaded on every session regardless of
relevance.

### The three enforcement planes

GTT's guarantees do not come from asking the agent nicely. They come from
putting each concern in the plane that can actually enforce it.

| Plane | Mechanism | Guarantee | Cost per session |
|---|---|---|---|
| Control | `permissions.deny`, PreToolUse hook | Deterministic | Zero context |
| Build | `.gtt/scripts/gtt-check-stack.sh` in CI | Deterministic, after the fact | Zero context |
| Instruction | `AGENTS.md`, `.claude/rules/` | Probabilistic | Tokens |
| Procedural | `.claude/skills/` | On demand | Zero until invoked |

The rule: **anything that can be enforced in the control plane must not be
written as an instruction.** An instruction is a request the model may decline
under pressure; a deny rule is not. Writing "AI must not modify L0 files" into
context is strictly worse than blocking the write — it costs tokens every
session and holds only probabilistically.

Instructions remain necessary for everything that requires judgment: whether a
change is architectural, whether code contradicts context, whether an
abstraction is warranted. No permission rule can decide those.

The drift detector (`detect-drift.py`, see [Drift detection](#drift-detection))
lives in the control plane too — a deterministic hook, zero tokens per
session — but its output is advisory, not a block. It is not a fifth plane; it
extends the control plane's reach from paths to decisions without making L3
governed territory, since L3 stays free by design.

### What lives where

| Concern | Location | Loads |
|---|---|---|
| Non-negotiable behavioral rules | `AGENTS.md`, imported by `.claude/CLAUDE.md` | always |
| Hard project constraints | `gtt-domain/context/constraints.md`, imported by `.claude/CLAUDE.md` | always |
| Rules for one area of the codebase | `.claude/rules/*.md` with `paths:` | when touching matching files |
| Proposal, ADR, audit procedures | `.claude/skills/*/SKILL.md` | when invoked |
| The stack and architecture map | `gtt-domain/context/stack.md` | when the task needs it |
| Architecture prose, vision, principles | `gtt-domain/context/` | when the task needs them |
| Accepted decisions | `gtt-domain/adr/` | when the task needs them |
| Change requests | `gtt-domain/change-request.md` | never |
| Agent drafts awaiting review | `gtt-domain/proposals/` | never |
| GTTGuard protection registry (derived, never hand-edited) | `.gtt/protection/registry.yaml` | never |
| Session state (derived, never hand-edited) | `gtt-domain/session.md` | never |
| This document | `.gtt/docs/` | never |

### The governed domain (`gtt-domain`)

> **Status — applied.** A layout change within v2.1 moved the Engine to `.gtt/` (with GTT's own documentation in
> `.gtt/docs/`) and gathered everything the method governs under `gtt-domain/`. Before it,
> the Engine was formerly `gtt/`, and the governed state and the documentation sat at the project root.


GTT-Method separates **how the method works** from **what the method is applied to**:

| | `.gtt/` — the Engine | `gtt-domain/` — the domain |
|---|---|---|
| Is | GTT-Method's own machinery and its documentation, plus the state it derives — none of it is architectural authority | GTT-Method's definition of the project or domain it governs |
| Holds | `index/`, `protection/`, `scaffold/`, `scripts/`, `session-adapters/`, `.gtt/docs/` | `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/proposals/`, `gtt-domain/backlog.md`, `gtt-domain/change-request.md`, `gtt-domain/session.md`, `gtt-domain/.frozen` |
| Answers | *How do identity, protection, validation and session memory work, and how is GTT used?* | *What is this system, what was decided, and what may change?* |

GTT's own documentation (this file, the installation and usage guides, the evidence and completion
records, the session-adapter contract) belongs to the **Engine**, in `.gtt/docs/`, not to the domain:
it explains the method, it does not define the project.

**`gtt-domain/` is the contextual space over which GTT applies the method.** Context is the source of
truth (ADR-001): `gtt-domain/context/` (L0) says what the system is, `gtt-domain/adr/` (L1) records why it is that way,
`gtt-domain/proposals/` holds what is waiting for a human decision, `gtt-domain/backlog.md` is the development line, and
`gtt-domain/.frozen` marks the moment the domain became governed. The domain is therefore not "documentation
about GTT" — it is the governed subject of the method, the one place an agent is told to read before
acting and forbidden to rewrite once frozen.

Two rules follow, and they are what the split exists to keep true:

- **Architectural authority stays in the domain, and executable GTT logic stays in the Engine.**
  Authority (L0/L1) lives only in `gtt-domain/context/` and `gtt-domain/adr/`; nothing in `.gtt/` is a
  governed decision — its index and protection registry are derived, and its documentation is a
  reference. The domain holds no executable GTT logic *in operation*: `gtt-domain/proposals/` holds
  governed **drafts** — proposals, ADR drafts, staged context files and promotion scripts — that the
  domain never executes and an agent never runs (a human does, under the Human Promotion Boundary).
  `AGENTS.md` and the ADE overlay are instructions to agents, and belong to neither group.
- **The code the project builds (L3: `src/`, `tests/`, infrastructure) belongs to neither.** The domain
  governs it by reference — the architecture map, the dependency rules and the boundaries — and
  never contains it.

For an adopting project the split also reduces GTT's footprint at the project root to the two names
`.gtt/` and `gtt-domain/` (plus the entry points `AGENTS.md`, `readme-gtt*.md`, `SOURCE-BRIEF.*` and the
ADE overlay), so a project's own `docs/`, `context/`, `adr/` or `proposals/` directories no longer collide
with GTT's.

### The change flow

Governance fails when the compliant path is harder than the workaround. GTT
therefore has exactly one entry point for change, and it is a plain markdown
file that is always in the same place.

```
gtt-domain/change-request.md  ->  gtt-domain/proposals/  ->  Designer reviews + runs script  ->  gtt-domain/adr/ + gtt-domain/context/
     Designer states          agent drafts a           gtt-promote.sh ADR-NNN-*          applied
     intent, 4 lines          promotion package
```

The asymmetry is the mechanism: `gtt-domain/proposals/` is the only governed directory
an agent can write to. An agent that wants to change the architecture
has exactly one move available — write a reviewable draft. There is no path
where it edits the architecture and no path where it silently skips review,
because the alternative is blocked at the permission layer rather than
discouraged in prose.

The last step is the **Human Promotion Boundary**: the agent's draft, however
complete, is not the change. It becomes one only when the Designer reads the
staged promotion set and applies it themselves (`bash .gtt/scripts/gtt-promote.sh ADR-NNN-<slug>`). The agent may
prepare a governed change — analyze it, draft the proposal, draft the ADR,
draft the affected context files, generate the script; it may never promote
one by running that script, editing `gtt-domain/adr/` or `gtt-domain/context/` directly,
or treating its own draft as approval. See `AGENTS.md` → *Human Promotion
Boundary*.

This also removes the friction that kills governance models in practice. The
Designer does not need to remember which of six files to edit, how to format
an ADR, or reconstruct a sequence of commands by hand. They write four lines
in one known location, then review and run one script.

### Governance model

**Human approval required for:** architectural direction, paradigm, module
boundaries, integration strategy, deployment strategy, data model, frameworks,
runtimes, cloud platform and managed services, and any change to L0.

**Agents may:** read and analyze context, detect inconsistencies, propose
changes, draft ADRs and their promotion scripts, and generate implementation
aligned with the governed context.

**The golden rule:** an agent may suggest, analyze, and accelerate. It may not
redefine architecture without explicit approval from the Solution Designer,
and it may not execute a promotion script even after that approval — the
Solution Designer runs it. See *Human Promotion Boundary* in `AGENTS.md`.

**Agent roles and the evidence boundary.** GTT names three responsibilities
that no skill or script may collapse into one — producing output, of any
kind, never grants an agent decision authority:

| Role | Does | Never does | This repo's mechanism |
|---|---|---|---|
| Grounding | Retrieves and exposes governed evidence faithfully | Decide architecture | `gtt-bootstrap`, `gtt-audit` reading `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/backlog.md` |
| Reasoning | Analyzes evidence, drafts gtt-domain/proposals/ADRs/session state | Authorize its own draft | `gtt-propose-change`, `gtt-adr`, `gtt-drift-response` |
| Validation | Runs deterministic structural checks | Make an architectural judgment | `.gtt/scripts/gtt-check-*.sh`, `gtt-validate.sh` |

The evidence boundary is the chain those roles sit on: **Sources → Grounding
→ Evidence Dossier → Reasoning → Proposal → Human Decision → Freeze.** This
is not a new mechanism — it is the change-flow diagram above, named. A
reasoning step (drafting a proposal or an ADR) must never receive raw
sources "for context" in a way that bypasses grounding: it reasons over the
governed context and backlog as read, not over arbitrary source material an
agent decided was relevant. Where the repository cannot enforce this
mechanically (nothing stops a skill's prompt from pasting in extra text),
it is stated here as the operational contract instead — the same honest
gap already documented for the two-regime condition and for GTTGuard on
non-Claude-Code adapters below: an instruction-plane rule, not a claimed
guarantee the tooling doesn't actually have.

### The two planes: Governance and Observation

GTT has two planes. Everything in this document belongs to one of them.

```text
                 HUMAN INTENT
                      │
          ┌───────────▼───────────┐
          │      GOVERNANCE       │  what the system is supposed to be
          │  design, architecture,│  -> the human decides, always
          │  constraints, ADRs,   │
          │  Epics, boundaries    │
          └───────────┬───────────┘
                   FREEZE            the design becomes the authority
          ┌───────────▼───────────┐
          │   WORK / OBSERVATION  │  what is actually happening
          │  the ADE works on its │  -> nobody approves ordinary work
          │  own; GTT observes    │
          └───────────────────────┘
```

> **GTT governs the boundaries. The ADE performs the work.**

The earlier model protected the design by putting the human inside the
development loop: a Story had to be designed and approved before it could be
implemented, and every deviation looked like a reason to stop. That does not
scale - ADEs exist precisely because the development loop can run on its own.
The two-plane model protects the design by moving the human to the right
boundary instead.

**A code change is not a governance change.** Renaming, refactoring, fixing a
bug, adding tests, optimising, reorganising internal code, writing and closing
Stories: ordinary work, done without approval. A new architectural component,
a moved boundary, a replaced governed technology, a changed API contract, a
changed security or data boundary, a violated constraint, a changed Epic
scope: governance, decided by the human through the change flow.

**Freeze is a governance baseline, not code immutability.** `gtt-freeze.sh`
records when, by whom, the commit and a digest of the governed state. Intent
and boundaries are frozen; the implementation is expected to evolve. There is
no unfreeze: a promoted change moves the governed state, and running
`gtt-freeze.sh` again records a new baseline and keeps the earlier one as
history. Run on an unchanged governed state it does nothing.

**Observation replaces continuous approval.** `.gtt/scripts/gtt-observe.sh`
compares the project with the frozen governed state and turns each meaningful
deviation into a signal:

| Level | Meaning | What happens |
|---|---|---|
| `NOTICE` | informational | recorded; never announced |
| `WARNING` | meaningful drift | announced once, recorded; work continues |
| `GOVERNANCE` | a boundary of the design was crossed | announced once, recorded; work continues; someone decides before the next freeze |
| `BLOCKING` | a state the governed design prohibits | the affected operation stops and `check` fails until it is fixed |

The levels are named, never numbered: L0 and L1 already mean the governed
context and the ADRs.

Five properties make this a governance mechanism rather than a nagging one:

| Property | What it means here |
|---|---|
| Deterministic | Facts come from Git, the filesystem, dependency manifests, the GTTGuard registry and the freeze baseline. No model takes part; no agent supervises another agent. *Use computation to detect facts; use governance to decide meaning.* |
| Explicit blocking | Something stops only because the governed state says so - a boundary declared `BLOCKING`, an observation the human rejected, a governed path, a GTTGuard artifact - and the block names its rule. "This looks different" never blocks. |
| Continue unless blocking | A `WARNING` or `GOVERNANCE` observation never stops the work, never asks for approval and never waits. |
| Idempotent | An observation is correlated by rule and artifact. The same state observed ten times is one item, reported once, and the tenth run writes nothing. |
| Silent by default | Compliant work produces no output at all. |

**The boundaries are declared, and the human ratifies them.** The
`gtt-boundaries` block of `gtt-domain/context/stack.md` (section 7) lists the
few places where a change in the code means the design may have changed:

```text
B-001 | path       | infra/**                                  | WARNING    | Deployment topology (section 3)
B-002 | path       | **/openapi.yaml                           | GOVERNANCE | Public API contract
B-003 | dependency | package.json                              | WARNING    | Stack at a glance (section 1)
B-004 | forbid     | src/domain/** :: import .*infrastructure  | BLOCKING   | Dependency rules (section 5)
```

`path` fires when a matching file changed since the freeze; `dependency` when
a manifest gained a dependency it did not have at the freeze (so "the ADE
decided to bring in Kafka" surfaces as `package.json#kafkajs`, whatever the
Story said); `forbid` when a matching file contains a pattern. Two boundaries
are built in and need no rule: the governed context itself moving
(`GTT-GOVERNED`) and a `@GTTGuard` artifact changing (`GTT-PROTECTED`).
Because the block lives in governed context, freezing it is what ratifies
each rule - and that ratification is the only thing that lets observation
stop anything.

**The governance backlog.** Observations live in
`gtt-domain/governance-backlog.json`, written only by the engine:

```text
detected -> open -> accepted | rejected | deferred -> resolved
```

`gtt-observe.sh accept | reject | defer OBS-NNNN --by <name> --apply` are the
human's decisions, never an agent's. *Accepted*: the deviation stands, and is
raised again only if the artifact changes; it ratifies nothing - a design that
must change still goes through a change request and a new freeze. *Rejected*:
`check` fails for as long as it is still observed - a veto that needs no
standing in the loop. *Deferred*: kept, silent. An observation that is no
longer true resolves itself.

**Where it runs.** No ADE-specific machinery is required:

| Trigger | What runs | Blocks? |
|---|---|---|
| `gtt-status.sh` (every session start, in every ADE) | `observe` | no |
| After a write, on ADEs with a post-write hook (Claude Code, Kiro) | `observe` | no |
| `gtt-validate.sh`, `gtt-maintain.sh`, CI | `check` | only `BLOCKING` or rejected |
| `gtt-git-hook.sh install` (a Git pre-commit hook, the human's choice) | `check` | only `BLOCKING` or rejected |
| A pre-write hook, on ADEs that have one | the `BLOCKING` *path* rules only | yes, naming the rule |
| `gtt-freeze.sh` (a new freeze) | `check --strict` | an undecided `GOVERNANCE` observation refuses the new baseline |

Git is the first control every ADE shares: whichever agent made the change, it
reaches the repository through a commit. It is not the guaranteed one - a local
pre-commit hook is skipped with `git commit --no-verify`. The guaranteed layer
is CI: `gtt-validate.sh` and `gtt-check-stack.sh` on the pull request.

**What an agent cannot do, and where that is enforced.** These are not approval
gates on work; they are the acts that would let an agent rewrite the authority
it works under. On an ADE with a pre-tool hook they are denied in real time, by
one decision core that is byte-identical in Claude Code's hook
(`.claude/hooks/protect-l0.py`) and in the portable engine
(`.gtt/scripts/gtt_protect.py`), and every denial names its rule:

| Act | Rule |
|---|---|
| Removing or writing `gtt-domain/.frozen` (an unfreeze, or a freeze nobody decided) | `freeze-semantics` |
| Editing `gtt-domain/governance-backlog.json` directly (forging an accept or a reject) | `human-decision-authority` |
| Running a promotion - `gtt-promote.sh`, or a `gtt-domain/proposals/apply-*.sh` script - in any spelling, or applying a patch staged there (`--check` / `--stat` stay available) | Human Promotion Boundary |
| With `commits: never` in `gtt-domain/workflow.md`: `git commit`, `git tag`, `git push`. With `branches-tags: never`: a new branch or tag | `workflow.md: commits: never` / `branches-tags: never` |
| In an installed project: writing `gtt-domain/workflow.md` | `workflow.md` |
| Writing `.gtt/local/checkpoint.json` or `.gtt/local/last-validation.json` | `deterministic-first` |
| Freezing; accepting, rejecting or deferring an observation; installing or removing the Git hook | `human-decision-authority` |
| With the Git hook installed: `git commit --no-verify`, changing `core.hooksPath`, deleting the hook | `explicit-blocking` |
| Writing under a path boundary the frozen design declares `BLOCKING` | the boundary's own id |

Two things hold where no hook can: `gtt-check-stack.sh` fails in CI when the
base ref was frozen and the freeze marker is gone ("there is no unfreeze") or
no longer carries the baseline the base recorded ("freeze history rewritten");
and if the observation engine cannot be loaded while the frozen design declares
a `BLOCKING` boundary, the hook still lets the session continue but says, out
loud, that the write was not checked. A write made by an interpreter
(`python -c "open(...)"`) or by Git plumbing (`git checkout <ref> -- <path>`)
is not seen by any pre-tool hook: that residual is exactly what the CI gate
covers, and GTT does not chase it with more patterns.

The CI gate holds only if three things are true, and the Bootstrap cannot make
any of them true by itself. The checkout has the base ref (full history): without
it a removed marker looks exactly like a project that was never frozen, so in CI
(`CI=true` or `--ci`) `gtt-check-stack.sh` exits 2, "cannot determine", and
outside CI it says that the check did not run - it never passes in silence. The
workflow exists: `.gtt/scaffold/ci/github-actions-gtt.yml` is a template the
human installs (`gtt-template.sh materialize ci-github-actions --apply`), never
an agent. And the job is a **required status check** under branch protection:
a failing job that is not required blocks no merge.

Under a Method Plan whose gate `governance_observation_fails_check` is true
(Hard, Team) an undecided `GOVERNANCE` observation fails `check` as well;
under the others only `BLOCKING` and rejected observations do.

**What stays exactly as it was.** Human authority over governed intent; the
evidence boundary and provenance tags in THINK; OPEN and BLOCKING gaps; the
no-unfreeze principle; ADR traceability; the Human Promotion Boundary;
protected artifacts. Provenance is mandatory where governed knowledge is
established or modified - it is not something a line of implementation, or a
Story, has to carry.

The architecture as data: `.gtt/contract/profiles.json` -> `two_planes`.

### Two regimes

`gtt-domain/context/`, `gtt-domain/adr/`, and `SOURCE-BRIEF.*` are not protected
unconditionally — they are protected only once something has actually been
ratified. Enforcement is split into two regimes, discriminated by
the marker file `gtt-domain/.frozen`:

| Regime | Condition | Those paths |
|---|---|---|
| Pre-freeze | `gtt-domain/.frozen` absent | writable by the agent |
| Governed | `gtt-domain/.frozen` present | denied |

This exists because the alternative — one unconditional deny — is wrong at the
moment a project is created, when the six context files are still template
placeholders and there is nothing ratified to protect yet. `gtt-bootstrap`
writes them directly in this window; the Solution Designer then runs
`.gtt/scripts/gtt-freeze.sh`, which refuses to ratify placeholder content and
writes the marker only once L0 is real. From that point the project is
governed and those paths are read-only for agents again.

Governance machinery — `AGENTS.md`, `.claude/settings.json`, `.claude/hooks/`,
`gtt-domain/change-request.md`, the Kiro equivalents, and the marker itself — has no
regime exception. It is denied in both regimes, always: an agent never drafts
its own directives or its own enforcement.

### The map

`gtt-domain/context/stack.md` is the one page that answers "what is this system" in a
single screen: the stack table, the component map, the deployment topology, the
observability view, the dependency rules, and the change log. It is written in Markdown and Mermaid, so it renders in
GitHub and any IDE without an image to regenerate and without a diagram tool to
keep licensed.

It is governed at L0 and updated in the same change as the ADR that approves the
architectural decision. Three mechanisms hold that line, in descending strength:

1. **CI gate** — `.gtt/scripts/gtt-check-stack.sh` fails the build when an ADR
   changes and the map does not.
2. **ADR procedure** — the `gtt-adr` skill requires a stack map delta section
   with before/after rows; an ADR without one is incomplete.
3. **Audit** — the `gtt-audit` skill checks each map claim against dependency
   manifests, the real import graph, and deployment definitions.

A row in "Stack at a glance" with no ADR in its "Locked by" column is a finding
in its own right: a decision that entered the system without passing through
governance.

### Context freshness

A stale context file is worse than a missing one — it produces confident,
consistent, wrong behavior across every agent in the project.

Context freshness is therefore an operational responsibility, not a
documentation chore. Run the `gtt-audit` skill before releases and after large
merges. When implementation and context diverge, the Solution Designer decides
which one is wrong; the agent is not permitted to assume the code is right.

### Drift detection

The control plane above protects paths, L3 is free by design, and a change
there can contradict a ratified decision without touching any denied path —
editing `docker-compose.yml` can silently override a datastore decision locked
in `stack.md`. Drift detection extends the control plane from paths to
decisions without making L3 governed territory.

**One engine, several triggers.** The `gtt-boundaries` block declared inside
`gtt-domain/context/stack.md` (L0, ratified at freeze) names the places outside
the governed tree that carry architectural weight, and the level each one has.
One engine, `.gtt/scripts/gtt-observe.sh`, computes what crossed them - see
[The two planes](#the-two-planes-governance-and-observation) for the levels,
the governance backlog and where it runs. A single skill,
`gtt-drift-response`, is the only path from an observation to a proposal
draft, and only when the governed design itself must change.

1. **After a write.** On Claude Code, `detect-drift.py` (a `PostToolUse` hook)
   runs the engine and hands whatever is new to the agent as context. It holds
   no logic of its own and never blocks.
2. **At session start, in validation and at commit.** `gtt-status.sh` runs
   `observe`; `gtt-validate.sh` and the optional Git pre-commit hook run
   `check`. These see shell mutations too, which a post-write hook cannot.
3. **Sweep.** `gtt-audit` runs the same engine, then judges what the engine
   cannot: what an observation means, and what no boundary covers.

Operates only under the governed regime - before the first freeze there is no
baseline to compare against. An earlier `gtt-drift-signals` block is still
read, as path boundaries at `WARNING`.

### Backlog governance

`gtt-domain/backlog.md` is the development line. It is a planning artifact,
not architecture, and it must never become a second source of truth beside
`gtt-domain/context/`. It holds two kinds of entry, governed differently.

**Precedence:**

```
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

The backlog never silently overrides architecture; what happens when an Epic or a Story contradicts it is stated once, in `AGENTS.md` → *Backlog* (*Precedence*).

| Entry | What it is | Who decides |
|---|---|---|
| **Epic** | Intent and scope: `Goal`, `Scope`, `Out of Scope` | The human. `**Approved:** who — YYYY-MM-DD`; until then it stays `Proposed`. Adding, removing or materially changing one goes through `gtt-propose-change` (form 4) |
| **Story** | The working plan inside an approved Epic | The ADE. It creates, splits, rewrites, implements and closes Stories on its own. Nobody approves a Story |

**Why Stories are not a gate.** An earlier version required every Story to be
designed and approved, one by one, before it could be implemented. That put
the human in the inner loop of ordinary work and bought little: a Story is a
plan for *how to get there*, not a decision about *what the system is*. What
actually needs protecting is the design, and a signature on a Story does not
protect it - observation does. If the work behind a Story introduces a new
backbone technology or changes a contract, the engine reports it whatever the
Story said, and that is where governance enters.

A Story is worth writing when it helps the next session resume: what it
delivers, how one knows it is done, and - once done - `Closed`: the date and
what closed it (commit or PR, tests passed), from what actually happened.

`gtt-domain/backlog.md` is **not** in `permissions.deny` and no hook blocks
it. One deterministic backstop keeps its structure sound:
`.gtt/scripts/gtt-check-backlog.sh` fails on duplicate Epic/Story ids, a status
outside the vocabulary, an Epic that is `Planned`, `In Progress` or
`Completed` without its `Goal` or its `Approved`, and a `Completed` Epic with
an open Story. It *reports*, without failing, a `Done` Story with no `Closed`
and Stories being worked under an Epic still `Proposed`. Whether an Epic is
real, current and matches the work being done is the `gtt-audit` *Backlog
reconciliation* pass's job.

**Work the human asks for directly needs no Epic first.** It is done, and
recorded under *General Development Work* or as a Story if worth resuming.
When Epics are defined elsewhere (a requirements document, an issue tracker)
but missing from the backlog, that gap is reported - never silently ignored,
and never filled with invented business Epics: a proposed Epic stays
`Proposed` until the human approves it.

A backlog written under the earlier model still reads: `Undesigned`, `Ready`
and `Proposed` Stories are treated as `Planned`.

**Why not just another ADR-governed file?** An ADR records a decision that,
once made, rarely changes shape again. A Story is expected to move through
statuses constantly as normal work happens — routing every status flip
through `gtt-domain/change-request.md` would make the backlog too expensive to keep
current, and a stale backlog is worse than no backlog (same failure mode as
stale context). The bar is calibrated to what actually needs a human
decision: *what* the project commits to building, not *how far along* it is.

### Provenance, gaps, sources and working agreements

Recovered from CDAD as semantics, not as a parallel system: they reuse the governed artifacts, the
index stays derived and no new authority appears. The rules are in `AGENTS.md` → *Provenance, gaps,
sources and working agreements*. In short: `[FUENTE: ref]` / `[VACÍO: GAP-id]` /
`[CONFLICTO: a vs b]` are allowed in governed context, `[PROPUESTA]` is not; a BLOCKING gap refuses freeze
and an OPEN gap (always scoped) does not and authorises nothing; sources carry authority and an
unambiguous precedence that orders a conflict without erasing it; working agreements sit below governed
context. The one gate is `.gtt/scripts/gtt-check-provenance.sh` (sub-checks: `tags`, `gaps`, `sources`,
`preferences`); `gtt-status.sh` prints the counts and `gtt-query.sh --governance open|blocking|resolved|conflicts|sources|agreements`
lists them from the artifacts. Limits: the checks are lexical and structural — they cannot judge whether a
`[FUENTE]` really supports a claim or whether a scope is wise; that stays a human judgment.

### GTTGuard: protected artifacts

`gtt-domain/context/` and `gtt-domain/adr/` govern architecture. `gtt-domain/backlog.md` governs
the development line. GTTGuard governs neither — it is a **sibling**
mechanism that lets a developer flag an individual file, class, or method
so an agent may read and propose a change to it, but never modify it
autonomously. Conflating it with L0/L1 or with the Human Promotion Boundary
below is a mistake this document exists to prevent.

**The marker.** A developer adds `@GTTGuard` (Java, Python), `[GTTGuard]`
(C#), or `// @GTTGuard` / `# @GTTGuard` (comment-based languages, e.g.
JS/TS) immediately above a declaration — or as the file's first line to
protect the whole file — optionally with `reason="..."` and
`source="..."`. Placing or removing the marker is an ordinary L3 edit: it
*is* the developer's proposal ("User proposes → GTT implements → Agent
respects"), not a protected change in its own right.

**The registry is derived, not authored.** `.gtt/scripts/gtt-guard-sync.sh`
scans source for markers, resolves each one's file/class/method
deterministically — brace-balance matching for Java/C#/JS/TS, indentation
matching for Python, never an LLM's judgment — and regenerates
`.gtt/protection/registry.yaml` in full. This is the same trust model as a
lockfile: the registry is committed for reviewability, but hand-editing it
is self-defeating, because `.gtt/scripts/gtt-check-protection.sh` fails the
build the moment the committed file no longer matches a fresh regeneration
from source. No write-block is needed on the file itself; the drift check
makes tampering with it pointless rather than merely forbidden.

**Real-time enforcement (Claude Code).** `.claude/hooks/protect-guard.py`,
a `PreToolUse` hook registered alongside `protect-l0.py`, blocks an
autonomous edit to a `HUMAN_APPROVAL` entry. A file-scope entry blocks the
whole file, the same way `protect-l0.py` blocks a machinery path. A
class/method-scope entry resolves that symbol's exact current line span
*live against the file on disk* — never a cached value, so it can never go
stale — and blocks only an edit that overlaps it: an unprotected sibling
method in the same file stays freely editable. Whenever that resolution is
ambiguous, the hook fails safe to blocking the whole file rather than
risking a silent bypass. A mutating-looking Bash command naming a
protected file is always blocked outright, for the same reason
`protect-l0.py` takes no chances with shell commands against machinery:
there is no way to inspect a shell command's line-range effect on a file.

**Deterministic validation.** `gtt-check-protection.sh` is the CI gate:
registry-drift, artifact/symbol resolution, protection-value validity, and
`source: "ADR-NNN"` existence are all checked unconditionally; a protected
artifact that changed in the diff must also be accompanied by a change
under `gtt-domain/proposals/` or `gtt-domain/adr/`, or the build fails. This is the one
real enforcement layer on Kiro, Codex, and GitHub Copilot, none of which
has a real-time equivalent — the same honest limitation already documented
for the two-regime `gtt-domain/context/`/`gtt-domain/adr/` condition below. GTTGuard
never claims a guarantee an ADE does not actually provide.

**Changing a protected artifact.** `gtt-propose-change` gets a fifth form
for exactly this. Once the Solution Designer approves it **in
conversation**, the agent implements the change directly, updates or
removes the marker, and re-syncs the registry — no ADR, no promotion set
script. This is deliberately lighter than the Human Promotion Boundary:
GTTGuard protects L3 code a developer opted into protecting, not governed
context, and is deliberately not a second, unrelated approval model — it
reuses the existing proposal mechanism, nothing heavier.

### Status and validation

`.gtt/scripts/gtt-status.sh` derives a deterministic snapshot from
repository artifacts — freeze state, Stories currently
`In Progress`/`Blocked`, pending files under `gtt-domain/proposals/`, whether
`gtt-domain/change-request.md` has been filled in, every ADR and its status, and
the GTTGuard protected-artifact count, artifact identity/index health, and
repository resume hints (branch, uncommitted count, recent commits) — and writes it to `gtt-domain/session.md`.
That file is a **derived artifact**, the same trust model as
`.gtt/protection/registry.yaml`: never hand-edited, safe to regenerate at
any time, and never loaded automatically by any agent. It exists so a
project resumes the same way regardless of which ADE's session picks it up
next — session continuity that does not depend on any tool's private
conversation memory. It is operational context only: never architectural
authority, never evidence, never a substitute for an ADR or decision
record, and no agent may invent it from memory instead of running the
script.

`.gtt/scripts/gtt-validate.sh` runs the existing deterministic check scripts
(`gtt-check-backlog.sh`, `gtt-check-adapter.sh`, `gtt-check-protection.sh`,
`gtt-check-stack.sh`, `gtt-check-markdown.sh`, `gtt-check-agents.sh`, `gtt-check-integrity.sh`) in sequence and reports PASS / FAIL /
CANNOT-DETERMINE per check — it does not reimplement any of their logic,
only aggregates it. The adapter check has two regimes. When `.gtt/ade.json`
exists it validates every participating ADE against it: a missing or
inconsistent integration FAILS, and a detected ADE that does not participate is
a WARN, never a pass. Without it, the check is skipped, not failed, when zero or
more than one adapter is present, since this source repository is the
catalog and legitimately ships every adapter — that is not the "wrong
adapter installed" violation the check exists to catch on an installed
project. `gtt-status.sh` also reports the ADE integration state (Primary,
participating, integration health) in `gtt-domain/session.md`; it records no
"last active ADE", because several ADEs may run at once and no deterministic
source for it exists.

Neither script makes an architectural judgment; both are read-only.

### Artifact identity and the technical index

GTT treats the repository as a set of *identifiable, related, traceable*
artifacts, not a pile of Markdown files. Paths may change; identity,
traceability, and provenance must not be lost.

| File | Role | Authority |
|---|---|---|
| `.gtt/index/artifacts.json` | **Identity manifest**: stable `id`, `type`, current `path`, `history` (former paths), `aliases` (intentional copies) | Authoritative for identity — changed by `gtt-index.sh` / `gtt-reconcile.sh`, reviewed in the diff |
| `.gtt/index/technical-index.json` | **Technical index**: documents, sections (heading, anchor, line span), concepts, references / referenced-by, `supersedes`, provenance, authority, version, content hash | **Derived accelerator.** Rebuildable from the Markdown; never a source of truth; a stale one fails the build |

Ids are path-independent: `ADR-007` is `ADR-007` in `gtt-domain/adr/` or
`gtt/architecture/adr/`. Reference an artifact as `[[ADR-007]]` and the
reference survives any move; relative Markdown links are reconciled
automatically when a move is applied. Code spans and fenced blocks never
count as references.

| Script | Does |
|---|---|
| `gtt-index.sh` | Registers new artifacts, rebuilds the index. Refuses while a registered path is missing (an unreconciled move) so a move is never silently recorded as delete + create |
| `gtt-reconcile.sh [--apply] [--map OLD=NEW] [--retire ID]` | Detects moves (git rename hint → same identity → content similarity), records old path as history, rewrites relative links. Dry-run by default; never rewrites a frozen `gtt-domain/context/`/`gtt-domain/adr/` file, it reports it |
| `gtt-check-integrity.sh` | Fails on unreconciled moves, unregistered artifacts, duplicate logical identity, broken links, links via an old path, unresolved `[[ID]]`, stale index. Part of `gtt-validate.sh` |
| `gtt-query.sh <term \| ID[#anchor]> [--show] [--deep]` | Section-level retrieval: locate via the index, read only the needed lines from the Markdown |

Scope is the GTT kit (the same set `gtt-check-markdown.sh` covers);
`gtt-domain/session.md` is derived and excluded. Git is a rename *hint* only —
correctness never depends on it, and GTT does not replace Git.

An agent never owns identity: it works through these scripts and contracts.
A move of a governed file remains a human/governed act; this tooling only
makes the aftermath deterministic.

### Session memory boundary

`gtt-domain/session.md` (see *Status and validation*) is GTT's session-memory
service. Its boundary:

| Kind | Where | Authority | Agent may write? |
|---|---|---|---|
| Governed project state | `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/backlog.md` | Authoritative | Only via the change flow |
| Grounding / evidence | governed artifacts + technical index (as a locator) | Evidence | No — read faithfully |
| Session memory | `gtt-domain/session.md` | **None** — operational, derived | Regenerated by script only |
| Working preferences | `gtt-domain/working-agreements.md` (team), `.gtt/local/preferences.md` (user, local) | Below governed context | Never self-authored |
| ADE-private memory | the ADE's own store | None to GTT | Out of GTT's scope |

Session memory is reconstructed, never remembered: it is derived from the
freeze marker, backlog, proposals, ADRs, the identity/index state, and Git
(branch, uncommitted count, recent commits) by `gtt-status.sh`. Delete it
and regenerate it — nothing is lost. It is outside the grounding corpus and
`gtt-check-markdown.sh`/the index skip it. The service has one ADE-independent
entry point, and each ADE gets a thin adapter:

```text
GTT Core
   ├── Artifact Identity
   ├── Technical Index
   └── Session Memory Service
          └── .gtt/scripts/gtt-session-context.sh   (ADE-independent; the Core ends here)
                 │
                 └── ADE Adapter Contract          (.gtt/docs/session-adapter-contract.md)
                        ├── Claude Code adapter    installed
                        ├── Codex adapter          staged (Draft)
                        ├── GitHub Copilot adapter staged (Draft)
                        └── Kiro adapter           staged (Draft)
```

> **GTT Core is ADE-agnostic. ADE adapters are integration-specific.**
> Claude Code is one adapter, not part of the Core.

`gtt-session-context.sh` resolves Python (same probe as the other GTT
wrappers), regenerates `gtt-domain/session.md`, verifies it, and prints a payload
headed *operational-only; NOT authority, NOT evidence, NOT a decision
record, NOT a grounding source*. It fails with a real exit code and a
message rather than returning partial context. An adapter only translates
that stdout for its ADE and must not contain GTT logic or hide failures.
The Claude Code adapter is a `SessionStart` hook (warm start on new or
resumed sessions — never `UserPromptSubmit`) that emits the payload as
`additionalContext`; hook commands resolve Python through
`.gtt/scripts/gtt-run-python.sh`, never `python3 X || python X`.

#### Session Memory adapter matrix

**Status: Draft — not a decision.** Full contract:
`.gtt/docs/session-adapter-contract.md`. Each adapter is declared in
`.gtt/session-adapters/<ade>.json`; `gtt-check-session-adapter.sh <ade>` (run by
`gtt-validate.sh`) checks it statically and never runs the ADE. Coverage:
**N1** native session injection · **N2** ADE-loaded session file · **N3**
instruction-based retrieval.

| ADE | Adapter (native path) | Event | Level | Implemented | Static check | Runtime |
|---|---|---|---|---|---|---|
| Claude Code | `.claude/hooks/session-start.py` | `SessionStart` | N1 | installed | PASS | **RUNTIME VERIFIED** — startup and resume both fired the hook (`session_source` observed) and the agent quoted the payload |
| Codex | `.codex/hooks.json` + `.codex/gtt-session-start.sh` | `SessionStart` | N1 | staged | PASS | **NOT VERIFIED** — in a sandbox the hook never executed (documented hook-approval requirement; bypass flag deliberately not used) |
| GitHub Copilot | `.github/hooks/gtt-session.json` + `gtt-session-start.py` | `sessionStart` | N1 (new interactive CLI sessions only) | staged | PASS | **VERIFICATION REQUIRES INTERACTIVE SESSION** |
| Kiro | `.kiro/agents/gtt-session.json` + `.kiro/gtt-session-start.sh` | `agentSpawn` (CLI) | N1 (CLI only, docs disagree) | staged | PASS | **STATICALLY VALIDATED, NOT RUNTIME VERIFIED** — not installed here |

Events per adapter (`verified` = observed at runtime, `documented` = vendor
docs only, `unknown`/`unsupported` as stated by the vendor):

| ADE | startup | resume | clear | compact | fork |
|---|---|---|---|---|---|
| Claude Code | verified | verified (hook fires; delivery not separable from the resumed transcript) | documented | documented | documented |
| Codex | documented | documented | documented | documented | unknown |
| GitHub Copilot | documented | **unsupported** (documented not to fire) | unknown | unknown | unknown |
| Kiro | documented | unknown | unknown | unknown | unknown |

"Static check PASS" means the declaration, registration, service reference,
absence of duplicated logic and silenced errors, the command's output
(markers + declared format) and its visible failure path passed in a sandbox
laid out as installed. It does **not** mean the ADE loads the context.

Known documentation gaps: Kiro's docs disagree on whether `agentSpawn` stdout
reaches the agent and show three hook schemas (this repo's existing
`.kiro/hooks/detect-drift.json` is a fourth shape, unverified). The
compatibility matrix earlier in this document says Copilot has no
programmatic hook; Copilot now documents hooks (`sessionStart`, and per its
reference others), so that row needs re-verification.

### Capability status

Not every mechanism gtt-bootstrap implements is a Canon *requirement* —
some are this tool's particular way of satisfying one. Confusing "exists in
this repo" with "the Canon demands exactly this" is the mistake this table
exists to prevent:

| Mechanism | Status | Note |
|---|---|---|
| Governed context (L0/L1), freeze | CANONICAL | The Canon's core model; not optional |
| Change flow (`gtt-domain/change-request.md` → `gtt-domain/proposals/` → ADR) | CANONICAL | The Canon's one entry point for change |
| Human Promotion Boundary | CANONICAL | Agent prepares, human promotes — non-negotiable |
| Agent roles (Grounding/Reasoning/Validation) | CANONICAL | Named vocabulary from the Canon; mapped onto existing skills here, not a new framework |
| GTTGuard | IMPLEMENTED | A Canon capability; this repo's marker syntax, registry format, and Bash-command heuristic are implementation choices, not canonical requirements |
| Backlog governance (`gtt-domain/backlog.md`) | IMPLEMENTED | Development-line tracking; the Canon requires the precedence rule, not this exact file format |
| Observation (two planes) | IMPLEMENTED | Deterministic observation of the work against the frozen governed state: `gtt-boundaries`, four named levels, an idempotent governance backlog, explicit blocking only |
| Drift detection | IMPLEMENTED | Extends the control plane from paths to decisions; this repo's `gtt-boundaries` block mechanism (earlier `gtt-drift-signals`) is one way to do it |
| Session continuity (`gtt-status.sh` / `gtt-domain/session.md`) | IMPLEMENTED | Satisfies the Canon's ADE-independence requirement for resuming work; the snapshot format is this repo's choice |
| `gtt status` / `gtt validate` | IMPLEMENTED | Deterministic aggregation the Canon asks for; implemented here as bash scripts because that is what this repo already uses, not because the Canon mandates a shell script |
| Artifact identity, integrity & technical index (`.gtt/index/`) | IMPLEMENTED | Canon v2.1 capability; JSON manifest/index, `[[ID]]` reference syntax, and the reconcile heuristics are this repo's choices. The index is derived, never authoritative |
| Working preferences (separate from session state) | IMPLEMENTED | Team file and local user file, both below governed context; `gtt-check-provenance.sh` rejects one that tries to override it. Not runtime-verified outside the rehearsal |
| Provenance, OPEN/BLOCKING gaps, source manifest | IMPLEMENTED | One gate (`gtt-check-provenance.sh`), the gap register in `stack.md`, `gtt-domain/context/sources.md`; wired into `gtt-validate.sh`, `gtt-freeze.sh`, `gtt-status.sh` and `gtt-query.sh --governance`. Optional per project; rehearsed, not run on an installed project |
| Bootstrap 1.0 CLI contracts (`.gtt/contract/`, `gtt-contract.sh`, `gtt-project.sh`) | IMPLEMENTED | Release identity, compatibility negotiation, capability and operation registries, Method Plans (methodology profiles), export policy, recovery, structured status/session/validation; see `.gtt/docs/bootstrap-contract.md`. Rehearsed on disposable copies by `.gtt/tests/bootstrap-acceptance.py`; not run against a real CLI, on Linux/macOS or on an installed project |
| RAG/vector-backed grounding | NOT IMPLEMENTED | Not required by the Canon or this repo's directives; would need its own proposal if ever needed |

### Operational boundary

GTT does not slow implementation down. It prevents accidental architectural
change. Everything under L3 stays fully editable, and the majority of day-to-day
work never touches the governance path at all.

If GTT is producing friction on routine work, the constraints are written too
broadly — narrow them rather than working around them.

---

## Where each thing lives: sources, design, backlog

```text
docs/sources/<ID>/vN/            the original source: copied, versioned, immutable     (evidence)
gtt-domain/context/              architecture, stack, constraints                      (governed)
gtt-domain/adr/                  architecturally significant decisions only            (governed)
gtt-domain/context/design/       the solution design: one file per Epic                (governed)
gtt-domain/backlog.md            Epics (approved intent) · Stories (the ADE's plan)    → cite the design
code
```

- **Sources** are registered with `bash .gtt/scripts/gtt-source.sh add <file> --id <ID> --apply`, which copies
  the file, records its hash and makes it immutable; a new version goes next to the old one. Citations are
  verifiable: `[FUENTE: D:§3.4]` must match a heading of the source.
- **The design of an Epic** is its complete specification - data, rules, flows, interfaces, examples - carried
  over from the sources and cited, never summarised. `gtt-design.sh scaffold EPIC-NNN --apply` starts it,
  `gtt-check-design.sh` checks it is complete, and you approve it together with the Epic:
  `bash .gtt/scripts/gtt-approve.sh EPIC-NNN`.
- **How it is read.** Story → `Implements:` → design → architecture or ADR → the cited section of the source.
  A Story is built from the Story and the design; a source is opened only to verify a citation.
- **Two routes of change, three levels of control.** *Architecture* changes through an ADR. *Specification* -
  an Epic's design - is staged and promoted with one command, recorded as `CHANGE-…` in the map change log, no
  ADR. *Work* - Stories and code - is the ADE's, with no approval. After a freeze both routes end in a new one,
  taken in the same confirmation.

## Continuity, review and Git

Three things, all computed from the repository and none from a conversation:

- **`bash .gtt/scripts/gtt-review.sh`** is the one review surface: what changed since the default
  branch, what it touches, what is risky, what you must decide, the last validation and the next
  step - in at most twelve lines. `--files` lists the files, `--gate` says whether a `BLOCKING`
  condition is open and whether the size of the change calls for a human review. It never says the
  design is right. `gtt-domain/session.md` opens with the same block, so the handoff between
  sessions and your review are one thing.
- **A checkpoint** (`gtt-checkpoint.sh`, called by each ADE's end-of-turn hook) regenerates
  `gtt-domain/session.md` when the work changed. It is never a commit, and it does nothing when
  nothing changed. Another ADE picks the project up from that file, not from a chat history.
- **`gtt-domain/workflow.md`** is where you say how Git is used here: whether the ADE may commit
  (`on-request` by default, `allowed`, or `never`), the commit convention, branches and tags, and
  the size above which a review is recommended. Only you edit it. Without it the ADE commits only
  when you ask, and GTT itself never commits, tags, branches or pushes.

A change that needs your authorization arrives as one promotion set; you apply it with
`bash .gtt/scripts/gtt-promote.sh <name>`, which shows the diff, asks for `apply`, and prints its undo.

## Portability: Claude Code, Kiro, Codex, Copilot, Cursor, OpenHands, Antigravity

GTT v2 separates **content** from **mechanism**. The governed context
(`gtt-domain/context/`, `gtt-domain/adr/`) is plain markdown and is fully portable. What differs per tool is how
that content is loaded and how the L0 protection is enforced.

Nothing in the Engine or the governed domain needs to change to move
between tools. Only the ADE overlay does.
A project installs the adapter of every ADE its human chose to have
participate, with exactly one of them declared Primary — see the ADE adapter
matrix in `README.md` and in `.claude/skills/gtt-bootstrap/SKILL.md` (step 0).
Detection is not participation: an ADE found on the machine or in the repository
is a candidate until the human chooses it. The Primary ADE is a workflow
identifier; it holds no authority over any governed artifact, and instruction
files or overlays (`AGENTS.md`, `.claude/`, `.kiro/`, `.github/instructions/`, `.codex/`, an
ADE's memory) are integration surfaces, never governance.

### Compatibility matrix

| Capability | Claude Code | Kiro | Codex | GitHub Copilot |
|---|---|---|---|---|
| Always-loaded instructions | `.claude/CLAUDE.md` | `AGENTS.md`, or steering `inclusion: always` | `AGENTS.md` | `AGENTS.md` + `.github/instructions/gtt.instructions.md` (`applyTo: "**"`) |
| Reads `AGENTS.md` natively | no — imports it | yes | yes | yes |
| Path-scoped rules | `.claude/rules/` + `paths:` | `.kiro/steering/` + `inclusion: fileMatch` | nested `AGENTS.md` only | `.github/instructions/*.instructions.md` + `applyTo` (GTT ships one, repo-wide) |
| On-demand procedures | Skills | steering `inclusion: manual` / `auto` | prompt or custom command | prompt |
| Declarative file-write blocking | `permissions.deny` | per user, outside the repository - a template the human installs | `[permissions.*.filesystem]` globs | not equivalent |
| Programmatic pre-tool block | PreToolUse hook | `PreToolUse` in `.kiro/hooks/gtt-protect.json` — shipped, **unverified in the ADE** | hooks / sandbox | `preToolUse` in `.github/hooks/gtt-protect.json` (cloud agent and CLI) — shipped, **unverified in the ADE** |
| Governed context in `gtt-domain/context/` and `gtt-domain/adr/` | works | works | works | works |
| CI gate (`.gtt/scripts/`) | works | works | works | works |
| GTTGuard real-time block | yes — `protect-guard.py` | through the same hook — unverified | no — CI gate only | through the same hook — unverified |

Cursor, OpenHands and Antigravity, added after the four above, have their own rows:

| Capability | Cursor | OpenHands | Antigravity |
|---|---|---|---|
| Always-loaded instructions | `AGENTS.md` + `.cursor/rules/gtt.mdc` (`alwaysApply`) | `AGENTS.md` | `AGENTS.md` + `.agents/rules/gtt.md` (`trigger: always_on`) |
| Reads `AGENTS.md` natively | yes | yes | yes — whether in full is unverified |
| Path-scoped rules | `.cursor/rules/*.mdc` + `globs` | none — a skill's `triggers` / `paths` | `.agents/rules/*.md` + `trigger: glob` |
| On-demand procedures | rules selected by `description` | repository skills in `.agents/skills/` | none shipped — the rule points at the sections of `AGENTS.md` |
| Programmatic pre-tool block | `preToolUse` in `.cursor/hooks.json` — shipped, **unverified in the ADE** | `pre_tool_use` in `.openhands/hooks.json` — shipped, **unverified in the ADE** | `PreToolUse` in `.agents/hooks.json` — shipped, **unverified in the ADE** |
| Session context at session start | `sessionStart` hook — shipped, unverified | `session_start` hook — shipped, unverified | no such event — the rule tells the agent to run the service |
| Governed context and CI gate | works | works | works |
| GTTGuard real-time block | through the same hook — unverified | through the same hook — unverified | through the same hook — unverified |
| Verified at runtime in the ADE | no | no | no |

**Short version:** Claude Code runs everything. Kiro runs everything except the
deterministic write block, which it approximates. Codex runs the content and the
write block, but loses conditional loading — its instruction file is
all-or-nothing. GitHub Copilot is the thinnest adapter: content and the CI
gate work, with neither conditional loading nor a deterministic write block —
GTT does not claim Copilot capabilities beyond what current GitHub
documentation actually supports (`.github/copilot-instructions.md` for
repository-wide instructions, `AGENTS.md` for agent instructions) — including
the fact that GTT's own adapter file does not live at that path by default.

### Claude Code

Native target. `.claude/CLAUDE.md` imports `AGENTS.md` and adds the
Claude-specific layer: skill routing and a note that permission denials are by
design.

Verify with `/context`: only `.claude/CLAUDE.md`, `AGENTS.md`, and
`constraints.md` should appear under memory files.

`.claude/hooks/protect-guard.py` is the only adapter with a real-time
GTTGuard block, resolving each protected symbol's span live against the
file on disk on every `Write`/`Edit`/`NotebookEdit`/`Bash` attempt.

### Kiro

Kiro reads `AGENTS.md` from the workspace root automatically, so the portable
core loads with no adapter at all. Note that `AGENTS.md` in Kiro does not
support inclusion modes — it is always included.

The path-scoped rules are mirrored in `.kiro/steering/` using
`inclusion: fileMatch` with a `fileMatchPattern`. Kiro accepts one pattern per
file, so a rule covering several globs becomes several steering files.

**Kiro reads no permission rules from a repository.** Workspace permissions
live per user, at `~/.kiro/workspace-roots/<hash>/permissions.yaml`, and Kiro's
documentation is explicit: "A cloned repo cannot inject permission rules - trust
is something you configure on your own machine" (https://kiro.dev/docs/permissions/,
read 2026-10-07). The `.kiro/permissions.yaml` GTT shipped until 1.3.1 was
therefore never read, and it was not in Kiro's format either. It is now a
template in Kiro's real format (`rules:` with `capability`, `match`, `effect`),
`.gtt/scaffold/ade/kiro-permissions.yaml`: `gtt-ade.sh install` and `gtt-ade.sh
list` point the human at it, and installing it is the human's act, on each
machine.

What the repository does carry is a pre-tool hook, `.kiro/hooks/gtt-protect.json`,
in Kiro's v1 hook schema (`"version": "v1"`, `hooks[]` with `name`, `trigger`,
`action`; https://kiro.dev/docs/ide/whats-new-v1/hooks/, read 2026-10-07). It
runs `.gtt/scripts/gtt_protect.py hook --format kiro`: exit 2 blocks the tool
call and the reason goes to the agent on stderr. Through that engine Kiro gets
what a static rule cannot express - the two-regime condition on
`gtt-domain/context/` and `gtt-domain/adr/`, and GTTGuard. It is **not verified
inside Kiro** (`enforcement: realtime-hook-unverified`), and two things are not
in the documentation GTT could read: the names of the fields in the event Kiro
sends on stdin, and the names of its tools. The engine reads the names the
other ADEs use plus Kiro's documented `path` and `command`, takes a tool for a
file write only when its name says so, and lets through whatever it does not
recognise - so until someone proves it in Kiro, the CI gate
(`.gtt/scripts/gtt-check-stack.sh`, `gtt-check-protection.sh`, a required
status check) is the layer that holds. The drift detector is advisory rather
than a write block: `.kiro/hooks/detect-drift.json`, a `PostToolUse` hook in
the same schema.

Known issue: global steering in `~/.kiro/steering/` has had reports of
`fileMatch` not triggering. Keep GTT steering in the workspace, not global.

GTTGuard goes through the same unverified hook. `.gtt/scripts/gtt-check-protection.sh`
in CI, plus `.kiro/steering/gtt-guard.md`, is the enforcement that holds.

### Codex

Codex reads `AGENTS.md` from the global config directory, the project root, and
nested directories, with more local files taking priority. The portable core
loads with no adapter.

Two adjustments matter:

**Conditional loading does not exist.** Codex has no `paths:` equivalent. The
closest approximation is nested `AGENTS.md` files that apply when Codex works in
that subtree:

```
AGENTS.md              # portable core
src/AGENTS.md          # implementation rules
infra/AGENTS.md        # infrastructure rules
```

This is coarser than path globs but preserves the principle: rules load near the
code they govern rather than all at once.

**Size cap.** Codex caps project docs at `project_doc_max_bytes`, 32 KiB by
default, counting nested `AGENTS.md` files in the same budget, and cuts the rest
without saying so. `AGENTS.md` is therefore kept at 24 KiB or less, with the
non-negotiable rules first and the detail in `.gtt/docs/agents/`, which it
points at section by section; `gtt-check-agents.sh` (part of `gtt-validate.sh`)
fails when that stops being true.

**Write protection** is available through filesystem permission globs in
`~/.codex/config.toml`:

```toml
[permissions.gtt.filesystem]
"gtt-domain/context/**" = "deny"
"gtt-domain/adr/**" = "deny"
```

Combine with `sandbox_mode` and `writable_roots` for a harder boundary. Verify
against the current Codex config reference — this surface has been changing
quickly.

GTTGuard has no real-time block on Codex either, for the same reason: its
registry is dynamic content a static filesystem glob cannot evaluate.
`gtt-check-protection.sh` in CI is the enforcement, backed by `AGENTS.md`.

### Cursor

Cursor reads `AGENTS.md` from the project root natively, so the portable core
loads with no adapter at all. The overlay adds two project rules — Cursor only
loads rules with the `.mdc` extension and a frontmatter:

| File | Frontmatter | Loaded |
|---|---|---|
| `.cursor/rules/gtt.mdc` | `alwaysApply: true` | every conversation — the governed paths, the marker, where the procedures are |
| `.cursor/rules/gtt-implementation.mdc` | `globs: src/**/*,lib/**/*,tests/**/*` | when a matching file is in play — the mirror of `.claude/rules/implementation.md` |

GTT owns exactly those two files (`owned:` in the registry), never `.cursor/`:
a host project's own rules, `hooks.json` and settings there are untouched by
`install`, `clean` and `export --clean`.

The overlay also ships `.cursor/hooks.json`. Cursor documents `preToolUse` as
able to deny a tool call (`"permission": "deny"` or exit code 2) and
`sessionStart` as able to inject `additional_context`; GTT registers both, each
running `.gtt/scripts/gtt_protect.py hook --format cursor`. That engine is
ADE-neutral: it applies the same rules as Claude Code's `protect-l0.py` and
`protect-guard.py` — governed paths, the freeze regime, promotion scripts, the
hook configuration itself, GTTGuard with live span resolution — and only the
input and output shapes are Cursor's. It fails open: an event it does not
understand never blocks a session.

It is built from Cursor's documented contract and tested against those
payloads (`protection_hooks` in the acceptance suite), **not verified inside
Cursor**. The names of the fields a `Write` tool call carries are not
documented, so the engine looks for the usual ones (`file_path`, `path`) and
lets through what it cannot read. The registry states `enforcement:
realtime-hook-unverified`; the CI gate remains the guaranteed layer. A host
project that already has a `.cursor/hooks.json` is a conflict `gtt-ade.sh
install` reports rather than merges.

### OpenHands

OpenHands includes the repository's root `AGENTS.md` in the initial system
prompt of every conversation, so the portable core is its always-on entry
point — that is what the registry records as `entry`. The overlay adds one
repository skill, `.agents/skills/gtt/SKILL.md` (frontmatter `name`,
`description`, `triggers`), which carries the OpenHands-specific notes: which
section of `AGENTS.md` governs which situation, and that a governed decision
is never taken in an unattended run. `.agents/skills/` is the current location;
OpenHands still reads the legacy `.openhands/skills/` and
`.openhands/microagents/`, which GTT does not use.

GTT owns exactly that one file, never `.agents/` or `.openhands/`. Detection
uses `.openhands/` only: `.agents/` is shared with other tools and would make
OpenHands a false candidate.

The overlay also ships `.openhands/hooks.json`: `pre_tool_use` (matcher `*`)
and `session_start`, both running `.gtt/scripts/gtt_protect.py hook --format
openhands` — the same engine as Cursor's, answering `{"decision": "deny"}` and
exit code 2, or `additionalContext` on session start. Same status: built from
the documented contract, tested against it, **not verified inside OpenHands**
(`enforcement: realtime-hook-unverified`). This matters more here than
elsewhere, because OpenHands is often run unattended — the CI gate and a
branch rule on `gtt-domain/context/**` and `gtt-domain/adr/**` are the real
backstop until the hook is proven.

### Antigravity

Google Antigravity is an ADE of its own in the registry (`antigravity`); it is
not treated as Codex, although both read `AGENTS.md`. The portable core is its
entry point — that is what the registry records as `entry`. The overlay adds
three files:

| File | What it is |
|---|---|
| `.agents/rules/gtt.md` | workspace rule, `trigger: always_on`: read `AGENTS.md` in full, run the session service, the governed paths, the `@gtt` marker, which section of `AGENTS.md` governs which situation |
| `.agents/rules/gtt-implementation.md` | workspace rule, `trigger: glob` on `src/`, `lib/`, `tests/` |
| `.agents/hooks.json` | one named hook, `gtt-protect`, on `PreToolUse` for `run_command`, `write_to_file`, `replace_file_content` and `multi_replace_file_content`, running `.gtt/scripts/gtt_protect.py hook --format antigravity` |

**What "supported" means here.** GTT installs, records, validates and maintains
the integration. It does not mean Antigravity guarantees the real-time block:
the CI gate is the only guaranteed layer.

| Level | What |
|---|---|
| Supported | registry, detection, install / update / remove, participating, Primary, the contract through `AGENTS.md` plus the rule, validation, CI gate |
| Partial | session context and GTT's procedures — both depend on the model following the rule |
| **Unverified** | the real-time block on every surface; whether `AGENTS.md` is loaded in full; what Antigravity does with the hook's exit code |
| Not supported | context injected at session start, merging into an existing `.agents/hooks.json`, native Antigravity skills |

**`.agents/` is shared.** OpenHands' skill lives there too, and so may the
host's own rules, skills and workflows. GTT owns exactly its three files, never
the directory: install, update and remove touch nothing else, and the two ADEs
can participate together. Detection uses `.agents/rules/`, `.agents/hooks.json`,
`.agents/workflows/` and the legacy `.agent/` — never `.agents/` itself or
`.agents/skills/`, which would make Antigravity a false candidate wherever
OpenHands is installed. With both participating, Antigravity also reads
OpenHands' skill from `.agents/skills/`; it only points back at `AGENTS.md`.

**A host that already has `.agents/hooks.json`.** `gtt-ade.sh install` reports
the conflict and writes nothing — not the rules either, because an ADE is
installed whole or not at all. GTT does not merge. Add the `gtt-protect` entry
to the host's file by hand, or leave the hook out and rely on the rule and the
CI gate; either way that file stays the host's and is not recorded as GTT's.

**The hook.** Antigravity's payload names no event, so the engine recognises a
pre-tool call by its `toolCall` field; it reads the path from
`toolCall.args.TargetFile` and the command from `toolCall.args.CommandLine`,
and answers `{"decision": "deny", "reason": ...}` with exit code 2. An edit
whose extent it cannot read fails safe to the whole file for GTTGuard. All of
this is built from Antigravity's documented contract and tested against it.
**None of it has been observed inside Antigravity.** Still to be observed, and
to be recorded in `.gtt/docs/evidence.md` when it is:

| To observe | CLI | IDE | Desktop app |
|---|---|---|---|
| The hook is invoked at all | not verified | not verified | not verified |
| The directory the hook runs in (its command is relative to the project root) | not verified | not verified | not verified |
| The real payload, per tool | not verified | not verified | not verified |
| A denial with exit code 2 is honoured | not verified | not verified | not verified |
| `AGENTS.md` reaches the agent in full | not verified | not verified | not verified |

Antigravity's documentation lists hooks for all three surfaces. A community
report says they ran only in the CLI. Neither is evidence here: a surface is
verified when someone runs it.

**`AGENTS.md` and Antigravity's size limits.** Antigravity documents a per-file
limit for rules and an aggregate budget for always-on content, and says
`AGENTS.md` is subject to them. GTT's `AGENTS.md` is larger than the per-file
limit. What Antigravity does then is not documented, which is why the rule is
short, always on, and tells the agent to open `AGENTS.md` with the file tool.
A user's global `~/.gemini/GEMINI.md` is outside the project and outside GTT's
control.

**Session.** Antigravity has no session-start event. `PreInvocation` runs
before every model call and is not used. The rule tells the agent to run
`bash .gtt/scripts/gtt-session-context.sh`; `gtt-domain/session.md` is the
same derived, ADE-independent state every other ADE gets.

### GitHub Copilot

Per GitHub's documentation
(https://docs.github.com/en/copilot/reference/custom-instructions-support, read
2026-10-07) Copilot reads three kinds of repository file: `AGENTS.md`,
`.github/copilot-instructions.md` and `.github/instructions/**/*.instructions.md`.
GTT's adapter file is `.github/instructions/gtt.instructions.md`, with
`applyTo: "**"`. Until 1.3.1 it lived at `.copilot/copilot-instructions.md`,
which no Copilot surface reads. GTT never touches the project's own
`.github/copilot-instructions.md`.

**Conditional loading** exists through `applyTo` in an instructions file. GTT
ships one file, repository-wide.

**Write protection.** GitHub documents hooks in `.github/hooks/*.json` for the
Copilot cloud agent and the Copilot CLI
(https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-hooks-reference,
read 2026-10-07). GTT ships `.github/hooks/gtt-protect.json`, whose `preToolUse`
runs `.gtt/scripts/gtt_protect.py hook --format copilot` and denies with
`{"permissionDecision": "deny", "permissionDecisionReason": ...}`. Copilot's
`preToolUse` **fails closed**: a hook that crashes or exits with anything but 0
denies the tool call. So GTT's hook never exits non-zero - only a decision of
the core is a denial, and an engine that cannot run allows the call and says on
stderr that it was not checked. It is **not verified inside Copilot**; the
fields inside `toolArgs` are not documented, so the engine reads `command` and
the path names the other ADEs use; a tool that carries neither (`apply_patch`)
is not seen; the `powershell` entry calls `python` directly and has not been
run on Windows; and every Copilot surface other than the cloud agent and the
CLI has no hook at all. `.gtt/scripts/gtt-check-stack.sh` as a required status
check is the layer that holds.

The adapter file itself must stay thin: it points at `AGENTS.md` and the governed directories
(`gtt-domain/context/`, `gtt-domain/adr/`) as the canonical source rather than restating GTT methodology, so there is
never a second copy of the rules to drift out of sync with the first.

GTTGuard is no exception to that thinness: Copilot gets `gtt-check-protection.sh`
in CI as its only real enforcement, and one pointer line in the adapter
file back to `AGENTS.md` — never a restatement of the mechanism.

### If your team uses more than one ADE

Bootstrap installs the adapter of every ADE the human chose — see the ADE
adapter matrix. If the team uses Claude Code and Copilot side by side, both are
declared participating (one of them Primary) and both get their overlay:
`gtt-ade.sh install --participating claude,copilot --primary claude`. A later
run adds an ADE only when told to, never drops one, never reintroduces one that
was excluded and never changes the Primary on its own. Real-time blocking exists
only on Claude Code; every other participating ADE is governed by its
instructions plus the CI gate, and the registry's `enforcement:` field says which.

Keep `AGENTS.md` as the single source for the core rules. Never restate a rule
in `.claude/CLAUDE.md` or `.github/instructions/gtt.instructions.md` that already lives
in `AGENTS.md` — that duplication is exactly the defect v2 was built to
remove.

The path-scoped rule files are the one place duplication is unavoidable,
since `.claude/rules/` and `.kiro/steering/` use incompatible front matter. They
are short and change rarely.

### If you use only one

Bootstrap installs only the adapters of the ADEs the human chose — there is
nothing to prune. If the project moves to a different ADE later, see
*Switching ADE later* in the README for the exact `gtt-ade.sh` commands and the
caveats: removing `.claude/` removes the deterministic enforcement layer, and
Codex/Copilot need nested `AGENTS.md` files to approximate path-scoped rules.

`AGENTS.md` is never deleted — it is the core every tool reads.

---

## Migrating from GTT v1

### What changed and why

v1 was correct as a methodology and expensive as an implementation. Every file
loaded on every session, whether relevant or not, and the same rules were
restated across four files.

| Problem in v1 | Fix in v2 |
|---|---|
| `AGENTS.md` ordered the agent to read 9 files at session start | Nothing is read at startup; content loads when relevant |
| L0 file list repeated 6 times across 4 files | Stated once, in `.claude/CLAUDE.md` |
| `Proposed Architecture Change` template duplicated in 3 files | One copy, in the `gtt-propose-change` skill |
| L0–L3 table in both `governance.md` and `project-context.md` | One copy, in the Methodology section above |
| 518 lines of methodology vs 263 lines of actual project context | Methodology moved out of the context window entirely |
| L0 protection written as prose the model may ignore | `permissions.deny` plus a PreToolUse hook |

Always-loaded context drops from roughly 826 lines to roughly 80.

### File mapping

| v1 | v2 |
|---|---|
| `gtt/AGENTS.md` | `.claude/CLAUDE.md` (rules) + this document's Methodology section (rationale) |
| `gtt/ai-rules.md` | `.claude/CLAUDE.md` + `.claude/skills/gtt-propose-change/` |
| `gtt/governance.md` | Methodology section above |
| `gtt/guardrails.md` | `.claude/settings.json` + `.claude/rules/` |
| `gtt/project-context.md` | Methodology section above |
| `gtt/context/*` | `gtt-domain/context/*` — unchanged in purpose; trimmed and marked read-only (in `gtt-domain/` in the current layout) |
| *(new)* | `gtt-domain/context/stack.md` — the visual stack and architecture map |
| *(new)* | `gtt-domain/change-request.md` — the single entry point for changes (root in v2, under `gtt/` in v2.1, project root after the scaffold restructure, `gtt-domain/` in the current layout) |
| *(new)* | `gtt-domain/proposals/` — agent-writable staging area |
| *(new)* | `.gtt/docs/index.md` — map of every file (root in v2, under `gtt/` in v2.1, `docs/index.md` after the scaffold restructure, `.gtt/docs/index.md` in the current layout) |
| *(new)* | `SOURCE-BRIEF.*` (project root) — the original design document, preserved by `gtt-bootstrap` |
| *(new, v2.1)* | `gtt-domain/backlog.md` — the development line: Epics, Stories, current focus |
| *(new, v2.1)* | `.gtt/docs/gtt-completion.md` — durable bootstrap completion record |
| `gtt-domain/adr/*` | unchanged; template added |

### Scaffold restructure (layout change within v2.1)

The v2.1 scaffold was reorganised so that its layers are separate, and then (below)
gathered into two homes: the Engine in `.gtt/` and the governed domain in `gtt-domain/`. Nothing about
governance semantics changed in either step; only locations (and lowercase names) did. The table lists where
each artifact lives now and where it lived in the v2.1 layout.

| Now | Formerly (before the scaffold restructure) |
|---|---|
| `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/proposals/` | `gtt/context/`, `gtt/adr/`, `gtt/proposals/` | <!-- legacy-layout -->
| `gtt-domain/backlog.md`, `gtt-domain/change-request.md` | `gtt/backlog.md`, `gtt/CHANGE-REQUEST.md` | <!-- legacy-layout -->
| `gtt-domain/session.md`, `gtt-domain/.frozen` | `gtt/SESSION.md`, `gtt/.frozen` | <!-- legacy-layout -->
| `.gtt/docs/index.md`, `.gtt/docs/installation*.md`, `.gtt/docs/usage*.md` | `gtt/INDEX.md`, `gtt/INSTALLATION*.md`, `gtt/USAGE*.md` | <!-- legacy-layout -->
| `.gtt/docs/gtt-completion.md`, `.gtt/docs/evidence.md` | `gtt/GTT-COMPLETION.md`, `gtt/EVIDENCE.md` | <!-- legacy-layout -->
| `.gtt/docs/docs.md`, `.gtt/docs/session-adapter-contract.md` | `gtt/docs/DOCS.md`, `gtt/docs/SESSION-ADAPTER-CONTRACT.md` | <!-- legacy-layout -->
| `readme-gtt.md`, `readme-gtt.es.md` | `README-GTT.md`, `README-GTT.es.md` | <!-- legacy-layout -->
| `.gtt/scaffold/manifest.yaml` | *(new)* the declarative scaffold definition |

`.gtt/scripts/`, `.gtt/index/`, `.gtt/protection/`, and `.gtt/session-adapters/` moved to `.gtt/`
in the layout migration below (formerly `gtt/`). Artifact ids are unchanged — identity follows the artifact, not the path.

### Layout migration to `.gtt/` and `gtt-domain/`

This migration renamed the Engine directory, moved GTT's documentation into it, and gathered the governed
state under one directory. Only locations changed; the freeze marker moved byte for byte.

| Now | Before this migration (the scaffold-restructure layout) |
|---|---|
| `.gtt/index/`, `.gtt/protection/`, `.gtt/scaffold/`, `.gtt/scripts/`, `.gtt/session-adapters/`, `.gtt/README.md` | `gtt/index/`, `gtt/protection/`, `gtt/scaffold/`, `gtt/scripts/`, `gtt/session-adapters/`, `gtt/README.md` | <!-- legacy-layout -->
| `.gtt/docs/` | `docs/` | <!-- legacy-layout -->
| `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/proposals/` | `context/`, `adr/`, `proposals/` | <!-- legacy-layout -->
| `gtt-domain/backlog.md`, `gtt-domain/change-request.md`, `gtt-domain/session.md`, `gtt-domain/.frozen` | `backlog.md`, `change-request.md`, `session.md`, `.frozen` | <!-- legacy-layout -->
| `.gtt/scaffold/manifest.yaml` (layout version 2) | `gtt/scaffold/manifest.yaml` (layout version 1) | <!-- legacy-layout -->

### Steps

1. Copy `.claude/` (includes `.claude/CLAUDE.md`), `.gtt/` (the Engine, including `.gtt/docs/`), and the
   governed-domain skeleton (`gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/proposals/`, `gtt-domain/backlog.md`,
   `gtt-domain/change-request.md`) into your project root.
2. Port your real content into the files under `gtt-domain/context/`. Copy from your
   v1 files; the governed content itself did not change.
3. Fill in `gtt-domain/context/stack.md`. This file is new in v2 and has no v1
   equivalent. Set the "Locked by" column to the ADR that made each decision;
   blanks are findings, not omissions.
4. Delete `gtt/AGENTS.md`, `ai-rules.md`, `governance.md`, `guardrails.md`, and
   `project-context.md`.
5. Adjust the `paths:` globs in `.claude/rules/` to match your folder layout.
   They ship with `src/`, `tests/`, `infra/`, `deploy/`.
6. Start a session and run `/context`. Confirm `.claude/CLAUDE.md` appears under
   memory files and that nothing from `.gtt/docs/` or `.claude/skills/` is
   loaded.
7. Wire `.gtt/scripts/gtt-check-stack.sh` into CI against your default branch.
8. Verify the protection holds: ask the agent to edit
   `gtt-domain/context/architecture.md`. It must be blocked, not merely reluctant.

### If you use other agents too

v2 ships this way already: `AGENTS.md` holds the portable core and
`.claude/CLAUDE.md` imports it. Kiro and Codex read `AGENTS.md` natively, so
they pick up the core with no adapter. See the Portability section above for
what each tool does and does not enforce.

If you only ever use Claude Code, you can inline `AGENTS.md` into
`.claude/CLAUDE.md` and delete it — but the indirection costs nothing and keeps
the door open.

### Verifying the token saving

Run `/context` before and after. The `Memory files` section shows what loaded
and what it costs. If you still see files from `gtt-domain/context/`, `gtt-domain/adr/`, or `.gtt/docs/` other than
`constraints.md`, something is importing more than it should.

