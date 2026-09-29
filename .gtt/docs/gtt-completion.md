# GTT Bootstrap — Completion Report

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> The durable record of what `gtt-bootstrap` did, and the outcome of any
> later re-run (an ADE/adapter switch, a migration, a re-freeze). Not a
> decision log for architecture — that is `gtt/adr/`. Not the development
> line — that is `gtt/backlog.md`. This file answers one question: *did the
> GTT workspace actually get set up correctly, and what does a human still
> need to do about it?*

---

## Entry 2026-09-28 — GTT v2.1 context Bootstrap + freeze

```text
GTT Bootstrap completed

Created:
- gtt/context/{stack,architecture,principles,constraints,solution-vision,glossary}.md
  populated from a direct interview with the Solution Designer (2026-09-28).
- gtt/EVIDENCE.md (reproducible technical-evidence log).
- gtt/.frozen.

Preserved:
- AGENTS.md, gtt/backlog.md structure, all existing gtt/proposals/ history,
  ADR-001, the .claude/.kiro/.copilot adapter files already present in this
  catalog repository.

Conflicts:
- None. No existing file was overwritten without the Solution Designer's
  explicit instruction in this session.

Source:
- This repository is the GTT Bootstrap catalog itself (not a host project
  being bootstrapped from an external source document); context values come
  from the Solution Designer's direct answers, not an inferred source brief.

Detected ADE:
- Claude Code (this session).

Adapter installed:
- Claude Code (.claude/).

Adapters excluded:
- None excluded by this session's action - this repository is the
  multi-adapter catalog (.claude/, .kiro/, .copilot/ all legitimately
  present); gtt-check-adapter.sh's own design SKIPs the single-adapter
  matrix check here for exactly that reason ("0 of 4 declared adapters
  match this workspace - catalog repo or ambiguous").

Native support:
- yes - Claude Code: SessionStart hook wired in .claude/settings.json,
  runtime-verified (startup, resume) per gtt/session-adapters/claude.json
  and this session's own live hook firings.

Backlog:
- defined - reconciled: yes (EPIC-001 + STORY-001..005 applied to
  gtt/backlog.md 2026-09-28; gtt-check-backlog.sh passes; Story statuses set
  from actual session evidence, not from the proposal's claims).

Context confirmation:
- confirmed - all 6 required gtt/context/ files answered directly by the
  Solution Designer; grep for template placeholders returns empty.

Freeze:
- executed - gtt/.frozen written 2026-09-28T17:18:49Z, "Frozen by: griott".

Protection verification:
- passed - gtt-check-protection.sh OK; post-freeze L0/L1 protection verified
  LIVE (see *Protection post-freeze* below), including a real gap found and
  fixed during this same closure (Windows path normalisation + missing
  PowerShell coverage in .claude/hooks/protect-l0.py and protect-guard.py).

CI gate:
- configured - gtt-validate.sh aggregates gtt-check-{backlog,protection,
  stack,markdown,integrity}.sh plus gtt-check-session-adapter.sh for every
  declared adapter; all PASS as of this entry.

Protection:
- GTTGuard markers found: none - registry: initialized (gtt/protection/registry.yaml
  exists, 0 protected artifacts).

Human action required:
- Decide whether to adopt the staged Codex/GitHub Copilot/Kiro session
  adapters (a separate governed decision, not made by this closure).
- Verify Codex/Copilot/Kiro runtime yourself if you want to claim it (see
  *Known gaps* below) - not achievable by an agent in this environment.
- Decide the real development status (Ready/In Progress/Done, beyond what
  is already set) if EPIC-001's remaining STORY-002 work continues.
- Commit and push when you decide to - not done by this closure.
```

---

## Entry 2026-09-28 — Virgin/Product closure

Solution Designer decision: `ADR-002-artifact-identity-index-session-memory.md`
is to be **removed from `gtt/adr/`**. It documented GTT's own internal
engineering (Artifact Identity, Technical Index, Session Memory Service, ADE
Adapter Contract) as a decision record, not a governed choice a host project
makes when adopting GTT. Its functional content is already fully covered by
`gtt/docs/DOCS.md` and `gtt/docs/SESSION-ADAPTER-CONTRACT.md` — nothing is
being copied or duplicated into a new ADR. Removal itself (`gtt/adr/` is
frozen) is staged as a promotion package under `gtt/proposals/` and requires
the Solution Designer to run it — an agent never writes into `gtt/adr/`
directly, decision or not. Once applied, `gtt/adr/` will hold only
`ADR-001-context-governance.md` (product boilerplate — required by
`gtt-freeze.sh`, written into every GTT installation by the `gtt-bootstrap`
skill) and `ADR-TEMPLATE.md`. The now-executed one-shot promotion scripts for
ADR-002's original promotion and the `protect-l0.py`/`protect-guard.py`/
`settings.json` fix were deleted in the earlier Virgin/Product cleanup pass,
same date.

