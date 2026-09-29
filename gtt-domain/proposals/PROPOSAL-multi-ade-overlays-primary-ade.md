# PROPOSAL — Multi-ADE overlays with one Primary ADE, and the Initial Design Questionnaire as Bootstrap contracts

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Form 1 — Architecture change. **Draft, not a decision.** Nothing here governs anything until the Solution Designer decides. This file supersedes the earlier
draft of the same name (which covered only Multi-ADE and proposed `.gtt/ade.yaml`); the task it answers is `GTT_BOOTSTRAP_TASK_QUESTIONNAIRE_MULTI_ADE.md`.

**Nothing was applied.** The project is frozen and no governed file was touched: everything below is staged under `gtt-domain/proposals/`.
The agent did not and will not run the promotion script.

## What is in the package

| File (under `gtt-domain/proposals/`) | What it is |
|---|---|
| `PROPOSAL-multi-ade-overlays-primary-ade.md` | This document: analysis, implementation plan, validation plan, open decisions |
| `ADR-DRAFT-bootstrap-integration-contracts.md` | ADR-005 as it will read once ratified (Status/Date/Approved-by are stamped by the script) |
| `context-{stack,architecture,glossary,constraints,principles}-adr-005.md` | Full-file drafts of the five L0 files the ADR changes |
| `adr-005-package/tree/**.staged` | Full post-image of every machinery, instruction and documentation file the decision changes or creates (`.staged` keeps the index and link checks from treating a copy as a live document) |
| `adr-005-package/rehearse-multi-ade.py` | Rehearsal harness: exercises the new engine on a **temporary copy**; independent of the promotion script |
| `apply-ADR-005-bootstrap-integration-contracts.sh` | The promotion script. **Human execution required; running it ratifies ADR-005** |

## Proposed Architecture Change (Form 1)

```text
Current decision:
  The ADE overlay is "exactly one per installed project", resolved from the ADE that executes the bootstrap
  (ADR-003 layer table; ADR-004 §1; manifest layers.overlay and the `overlays:` comment; AGENTS.md; the gtt-bootstrap
  skill step 0; gtt-check-adapter.sh; gtt-validate.sh). The Initial Design Questionnaire exists at
  .gtt/scaffold/templates/gtt-initial-design-questionnaire.md but nothing in the Bootstrap exposes it.

Suggested change:
  1. One governance model, several ADE integration surfaces: one overlay per PARTICIPATING ADE, exactly ONE PRIMARY ADE.
  2. Detected (an observation, never stored) != participating (human-chosen, stored) != primary (one participating ADE).
  3. The Primary ADE is a workflow identifier and holds NO authority. No ADE hierarchy, voting or arbitration.
  4. Instruction files and overlays (AGENTS.md, CLAUDE.md, .claude/, .kiro/, .copilot/, .codex/, ADE memory) are integration
     surfaces, never governance authority.
  5. The ADE registry is the manifest's `overlays:` section, extended; the per-project choice and the ledger of what GTT
     installed is `.gtt/ade.json`, written only by `.gtt/scripts/gtt-ade.sh`.
  6. The Questionnaire stays where it is, is declared under `templates:` in the manifest and requested through
     `.gtt/scripts/gtt-template.sh`; the working copy goes to gtt-domain/proposals/bootstrap/; it is source material.
  7. Every lifecycle operation (init, validate, status, inspect, resume, freeze, update, clean, export --clean) has a
     Bootstrap-side contract the CLI consumes (ADR-005, Decision 10).

Reason:
  Other agents (Copilot, Codex, a second Claude Code terminal) will open the project and edit files; "GTT governs the project"
  is false for any of them that runs without its overlay. Forcing one overlay leaves an ADE ungoverned or pushes a workaround
  into the CLI. And a project with no design document has no Bootstrap-defined way to start.

Impact / Risk / Alternatives:  ADR-005 draft (Impact = "Affected context"; Risks; Alternatives considered).

Status: Requires Solution Designer approval
```

## 1. Analysis of the current Bootstrap (task §28)

Inspected: manifest, ADE detection, overlays, `AGENTS.md`, ADE instructions, scripts, scaffold, protection, session adapters, status, validation, freeze,
clean/export mechanisms, indexes and installation metadata.

**1. What already supports several ADEs (kept, not rewritten)**

