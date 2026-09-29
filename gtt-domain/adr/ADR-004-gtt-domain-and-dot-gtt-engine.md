# ADR-004 — `.gtt/` Engine and `gtt-domain/` governed domain

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

- Status: Accepted
- Date: 2026-09-29
- Approved by: Solution Designer (mgriott) - ratified by executing apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh on 2026-09-29
- Supersedes: ADR-003 (in part: its layout decisions — where the Engine, Project Governance and GTT documentation live; see Decision)

## Context

[[ADR-003]] restructured the scaffold into four layers — Engine in `gtt/`, Project Governance at the project root, GTT Documentation in `docs/`,
ADE overlay — declared once in `gtt/scaffold/manifest.yaml`. It kept [[ADR-001]]'s decision intact (governed context is the source of truth and is
write-protected after freeze) and changed only where things live.

Living with that layout shows three things:

1. **The governed subject is not one thing.** The project's governed state is seven root-level names (`context/`, `adr/`, `proposals/`,
   `backlog.md`, `change-request.md`, `session.md`, `.frozen`). To freeze it, protect it, back it up or exclude it, a tool has to enumerate
   seven paths, and nothing in the layout says that they belong together.
2. **GTT's footprint at the root of an adopting project is four generic directory names** (`docs/`, `context/`, `adr/`, `proposals/`), each of which
   a host project may already own for unrelated reasons; ADR-003 accepted that and handled it by instruction (report, never merge).
3. **GTT's own documentation sits in a layer of its own next to the governed state**, although it explains the method and does not define the project.

The Solution Designer therefore approved a design (2026-09-29) that separates **how the method works** from **what the method is applied to**, and gives
the second a name: `gtt-domain` — GTT-Method's definition of the project or domain it governs, the contextual space over which GTT applies the method.

`context/stack.md` §6 (*Map change log*) states the governing rule: *"Every row here corresponds to an accepted ADR. If an architectural change happened
without a row, the governance loop was skipped."* This change relocates every module of the map and changes what the protection hook matches, so it needs
an accepted ADR and a change-log row; AGENTS.md → *Human Promotion Boundary* independently requires the ADR draft to accompany a change to governed context
(six L0 files here). It reverses part of [[ADR-003]], which is dated 2026-09-28 and was ratified on 2026-09-29 — hours before this design was approved. That is
legitimate (decisions may be revised) but must be explicit.

## Decision