---

## GTT v2.1 — Technical closure detail

Everything below is additional detail for the entry above, each item
separating **ESTADO** (IMPLEMENTADO / PARCIAL / NO IMPLEMENTADO) from
**EVIDENCIA** (STATIC VERIFIED / RUNTIME VERIFIED / DOCUMENTED ONLY /
NO EVIDENCE). Nothing here is invented; every claim traces to a script run
in this session or a file in this repository.

| Item | ESTADO | EVIDENCIA |
|---|---|---|
| ADR-002 ratified, promoted, then removal decided (Virgin/Product) | IMPLEMENTADO (historically), removal PENDING human execution | RUNTIME VERIFIED: ratified and promoted 2026-09-28 (`Status: Accepted`); Solution Designer decided the same day to remove it from `gtt/adr/` — its functional content lives in `gtt/docs/DOCS.md` and `gtt/docs/SESSION-ADAPTER-CONTRACT.md`, not duplicated into any ADR; removal staged under `gtt/proposals/`, pending the Solution Designer running the promotion script |
| Artifact Identity | IMPLEMENTADO | RUNTIME VERIFIED — `gtt/index/artifacts.json`, 49 active artifacts, 0 unregistered/missing per `gtt-check-integrity.sh`; determinism confirmed across two consecutive `gtt-index.sh` runs (`gtt/EVIDENCE.md`) |
| Repository Reconciliation | PARCIAL | RUNTIME VERIFIED for the `--retire` path (exercised twice this session: Kiro identities, ADR-002's proposal→ADR identity split; a third use is staged, pending human execution, to retire ADR-002's own identity when it is removed from the product); NO EVIDENCE this session for the move/rename-detection path itself (no real move occurred) — reflected as `STORY-002: In Progress` in `gtt/backlog.md` |
| Technical Index | IMPLEMENTADO | RUNTIME VERIFIED — `gtt/index/technical-index.json` rebuilt deterministically (identical sha256 across two runs, `gtt/EVIDENCE.md`); `gtt-query.sh` resolved real queries repeatedly this session |
| Session Memory | IMPLEMENTADO | RUNTIME VERIFIED — `gtt-session-context.sh` output cross-checked field-by-field against independent ground truth (`gtt/EVIDENCE.md`); Claude Code SessionStart hook fired live multiple times this session |
| ADE Adapter Contract | IMPLEMENTADO | RUNTIME VERIFIED — `gtt-check-session-adapter.sh` PASS for all 4 declared adapters (claude/codex/copilot/kiro), this session, repeatedly |
| Core ADE-agnostic | IMPLEMENTADO | STATIC VERIFIED — `grep -i "claude\|codex\|kiro\|copilot"` over `gtt-status.sh`, `gtt-session-context.sh`, `gtt-run-python.sh` returns nothing; `gtt-validate.sh`'s own adapter-matrix detection (the one remaining Core-adjacent ADE-name dependency) was fixed this session to discover adapters via `gtt/session-adapters/*.json` instead of hardcoded `.claude`/`.kiro`/`.copilot` paths |
| Kiro mirror corrected | IMPLEMENTADO | RUNTIME VERIFIED — `.kiro/steering/` now has one file per glob in the corresponding `.claude/rules/*.md` (implementation: src/tests/lib; infrastructure: infra/deploy/bicep/tf/Dockerfile/docker-compose/workflows); `gtt-guard.md` scope corrected to `inclusion: always`; `SOURCE-BRIEF.*` added to `.kiro/permissions.yaml` |
| Evidencia reproducible | IMPLEMENTADO | RUNTIME VERIFIED — `gtt/EVIDENCE.md` persists command, repository state, result, and evidence type for the reconciliation/index/identity/session-memory checks run 2026-09-28 |
| Governance / Context L0 completo | IMPLEMENTADO | RUNTIME VERIFIED — `grep -RniE 'TODO\|PLACEHOLDER\|REPLACE ME\|<[a-z][^>]*>' gtt/context/` returns empty; all 6 files pass `gtt-freeze.sh`'s own literal checks (confirmed before the actual freeze ran) |
| Backlog y estados finales | IMPLEMENTADO | RUNTIME VERIFIED — EPIC-001 in `gtt/backlog.md`: STORY-001 Done, STORY-002 In Progress, STORY-003 Done, STORY-004 Done, STORY-005 Done, each with a stated reason tied to this session's actual evidence, not the original proposal's claims |
| Human Promotion Boundary | IMPLEMENTADO | RUNTIME VERIFIED — no ADR/context/AGENTS.md/hook-machinery change was ever written directly by the agent this session; every such change was staged under `gtt/proposals/` and applied by the Solution Designer running the script or editing the file themselves (ADR-002 promotion, its staging-note cleanup, the AGENTS.md phrase, and this closure's own protect-l0.py/protect-guard.py/settings.json fix) |
| Freeze activo | IMPLEMENTADO | RUNTIME VERIFIED — `gtt/.frozen` exists, `2026-09-28T17:18:49Z`, `Frozen by: griott` |
| Protección post-freeze verificada en vivo | IMPLEMENTADO | RUNTIME VERIFIED — a real gap was found (an absolute Windows path bypassed `protect-l0.py`'s Write/Edit check; PowerShell was entirely outside the hook's matcher) and fixed; after the fix, real attempts were made and denied: Write → DENIED, Edit → DENIED, Bash → DENIED, PowerShell → DENIED |
| Las 4 validaciones | IMPLEMENTADO | RUNTIME VERIFIED — `gtt-check-integrity.sh`, `gtt-check-protection.sh`, `gtt-check-session-adapter.sh` (×4), `gtt-validate.sh` all PASS, run immediately after the protection fix |
| Codex / GitHub Copilot / Kiro runtime | NO IMPLEMENTADO (runtime) | NO EVIDENCE — `gtt/session-adapters/{codex,copilot,kiro}.json` declare `not-verified` / `requires-interactive-session` / `not-installed` respectively; nothing in this session changed that, and nothing here claims otherwise |

---
Append, do not overwrite, on a later re-run (ADE/adapter switch, migration,
re-freeze) — each entry is a dated record of one bootstrap-related event, not
a single mutable status. A stale, unresolved "Human action required" here is
itself a finding worth surfacing during a `gtt-audit` pass.

---

## Scaffold restructure — 2026-09-29T14:27:13Z

```text
GTT Scaffold restructure applied

Moved:
- Project Governance to the project root: context/ adr/ proposals/ backlog.md change-request.md session.md .frozen
- GTT Documentation to docs/: index installation usage gtt-completion evidence docs session-adapter-contract
- Entry points renamed lowercase: readme-gtt.md readme-gtt.es.md
Engine (unchanged location): gtt/scripts gtt/index gtt/protection gtt/session-adapters; added gtt/scaffold/manifest.yaml

ADR: ADR-003 ratified by executing apply-ADR-003-scaffold-restructure.sh (L0 text changed only through it)
Freeze: .frozen preserved byte-for-byte; gtt-freeze.sh was not run
Human action required: review 'git status', commit, then delete the staged package in proposals/ (see the ADR script's closing message)
```

---

## Layout migration to .gtt/ and gtt-domain/ — 2026-09-29T17:32:28Z

```text
GTT layout migration applied (layout version 2)

Moved:
- Engine to .gtt/: index protection scaffold scripts session-adapters (from gtt/), README.md, and GTT documentation to .gtt/docs/ (from docs/)
- Governed domain to gtt-domain/: context adr proposals backlog.md change-request.md session.md .frozen
Unchanged: AGENTS.md, readme-gtt*.md, SOURCE-BRIEF.*, .claude/ .kiro/ .copilot/

ADR: ADR-004 ratified by executing apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh (L0 text changed only through it)
Freeze: .frozen preserved byte-for-byte at gtt-domain/.frozen; gtt-freeze.sh was not run
Human action required: review 'git status', commit, then delete the staged package in gtt-domain/proposals/ (see the ADR script's closing message and gtt-domain/proposals/gtt-domain-migration/CLEANUP.md)
```