- `.gtt/session-adapters/<ade>.json` — one data-only declaration per ADE (claude, codex, copilot, kiro); `gtt-validate.sh` already discovers the ADE set from it.
- The Core (`gtt-status.sh`, `gtt-session-context.sh`, `gtt-run-python.sh`): ADE-agnostic (verified by grep: no ADE name).
- The Session Memory contract and its static conformance check (`gtt-check-session-adapter.sh`).
- GTTGuard, artifact identity/index, the freeze regime and `protect-l0.py`: none of them mentions an ADE.
- The manifest already lists all four overlays (`overlays:`) with `id`/`path`/`kind`.

**2. What assumes exactly one ADE (to generalise)** — every row listed under *Current state* in the ADR, concretely: manifest `layers.overlay` and the `overlays:` comment;
`AGENTS.md` (2 workspace trees, the overlay table row, *Adapters vs. portable core*, *Bootstrap behavior* 1, 3 *Non-negotiable rules*, installed-layout rules 4, 5, 14);
`gtt-bootstrap` step 0; `gtt-check-adapter.sh` (one ADE ⇒ the others must be ABSENT); `gtt-validate.sh` (SKIPPED unless exactly one adapter matches); READMEs (EN/ES),
`installation`/`usage` (EN/ES), `docs.md`, `index.md`; glossary *Scaffold*; ADR-003/ADR-004 rows (amended by ADR-005, not edited).

**3. What must be generalised** — the overlay layer (one → one per participating ADE + one Primary); adapter validation (matrix → state-driven); the bootstrap step 0
(resolve the executing ADE → detect candidates, human chooses, install); status/session (name the ADE state).

**4. What must remain unchanged** — L0/L1 protection and freeze; GTTGuard; identity/index contracts; the Session Memory contract and every `session-adapters/*.json`;
`gtt-freeze.sh`; `gtt-session-context.sh`; the hooks and `settings.json` (machinery); the Human Promotion Boundary; the questionnaire file itself (not renamed, moved or duplicated);
`backlog.md`; ADR-001/003/004 (remain the record of what was decided then).

**5. What new state must be represented** — `.gtt/ade.json` only: `primary`, `participating`, `excluded`, and per ADE an install record (`origin`, ledger `path → sha256`).
*Detected* is deliberately **not** state. There was no per-project ADE state, no record of what GTT installed and no cleanup contract before; nothing here competes with existing state.

**6. What contracts the CLI consumes** — `gtt-ade.sh {list,detect,state,validate,owned}` (`--json`) and `{install,adopt,set-primary,record,remove,update}` (dry run until `--apply`);
`gtt-template.sh {list,show,materialize}`; the manifest sections `overlays:` and `templates:`; the exit codes (0 ok, 1 violation/conflict, 2 cannot run).
The CLI holds no ADE-specific path, no template copy and no governance logic.

## 2. Implementation plan (task §29.2)

All files below are placed by `apply-ADR-005-…sh` from the staged post-images; *Risk* is the risk of that one change.

### New files

| Path | Current responsibility | Required change | Reason | Risk |
|---|---|---|---|---|
| `.gtt/scripts/gtt_manifest.py` | — | New: reads the manifest's single-line flow mappings (no YAML dependency); typed accessors for `overlays:`/`templates:` | The registry lives in the existing manifest; the Core needs a reader, not a parser package | It is not a YAML parser: fails loudly (`ManifestError`) on anything outside the subset; a future manifest change must respect it |
| `.gtt/scripts/gtt_ade.py` | — | New: ADE integration engine — `list detect state validate owned` (read-only), `install adopt set-primary record remove update` (dry run, no overwrite, rollback) | One deterministic contract for the CLI and humans; ownership ledger for clean/export | Largest new code; exercised by 103 rehearsal checks on one platform only |
| `.gtt/scripts/gtt-ade.sh` | — | New: ADE-independent entry point over `gtt-run-python.sh` | Same launcher pattern as every other Core script | Low |
| `.gtt/scripts/gtt_template.py`, `gtt-template.sh` | — | New: `list`, `show`, `materialize` for Bootstrap-owned templates; registers the working copy via `gtt-index.sh` | The CLI must discover/request the questionnaire through the Bootstrap, never hard-code it | `materialize` calls `gtt-index.sh`; if that refuses (unreconciled move) the copy exists but exits 1 with the reason |

### Modified files (machinery, instructions, documentation)

