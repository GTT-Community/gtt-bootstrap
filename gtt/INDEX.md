# GTT Index

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Every file in this kit: what it is, who owns it, and when it enters an agent's
context. If you read one file to orient yourself, read this one.

This is the canonical map of the GTT governance surface — everything under
`gtt/`, plus the handful of files that stay at the project root because an
ADE or a human needs to find them there. See *Workspace hygiene* in
`README-GTT.md` for why the split is drawn where it is.

---

## Quick links

- [Change Request](CHANGE-REQUEST.md) — the only input door
- [Backlog](backlog.md) — Epics, Stories, current focus
- [Completion Report](GTT-COMPLETION.md) — durable bootstrap record
- [Context](context/) — L0, governed
- [ADRs](adr/) — L1, accepted decisions
- [Proposals](proposals/) — agent drafts awaiting review
- [Installation](INSTALLATION.md) — detailed setup procedures
- [Usage](USAGE.md) — the normal development loop
- [Docs](docs/) — human reference, methodology
- [Scripts](scripts/) — CI gates and freeze
- [AGENTS.md](../AGENTS.md) — portable core rules (root)
- [README-GTT.md](../README-GTT.md) — setup and tool support (root)

---

## Start here

| I want to... | Go to |
|---|---|
| Populate GTT for the first time in this project | drop your solution doc at the project root, any name (optional), then run the `gtt-bootstrap` skill |
| Ratify a freshly-bootstrapped context so it becomes read-only | `gtt/scripts/gtt-freeze.sh` |
| Change the stack, architecture, any directive, or an Epic/Story | `CHANGE-REQUEST.md` |
| See the development line — Epics, Stories, current focus | `backlog.md` |
| Check whether an L3 change (infra, a manifest) contradicts ratified architecture | `.claude/skills/gtt-drift-response/SKILL.md`, or wait for the `GTT DRIFT SIGNAL` warning |
| Protect a file, class, or method from autonomous agent edits | `.claude/skills/gtt-guard/SKILL.md` — add a `@GTTGuard` marker |
| Request a change to a GTTGuard-protected artifact | `.claude/skills/gtt-propose-change/SKILL.md` (form 5) |
| See what this system is, in one screen | `context/stack.md` |
| Understand why GTT works this way | `docs/DOCS.md` (Methodology) |
| Set this up in my project | `../README-GTT.md` |
| Run it on Kiro, Codex, or Copilot | `docs/DOCS.md` (Portability) |
| See which adapter I get for my ADE | `.claude/skills/gtt-bootstrap/SKILL.md` (step 0) or `../README-GTT.md` → *ADE adapters* |
| Resume work / see current state, regardless of which ADE picks it up | `gtt/scripts/gtt-status.sh` (regenerates `SESSION.md`) |
| Run every deterministic check before a release | `gtt/scripts/gtt-validate.sh` |
| Find a concept or section without loading whole documents | `gtt/scripts/gtt-query.sh` (or the `gtt-retrieve` skill) |
| Moved or renamed an artifact | `gtt/scripts/gtt-reconcile.sh` (dry-run), then `--apply` |

---

## Governed context — you own it, agents cannot write it once frozen

Pre-freeze (`gtt/.frozen` absent), `gtt/context/` and `gtt/adr/` are the one
exception: `gtt-bootstrap` writes them directly. See `gtt/.frozen` under
*Enforcement* below.

| File | Layer | Contains | Loads |
|---|---|---|---|
| `CHANGE-REQUEST.md` | — | Your standing request desk. The only input door | never |
| `SOURCE-BRIEF.*` | — | Your original design document, if one existed. Written once by `gtt-bootstrap`, then locked — not present if the context came entirely from conversation | never |
| `context/stack.md` | L0 | **The map**: stack table, components, topology, observability, dependency rules, drift signals, change log | on demand |
| `context/architecture.md` | L0 | Architecture in prose, module responsibilities | on demand |
| `context/constraints.md` | L0 | Hard limits. Kept short because it is always loaded | **always** |
| `context/principles.md` | L0 | Design principles in force | on demand |
| `context/solution-vision.md` | L0 | Purpose and non-goals | on demand |
| `context/glossary.md` | L0 | Terms whose meaning here differs from the usual | on demand |
| `adr/ADR-*.md` | L1 | Accepted decisions and their rationale | on demand |
| `adr/ADR-TEMPLATE.md` | L1 | Blank ADR | never |

