---
name: gtt-bootstrap
description: Detect candidate ADEs, install the GTT overlays of the ADEs the human chooses to participate (exactly one Primary), then populate gtt-domain/context/ for the first time in a new project. Use when the user says to set up GTT, bootstrap GTT, initialize GTT, or has just cloned GTT Bootstrap into a project and gtt-domain/context/ still holds template placeholders. Checks the project root for an existing solution document (offering the Bootstrap's Initial Design Questionnaire when there is none), assesses an existing design in writing and strengthens it when it is poor - a decided technology stack is the minimum - resolves several design documents into one or keeps them as declared sources, confirms with the Solution Designer that it is finished rather than a draft, asks for whatever it does not answer, and drafts the six context files plus a permanent SOURCE-BRIEF at the project root for review before anything is written.
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Bootstrap the governed context

> **Speaking for GTT.** Every message this skill raises to the human — a
> question, a confirmation, a proposal, a finding, a request for
> authorization, a report — opens with `@gtt · <what this is>`
> (e.g. `@gtt · Method Plan`). The marker says who is speaking; it is never a decision.

`gtt-domain/context/` ships as a template — angle-bracket placeholders and empty
table rows, not real answers. This skill turns those placeholders into the
project's actual context, confirmed by the Solution Designer before anything
is written.

## 0. Detect candidate ADEs, let the human choose, and resolve the overlays

Do this before touching the filesystem, and before step 1. Three separate
questions: which ADEs look present (detection), which ones the human wants GTT
to govern (participation), and which one is the Primary.

GTT Bootstrap ships a portable core — `AGENTS.md` and `SOURCE-BRIEF.*` (if a
source document exists) at the project root, plus the governed domain
(`gtt-domain/`: `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`) and
the Engine (`.gtt/`, including its documentation in `.gtt/docs/`, defined by
`.gtt/scaffold/manifest.yaml`) — plus one adapter per
supported ADE. The source repository carries every adapter — it is a
catalog, not a package to install whole. A target project receives the
portable core plus the overlay of every ADE the human chose to have
participate, never the whole catalog. Workspace hygiene: the Engine and its
documentation stay in `.gtt/`, and the governed domain in `gtt-domain/`;
never mix them, and report (never merge) a collision with a `.gtt/` or
`gtt-domain/` the project already has.

What each ADE's adapter contains (a project with several participating ADEs
has the union of their rows; the registry itself is the `overlays:` section of
the manifest, read through `gtt-ade.sh list`):

| Host ADE | Adapter | `.claude/` | `.kiro/` | `AGENTS.md` | `.copilot/copilot-instructions.md` |
|---|---|---|---|---|---|
| Claude Code | Claude | YES | NO | YES | NO |
| Kiro | Kiro | NO | YES | YES | NO |
| Codex | Portable/AGENTS | NO | NO | YES | NO |
| GitHub Copilot | Copilot | NO | NO | YES | YES |
| Other supported ADE | Explicit adapter only | only if mapped | only if mapped | per support | per support |
| Unknown ADE | Portable/unknown | NO | NO | do not guess | NO |

**Detection is not participation.** From the project root, run
`bash <catalog>/.gtt/scripts/gtt-ade.sh detect --from <catalog>`. It lists every ADE in the
registry with the signals it found (an overlay path, an ADE binary on the PATH). Those
are *candidates* — nothing more: not installed, not authorized, not governed, not
participating. Never detect from the underlying model: a Claude model is not Claude Code,
a GPT model is not Codex, and an API alone is neither. The ADE executing this bootstrap
is self-evident to that ADE and is a sensible suggestion — still only a suggestion.

**Ask, do not assume.** Show the candidates (and the registry ADEs that were not
detected: the human may want one that is not installed yet) in this shape:

> Detected these possible ADEs.
>
> - Claude Code (signals: `.claude/`, binary `claude`)
> - Kiro (signals: `.kiro/`)
>
> Which of them should participate in this project? GTT installs and governs each
> one's integration. And which one is the Primary ADE — the principal environment of
> your workflow? (The Primary ADE has no extra authority.)

Silence is not an answer. Exactly one Primary, and it must be one of the participating
ADEs. If the human names no ADE, or the only ADE has no row above and none has been
explicitly mapped for it, install the portable core only, do not invent an adapter,
and report plainly that no native adapter exists (it falls back to `AGENTS.md` where it
can read that natively).