1. **Layout.** The scaffold is an Engine, a domain and an ADE overlay, plus the root entry points:

   | Group | Where | Members |
   |---|---|---|
   | **Engine** | `.gtt/` (was `gtt/`) | `index/`, `protection/`, `scaffold/` (`manifest.yaml`), `scripts/`, `session-adapters/`, **`docs/`** (was `docs/` at the root: GTT's own documentation) |
   | **Domain** | `gtt-domain/` | `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen` |
   | **ADE overlay** | `.claude/`, `.kiro/`, `.copilot/` | unchanged; exactly one per installed project |
   | **Entry points** | project root | `AGENTS.md`, `readme-gtt.md`, `readme-gtt.es.md`, `SOURCE-BRIEF.*` — unchanged (ADE discovery names, human-facing entry points) |

2. **`gtt-domain/` is the contextual, governed space over which GTT applies the method.** `gtt-domain/context/` says what the system is, `gtt-domain/adr/`
   records why, `gtt-domain/proposals/` holds governed drafts — what waits for a human decision — `gtt-domain/backlog.md` is the development line,
   `gtt-domain/session.md` is the derived resume-state and `gtt-domain/.frozen` marks the moment the domain became governed.
3. **Invariants: authority and logic stay apart.**
   (a) **Architectural authority (L0/L1) lives only in `gtt-domain/context/` and `gtt-domain/adr/`.** Nothing in `.gtt/` is a governed decision: its index and
   protection registry are derived, its documentation is reference, its scripts are logic.
   (b) **Executable GTT logic lives in `.gtt/`.** The domain holds none *in operation*: `gtt-domain/proposals/` holds governed **drafts** — proposals, ADR drafts,
   staged context files and promotion scripts — which the domain never executes and an agent never runs (a human does, under the Human Promotion Boundary).
   (c) The root entry points (`AGENTS.md`) and the ADE overlay are instructions to agents; they belong to neither group and are not architectural authority.
   (d) The code the project builds (L3) belongs to neither group; the domain governs it by reference (map, dependency rules, drift signals).
4. **[[ADR-001]]'s decision is unchanged**: governed context remains the source of truth and remains write-protected after freeze at the permission and hook
   layers — only the path it names changes, from `context/` to `gtt-domain/context/` (and likewise `adr/`, `proposals/`, `.frozen`). `.frozen` moves with its
   content byte-for-byte, so the project is never unfrozen by the move.
5. **Scaffold definition.** `.gtt/scaffold/manifest.yaml` remains the single declarative definition, at layout `version: 2`, with layers `engine` (documentation
   folded into it), `domain` and `overlay`.
6. **Collision policy.** If a host project already has `.gtt/` or `gtt-domain/` at its root, the bootstrap stops and reports the collision under AGENTS.md →
   *Conflict policy*; it never overwrites, merges or relocates the host's files. Enforcement plane: **instruction only** (`AGENTS.md`, the `gtt-bootstrap` skill);
   there is no deterministic collision check today. **Today** (the layout of [[ADR-003]]) the protection hook resolves paths against the project root and anchors the
   regime to `context/`, `adr/` and `proposals/`, and GTTGuard's marker scan skips `context adr proposals docs` at the root only and already skips every directory
   whose name starts with a dot. **The migration that realises this decision will** re-anchor the hook's regime directories, its always-writable directory and its
   freeze marker to `gtt-domain/context`, `gtt-domain/adr`, `gtt-domain/proposals` and `gtt-domain/.frozen`, and change GTTGuard's root-only exclusion to
   `gtt-domain`; `.gtt/` needs no change (dot-directory). After it, a host's own `src/context/`, `src/docs/` or `docs/` is neither blocked nor hidden from GTTGuard.
7. **Protection surface (unchanged in kind; only the paths move).** Under the freeze regime, `gtt-domain/context/` and `gtt-domain/adr/` are denied to agents once
   `gtt-domain/.frozen` exists. `gtt-domain/change-request.md`, `AGENTS.md`, `SOURCE-BRIEF.*` and the ADE machinery paths stay protected by filename or static
   deny. **`gtt-domain/proposals/` remains the one governed directory agents may write, under the existing rules** — drafts only; an agent never executes a
   promotion script staged there. **`.gtt/docs/` stays outside the freeze regime, exactly as `docs/` is today** (L2: editable with review), and `.gtt/index/`,
   `.gtt/protection/` and `gtt-domain/session.md` are derived and never hand-edited.
8. **What [[ADR-003]] decided and this keeps:** one canonical scaffold and ADEs only as overlays; root-anchored protection; the collision policy (now over two
   names instead of four); the naming exceptions (`AGENTS.md`, `ADR-*`, `PROPOSAL-*`, `SOURCE-BRIEF.*`, `CLAUDE.md`, `SKILL.md`); L0 text changing only through
   its ADR promotion. **What it supersedes:** the location of the Engine (`gtt/`), of Project Governance (project root) and of GTT documentation (`docs/`, a layer of
   its own). [[ADR-003]] itself is not edited: it remains the record of the layout as it stood.

## Alternatives considered

| Option | Why it lost |
|---|---|
| Keep the [[ADR-003]] layout | Leaves the governed subject as seven root names and four generic directory names at every adopter's root; Engine and domain are distinguished only by convention. |
| Put GTT's own documentation inside the domain (`gtt-domain/docs/`) | Rejected by the Solution Designer (Q1): the documentation explains the method, it does not define the project, so it belongs with the Engine. |
| Keep the Engine visible as `gtt/` and only add `gtt-domain/` | A dot-name marks the Engine as machinery and leaves the project root reading like the project; the discoverability cost of a hidden directory is accepted and mitigated by the visible root entry points. |
| Move the entry points or `SOURCE-BRIEF.*` into the domain | `AGENTS.md` and the READMEs are ADE-discovery and human-facing names, and `SOURCE-BRIEF.*` is protected by filename; all stay at the root (Q3, Q4). |

## Consequences

Makes easy: telling from a directory name whether a file is machinery (`.gtt/`) or governed subject (`gtt-domain/`); freezing, protecting, backing up or
excluding the domain as one path; a root that reads like the project; upgrading or removing the Engine without touching the domain, since GTT's documentation
travels with it; a collision surface of two names.

Makes hard: every path in every file changes a second time, right after [[ADR-003]] (identity, index, session adapters, hooks, docs, skills, READMEs); tools that skip
dot-directories no longer see the Engine or its documentation; any external configuration that hard-codes the old paths (for example branch rules on `gtt/**`
or `context/**`) must be updated.

Locked in: `gtt-domain/context/` and `gtt-domain/adr/` stay write-protected for agents after freeze; `.frozen` lives at `gtt-domain/.frozen`; the Engine is
`.gtt/` and includes GTT's documentation; `.gtt/scaffold/manifest.yaml` is the canonical scaffold definition (layout version 2), data only; the ADE never defines
the scaffold.

## Risks

- **`.gtt/` and, with it, GTT's documentation are hidden.** Signal: adopters not finding the documentation, or a tool silently skipping the Engine. Mitigation:
  `AGENTS.md` and the READMEs stay visible and link into `.gtt/docs/`.
- **Per-project records live in the Engine.** `.gtt/docs/gtt-completion.md` and `.gtt/docs/evidence.md` record this project next to method documentation. They are
  records, not authority, so invariant (a) holds; if they should live with the domain instead, that is a small follow-up decision, not a structural one.
- **Migration size and a second re-migration right after ADR-003.** Signal: a migration that needs hand-edits beyond the reviewed patches. Mitigation: the ADR-003
  migration engine, kept verbatim with a provenance file and checksums in the working package; a rehearsal on a disposable copy; and a roll-back-safe orchestrator.
- **Host-project collisions are handled by instruction, not by a deterministic check** (now over `.gtt/` and `gtt-domain/`). Follow-up: a scaffold conformance check.
- **The protection hook resolves paths against the project root** (`CLAUDE_PROJECT_DIR`, else the working directory); its command is a relative path, so a wrong
  working directory fails closed, as observed in ADR-003's session. Kiro, Codex and Copilot keep the limitation already documented: no real-time block, CI gate only.
- **Manifest drift.** If the manifest and the repository disagree, the repository wins; it is verified at apply time, not continuously.
- **Verification scope.** Nothing here is verified yet: the migration package that realises this decision does not exist and the L0 drafts were checked statically.
  Claude Code hooks have no live-session verification of the new anchors; the Kiro, Codex and Copilot overlays have no runtime verification. This ADR claims none.

## Stack map delta

Exact rows this decision changes in `stack.md` (today `context/stack.md`, after the migration `gtt-domain/context/stack.md`); "before" is the current text, "after" is the text at promotion:

| Section | Row | Before | After |
|---|---|---|---|
| header | Governing ADRs | `ADR-001` | `ADR-001, ADR-003, ADR-004` (ADR-003 was omitted when it was promoted; corrected here) |
| 1. Stack at a glance | Datastore (primary) | `gtt/index/artifacts.json` | `.gtt/index/artifacts.json` |
| 4. Observability | evidence pointer | `docs/evidence.md` | `.gtt/docs/evidence.md` |
| 5. Dependency rules | Core scripts | `gtt/scripts/` (Core) | `.gtt/scripts/` (Core) |
| 5. Dependency rules | ADE adapters | may depend on `gtt/scripts/` | may depend on `.gtt/scripts/` |
| 5. Dependency rules | session adapters | `gtt/session-adapters/` | `.gtt/session-adapters/` |
| 5. Dependency rules | index | `gtt/index/` → `gtt/scripts/gtt_artifacts.py` | `.gtt/index/` → `.gtt/scripts/gtt_artifacts.py` |
| 5. Dependency rules | protection | `gtt/protection/` → `gtt/scripts/gtt_guard.py` | `.gtt/protection/` → `.gtt/scripts/gtt_guard.py` |
| 5. Dependency rules | governed directories | `context/`, `adr/` | `gtt-domain/context/`, `gtt-domain/adr/` |
| 5. Dependency rules | proposals | `proposals/` | `gtt-domain/proposals/` |
| 5. Dependency rules | note under the table | restates the Core/adapter rule | also restates the authority/logic rule of `architecture.md` (architectural authority stays in the domain, executable logic in the Engine) |
| 6. Map change log | note under the table | `docs/docs.md`, `docs/session-adapter-contract.md` | `.gtt/docs/docs.md`, `.gtt/docs/session-adapter-contract.md` |
| 7. Drift signals | scope wording | "Paths outside the GTT-owned directories that carry architectural weight …" | "Paths outside the scaffold — the code the project builds and its infrastructure (`src/`, `infra/`, dependency manifests, …) — that carry architectural weight …"; the root entry points and the ADE overlay are not drift signals (AGENTS.md is protected by filename, the overlay is machinery) |

Plus the line to append to the map change log (the existing ADR-003 row is history and is left as it reads):

| 2026-09-29 | ADR-004 | `.gtt/` Engine and `gtt-domain/` governed domain: the Engine directory `gtt/` is renamed `.gtt/` and gains GTT's own documentation (`docs/` → `.gtt/docs/`); Project Governance (`context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen`) moves from the project root into `gtt-domain/`, the contextual space over which GTT applies the method. Rows of the dependency-rule table are re-pathed; architectural authority stays in the domain and executable logic in the Engine (the domain's `proposals/` holds governed drafts, not logic in operation); no module boundary is added, removed, or relaxed. Amends the layout of ADR-003. |

