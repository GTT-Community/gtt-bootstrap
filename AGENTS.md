# AGENTS.md — GTT Bootstrap Agent Contract

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

This file defines the portable agent-facing contract for GTT Bootstrap.

## Mission

When asked to bootstrap GTT into a project, establish the GTT workspace contract without destroying, moving, guessing, or silently overwriting host-project content.

The governing principle is:

> **Context is the Source of Truth.**

## Agent roles and the evidence boundary

GTT distinguishes three responsibilities. No skill or script may collapse
them into one:

| Role | Does | Never does | This repo's mechanism |
|---|---|---|---|
| Grounding | Retrieves and exposes governed evidence faithfully | Decide architecture | `gtt-bootstrap`, `gtt-audit` reading `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/backlog.md` |
| Reasoning | Analyzes evidence, drafts gtt-domain/proposals/ADRs | Authorize its own draft | `gtt-propose-change`, `gtt-adr`, `gtt-drift-response` |
| Validation | Runs deterministic structural checks | Make an architectural judgment | `.gtt/scripts/gtt-check-*.sh`, `gtt-validate.sh` |

The chain is: Sources → Grounding → Evidence Dossier (governed context as
read) → Reasoning → Proposal → Human Decision → Freeze. A reasoning step
must never receive raw sources "for context" in a way that bypasses
grounding — read `.gtt/docs/docs.md` → *Governance model* for the full
rationale. Producing output, of any kind, never grants an agent decision
authority.

## Before changing anything

1. Read `readme-gtt.md`.
2. Inspect the host project.
3. Identify existing files with GTT-required names.
4. Identify design/source documents at the project root.
5. If there is no source document, continue through conversation.
6. If multiple candidate source documents exist, ask the user. Never guess. When several are
   design sources, the user chooses whether to consolidate them into one or keep them all
   as declared sources (see *Design assessment*).
7. Never silently overwrite an existing file.

## Required workspace

The GTT bootstrap contract is:

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
│   ├── local/                    #   user-level working preferences (local, never committed)
│   ├── ade.json                  #   per-project ADE state: participating, primary, install ledger (installed projects)
│   ├── scaffold/manifest.yaml    #   also the ADE registry (overlays:) and the templates: the Bootstrap owns
│   ├── scaffold/templates/       #   Bootstrap-owned templates (the Initial Design Questionnaire)
│   ├── scripts/
│   ├── session-adapters/
│   └── docs/                     #   GTT's own documentation: index, installation, usage, method-plans, docs, evidence,
│                                 #   gtt-completion, session-adapter-contract
│
├── gtt-domain/                   # THE DOMAIN GOVERNED BY GTT-METHOD
│   ├── context/                  #   L0 governed context
│   ├── adr/                      #   L1 accepted decisions
│   ├── proposals/                #   governed drafts awaiting a human decision
│   ├── backlog.md
│   ├── working-agreements.md     #   team working agreements (optional; below L0, never authority)
│   ├── change-request.md
│   ├── session.md                #   derived operational state (never authority)
│   └── .frozen                   #   freeze marker, written by gtt-freeze.sh
│
└── .claude/ | .kiro/ | .copilot/ | .cursor/rules/ | .agents/skills/gtt/
                                  # ADE OVERLAYS - one per participating ADE; exactly one ADE is Primary
