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
| Grounding | Retrieves and exposes governed evidence faithfully | Decide architecture | `gtt-bootstrap`, `gtt-audit` reading `gtt/context/`, `gtt/adr/`, `gtt/backlog.md` |
| Reasoning | Analyzes evidence, drafts proposals/ADRs | Authorize its own draft | `gtt-propose-change`, `gtt-adr`, `gtt-drift-response` |
| Validation | Runs deterministic structural checks | Make an architectural judgment | `gtt/scripts/gtt-check-*.sh`, `gtt-validate.sh` |

The chain is: Sources → Grounding → Evidence Dossier (governed context as
read) → Reasoning → Proposal → Human Decision → Freeze. A reasoning step
must never receive raw sources "for context" in a way that bypasses
grounding — read `gtt/docs/DOCS.md` → *Governance model* for the full
rationale. Producing output, of any kind, never grants an agent decision
authority.

## Before changing anything

1. Read `README-GTT.md`.
2. Inspect the host project.
3. Identify existing files with GTT-required names.
4. Identify design/source documents at the project root.
5. If there is no source document, continue through conversation.
6. If multiple candidate source documents exist, ask the user. Never guess.
7. Never silently overwrite an existing file.

## Required workspace

The GTT bootstrap contract is:

```text
/
├── AGENTS.md
├── README-GTT.md
├── README-GTT.es.md
├── SOURCE-BRIEF.*                # if a source document existed
└── gtt/
    ├── README.md
    ├── INDEX.md
    ├── CHANGE-REQUEST.md
    ├── GTT-COMPLETION.md
    ├── backlog.md
    ├── INSTALLATION.md
    ├── INSTALLATION.es.md
    ├── USAGE.md
    ├── USAGE.es.md
    ├── adr/
    ├── context/
    ├── docs/
    ├── proposals/
    ├── protection/
    └── scripts/
```

Tool-specific integration directories remain at their required locations.
Workspace hygiene: the project root stays the user's — only ADE
discovery/integration files, the two GTT READMEs, `AGENTS.md`, and
`SOURCE-BRIEF.*` belong there. Everything else GTT owns lives under
`gtt/`. See *Workspace hygiene* in `README-GTT.md` for the full principle.

## Backlog governance

`gtt/backlog.md` is the development line: Epics, Stories, and the work
currently expected to be built. It is a development-planning artifact, not
architecture — never a second source of truth beside `gtt/context/`.

**Precedence:** Governed Context / L0 → ADR → this backlog → implementation.
A Story that contradicts governed context or an accepted ADR is a finding,
not a resolution — surface it through `gtt/CHANGE-REQUEST.md`; never let a
Story silently override architecture.

**What goes through `gtt/CHANGE-REQUEST.md` → `gtt/proposals/` → decision:**
adding or removing an Epic or Story, or materially changing its scope or
acceptance criteria — the same funnel as an architectural change.

**What does not:** updating a Story's status, or the *Current Focus* /
*Next Work* / *Blocked* lists, as part of already-approved implementation
work. Routine progress tracking is not a governed decision; do not force it
through the change-request flow, and do not use it as a backdoor to add or
remove Epics/Stories either — that distinction requires judgment, not a
loophole.

**Before development work, establish the applicable Epic/Story from
`gtt/backlog.md`.** If defined Epics/Stories exist elsewhere (a requirements
doc, an issue tracker, prior conversation) but are missing from the
backlog, reconcile them through the normal change process — do not
silently ignore them and do not silently rewrite the backlog to match.
Report the gap and offer the `gtt-propose-change` skill. If no Epics or
Stories are defined at all, say so explicitly and ask whether the
development line should be defined, or proceed only where the requested
work is genuinely independent of one. Never invent business Epics/Stories
and present them as user-defined requirements — proposed ones must stay
labeled `Status: Proposed` until accepted.

Structural integrity (unique IDs, valid status values) is checked
deterministically by `gtt/scripts/gtt-check-backlog.sh`; whether an
Epic/Story is real, current, and correctly linked to actual work is a
judgment call for the `gtt-audit` skill.

## Protected artifacts (GTTGuard)