| Path | Current responsibility | Required change | Reason | Risk |
|---|---|---|---|---|
| `.gtt/scaffold/manifest.yaml` | Single declarative scaffold definition; `overlays:` = id/path only | `overlays:` extended into the ADE registry (`name entry owned detect enforcement scaffold`); new `templates:` section; `.gtt/ade.json` and `templates/` declared; "exactly one" wording removed | "Use the existing registry/manifest; do not create a parallel model" | Data only; the reader tolerates only its subset |
| `.gtt/scripts/gtt-check-adapter.sh` | One ADE ⇒ the others must be absent | No argument: validate every participating ADE against `.gtt/ade.json`; with an argument: the old single-ADE matrix, unchanged | `validate` must check each participating integration and never silently ignore one; legacy projects keep working | Exit-code contract for no-argument calls changes (0/1, or 2 when no state) |
| `.gtt/scripts/gtt-validate.sh` | Adapter check SKIPPED when 0 or >1 adapters match | When `.gtt/ade.json` exists: run the state check (FAIL/WARN per ADE); otherwise the previous behaviour | Same aggregate gate, now multi-ADE aware | The catalog stays SKIPPED, exactly as before |
| `.gtt/scripts/gtt-status.sh` | Derived session snapshot; names no ADE | New section *ADE integration* (via `gtt-ade.sh state`) | `status`/`inspect`/`resume` show Primary, participating, health; the same file is what every ADE resumes from | Must stay ADE-agnostic (asserted by the rehearsal) |
| `AGENTS.md` (CRLF in the working tree; preserved) | Portable agent contract | Trees, overlay row, *Adapters vs. portable core*, new *Multi-ADE participation* and *Initial Design Questionnaire* sections, *Bootstrap behavior*, *Conflict policy*, *Session continuity*, *Validation*, non-negotiable rules, installed-layout rules | The contract must state the model, the Primary semantics and the ownership rules | Protected file: only a human places it |
| `.claude/skills/gtt-bootstrap/SKILL.md` | Step 0: resolve exactly one adapter; interview when no document | Step 0: detect → human chooses participating + Primary → `gtt-ade.sh install`; re-run rules; questionnaire procedure; closing checks | The skill is how the bootstrap runs | Behavioural: an agent following the old skill still installs one ADE |
| `readme-gtt.md`, `readme-gtt.es.md` | Human entry point; "exactly one adapter" | Process steps, *ADE adapters* (model, terms, `gtt-ade.sh`), new *Starting without a design document*, *Switching ADE later* rewritten around `gtt-ade.sh`; EN/ES kept in step | The canonical human documentation | Two languages: a mismatch is possible; the ES text was written from the EN text |
| `.gtt/docs/installation.md`, `installation.es.md`, `usage.md`, `usage.es.md` | Install/usage procedures; "exactly one" | Procedure, checklist, tree and adapter sections | Same reason | As above |
| `.gtt/scaffold/templates/gtt-initial-design-questionnaire.md` | The questionnaire | Its 53 `{=html}` answer slots become plain `<!-- ADE populates this section -->` comments; wording and semantics untouched (verified: diff ignoring fences and blank lines is empty) | Slots rendered as code blocks | Low; same file, same path |
| `gtt-domain/proposals/apply-session-adapters.sh` (edited in place; not part of the promotion) | Installs staged Session Memory adapters | After its validation it calls `gtt-ade.sh record` for the installed files (warns, never fails, if the ADE does not participate or there is no `.gtt/ade.json`) | One ownership contract for clean / export --clean | Not run; the record step is rehearsed |
| `.gtt/docs/docs.md`, `.gtt/docs/index.md` | Methodology/portability; file map | Validation regimes, participation model, the "more than one ADE" and "only one" sections, new rows for the engines, `.gtt/ade.json`, the template | The map must list every file | Low |

### Governed context (L0) — via the ADR