**The Primary ADE holds no authority.** It identifies the principal environment of the
workflow and nothing else. It does not outrank, approve or arbitrate for another ADE, and
no ADE — the Primary included — ratifies anything: every ADE prepares, the human decides.
Do not describe or behave as if there were an ADE hierarchy. `AGENTS.md`, `.claude/`,
`.kiro/`, `.copilot/`, `.codex/` and any ADE's memory or session history are integration
surfaces, never governance authority. Several ADEs may run at once (three terminals in one
editor), which is why every participating ADE gets its overlay.

**Install.** Once the portable core and the Engine are in place, with the choice made,
dry-run first, show the plan (a CONFLICT means an overlay file already exists — it is never
overwritten or merged; stop and report it), then apply:

```bash
bash <catalog>/.gtt/scripts/gtt-ade.sh install --from <catalog> --participating claude,codex --primary claude
bash <catalog>/.gtt/scripts/gtt-ade.sh install --from <catalog> --participating claude,codex --primary claude --apply
```

That copies only the participating overlays, writes `.gtt/ade.json` (participating, Primary,
the ADEs declined as excluded, and a ledger of the files it installed so a later clean removes
exactly those and never the host project's own ADE configuration), and validates the result,
rolling everything back on failure. Do not copy overlay files by hand and never hand-edit
`.gtt/ade.json`. Only Claude Code has a real-time write block; say so for every other
participating ADE (governed by instructions plus the CI gate, not hard-blocked).

**Re-running bootstrap.** Read the state first (`gtt-ade.sh state`). If `.gtt/ade.json`
exists: never drop a participating ADE, never re-add one recorded as excluded unless the
human says so (`--reinclude <ade>`), never change the Primary unless the human says so
(`gtt-ade.sh set-primary`). A project that predates `.gtt/ade.json` (an overlay present, no
state) is migrated with `gtt-ade.sh adopt` (dry run first): it records the existing ADE as
both Primary and participating only when exactly one overlay is present and intact; where
several are present, ask the human and pass `--participating a,b --primary a`. Never infer
an authorization the state does not show.

Once resolved, note the detected ADEs, the participating ADEs, the Primary, the files this
will install, and the ADEs this will exclude — this becomes part of the report after
step 6. Then continue to step 1.

### Method Plan

Before step 1, establish the project's Method Plan. It is the human's choice.

1. Run `bash .gtt/scripts/gtt-project.sh profile get`. If it names a selected plan, state
   it and do not ask again. If it says `plan: not selected`, ask.
2. Show the four plans - Light, Medium, Hard, Team - each with the `label` and `summary`
   it carries in `.gtt/contract/profiles.json` (`bash .gtt/scripts/gtt-contract.sh show
   profiles`), in that order, as written. Do not paraphrase them into "basic" or
   "advanced": a plan is an operating profile, not a quality level.
3. Ask for that one choice only. Never ask the human to configure the derived policies
   (index, identity, validation, ADE sync) one by one, and never pick, default or
   recommend a plan on your own. If the human asks what the difference is, answer from
   `.gtt/docs/method-plans.md` - what each plan does without asking, what it asks, what
   it requires - including exactly what Light relaxes.
4. Record the answer: `bash .gtt/scripts/gtt-project.sh profile set --profile <id>` (dry
   run), then the same with `--apply`. If the human declines to choose now, leave it
   unselected, say that the Medium gates apply meanwhile as a fallback, and list the
   selection under *Human action required* in the report.
5. For the rest of the bootstrap, apply the selected plan's `semantics` (for example,
   Light may ask Confirmation A and B in one exchange; each still needs its own answer).
   No plan lets you skip a confirmation, write governed context unconfirmed, or freeze.

## 1. Establish the regime

Two independent questions. Cross them before doing anything.

| `gtt-domain/context/` has real content? | `gtt-domain/.frozen` exists? | Action |
|---|---|---|
| No | No | Normal case. Proceed to step 2. |
| No | Yes | Anomaly — freeze validates content before writing the marker, so this should be impossible. Stop. Report the inconsistency. Do not guess which side is right. |
| Yes | Yes | Normal governed state. Bootstrap does not apply. Offer `gtt-audit` instead. |
| Yes | No | **Migration case.** Say exactly: "gtt-domain/context/ is populated but gtt-domain/.frozen is absent. If this project was already governed before this version of GTT, run .gtt/scripts/gtt-freeze.sh now rather than treating this as a fresh bootstrap." Stop. Do not offer to overwrite it. |

"Real content" means not placeholders like `<layered / hexagonal / ...>` or
empty table rows.

