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
| `.claude/`, `.kiro/`, `.copilot/` (and equivalents) | ADE-specific integration: one overlay per participating ADE | `.gtt/scripts/` (the Core service) | duplicating Core logic, or being treated as governance authority |
| `.gtt/ade.json` | Per-project ADE state: participating, primary and excluded ADEs, and the ledger of files GTT installed | `.gtt/scripts/` (`gtt_ade.py`, its only writer) | being hand-edited; granting any ADE authority |
| `.gtt/scripts/gtt_provenance.py` | Reads provenance tags, the gap register, the source manifest and working agreements; one gate, status and query views | governed artifacts (read-only) | owning them, writing to the domain, or being treated as authority |
| `.gtt/scaffold/` | The scaffold manifest — including the ADE registry (`overlays:`) and the templates the Bootstrap owns (`templates:`) — and the templates themselves | — | containing logic |
| `gtt-domain/context/` | Governed L0 context | — | direct agent writes once frozen |
| `gtt-domain/adr/` | Ratified architectural decisions | — | — |
| `gtt-domain/proposals/` | Proposals pending decision | — | — |
| `.gtt/protection/` | Derived GTTGuard state | `.gtt/scripts/gtt_guard.py` | being hand-edited |

Governing rule: **GTT Core provides the service; ADE adapters provide the
integration.** Adapters must not duplicate Core logic.

Second governing rule (ADR-004): **architectural authority stays in the domain, and executable GTT logic stays in the Engine.** `gtt-domain/` is the contextual, governed space over which GTT applies the method — `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md` and `.frozen`. `.gtt/` is the machinery, the state it derives (identity manifest, technical index, protection registry) and GTT's own documentation. Architectural authority (L0/L1) lives only in `gtt-domain/context/` and `gtt-domain/adr/`; nothing in `.gtt/` is a governed decision. The domain holds no executable GTT logic in operation: `gtt-domain/proposals/` holds governed drafts — proposals, ADR drafts, staged context files and promotion scripts — which the domain never executes and an agent never runs. The root entry points (`AGENTS.md`) and the ADE overlay are instructions to agents and belong to neither group. The code the project builds (L3) belongs to neither.

Third governing rule (ADR-005): **one governance model, several ADE integration surfaces, one Primary ADE.** A project has one or more *participating* ADEs — the ones its human explicitly chose — each with its own overlay, and exactly one of them is the *Primary ADE*. Detection only ever produces candidates; it never makes an ADE installed, authorized, governed or participating. The Primary ADE identifies the principal environment of the project's workflow and holds no authority over any governed artifact: there is no ADE hierarchy, voting or arbitration. Instruction files and overlays (`AGENTS.md`, `.claude/`, `.kiro/`, `.copilot/`, `.codex/`, an ADE's memory or session history) are integration surfaces, never governance authority. The Bootstrap owns the contracts that describe this (the ADE registry, the per-project state, the ownership ledger, the questionnaire template); a CLI consumes them through `gtt-ade.sh` and `gtt-template.sh` and never invents an ADE-specific path or carries a copy of a Bootstrap template.

Fourth governing rule (ADR-006): **evidence, gaps and sources live in the governed artifacts and are only read by the Engine.** Governed context uses `[FUENTE]`, `[VACÍO]` and `[CONFLICTO]` with their references and never `[PROPUESTA]`; a BLOCKING gap refuses freeze; an OPEN gap is scoped, visible and authorises nothing; the source manifest (`gtt-domain/context/sources.md`, optional) orders sources by an unambiguous precedence without erasing a conflict; working agreements (`gtt-domain/working-agreements.md`, `.gtt/local/preferences.md`) sit below governed context and never override it. One gate, `gtt-check-provenance.sh`, checks all of it and grants no authority.

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
- The manifest's `overlays:` section is the ADE registry (data only); `.gtt/ade.json` is the per-project declaration of the participating and Primary ADEs plus the ledger of GTT-installed files. Neither is authority, and `.gtt/ade.json` is written only by `gtt-ade.sh`.
- The gap register is the `gtt-gaps` block of `stack.md`, the source manifest is `gtt-domain/context/sources.md`, team working agreements are `gtt-domain/working-agreements.md`; the technical index may locate them and is never their authority.
- The Initial Design Questionnaire lives once, at `.gtt/scaffold/templates/`; a filled copy is source material and never governed context by itself.
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

Real-time write blocking exists only on Claude Code. Every other participating ADE is governed by its instructions plus the CI gate (`gtt-check-protection.sh`); multi-ADE support does not change that, and the registry's `enforcement:` field states it per ADE. "Governed" is not "hard-blocked".

---
Governance: L0. Read-only for AI agents. Changes require an approved ADR.