| Path | Current responsibility | Required change | Reason | Risk |
|---|---|---|---|---|
| `gtt-domain/context/stack.md` | The architecture map | Governing ADRs +ADR-005; two dependency-rule rows; Multi-ADE rule line; change-log row | `context/stack.md` §6: every accepted ADR has a row; `gtt-check-stack.sh` fails an ADR without a map change | L0: only through the script |
| `gtt-domain/context/architecture.md` | Architecture in prose | Adapter row generalised; `.gtt/ade.json` and `.gtt/scaffold/` rows; third governing rule; two data bullets; enforcement note in *Known deviations* | The model becomes architecture | L0 |
| `gtt-domain/context/glossary.md` | Terms | *Scaffold* updated; Detected/Participating/Primary ADE, Integration surface, Initial Design Questionnaire | The terms must mean one thing | L0 |
| `gtt-domain/context/constraints.md` | Always-loaded hard limits | One line under *Explicitly out of scope* (no ADE governance/hierarchy; Primary holds no authority) | It is the one file every session loads; the invariant rules something out | L0; loaded every session, so kept to one line |
| `gtt-domain/context/principles.md` | Principles in force | Three principles that each rule something out | Same | L0 |
| `gtt-domain/adr/ADR-005-bootstrap-integration-contracts.md` | — | New (from the draft), stamped at ratification | The decision record | — |

### Written by the script, derived or appended

| Path | Change | Reason |
|---|---|---|
| `.gtt/docs/gtt-completion.md` | Append-only record of this promotion (states what was and was not verified) | Durable record; AGENTS.md → *Completion report* |
| `.gtt/index/artifacts.json`, `technical-index.json`, `gtt-domain/session.md` | Regenerated by `gtt-index.sh` / `gtt-status.sh` | Derived; registers ADR-005, the drafts, the questionnaire and this proposal (today they are unregistered and fail `gtt-check-integrity.sh`) |

### Deliberately not changed

`.gtt/session-adapters/*.json` and the staged Codex/Copilot/Kiro session adapters (adopting them is a separate promotion, `apply-session-adapters.sh`); `gtt-freeze.sh`;
`gtt-session-context.sh`; `.claude/hooks/*`, `.claude/settings.json`, `.claude/CLAUDE.md`; `.kiro/`, `.copilot/`; `gtt-check-session-adapter.sh`; `gtt-domain/backlog.md`; the questionnaire file; ADR-001/003/004.

## 3. Validation plan (task §29.4)

**Before running the script** (nothing here writes to the project)

1. `bash -n gtt-domain/proposals/apply-ADR-005-bootstrap-integration-contracts.sh` — syntax only.
2. `bash .gtt/scripts/gtt-validate.sh` — baseline: everything PASS except `gtt-check-integrity.sh` (the questionnaire and the staged drafts are not registered yet, plus 2 pre-existing Spanish-anchor warnings). The script registers them (`gtt-index.sh`) and requires no *new* FAIL.
3. `python gtt-domain/proposals/adr-005-package/rehearse-multi-ade.py --project .` — expect `103/103 checks held` (it copies the project to a temp dir, overlays the package, drives the whole lifecycle and runs the gate).
4. Read this proposal and the ADR; run the script and use `adr`, `l0` and `all` at its prompt to read the ADR and the exact diffs before typing `ratify`.

**After running it**

5. The script itself runs `gtt-validate.sh`; expect every line PASS, SKIPPED (adapter check — this repository is the catalog and has no `.gtt/ade.json`) or CANNOT-DETERMINE (`gtt-check-stack.sh` needs `origin/main`). Any new FAIL restores everything.
6. `python gtt-domain/proposals/adr-005-package/rehearse-multi-ade.py --catalog .` — same rehearsal against the promoted tree.
7. `bash .gtt/scripts/gtt-ade.sh list`, `detect`, `state`; `bash .gtt/scripts/gtt-template.sh list`, `show initial-design-questionnaire`.
8. `git status` / `git diff --stat`: only the files listed in the script's summary changed; `gtt-domain/.frozen`, `backlog.md`, `change-request.md`, `SOURCE-BRIEF.*`, hooks and `settings.json` did not.
9. In a scratch project (never this one): `gtt-ade.sh install --from <this repo> --participating claude,codex --primary claude` (dry run, then `--apply`), `validate`, `owned`, `remove … --apply`, `adopt` — the rehearsal already does this on temp copies.

**Acceptance criteria → where they are met** (task §31–§32)