```

The scaffold has two homes and its ADE overlays, and the layout keeps them apart:

| Part | Where | Contents |
|---|---|---|
| GTT Engine | `.gtt/` | scripts, artifact identity and technical index, protection registry, session-adapter declarations, the scaffold manifest, and GTT's own documentation (`.gtt/docs/`) |
| Governed domain | `gtt-domain/` | `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen` |
| ADE Overlay | `.claude/`, `.kiro/`, `.copilot/` | the integration of every participating ADE (one Primary; see *Multi-ADE participation*) |

`.gtt/scaffold/manifest.yaml` is the single, declarative definition of this
scaffold: what each part contains and what is required. The layout above is
its human-readable rendering; if the two ever disagree, surface it as a
finding rather than choosing one.

Tool-specific integration directories remain at their required locations.
Workspace hygiene: architectural authority (L0/L1) lives only in
`gtt-domain/context/` and `gtt-domain/adr/`; executable GTT logic lives only in
`.gtt/`, and `gtt-domain/` holds none in operation (`gtt-domain/proposals/` holds
governed drafts, including promotion scripts that only a human ever runs).
`AGENTS.md` and the ADE overlay are instructions to agents and belong to neither
group; the project's own L3 code belongs to neither either. Never mix the two:
no governance artifact inside `.gtt/`, no engine file inside `gtt-domain/`.
Both directory names are namespaced, so a host project's own `docs/`,
`context/`, `adr/` or `proposals/` never collide with GTT; a host project that
already has `.gtt/` or `gtt-domain/` is a conflict to report under *Conflict
policy*, never a reason to overwrite or merge silently. See *Workspace
hygiene* in `readme-gtt.md` for the full principle.

## Backlog governance

`gtt-domain/backlog.md` is the development line: Epics, Stories, and the work
currently expected to be built. It is a development-planning artifact, not
architecture — never a second source of truth beside `gtt-domain/context/`.

**Precedence:** Governed Context / L0 → ADR → this backlog → implementation.
A Story that contradicts governed context or an accepted ADR is a finding,
not a resolution — surface it through `gtt-domain/change-request.md`; never let a
Story silently override architecture.

**What goes through `gtt-domain/change-request.md` → `gtt-domain/proposals/` → decision:**
adding or removing an Epic or Story, or materially changing its scope or
acceptance criteria — the same funnel as an architectural change.

**What does not:** updating a Story's status, or the *Current Focus* /
*Next Work* / *Blocked* lists, as part of already-approved implementation
work. Routine progress tracking is not a governed decision; do not force it
through the change-request flow, and do not use it as a backdoor to add or
remove Epics/Stories either — that distinction requires judgment, not a
loophole.

### Story Ready

A title is not a design. The design of a Story is governed like the rest of
the development line: it is written in `gtt-domain/backlog.md` and approved by
the Solution Designer, so that another session - or another person - can
implement it from the backlog alone, never from a conversation.

**Definition.** A Story Ready carries, in the backlog: Description, Scope,
Out of Scope, Acceptance Criteria, Tests, Sources, `Governed by`, and
`Design Approved` (who, `YYYY-MM-DD`). Every statement in the first four carries its origin:
`[FUENTE: ref]` (a source says it), `[HUMANO]` (the Solution Designer decided
it) or `[PROPUESTA]` (the agent proposed it; approving the Story is what
accepts it, and the tag stays). A `[VACÍO]` or `[CONFLICTO]` in a Story means
it is not designed yet. `[PROPUESTA]` is legitimate here and never inside
governed context.

**Status.** `Undesigned` means the Story is in the line but only a title (or
an incomplete design) exists: it is reported and it is not implementable.
`Ready` means designed and approved, and nothing else. A Story may be
`Ready`, `In Progress` or `Done` only as a complete Story Ready definition.
`Proposed` keeps its meaning: not yet accepted into the line.

**Bootstrap.** When a source brings only titles, record each Story as
`Undesigned` with exactly what the source gives, and report how many there
are. Never complete a Story from your own reading of the source to make the
backlog look finished.

**Design stage, per Epic, before implementation.** Analyse the Epic against
the governed context and the sources, propose the complete Stories, mark
gaps and conflicts instead of guessing, and obtain the Solution Designer's
approval **Story by Story** (`gtt-propose-change`, form 6). One Story's
approval never carries over to the next. Only an approved Story is written
as `Ready`, and `Design Approved` is never written on the agent's own
initiative.

**Implementation.** Implement only against the written Story. If something
that is not written turns out to be needed, stop and update the Story first;
do not fill it from the conversation, from memory or from a source read on
the spot.

**The backlog references the architecture; it never copies it.** `Governed
by` names the governed decisions that apply to the Story - ADR ids, sections
of `gtt-domain/context/` - or `None`. Their text stays in governed context,
the single place where architecture is written; a copy in a Story would be a
second source of truth. The backlog is the truth of what is built and how it
is verified, never of how it may be built.

**Closure is evidence.** A `Done` Story carries `Closed`: the date and what
closed it - commit or PR, tests passed - written from what actually
happened. It is a routine status update, not a governed change. An Epic is
`Completed` only when every one of its Stories is `Done` or `Cancelled`.

**Before development work, establish the applicable Epic/Story from
`gtt-domain/backlog.md`.** If defined Epics/Stories exist elsewhere (a requirements
doc, an issue tracker, prior conversation) but are missing from the
backlog, reconcile them through the normal change process — do not
silently ignore them and do not silently rewrite the backlog to match.
Report the gap and offer the `gtt-propose-change` skill. If no Epics or
Stories are defined at all, say so explicitly and ask whether the
development line should be defined, or proceed only where the requested
work is genuinely independent of one. Never invent business Epics/Stories
and present them as user-defined requirements — proposed ones must stay
labeled `Status: Proposed` until accepted.

Structural integrity (unique IDs, valid status values) and Story Ready (a
`Ready`, `In Progress` or `Done` Story with an empty field, a statement
without its origin, or no approval; a `Done` Story without `Closed`; a
`Governed by` citing an ADR that does not exist; a `Completed` Epic with
open Stories) are checked deterministically by
`.gtt/scripts/gtt-check-backlog.sh`, which also reports the Stories still
`Undesigned`; whether a criterion is good, a source says what its tag
claims, or an
Epic/Story is real, current, and correctly linked to actual work is a
judgment call for the `gtt-audit` skill.

## Protected artifacts (GTTGuard)

GTTGuard is a lightweight, language-agnostic mechanism for marking a file,
class, or method so an AI coding agent may read, analyze, and propose a
change to it, but may never modify it autonomously. It is a **sibling** to
L0/L1 governance, not a restatement of it: it protects arbitrary L3 code
the developer opts into protecting, never `gtt-domain/context/` or `gtt-domain/adr/`, and
it must never be conflated with the Human Promotion Boundary below — the
two are deliberately different weights of ceremony for different things.

**Core rule:** User proposes the protection → GTT implements it → Agent
respects it.

A developer marks a declaration with `@GTTGuard` (Java, Python), `[GTTGuard]`
(C#), or a `// @GTTGuard` / `# @GTTGuard` comment (other languages),
optionally with `reason=`/`source=`. `.gtt/scripts/gtt-guard-sync.sh`
detects every marker, resolves the file/class/method it protects
deterministically (never by LLM judgment), and regenerates
`.gtt/protection/registry.yaml` — a **derived artifact**, like a lockfile:
never hand-edit it, since `.gtt/scripts/gtt-check-protection.sh` fails the
build the moment the committed file drifts from what the markers in source
actually declare. Placing or removing the marker is an ordinary L3 edit —
it is the Solution Designer's proposal, not a protected change itself.

On Claude Code, `.claude/hooks/protect-guard.py` (a PreToolUse hook,
registered alongside `protect-l0.py`) blocks an autonomous edit to a
protected artifact in real time, resolving each protected symbol's exact
span live against the file on disk so an unprotected method next to a
protected one stays freely editable — and failing safe to whole-file
blocking whenever that resolution is ambiguous. Kiro, Codex, and GitHub
Copilot have no equivalent real-time block, the same honest limitation
already documented for the two-regime `gtt-domain/context/`/`gtt-domain/adr/` condition —
`gtt-check-protection.sh` in CI is the enforcement there, backed by an
instruction-plane note in each adapter. No ADE is credited with a guarantee
it does not actually have.

**Changing a protected artifact:** draft a proposal with `gtt-propose-change`
(form 5). Once the Solution Designer approves **in conversation** — not a
script run — implement the change directly, update or remove the marker,
and re-sync the registry. This promotion model is deliberately lighter than
the Human Promotion Boundary below (no ADR, no `apply-*.sh` script):
GTTGuard protects L3 code the developer chose to flag, not L0/L1 governed
context, and the proposal that introduced this mechanism is explicit that
it "should not create a second, unrelated approval model."

Full procedure: `.claude/skills/gtt-guard/SKILL.md` (marking/unmarking) and
`.claude/skills/gtt-propose-change/SKILL.md` (form 5, changing a protected
artifact).

## Session continuity

Run `.gtt/scripts/gtt-status.sh` to regenerate `gtt-domain/session.md`: a
deterministic snapshot (freeze state, backlog focus, pending proposals,
protected-artifact count, artifact identity and index state) derived from repository
artifacts, never from any ADE's private conversation memory — the same
project resumes the same way whether the next session is Claude Code,
Codex, Kiro, or Copilot. Treat it as operational context only: never
architectural authority, never evidence, never a substitute for an ADR or
decision record. An agent must never invent this state from memory instead
of running the script.

