---
name: gtt-bootstrap
description: Set up GTT in a project for the first time - detect candidate ADEs and install the overlays of the ones the human chooses (exactly one Primary), then populate gtt-domain/context/. Use when the user says to set up, bootstrap or initialize GTT, or when gtt-domain/context/ still holds template placeholders. Finds the design document at the project root (or offers the Initial Design Questionnaire), assesses it in writing and strengthens a poor one - a decided technology stack is the minimum - resolves several documents, asks for the development method (never defaulted) and cuts Epics by it, confirms the design is finished, asks for what is missing, and drafts the six context files plus SOURCE-BRIEF for review before writing anything. Not for a frozen project: use gtt-audit or gtt-propose-change.
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

# Bootstrap the governed context

> **Speaking for GTT.** Every message this skill raises to the human — a
> question, a confirmation, a proposal, a finding, a request for
> authorization, a report — opens with `@gtt · <what this is>`
> (e.g. `@gtt · Autonomy Profile`). The marker says who is speaking; it is never a decision.

`gtt-domain/context/` ships as a template — angle-bracket placeholders and empty
table rows, not real answers. This skill turns those placeholders into the
project's actual context, confirmed by the Solution Designer before anything
is written.

## 0. Detect candidate ADEs, let the human choose, and resolve the overlays

Do this before touching the filesystem, and before step 1. **Read
[references/ade-overlays.md](references/ade-overlays.md) and follow it.** In short:
detection is not participation (`gtt-ade.sh detect` lists candidates only); ask which
ADEs participate and which one is the Primary - exactly one, and it holds no authority;
install with `gtt-ade.sh install`, dry run first, never by hand; on a re-run read
`gtt-ade.sh state` and never drop, re-add or re-prime an ADE the human did not name.
Note what was resolved for the report after step 6.

### Autonomy Profile

Before step 1, establish the project's Autonomy Profile. It is the human's choice.

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

### Development method (Method Governance)

Right after the Autonomy Profile, establish how the solution will be developed. It is a
different question from the Autonomy Profile (how much work GTT does without asking) and
from the THINK Depth (how deep THINK digs); never derive one from another. The
method is the template THINK reasons with when it cuts Epics and writes their
designs; the freeze ratifies it as the **Method Lock** and it is verified afterwards.
The Method Packs (`.gtt/methods/`) are the only source of each method's texts.

1. Run `bash .gtt/scripts/gtt-method.sh get`. If the setup already answered (the CLI's
   `gtt init`, or an earlier run), state the answer in one line and do not ask again.
   If the project is frozen, do not ask at all: the ratified method changes only
   through `gtt-propose-change` (form 6).
2. Otherwise ask the two questions under `@gtt · Development method`, one per message,
   with numbered options. Show each option exactly as
   `bash .gtt/scripts/gtt-method.sh list --lang <es|en>` prints it - name, *Qué es* /
   *What it is*, *Conviene si* / *Fits when* - never a paraphrase, and mark as
   recommended only what it marks. Question 1 (how to organise the development)
   allows a combination and offers "I am not sure, help me choose"; question 2 (how
   to start) offers "straight to the main functionality".
3. Record the answer: `bash .gtt/scripts/gtt-method.sh select --style <ids|help> --start
   <id|direct|help>` (dry run), then `--apply`. It refuses a combination the packs
   declare incompatible: say which pair and ask the human to change it. A question
   left unanswered is `OPEN`.
4. **Never apply the recommended option in silence**, and never infer the method from
   the project, the stack, the ADE or a previous project. `help` decides nothing yet:
   see *Help me choose* in *The design intake* (step 2).

The setup answer is not governed context. It reaches `architecture.md` as the Method
Lock in step 4, with Confirmation B, and the freeze ratifies it.

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
  none at all, offer the Initial Design Questionnaire (*The design intake*, below).
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

### The design intake

Once you know whether a design document exists, **read
[references/design-intake.md](references/design-intake.md)** and follow the part that applies:

- *Assess the design* - a document exists: establish the THINK Depth, write the Design
  Assessment (`SOLID` / `THIN` / `MISSING` per area, the minimum floor, the verdict) and
  offer strengthening; a `POOR` design is never mapped as it is.
- *Help me choose* - the development method is `OPEN`: propose one as a `[PROPUESTA]`, and
  cut no Epic until the human answers.
