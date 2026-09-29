# ADR-005 — Bootstrap integration contracts: Multi-ADE with one Primary ADE, and the Initial Design Questionnaire

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

- Status: Proposed
- Date: {{RATIFIED_ON}}
- Approved by: {{RATIFIED_BY}}
- Supersedes: ADR-003 and ADR-004 in part (only their overlay row, "exactly one per installed project"; their layout decisions stand)

> Draft staged by an agent. **Not a decision.** `Status`, `Date` and `Approved by` are filled in by `apply-ADR-005-bootstrap-integration-contracts.sh`
> at the moment the Solution Designer ratifies by running it. Nothing here governs anything before that.

## Context

**Problem.** The Bootstrap installs *exactly one* ADE overlay per project, resolved from the ADE that happens to execute the bootstrap. Real projects do not work
that way: one engineer runs Claude Code, another Copilot, a third has Codex in a terminal next to it, and one editor may host three agents at once. With one
overlay, either the other ADEs run **ungoverned** (no instruction surface, no adapter check) or a CLI bolts extra overlays on outside the Bootstrap, so the
Bootstrap and the installed project disagree with the manifest. "GTT governs the project" is false the moment an agent without its overlay edits a file.
Separately, a project with **no sufficient design document** has no Bootstrap-defined way to start: the existing `gtt-bootstrap` step 4 improvises an interview,
while the Bootstrap already ships an elicitation instrument — `.gtt/scaffold/templates/gtt-initial-design-questionnaire.md` — that nothing exposes to a CLI or the skill.

**Current state (inspected, not assumed).** "Exactly one" is written in: ADR-003 (layer table), ADR-004 §1 (same row), `.gtt/scaffold/manifest.yaml`
(`layers.overlay`, the `overlays:` comment), `AGENTS.md` (workspace trees and table, *Adapters vs. portable core*, *Bootstrap behavior* 1, *Conflict policy*, three
*Non-negotiable rules*, installed-layout rules 4, 5, 14), the `gtt-bootstrap` skill (step 0), `gtt-check-adapter.sh` (one ADE ⇒ the others must be ABSENT),
`gtt-validate.sh` (adapter check SKIPPED when 0 or >1 overlays match), both READMEs, `installation`/`usage` (EN/ES), `docs.md`, `index.md` and the glossary
(*Scaffold*). What already supports several ADEs and is **not** rewritten: `.gtt/session-adapters/<ade>.json` (one declaration per ADE, data only — `gtt-validate.sh`
already discovers the ADE set from it), the Core (`gtt-status.sh`, `gtt-session-context.sh`, `gtt-run-python.sh`: ADE-agnostic, verified by grep), the
Session Memory contract, GTTGuard, artifact identity and the freeze regime (none of them mentions an ADE). There is **no** per-project ADE state, no
declared detection or installation contract, no record of what GTT installed (so nothing can safely `clean` or `export --clean` an overlay), no `gtt clean`
contract and no consumer contract for the CLI: `manifest.yaml` states that `gtt init` is "not implemented here". The questionnaire file exists but is unregistered
in the identity index and unreferenced by the manifest, the skill and `AGENTS.md`.

## Decision

1. **One governance model, several integration surfaces, one Primary ADE.** The overlay layer changes from "exactly one ADE integration per installed project" to
   **one overlay per participating ADE, with exactly one Primary ADE**. The governance, the governed artifacts, the freeze regime, GTTGuard and the Human
   Promotion Boundary are identical for every ADE. Nothing about ADEs is added to L0/L1 authority.
2. **Three concepts, kept apart.**
   - *Detected ADE* — an observation (an overlay path or an ADE binary was seen). A candidate only; it is **never installed, authorized, governed or
     participating by itself**. It is computed on demand (`gtt-ade.sh detect`) and **never stored** — a stored observation is stale by construction.
   - *Participating ADE* — an ADE the human explicitly chose to have GTT govern. It receives its overlay. Stored in `.gtt/ade.json`.
   - *Primary ADE* — exactly one participating ADE, chosen by the human: the principal environment of the project's workflow (for example, the ADE that
     conducts the Initial Design Questionnaire when a CLI launches it). Stored in `.gtt/ade.json`.
   Also stored: *excluded* ADEs — registry ADEs the human declined; a re-run never reintroduces one unless told to.
3. **The Primary ADE holds no authority.** It is a workflow identifier. It does not outrank, approve, arbitrate between or speak for another ADE, and no ADE —
   the Primary included — ratifies anything (`AGENTS.md` roles table unchanged: every ADE prepares, the human decides). No script behaves differently
   because an ADE is Primary. Changing the Primary is a **direct operation** (`gtt-ade.sh set-primary --apply`, recorded in `.gtt/ade.json`), not a governed change and needs no ADR: it alters the operating flow, not authority or governed architecture. ADE hierarchy, agent voting, arbitration and "agent authority" are **not introduced** and stay out of scope (`constraints.md`).
