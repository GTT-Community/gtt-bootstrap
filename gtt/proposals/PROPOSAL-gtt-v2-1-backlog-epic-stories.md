# Proposed Backlog Change — GTT v2.1 Epic and Stories

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

**Status: Draft — not a decision.** Requires Solution Designer approval.

```text
Proposed Backlog Change

Kind: new Epic + 5 new Stories (development line), describing work that is
      ALREADY IMPLEMENTED and awaiting human ratification
Epic/Story ID: EPIC-001, STORY-001 … STORY-005 (proposed numbering; not assigned)
Current state: gtt/backlog.md defines no Epics or Stories (only the EPIC-000
               illustration inside a code block)
Suggested change: add the block in "Backlog-ready block" below
Reason: development on this capability began without an Epic/Story in the
        backlog, contrary to AGENTS.md → Backlog governance ("establish the
        applicable Epic/Story before development work"). This regularises the
        record; it does not claim the work was approved.
Contradicts governed context or an ADR?: no. gtt/context/ is template
        placeholders and ADR-001 is unaffected. Depends on the draft ADR-002.
Impact: none on code. Adds development-line entries only.
Risk: presenting implemented work as accepted. Mitigated: every Story is
      Status: Proposed and carries a separate "Implementation state" line.
Status: Requires Solution Designer approval
```

**Supersedes** the earlier draft backlog block in
`PROPOSAL-artifact-identity-followups.md` §2c (an Epic limited to Session Memory
across ADEs, with five differently scoped Stories). Do not apply both: they reuse
the same ids.

## Ground rules used to write this

- Only what exists in the repository. Nothing here describes future work as done.
- Story `Status` uses the backlog's vocabulary and stays `Proposed`; `Done`,
  `Accepted`, and `Ratified` are deliberately not used because none has happened.
- "Implementation state" is a separate, factual line: what exists, and whether it
  is committed. State as of preparation: commit `81bf8df` (*Artifact Identity +
  Technical Index*) holds the identity/index/reconcile/query scripts, both index
  files, the Claude adapter and its registration, and the first Session Memory
  wrapper. The adapter contract, its check, the declarations, the staged
  adapters, and the ADE-neutral clean-up of the Core were **uncommitted** when
  this package was prepared.
- Evidence is cited by where it lives; the evidence register and its limits are
  in `GOVERNANCE-PACKAGE-gtt-v2-1.md`.

## Backlog-ready block