## Development line — governed like architecture, but not L0

`backlog.md` is Epics, Stories, current focus, and next work. Structural
changes (new/removed Epic or Story, material scope or acceptance-criteria
change) go through `CHANGE-REQUEST.md` like an architectural decision. Story
status and focus updates during already-approved implementation are direct
edits — see *Backlog governance* in `AGENTS.md`. Precedence: L0 → ADR →
`backlog.md` → implementation; a Story never overrides governed context.

## Staging — agents write here

| File | Contains | Loads |
|---|---|---|
| `proposals/` | Agent drafts, and approved changes' promotion packages (ADR draft + affected context files + `apply-*.sh`), awaiting your review. Delete when resolved | never |

## Protection registry — derived, self-correcting

GTTGuard (see `AGENTS.md` → *Protected artifacts*) is a sibling to L0/L1,
not part of it — it protects L3 code you opt into protecting, not
`gtt/context/`/`gtt/adr/`.

| File | Contains | Loads |
|---|---|---|
| `protection/registry.yaml` | Every `@GTTGuard`-marked artifact, regenerated from source markers by `gtt-guard-sync.sh`. Derived, like a lockfile — never hand-edited; `gtt-check-protection.sh` fails the build if it drifts from a fresh regeneration | never |

## Session state — derived, on demand

Operational context for resuming work across ADEs, not architectural
authority, evidence, or a substitute for an ADR — see `AGENTS.md` →
*Session continuity*.

| File | Contains | Loads |
|---|---|---|
| `SESSION.md` | Snapshot of freeze/backlog-focus/proposals/change-request/ADRs/GTTGuard state, regenerated by `gtt-status.sh`. Derived — never hand-edited | never |

## Artifact identity and technical index — derived accelerator, identity manifest

See `docs/DOCS.md` → *Artifact identity and the technical index*. Ids survive
moves; reference an artifact as `[[ID]]`.

| File | Contains | Loads |
|---|---|---|
| `index/artifacts.json` | Identity manifest: id, type, path, former paths, aliases. Authoritative for identity; changed only by `gtt-index.sh` / `gtt-reconcile.sh` | never |
| `index/technical-index.json` | Documents, sections, concepts, relationships, provenance, authority, version. Derived — rebuildable, never authoritative; `gtt-check-integrity.sh` fails on a stale one | never (query it via `gtt-query.sh`) |

## Instructions — how agents behave

A project has exactly one adapter, matching the ADE that executed its
bootstrap — see `.claude/skills/gtt-bootstrap/SKILL.md` (step 0). The rows
below marked *(Claude Code adapter)* or *(Kiro adapter)* are mutually
exclusive with each other in an installed project; both are shown here
because this source repository is the catalog, not an installed project.

| File | Contains | Loads |
|---|---|---|
| `../AGENTS.md` | Portable core rules. Read natively by Kiro, Codex, and Copilot | **always** |
| `../.claude/CLAUDE.md` *(Claude Code adapter)* | Imports `AGENTS.md`, adds skill routing | **always** |
| `../.claude/rules/implementation.md` *(Claude Code adapter)* | Rules for `src/`, `tests/`, `lib/` | on matching files |
| `../.claude/rules/infrastructure.md` *(Claude Code adapter)* | Rules for `infra/`, `deploy/`, CI | on matching files |
| `../.kiro/steering/gtt-implementation.md` *(Kiro adapter)* | Kiro mirror of the above | on matching files |
| `../.kiro/steering/gtt-infrastructure.md` *(Kiro adapter)* | Kiro mirror of the above | on matching files |
| `../.copilot/copilot-instructions.md` *(Copilot adapter)* | Points Copilot at `AGENTS.md` and `gtt/` as the canonical source; no duplicated methodology. Not auto-loaded by Copilot at this path — see the note in `README-GTT.md` → *ADE adapters* | never (manual reference only, unless also mirrored to `.github/copilot-instructions.md`) |

