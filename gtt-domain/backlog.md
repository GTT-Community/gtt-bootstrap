# Project Backlog

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> The project's living development line — Epics, Stories, and the work
> currently expected to be built. This is a development-planning artifact,
> not architecture: see *Precedence* below. It answers "what exists, what's
> next, what's blocked" — not "how may it be built" or "what decisions are
> authoritative."

**Last verified:** `2026-09-29` — run the `gtt-audit` skill to reconcile against defined requirements.

---

## Development Line

<what phase, release, or milestone this backlog currently represents — one or two sentences. Leave empty rather than inventing one.>

## Precedence

```text
Governed Context / L0
        v
ADR / governed decisions
        v
This backlog
        v
Implementation work
```

If a Story appears to contradict governed context or an accepted ADR, that
is a finding, not a resolution. Raise it through `gtt-domain/change-request.md` —
a Story never silently overrides architecture.

---

## Epics

Accepted by the Solution Designer on 2026-09-28 from
`gtt-domain/proposals/PROPOSAL-gtt-v2-1-backlog-epic-stories.md`. Every Story below
keeps `Status: Proposed` as drafted in that proposal — accepting the
Epic/Story into the backlog is a separate decision from choosing each
Story's real development status (Ready / In Progress / Done), which the
Solution Designer has not yet made explicitly.

### EPIC-001 — GTT v2.1 — Artifact Identity, Technical Index & Session Memory

**Status:** Proposed
**Goal:** Give GTT a stable artifact identity that survives moves, a derived and
verifiable technical index for targeted retrieval, and an ADE-agnostic Session
Memory Service with a checked adapter contract — without changing what any agent
may write and without making any derived artifact an authority.
**Implementation state:** implemented and shipped as GTT Core functionality
— see `.gtt/docs/docs.md` → *Artifact identity and the technical index* and
`.gtt/docs/session-adapter-contract.md`. Not recorded as a product ADR: this
capability is Core engineering, not a project-specific governed decision
(see *Virgin/Product* closure, 2026-09-28).

#### Stories

##### STORY-001 — Artifact Identity

- **Status:** Done
- **Priority:** High
- **Description:** A stable, path-independent identity for every Markdown artifact
  of the GTT kit, kept in `.gtt/index/artifacts.json`; references by `[[ID]]`.
- **Scope:** id, type, current path, former paths, aliases; ADR ids independent of
  directory; registration of new artifacts; duplicate-identity detection. Out of
  scope: identity for non-Markdown files, cross-repository references, version
  transitions.
- **Implementation state:** implemented in `.gtt/scripts/gtt_artifacts.py`,
  `gtt-index.sh`, `gtt-check-integrity.sh`.
- **Evidence:** `gtt-check-integrity.sh` passes on the current tree (part of
  `gtt-validate.sh`); `.gtt/index/artifacts.json`; `.gtt/docs/evidence.md`.
- **Acceptance Criteria:**
  - A file keeps its `id` across a path or directory change.
  - Two files that derive the same id are reported as a duplicate unless listed
    under `aliases`.
  - An unregistered artifact, an unresolved `[[ID]]`, and a link using a former
    path each fail `gtt-check-integrity.sh`.
  - Registering new artifacts is refused while a registered path is missing.
- **Dependencies:** None

##### STORY-002 — Repository Reconciliation

- **Status:** In Progress
- **Priority:** High
- **Description:** Detect that an artifact moved or was renamed, keep its
  identity, and repair references deterministically.
- **Scope:** `gtt-reconcile.sh` (dry-run default, `--apply`, `--map`,
  `--retire`); matching by git rename hint, then same derived identity, then
  content similarity; rewriting relative links including a moved file's own
  outgoing links; skipping frozen `gtt-domain/context/` and `gtt-domain/adr/` files. Out of
  scope: deciding an ambiguous match (a human does, via `--map`/`--retire`).
- **Implementation state:** implemented in `.gtt/scripts/gtt_artifacts.py` and
  `gtt-reconcile.sh`.
- **Evidence:** `.gtt/docs/evidence.md` (reconciliation dry-run against the real
  repository, 2026-09-28).
- **Acceptance Criteria:**
  - A moved artifact is reported as the same artifact with its former path kept in
    `history`, not as delete + create.
  - `--apply` rewrites references and ends with a passing
    `gtt-check-integrity.sh`.
  - An ambiguous or unmatched path is reported and never guessed.
  - With `gtt-domain/.frozen` present, no file under `gtt-domain/context/` or `gtt-domain/adr/` is
    modified by the tool.
