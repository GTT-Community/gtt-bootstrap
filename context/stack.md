# Stack & Architecture Map

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> The single view of this solution. If it is not on this page, it is not part of
> the architecture. Every approved architectural change updates this file in the
> same commit as the ADR that approves it.

- **Last verified:** `2026-09-28`
- **Governing ADRs:** ADR-001

---

## 1. Stack at a glance

One row per layer. If a cell is empty, the decision has not been made — say so
rather than leaving a plausible guess in place.

| Layer | Technology | Version | Locked by |
|---|---|---|---|
| Language | Bash (Core scripts, CI gate) + Python 3 (engine components, hooks) | not pinned | |
| Runtime | none — no single application runtime; GTT executes as repository tooling | | |
| Application framework | none | | |
| Compute model | none — runs as scripts/tooling inside the repository; not deployed as a service | | |
| Datastore (primary) | none — filesystem-based; `gtt/index/artifacts.json` is the identity manifest | | |
| Datastore (cache) | none | | |
| Messaging / events | none | | |
| Identity & authz | none as an application identity service — authorization is repository governance/protection plus each ADE's own permission/hook mechanism | | |
| Secrets | none | | |
| IaC | none — no infrastructure to provision | | |
| CI/CD | Bash-based repository CI gate (`gtt-validate.sh` and its specialized checks); no specific CI/CD platform declared | | |
| Observability | none — deterministic PASS/FAIL/SKIPPED results and operational evidence from GTT scripts; no logs/metrics/traces infrastructure | | |
| Testing | deterministic validation via GTT scripts (`gtt-validate.sh` + specialized checks); no separate formal test framework | | |

"Locked by" points at the ADR that made the decision. Every cell above is
empty on purpose: no ADR has formally locked any of these choices yet
(ADR-001 governs the context mechanism itself, not these choices). A row
with no ADR is a decision nobody made on purpose — treat it as technical
debt.

---

## 2. Component map

Not applicable. GTT has no client/server component graph: it is
repository-native tooling (Bash/Python scripts operating on Markdown/JSON
files), with no network API and no messaging between components (see
`architecture.md` → *Integration strategy*).

---

## 3. Deployment topology

Not applicable as a deployed service. GTT lives and runs inside the
repository; its scripts execute locally or within the repository's own
CI/automation context (see `architecture.md` → *Deployment topology*).

---

## 4. Observability

Not applicable as an external observability stack. GTT scripts produce
deterministic PASS/FAIL/SKIPPED results and operational evidence (see
`docs/evidence.md`); there is no logs/metrics/traces collection pipeline,
and nothing pages anyone.

---

## 5. Dependency rules

The boundaries the code must respect. This table is what makes drift
detectable — without it, "Service A calls the database directly" is an opinion.

| Module | May depend on | Must not depend on |
|---|---|---|
| `gtt/scripts/` (Core) | — | any specific ADE |
| ADE adapters (`.claude/`, `.kiro/`, `.copilot/`, staged `.codex/`) | `gtt/scripts/` (via `gtt-session-context.sh` and the other Core entry points) | duplicating Core logic |
| `gtt/session-adapters/` | — | containing GTT logic (declarations are data only) |
| `gtt/index/` (identity manifest + derived technical index) | `gtt/scripts/gtt_artifacts.py` | being hand-edited, or the derived index being treated as a source of truth |
| `gtt/protection/` (GTTGuard registry) | `gtt/scripts/gtt_guard.py` | being hand-edited |
| `context/`, `adr/` | — | direct agent writes once frozen |
| `proposals/` | — | — |

Restates, as a table, the rule from `architecture.md` → *Modules and
boundaries*: **GTT Core provides the service; ADE adapters provide the
integration.** Adapters must not duplicate Core logic.

---

## 6. Map change log

Every row here corresponds to an accepted ADR. If an architectural change
happened without a row, the governance loop was skipped.

| Date | ADR | What changed in this map |
|---|---|---|
| 2026-09-28 | ADR-003 | Scaffold restructure: Project Governance (`context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen`) moves from `gtt/` to the project root; GTT Documentation moves to `docs/`; `gtt/` keeps only the Engine and gains `scaffold/manifest.yaml`. Rows of the dependency-rule table are re-pathed; no module boundary is added, removed, or relaxed. |

No other ADR has changed this map. The Artifact Identity, Technical Index,
and Session Memory Service capabilities documented in `docs/docs.md` and
`docs/session-adapter-contract.md` are GTT Core functionality, not a
decision recorded against this map (Virgin/Product closure, 2026-09-28).

---

## 7. Drift signals

Paths outside the GTT-owned directories that carry architectural weight even
though they are not themselves governed. `detect-drift.py` and the `gtt-audit` sweep read this
block to know what to watch; without it, the detector is blind. One line per
signal: a glob, then the decision or view it guards.

```gtt-drift-signals
```

None declared. GTT has no `src/`/`infra/`-style application code for this
block to watch (see *Explicitly out of scope* in `constraints.md`).

---
Governance: L0. Read-only for AI agents. Changes require an approved ADR and are
applied by the Solution Designer.
