# Bootstrapping GTT into a project

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Part of the agent contract. `AGENTS.md` points here, and what this file says binds exactly as if it
were written there. A section named in *italics* that is not in this file is a section of
`AGENTS.md` or of another file in this directory.

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
│   ├── governance-backlog.json   #   observations and the human decisions on them (gtt-observe.sh)
│   └── .frozen                   #   freeze marker and governance baseline, written by gtt-freeze.sh
│
└── .claude/ | .kiro/ | .github/instructions/ | .cursor/rules/ | .agents/skills/gtt/ | .agents/rules/
                                  # ADE OVERLAYS - one per participating ADE; exactly one ADE is Primary
```

The scaffold has two homes and its ADE overlays, and the layout keeps them apart:

| Part | Where | Contents |
|---|---|---|
| GTT Engine | `.gtt/` | scripts, artifact identity and technical index, protection registry, session-adapter declarations, the scaffold manifest, and GTT's own documentation (`.gtt/docs/`) |
| Governed domain | `gtt-domain/` | `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen` |
| ADE Overlay | `.claude/`, `.kiro/`, `.github/instructions/`, and GTT's own files under `.cursor/`, `.agents/` and `.openhands/` | the integration of every participating ADE (one Primary; see *Multi-ADE participation*) |

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
│   ├── governance-backlog.json   #   observations and the human decisions on them (gtt-observe.sh)
│   └── .frozen                   #   freeze marker and governance baseline, written by gtt-freeze.sh
│
└── .claude/ | .kiro/ | .github/instructions/ | .cursor/rules/ | .agents/skills/gtt/ | .agents/rules/
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
.github/instructions/gtt.instructions.md  # GitHub Copilot
.cursor/rules/gtt*.mdc            # Cursor (two rule files; the rest of .cursor/ is the host's)
.cursor/hooks.json                # Cursor (write block + session context, unverified in the ADE)
.agents/skills/gtt/SKILL.md       # OpenHands (one skill; AGENTS.md is its entry point)
.openhands/hooks.json             # OpenHands (write block + session context, unverified in the ADE)
.agents/rules/gtt*.md             # Antigravity (two rule files; the rest of .agents/ is the host's or another ADE's)
.agents/hooks.json                # Antigravity (write block, unverified in the ADE)
```

Codex takes no adapter file beyond `AGENTS.md` itself. OpenHands reads `AGENTS.md` as its
always-on entry point and takes one repository skill beyond it. Antigravity reads `AGENTS.md` and takes two workspace rules and a hooks file beyond it. Do not install the adapters for ADEs the human did not choose, even if the GTT Bootstrap source contains them all.

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

Register every source before reading it for the design: `bash .gtt/scripts/gtt-source.sh add <file> --id <ID> --apply`
copies it to `docs/sources/<ID>/v1/` and records its hash (`adopt <path> --id <ID>` registers one where it is,
such as `SOURCE-BRIEF.*`). The completed Initial Design Questionnaire is a source too: add it as `IDQ` and cite
its answers (`[FUENTE: IDQ:§git-workflow]`). A source is never edited afterwards.

After the six context files are populated, write the design of every `Proposed` Epic in scope:
`bash .gtt/scripts/gtt-design.sh scaffold EPIC-NNN --apply` creates the draft; list under *Source sections* every
section of the sources that belongs to the Epic and carry its content over in full, a `[FUENTE]` on each line.
What the sources do not define is a `[VACÍO]`: ask the human under `@gtt · Design EPIC-NNN`, at most five
questions a turn, grouped by Epic, with options where the source suggests them; each answer goes to section 8 as
`D-n` and closes its `[VACÍO]`. The design is complete in every Method Plan and at every THINK Depth: the depth
changes how much is analysed, never which sections exist. The human approves the Epic and its design together
(`bash .gtt/scripts/gtt-approve.sh EPIC-NNN`); you never do.

While reading the sources, run `bash .gtt/scripts/gtt-workflow.sh detect`. If the project's own
documents mention a commit convention, it prints one `@gtt · Finding` line: pass it on as it is.
Never adopt the convention and never write `gtt-domain/workflow.md` - the human does, with the
line the finding names.

While mapping the source (step 5), draft the `gtt-boundaries` rules of
`gtt-domain/context/stack.md`: the few places where a change in the code would mean the design
itself changed - a deployment path, an API contract, the dependency manifests, a dependency
direction the architecture forbids. Each rule points at the decision behind it, the human
confirms them with the rest of the context (Confirmation B), and `BLOCKING` is the exception,
never the default: propose it only where the source itself prohibits something.

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

## Two confirmations

Do not collapse these into one:

### Confirmation A — source/design

Is the user's design document complete and ready to be used?

### Confirmation B — governed context

Do the generated six context files accurately represent the user's intended solution?

Both confirmations matter.

## Source preservation

`SOURCE-BRIEF.*` is the original source used to bootstrap the governed context.

Do not silently rewrite it after bootstrap.

If the user wants the source design changed, treat that as an explicit design change and report the consequences for governed context.

## Completion report

After bootstrap, report in chat **and** append this same report to
`.gtt/docs/gtt-completion.md` — that file is the durable record; chat output
alone is lost once the session ends. Append, do not overwrite, on a later
re-run (ADE/adapter switch, migration, re-freeze). The file gets the whole
report; the chat gets at most six lines - what was created, what is pending,
what the human must do - and the pointer to the file.

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
- Epics awaiting approval: <ids, or "none">

Boundaries:
- declared: <count> (BLOCKING: <count>) / none - observation watches only the built-in boundaries

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
