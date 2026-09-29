# Architecture

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

The current architecture of this solution. Loaded on demand, not at session
start — so it can be longer than `constraints.md`, but every section should
still be something an agent would act on.

## Architectural style

Repository-native tooling: a set of CLI scripts (Bash) plus Python engines,
operating on declarative/documentary artifacts (Markdown, JSON) inside the
repository. Not a deployed runtime application.

## Modules and boundaries

| Module | Responsibility | May depend on | Must not depend on |
|---|---|---|---|
| `.gtt/scripts/` | Core operational/validation engine | — | any specific ADE |
| `.gtt/index/` | Artifact identity manifest + derived technical index | `.gtt/scripts/` | being hand-edited, or the derived index being treated as a source of truth |
| `.gtt/session-adapters/` | ADE integration declarations | — | containing GTT logic |
| `.claude/`, `.kiro/`, `.copilot/` (and equivalents) | ADE-specific integration | `.gtt/scripts/` (the Core service) | duplicating Core logic |
| `gtt-domain/context/` | Governed L0 context | — | direct agent writes once frozen |
| `gtt-domain/adr/` | Ratified architectural decisions | — | — |
| `gtt-domain/proposals/` | Proposals pending decision | — | — |
| `.gtt/protection/` | Derived GTTGuard state | `.gtt/scripts/gtt_guard.py` | being hand-edited |

Governing rule: **GTT Core provides the service; ADE adapters provide the
integration.** Adapters must not duplicate Core logic.

Second governing rule (ADR-004): **architectural authority stays in the domain, and executable GTT logic stays in the Engine.** `gtt-domain/` is the contextual, governed space over which GTT applies the method — `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md` and `.frozen`. `.gtt/` is the machinery, the state it derives (identity manifest, technical index, protection registry) and GTT's own documentation. Architectural authority (L0/L1) lives only in `gtt-domain/context/` and `gtt-domain/adr/`; nothing in `.gtt/` is a governed decision. The domain holds no executable GTT logic in operation: `gtt-domain/proposals/` holds governed drafts — proposals, ADR drafts, staged context files and promotion scripts — which the domain never executes and an agent never runs. The root entry points (`AGENTS.md`) and the ADE overlay are instructions to agents and belong to neither group. The code the project builds (L3) belongs to neither.

## Integration strategy

Integration happens through the filesystem: Bash/Python scripts and
Markdown/JSON files. ADE adapters invoke the Core Session Memory service
through `gtt-session-context.sh`. There is no network API and no messaging
between modules.

## Data model ownership

- The filesystem/Markdown is the source of truth for governed documents.
- `.gtt/index/artifacts.json` is authoritative only for `id ↔ path` identity.
- `.gtt/index/technical-index.json` is derived and reconstructible; never a
  source of truth.
- `.gtt/session-adapters/*.json` are declarations, not runtime evidence.
- `gtt-domain/session.md` is derived operational state, never authority or evidence.

## Deployment topology

Not applicable as a deployed service. GTT lives and runs inside the
repository; its scripts run locally or within the repository's own
CI/automation context.

## Known deviations

The Codex, GitHub Copilot, and Kiro ADE adapters are declared and
statically validated, but their runtime is not verified in this
environment. This must not be recorded as verified runtime support (see
`.gtt/session-adapters/*.json` → `verification.runtime`).

---
Governance: L0. Read-only for AI agents. Changes require an approved ADR.