**Earlier layouts.** Before proceeding, also check for artifacts left by an
earlier GTT layout:

- v2 layout: `INDEX.md`, `CHANGE-REQUEST.md`, `GTT-COMPLETION.md`, or
  `BACKLOG.md` sitting at the project root under those upper-case names.
- v2.1 layout before the scaffold restructure: governance nested under `gtt/` —
  `gtt/context/`, `gtt/adr/`, `gtt/proposals/`, `gtt/backlog.md`,
  `gtt/CHANGE-REQUEST.md`, `gtt/SESSION.md`, `gtt/.frozen`, or documentation
  directly under `gtt/` (`gtt/INDEX.md`, `gtt/INSTALLATION*.md`, ...).
- v2.1 layout after the scaffold restructure, before the move to `.gtt/` and `gtt-domain/`: the Engine in `gtt/` and governance and documentation at the project root (`context/`, `adr/`, `proposals/`, `docs/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen`).

If any are found:

- Do not silently create new copies at the current scaffold locations
  alongside them — that produces two canonical artifacts with the same
  meaning, which is worse than either problem alone.
- Do not silently move or delete the old files either.
- Stop and tell the Solution Designer plainly what was found and where, and
  ask whether to migrate them or leave the project on its current layout for
  now. Only move on explicit confirmation.
- If the project is frozen, relocating `gtt-domain/context/` or `gtt-domain/adr/` is a governed
  change: route it through `gtt-propose-change` and a promotion script, never
  a direct move.
- If they confirm an unfrozen migration, move each file's content verbatim (no
  rewriting) to its current scaffold path, remove the old copy, and report
  exactly what moved.

## 2. Look for an existing solution document

Look at the project root only — not subdirectories, not the rest of the repo.
Anything there that isn't part of the kit itself (`AGENTS.md`, `SOURCE-BRIEF.*`,
`readme-gtt.md`, `readme-gtt.es.md`, `.claude/`, `.kiro/`, `copilot/`, `.gtt/`,
`gtt-domain/`)
and isn't ordinary project scaffolding (`package.json`, `.gitignore`, a
pre-existing `README.md`, `LICENSE`, and the like) is a candidate solution
document. The
Solution Designer does not have to name it anything in particular or tell the
agent it exists — a `.md`, `.txt`, Word, or PDF file sitting there is enough.

- **Exactly one candidate:** confirm it in one line — "Using `<name>` as the
  source document?" — rather than assuming silently, then use it.
- **No candidate at the root:** ask directly whether a document exists
  elsewhere — another path, an external doc, or paste it into chat. If there is
  none at all, offer the Initial Design Questionnaire (below).
- **More than one candidate:** never guess between them, and never pick one by name, order or
  size. First ask whether all of them are design sources or only some. If only one is, use it.
  If several are, they must be resolved before design continues, and the Solution Designer
  chooses how — show both options and ask once:
  - **`CONSOLIDATE`** — you draft one design document from all of them at
    `gtt-domain/proposals/bootstrap/design-consolidated.md`: every statement carries the
    `[FUENTE: file:line]` it came from, and every disagreement stays visible as
    `[CONFLICTO: a vs b]` for the Solution Designer to resolve — you never pick a winner. Once
    reviewed, that document is the single source document. The originals are not modified.
  - **`KEEP_AS_SOURCES`** — each document stays as it is and is declared in
    `gtt-domain/context/sources.md` (template: `gtt-template.sh materialize source-manifest`)
    with an authority and an unambiguous precedence — never by reading order — and cited with
    `[FUENTE: id]`. All of them are context throughout the design work; precedence orders the
    reading and never erases a `[CONFLICTO]`.

  Either way, read all of them before the assessment below, and record the choice in its
  section 2.
- **A `SOURCE-BRIEF.*` already at the root:** this project was already
  bootstrapped. Stop and offer the `gtt-audit` skill instead (same as step 1).

Do not scan subdirectories or the rest of the repository speculatively looking
for "the" document — the root check above is the only place this skill looks
without being told, same as Claude Code checking a fixed location for
`AGENTS.md` instead of searching for it. Beyond that, ask.

Wherever it comes from, once it is processed a copy becomes `SOURCE-BRIEF.*` at
the project root (step 6) — permanent, not archived away into `.gtt/docs/` —
so the reasoning behind the context stays visible and traceable right at the
project root, the one GTT artifact a human should never have to go looking
for under `.gtt/`.

### Assess the design (a design document exists)