- **Dependencies:** STORY-001

##### STORY-003 — Technical Index

- **Status:** Done
- **Priority:** Medium
- **Description:** A derived, rebuildable index for section-level retrieval.
- **Scope:** documents, sections, concepts, references, `supersedes`,
  provenance, authority, version; `gtt-index.sh`, `gtt-query.sh`, the
  `gtt-retrieve` skill; staleness check. Out of scope: any use of the index as a
  source of truth; semantic/vector retrieval.
- **Implementation state:** implemented.
- **Evidence:** `gtt-check-integrity.sh` fails on a stale index and passes on the
  current tree; `.gtt/index/technical-index.json`; `.gtt/docs/evidence.md`
  (reconstruction-determinism test, 2026-09-28).
- **Acceptance Criteria:**
  - Deleting the index and running `gtt-index.sh` reproduces it byte for byte.
  - A stale index fails `gtt-check-integrity.sh`.
  - `gtt-query.sh` returns a section location and reads only that span, warning
    when the file changed since indexing.
  - No document states the index is authoritative.
- **Dependencies:** STORY-001

##### STORY-004 — Session Memory Service

- **Status:** Done
- **Priority:** High
- **Description:** One ADE-independent entry point that regenerates and delivers
  operational session state, never as authority.
- **Scope:** `gtt-session-context.sh`, `gtt-run-python.sh`, `gtt-status.sh`,
  `gtt-domain/session.md` (with non-authority markers in its header), the boundary table
  in `.gtt/docs/docs.md`. Out of scope: working preferences; any ADE-specific
  mechanism.
- **Implementation state:** implemented.
- **Evidence:** `gtt-validate.sh` OK; `.gtt/session-adapters/claude.json` records
  real Claude Code sessions (startup and resume fired the hook and the agent
  quoted the payload); `.gtt/docs/evidence.md` (reproducibility cross-check against
  independent ground truth, 2026-09-28).
- **Acceptance Criteria:**
  - The service fails with a non-zero exit and a stderr message, never with
    partial context.
  - The payload and `gtt-domain/session.md` carry `operational-only`, `NOT authority`,
    `NOT evidence`, `NOT a decision record`, `NOT a grounding source`.
  - The chain names no ADE, hook event, or format.
  - `gtt-domain/session.md` is regenerable and never hand-edited.
- **Dependencies:** STORY-001

##### STORY-005 — ADE Adapter Contract and integration boundary

- **Status:** Done
- **Priority:** High
- **Description:** A contract every ADE adapter meets, declarations as data, and a
  static conformance check that needs no ADE.
- **Scope:** `.gtt/docs/session-adapter-contract.md`; `.gtt/session-adapters/*.json`;
  `gtt-check-session-adapter.sh`; the Claude adapter (installed); Codex,
  GitHub Copilot, Kiro adapters (staged). Out of scope: adopting the staged
  adapters (a governed matrix change), the IDE variant of Kiro, N2/N3 adapters.
- **Implementation state:** implemented, except the Claude adapter is the only
  one installed; the others remain staged.
- **Evidence:** `gtt-validate.sh` reports PASS for the four adapters (static)
  with the declared runtime shown alongside.
- **Acceptance Criteria:**
  - The check passes a conforming adapter and fails each contract violation.
  - Runtime verification is never reported as PASS by the check.
  - A declaration contains no key outside the schema.
  - Nothing claims runtime verification for an ADE that was not actually run.
- **Dependencies:** STORY-004
- **Notes:** Runtime for Codex, GitHub Copilot, and Kiro remains NOT VERIFIED.
  Promotion of staged adapters is a separate decision.

### EPIC-002 — Multi-ADE participation and the Initial Design Questionnaire

**Status:** Completed
**Goal:** Let one GTT governance model serve several ADEs at once (one Primary, no extra authority) and let a project without a design document start through a Bootstrap-owned,
ADE-guided questionnaire — with every contract owned by the Bootstrap and consumed, not duplicated, by the CLI.
**Implementation state:** implemented and ratified by ADR-005 (2026-09-29); see `.gtt/docs/evidence.md` for what was and was not verified (rehearsal on temporary copies only;
no installed project, no Linux/macOS, no Codex/Copilot/Kiro runtime).

#### Stories

##### STORY-006 — ADE registry and per-project ADE state