## Procedures — load only when invoked

| File | Invoked when |
|---|---|
| `../.claude/skills/gtt-bootstrap/SKILL.md` | first time populating `context/`, pre-freeze, right after cloning the kit |
| `../.claude/skills/gtt-propose-change/SKILL.md` | processing a change request — architecture, context, conflict, a development-line (Epic/Story) change (form 4), or a change to a GTTGuard-protected artifact (form 5) |
| `../.claude/skills/gtt-adr/SKILL.md` | a change was approved and needs recording — drafts the ADR, the affected context files, and the `apply-ADR-NNN-<slug>.sh` promotion script together (architecture/context changes only — a backlog-only or GTTGuard-only change does not get an ADR) |
| `../.claude/skills/gtt-audit/SKILL.md` | checking whether context still matches the code, or whether `backlog.md` is reconciled with defined Epics/Stories — also the scheduled sweep counterpart to the drift detector below |
| `../.claude/skills/gtt-drift-response/SKILL.md` | a `GTT DRIFT SIGNAL` fired, `gtt-audit` found a divergence, or you're asking whether an L3 change contradicts ratified architecture — stages the same promotion-script package as `gtt-adr` |
| `../.claude/skills/gtt-retrieve/SKILL.md` | locating a concept/section or an artifact's relationships, or reconciling a move — through the technical index instead of scanning Markdown |
| `../.claude/skills/gtt-guard/SKILL.md` | marking or unmarking a `@GTTGuard`-protected file/class/method, then syncing the registry |

## Enforcement — costs zero context