`gtt-domain/session.md` also reports the ADE integration state (Primary ADE,
participating ADEs, integration health, read from `.gtt/ade.json` through
`.gtt/scripts/gtt-ade.sh state`). It is portable across ADEs and records no "last
active ADE": several ADEs may run at once and would overwrite each other's entry,
and no deterministic source for it exists. It is operational state, never a
second memory architecture and never authority.

Working preferences are defined in *Provenance, gaps, sources and working agreements*; keep them in
an artifact separate from session state — they are not Canon, architecture,
evidence, or decisions, sit below governed gtt-domain/context/constraints in
precedence, must never silently override them, and no agent may author its
own preferences.

## Artifact identity and technical index

Every governed Markdown artifact has a stable identity (`.gtt/index/artifacts.json`)
independent of its path: a move or rename is reconciled, never treated as delete
+ create. Reference an artifact as `[[ID]]` (e.g. `[[ADR-007]]`) so the reference
survives moves. `.gtt/index/technical-index.json` is a DERIVED accelerator - for
locating concepts and sections (`.gtt/scripts/gtt-query.sh`) - never a source of
truth, never evidence in itself; the Markdown it points to is authoritative.
Regenerate it with `.gtt/scripts/gtt-index.sh`; never hand-edit it. After any move
run `.gtt/scripts/gtt-reconcile.sh` (dry-run first). `.gtt/scripts/gtt-check-integrity.sh`
(part of `gtt-validate.sh`) fails on unreconciled moves, duplicate logical identity,
broken or old-path references, unresolved `[[ID]]`, and a stale index. Agents
operate through these scripts and MUST NOT own an artifact's identity or authority,
and never rewrite frozen `gtt-domain/context/` or `gtt-domain/adr/` files to fix a reference.

## Validation

`.gtt/scripts/gtt-validate.sh` runs every deterministic check script
(`gtt-check-backlog.sh`, `gtt-check-adapter.sh`, `gtt-check-protection.sh`,
`gtt-check-stack.sh`, `gtt-check-provenance.sh`) and reports pass/fail/cannot-determine.
A Session Memory adapter is checked only for an ADE that participates: `adapter_status`
describes the Bootstrap catalog, not the project, so the adapter of an ADE the human did
not choose is skipped, never failed. Every ADE therefore validates on its own.
`.gtt/scripts/gtt-status.sh` reports what is current, governed, pending,
proposed, blocked, and frozen. Both are read-only and deterministic;
neither substitutes for a human architectural judgment.

`gtt-check-adapter.sh` validates every participating ADE against
`.gtt/ade.json`: a missing or inconsistent integration FAILS, a detected ADE that
does not participate is a WARN, never a pass (`gtt-ade.sh validate` reports the
same per ADE). Without `.gtt/ade.json` it falls back to the single-ADE matrix of
projects that predate multi-ADE support.

## Adapters vs. portable core

GTT ships a portable core — this file, `readme-gtt.md`, `readme-gtt.es.md`,
and `SOURCE-BRIEF.*` (if a source document existed) at the project root, plus
the governed domain (`gtt-domain/`) and the GTT Engine (`.gtt/`, including
`.gtt/docs/` and `scaffold/manifest.yaml`) — plus

one adapter per supported ADE: Claude Code → `.claude/`, Kiro → `.kiro/`,
Codex → `AGENTS.md` alone, GitHub Copilot → `.copilot/copilot-instructions.md`,
Cursor → `.cursor/rules/gtt.mdc`, `.cursor/rules/gtt-implementation.mdc` and
`.cursor/hooks.json`, OpenHands → `AGENTS.md` plus `.agents/skills/gtt/SKILL.md` and
`.openhands/hooks.json`. For Cursor and OpenHands GTT owns exactly those files, never
the rest of the host's `.cursor/`, `.agents/` or `.openhands/`.
The GTT Bootstrap source carries every adapter as a catalog; a target
project receives the portable core plus the adapter of every ADE its human
chose to have participate (see *Multi-ADE participation*) — never the whole
catalog, never an adapter nobody chose.

Detecting an ADE and choosing it are different acts. Base detection on the
environment actually present, never on the underlying model (a Claude model is
not Claude Code; a GPT model is not Codex). Adapter files that merely happen to
exist in the target repo, or an ADE binary on the PATH, make an ADE a
*candidate* — nothing more. Which ADEs participate and which one is Primary is
the human's decision; if it cannot be established, ask — do not guess. Full
resolution procedure: the `gtt-bootstrap` skill.

## Multi-ADE participation

One GTT governance model; several ADE integration surfaces; one Primary ADE. A
project may have one ADE or several — the governance, the governed artifacts and
the Human Promotion Boundary are the same for all of them.

| Term | Meaning | Recorded |
|---|---|---|
| Detected ADE | A candidate: its files or binary were observed. Never installed, authorized, governed or participating by itself. | never (an observation) |
| Participating ADE | An ADE the human explicitly chose to have GTT govern. It gets its overlay. | `.gtt/ade.json` |
| Primary ADE | Exactly one participating ADE, chosen by the human: the principal AI development environment of the project's workflow. | `.gtt/ade.json` |
| Excluded ADE | A registry ADE the human declined. A re-run never reintroduces it unless the human says so. | `.gtt/ade.json` |

**The Primary ADE holds no authority.** It identifies the principal environment of
the workflow and nothing else: it does not outrank, approve, arbitrate between or
speak for any other ADE, and it has no more authority over a governed artifact than
any participating ADE — which is none: every ADE prepares, none ratifies. GTT has no
ADE hierarchy, agent voting or arbitration, and none may be introduced.

Instruction files and overlays — `AGENTS.md`, `.claude/`, `.kiro/`, `.copilot/`,
`.codex/`, and any ADE's memory, session history or notes — are integration
surfaces. They let an ADE take part in GTT; they never become a source of
governance authority. Several agents may run at the same time (for example three
terminals in one editor), so every participating ADE receives its integration
surface; governance never depends on the Primary being the one that is active.

