# GTT Bootstrap — Usage Guide

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

GTT governs the context that guides AI-assisted development. The normal development loop is:

```text
Governance   Context → Decision → Proposal → Human decision → Freeze
Work         Freeze → the ADE works on its own → GTT observes → the work continues
```

The upper line is travelled only when the governed design itself changes -
architecture, a boundary, a constraint, an Epic's goal or scope. Ordinary work
never takes it: once the design is frozen, implementation needs no approval.

## The normal workflow

### 1. Start from governed context

Before making an implementation decision, the agent should read the applicable governed context.

At minimum, this includes the core rules and relevant context files.

The goal is not to load every document into every session. GTT deliberately separates always-needed constraints from context that is required only for a specific task.

### 2. Work on implementation

Routine implementation belongs to the implementation layer.

The agent may modify source code, tests, pipelines, and infrastructure according to the project's rules.

Routine implementation does not require a `gtt-domain/change-request.md`.

### 3. Detect an architectural change

If a requested change affects an architectural decision, technology choice, dependency rule, deployment topology, observability design, or another governed decision, do not silently modify the governed map.

Use:

```text
gtt-domain/change-request.md
```

### 4. Propose the change

The agent creates a reviewable proposal under:

```text
gtt-domain/proposals/
```

The proposal should explain:

- current decision
- requested change
- reason
- trigger
- scope
- impact
- risk
- alternatives
- affected architecture-map rows

### 5. Approve

The human reviews the proposal.

Approval is a governance decision, not an implementation detail.

### 6. Record the decision

The approved change becomes a **promotion package**, staged under:

```text
gtt-domain/proposals/
```

— the ADR draft, the full text of every affected file under `gtt-domain/context/`
(including the updated `gtt-domain/context/stack.md`), and an executable script:

```text
gtt-domain/proposals/apply-ADR-NNN-<slug>.sh
```

The agent never runs it. Review the package, then run it yourself from the
project root:

```bash
bash gtt-domain/proposals/apply-ADR-NNN-<slug>.sh
```

It asks for a final confirmation, applies every affected file together, and
fails clearly rather than leaving the map half-updated. Only this explicit
human execution actually writes to `gtt-domain/adr/` and `gtt-domain/context/stack.md` —
see the Human Promotion Boundary in `AGENTS.md`.

### 7. Verify

Run the relevant audit/check mechanisms.

The CI gate:

```text
.gtt/scripts/gtt-check-stack.sh
```

must fail when the governed architecture and its map become inconsistent.

---

## The architecture map

`gtt-domain/context/stack.md` provides seven views:

1. stack
2. components
3. deployment
4. observability
5. dependency rules
6. map change log
7. boundaries — where a change in the code means the design may have changed, and how serious it is; watched by `gtt-observe.sh`

Use the map as the first architectural orientation point.

If a stack entry has no ADR in its `Locked by` field, investigate it as an ungoverned decision.

---

## The backlog

`gtt-domain/backlog.md` is the development line: Epics, Stories, current focus, and
next work. It is a planning artifact, not architecture — precedence is
governed context → ADR → backlog → implementation, and a Story never
overrides an architectural decision.

The backlog holds two kinds of entry, governed differently:

- **An Epic is yours to decide.** It is intent and scope: its goal, what it
  includes, where it stops. You approve it (`**Approved:** who — YYYY-MM-DD`)
  and only then does it leave `Proposed`. Adding, removing or materially
  changing one is your decision (`gtt-propose-change`, form 4).
- **A Story is the agent's working plan.** The agent creates, splits,
  rewrites, implements and closes Stories on its own. You approve none of
  them, and a Story is never a gate in front of the work.

You do not keep Stories honest by signing them. GTT does, by observing the
work (next section): if what a Story leads to crosses a boundary of the
design you froze, you hear about it, whatever the Story said.

Work you ask for directly needs no Epic first. When a Story is finished it is
marked `Done` with `Closed` (date, commit or PR, tests passed), and an Epic
is `Completed` only when all its Stories are `Done` or `Cancelled`.

Run `.gtt/scripts/gtt-check-backlog.sh` for structural integrity (unique
IDs, valid status values, an approved Epic carries its goal and who approved
it); run `gtt-audit` to reconcile the backlog against what is actually
defined and actually done.

---

## Working: the agent works, GTT observes

Once the design is frozen you are not in the loop of ordinary work. The agent
implements, refactors, tests and commits without asking. Freeze does not stop
the code from changing; it makes the design you approved the authority.

While the agent works, GTT compares the project with that frozen design and
tells you only what matters:

```text
@gtt · Observation
⚠ OBS-0003 WARNING    B-003  package.json#kafkajs
    new dependency `kafkajs`
    guards: Stack at a glance (section 1)
    work continues
```