A document existing is not the same as a design being good enough to govern. Before
asking whether it is finished, read it — all of them, when there are several — and write
down how good it is. This is the first act of the Think stage, and it produces a document,
not a conversation.

1. Materialize the working copy: `bash .gtt/scripts/gtt-template.sh materialize design-assessment`
   (dry run), then `--apply`. It creates `gtt-domain/proposals/bootstrap/design-assessment.md`.
   Read its *Operating contract* and follow it.
   **Establish the THINK Depth before rating anything.** Ask once, showing the three levels
   as the template describes them — `QUICK` (simple or small designs: floor areas and
   critical gaps, a reduced questionnaire), `STANDARD` (ordinary projects: the complete
   assessment, stack alternatives with trade-offs, an adaptive questionnaire), `DEEP`
   (complex, critical or uncertain systems: exhaustive assessment, architectural as well as
   stack alternatives, dependencies and risks, a deep iterative questionnaire). Record the
   answer in the *THINK Depth* block with who and when. Never infer it — not from the
   project's size, not from the Method Plan (a different thing; the two are independent),
   not from a previous project. If the human does not choose, leave it empty: `STANDARD`
   applies as a fallback and you report it as *not selected*, never as a choice.

   The depth changes how far you dig, never which rule you may skip. At `QUICK` the floor
   is still assessed line by line, a design below it is still `POOR`, and an area you did
   not assess is written `not assessed (QUICK)`, never `SOLID`.

   **Escalation is a proposal.** If what you find justifies a deeper level — regulated
   data, requirements that constrain the architecture, several integrations, documents
   that disagree on a structural point, a floor line with no obvious way to meet it — add
   a row to the *Escalation log* with the evidence, tell the human in one line, and keep
   working at the current depth until they decide. Only an accepted row changes the depth.
   `bash .gtt/scripts/gtt-project.sh think` reports the recorded depth and fails on a depth
   nobody decided or a verdict above `POOR` with the floor unmet.