The ADE registry — which ADEs exist, where each integrates, what it owns, how it
is detected, what enforcement it really has — is the `overlays:` section of
`.gtt/scaffold/manifest.yaml`. The per-project choice is `.gtt/ade.json`. Both are
read and written only through `.gtt/scripts/gtt-ade.sh` (`list`, `detect`, `state`,
`validate`, `owned`, `install`, `adopt`, `set-primary`, `record`, `remove`,
`update`); a CLI or an agent consumes that contract and never invents an
ADE-specific path. Every mutating command is a dry run without `--apply`, never
overwrites a file GTT did not install, and rolls back on failure. `.gtt/ade.json`
records the files GTT itself installed, with hashes, so a clean or an
`export --clean` removes exactly those and never the host project's own ADE
configuration; a directory whose name merely resembles an ADE's is not GTT's.

Cursor and OpenHands both document hooks that can block a tool call before it runs.
GTT ships one for each (`.cursor/hooks.json`, `.openhands/hooks.json`), both pointing at
one ADE-neutral engine, `.gtt/scripts/gtt_protect.py`, which applies the same rules as
Claude Code's hooks - governed paths, the freeze regime, promotion scripts, GTTGuard -
answers in each ADE's own shape, fails open, and injects the session context at session
start. They are built from each ADE's documented contract and tested against it, but
not verified inside the ADE: the registry states `realtime-hook-unverified`, and until
one is proven there the CI gate is the only guaranteed layer for that ADE. The
instruction binds on its own, whether or not the hook fires.

Only Claude Code has a verified real-time write block. Every other participating ADE is
governed by its instructions plus the CI gate (`gtt-check-protection.sh`):
governed is not the same as hard-blocked, and no ADE is credited with a guarantee
it does not have.

## Bootstrap behavior

During initial bootstrap:

1. Detect the candidate ADEs, have the human choose the participating ADEs and
   exactly one Primary, and resolve the adapters to install (see *Multi-ADE
   participation*) before touching the filesystem.
2. Obtain or confirm the design/source document — or, if there is none, offer the
   Initial Design Questionnaire (see *Initial Design Questionnaire*).
3. Assess the design in writing (see *Design assessment*), strengthen it when it is poor or
   the human asks, and verify that it is complete enough to serve as a source.
4. Inspect `gtt-domain/context/` for placeholders.
5. Map the source into the six governed context files.
6. Ask for missing information rather than inventing decisions.
7. Summarize the resulting context.
8. Obtain explicit human confirmation.
9. Write the confirmed context.
10. Preserve the source as `SOURCE-BRIEF.*`.
11. Ask the user to review.
12. Freeze only after explicit confirmation.

Before step 4, have the human select the Method Plan (see *Method Plans*): ask, never infer.

## Method Plans

A Method Plan is the human's answer to one question: how much operational work is
delegated to GTT. There are four - **Light**, **Medium**, **Hard**, **Team** - and
`.gtt/contract/profiles.json` is the single definition of what each one means;
`.gtt/docs/method-plans.md` renders it in plain words. A plan is an operating and
collaboration profile, never a quality level, and no plan turns governance off.

- **The human selects; nobody infers.** During bootstrap, ask for the plan, showing
  the four with the `label` and `summary` the contract gives them. Never choose,
  default or infer one - not from the project, the ADE or a previous project. Ask
  for the methodological intent only, never for the technical policies derived
  from it.
- **Not selected is a state, said plainly.** Until the human chooses,
  `gtt-project.sh profile get` reports `plan: not selected`; the Medium gates apply
  only as a fallback so validation keeps working. Never report that fallback as a
  choice.
- **What never varies.** In every plan a governed decision and a destructive
  operation need the human's explicit confirmation, and every invariant in the
  contract holds. Only Light relaxes anything, and only the four controls its
  `relaxes` names.