GTTGuard is a lightweight, language-agnostic mechanism for marking a file,
class, or method so an AI coding agent may read, analyze, and propose a
change to it, but may never modify it autonomously. It is a **sibling** to
L0/L1 governance, not a restatement of it: it protects arbitrary L3 code
the developer opts into protecting, never `gtt/context/` or `gtt/adr/`, and
it must never be conflated with the Human Promotion Boundary below — the
two are deliberately different weights of ceremony for different things.

**Core rule:** User proposes the protection → GTT implements it → Agent
respects it.

A developer marks a declaration with `@GTTGuard` (Java, Python), `[GTTGuard]`
(C#), or a `// @GTTGuard` / `# @GTTGuard` comment (other languages),
optionally with `reason=`/`source=`. `gtt/scripts/gtt-guard-sync.sh`
detects every marker, resolves the file/class/method it protects
deterministically (never by LLM judgment), and regenerates
`gtt/protection/registry.yaml` — a **derived artifact**, like a lockfile:
never hand-edit it, since `gtt/scripts/gtt-check-protection.sh` fails the
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
already documented for the two-regime `gtt/context/`/`gtt/adr/` condition —
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

Run `gtt/scripts/gtt-status.sh` to regenerate `gtt/SESSION.md`: a
deterministic snapshot (freeze state, backlog focus, pending proposals,
protected-artifact count, installed adapter) derived from repository
artifacts, never from any ADE's private conversation memory — the same
project resumes the same way whether the next session is Claude Code,
Codex, Kiro, or Copilot. Treat it as operational context only: never
architectural authority, never evidence, never a substitute for an ADR or
decision record. An agent must never invent this state from memory instead
of running the script.

If working preferences for this project are ever introduced, keep them in
an artifact separate from session state — they are not Canon, architecture,
evidence, or decisions, sit below governed context/constraints in
precedence, must never silently override them, and no agent may author its
own preferences.

## Validation

`gtt/scripts/gtt-validate.sh` runs every deterministic check script
(`gtt-check-backlog.sh`, `gtt-check-adapter.sh`, `gtt-check-protection.sh`,
`gtt-check-stack.sh`) and reports pass/fail/cannot-determine.
`gtt/scripts/gtt-status.sh` reports what is current, governed, pending,
proposed, blocked, and frozen. Both are read-only and deterministic;
neither substitutes for a human architectural judgment.

## Adapters vs. portable core

GTT ships a portable core — this file, `README-GTT.md`, `README-GTT.es.md`,
and `SOURCE-BRIEF.*` (if a source document existed) at the project root, plus
`gtt/` itself (carrying `INDEX.md`, `CHANGE-REQUEST.md`, `GTT-COMPLETION.md`,
`backlog.md`, `INSTALLATION.md`/`.es.md`, `USAGE.md`/`.es.md`, `context/`,
`adr/`, `proposals/`, `docs/`, `scripts/`) — plus
one adapter per supported ADE: Claude Code → `.claude/`, Kiro → `.kiro/`,
Codex → `AGENTS.md` alone, GitHub Copilot → `.copilot/copilot-instructions.md`.
The GTT Bootstrap source carries every adapter as a catalog; a target
project receives the portable core plus exactly the one adapter matching the
ADE that is executing the bootstrap — never the whole catalog, never more
than one native adapter.

Base the choice on the ADE actually executing the bootstrap, never on the
underlying model (a Claude model is not Claude Code; a GPT model is not
Codex) and never by guessing from adapter files that merely happen to exist
in the target repo. If the executing ADE cannot be established with
confidence, ask — do not guess. Full resolution table and procedure: the
`gtt-bootstrap` skill.

## Bootstrap behavior

During initial bootstrap:

1. Detect the ADE executing the bootstrap and resolve exactly one adapter for
   it (see *Adapters vs. portable core*) before touching the filesystem.
2. Obtain or confirm the design/source document.
3. Verify that it is complete enough to serve as a source.
4. Inspect `gtt/context/` for placeholders.
5. Map the source into the six governed context files.
6. Ask for missing information rather than inventing decisions.
7. Summarize the resulting context.
8. Obtain explicit human confirmation.
9. Write the confirmed context.
10. Preserve the source as `SOURCE-BRIEF.*`.
11. Ask the user to review.
12. Freeze only after explicit confirmation.

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
- `README-GTT.md`
- `README-GTT.es.md`
- `SOURCE-BRIEF.*`
- `gtt/` (including `INDEX.md`, `CHANGE-REQUEST.md`, `GTT-COMPLETION.md`, `backlog.md` inside it)
- `.claude/`
- `.kiro/`
- `.copilot/copilot-instructions.md`

inspect before changing.

Report conflicts explicitly.

Do not silently overwrite.

Preserve the host project's existing source structure.

## Governed regime

Before:

```text
gtt/.frozen
```

the bootstrap procedure may populate `gtt/context/`.

After:

```text
gtt/.frozen
```

do not directly modify governed context.

Architectural changes must go through:

```text
gtt/CHANGE-REQUEST.md
        ↓
gtt/proposals/               (proposal, then ADR draft + promotion script)
        ↓
Human Promotion Boundary      (review, then explicit human execution)
        ↓
gtt/adr/
        ↓
gtt/context/stack.md
```

## Change requests

Routine implementation does not require a change request.

Use `gtt/CHANGE-REQUEST.md` when a requested change affects a governed decision.

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
full/fast track) is approved, the agent's job is not to edit `gtt/adr/` or
`gtt/context/` — those stay write-protected regardless. Instead it stages a
**promotion package** entirely under `gtt/proposals/`: the ADR draft, the
full text of every affected `gtt/context/` file, and an executable script —
`apply-ADR-NNN-<slug>.sh` — that applies all of them together.