- *Git workflow* - run `gtt-workflow.sh detect` once; report, adopt nothing.
- *The Initial Design Questionnaire* - no document, a `POOR` one, or strengthening chosen:
  materialize it, never improvise an interview.


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
- **No document exists at all:** run the Initial Design Questionnaire (*The design intake*);
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
| `architecture.md` | Architectural style (and the development method: the Method Lock below), modules and boundaries, integration strategy, data ownership, deployment topology, known deviations |
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

**The Method Lock.** Map the development method (`gtt-method.sh get`) into the context, as
`.gtt/methods/README.md` → *The Method Lock* defines it:

- `architecture.md` → *Architectural style*: the method or combination in words, and why; the
  `gtt-method` block (style, start, status, locked_by, verification); and, in *Modules and
  boundaries*, the real folders the packs' roles map to (the slices and the shared kernel, the
  domain and the adapters, the bounded contexts, the layers).
- An ADR when a chosen pack says `requires_adr: true` (every architecture style does; a
  decomposition strategy such as Walking Skeleton does not): draft it from
  `gtt-domain/adr/ADR-TEMPLATE.md` with the next free id (`gtt-project.sh next-id --kind adr`) -
  context, the decision, the packs not chosen as *Alternatives considered* with why they lost,
  and what the packs' *Qué descarta* means as consequences. It is part of what Confirmation B
  confirms; it names the lock's `locked_by`, and the map change log gets its row.
- `stack.md`: the row `Development method` (the pack ids, and the ADR under Locked by), and in
  section 5 every `dependency` rule of the chosen packs with this project's real paths and the
  rule id in the *Rule* column. Never invent a path: a folder architecture.md does not declare
  is a question.
- **An OPEN method** is written as such, never left out and never guessed: `status: open`,
  `locked_by: OPEN`, `gap: GAP-NNN`, an `OPEN` gap with the topic `Development method` and an
  explicit scope in section 8, and `OPEN` under *Locked by* of the `Development method` row. It
  does not block the freeze, and no pack's template or rule applies while it is open.

`bash .gtt/scripts/gtt-method.sh check` reports what is missing (`--pre-freeze` is what the
freeze runs).

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

### Register the sources and write the design of each Epic

**Read [references/epic-designs.md](references/epic-designs.md) and follow it** before
registering a source or cutting an Epic: sources go through `gtt-source.sh`, the chosen
method packs cut the Epics (they stay `Proposed`), one design per Epic carried over in full
and cited, `gtt-check-design.sh` and `gtt-method.sh check` must pass, and approval is the
human's (`gtt-approve.sh`) - never write `Approved` yourself.

Then stop, without touching the freeze marker. End with a note telling the
Solution Designer to review and then run the freeze script to ratify. Freezing
makes this design the authority and records the baseline observation compares
the work against; it does not stop the code from changing.

## After bootstrap

Report, then point out three things.

**Report** (from step 0): the Autonomy Profile the human selected (or `not selected`), the development
method (the packs and who decided, or `OPEN` with its gap), detected ADEs,
participating ADEs, the Primary ADE, files
installed, ADEs explicitly excluded, and whether native support exists for each
participating ADE. Give this report in chat, and also append it to `.gtt/docs/gtt-completion.md`,
following the exact shape in `AGENTS.md` → *Completion report* — that file
is the durable record; chat output alone is lost once the session ends.
Append, don't overwrite, if the file already has an entry from a prior
bootstrap or re-run.

Before stopping, check `gtt-domain/backlog.md`: if the source document or the
conversation surfaced Epics, ask whether they should be recorded there now
(`gtt-propose-change`, form 4) - do not silently leave them out, and do not
invent ones that were not actually stated. An Epic the human has not approved
is recorded as `Proposed`; never write its `Approved` yourself. If nothing
like that came up, say so plainly and move on; an empty backlog is a valid
state, not a gap to fill by guessing.

Stories need none of this. If the source lists Stories, record them under
their Epic as `Planned`, with what the source gives; they are the working plan
and whoever does the work will rewrite them. Nobody approves a Story.

Check the `gtt-boundaries` block of `gtt-domain/context/stack.md` too: it is
what observation will watch once the project is frozen. If it is empty, say so
in the report - observation then only knows the built-in boundaries - and
offer to draft rules from the decisions the context now holds (each one
pointing at its decision; `BLOCKING` only where the source itself prohibits
something). The human confirms them like the rest of the context.

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