- **What varies.** The gates (`gates`, enforced by `gtt-check-provenance.sh`), the
  rigor an agent applies (`semantics`: proposal, documentation depth, ADR, audit,
  promotion, evidence - follow the selected plan's), and the operating policy
  (`plan.policy`: what is automatic, confirmed, proposed or left to team policy),
  which the CLI executes; the Bootstrap declares it and does not implement it twice.
- **Team** is the Hard gates plus collaboration requirements (CI, actor
  traceability, second-person review). It is a baseline: dedicated team plans are
  planned. Promise nothing beyond what the contract states.
- **Changing it later** writes only `.gtt/methodology.json`
  (`gtt-project.sh profile set --profile <id>`, a dry run without `--apply`) and
  recreates nothing. In a frozen project a *less* strict plan is refused: it is a
  governed change. The order is light < medium < hard < team.

## Working without unnecessary interruption

> The developer decides what only the developer can decide. GTT does everything else.

Lower friction never means less governance. The policy is data -
`.gtt/contract/profiles.json` -> `developer_experience` - and applies in every
Method Plan; what is automatic, confirmed or proposed for each kind of operation is
the selected plan's own `plan.policy`.

**Before asking the human anything**, check whether the answer already follows from
governed context, the selected plan, project policies and working agreements, the
actual state of the project, or a deterministic rule. If it does: act, validate the
result, continue. If it does not: name the decision, explain it briefly, ask once.

**Do, do not ask.** Never turn these into a question:

- an occupied id - take the next free one: `bash .gtt/scripts/gtt-project.sh next-id --kind adr|epic|story`
  (it never reuses a retired id; under a plan whose id resolution is `propose_confirm`
  or `team_policy` the human confirms the number when reviewing the package, not in a
  separate question);
- rebuilding the index, syncing the GTTGuard registry, validating - after any
  operation run `bash .gtt/scripts/gtt-maintain.sh`, which does all three and reports
  in a few lines;
- continuing to the next planned task after a step succeeded;
- a policy the plan or a working agreement already defines.

**Protected and governed operations use a script, never a recipe.** When an operation
needs human authorization (approve, promote, advance a governed stage, copy, move,
delete, overwrite, modify a governed or protected artifact), provide one directly
executable script that contains the whole operation, checks its preconditions, fails
explicitly when the expected state is absent and runs from the project root - and give
the one-line command. Never ask the human to reconstruct a command by hand. You still
never run it: see *Human Promotion Boundary*. Once the human has run it, validate the
result (`gtt-maintain.sh`) and continue.

**STOP is not a general precaution.** Stop only for: a genuine architectural or
semantic conflict; a decision only the developer can make; explicit authorization
required for a protected or governed operation; a safety or integrity condition that
prevents continuing safely; unresolved evidence required to continue correctly.
Reaching an intermediate mechanical step is never a reason to stop.

**Say when it is GTT speaking.** Every message in which you speak on behalf of GTT
opens with `@gtt · <what this is>`, so the human always knows it is the method and not
the assistant's ordinary conversation: a question the method needs answered; a
confirmation or a choice (ADE participation, Method Plan, Confirmation A, Confirmation
B, a Story's design approval); the Initial Design Questionnaire, in every turn of the
interview; a proposal, a finding, a conflict or a STOP; a request for authorization;
a report. For example `@gtt · Method Plan`, `@gtt · Initial Design Questionnaire`,
`@gtt · Authorization required`, `@gtt · Report`. Ordinary work GTT did not raise -
explaining code, answering a question, implementing a Story - carries no marker. The
marker is data (`developer_experience.dialogue.marker`) and identifies who is
speaking: it is never a decision, an approval or evidence.

**Report briefly by default**: what was done, the result, whether the developer must
act (with the exact command), and the next step when relevant. No long explanation,
internal reasoning or operational history unless asked. Detail is never withheld: give
it when asked, or point to it (`gtt-maintain.sh --verbose`, `gtt-status.sh`,
`gtt-query.sh`, the full output of a check).

```text
@gtt · Authorization required
✓ ADR draft and promotion package staged.
✓ Validation: 11 passed, 1 skipped.
⚠ ADR-009 needs your authorization: it changes governed context.
→ bash gtt-domain/proposals/apply-ADR-009-base-evolution-alignment.sh
```

## Design assessment

A design document existing is not the same as a design good enough to govern. When one
or more exist, the Think stage begins by assessing them - in writing, in
`gtt-domain/proposals/bootstrap/design-assessment.md`, materialized from the Bootstrap's
template (`.gtt/scripts/gtt-template.sh materialize design-assessment`, declared under
`templates:` in `.gtt/scaffold/manifest.yaml`). The Primary ADE writes it; the human reads
it and decides.

- **What it rates.** Vision, scope, users, capabilities, non-functional requirements,
  architecture, technology stack, data, security, integrations, deployment, development
  architecture, observability and constraints - each `SOLID`, `THIN` or `MISSING`, with the
  `[FUENTE: file:line]` that supports the rating. Rate what the documents say, never what
  the author is assumed to have meant.
- **Minimum floor.** The problem and scope are stated; the architectural style is stated;
  the technology stack is decided (language and runtime, framework, compute model); the
  datastore is decided or explicitly not needed. Below the floor the verdict is `POOR`,
  whatever else the design gets right.
- **Verdict.** `STRONG`, `ADEQUATE` or `POOR`. Strengthening is offered for the first two
  and required for `POOR`: a design below the floor is never mapped into governed context
  as it is, and the human's confirmation that it is finished does not lift the floor.
- **THINK Depth.** How deep THINK goes: `QUICK` (simple or small designs: the floor areas
  and the areas the documents make relevant, critical gaps, a reduced questionnaire),
  `STANDARD` (ordinary projects: the complete assessment, stack alternatives with trade-offs,
  an adaptive questionnaire) or `DEEP` (complex, critical or uncertain systems: exhaustive
  assessment, architectural as well as stack alternatives, dependencies and risks, a deep
  iterative questionnaire). `.gtt/contract/elicitation.json` -> `think_depth` is the single
  definition. The human selects it - ask once when the assessment starts, never infer it -
  and it is recorded with who and when - in the assessment, or in the questionnaire's own
  *THINK Depth* block when there is no design document; unselected is a state, `STANDARD`
  applies as a fallback and is never reported as a choice. **Depth is not governance and
  is not the Method Plan** (the two are independent and chosen separately): it changes how
  far THINK digs, never which rule it may skip. At every depth the floor is assessed line
  by line, an area not assessed is written as such and never as `SOLID`, and the evidence
  boundary, the provenance tags, human decision and freeze are unchanged.
- **Escalation is a proposal.** When what you find justifies a deeper level, record it in
  the assessment's escalation log - one level at a time, with the evidence - tell the
  human, and keep working at the current depth until they accept or decline. Never raise
  or lower the depth yourself. `bash .gtt/scripts/gtt-project.sh think` reports the
  recorded depth; `gtt-validate.sh` fails on a depth nobody decided and on a verdict above
  `POOR` with the floor unmet or unassessed.
- **Helping reach the best stack.** For every stack layer that is undecided, or decided
  without a reason, give the options that fit this project - its requirements,
  constraints, team and scale as the documents state them - with the trade-offs of each
  and a recommendation that says what it optimises for and what it gives up. Each is a
  `[PROPUESTA]`; the human decides. Never recommend a generic favourite, never recommend
  from nothing, and never write a stack choice as decided because you recommended it.
- **Strengthening is written, not talked about.** Carry what the documents establish into
  the Initial Design Questionnaire, each statement with its `[FUENTE]`, and interview only
  about what was `THIN` or `MISSING`. The original documents are never rewritten. The
  completed questionnaire is then the source document.
- **More than one document.** They are resolved before design continues, and the human
  chooses how - ask, never infer from name, order or size. `CONSOLIDATE`: draft one design
  document from all of them (`gtt-domain/proposals/bootstrap/design-consolidated.md`),
  every statement with its `[FUENTE]` and every disagreement left as `[CONFLICTO: a vs b]`
  for the human to resolve; after review it is the single source document.
  `KEEP_AS_SOURCES`: declare each in `gtt-domain/context/sources.md` with an authority and
  an unambiguous precedence; all are context throughout design, and precedence never
  erases a conflict.
- **Status.** The assessment is source material: it decides nothing and governs nothing,
  and its ratings are the ADE's judgment - no deterministic check verifies them.

## Initial Design Questionnaire

When a project has no sufficient design source document, the Bootstrap offers its
Initial Design Questionnaire: `.gtt/scaffold/templates/gtt-initial-design-questionnaire.md`,
declared under `templates:` in `.gtt/scaffold/manifest.yaml`. It is an ADE-guided
elicitation instrument — not CLI logic, and not governed architecture. There is
exactly one questionnaire.

- **Ownership.** The Bootstrap owns the template, its contract and its evolution;
  its version is the Bootstrap's own. A CLI detects the need, asks
  `.gtt/scripts/gtt-template.sh` for the template and materializes a working copy at
  the declared location (`gtt-domain/proposals/bootstrap/initial-design-questionnaire.md`,
  never overwritten). It never carries a copy of the questionnaire or of its
  methodology.
- **Also the instrument of strengthening.** When an existing design is assessed as poor,
  or the human chooses to strengthen it, the same questionnaire is used: pre-filled from
  the documents with `[FUENTE]`, and asked only for what they leave thin or missing.
- **Use.** The Primary ADE reads the questionnaire's Operating Contract first,
  inspects the project, and asks the human only what the evidence does not answer,
  progressively — never the whole form at once. `[VACÍO]` is preferable to an
  invented answer. `[CONFLICTO]` and `[PROPUESTA]` stay distinguishable from
  confirmed decisions, and a proposal is never written as a decision.
- **Status.** The filled questionnaire is source material. It becomes the source
  document only after the human reviews it (Confirmation A) with Readiness `READY`
  or `READY_WITH_OPEN_ITEMS`; it is then preserved verbatim as `SOURCE-BRIEF.md`, and
  the governed context is derived from it through the normal bootstrap steps and
  Confirmation B. An unresolved `[CONFLICTO]` or an undecided `[PROPUESTA]` maps to
  nothing in governed context. Completing the questionnaire never makes anything
  governed by itself.

## Provenance, gaps, sources and working agreements

One deterministic gate — `.gtt/scripts/gtt-check-provenance.sh`, part of `gtt-validate.sh` and of
`gtt-freeze.sh` — checks the four mechanisms below. It makes no architectural judgment and is never
authority; `gtt-status.sh` and `gtt-query.sh --governance <open|blocking|resolved|conflicts|sources|agreements>`
report them from the governed artifacts themselves. A project that has adopted none of them is unchanged.

- **Provenance.** In governed context and ADRs a claim is one of: `[FUENTE: ref]` (evidence from a declared
  source id, or a repo path with an optional `:line`), `[VACÍO: GAP-id]` (the authorised sources do not
  determine it; classified by a gap), `[CONFLICTO: a vs b]` (named sources disagree), or a
  `[PROPUESTA]`, which is reasoning output and **never** appears inside governed context (it stays in
  `gtt-domain/proposals/`). An unclassified `[VACÍO]`, a `[FUENTE]` that does not resolve, or a `[CONFLICTO]`
  that does not name its sources is a finding. The evidence boundary stays as stated in *Agent roles*:
  grounding retrieves, cites, declares absence and exposes conflicts; reasoning works on that dossier and
  proposes; neither decides.
- **Gaps: OPEN and BLOCKING.** The register is the `gtt-gaps` block in `gtt-domain/context/stack.md`
  (section 8). A **BLOCKING** gap must be decided before freeze: freeze is refused while one is pending, and a
  frozen design cannot carry one. An **OPEN** gap is known, undecided and not needed for the current design: it
  has an explicit `scope:`, crosses freeze, stays visible in status and query, and is **never an authorisation**
  — resolving it, or changing anything outside its scope, follows the normal path (change request → proposal →
  human decision → promotion → new freeze). A resolved gap is not deleted: it becomes an append-only
  `RESOLVED` line citing the ADR that resolved it.
- **Sources.** When there is more than one design source, or a provenance policy is wanted, they are declared in
  `gtt-domain/context/sources.md` (`gtt-sources` block): id, path, version, authority, precedence, status, and
  `policy: provenance=advisory|required`. Precedence must be unambiguous and is never decided by reading order.
  It orders sources for interpreting a conflict and never erases the conflict. After freeze `SOURCE-BRIEF.*` is
  evidence and history, never an authority; the governed context wins over it.
- **Working agreements.** Team agreements live in `gtt-domain/working-agreements.md` (versioned, reviewed);
  a person's own preferences in `.gtt/local/preferences.md` (local, never committed). Both sit below governed
  context, are not Session Memory, never override a governed decision (the gate rejects one that tries), and no
  agent authors its own.

## Two confirmations

Do not collapse these into one:

### Confirmation A — source/design

Is the user's design document complete and ready to be used?

### Confirmation B — governed context

Do the generated six context files accurately represent the user's intended solution?

Both confirmations matter.

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
- `.copilot/copilot-instructions.md`
- `.cursor/rules/gtt.mdc`, `.cursor/rules/gtt-implementation.mdc`, `.cursor/hooks.json`
- `.agents/skills/gtt/SKILL.md`, `.openhands/hooks.json`

inspect before changing.

Report conflicts explicitly.

Do not silently overwrite.

Preserve the host project's existing source structure.

An ADE path that already exists in the host — its own `.claude/settings.json`, say
— is a conflict for that file: `gtt-ade.sh install` reports it and writes nothing;
it never merges or overwrites, and it never records as GTT's a file GTT did not
install.

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

do not directly modify governed context.

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
```

## Change requests

Routine implementation does not require a change request.

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

## Human Promotion Boundary

Preparing a governed change and promoting it are different acts. The agent
does the first; only the human does the second.

```text
PROPOSAL
    ↓
PROMOTION PACKAGE      (ADR draft + affected context files + apply-*.sh)
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
**promotion package** entirely under `gtt-domain/proposals/`: the ADR draft, the
full text of every affected `gtt-domain/context/` file, and an executable script —
`apply-ADR-NNN-<slug>.sh` — that applies all of them together.

The script is a first-class GTT artifact, not a convenience wrapper:

- lives in `gtt-domain/proposals/`, the one directory the agent may always write to;
- opens with a header naming the proposal and ADR and stating that human
  execution is required;
- lets the human view the ADR text and the exact diff against current context
  before deciding, and asks for an explicit confirmation before writing
  anything — not a single blind `[yes/no]`;
- applies every file the approved change touches in one run, and stops with a
  clear error rather than continuing after a partial failure;
- is never executed by the agent, under any circumstance — the human runs it
  from the project root: `bash gtt-domain/proposals/apply-ADR-NNN-<slug>.sh`.

After generating it, the agent must plainly tell the user: that a promotion
script was generated and exactly where it is, what it will change, that they
must review the proposal, ADR, and script before running it, the one-line
command to run it, that execution is their decision, and that the agent has
not promoted the change automatically. Generating a proposal, an ADR draft, or
a promotion script is never itself approval — each governed promotion needs
its own explicit human decision, and approving one change does not carry over
to the next.

For changes that do not touch governed context — a development-line change
applied straight to `gtt-domain/backlog.md` (see *Backlog governance*) — this
boundary does not apply; that stays a direct edit after approval, no ADR and
no script.

## Protected context

Do not bypass the protection mechanism by:

- renaming governed files;
- creating duplicate copies outside the governed location;
- moving governed files;
- editing through an alternate path;
- disabling the guardrail to make a change.

If the requested change is legitimate, use the governed change process.

## Source preservation

`SOURCE-BRIEF.*` is the original source used to bootstrap the governed context.

Do not silently rewrite it after bootstrap.

If the user wants the source design changed, treat that as an explicit design change and report the consequences for governed context.

## Completion report

After bootstrap, report in chat **and** append this same report to
`.gtt/docs/gtt-completion.md` — that file is the durable record; chat output
alone is lost once the session ends. Append, do not overwrite, on a later
re-run (ADE/adapter switch, migration, re-freeze).

```text
GTT Bootstrap completed

Created:
- ...

Preserved:
- ...

Conflicts:
- ...

Source:
- ...

Design assessment:
- STRONG / ADEQUATE / POOR / not applicable (no design document) - strengthened: yes / no - several documents: consolidated / kept as sources / not applicable
- THINK Depth: QUICK / STANDARD / DEEP - selected by the human / not selected (STANDARD applied) - escalations: <from -> to, accepted / declined, who, date; or "none">

Detected ADE:
- ...

Adapter installed:
- ...

Adapters excluded:
- ...

Native support:
- yes / no — ...

Method plan:
- light / medium / hard / team - selected by the human / not selected

Backlog:
- defined / not yet defined — reconciled: yes / no / not applicable
- Stories not designed (Undesigned): <count, or "none"> - not implementable until designed and approved

Context confirmation:
- confirmed / pending

Freeze:
- executed / pending

Protection verification:
- passed / pending

CI gate:
- configured / pending

Protection:
- GTTGuard markers found: <count, or "none"> — registry: initialized / not applicable

Human action required:
- ...
```

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
- Never execute a generated promotion script, or apply its changes by any
  other means, on the agent's own initiative — see *Human Promotion Boundary*.
- Never treat a drafted proposal, ADR, or promotion script as approval for the
  next one; each governed promotion requires its own explicit human decision.
- Never delete `AGENTS.md`.
- Never bypass governed protection after freeze.
- Never treat a detected ADE as installed, authorized, governed or participating; only the human's explicit choice makes an ADE participate.
- Never install an adapter for an ADE the human did not choose, and never reintroduce one a prior run excluded unless the human says so.
- Never infer the participating or Primary ADE from the underlying model, from adapter files that merely happen to exist, or from a binary on the PATH; ask if it cannot be established with confidence.
- Never give the Primary ADE, or any ADE, authority over a governed artifact, and never introduce an ADE hierarchy, agent voting or arbitration.
- Never write a `[PROPUESTA]` inside governed context, never leave a `[VACÍO]` unclassified there, and never use an OPEN gap — or the precedence of a source — as authorisation to change a frozen design or to hide a `[CONFLICTO]`.
- Never let a working preference override governed context, never author your own preferences, and never commit `.gtt/local/preferences.md`.
- Never treat an instruction file or ADE overlay (`AGENTS.md`, `.claude/`, `.kiro/`, `.copilot/`, `.codex/`, ADE memory or session history) as governance authority.
- Never hand-edit `.gtt/ade.json`; write it only through `.gtt/scripts/gtt-ade.sh`. Never remove an ADE path GTT did not install.
- Never copy the Initial Design Questionnaire, or its methodology, out of the Bootstrap, and never write a `[PROPUESTA]` or an ADE inference as a confirmed decision.
- Never select, default, infer or change the Method Plan on the human's behalf; never present a plan as a quality level; never report the unselected fallback as a choice; and never treat any plan as weakening an invariant or as permission to skip a human confirmation.
- Never turn deterministic work into a question, never stop at an intermediate mechanical step, and never use lower friction as a reason to skip a human confirmation, a gate or the Human Promotion Boundary.
- Never raise a question, a confirmation, a questionnaire turn, a proposal, an authorization request or a report on behalf of GTT without opening it with `@gtt · <what this is>`; never put the marker on ordinary work; and never treat the marker as a decision, an approval or evidence.
- Never invent Epics or Stories and present them as user-defined requirements.
- Never let a Story in `gtt-domain/backlog.md` silently override governed context or an accepted ADR.
- Never add or remove an Epic/Story, or materially change one, outside the `gtt-domain/change-request.md` flow.
- Never mark a Story `Ready`, `In Progress` or `Done` without its written Story Ready definition, and never write `Design Approved` without the Solution Designer's explicit approval of that Story.
- Never complete a title-only Story from your own reading of the sources and present it as designed; record it as `Undesigned` and say so.
- Never implement beyond the written Story; when something unwritten is needed, stop and update the Story first.
- Never copy governed context into a Story - reference it in `Governed by` - and never treat the backlog as a source of architecture.
- Never mark a Story `Done` without its `Closed` evidence, never write a closure you did not verify, and never mark an Epic `Completed` while one of its Stories is open.
- Never generate a scaffold artifact (`gtt-domain/change-request.md`, `gtt-domain/backlog.md`, `gtt-domain/session.md`, or the files under `.gtt/docs/`) at a temporary location and move it into place afterward — write it where `.gtt/scaffold/manifest.yaml` places it, directly.
- Never bypass a GTTGuard-protected artifact's approval requirement — not by renaming or removing its marker without authorization, not by editing around the enforcing hook, and not by hand-editing `.gtt/protection/registry.yaml`.
- Never treat approval of one GTTGuard proposal as authorization for a different protected artifact, and never confuse its lightweight, in-conversation promotion with the L0/L1 Human Promotion Boundary.

### Bootstrap documentation vs. installed project layout

The GTT Bootstrap repository and an installed GTT workspace have different documentation locations.

In the **GTT Bootstrap repository**, the canonical entry points remain at the repository root:

- `readme-gtt.md`
- `readme-gtt.es.md`
- `AGENTS.md`

`installation.md`, `installation.es.md`, `usage.md`, and `usage.es.md` live
under `.gtt/docs/` — indexed from `.gtt/docs/index.md` and linked from the two
READMEs above — the same as in any host project this repository bootstraps.

When an agent installs/bootstraps GTT into a **host project**, it MUST organize the installed GTT workspace as follows:

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
│   ├── local/                    #   user-level working preferences (local, never committed)
│   ├── ade.json                  #   per-project ADE state: participating, primary, install ledger (installed projects)
│   ├── scaffold/manifest.yaml    #   also the ADE registry (overlays:) and the templates: the Bootstrap owns
│   ├── scaffold/templates/       #   Bootstrap-owned templates (the Initial Design Questionnaire)
│   ├── scripts/
│   ├── session-adapters/
│   └── docs/                     #   GTT's own documentation: index, installation, usage, method-plans, docs, evidence,
│                                 #   gtt-completion, session-adapter-contract
│
├── gtt-domain/                   # THE DOMAIN GOVERNED BY GTT-METHOD
│   ├── context/                  #   L0 governed context
│   ├── adr/                      #   L1 accepted decisions
│   ├── proposals/                #   governed drafts awaiting a human decision
│   ├── backlog.md
│   ├── working-agreements.md     #   team working agreements (optional; below L0, never authority)
│   ├── change-request.md
│   ├── session.md                #   derived operational state (never authority)
│   └── .frozen                   #   freeze marker, written by gtt-freeze.sh
│
└── .claude/ | .kiro/ | .copilot/ | .cursor/rules/ | .agents/skills/gtt/
                                  # ADE OVERLAYS - one per participating ADE; exactly one ADE is Primary
```

`.gtt/` is the GTT Engine (with GTT's own documentation in `.gtt/docs/`) and
`gtt-domain/` is the governed domain (`context/`, `adr/`, `proposals/`,
`backlog.md`, `change-request.md`, `session.md`, `.frozen`). Each
artifact is generated directly at its place in the scaffold, never written
elsewhere and moved afterward.


Install the portable core plus the overlay of every ADE the human chose to have participate (see *Multi-ADE participation*). Each remains at the host-project root, never moved under `.gtt/`:

```text
.claude/                         # Claude Code
.kiro/                           # Kiro
.copilot/copilot-instructions.md  # GitHub Copilot
.cursor/rules/gtt*.mdc            # Cursor (two rule files; the rest of .cursor/ is the host's)
.cursor/hooks.json                # Cursor (write block + session context, unverified in the ADE)
.agents/skills/gtt/SKILL.md       # OpenHands (one skill; AGENTS.md is its entry point)
.openhands/hooks.json             # OpenHands (write block + session context, unverified in the ADE)
```

Codex takes no adapter file beyond `AGENTS.md` itself. OpenHands reads `AGENTS.md` as its
always-on entry point and takes one repository skill beyond it. Do not install the adapters for ADEs the human did not choose, even if the GTT Bootstrap source contains them all.

`readme-gtt.md` and `readme-gtt.es.md` ARE installed at the host-project
root — they are the human-facing GTT entry points and must stay
discoverable there, not buried under `.gtt/docs/`. `installation.md` and
`usage.md` (and their `.es.md` pairs) ARE also installed, under `.gtt/docs/`
alongside `index.md`, `gtt-completion.md`, and `evidence.md` — indexed from
`.gtt/docs/index.md` and linked from the two READMEs at root.

The **project-facing GTT README MUST be installed as**:

```text
.gtt/README.md
```

`.gtt/README.md` is the operational README for the GTT Engine as installed in that project. It should explain the installed GTT workspace and its operation; it is not a reason to dump the bootstrap repository's documentation into the host project's root.

The agent MUST:

1. Clone/download the GTT Bootstrap repository into a temporary/work location.
2. Read the bootstrap `AGENTS.md` and canonical `readme-gtt.md` before installing.
3. Preserve the host project's existing structure and files.
4. Detect the candidate ADEs (an observation, never a choice), show them to the human, and obtain the participating ADEs and exactly one Primary; if that cannot be established with confidence, ask rather than guess.
5. Install the portable core plus only the overlays of the participating ADEs — `bash .gtt/scripts/gtt-ade.sh install --from <catalog> --participating a,b --primary a`, a dry run first and then `--apply` — and explicitly exclude the others; the source repository is a catalog, not a package to install whole.
6. Create/organize the GTT scaffold as defined above and declared in `.gtt/scaffold/manifest.yaml`.
7. Keep `AGENTS.md`, `readme-gtt.md`, and `readme-gtt.es.md` at the host-project root.
8. Write `gtt-domain/change-request.md` and `gtt-domain/backlog.md` under `gtt-domain/` and `index.md` and `gtt-completion.md` under `.gtt/docs/` — directly, never generated elsewhere and then moved.
9. Install the project-facing README at `.gtt/README.md`, keep the Engine directories (`scaffold/`, `scripts/`, `index/`, `protection/`, `session-adapters/`, `docs/`) under `.gtt/`, and place `context/`, `adr/`, `proposals/` and the derived and state files under `gtt-domain/`.
10. Preserve the original design/source brief (`SOURCE-BRIEF.*`) in the host project according to the GTT bootstrap procedure.
11. Never move, rename, duplicate, redistribute, or silently overwrite an existing host-project file.
12. If a target file already exists, stop and report the conflict rather than silently replacing it.
13. Do not automatically freeze the project. `.gtt/scripts/gtt-freeze.sh` is run after human review/confirmation.
14. On re-run, never drop a participating ADE, never reintroduce an ADE that a prior bootstrap explicitly excluded unless the human says so, never change the Primary ADE unless the human says so, and never overwrite an existing overlay file outside the normal conflict-reporting rule above. A project that predates `.gtt/ade.json` is migrated with `gtt-ade.sh adopt`: its existing ADE is recorded as both Primary and participating only if that matches the actual state, and never inferred where several overlays exist.
15. If the project has no sufficient design document, offer the Initial Design Questionnaire through `.gtt/scripts/gtt-template.sh` rather than improvising an interview; never keep a second copy of it.

The bootstrap entry points stay at the root **of the bootstrap repository**. Inside a host project, the installed operational documentation goes under `.gtt/docs/`, the governed domain under `gtt-domain/`, and the Engine under `.gtt/`.