## Affected context

Staged as **full-file drafts** named `context-<name>-adr-004.md` in the proposals directory (the complete text each file must have after promotion) and applied only by
`apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh`, which sits next to them and shows the exact diff of each file before asking for ratification, checks each file's hash before the
prompt and again after `yes`, and refuses to overwrite a file that changed since the drafts were prepared. **The promotion script works against the migrated
layout** (`gtt-domain/context/…`): the migration that relocates the directories moves the L0 files but never edits their text, then calls this script as its
ratification step and cancels everything if ratification is declined. That migration package is a separate step and does not exist yet.

Per file (paths relative to `gtt-domain/`, i.e. `context/stack.md` means `gtt-domain/context/stack.md` in the migrated layout):

- `context/stack.md` — the delta above.
- `context/architecture.md` — the modules table re-pathed (8 rows), the data-model bullets and the known-deviations pointer re-pathed, and a **second governing
  rule** added after the Core/adapter rule: architectural authority (L0/L1) stays in the domain and executable GTT logic in the Engine; `gtt-domain/` is the
  contextual, governed space over which GTT applies the method; the domain's `proposals/` holds governed drafts (including promotion scripts) that neither the domain
  nor an agent executes; `AGENTS.md` and the ADE overlay are instructions to agents, in neither group; the code the project builds belongs to neither.
- `context/glossary.md` — existing entries re-pathed; the **Scaffold** entry updated; two terms added: **Engine** (`.gtt/`) and **Domain** (`gtt-domain`), both stated
  with the authority/logic distinction.
- `context/constraints.md` — the datastore bullet re-pathed (`.gtt/index/…`); nothing else changes. It is the file loaded into every session, so its import path
  changes with the migration.
- `context/solution-vision.md` — five path mentions re-pathed.
- `context/principles.md` — one mention, `session.md` → `gtt-domain/session.md`.

[[ADR-001]] and [[ADR-003]] are not edited: they remain the records of the decisions as they stood.