| File | Does |
|---|---|
| `.frozen` | The regime marker. Absent = pre-freeze, `context/`/`adr/` are agent-writable. Present = governed, they're denied. Human-written only, via `gtt-freeze.sh`; versioned, not ignored |
| `scripts/gtt-freeze.sh` | Run by the Solution Designer to ratify: validates L0 has real content, then writes `.frozen` |
| `../.claude/settings.json` | Denies writes to governance machinery unconditionally; registers all hooks below |
| `../.claude/hooks/protect-l0.py` | `PreToolUse`. Regime-aware: blocks `context/`/`adr/`/`CHANGE-REQUEST.md`/`SOURCE-BRIEF.*` (the last two unconditionally) once frozen; blocks machinery paths always, via shell too. Exit 2 |
| `../.claude/hooks/protect-guard.py` | `PreToolUse`. Blocks an autonomous edit to a `HUMAN_APPROVAL` entry in `protection/registry.yaml` in real time — file-scope blocks the whole file, symbol-scope resolves the exact span live from disk and fails safe to whole-file if resolution is ambiguous. Exit 2 |
| `../.claude/hooks/detect-drift.py` | `PostToolUse`, governed regime only. Warns (never blocks) when a write matches the `gtt-drift-signals` block in `stack.md`. Deduplicated per session |
| `../.claude/hooks/notify-change-request.py` | `UserPromptSubmit`. Advisory only: notices a filled-in, unprocessed `CHANGE-REQUEST.md` and surfaces it in context — never analyzes or drafts. Deduplicated per session/content |
| `../.kiro/permissions.yaml` | Kiro's declarative equivalent of the machinery-path deny (1.0+) |
| `../.kiro/hooks/detect-drift.json` | Kiro mirror of `detect-drift.py` — same script, different trigger wiring |
| `scripts/gtt-check-stack.sh` | CI gate: an ADR without a map update fails the build; also checks referential integrity of ADR citations and warns if the drift-signals block is missing |
| `scripts/gtt-check-adapter.sh` | Deterministic validation of the ADE-adapter matrix: given a target ADE, asserts the installed files match exactly what that ADE should have and nothing else |
| `scripts/gtt-check-backlog.sh` | CI gate: fails on duplicate Epic/Story IDs or a status value outside the agreed vocabulary in `backlog.md`; warns on an Epic with no Stories yet |
| `scripts/gtt-check-protection.sh` | CI gate: fails if `protection/registry.yaml` drifts from a fresh regeneration, if an artifact/symbol/source fails to resolve, or if a protected artifact changed with no accompanying `gtt/proposals/`/`gtt/adr/` change (the one real-time backstop on Kiro, Codex, and Copilot) |
| `scripts/gtt-guard-sync.sh` / `scripts/gtt_guard.py` | Regenerates `protection/registry.yaml` from `@GTTGuard` markers in source; the shared, deterministic engine both this script and `protect-guard.py` import |
| `scripts/gtt-index.sh` / `scripts/gtt-reconcile.sh` / `scripts/gtt-query.sh` / `scripts/gtt_artifacts.py` | Register artifacts and rebuild the derived index / reconcile moves and rewrite links / section-level retrieval; the shared deterministic engine behind all three and the check below |
| `scripts/gtt-check-integrity.sh` | CI gate: fails on unreconciled moves, unregistered artifacts, duplicate logical identity, broken/old-path links, unresolved `[[ID]]`, or a stale technical index |
| `scripts/gtt-session-context.sh` | Session Memory Service entry point (ADE-independent): runs `gtt-status.sh`, verifies `SESSION.md`, prints an operational-only payload for an ADE adapter; fails loudly. See `docs/DOCS.md` → *Session memory boundary* |
| `scripts/gtt-check-session-adapter.sh` / `scripts/gtt_session_adapter.py` | Static conformance of a Session Memory ADE adapter against `docs/SESSION-ADAPTER-CONTRACT.md`, driven by `session-adapters/<ade>.json`; needs no ADE; PASS/FAIL/SKIPPED per item, runtime verification always SKIPPED and reported as declared. Run per adapter by `gtt-validate.sh` |
| `session-adapters/<ade>.json` | Declaration of one adapter (coverage N1/N2/N3, events, registration, verification, limitations). Adapter layer, not Core |
| `scripts/gtt-run-python.sh` | Launcher for ADE hooks: one Python 3 probe, then `exec`; a missing interpreter is a visible error, never a fallback after the script started |
| `scripts/gtt-status.sh` | Deterministic snapshot of current/governed/pending/proposed/blocked/frozen state, derived from repository artifacts; regenerates `SESSION.md` |
| `scripts/gtt-validate.sh` | Runs every `gtt-check-*.sh` above in sequence and reports pass/fail/cannot-determine; skips (not fails) the adapter check when this repo's own multi-adapter catalog state is detected |

## Human documentation — never loaded by any agent

| File | Contains |
|---|---|
| `INDEX.md` | This file |
| `../README-GTT.md` / `../README-GTT.es.md` | What GTT is, setup, tool support — the canonical entry point |
| `docs/SESSION-ADAPTER-CONTRACT.md` | Draft contract every Session Memory ADE adapter must meet; GTT Core is ADE-agnostic, adapters are integration-specific |
| `INSTALLATION.md` / `INSTALLATION.es.md` | Detailed installation procedures, manual and agent-assisted |
| `USAGE.md` / `USAGE.es.md` | The normal development loop, change requests, freeze model |
| `docs/DOCS.md` | Governance model, layers, enforcement planes, Claude Code vs Kiro vs Codex vs Copilot, upgrading from GTT v1 |

---

## The one flow that matters

```
CHANGE-REQUEST.md  ->  proposals/  ->  your review + `bash apply-*.sh`  ->  adr/ + context/stack.md
   you state intent      agent drafts        the Human Promotion Boundary       blocked for agents
   always writable       agent writable      your terminal, your decision
```

(All four paths above are relative to `gtt/`.) The promotion script the
agent stages in `proposals/` is never run by the agent — see `AGENTS.md` →
*Human Promotion Boundary*. Everything else in this kit exists to make that
flow cheap to run and hard to skip.

---

## What loads on every single session

Only these. Everything else is on demand or never.

- `.claude/CLAUDE.md` (or `AGENTS.md` on Kiro, Codex, and Copilot)
- `AGENTS.md`
- `gtt/context/constraints.md`

If `/context` shows anything else from `gtt/`, something is importing more than
it should.