The script is a first-class GTT artifact, not a convenience wrapper:

- lives in `gtt/proposals/`, the one directory the agent may always write to;
- opens with a header naming the proposal and ADR and stating that human
  execution is required;
- lets the human view the ADR text and the exact diff against current context
  before deciding, and asks for an explicit confirmation before writing
  anything — not a single blind `[yes/no]`;
- applies every file the approved change touches in one run, and stops with a
  clear error rather than continuing after a partial failure;
- is never executed by the agent, under any circumstance — the human runs it
  from the project root: `bash gtt/proposals/apply-ADR-NNN-<slug>.sh`.

After generating it, the agent must plainly tell the user: that a promotion
script was generated and exactly where it is, what it will change, that they
must review the proposal, ADR, and script before running it, the one-line
command to run it, that execution is their decision, and that the agent has
not promoted the change automatically. Generating a proposal, an ADR draft, or
a promotion script is never itself approval — each governed promotion needs
its own explicit human decision, and approving one change does not carry over
to the next.

For changes that do not touch governed context — a development-line change
applied straight to `gtt/backlog.md` (see *Backlog governance*) — this
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
`gtt/GTT-COMPLETION.md` — that file is the durable record; chat output
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

Detected ADE:
- ...

Adapter installed:
- ...

Adapters excluded:
- ...

Native support:
- yes / no — ...

Backlog:
- defined / not yet defined — reconciled: yes / no / not applicable

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
- Never install an adapter for an ADE other than the one executing the bootstrap.
- Never infer the executing ADE from the underlying model or from adapter files that merely happen to exist; ask if it cannot be established with confidence.
- Never invent Epics or Stories and present them as user-defined requirements.
- Never let a Story in `gtt/backlog.md` silently override governed context or an accepted ADR.
- Never add or remove an Epic/Story, or materially change one, outside the `gtt/CHANGE-REQUEST.md` flow.
- Never generate `INDEX.md`, `CHANGE-REQUEST.md`, `GTT-COMPLETION.md`, or `backlog.md` at the project root and move them into `gtt/` afterward — write them under `gtt/` directly.
- Never bypass a GTTGuard-protected artifact's approval requirement — not by renaming or removing its marker without authorization, not by editing around the enforcing hook, and not by hand-editing `gtt/protection/registry.yaml`.
- Never treat approval of one GTTGuard proposal as authorization for a different protected artifact, and never confuse its lightweight, in-conversation promotion with the L0/L1 Human Promotion Boundary.

### Bootstrap documentation vs. installed project layout

The GTT Bootstrap repository and an installed GTT workspace have different documentation locations.

In the **GTT Bootstrap repository**, the canonical entry points remain at the repository root:

- `README-GTT.md`
- `README-GTT.es.md`
- `AGENTS.md`

