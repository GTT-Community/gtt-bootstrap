# GTT Bootstrap

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> **When context doesn't govern AI, AI governs the solution.**

The official starter kit for **Governance Throw Think (GTT)** — a practical flow for AI-assisted software development.

**Context is the Source of Truth.**

Works with Claude Code, Kiro, Copilot and Codex · CC BY 4.0

🌐 **Languages**
- 🇺🇸 English (canonical)
- 🇪🇸 [Español](readme-gtt.es.md)

---

## Quick navigation

- [Usage flow](#usage-flow)
- [ADE adapters](#ade-adapters)
- [Mandatory GTT workspace scaffolding](#mandatory-gtt-workspace-scaffolding)
- [Workspace hygiene](#workspace-hygiene)
- [The problem](#the-problem)
- [The two files you will always touch](#the-two-files-you-will-always-touch)
- [The map](#the-map)
- [Changing something](#changing-something)
- [Human Promotion Boundary](#human-promotion-boundary)
- [Backlog](#backlog)
- [Governance and observation: the two planes](#governance-and-observation-the-two-planes)
- [Protected artifacts (GTTGuard)](#protected-artifacts-gttguard)
- [Keeping the map honest](#keeping-the-map-honest)
- [Design principle](#design-principle)
- [Structure](#structure)
- [Context layers](#context-layers)
- [Getting started](#getting-started)
- [Tool support](#tool-support)
- [What you maintain](#what-you-maintain)
- [Requirements](#requirements)
- [Evolution](#evolution)
- [License](#license)

---

## Usage flow

### 1. Bootstrap the governed context

**Step 1 — Start with your design, if you have one.**

Leave your design document at the project root. Any name and any common format is acceptable: `.md`, `.txt`, Word, PDF, or equivalent.

There is no filename convention to follow. The document should be finished rather than a draft and should describe, as applicable:

- idea and goal
- vision
- requirements
- proposed architecture
- technology stack
- constraints
- development rules

Ideally, review the design with an LLM before bootstrapping to identify inconsistencies.

If you do not have a design document yet, skip this step. The agent can define the context with you through conversation.

**Step 2 — Tell your ADE/AI coding agent to bootstrap GTT.**

For example:

> `clone GTT Bootstrap and bootstrap the project`

The agent may be Claude Code, Kiro, Codex, GitHub Copilot, Cursor, OpenHands, Google Antigravity, or another ADE capable of following the GTT bootstrap procedure.

The bootstrap process:

1. Downloads/clones GTT Bootstrap into the project — the source distribution is a catalog of every adapter, not something to install whole.
2. Detects the candidate ADEs (an observation, never a choice), shows them to you, and asks which ADEs participate in the project and which one is Primary. If that can't be established it asks instead of guessing — see [ADE adapters](#ade-adapters).
3. Installs the portable GTT core plus only the overlays of the participating ADEs, explicitly excluding the others.
4. Checks whether `gtt-domain/context/` still contains template placeholders.
5. Checks the project root for the design/source document.
6. If there is more than one candidate, asks instead of guessing — and when several really are design sources, asks you whether to consolidate them into one document or keep them all as declared sources. If you have no design document at all, it offers the Initial Design Questionnaire — see [Starting without a design document](#starting-without-a-design-document).
7. If a document exists, reads it and writes a **Design Assessment**: how good it is, area by area, whether it meets the minimum floor (stack and datastore decided), and what would strengthen it — see [Assessing and strengthening an existing design](#assessing-and-strengthening-an-existing-design).
8. Asks you to confirm that the design is complete and not a draft. If it is a draft, or the assessment found it poor, it offers to strengthen it with you instead of mapping it as it is.
9. Reads the confirmed source and maps it into the six governed context files.
10. Asks directly for information that the source does not answer.
11. Summarizes the resulting context and asks for a separate explicit confirmation that the six files accurately represent the design.
12. Only after confirmation, writes the completed context files.
13. Preserves your original source document as `SOURCE-BRIEF.*` at the project root when one was provided (or the reviewed questionnaire that stood in for it).
14. Tells you to review the result and run `.gtt/scripts/gtt-freeze.sh` to ratify it.

Before the project is frozen, there is nothing ratified yet to protect, so the agent may write `gtt-domain/context/` directly during this one-time bootstrap.

Freezing is a **human act**. It validates that the context no longer contains template placeholders and creates the `gtt-domain/.frozen` marker. That marker switches the project into the governed regime, where governed paths become protected from direct agent writes.

See `.claude/skills/gtt-bootstrap/SKILL.md` for the detailed procedure.

From that point onward, the agent reads the governed context first before making implementation decisions.

The idea is simple:

> You and the agent define what you want to build and how it should be built; you confirm it; GTT turns that agreed design into governed context; then AI develops under that context.

**Method Plan.** During bootstrap you are asked how much operational work to delegate to GTT — one choice among **Light**, **Medium**, **Hard** and **Team**. It is an operating profile, not a quality level; GTT derives the technical policies from it and never picks one for you. No plan turns governance off. What each plan does without asking, what it asks you, and what it requires is spelled out in [.gtt/docs/method-plans.md](.gtt/docs/method-plans.md).

For the detailed procedures, see [.gtt/docs/installation.md](.gtt/docs/installation.md) and [.gtt/docs/usage.md](.gtt/docs/usage.md).

### 2. Manual installation

GTT can also be installed manually by a human.

At minimum, the project must receive the GTT workspace scaffolding defined below. Copy the shipped GTT files/directories into the project root, preserve the required locations, merge the supplied `.gitignore` rather than overwriting an existing one, and then complete the governed context before freezing it.

See [.gtt/docs/installation.md](.gtt/docs/installation.md#manual-installation) for the complete manual procedure.

### 3. Agent-assisted installation

An ADE can install GTT from this repository when the user provides the repository URL or asks the agent to bootstrap GTT.

The agent should:

1. Read this README first.
2. Identify the GTT bootstrap contract and required workspace structure.
3. Inspect the host project before changing anything.
4. Detect source/design documents without guessing.
5. Report conflicts instead of overwriting them.
6. Create the required scaffolding.
7. Populate governed context through the bootstrap workflow.
8. Obtain explicit user confirmation before ratifying the context.
9. Run the freeze procedure when instructed.
10. Report exactly what was created, preserved, skipped, or requires human action.

See [AGENTS.md](AGENTS.md) for the agent-oriented contract.

---

## ADE adapters

GTT ships a portable core plus one adapter per supported ADE. A target
project receives the portable core plus the adapter of every ADE you chose to
have participate — never the whole catalog, never an adapter nobody chose.
The GTT Bootstrap source distribution contains every adapter because it is a
catalog; installing all of them into a project is not the intended flow.

**One governance model, several integration surfaces, one Primary ADE.** A project
may use one ADE or several, possibly at the same time (three terminals in one
editor, say). The governance, the governed artifacts and the Human Promotion
Boundary are the same for all of them, and every participating ADE gets its
overlay — governance never depends on the Primary being the one that is active.
Exactly one participating ADE is the **Primary ADE**: the principal environment of
the project's workflow. It is a workflow identifier, not an authority — it does not
outrank, approve or arbitrate for any other ADE, and no ADE ratifies anything.

| Term | Meaning |
| --- | --- |
| Detected | Observed on this machine or in the repository. A candidate only — never installed, authorized, governed or participating by itself. |
| Participating | Chosen by you to be governed by GTT; it gets its overlay. |
| Primary | One participating ADE, chosen by you. |

The choice is recorded in `.gtt/ade.json`, and the ADE registry is the `overlays:`
section of `.gtt/scaffold/manifest.yaml`; both are read and written only through
`.gtt/scripts/gtt-ade.sh` (`list`, `detect`, `state`, `validate`, `owned`, `install`,
`adopt`, `set-primary`, `record`, `remove`, `update`). Every mutating command is a dry
run until `--apply`, never overwrites a file GTT did not install, and rolls back on
failure. Instruction files and overlays (`AGENTS.md`, `.claude/`, `.kiro/`,
`.copilot/`, `.codex/`, an ADE's memory or session history) are integration surfaces:
they let an ADE take part in GTT and never become an authority of their own.

**Portable core:** `AGENTS.md`, `readme-gtt.md`, `readme-gtt.es.md`, `SOURCE-BRIEF.*` (if a source document existed) at the project root, plus the governed domain (`gtt-domain/`: `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`) and the GTT Engine (`.gtt/`, including GTT's own documentation in `.gtt/docs/`, declared by `.gtt/scaffold/manifest.yaml`).

What each ADE's adapter contains — a project with several participating ADEs has the union of their rows:

| Host ADE | Adapter | `.claude/` | `.kiro/` | `AGENTS.md` | `.copilot/copilot-instructions.md` |
| --- | --- | :---: | :---: | :---: | :---: |
| Claude Code | Claude | YES | NO | YES | NO |
| Kiro | Kiro | NO | YES | YES | NO |
| Codex | Portable/AGENTS | NO | NO | YES | NO |
| GitHub Copilot | Copilot | NO | NO | YES | YES |
| Cursor | Cursor | NO | NO | YES | NO |
| OpenHands | OpenHands | NO | NO | YES | NO |
| Google Antigravity | Antigravity | NO | NO | YES | NO |
| Other supported ADE | Explicit adapter only | only if mapped | only if mapped | per support | per support |
| Unknown ADE | Portable/unknown | NO | NO | do not guess | NO |

Cursor, OpenHands and Antigravity integrate through files of their own, outside
the four columns above, and GTT owns only those files — never the host's
`.cursor/`, `.agents/` or `.openhands/`. `.agents/` is shared: OpenHands and
Antigravity both read it, and so may the host's own tools:

| ADE | What GTT installs | How the ADE loads it |
| --- | --- | --- |
| Cursor | `.cursor/rules/gtt.mdc` (always applied), `.cursor/rules/gtt-implementation.mdc` (attached to `src/`, `lib/`, `tests/`) and `.cursor/hooks.json` | Cursor reads project rules from `.cursor/rules/*.mdc`, `AGENTS.md` natively, and project hooks from `.cursor/hooks.json` |
| OpenHands | `.agents/skills/gtt/SKILL.md` and `.openhands/hooks.json` | OpenHands includes `AGENTS.md` in every conversation, loads repository skills from `.agents/skills/`, and hooks from `.openhands/hooks.json` |
| Google Antigravity | `.agents/rules/gtt.md` (always on), `.agents/rules/gtt-implementation.md` (attached to `src/`, `lib/`, `tests/`) and `.agents/hooks.json` | Antigravity reads `AGENTS.md`, workspace rules from `.agents/rules/*.md`, and hooks from `.agents/hooks.json` |

The three hook files point at one shared engine, `.gtt/scripts/gtt_protect.py`,
which applies the same rules as Claude Code's own hooks — governed paths, the
freeze regime, promotion scripts, GTTGuard — and answers in each ADE's own
shape; on session start it injects the session context where the ADE has such
an event. The engine is tested against the payloads each ADE documents, but
**it has not been verified inside Cursor, OpenHands or Antigravity**. The
registry says so (`enforcement: realtime-hook-unverified`), and until someone
proves it in the ADE the CI gate is the only guaranteed layer there. If a host
project already has its own `hooks.json`, `gtt-ade.sh install` reports the
conflict and writes nothing — merge the GTT entries by hand.

What "supported" means for Antigravity: GTT installs, records, validates and
maintains the integration. It does not mean Antigravity guarantees the
real-time block.

| Antigravity | Status |
| --- | --- |
| Registry, detection, install / update / remove, participating, Primary, the contract through `AGENTS.md` plus the rule, validation, CI gate | supported |
| Session context and GTT's procedures | partial — Antigravity has no session-start event, so the rule tells the agent to run `gtt-session-context.sh`; both depend on the model following the instruction |
| The real-time block in its CLI, its IDE and its desktop app; whether `AGENTS.md` is loaded in full (it is larger than the per-file limit Antigravity documents for rules); what Antigravity does with the hook's exit code | **unverified** |
| Context injected at session start, merging into an existing `.agents/hooks.json`, native Antigravity skills | not supported |

> **Known limitation:** GitHub Copilot's actual discovery path for
> repository-wide custom instructions is `.github/copilot-instructions.md`,
> per current GitHub documentation. GTT deliberately keeps the file at
> `.copilot/copilot-instructions.md` instead, for naming consistency with
> `.claude/` and `.kiro/` — which means Copilot will not pick it up
> automatically at that path. Mirror it to `.github/copilot-instructions.md`
> as well if you need Copilot to load it on its own.

Detection is based on the environment actually present — never on the underlying
model. A Claude model is not Claude Code; a GPT model is not Codex; the Anthropic
or OpenAI API alone is neither. And detection is not participation: files or a
binary found for an ADE (`gtt-ade.sh detect`) make it a *candidate*. If the target
project already shows files for more than one ADE (for example a prior partial
setup left both `.claude/` and `.kiro/`), the agent does not adopt one just because
its files exist — it shows the candidates and asks:

> Detected these possible ADEs.
>
> - Claude Code
> - Kiro
>
> Which of them should participate in this project (GTT installs and governs each
> one's integration), and which one is the Primary ADE?

Only Claude Code has a **verified** real-time write block. Cursor, OpenHands and
Antigravity ship one that is tested but unverified in the ADE; every other participating ADE is
governed by its instructions plus the CI gate (`gtt-check-protection.sh`) — governed
is not the same as hard-blocked, and no ADE is credited with a guarantee it does not
have (`enforcement:` in the registry states it per ADE).

For an ADE with no native adapter, GTT installs the portable core only and
reports plainly that no native adapter exists — it never invents one.

Re-running bootstrap never drops a participating ADE, never reintroduces an ADE a
prior run excluded unless you say so, and never changes the Primary ADE unless you
say so. A project that predates `.gtt/ade.json` keeps working unchanged;
`gtt-ade.sh adopt` records its existing ADE as both Primary and participating —
only when that matches the actual state (where several overlays exist, it is never
guessed).

Full algorithm: `.claude/skills/gtt-bootstrap/SKILL.md` (step 0). Validate an
installed project with `.gtt/scripts/gtt-check-adapter.sh` (every participating ADE
against `.gtt/ade.json`; a missing or inconsistent integration FAILS, a detected ADE
that does not participate is a WARN). The single-ADE matrix above remains available
as `.gtt/scripts/gtt-check-adapter.sh <claude|kiro|codex|copilot|unknown>`.

---

## Assessing and strengthening an existing design

Having a design document is not the same as having a design good enough to
govern. When one exists, the Think stage begins with a **Design Assessment**
(`.gtt/scaffold/templates/gtt-design-assessment.md`, materialized to
`gtt-domain/proposals/bootstrap/design-assessment.md`) that the Primary ADE
writes and you read:

| Part | What it says |
|---|---|
| By area | Vision, scope, users, capabilities, non-functional requirements, architecture, technology stack, data, security, integrations, deployment, development architecture, observability, constraints — each `SOLID`, `THIN` or `MISSING`, with the place in the document that supports the rating |
| Minimum floor | The problem and scope are stated, the architectural style is stated, **the technology stack is decided** (language and runtime, framework, compute model) and **the datastore is decided** or explicitly not needed |
| Verdict | `STRONG`, `ADEQUATE` or `POOR`. Below the floor the design is `POOR`, whatever else it gets right |
| Strengthening plan | What would make it better. For every stack layer that is undecided or decided without a reason: the options that fit *this* project, the trade-offs of each, and a recommendation that says what it optimises for and what it gives up |

**Strengthening is offered when the design is `STRONG` or `ADEQUATE`, and
required when it is `POOR`** — a design with no decided stack is not mapped
into governed context as it is. Strengthening is written, not talked about:
the ADE carries what your documents already establish into the Initial Design
Questionnaire, each statement with the `[FUENTE]` it came from, and interviews
you only about what was thin or missing. Your documents are never rewritten.

**THINK Depth — how deep the assessment goes.** You choose it when the
assessment starts; the ADE asks once and never infers it:

| | `QUICK` | `STANDARD` | `DEEP` |
|---|---|---|---|
| For | simple or small designs | ordinary projects | complex, critical or highly uncertain systems |
| Assessment | the floor areas and the areas your documents make relevant; critical gaps | every area, with its evidence | exhaustive; architecture, non-functional requirements, security, data, integrations, deployment, observability, development architecture and constraints in depth |
| Stack | options only for an undecided floor layer | reasonable alternatives, trade-offs, a recommendation | stack **and** architectural alternatives, dependencies and risks explicit |
| Questionnaire | reduced: only what the floor or a critical gap needs | adaptive: what was thin or missing | deep and iterative |

The depth decides how far THINK digs, never which rules it may skip. At every
depth the floor is assessed line by line and a design below it is `POOR`,
options are `[PROPUESTA]`, unknowns stay `[VACÍO]`, disagreements stay
`[CONFLICTO]`, you decide, and freeze works the same. It is **not** the Method
Plan: the two are independent and chosen separately. If you
choose none, `STANDARD` applies as a fallback and is reported as *not selected*.

The ADE never changes the depth. When what it finds justifies a deeper level
— regulated data, requirements that constrain the architecture, documents
that disagree on something structural — it **proposes** an escalation, one
level at a time and with the evidence, in the assessment's escalation log, and
keeps working at the current depth until you accept or decline.
`gtt-project.sh think` reports the recorded depth, and validation fails on a
depth nobody decided or on a verdict above `POOR` with the floor unmet.

GTT helps you reach the best stack; it does not choose it. Every option and
every recommendation is a `[PROPUESTA]`, and only the ones you decide become
part of the design.

**More than one design document.** They are resolved before design continues,
and you choose how:

| Option | What happens |
|---|---|
| `CONSOLIDATE` | The ADE drafts one design document from all of them — every statement with its `[FUENTE]`, every disagreement left visible as a `[CONFLICTO]` for you to resolve. After your review it is the single source document |
| `KEEP_AS_SOURCES` | Each document stays as it is, declared in the source manifest with an authority and an unambiguous precedence. All of them are context throughout the design work; precedence orders the reading and never erases a conflict |

The assessment is an instruction to the ADE and a document for you: it decides
nothing and governs nothing, and the rating itself is the ADE's judgment —
nothing deterministic verifies it.

---

## Starting without a design document

If the project has no sufficient design document, the Bootstrap offers its **Initial
Design Questionnaire** (`.gtt/scaffold/templates/gtt-initial-design-questionnaire.md`,
declared under `templates:` in the manifest). It is an elicitation instrument for the
Primary ADE, not CLI logic and not governed architecture:

1. The need is detected (by you, the ADE or a CLI) and the template is requested from the
   Bootstrap — `.gtt/scripts/gtt-template.sh materialize initial-design-questionnaire --apply`
   creates the working copy at `gtt-domain/proposals/bootstrap/initial-design-questionnaire.md`.
   Nobody else carries a copy of the questionnaire or of its methodology.
2. The Primary ADE conducts an adaptive interview: it inspects the project first, asks you
   only what is missing, and fills the document in as you go. You are never expected to
   complete the whole form by yourself.
3. Unknowns stay `[VACÍO]` (better than an invented answer); disagreements stay `[CONFLICTO]`;
   the ADE's suggestions stay `[PROPUESTA]` until you decide. None of them is a confirmed
   decision.
4. After your review, with Readiness `READY` or `READY_WITH_OPEN_ITEMS`, the completed
   questionnaire is your source document (Confirmation A): it is preserved verbatim as
   `SOURCE-BRIEF.md`, and the governed context is derived from it through the normal
   bootstrap and Confirmation B. Completing the questionnaire never makes anything
   governed by itself.

---

## Mandatory GTT workspace scaffolding

When bootstrapping GTT into a project, **the AI coding agent/ADE MUST create and preserve the following workspace structure exactly as defined below**:

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
│   ├── scaffold/manifest.yaml
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

### Scaffolding rules

- `AGENTS.md`, `readme-gtt.md`, `readme-gtt.es.md`, and `SOURCE-BRIEF.*` (when one exists) MUST remain at the project root.
- The governed domain — `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/proposals/`, `gtt-domain/backlog.md`, `gtt-domain/change-request.md`, `gtt-domain/session.md`, `gtt-domain/.frozen` — MUST be generated directly under `gtt-domain/`, never elsewhere and moved afterward. `gtt-domain/.frozen` is written only by `.gtt/scripts/gtt-freeze.sh`, after human confirmation; `gtt-domain/session.md` is derived and regenerated by `.gtt/scripts/gtt-status.sh`.
- The GTT Engine (`scaffold/`, `scripts/`, `index/`, `protection/`, `session-adapters/`) and GTT's own documentation (`docs/`: `index.md`, `installation.md`, `usage.md`, `method-plans.md` and their `.es.md` pairs, `gtt-completion.md`, `evidence.md`, `docs.md`, `session-adapter-contract.md`) MUST live under `.gtt/`, and the GTT bootstrap README MUST be installed as `.gtt/README.md`. `.gtt/scaffold/manifest.yaml` is the canonical, declarative definition of this scaffold.

- The agent MUST NOT move, rename, duplicate, or redistribute GTT artifacts outside this structure.
- The agent MUST preserve the host project's existing source structure and must not silently overwrite an existing file with the same name. Conflicts MUST be reported and resolved explicitly.
- ADE-specific files required by the host tool — `.claude/`, `.kiro/`, or `.copilot/copilot-instructions.md` — remain at their required locations and do not change the GTT workspace contract. Only the adapters of the participating ADEs are installed; see [ADE adapters](#ade-adapters).

This structure is a **GTT bootstrap contract**, not merely a documentation convention.

---

## Workspace hygiene

**GTT keeps two homes apart: the Engine (`.gtt/`) and the governed domain
(`gtt-domain/`), plus the ADE overlay.**

The project root belongs to the project. GTT occupies exactly two directories
of it, both namespaced so that they cannot collide with the project's own
`docs/`, `context/`, `adr/` or `proposals/`: `.gtt/` holds GTT's own machinery
(scripts, artifact identity and technical index, protection registry,
session-adapter declarations, the scaffold manifest) and GTT's own
documentation (`.gtt/docs/`); `gtt-domain/` holds the domain governed by
GTT-Method — `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`,
`session.md`, `.frozen`. Beside them the root keeps only the human-facing entry
points (`readme-gtt.md`, `readme-gtt.es.md`, `SOURCE-BRIEF.*`), `AGENTS.md` and
the ADE overlay — instructions to agents, in neither group.

The invariant: architectural authority (L0/L1) exists only in
`gtt-domain/context/` and `gtt-domain/adr/`; executable GTT logic exists only in
`.gtt/`. `gtt-domain/` holds none in operation: `gtt-domain/proposals/` holds
governed drafts, including promotion scripts that only a human ever runs.

The test: *can I tell, from the directory name alone, whether a file is GTT
machinery or documentation about GTT (`.gtt/`), or the project's governed state
(`gtt-domain/`)?*

| Part | Where | Owned by |
| --- | --- | --- |
| Engine | `.gtt/` (including `.gtt/docs/`) | GTT |
| Governed domain | `gtt-domain/`: `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen` | the Solution Designer (agents draft in `gtt-domain/proposals/` only) |
| ADE overlay | `.claude/`, `.kiro/`, `.copilot/` | the ADE integrations — one per participating ADE, exactly one of them Primary (a workflow identifier, never an authority) |


`.gtt/scaffold/manifest.yaml` declares this scaffold. There is one scaffold; ADEs
only add overlays to it. The bootstrap generates each artifact directly where
it belongs — it never writes it elsewhere and asks you to tidy up afterward, the
way earlier versions asked you to delete unused ADE adapters. See *ADE adapters*
above for the same selective-generation principle applied to tool integrations.
`.gtt/` and `gtt-domain/` are namespaced so they never collide with a host project's own `docs/`, `context/` or
`adr/`: if the host project already has either one, the bootstrap stops and reports the conflict instead of merging.

---

## The problem

AI accelerates implementation. Humans govern context and architecture.

The failure mode is not necessarily bad code — agents can write individually reasonable code. The deeper failure mode is **architectural drift**: a sequence of individually defensible changes that collectively moves the solution somewhere nobody decided to go.

Drift is often invisible at the commit level and becomes visible only at the architecture level — precisely the level that is least likely to be reviewed continuously.

GTT makes architecture and its surrounding context explicit, protected, and machine-readable. Changing governed decisions becomes a deliberate act rather than an accidental side effect of implementation.

---

## The two files you will always touch

| File | What it is | When you touch it |
| --- | --- | --- |
| **`SOURCE-BRIEF.*`** (project root) | Your original design: vision, architecture, stack, constraints, in your own words | Once, before or during setup |
| **`gtt-domain/change-request.md`** | The front door for a requested change | Whenever a governed decision or the development line needs to change |

`SOURCE-BRIEF.*` stays at the project root — the one GTT artifact that is
purely yours to find quickly, never governance machinery. `gtt-domain/change-request.md`
sits in `gtt-domain/` with the rest of the governed state, and is the
single entry point you use constantly.

`gtt-domain/context/stack.md` is the file you will read most often — the one-screen map of what the system is — but it is an output, not a file you should normally edit by hand. Approved changes reach it through `gtt-domain/change-request.md`, never by silently editing the governed map.

---

## The map

`gtt-domain/context/stack.md` answers **“what is this system?”** without opening the code.

It provides seven views:

| # | View | Answers |
| ---: | --- | --- |
| 1 | Stack at a glance | What are we built on, and which ADR locked it? |
| 2 | Component map | What talks to what, over which protocol? |
| 3 | Deployment topology | Where does each piece run? |
| 4 | Observability | If it breaks at 3am, what do I look at? |
| 5 | Dependency rules | Which module may call which? |
| 6 | Map change log | One row per accepted ADR |
| 7 | Boundaries | Where does a change in the code mean the design may have changed, and how serious is it? Observation watches these |

The map uses Markdown plus Mermaid so it renders in GitHub and IDEs. There is no image to regenerate and no diagram tool to keep licensed. Most importantly, it diffs like code: a pull request can show exactly what changed in the architecture.

A stack-table row without an ADR in its **Locked by** column is itself a finding: a decision entered the system without passing through governance.

---

## Changing something

There is one entry point. You do not hunt for the right governed file.

```text
gtt-domain/change-request.md  ->  gtt-domain/proposals/  ->  you review + run one script  ->  gtt-domain/adr/ + gtt-domain/context/stack.md
      you state intent          agent drafts           the Human Promotion Boundary       governed/protected
      always writable           agent writable
```

Fill in the request block in `gtt-domain/change-request.md` with what needs to change, why, trigger, scope, impact, risk, and priority.

Then ask the agent to process the change request.

The agent returns a complete proposal covering:

- current decision
- suggested change
- impact
- risk
- alternatives
- exact stack-map rows that change

You approve the proposal. The agent then stages a **promotion package** in `gtt-domain/proposals/`: the ADR draft, the full text of every affected `gtt-domain/context/` file, and an executable script:

```bash
bash gtt-domain/proposals/apply-ADR-NNN-<slug>.sh
```

Review the proposal, the ADR, and the script, then run that one command yourself from the project root. The script lets you `view` the ADR text and the exact diff against current context, applies every affected file together only once you say `yes`, and is never executed by the agent — see [Human Promotion Boundary](#human-promotion-boundary).

**`gtt-domain/proposals/` is the only governed directory that an agent may write to as part of the governed change workflow.**

Routine implementation work does not need to enter this flow. If ordinary implementation repeatedly requires change requests, the constraints may be written too broadly and should be narrowed.

---

## Human Promotion Boundary

Preparing a governed change and promoting it are different acts, and GTT
keeps them that way:

```text
PROPOSAL -> PROMOTION PACKAGE -> HUMAN REVIEW -> EXPLICIT HUMAN EXECUTION -> GOVERNED CHANGE
```

> **AI may prepare the change. AI may not autonomously promote the change.**

The agent can analyze impact, draft the proposal, draft the ADR, prepare the
affected `gtt-domain/context/` files, and generate the promotion script. It cannot
execute that script, edit `gtt-domain/adr/` or `gtt-domain/context/` directly, or treat a
drafted proposal, ADR, or script as approval — each governed promotion needs
its own explicit decision from you, and approving one change never carries
over to the next.

The promotion script is a GTT artifact in its own right, not a convenience
wrapper. It lives in `gtt-domain/proposals/`, names the proposal and ADR it belongs
to in its header, asks for a final confirmation before it writes anything,
applies every file the change touches in one run, and fails clearly rather
than leaving the map half-updated. Full rule: `AGENTS.md` → *Human Promotion
Boundary*.

---

## Backlog

`gtt-domain/backlog.md` is the development line: Epics, Stories, and the work
currently expected to be built. It answers "what exists, what's next,
what's blocked" — it is a planning artifact, not architecture, and never a
second source of truth beside `gtt-domain/context/`.

```text
Governed Context / L0  ->  ADR  ->  gtt-domain/backlog.md  ->  Implementation
```

A Story that contradicts governed context or an accepted ADR is a finding,
not a resolution — it never silently overrides the architecture.

**Two kinds of entry, governed differently:**

| Entry | What it is | Who decides |
| --- | --- | --- |
| **Epic** | Intent and scope: its goal, what it includes, where it stops | The human approves it (`**Approved:** who — YYYY-MM-DD`). Adding, removing or materially changing one is the human's decision |
| **Story** | The working plan inside an approved Epic | The ADE. It creates, splits, rewrites, implements and closes Stories on its own — nobody approves a Story |

**A Story is not a gate.** An earlier version required each Story to be
designed and approved before it could be implemented. That put the human
inside the loop of ordinary work. A Story is a plan for how to get there, not
a decision about what the system is: what protects the design is not a
signature on a Story but **observation** (next section). If the work behind a
Story brings in a new backbone technology or changes a contract, GTT reports
it whatever the Story said.

Work the human asks for directly needs no Epic first. If Epics are defined
elsewhere but missing from the backlog, the agent reports the gap — it never
ignores them and never invents business requirements.

**Closure is evidence.** A `Done` Story records `Closed`: the date and what
closed it — commit or PR, tests passed. An Epic is `Completed` only when
every one of its Stories is `Done` or `Cancelled`.

`.gtt/scripts/gtt-check-backlog.sh` deterministically checks structure —
unique Epic/Story IDs, valid status values, an Epic that is `Planned`,
`In Progress` or `Completed` carries its `Goal` and its `Approved`, a
`Completed` Epic has no open Story. It reports, without failing, a `Done`
Story without `Closed` and Stories being worked under an Epic still
`Proposed`. It approves nothing. Whether an Epic is real, current and matches
the work is a judgment call the `gtt-audit` skill makes.

## Governance and observation: the two planes

> **GTT governs the boundaries. The ADE performs the work.**

GTT does not exist to approve ordinary code changes. It exists to protect the
human's design, intent, architecture and constraints while the ADE works on
its own inside them.

| | Governance | Work |
| --- | --- | --- |
| Answers | What the system is supposed to be | What is actually happening |
| Holds | intent, architecture, constraints, ADRs, Epics, the boundaries, the freeze | implementation, tests, refactors, commits, Stories |
| Who decides | the human — always | the ADE — no approval for ordinary work |
| GTT's part | proposals, promotion packages, freeze | observation |

**Freeze does not freeze the code.** It makes the design you approved the
authority and records a baseline (when, by whom, commit, digest of the
governed state). The code keeps changing. There is no unfreeze: after a
governed change is promoted, running `gtt-freeze.sh` again records a new
baseline and keeps the earlier one as history.

**During work GTT observes; it does not approve.**
`.gtt/scripts/gtt-observe.sh` compares the project with the frozen governed
state — Git, the filesystem, dependency manifests, the GTTGuard registry:
computed facts, never a model's opinion — and reports only what matters:

| Level | What happens |
| --- | --- |
| `NOTICE` | recorded; never announced |
| `WARNING` | announced once and recorded; work continues |
| `GOVERNANCE` | announced once and recorded; work continues; you decide before the next freeze |
| `BLOCKING` | the affected operation stops, and validation fails, until it is fixed |

Only `BLOCKING` interrupts work, and something is `BLOCKING` only because the
governed state says so — a rule you ratified in the `gtt-boundaries` block of
`gtt-domain/context/stack.md`, or an observation you rejected. A detector
that merely finds something unusual never blocks.

```text
@gtt · Observation
⚠ OBS-0003 WARNING    B-003  package.json#kafkajs
    new dependency `kafkajs`
    guards: Stack at a glance (section 1)
    work continues
```

Observations are kept in the governance backlog
(`gtt-domain/governance-backlog.json`), so nothing is lost and nothing is
reported twice. You decide on them when you want to:

```bash
bash .gtt/scripts/gtt-observe.sh backlog
bash .gtt/scripts/gtt-observe.sh accept OBS-0003 --by <you> --apply   # it stands
bash .gtt/scripts/gtt-observe.sh reject OBS-0003 --by <you> --apply   # validation fails until it is gone
bash .gtt/scripts/gtt-observe.sh defer  OBS-0003 --by <you> --apply   # later
```

Observation runs at every session start (through `gtt-status.sh`), after a
write on ADEs that have a post-write hook, and in validation and CI. The first
control every ADE shares is the Git pre-commit hook — your choice, one command:
`bash .gtt/scripts/gtt-git-hook.sh install --apply`. It can be skipped with
`git commit --no-verify`: the guaranteed layer is CI (`gtt-validate.sh` and
`gtt-check-stack.sh` on the pull request).

Full description: [`.gtt/docs/docs.md`](.gtt/docs/docs.md#the-two-planes-governance-and-observation).

## Protected artifacts (GTTGuard)

`gtt-domain/backlog.md` governs *what* gets built. GTTGuard governs *which pieces
of already-existing code an agent may never touch on its own* — a file, a
class, or a method. It is a sibling mechanism to L0/L1, not a copy of it:
it protects L3 code you opt into protecting, and its promotion model is
deliberately lighter than the Human Promotion Boundary above.

Mark a declaration and GTT does the rest:

```java
@GTTGuard(reason = "Financial calculation", source = "ADR-021")
public PaymentResponse calculatePayment(...) { ... }
```

```text
Developer adds @GTTGuard
        ↓
.gtt/scripts/gtt-guard-sync.sh detects it, resolves the symbol deterministically
        ↓
.gtt/protection/registry.yaml regenerated (derived — never hand-edited)
        ↓
.gtt/scripts/gtt-check-protection.sh validates it in CI
        ↓
.claude/hooks/protect-guard.py blocks an autonomous edit to it in real time
```

`getPayment()` next to a protected `calculatePayment()` in the same file
stays freely editable — only the marked symbol's resolved span is blocked,
and the hook fails safe to blocking the whole file if that resolution is
ever ambiguous. Requesting a change to a protected artifact goes through
`gtt-propose-change` (form 5): once you approve it **in conversation**, the
agent implements it directly and re-syncs the registry — no ADR, no script,
on purpose.

Real-time blocking exists on Claude Code today. Kiro, Codex, and GitHub
Copilot rely on the CI gate (`gtt-check-protection.sh`) plus an
instruction-plane note, the same honest fallback already used for the
two-regime `gtt-domain/context/`/`gtt-domain/adr/` condition.

Full mechanism: `AGENTS.md` → *Protected artifacts (GTTGuard)*. Procedures:
`.claude/skills/gtt-guard/SKILL.md` and `.claude/skills/gtt-propose-change/SKILL.md`.

---

## Keeping the map honest

Four mechanisms, from weakest to strongest:

| Mechanism | What it does |
| --- | --- |
| `AGENTS.md` | States the rule: an ADR that does not declare its effect on the map is incomplete |
| Skill `gtt-adr` | Requires a before/after stack delta plus a change-log row |
| Skill `gtt-audit` | Verifies views against manifests, the real import graph, and alert rules |
| `.gtt/scripts/gtt-check-stack.sh` | **Fails the build** when an ADR changes and the map does not |

The first three are instructions or procedures and therefore depend partly on model behavior. The fourth is deterministic enforcement.

---

## Design principle

Put each concern in the plane that can enforce it.

| Plane | Mechanism | Guarantee | Context cost |
| --- | --- | --- | --- |
| Control | `permissions.deny` + PreToolUse hook | Deterministic | Zero |
| Build | CI gate in `.gtt/scripts/` | Deterministic, at merge | Zero |
| Instruction | `AGENTS.md`, `.claude/rules/` | Probabilistic | Tokens |
| Procedural | `.claude/skills/` | On demand | Zero until invoked |

**Anything enforceable in the control plane should not be expressed only as an instruction.**

For example, writing “AI must not modify architecture files” into the context window costs tokens every session and is only probabilistic. Blocking the write at the control plane holds deterministically and costs no model context.

Instructions remain necessary for work requiring judgment: whether a change is architectural, whether implementation contradicts context, or whether an abstraction is warranted.

The second principle follows: **the layer determines both who may edit and when it loads.** Only the rules and hard constraints should be loaded at session start; the broader knowledge base remains available on demand.

---

## Structure

```text
AGENTS.md                       # portable core rules
readme-gtt.md                   # this file — setup, tool support
readme-gtt.es.md                # Spanish mirror
SOURCE-BRIEF.*                  # original design, preserved after bootstrap
.gitignore                      # merge with the host project's existing file
│
.gtt/                           # GTT ENGINE — machinery, derived state, GTT's own documentation
├── README.md                   # project-facing operational README
├── scaffold/manifest.yaml      # the canonical, declarative scaffold definition (layout version 2)
├── index/                      # artifact identity (artifacts.json) + derived technical index
├── protection/                 # GTTGuard registry.yaml — derived, never hand-edited
├── session-adapters/           # per-ADE Session Memory declarations (data only)
├── docs/                       # GTT's own documentation
│   ├── index.md                # map of every file — start here
│   ├── installation.md         # detailed setup procedures (+ installation.es.md)
│   ├── usage.md                # the normal development loop (+ usage.es.md)
│   ├── method-plans.md         # Light / Medium / Hard / Team in plain words (+ method-plans.es.md)
│   ├── gtt-completion.md       # durable bootstrap completion record
│   ├── evidence.md
│   ├── docs.md                 # methodology, portability, migration
│   └── session-adapter-contract.md
└── scripts/
    ├── gtt-check-stack.sh       # CI gate
    ├── gtt-check-adapter.sh     # validates the installed adapter matches the matrix
    ├── gtt-check-backlog.sh     # validates gtt-domain/backlog.md structural integrity
    ├── gtt-check-protection.sh  # validates the GTTGuard registry
    ├── gtt-guard-sync.sh        # regenerates the GTTGuard registry from source markers
    └── gtt_guard.py             # shared GTTGuard engine (detection, resolution, registry)
│
gtt-domain/                     # THE DOMAIN GOVERNED BY GTT-METHOD
├── context/                    # L0 — governed context
│   ├── stack.md                # the seven-view architecture map
│   ├── architecture.md
│   ├── solution-vision.md
│   ├── principles.md
│   ├── constraints.md          # always-in-context constraints
│   └── glossary.md
├── adr/                        # L1 — accepted decisions
├── proposals/                  # governed drafts awaiting a human decision
├── backlog.md                  # development line — Epics, Stories, current focus
├── change-request.md           # front door for change intent
├── session.md                  # derived operational state — never authority
└── .frozen                     # freeze marker, written by gtt-freeze.sh
│

# below: the catalog of adapters this source ships — an installed project
# gets the ones its participating ADEs need, chosen at bootstrap time (see ADE adapters)
│
.claude/                        # Claude Code adapter
├── CLAUDE.md
├── settings.json
├── hooks/protect-l0.py
├── hooks/protect-guard.py      # GTTGuard real-time block
├── rules/
└── skills/
    ├── gtt-bootstrap
    ├── gtt-propose-change
    ├── gtt-adr
    ├── gtt-audit
    └── gtt-guard
│
.kiro/steering/                 # Kiro adapter
│
.copilot/copilot-instructions.md # GitHub Copilot adapter
```

### Why some files stay at the root

`.claude/`, `.kiro/`, and `.copilot/copilot-instructions.md` remain at the root because these tools discover their configuration at fixed locations. Moving them into `.gtt/` can make the tools silently stop loading the intended rules and skills. Only the one matching your resolved adapter is actually installed — see [ADE adapters](#ade-adapters).

`AGENTS.md` remains at the root because Kiro, Codex, and Copilot read it by convention.

`readme-gtt.md`/`.es.md` remain at the root because they are the human-facing entry points — the first thing anyone opening the project should be able to find, not something buried under `.gtt/docs/`.

`SOURCE-BRIEF.*` remains at the root for the same reason: it is the Solution Designer's own original design, in their own words, and should stay as discoverable as the READMEs.

The governed domain sits in `gtt-domain/`, apart from the Engine, because it is the project's own governed state, not GTT machinery — see [Workspace hygiene](#workspace-hygiene). The Engine and GTT's own documentation stay in `.gtt/`.

---

## Context layers

| Layer | Contents | Policy | Loads |
| --- | --- | --- | --- |
| L0 | `gtt-domain/context/` | Propose only | On demand, except `constraints.md` |
| L1 | `gtt-domain/adr/` | Propose with review | On demand |
| L2 | `.gtt/docs/` | Editable with review | Never automatically |
| L3 | `src/`, `tests/`, pipelines, IaC | Editable | As required |

---

## Getting started

1. Copy the portable core — `AGENTS.md`, `readme-gtt.md`, `readme-gtt.es.md`, `.gtt/` (the Engine, including `.gtt/scripts/`, `.gtt/docs/` and `.gtt/scaffold/manifest.yaml`), and the governed-domain skeleton (`gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/proposals/`, `gtt-domain/backlog.md`, `gtt-domain/change-request.md`) — into the project root, plus only the adapter matching your ADE: `.claude/` (including `.claude/CLAUDE.md`) for Claude Code, `.kiro/` for Kiro, `.copilot/copilot-instructions.md` for GitHub Copilot, or nothing extra for Codex. See [ADE adapters](#ade-adapters); do not copy the other adapters in "just in case."
2. Merge the kit's `.gitignore` into your existing `.gitignore`; do not overwrite an existing project file.
3. Run the `gtt-bootstrap` skill (for example, “bootstrap GTT” or “set up GTT”) instead of filling `gtt-domain/context/` by hand — it performs step 1 above for you, deterministically.
4. If you prefer to author the context manually, start with `gtt-domain/context/stack.md`. Leave a cell empty rather than guessing; an explicit unknown is preferable to an invented decision.
5. Adjust the `paths:` globs in `.claude/rules/` to match the host project's folder layout (Claude Code only).
6. Wire `.gtt/scripts/gtt-check-stack.sh`, `.gtt/scripts/gtt-check-backlog.sh`, and `.gtt/scripts/gtt-check-protection.sh` into CI against the default branch.
7. Run a session and inspect `/context`. Only the expected core rules and constraints should be loaded automatically.
8. Verify the guardrail: ask the agent to edit a protected context file such as `gtt-domain/context/stack.md`. The write must be blocked by the applicable enforcement layer, not merely discouraged.
9. Verify the adapters: `.gtt/scripts/gtt-check-adapter.sh` confirms every participating ADE has an intact integration (against `.gtt/ade.json`).
10. Review the completed context and run `.gtt/scripts/gtt-freeze.sh` to ratify it.

### Upgrading to the two-regime model

If you are upgrading a project bootstrapped before the two-regime model existed, run:

```bash
./.gtt/scripts/gtt-freeze.sh
```

immediately after the upgrade when `gtt-domain/context/` already contains real content. Until the freeze marker exists, that context may remain agent-writable.

Full file map: [`.gtt/docs/index.md`](.gtt/docs/index.md) · Migration guidance: [`.gtt/docs/docs.md#migrating-from-gtt-v1`](.gtt/docs/docs.md#migrating-from-gtt-v1)

---

## Tool support

| Capability | Claude Code | Kiro | Codex | GitHub Copilot |
| --- | --- | --- | --- | --- |
| Portable core rules | via import | native | native | native (`AGENTS.md`) + `.github/copilot-instructions.md` pointer |
| Conditional loading | `paths:` | `inclusion: fileMatch` | nested `AGENTS.md` | none — repo-wide only |
| On-demand procedures | Skills | `inclusion: manual` | prompt | prompt |
| Deterministic write block | yes | `permissions.yaml` (1.0+) | config globs | no — CI gate only |
| Governed context + CI gate | yes | yes | yes | yes |
| GTTGuard real-time block | yes — `protect-guard.py` | no — CI gate only | no — CI gate only | no — CI gate only |

Claude Code supports the complete adapter set. Kiro's `permissions.yaml` covers unconditional machinery paths declaratively; regime-conditional paths rely on the shared hook plus CI gate where needed. Codex keeps the write protection model but has fewer fine-grained conditional-loading controls. GitHub Copilot reads repository-wide instructions from `.github/copilot-instructions.md` and agent instructions from `AGENTS.md`, per current GitHub documentation — note that GTT's adapter file lives at `.copilot/copilot-instructions.md` instead, so it is not picked up automatically at Copilot's real path; see the note above. It gets no path-scoped loading and no deterministic write block beyond the CI gate — the Copilot adapter is intentionally thin and does not claim capabilities GTT has not actually implemented for it.

Details and portability notes: [`.gtt/docs/docs.md`](.gtt/docs/docs.md#portability-claude-code-kiro-codex-copilot-cursor-openhands-antigravity)

### Switching ADE later

Bootstrap installs only the adapters of the ADEs you chose — see
[ADE adapters](#ade-adapters). There is nothing to prune on day one. Adding,
removing or re-prioritising an ADE later is done through `gtt-ade.sh`, never by
deleting directories by hand: it knows exactly which files GTT installed
(`.gtt/ade.json` keeps a ledger with hashes) and leaves your own ADE configuration
alone. Every command is a dry run until `--apply`:

```bash
# Add Copilot alongside the ADEs you already use
bash .gtt/scripts/gtt-ade.sh install --from <bootstrap catalog> --participating claude,copilot --primary claude
# Make another participating ADE the Primary (a workflow identifier; no authority moves)
bash .gtt/scripts/gtt-ade.sh set-primary copilot --apply
# Stop using Kiro: removes only the files GTT installed for it, keeps your own
bash .gtt/scripts/gtt-ade.sh remove kiro --apply
# Update every participating overlay after a Bootstrap update (local edits are never overwritten)
bash .gtt/scripts/gtt-ade.sh update --from <new bootstrap catalog> --apply
```

For a project installed before multi-ADE support, run `gtt-ade.sh adopt` once to record
the existing ADE; nothing else changes.

**Never delete `AGENTS.md`.** It contains the portable core rules. Claude Code imports it; Kiro, Codex, and Copilot read it natively.

Deleting `.claude/` removes its local enforcement layer. On Kiro, `permissions.yaml` provides unconditional protection where supported; regime-conditional paths may rely on the shared hook and CI gate. On Codex or Copilot, use nested `AGENTS.md` files when you need scoped rules:

```text
AGENTS.md
src/AGENTS.md
infra/AGENTS.md
```

---

## What you maintain

- `gtt-domain/context/` and `gtt-domain/adr/`: applied through the governed process and not directly written by an agent once frozen.
- `gtt-domain/backlog.md`: Epics/Stories change through `gtt-domain/change-request.md` like an architectural decision; status and focus updates during routine implementation are direct edits.
- `gtt-domain/change-request.md`: your entry point whenever a governed decision or the committed development line needs to change.
- `SOURCE-BRIEF.*`: written once during bootstrap and preserved as the original source, at the project root.
- Your participating ADEs' adapters (`.claude/`, `.kiro/`, `.copilot/copilot-instructions.md`), `.gtt/ade.json` (written only by `gtt-ade.sh`) and `.gtt/scripts/`: GTT runtime/integration assets that normally require little change beyond path configuration.
- `.gtt/protection/registry.yaml`: never hand-maintained — it is regenerated from `@GTTGuard` markers in source by `.gtt/scripts/gtt-guard-sync.sh`. Your part is placing/removing the marker; the registry follows.

---

## Requirements

Claude Code, Kiro, Codex, or GitHub Copilot.

The protection hook (Claude Code) needs `python3`, present by default on Linux and macOS. The CI gate needs `git` and `bash`.

---

## Evolution

GTT is an evolving methodology focused on the governance of context in AI-assisted development. Future work may extend it across software solutions, cloud and infrastructure, agentic systems, documentation, and knowledge governance — while preserving the core principle:

> **Context is the Source of Truth.**

Related: [GTT Framework](https://github.com/mgriott/context-driven-ai-development) — methodology, whitepapers, principles, and governance model.

Community: [GTT Community (ES)](https://gtt-community.github.io/es/) · [gtt-docs](https://github.com/GTT-Community/gtt-docs)

---

## License

Creative Commons Attribution 4.0 International (CC BY 4.0).

You are free to share, adapt, and build upon this work, including commercially, provided appropriate attribution is given.

**Attribution:** Copyright © 2026 Moisés Griott. Maintained by **GTT Community**.

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

---

**GTT Community** · Governance Throw Think