| Level | What it means for you |
|---|---|
| `NOTICE` | Nothing. It is recorded |
| `WARNING` | You are told once. The work continues |
| `GOVERNANCE` | You are told once. The work continues. Decide before the next freeze |
| `BLOCKING` | The affected operation stopped: a rule you ratified says this must not happen |

What you can do, when you choose to:

```bash
bash .gtt/scripts/gtt-observe.sh backlog                              # what is open
bash .gtt/scripts/gtt-observe.sh accept OBS-0003 --by <you> --apply   # it stands
bash .gtt/scripts/gtt-observe.sh reject OBS-0003 --by <you> --apply   # validation fails until it is gone
bash .gtt/scripts/gtt-observe.sh defer  OBS-0003 --by <you> --apply   # later
```

Accepting an observation does not change the design. If the design itself
must change — the event bus really is part of the architecture now — that is
a change request, an ADR, and then a **new freeze**:
`bash .gtt/scripts/gtt-freeze.sh` records a new baseline and keeps the earlier
one as history. There is no unfreeze.

What GTT watches is what you declared in section 7 of
`gtt-domain/context/stack.md` (`gtt-boundaries`). Keep it short, and keep
`BLOCKING` for what must never happen without a decision.

The first control every agent and every person shares is the Git pre-commit
hook: `bash .gtt/scripts/gtt-git-hook.sh install --apply`. It can be skipped
with `git commit --no-verify`, so the guaranteed layer is CI: run
`gtt-validate.sh` and `gtt-check-stack.sh` on the pull request.

---

## Protected artifacts (GTTGuard)

Some L3 code deserves a narrower rule than "freely editable": a file,
class, or method a developer has explicitly marked so an agent may read and
propose changes to it, but never modify it autonomously. That is GTTGuard —
a sibling to L0/L1 governance, not part of it.