`INSTALLATION.md`, `INSTALLATION.es.md`, `USAGE.md`, and `USAGE.es.md` live
under `gtt/` — indexed from `gtt/INDEX.md` and linked from the two
READMEs above — the same as in any host project this repository bootstraps.

When an agent installs/bootstraps GTT into a **host project**, it MUST organize the installed GTT workspace as follows:

```text
/
├── AGENTS.md
├── README-GTT.md
├── README-GTT.es.md
├── SOURCE-BRIEF.*                # if a source document existed
└── gtt/
    ├── README.md
    ├── INDEX.md
    ├── CHANGE-REQUEST.md
    ├── GTT-COMPLETION.md
    ├── backlog.md
    ├── INSTALLATION.md
    ├── INSTALLATION.es.md
    ├── USAGE.md
    ├── USAGE.es.md
    ├── adr/
    ├── context/
    ├── docs/
    ├── proposals/
    ├── protection/
    └── scripts/
```

The project root belongs to the user's project; `gtt/` belongs to GTT
governance. Only ADE discovery/integration files, the two GTT READMEs,
`AGENTS.md`, and `SOURCE-BRIEF.*` earn a place at the root — every other
GTT-owned artifact is generated directly under `gtt/`, never written to
the root and moved afterward.

Install only the adapter matching the ADE executing the bootstrap (see *Adapters vs. portable core*). Whichever one it is, it remains at the host-project root, never moved under `gtt/`:

```text
.claude/                         # Claude Code
.kiro/                           # Kiro
.copilot/copilot-instructions.md  # GitHub Copilot
```

Codex takes no adapter file beyond `AGENTS.md` itself. Do not install the adapters for ADEs other than the one executing the bootstrap, even if the GTT Bootstrap source contains them all.

`README-GTT.md` and `README-GTT.es.md` ARE installed at the host-project
root — they are the human-facing GTT entry points and must stay
discoverable there, not buried under `gtt/`. `INSTALLATION.md` and
`USAGE.md` (and their `.es.md` pairs) ARE also installed, under `gtt/`
alongside `INDEX.md`, `CHANGE-REQUEST.md`, `GTT-COMPLETION.md`, and
`backlog.md` — indexed from `gtt/INDEX.md` and linked from the two
READMEs at root.

The **project-facing GTT README MUST be installed as**:

```text
gtt/README.md
```

`gtt/README.md` is the operational README for GTT as installed in that project. It should explain the installed GTT workspace and its operation; it is not a reason to dump the bootstrap repository's documentation into the host project's root.

The agent MUST:

1. Clone/download the GTT Bootstrap repository into a temporary/work location.
2. Read the bootstrap `AGENTS.md` and canonical `README-GTT.md` before installing.
3. Preserve the host project's existing structure and files.
4. Detect the ADE executing the bootstrap and resolve exactly one adapter for it; if it cannot be established with confidence, ask rather than guess.
5. Install the portable core plus only the resolved adapter, and explicitly exclude the others — the source repository is a catalog, not a package to install whole.
6. Create/organize the GTT scaffold under `gtt/` as defined above.
7. Keep `AGENTS.md`, `README-GTT.md`, and `README-GTT.es.md` at the host-project root.
8. Write `INDEX.md`, `CHANGE-REQUEST.md`, `GTT-COMPLETION.md`, and `backlog.md` directly under `gtt/` — never at the project root, and never generated at the root then moved.
9. Install the project-facing README at `gtt/README.md`, and keep the other GTT-owned `adr/`, `context/`, `docs/`, `proposals/`, `protection/`, and `scripts/` under `gtt/`.
10. Preserve the original design/source brief (`SOURCE-BRIEF.*`) in the host project according to the GTT bootstrap procedure.
11. Never move, rename, duplicate, redistribute, or silently overwrite an existing host-project file.
12. If a target file already exists, stop and report the conflict rather than silently replacing it.
13. Do not automatically freeze the project. `gtt/scripts/gtt-freeze.sh` is run after human review/confirmation.
14. On re-run, never reintroduce an adapter that a prior bootstrap explicitly excluded, and never overwrite an existing adapter outside the normal conflict-reporting rule above.

The bootstrap documentation stays at the root **of the bootstrap repository**. The installed operational documentation and GTT-owned artifacts go under `gtt/` **inside the host project**.