4. **Instruction files and overlays are integration surfaces, not authority.** `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.kiro/`, `.copilot/`, `.codex/`, and any ADE's
   memory, session history or notes let an ADE participate in GTT; none becomes a source of governance authority. Because several agents may run concurrently,
   **every** participating ADE receives its integration surface — governance never depends on the Primary being the active one.
5. **The registry is the manifest's `overlays:` section (extended), not a parallel model.** Each entry keeps `id`, `path`, `kind`, `required`, `role` and gains
   `name`, `entry` (the instruction entry point), `owned` (the paths GTT installs for it — the only paths clean/export may remove; `[]` for Codex), `detect`
   (paths that make it a candidate), `enforcement` (`realtime-hook` for Claude Code, `ci-gate` for the others — no ADE is credited with a guarantee it does not have)
   and `scaffold` (the layout version it targets). The ADE's Session Memory declaration stays `.gtt/session-adapters/<id>.json`, linked by `id`; its `ade_binary` is
   reused for detection. Directory conventions are data, never assumed: Claude Code `.claude/`, Kiro `.kiro/`, Copilot a single file, Codex `AGENTS.md` alone.
6. **The per-project state is one file, `.gtt/ade.json`** (schema 1, JSON like `artifacts.json` and the session-adapter declarations): `primary`, `participating`,
   `excluded`, and per ADE an install record — `origin` (`bootstrap` or `adopted`) and `files`, the ledger `path → sha256` of what GTT itself copied. It is written
   **only** by `.gtt/scripts/gtt-ade.sh`, never hand-edited, and is not governed context and not authority. It is required in an installed project and absent in the
   catalog. (The earlier draft named `.gtt/ade.yaml`; JSON was chosen so the Core needs no YAML parser and the ledger is machine-written.)
7. **The Bootstrap exposes the contract; the CLI only consumes it.** `.gtt/scripts/gtt-ade.sh` (engine `gtt_ade.py`, reader `gtt_manifest.py`) provides
   `list`, `detect`, `state`, `validate`, `owned` (read-only) and `install`, `adopt`, `set-primary`, `record`, `remove`, `update` (dry run unless `--apply`; never
   overwrite a file GTT did not install; roll back on any failure; `--json` on the read commands). The CLI never invents an ADE-specific path or carries ADE logic.
8. **Ownership ledger and the cleanup boundary.** `clean` and `export --clean` may remove only what `gtt-ade.sh owned` reports: files recorded in the ledger and
   still unmodified. A modified file is kept unless `--include-modified`; a file from an *adopted* ADE (no install record exists) is kept unless
   `--assume-registry-owned`; anything else — including a host `.claude/settings.json` that predates GTT, or a directory that merely *looks* like an ADE's — is the
   host project's and is never touched. Core entry points (`AGENTS.md`, the READMEs) go with the core, never with an ADE. An existing destination file is a
   **CONFLICT**: it is reported and nothing is written; GTT never merges into a host file.
9. **Validation semantics.** `gtt-check-adapter.sh` (no argument) validates every participating ADE against `.gtt/ade.json`: schema; exactly one Primary, and it
   participates; no ADE both participating and excluded; every participating ADE has an install record; its overlay path, entry point, recorded files and declared
   session-adapter files exist → **FAIL** otherwise. A recorded file changed since install is a **WARN**. A detected ADE that does not participate is a **WARN**, never a
   pass and never silently ignored. Without `.gtt/ade.json` the script keeps its single-ADE matrix (`gtt-check-adapter.sh <ade>`, unchanged) and `gtt-validate.sh`
   keeps its previous behaviour (SKIPPED in the catalog).
