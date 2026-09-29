# ADR-003 — Scaffold restructure: four layers, one canonical scaffold

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

- Status: Accepted
- Date: 2026-09-28
- Approved by: Solution Designer (mgriott) - ratified by executing apply-ADR-003-scaffold-restructure.sh on 2026-09-29
- Supersedes: none

## Context

[[ADR-001]] establishes that the governed context is the source of truth and that
`gtt/context/` is write-protected for agents "at the permission and hook layers, not
merely by instruction". It also fixes where that context lives: everything GTT owns sits
under `gtt/` — the Engine (`scripts/`, `index/`, `protection/`, `session-adapters/`), the
project's governed state (`context/`, `adr/`, `proposals/`, `backlog.md`,
`CHANGE-REQUEST.md`, `SESSION.md`, `.frozen`) and GTT's own documentation (`INDEX.md`,
`INSTALLATION*.md`, `USAGE*.md`, `docs/`, `GTT-COMPLETION.md`, `EVIDENCE.md`).

That mix has three costs, all visible in the current L0:

1. **The map encodes the mix.** `context/architecture.md` (*Modules and boundaries*) and
   `context/stack.md` §5 (*Dependency rules*) list `gtt/context/`, `gtt/adr/` and
   `gtt/proposals/` as modules of the same directory as the Engine. There is no physical
   boundary between what GTT *is* and what a project *governs with it*.
2. **There is no single scaffold definition.** The layout is restated in prose in
   `AGENTS.md`, both READMEs, the installation and usage guides and the bootstrap skill. A
   future `gtt init` has nothing declarative to consume, and the ADE adapters risk each
   being read as defining a scaffold of their own.
3. **Protection addresses a long, mixed path.** The freeze regime is keyed on
   `gtt/(context|adr)/` and `gtt/.frozen`, so the control plane is coupled to the
   Engine's directory.

`context/stack.md` §6 (*Map change log*) states the governing rule: *"Every row here
corresponds to an accepted ADR. If an architectural change happened without a row, the
governance loop was skipped."* Relocating the map's modules changes the map, so it needs
an accepted ADR and a change-log row. AGENTS.md → *Human Promotion Boundary* independently
requires an ADR draft to accompany any change to governed context, and this change edits
five L0 files (see *Affected context*).

Finally, the target structure places generic directory names (`docs/`, `context/`, `adr/`,
`proposals/`) at the root of a host project, where they can already exist for unrelated
reasons; that trade-off must be decided, not discovered.

## Decision

GTT's scaffold has four layers, declared once in `gtt/scaffold/manifest.yaml` and physically
separated:

| Layer | Where | Contents |
|---|---|---|
| **Engine** | `gtt/` | `scripts/`, `index/`, `protection/`, `session-adapters/`, `scaffold/manifest.yaml` |
| **Project Governance** | project root | `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md` (derived), `.frozen` |
| **Documentation** | `docs/` | `index`, `installation`, `usage`, `gtt-completion`, `evidence`, `docs`, `session-adapter-contract` |
| **ADE overlay** | `.claude/` `.kiro/` `.copilot/` | exactly one per installed project; contributes integration only |

The scaffold is one and canonical: ADEs add an overlay to it and never define a scaffold of
their own, and adapters keep no GTT logic. [[ADR-001]]'s decision is unchanged — governed
context remains the source of truth and remains write-protected after freeze at the
permission and hook layers — only the **path** it names changes, from `gtt/context/` to
`context/` (and likewise `gtt/adr/`, `gtt/proposals/`, `gtt/.frozen`). `.frozen` moves with
its content byte-for-byte, so the project is never unfrozen by the move.

**Collision policy.** If a host project already has any scaffold name at its root — `docs/`,
`context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen` —
the bootstrap stops and reports the collision under AGENTS.md → *Conflict policy*. It never
overwrites, merges or relocates the host's files. Enforcement plane: **instruction only**
(`AGENTS.md` and the `gtt-bootstrap` skill); there is no deterministic collision check yet.
What *is* mechanical: the protection hook and GTTGuard's marker scan are anchored to the
project root, so a host's own `src/context/` or `src/docs/` is neither blocked nor hidden
from GTTGuard.

Entry points stay at the root (`AGENTS.md`, `readme-gtt.md`, `readme-gtt.es.md`).
Names the scaffold defines are lowercase; `AGENTS.md`, `ADR-*`, `PROPOSAL-*`, `SOURCE-BRIEF.*`,
`CLAUDE.md` and `SKILL.md` follow an external or established convention and are listed under
`naming.exceptions` in the manifest.

## Alternatives considered

| Option | Why it lost |
|---|---|
| Keep everything under `gtt/` (status quo) | Leaves Engine, governed state and documentation physically mixed; a `gtt init` would have to distinguish layers by file name. |
| One scaffold per ADE | Duplicates structure and invites GTT logic inside adapters; contradicts *GTT Core provides the service; ADE adapters provide the integration*. |
| Namespace the governed state under a single new directory to avoid generic-name collisions | Adds a wrapper directory that the target structure specified for this change deliberately does not have; the collision trade-off is accepted and handled by the collision policy instead. |
| Apply the relocation as a mechanical edit with no ADR | Leaves `stack.md` §6's rule unmet: the map's module rows change without a corresponding accepted ADR and change-log row. Declining ratification cancels the whole operation instead. |