```markdown
### EPIC-001 — GTT v2.1 — Artifact Identity, Technical Index & Session Memory

**Status:** Proposed
**Goal:** Give GTT a stable artifact identity that survives moves, a derived and
verifiable technical index for targeted retrieval, and an ADE-agnostic Session
Memory Service with a checked adapter contract — without changing what any agent
may write and without making any derived artifact an authority.
**Implementation state:** implemented; not ratified. Decision record: draft
ADR-002 (Draft — not a decision).

#### Stories

##### STORY-001 — Artifact Identity

- **Status:** Proposed
- **Priority:** High
- **Description:** A stable, path-independent identity for every Markdown artifact
  of the GTT kit, kept in `gtt/index/artifacts.json`; references by `[[ID]]`.
- **Scope:** id, type, current path, former paths, aliases; ADR ids independent of
  directory; registration of new artifacts; duplicate-identity detection. Out of
  scope: identity for non-Markdown files, cross-repository references, version
  transitions.
- **Implementation state:** implemented in `gtt/scripts/gtt_artifacts.py`,
  `gtt-index.sh`, `gtt-check-integrity.sh`; 37 artifacts registered before this
  package's three documents were added (the count grows with the kit). Committed
  in `81bf8df` with a later, uncommitted change that removed ADE-named id
  prefixes (manifest and index verified byte-identical afterwards).
- **Evidence:** `gtt-check-integrity.sh` passes on the current tree (part of
  `gtt-validate.sh`); `gtt/index/artifacts.json`. Duplicate-identity and
  unresolved-reference detection were exercised on throwaway copies during
  development — **not persisted** in the repository.
- **Acceptance Criteria:**
  - A file keeps its `id` across a path or directory change.
  - Two files that derive the same id are reported as a duplicate unless listed
    under `aliases`.
  - An unregistered artifact, an unresolved `[[ID]]`, and a link using a former
    path each fail `gtt-check-integrity.sh`.
  - Registering new artifacts is refused while a registered path is missing.
- **Dependencies:** None
- **Notes:** Open questions from the source design (alias representation beyond
  a path list, cross-repository references, version transitions) are not addressed.

##### STORY-002 — Repository Reconciliation

- **Status:** Proposed
- **Priority:** High
- **Description:** Detect that an artifact moved or was renamed, keep its
  identity, and repair references deterministically.
- **Scope:** `gtt-reconcile.sh` (dry-run default, `--apply`, `--map`,
  `--retire`); matching by git rename hint, then same derived identity, then
  content similarity; rewriting relative links including a moved file's own
  outgoing links; skipping frozen `gtt/context/` and `gtt/adr/` files. Out of
  scope: deciding an ambiguous match (a human does, via `--map`/`--retire`).
- **Implementation state:** implemented in `gtt/scripts/gtt_artifacts.py` and
  `gtt-reconcile.sh`; committed in `81bf8df`.
- **Evidence:** the code. A plain `mv` of an ADR was reconciled with identity and
  links preserved, on a throwaway copy — **not persisted**. The content-similarity
  path and the frozen-file skip path have **not been exercised**.
- **Acceptance Criteria:**
  - A moved artifact is reported as the same artifact with its former path kept in
    `history`, not as delete + create.
  - `--apply` rewrites references and ends with a passing
    `gtt-check-integrity.sh`.
  - An ambiguous or unmatched path is reported and never guessed.
  - With `gtt/.frozen` present, no file under `gtt/context/` or `gtt/adr/` is
    modified by the tool.
- **Dependencies:** STORY-001
- **Notes:** Persisting these scenarios as repeatable tests is the main gap.

##### STORY-003 — Technical Index

- **Status:** Proposed
- **Priority:** Medium
- **Description:** A derived, rebuildable index for section-level retrieval.
- **Scope:** documents, sections, concepts, references, `supersedes`,
  provenance, authority, version; `gtt-index.sh`, `gtt-query.sh`, the
  `gtt-retrieve` skill; staleness check. Out of scope: any use of the index as a
  source of truth; semantic/vector retrieval.
- **Implementation state:** implemented; committed in `81bf8df`. Before this
  package's three documents were added, the index held 37 documents, 362
  sections, 332 concepts (it is rebuilt, so these figures move).
- **Evidence:** `gtt-check-integrity.sh` fails on a stale index and passes on the
  current tree; `gtt/index/technical-index.json`; `gtt/docs/DOCS.md` →
  *Artifact identity and the technical index*.
- **Acceptance Criteria:**
  - Deleting the index and running `gtt-index.sh` reproduces it byte for byte.
  - A stale index fails `gtt-check-integrity.sh`.
  - `gtt-query.sh` returns a section location and reads only that span, warning
    when the file changed since indexing.
  - No document states the index is authoritative.
- **Dependencies:** STORY-001
- **Notes:** Concepts come from headings and glossary terms only. Committing the
  index means every Markdown edit needs a `gtt-index.sh` run. No CI runs the gate.

##### STORY-004 — Session Memory Service

- **Status:** Proposed
- **Priority:** High
- **Description:** One ADE-independent entry point that regenerates and delivers
  operational session state, never as authority.
- **Scope:** `gtt-session-context.sh`, `gtt-run-python.sh`, `gtt-status.sh`,
  `gtt/SESSION.md` (with non-authority markers in its header), the boundary table
  in `gtt/docs/DOCS.md`. Out of scope: working preferences; any ADE-specific
  mechanism.
- **Implementation state:** implemented. The wrapper and Claude adapter are in
  `81bf8df`; the removal of ADE names from the chain and the marker header are
  uncommitted at preparation time.
- **Evidence:** `gtt-validate.sh` OK; `gtt/session-adapters/claude.json` records
  real Claude Code sessions (startup and resume fired the hook and the agent
  quoted the payload). A search found no ADE name in the three chain scripts.
  Failure paths (no Python, broken engine) were exercised on throwaway copies —
  **not persisted**.
- **Acceptance Criteria:**
  - The service fails with a non-zero exit and a stderr message, never with
    partial context.
  - The payload and `SESSION.md` carry `operational-only`, `NOT authority`,
    `NOT evidence`, `NOT a decision record`, `NOT a grounding source`.
  - The chain names no ADE, hook event, or format.
  - `SESSION.md` is regenerable and never hand-edited.
- **Dependencies:** STORY-001 (identity/index state appears in the snapshot)
- **Notes:** On resume the hook fires but delivery cannot be told apart from the
  resumed transcript.

##### STORY-005 — ADE Adapter Contract and integration boundary

- **Status:** Proposed
- **Priority:** High
- **Description:** A contract every ADE adapter meets, declarations as data, and a
  static conformance check that needs no ADE.
- **Scope:** `gtt/docs/SESSION-ADAPTER-CONTRACT.md`; `gtt/session-adapters/*.json`;
  `gtt-check-session-adapter.sh`; the Claude adapter (installed); Codex,
  GitHub Copilot, Kiro adapters (staged); the staged promotion script. Out of
  scope: adopting the staged adapters (a governed matrix change), the IDE variant
  of Kiro, N2/N3 adapters.
- **Implementation state:** implemented and **uncommitted** at preparation time,
  except the Claude adapter (`81bf8df`). Staged adapters are not installed.
- **Evidence:** `gtt-validate.sh` reports PASS for the four adapters (static) with
  the declared runtime shown alongside. A mutation suite (exit 2, hidden stderr,
  swallowed failure, duplicated logic, stripped marker, wrong event, unreferenced
  service, overclaimed event, missing event, logic in a declaration) made the check
  fail every time on a throwaway copy — **the suite is not stored in the
  repository**.
- **Acceptance Criteria:**
  - The check passes a conforming adapter and fails each contract violation.
  - Runtime verification is never reported as PASS by the check.
  - A declaration contains no key outside the schema.
  - Nothing claims runtime verification for an ADE that was not actually run.
- **Dependencies:** STORY-004
- **Notes:** Runtime for Codex, GitHub Copilot, and Kiro is **NOT VERIFIED**
  (Codex: hook approval by the user required; Copilot: verification requires an
  interactive session; Kiro: not installed). Promotion of staged adapters is a
  separate decision.
```