2. Fill sections 1–5: the documents assessed; how several documents are resolved (the
   Solution Designer's choice above); each area rated `SOLID`, `THIN` or `MISSING` with the
   `[FUENTE: file:line]` that supports the rating; the minimum floor; the verdict. Rate what
   the documents say, never what you assume the author meant.
3. The floor is not negotiable: the problem and scope are stated, the architectural style is
   stated, **the technology stack is decided** (language and runtime, framework, compute
   model) and **the datastore is decided** or explicitly not needed. A design below the
   floor is `POOR`, whatever else it gets right.
4. Fill section 6, the strengthening plan. For every stack layer that is undecided, or
   decided without a reason, give the options that fit **this** project — its requirements,
   constraints, team and scale as the documents state them — with the trade-offs of each
   and a recommendation that says what it optimises for and what it gives up. Each option
   and each recommendation is a `[PROPUESTA]`. When the documents do not say enough to
   recommend, say so and ask; never recommend a generic favourite, and never write a stack
   choice as decided because you recommended it.
5. Report the verdict in a few lines — verdict, what is thin or missing, what you recommend —
   and ask the Solution Designer how to proceed:
   - **`STRONG`** — offer strengthening; they may skip it.
   - **`ADEQUATE`** — offer strengthening and recommend it for the areas listed.
   - **`POOR`** — the design must be strengthened before it is used. Do not map it into the
     six files as it is; say plainly that the floor is not met and which line fails.
6. **Strengthening** is written, not talked about, and it reuses the one instrument the
   Bootstrap has for this: materialize the Initial Design Questionnaire (below), carry into it
   what the documents already establish — each statement with its `[FUENTE: file:line]` — and
   conduct the interview only for the areas rated `THIN` or `MISSING`. The decisions the
   Solution Designer takes on section 6 are recorded there as human decisions; an option
   nobody decided stays a `[PROPUESTA]` and maps to nothing. The original documents are never
   rewritten. The completed questionnaire is then the source document, exactly as when there
   was no document at all.

The assessment decides nothing and governs nothing. It is removed by `gtt-freeze.sh` with
the other bootstrap drafts.

### The Initial Design Questionnaire (no sufficient design document)

If the human has no design document, or the assessment above found it `POOR`, or they chose
to strengthen it, do not improvise an interview: offer the Bootstrap's Initial Design Questionnaire. It is owned
by the Bootstrap (`.gtt/scaffold/templates/gtt-initial-design-questionnaire.md`, declared
under `templates:` in the manifest); there is exactly one, and you never copy or
paraphrase it anywhere else.

1. Materialize the working copy: `bash .gtt/scripts/gtt-template.sh materialize initial-design-questionnaire`
   (dry run), then `--apply`. It creates `gtt-domain/proposals/bootstrap/initial-design-questionnaire.md`,
   never overwrites an existing one and registers it in the index. To resume an earlier
   session, open the existing copy instead.
2. Read the questionnaire's *Operating Contract* (section 1) and follow it: inspect the
   project before asking, ask progressively — never the whole form at once — and populate
   the document as the conversation goes. When there is no Design Assessment, establish the
   THINK Depth here before the first question — ask once, record it in the questionnaire's
   *THINK Depth* block, never infer it; with an assessment, the depth recorded there applies
   and this block stays empty. Escalation is proposed in the questionnaire's own log.
3. Keep provenance honest: `[FUENTE: archivo:línea]` for what the project shows, `[VACÍO]`
   for what is not established, `[CONFLICTO]` when sources or answers disagree,
   `[PROPUESTA]` for an option you suggest. A proposal is never a decision, an ADE
   inference is never a human decision, and you never fill `Human decision` for the human.
4. Stop when the human has reviewed the summary (section 24) and Readiness (section 23) is
   `READY` or `READY_WITH_OPEN_ITEMS`, or when they decide to continue later. `NOT_READY`
   is the same as an unfinished draft (step 3): stop.
5. From then on the questionnaire is the source document: step 3's confirmation is about
   it; step 4 maps it to the six files — a `[VACÍO]` becomes an empty cell, an unresolved
   `[CONFLICTO]` is asked again, and a `[PROPUESTA]` becomes context only if a
   `Human decision` records it; step 6 preserves the completed questionnaire verbatim as
   `SOURCE-BRIEF.md`. The working copy under `gtt-domain/proposals/bootstrap/` is removed
   by `gtt-freeze.sh` together with the other bootstrap drafts.

The questionnaire never becomes governed architecture by being filled in.

## 3. Confirm the document is finished — or stop

If a document exists, do not start mapping it yet. With the assessment written
(step 2), ask the Solution Designer directly: is this finished — the real
decisions, not a draft you're still thinking through?

- **Confirmed finished, and the assessment is `STRONG` or `ADEQUATE`:** move to
  step 4. What the assessment found `THIN` or `MISSING` and they chose not to
  strengthen becomes a question in step 4 or a gap — never a guess.
- **Confirmed finished, but the assessment is `POOR`:** the confirmation does
  not lift the floor. Say which line is not met and strengthen the design
  (step 2); a design with no decided stack cannot be governed, however final
  its author considers it.
- **Still a draft, unsure, or "sort of":** do not map it. Offer to strengthen
  it (step 2) — that is the governed way to finish a draft: the open points
  become questions and proposals the Solution Designer decides, in writing.
  If they prefer to finish it on their own, stop; they run this skill again
  once it is ready. Patching a draft with ad-hoc interview questions is not
  the same as the Solution Designer deciding it.
- **No document exists at all:** run the Initial Design Questionnaire (above);
  its review, with Readiness `READY` or `READY_WITH_OPEN_ITEMS`, is this step's
  confirmation, so continue to step 4 once that holds. The interview itself is how
  the design gets defined this time.

This is a different confirmation from step 5. This one is about whether the
Solution Designer's *own* thinking is settled. Step 5 is about whether the
*derived* context files accurately capture it. Conflating them lets an
unfinished design slip through disguised as a completed bootstrap.

## 4. Ask what is still missing

Read the confirmed document and map its content onto the six files below. For
anything it does not answer, add it to the question list — do not infer or
invent an answer from adjacent context.

Group questions by file, not by field — six short rounds, not forty
one-line questions. Only ask about what the document actually left open.

| File | Ask for |
|---|---|
| `solution-vision.md` | The problem, who it's for, what success looks like, what it deliberately will not become |
| `architecture.md` | Architectural style, modules and boundaries, integration strategy, data ownership, deployment topology, known deviations |
| `stack.md` | Language, runtime, framework, compute model, datastores, messaging, identity, secrets, IaC, CI/CD, observability, testing |
| `constraints.md` | Cloud provider, compute model, IaC, runtime/language version, datastore, comms style, data residency, compliance, budget ceilings, explicit out-of-scope |
| `principles.md` | Design principles that would actually cause a PR to be rejected, and the trade-off each one accepts |
| `glossary.md` | Domain terms whose meaning here differs from the everyday meaning |

The fewer answers exist going in, the more of this step runs. That is
expected, not a failure state — a project with a thin source document just
needs more of the conversation to happen here instead.

If an answer is genuinely not decided yet, leave it empty rather than filling
it with a plausible guess — say so explicitly. An empty cell is a decision not
yet made; a guessed one is architecture invented by the agent, which is the
exact failure GTT exists to prevent.

Classify every empty decision as a gap in the `gtt-gaps` block of `stack.md` (section 8), tagged
`[VACÍO: GAP-001]` where it appears: **BLOCKING** if the design cannot be frozen without it,
**OPEN** if the current design stands without it (an OPEN carries an explicit `scope:` and is never
an authorisation). Where sources disagree write `[CONFLICTO: a vs b]`; never pick a winner silently.
A `[PROPUESTA]` never goes into the six files. `.gtt/scripts/gtt-check-provenance.sh --pre-freeze`
tells the Solution Designer what still blocks the freeze.

## 5. Confirm before drafting

Summarize what will go into each of the six files — not the full file text,
enough to review in one pass — and get explicit confirmation from the
Solution Designer before writing anything. Silence is not confirmation.

## 6. Write the context, then stop

The project is pre-freeze, so these paths are writable. Write directly the six
files under `gtt-domain/context/`, using the exact target filenames (`stack.md`,
`architecture.md`, `constraints.md`, `principles.md`, `solution-vision.md`,
`glossary.md`).

If a source document existed (step 2), also write it at the project root as
`SOURCE-BRIEF`, keeping the original file extension, unmodified and not
paraphrased.

The accepted-decisions folder is writable in this same window: if
`ADR-001-context-governance.md` is not already there, write it too.

Then stop, without touching the freeze marker. End with a note telling the
Solution Designer to review and then run the freeze script to ratify.

## After bootstrap

Report, then point out three things.

**Report** (from step 0): the Method Plan the human selected (or `not selected`), detected ADEs,
participating ADEs, the Primary ADE, files
installed, ADEs explicitly excluded, and whether native support exists for each
participating ADE. Give this report in chat, and also append it to `.gtt/docs/gtt-completion.md`,
following the exact shape in `AGENTS.md` → *Completion report* — that file
is the durable record; chat output alone is lost once the session ends.
Append, don't overwrite, if the file already has an entry from a prior
bootstrap or re-run.

Before stopping, check `gtt-domain/backlog.md`: if the source document or the
conversation surfaced Epics or Stories, ask whether they should be recorded
there now (via `gtt-propose-change`, form 4, same as any other backlog
change) — do not silently leave them out, and do not invent ones that
weren't actually stated. If nothing like that came up, say so plainly and
move on; an empty backlog is a valid state, not a gap to fill by guessing.

Record each Story with exactly what the source gives. When the source
brings only titles — the usual case — the Story is `Undesigned`: title and
status, nothing else. Do not complete Description, Scope or Acceptance
Criteria from your own reading of the source to make the backlog look
finished, and never record such a Story as `Ready`. Then say it plainly in
the report: how many Stories were recorded, how many are `Undesigned`, and
that none of those is implementable until its Epic goes through the design
stage (`gtt-propose-change`, form 6) and the Solution Designer approves each
Story. A source that does carry a full definition for a Story is mapped
field by field with `[FUENTE: ref]` on every statement; it still becomes
`Ready` only after the Solution Designer approves it.

If the host project already contains source files with `@GTTGuard` markers
(a prior partial setup, or code copied in before GTT was bootstrapped), run
`bash .gtt/scripts/gtt-guard-sync.sh` once the workspace is in place so
`.gtt/protection/registry.yaml` reflects them from the start, rather than
leaving it stale until someone happens to run the sync later.

Point out three things:

- `stack.md`'s "Locked by" column should reference `ADR-001` for now; later
  decisions get their own ADR through the normal change flow.
- If a `SOURCE-BRIEF.*` was created, it now sits permanently at the project
  root — the original design intent, kept for anyone who later asks why the
  context says what it says.
- Run `bash .gtt/scripts/gtt-validate.sh` (every participating ADE's integration is
  checked against `.gtt/ade.json`) and, in each participating ADE, confirm only its
  own always-loaded file (`.claude/CLAUDE.md` for Claude Code, `AGENTS.md` itself
  for Kiro/Codex/Copilot), `AGENTS.md`, and `constraints.md` load — the same check
  the README asks for after any setup.