## Consequences

Makes easy: reading the layer of any file from its directory name alone; a `gtt init` that
consumes one declarative scaffold; a protection layer keyed on short, root-anchored paths;
moving between ADEs by swapping only the overlay.

Makes hard: adopting GTT into a host project that already uses `docs/`, `context/`, `adr/` or
`proposals/` at its root — it now requires a human conflict decision; any external tooling that
hard-codes the old paths (for example branch-protection rules on `gtt/**`) must be updated.

Locked in: `context/` and `adr/` stay write-protected for agents after freeze; `.frozen` lives
at the project root; `gtt/scaffold/manifest.yaml` is the canonical scaffold definition and is
data only — it describes the repository and never overrides it; the ADE never defines the
scaffold.

## Risks

- **Host-project collisions** are handled by instruction, not by a deterministic check. Signal:
  bootstrap conflict reports on `docs/`/`context/`/`adr/` becoming routine, or a collision that
  slipped through. Follow-up: a scaffold conformance check.
- **The protection hook now resolves paths against the project root** (`CLAUDE_PROJECT_DIR`, else
  the working directory). Its command is a relative path, so a wrong working directory makes the
  hook fail closed rather than open — observed on 2026-09-28. Signal: an unexplained hook error
  that blocks every tool call. Kiro, Codex and Copilot keep the same limitation already documented
  for the two-regime paths: no real-time block, CI gate only.
- **Manifest drift.** If the manifest and the repository disagree, the repository wins. It is
  verified only at apply time, not continuously. Signal: `gtt/scaffold/manifest.yaml` naming a path
  that does not exist.
- **Installed projects on the old layout** are not migrated by this decision; the `gtt-bootstrap`
  skill detects both earlier layouts and stops to ask. Signal: a project whose `gtt/context/`
  still exists alongside a root `context/`.
- **Verification scope.** Static checks and a hook battery were run on a throw-away clone;
  Claude Code hooks have not been exercised in a live session after the move, and the Kiro, Codex
  and Copilot overlays have no runtime verification. This ADR claims none.

## Stack map delta

Exact rows this decision changes in `context/stack.md` (paths as they read *after* promotion;
"before" shows the path as it read in `gtt/context/stack.md`).

| Section | Row | Before | After |
|---|---|---|---|
| 4. Observability | evidence pointer | `` `gtt/EVIDENCE.md` `` | `` `docs/evidence.md` `` |
| 5. Dependency rules | governed directories | `` `gtt/context/`, `gtt/adr/` `` \| — \| direct agent writes once frozen | `` `context/`, `adr/` `` \| — \| direct agent writes once frozen |
| 5. Dependency rules | proposals | `` `gtt/proposals/` `` \| — \| — | `` `proposals/` `` \| — \| — |
| 6. Map change log | note under the table | `Empty: no ADR has changed this map. …` and paths `gtt/docs/DOCS.md`, `gtt/docs/SESSION-ADAPTER-CONTRACT.md` | `No other ADR has changed this map. …` and paths `docs/docs.md`, `docs/session-adapter-contract.md` |
| 7. Drift signals | scope wording | "Paths outside gtt/ that carry architectural weight …" | "Paths outside the GTT-owned directories that carry architectural weight …" |

Plus the line to append to the map change log:

| 2026-09-28 | ADR-003 | Scaffold restructure: Project Governance (`context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen`) moves from `gtt/` to the project root; GTT Documentation moves to `docs/`; `gtt/` keeps only the Engine and gains `scaffold/manifest.yaml`. Rows of the dependency-rule table are re-pathed; no module boundary is added, removed, or relaxed. |

## Affected context

Staged as **full-file drafts** `proposals/context-<name>-adr-003.md` (the complete text each file must have
after promotion) and applied only by `apply-ADR-003-scaffold-restructure.sh`, which shows the
exact diff of each file before asking for ratification and refuses to overwrite a file that
changed since the drafts were prepared. The migration script
(`apply-scaffold-restructure.sh`) moves `gtt/context/` to `context/` but never edits its text; it
calls the ADR script as its ratification step and cancels everything if ratification is declined.
Per file:

- `context/stack.md` — the delta above.
- `context/architecture.md` — *Modules and boundaries*: rows `gtt/context/`, `gtt/adr/`,
  `gtt/proposals/` become `context/`, `adr/`, `proposals/`. No module is added or removed.
- `context/glossary.md` — existing entries re-pathed to the new locations; new term
  **Scaffold** (source: `gtt/scaffold/manifest.yaml`; `AGENTS.md` → *Required workspace*).
- `context/solution-vision.md` — five path mentions re-pathed (ADR-001 reference,
  `docs/docs.md`, `docs/session-adapter-contract.md`, `context/`, `context/constraints.md`).
- `context/principles.md` — one mention, `SESSION.md` → `session.md`.

`context/constraints.md` is unchanged. [[ADR-001]] is not edited: it remains the record of the
path decision as it stood, and this ADR is the record of its relocation.
