# Project Backlog

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> The project's living development line — Epics, Stories, and the work
> currently expected to be built. This is a development-planning artifact,
> not architecture: see *Precedence* below. It answers "what exists, what's
> next, what's blocked" — not "how may it be built" or "what decisions are
> authoritative."

**Last verified:** `2026-09-28` — run the `gtt-audit` skill to reconcile against defined requirements.

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