10. **Lifecycle** (the Bootstrap side of each operation; the CLI orchestrates):

    | Operation | Bootstrap contract |
    |---|---|
    | `init` | `gtt-ade.sh detect` → the human confirms participating ADEs → picks the Primary → `install` (dry run, then `--apply`) → `gtt-validate.sh`. |
    | `validate` | `gtt-check-adapter.sh` / `gtt-ade.sh validate`: every participating ADE PASS/FAIL, non-participating detected ADEs WARN; part of `gtt-validate.sh`. |
    | `status` | `gtt-status.sh` gains an *ADE integration* section (Primary, participating, excluded, detected-not-participating, per-ADE health); `gtt-ade.sh state [--json]`. |
    | `inspect` | `gtt-ade.sh list`, `state`, `owned` — operational visibility, no governance interpretation. |
    | `resume` | `gtt-domain/session.md` carries the same state and stays operational-only; it records **no** "last active ADE" (concurrent ADEs would overwrite each other's entry and no deterministic source exists). |
    | `freeze` | Unchanged: freeze governs L0/L1, not ADEs. `gtt-freeze.sh` still removes `gtt-domain/proposals/bootstrap/`, which is where a questionnaire working copy lives. |
    | `update` | `gtt-ade.sh update --from <catalog>` evaluates **every** participating overlay: refuses across a layout change (core migration first), plans UPDATE/ADD/STALE/RESTORE, never overwrites a locally modified file that also changed upstream (CONFLICT, nothing written), then validates. |
    | `clean` | `gtt-ade.sh remove <ade>… | --all` removes ledger files only (see 8), prunes directories it emptied, drops the ADE from the state, records it as excluded. |
    | `export --clean` | Uses `gtt-ade.sh owned --json` as the exact list of GTT integration surfaces to leave out of the delivery artifact. |

11. **Backward compatibility and migration.** A project without `.gtt/ade.json` keeps working unchanged (single-ADE matrix; `gtt-validate.sh` as before). It migrates with
    `gtt-ade.sh adopt` (dry run first): with exactly one overlay present and intact it records `primary = participating = that ADE` (`origin: adopted`, empty ledger, `excluded`
    empty); with several overlays present it **refuses to infer** and requires `--participating a,b --primary a`. No governed file is touched. An adopted ADE carries no fabricated
    install record. Authorization is never inferred where the state cannot establish it.
12. **The Initial Design Questionnaire is a Bootstrap artifact exposed through the Bootstrap contract.** It stays at
    `.gtt/scaffold/templates/gtt-initial-design-questionnaire.md` (not renamed, not moved, not duplicated). The manifest gains a `templates:` section declaring it (`id`, `path`,
    `use`, `when`, `materialize_to`, `becomes: source-material`, `scaffold`) and `.gtt/scripts/gtt-template.sh` (`list`, `show`, `materialize`, dry run unless `--apply`, never
    overwriting) lets a CLI discover, check compatibility (`scaffold` layout) and request a working copy at `gtt-domain/proposals/bootstrap/initial-design-questionnaire.md` — a governed-draft
    location an agent may always write and `gtt-freeze.sh` already cleans. Ownership: the Bootstrap owns the template, its contract and its evolution (its version is the Bootstrap's own); the CLI detects
    the need, requests the copy and orchestrates; the Primary ADE conducts the adaptive interview and populates it; the human provides and confirms. The CLI carries neither a copy nor the methodology.
13. **The questionnaire is source material, never governed architecture.** `[VACÍO]`, `[CONFLICTO]` and `[PROPUESTA]` stay distinguishable from confirmed decisions; a proposal is never written as a decision;
    an ADE inference is never a human decision. Once the human reviews it with Readiness `READY` or `READY_WITH_OPEN_ITEMS` it is the *source document* (Confirmation A): it is preserved verbatim as
    `SOURCE-BRIEF.md`, and the six governed context files are derived through the normal bootstrap steps and Confirmation B — an unresolved `[CONFLICTO]` is asked again and a `[PROPUESTA]` becomes context only if
    a recorded `Human decision` says so. A Minimum Viable Governed Design can therefore emerge without the human owning a finished design document, and without any step promoting anything autonomously.
14. **What does not change.** L0/L1 protection and the freeze regime; GTTGuard; artifact identity and the technical index (they only register the new Markdown); the Session Memory contract and every
    `.gtt/session-adapters/*.json`; the Human Promotion Boundary; ADR-001. The staged Codex/Copilot/Kiro **Session Memory** adapters stay staged — adopting them remains a separate governed promotion
    (`apply-session-adapters.sh`); that script now calls `gtt-ade.sh record` for the files it installs, so `clean` and `export --clean` keep a single ownership contract.

## Alternatives considered

| Option | Why it lost |
|---|---|
| Keep one overlay; let the CLI install extra overlays itself | The workaround the Solution Designer rejected: the Bootstrap and installed projects would disagree with the manifest, and the CLI would carry ADE-specific paths. |
| All participating ADEs equal, no Primary | The task requires one; without it nothing identifies who conducts guided workflows (the questionnaire) or which ADE a CLI launches. |
| A Primary with extra authority (leads, arbitrates, approves) | Introduces a second governance model and an ADE hierarchy. The Primary is a workflow identifier only. |
| Persist *detected* ADEs in the state | A stored observation is stale; detection is cheap and computed on demand. |
| Infer the participating set from overlays present, no state file | Cannot represent "excluded on purpose", the Primary, or what GTT installed; brings back guessing and would treat a host's own `.claude/` as governed. |
| State in the manifest | The manifest is the data-only description of *the* scaffold, shared with the catalog; per-project state belongs in a per-project file. |
| State under `gtt-domain/` | Makes a tooling setting a governed decision that needs an ADR to change; heavy, and authority would then attach to it. |
| `.gtt/ade.yaml` | Needs a YAML parser in the ADE-agnostic Core, and a hash ledger is machine-written, not hand-edited. |
| A second registry file beside the manifest, or extending `session-adapters/*.json` | Competing state; the session declarations are Session-Memory scoped and strictly schema-checked, and the manifest's `overlays:` already is the ADE list. |
| Clean by directory name (`rm -rf .claude .kiro`) | Destroys a host project's own ADE configuration; ownership must be recorded, not guessed. |
| Record a "last active ADE" in `session.md` | No deterministic source; concurrent ADEs would overwrite each other; it would grow a second memory. |
| The CLI carries the questionnaire (or a copy of its methodology) | Violates ownership: the Bootstrap owns the template, its contract and its evolution; the CLI would fork it. |
| Materialize the working copy at the project root | Pollutes the host root and is never cleaned; `gtt-domain/proposals/bootstrap/` is already agent-writable and removed at freeze. |
| Two ADRs (Multi-ADE, questionnaire) | Considered. One was chosen because both share the same machinery (manifest, `gtt-validate.sh`, docs, the bootstrap skill) and the same principle — the Bootstrap exposes contracts, the CLI consumes them; the sections above stay separable. |

## Consequences

Makes easy: governing a project where several ADEs work at once; telling, from one file and one command, which ADEs participate, which is Primary and whether each integration is intact; a CLI (`init`, `validate`,
`status`, `inspect`, `update`, `clean`, `export --clean`) that needs no ADE-specific path or questionnaire text; removing exactly what GTT installed and nothing else; starting a project with no design document without
improvising an interview; adding an ADE tomorrow by adding one `overlays:` entry and one session declaration.

Makes hard: a project now has one more state file to keep truthful; the Core has more code (`gtt_ade.py`, `gtt_manifest.py`, `gtt_template.py`) and a lenient reader for the manifest's flow-mapping subset; every place that said
"exactly one" changed (see *Affected context*); an installed project's `gtt-check-adapter.sh` behaves differently once `.gtt/ade.json` exists.

Locked in: one Primary ADE and it carries no authority; detection is never participation; `.gtt/ade.json` is written only by `gtt-ade.sh`; clean/export act only on the ledger; the questionnaire has one home
(`.gtt/scaffold/templates/`) and is source material; the CLI consumes Bootstrap contracts and holds no ADE logic or template copy.

## Risks

- **Weaker enforcement on non-Claude ADEs.** Only Claude Code has real-time hooks. Installing Kiro/Copilot/Codex overlays "governs" them by instructions plus CI (`gtt-check-protection.sh`), not by blocking. The
  docs and the registry (`enforcement:`) say so; "governed" is not "hard-blocked". Signal: a non-Claude agent editing a protected file locally and only being caught in CI.
- **"Primary" read as authority.** Mitigated by stating it in `AGENTS.md`, the glossary, `constraints.md` and this ADR; no script branches on it. Signal: any proposal or prompt that gives the Primary extra say.
- **`.gtt/ade.json` is not hook-protected.** The hooks do not block hand-edits of derived/state files under `.gtt/` (same as `.gtt/index/` and `.gtt/protection/`). `gtt-check-adapter.sh` fails on inconsistency, but a
  hand-edit that stays internally consistent (for example swapping the Primary) is not detected as tampering; it is only ever a workflow identifier, so the blast radius is confusion, not authority.
- **Ledger trust.** The hashes prove a file is unchanged since GTT wrote it, not who edited it. Adopted ADEs have no ledger, so clean/export deliberately keep their files until the human asserts ownership.
- **Manifest reader is not a YAML parser.** It handles exactly the manifest's single-line flow mappings and fails loudly on anything else (`ManifestError`), including a duplicate key; a future manifest that stops fitting the
  subset needs a deliberate change, not a silent misread.
- **Detection heuristics.** Path and binary signals can be wrong (a foreign `.claude/`; an ADE installed but unused). They only produce candidates; the human confirms.
- **`apply-session-adapters.sh` records via `gtt-ade.sh record`** (changed in this package). If the ADE does not participate or `.gtt/ade.json` is absent it only warns, and clean/export keep those files until they are recorded.
- **Shared `AGENTS.md`.** Codex, Kiro and Copilot read `AGENTS.md`; `codex` in the participating set is therefore declarative (its integration is the core entry point). A host project's own `AGENTS.md` is still a
  conflict under *Conflict policy*.
- **The questionnaire's 53 answer slots were pandoc fences** (`` ```{=html} `` around an HTML comment) that rendered as code; this package normalises them to plain Markdown comments (`<!-- ... -->`), changing neither wording nor semantics. The Bootstrap has no version number of its own beyond `scaffold.version` and the canon id, so template compatibility is expressed as the layout version.
- **Verification scope.** The engine was exercised by a rehearsal in a disposable copy (`rehearse-multi-ade.py`, Windows / Git Bash, Python 3.13). Nothing was run on Linux/macOS, and no Codex, Copilot or Kiro runtime was
  exercised; the `enforcement` values restate the existing compatibility matrix in `.gtt/docs/docs.md` and are documented, not runtime-verified. This ADR claims no more.

## Stack map delta

Exact rows this decision changes in `gtt-domain/context/stack.md`:

| Section | Row | Before | After |
|---|---|---|---|
| header | Governing ADRs | `ADR-001, ADR-003, ADR-004` | `ADR-001, ADR-003, ADR-004, ADR-005` |
| 5. Dependency rules | ADE registry and ADE state | *(absent)* | new row: `overlays:` in the manifest and `.gtt/ade.json` → may depend on `gtt_ade.py`; must not contain logic, be hand-edited, or grant an ADE authority |
| 5. Dependency rules | Bootstrap templates | *(absent)* | new row: `.gtt/scaffold/templates/` → may depend on `gtt_template.py`; must not be copied into a CLI or become governed context outside the governed process |
| 5. Dependency rules | note under the table | Core/adapter rule and Engine/domain rule | also the Multi-ADE rule (one governance model, several integration surfaces, one Primary; no ADE is authority) |
| 6. Map change log | new row | — | ADR-005 (below) |

Line to append to the map change log (existing rows are history and are left as they read):

| {{RATIFIED_ON}} | ADR-005 | Multi-ADE and the Initial Design Questionnaire as Bootstrap contracts: one overlay per participating ADE with exactly one Primary ADE (a workflow identifier with no authority); the ADE registry is `overlays:` in the manifest and the per-project choice is `.gtt/ade.json` (written only through `gtt-ade.sh`); the questionnaire is a Bootstrap-owned template (`templates:`, `gtt-template.sh`). Two dependency-rule rows added; no module boundary relaxed; the Core stays ADE-agnostic. Amends the overlay rows of ADR-003 and ADR-004. |

## Affected context

Staged as **full-file drafts** named `context-<name>-adr-005.md` in the proposals directory (the complete text each file must have after promotion), applied only by
`apply-ADR-005-bootstrap-integration-contracts.sh`, which shows the exact diff of each file before asking for ratification, checks each file's hash before the prompt and again after `yes`, and refuses to overwrite a file
that changed since the drafts were prepared:

- `context/stack.md` — the delta above.
- `context/architecture.md` — modules table (adapter row generalised; `.gtt/ade.json` and `.gtt/scaffold/` rows added), a **third governing rule** (Multi-ADE), two data-ownership bullets, and a *Known deviations* note on the enforcement asymmetry.
- `context/glossary.md` — *Scaffold* updated; new terms: Detected ADE, Participating ADE, Primary ADE, Integration surface, Initial Design Questionnaire.
- `context/constraints.md` — one line under *Explicitly out of scope*: no ADE/agent governance, hierarchy, voting or arbitration; the Primary holds no authority; integration surfaces are not authority.
- `context/principles.md` — three principles that rule something out (one governance model / many integration surfaces; the Bootstrap owns its contracts and the CLI consumes them; detection is not participation).
- `context/solution-vision.md` — unchanged.

Machinery and instruction files (not L0/L1) are staged under `adr-005-package/tree/` with the hash of the file each one replaces, and placed by the same script: `AGENTS.md`, the manifest, `gtt-check-adapter.sh`,
`gtt-validate.sh`, `gtt-status.sh`, the `gtt-bootstrap` skill, the questionnaire (slot syntax only), both READMEs, `installation`/`usage` (EN/ES), `docs.md`, `index.md`; new: `gtt-ade.sh`, `gtt_ade.py`, `gtt_manifest.py`, `gtt-template.sh`, `gtt_template.py`.
ADR-001, ADR-003 and ADR-004 are not edited: they remain the records of the decisions as they stood.