**Marking something protected** is a normal source edit, not a governed
change: add `@GTTGuard` (Java/Python), `[GTTGuard]` (C#), or `// @GTTGuard`
/ `# @GTTGuard` (comment-based languages), optionally with
`reason="..."`/`source="..."`, immediately above the declaration — or as
the file's first line to protect the whole file. Use the `gtt-guard` skill
for this, then run:

```bash
bash .gtt/scripts/gtt-guard-sync.sh
```

to regenerate `.gtt/protection/registry.yaml` from every marker in source.
The registry is derived, never hand-edited — `gtt-check-protection.sh`
fails the build if it drifts from what the markers actually declare.

**Changing something already protected** goes through `gtt-propose-change`
form 5, not a direct edit. Once you approve the proposal **in
conversation**, the agent implements the change directly and re-syncs the
registry — no ADR, no promotion script. This is deliberately lighter than
the Human Promotion Boundary above: GTTGuard protects L3 code you opted
into protecting, not `gtt-domain/context/` or `gtt-domain/adr/`, and the two promotion
models must never be conflated.

On Claude Code, `.claude/hooks/protect-guard.py` blocks a protected edit in
real time, resolving each protected symbol's current line span live from
disk so an unprotected method next to a protected one stays editable. Kiro,
Codex, and GitHub Copilot have no equivalent real-time block; enforcement
there is `.gtt/scripts/gtt-check-protection.sh` in CI plus an
instruction-plane note, the same honest fallback the two-regime
`gtt-domain/context/`/`gtt-domain/adr/` condition already uses.

---

## Change request example

A request should communicate intent rather than prescribe an implementation blindly.

Example:

```text
What needs to change?
Replace the current cache technology.

Why?
The current technology no longer meets the agreed operational constraints.

Trigger:
New deployment requirements.

Scope:
Caching layer and related observability.

Impact:
Architecture, deployment, configuration and operational documentation.

Risk:
Migration compatibility and cache invalidation behavior.

Priority:
High.
```

The agent should turn this into a proposal rather than directly editing the architecture map.

---

## Context layers

### L0 — governed context

```text
gtt-domain/context/
```

Contains the current governed understanding of the solution.

### L1 — architecture decisions

```text
gtt-domain/adr/
```

Contains accepted decisions and their rationale.

### L2 — documentation

```text
.gtt/docs/
```

Contains human reference material and methodology documentation.

### L3 — implementation

```text
src/
tests/
pipelines/
IaC/
```

Contains the implementation governed by the upper layers.

---

## Freeze and the two-regime model

GTT distinguishes between:

### Bootstrap regime

Before freeze:

- context can be populated by the bootstrap procedure;
- the design is still being confirmed;
- the context is not yet ratified.

### Governed regime

After:

```text
gtt-domain/.frozen
```

the governed context is protected.

Architectural changes must follow the change-request/proposal/ADR process.

---

## Keeping context useful

Keep the always-loaded context small.

`constraints.md` should contain only constraints that genuinely need to be available continuously.

Put detailed explanations, methodology, migration material, and reference documentation under `.gtt/docs/`.

Do not turn every instruction into a permanently loaded rule.

---

## Tool-specific adapters

GTT provides one adapter per supported ADE. A project installs the adapter of
every ADE its human chose to have participate, with exactly one of them declared
Primary (a workflow identifier that carries no authority) — chosen at bootstrap and
recorded in `.gtt/ade.json`, not by copying files around afterward. Several ADEs may
work in the project at once: the same governed artifacts and the same Human Promotion
Boundary apply to all of them.

- Claude Code uses `.claude/`.
- Kiro uses `.kiro/`.
- Codex uses `AGENTS.md` and applicable configuration, no extra adapter file.
- GitHub Copilot uses `.copilot/copilot-instructions.md` plus `AGENTS.md`.

Manage the set with `.gtt/scripts/gtt-ade.sh` (dry run until `--apply`): `state` shows the
Primary and participating ADEs and the health of each integration, `validate` fails when a
participating integration is broken, `install`/`remove`/`set-primary`/`update` change the set,
and `owned` lists exactly the files GTT installed for the ADEs — what a clean or an
`export --clean` may remove, and nothing else. `gtt-domain/session.md` carries the same state,
so any ADE that resumes the project sees it.

**Never remove `AGENTS.md`.**

---

## Operational checklist

Before implementation:

- [ ] Read applicable governed context.
- [ ] Determine whether the task is ordinary work or a change to the governed design.
- [ ] Ordinary work: do it. No Story has to be approved first.
- [ ] A change to the governed design, or a new/changed Epic: create/process a change request.

During implementation:

- [ ] Keep implementation aligned with governed context.
- [ ] Do not silently modify governed decisions.
- [ ] If a file/class/method carries a `@GTTGuard` marker, use `gtt-propose-change` (form 5) instead of editing it directly.
- [ ] Keep the Story current as you go: it is your working plan, so when something unwritten turns out to be needed, update it and continue - nobody approves it.
- [ ] Update the Story's status and Current Focus as work actually progresses.
- [ ] On finishing, mark the Story `Done` with `Closed` (date, commit or PR, tests passed); mark the Epic `Completed` when all its Stories are.
- [ ] Preserve host-project structure.

Before merge:

- [ ] Confirm required ADRs exist for architectural changes.
- [ ] Confirm the architecture map reflects accepted decisions.
- [ ] Run the stack check.
- [ ] Review the resulting diff.

---

## Guiding principle

> **Context is the Source of Truth.**

GTT does not attempt to make AI incapable of changing software. It establishes a governed boundary around the decisions that define what the software is supposed to be.

### Deployment target: bootstrap repository vs. host project

`readme-gtt.md`, `readme-gtt.es.md`, and `AGENTS.md` stay at the
**project root** — the canonical entry points, read before anything else.
Everything else follows the same scaffold in the bootstrap repository and in any
host project it installs into: the Engine (with Documentation, including this
file) in `.gtt/`, and the governed domain in `gtt-domain/`.


When an agent deploys GTT into a host project, it MUST reorganize the installed workspace so that it matches the GTT scaffold:

```text
/
├── AGENTS.md                     # portable agent contract (ADE discovery file)
├── readme-gtt.md
├── readme-gtt.es.md
├── SOURCE-BRIEF.*                # if a source document existed
│
├── .gtt/                         # GTT-METHOD ENGINE (machinery, derived state, GTT's own documentation)
│   ├── README.md
│   ├── index/
│   ├── protection/
│   ├── ade.json                  #   per-project ADE state: participating, primary, install ledger (installed projects)
│   ├── scaffold/manifest.yaml    #   also the ADE registry (overlays:) and the templates: the Bootstrap owns
│   ├── scaffold/templates/       #   Bootstrap-owned templates (the Initial Design Questionnaire)
│   ├── scripts/
│   ├── session-adapters/
│   └── docs/                     #   GTT's own documentation: index, installation, usage, docs, evidence,
│                                 #   gtt-completion, session-adapter-contract
│
├── gtt-domain/                   # THE DOMAIN GOVERNED BY GTT-METHOD
│   ├── context/                  #   L0 governed context
│   ├── adr/                      #   L1 accepted decisions
│   ├── proposals/                #   governed drafts awaiting a human decision
│   ├── backlog.md
│   ├── change-request.md
│   ├── session.md                #   derived operational state (never authority)
│   └── .frozen                   #   freeze marker, written by gtt-freeze.sh
│
└── .claude/ | .kiro/ | .copilot/ # ADE OVERLAYS - one per participating ADE; exactly one ADE is Primary
```

Every participating ADE's adapter — `.claude/`, `.kiro/`, or `.copilot/copilot-instructions.md` — remains at the host-project root. Only the adapters of participating ADEs are installed.

The agent must preserve existing host-project files, must not silently overwrite conflicts, and must not run the freeze step automatically. Human review and confirmation precede freezing.