- **Status:** Done
- **Priority:** High
- **Description:** The manifest `overlays:` section as the ADE registry; `.gtt/ade.json` for participating, primary and excluded ADEs and the ledger of GTT-installed files; `gtt-ade.sh list|detect|state`.
- **Scope:** registry keys, state schema, manifest reader, detection as candidates only. Out of scope: ADE hierarchy, authority, agent voting or arbitration.
- **Implementation state:** implemented in `.gtt/scripts/gtt_ade.py`, `gtt_manifest.py`, `gtt-ade.sh`.
- **Evidence:** ADR-005; `.gtt/docs/evidence.md`.
- **Acceptance Criteria:**
  - Detection never writes and never makes an ADE participating.
  - Exactly one Primary, and it participates; an inconsistent state fails validation.
  - `.gtt/ade.json` is written only by `gtt-ade.sh`.
- **Dependencies:** STORY-005

##### STORY-007 — Multi-ADE lifecycle contract

- **Status:** Done
- **Priority:** High
- **Description:** `install`, `validate`, `status`, `inspect`, `resume`, `update`, `clean` and `export --clean` understand participating ADEs.
- **Scope:** `gtt-ade.sh install|update|remove|owned|set-primary`, state-driven `gtt-check-adapter.sh`, the ADE section in `gtt-status.sh`, `gtt-validate.sh`. Out of scope: the CLI itself.
- **Implementation state:** implemented.
- **Evidence:** ADR-005; `.gtt/docs/evidence.md`.
- **Acceptance Criteria:**
  - A missing or inconsistent participating integration FAILS; a detected non-participating ADE WARNs.
  - `update` never overwrites a locally modified file that also changed upstream.
  - `clean` and `export --clean` remove only ledger-recorded, unmodified files and never the host project's own ADE configuration.
  - Changing the Primary is a direct operation recorded in `.gtt/ade.json`.
- **Dependencies:** STORY-006

##### STORY-008 — Migration and ownership ledger

- **Status:** Done
- **Priority:** Medium
- **Description:** Single-ADE projects keep working and migrate with `gtt-ade.sh adopt`; installers record what they install (`gtt-ade.sh record`), including `apply-session-adapters.sh`.
- **Scope:** legacy matrix retained; adopt refuses to infer among several overlays; adopted ADEs carry no fabricated install record.
- **Implementation state:** implemented; the `apply-session-adapters.sh` record step was rehearsed piecewise only.
- **Evidence:** ADR-005; `.gtt/docs/evidence.md`.
- **Acceptance Criteria:**
  - A project without `.gtt/ade.json` validates exactly as before.
  - `adopt` touches no governed file.
  - Files installed by the session-adapter installer appear in `gtt-ade.sh owned`.
- **Dependencies:** STORY-006

##### STORY-009 — Initial Design Questionnaire as a Bootstrap contract

- **Status:** Done
- **Priority:** High
- **Description:** The existing questionnaire is declared under `templates:` and requested through `gtt-template.sh`; the Primary ADE conducts it; the reviewed copy becomes `SOURCE-BRIEF.md` (source material, never governed architecture).
- **Scope:** `gtt-template.sh list|show|materialize`, the bootstrap skill and `AGENTS.md` procedure, plain-comment answer slots. Out of scope: any CLI copy of the questionnaire; a second questionnaire.
- **Implementation state:** implemented; an ADE following the questionnaire's Operating Contract is instruction-plane only (NO EVIDENCE).
- **Evidence:** ADR-005; `.gtt/docs/evidence.md`.
- **Acceptance Criteria:**
  - Exactly one questionnaire exists, at its canonical path.
  - `materialize` never overwrites a filled copy.
  - `[VACÍO]`, `[CONFLICTO]` and `[PROPUESTA]` never map to a confirmed decision.
- **Dependencies:** STORY-005

---

## General Development Work

Work tracked here that is not tied to a specific Story.

- None

## Current Focus

What is actively being worked on right now.

- None

## Next Work

What comes after Current Focus.

- None

## Blocked

- None

---
Governance: adding or removing an Epic/Story, or materially changing its
scope or acceptance criteria, goes through `gtt-domain/change-request.md` ->
`gtt-domain/proposals/` -> Solution Designer decision — the same funnel as an
architecture change. Updating a Story's status, or the *Current Focus* /
*Next Work* / *Blocked* lists, as part of already-approved implementation
work does not need a change request. See `AGENTS.md` → *Backlog governance*
for the full rule and precedence relative to L0/ADRs.