| Criterion | Where / how |
|---|---|
| Multiple ADEs formally supported; one Primary; several participating | ADR Decisions 1–3, 6; `.gtt/ade.json`; `validate` (exactly one Primary ∈ participating) |
| Detection separated from participation | Decision 2; `detect` never writes; rehearsal "detect writes nothing" |
| Overlays via Bootstrap contracts; different directory conventions | Decision 5; `overlays:` (`.claude/` dir, `.kiro/` dir, one Copilot file, Codex `[]`) — no `.<ade>/` assumption |
| Governance authority stays GTT; instruction files are surfaces | Decisions 3–4; `AGENTS.md`, L0 (glossary, constraints, principles) |
| `init`, `validate`, `status`, `inspect`, `resume`, `update`, `clean`, `export --clean` | Decision 10; rehearsal scenarios init / validate / status-inspect-resume / update / clean |
| `resume` ADE-portable; no second memory | `session.md` section; no "last active ADE" (Decision 10); rehearsal "session.md carries it, still operational-only" |
| `export --clean` never deletes unrelated ADE config | Decision 8; `owned --json`; rehearsal keeps the host's own `.kiro/user-notes.md` and `.claude/keep-me.txt` |
| Single-ADE projects still supported | Decision 11; legacy matrix and `gtt-validate.sh` unchanged; `adopt`; rehearsal "migration" |
| No second governance model; CLI holds no ADE logic | Decisions 3, 7; `constraints.md` line; the Core-neutrality rehearsal check |
| Questionnaire recognised at its path; no duplicate; Bootstrap-owned | Decision 12; `templates:`; rehearsal asserts one template and the canonical path |
| CLI can discover/request/materialise it; does not duplicate content | `gtt-template.sh list/show/materialize`; rehearsal "verbatim working copy", "never overwritten" |
| ADE-guided, progressive; unknowns/conflicts/proposals explicit and distinct; not governed architecture; MVGD can emerge | Decision 13; `AGENTS.md` *Initial Design Questionnaire*; skill step 2 procedure. **Behavioural — instruction plane only**: no script can prove an ADE follows it |

**Not verified (stated plainly).** No run on Linux or macOS. No Codex, Copilot or Kiro runtime exercised; `enforcement:` restates `.gtt/docs/docs.md` (documented, not runtime-verified).
Nothing checks that an ADE actually follows the questionnaire's Operating Contract. The promotion script itself was **not executed** by the agent (only `bash -n`, isolated checks of its
hash table and `sed` expressions, and the rehearsal of the code it installs).

## 4. Decisions

**Taken by the Solution Designer in this session** (recorded so they are not silently re-opened)

| Question | Decision |
|---|---|
| Where/what format is the per-project state? | `.gtt/ade.json` (JSON, in the Engine) — replaces the earlier `.gtt/ade.yaml` |
| Where does the questionnaire working copy go? | `gtt-domain/proposals/bootstrap/initial-design-questionnaire.md` (cleaned by `gtt-freeze.sh`; becomes `SOURCE-BRIEF.md` once reviewed) |
| Scope of the new Engine code | Full: `gtt-ade.sh` with install/update/remove/… and `gtt-template.sh` |

**Second round, decided by the Solution Designer**

| Question | Decision |
|---|---|
| Backlog | Draft the Epic as a form-4 proposal (`PROPOSAL-backlog-epic-multi-ade-questionnaire.md`); `backlog.md` is not edited |
| `apply-session-adapters.sh` | Records installed files through `gtt-ade.sh record` (done) |
| Questionnaire slots | Normalised to plain Markdown comments, content unchanged (done, staged) |
| Changing the Primary ADE | Direct operation recorded in `.gtt/ade.json`; no ADR (in ADR Decision 3) |

**Made by the agent under those, and open to veto before you run the script**

1. One ADR (005) for both capabilities (the alternative, two ADRs, is in the ADR's table).
2. `excluded` is recorded at install for every registry ADE not chosen, so "never reintroduce" is enforceable; `adopt` leaves it empty (declining cannot be inferred).
3. No "last active ADE" in `session.md`.
4. Codex's overlay stays "AGENTS.md alone" (`owned: []`); its staged `.codex/` session adapter stays a separate promotion.
5. Non-Claude ADEs are governed by instructions plus CI, and the registry says so (`enforcement: ci-gate`).

**Still open**

- **Evidence.** `.gtt/docs/evidence.md` should gain classified rows for this work (STATIC VERIFIED / rehearsal only). Not staged: it is a claim about what you ran.

## 5. Next step (only after approval)

Review, then run it yourself from the project root:

```bash
bash gtt-domain/proposals/apply-ADR-005-bootstrap-integration-contracts.sh
```

Approving this proposal is not the promotion, and drafting the package was not approval of it. If the tree changes before you run it, the script refuses (sha256 of every file it replaces) and nothing is written.
