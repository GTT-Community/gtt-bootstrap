# GTT Technical Evidence Log

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> A durable, append-only record of reproducible technical checks executed
> against this repository — command, repository state (commit/branch), raw
> result, PASS/FAIL, and evidence type. Not a decision record, not
> Governance, not architecture, not the backlog, not the bootstrap
> completion report. It exists so a later audit does not have to take a
> chat transcript's word for what was actually run. Append, do not
> overwrite, on a later entry.
>
> Evidence types used below: `STATIC VERIFIED` (read/derived from source
> without executing it), `RUNTIME VERIFIED` (actually executed in this
> repository and the output shown), `DOCUMENTED ONLY` (a claim recorded in
> a declaration/doc, not independently re-run here), `NO EVIDENCE` (checked
> for and not found).

---

## Entry 2026-09-28T14:19 — Reproducible evidence pass (v2.1 Artifact Identity / Technical Index / Session Memory)

**State:** branch `dev`, HEAD `b2cdceb` (GTT v2.1 technical checkpoint), working tree had uncommitted `.kiro/` and `gtt/index/` changes from prior work in this same session (Kiro mirror-fidelity fixes, ADE-agnostic `gtt-validate.sh`). No freeze, no ratification.

### 1. Reconciliation

| Command | Result | Type |
|---|---|---|
| `bash gtt/scripts/gtt-reconcile.sh` | `gtt-reconcile: nothing to reconcile - every registered path exists.` (exit 0) | RUNTIME VERIFIED |
| `python gtt/scripts/gtt_artifacts.py summary` | `identity: 48 active artifact(s), 0 retired` / `technical index: fresh` / `unresolved references: 0` — no "unregistered artifacts" line printed | RUNTIME VERIFIED |

Missing (registered path, no file on disk): **0**. Extra (file on disk, unregistered): **0**. Filesystem and `gtt/index/artifacts.json` are consistent as of this commit + uncommitted state. `artifacts.json` was not hand-edited.

### 2. Technical Index — reconstruction determinism

Procedure: ran `bash gtt/scripts/gtt-index.sh` twice in immediate succession against the same repository state, hashing both derived files after each run.

| Run | `technical-index.json` sha256 | `artifacts.json` sha256 |
|---|---|---|
| 1 | `a2ece57cf24170ed578da4a1ac12664222ae2426e3ad251f92d041373a51fec6` | `be14e12bd87712df4162de41916a89edc549959df037d44ffbf9f3d73e775659` |
| 2 | `a2ece57cf24170ed578da4a1ac12664222ae2426e3ad251f92d041373a51fec6` | `be14e12bd87712df4162de41916a89edc549959df037d44ffbf9f3d73e775659` |

**Identical.** The index is deterministic/reconstructible from the same Markdown state; `artifacts.json` did not change between runs (no new files to register), so identity was neither lost nor reassigned. RUNTIME VERIFIED.

### 3. Artifact Identity — stability

| Check | Result | Type |
|---|---|---|
| Duplicate IDs / duplicate paths | none (`gtt-check-integrity.sh` — see §6) | RUNTIME VERIFIED |
| IDs stable across the two `gtt-index.sh` runs above | unchanged (`artifacts.json` sha256 identical) | RUNTIME VERIFIED |
| Paths coherent with filesystem | 0 missing, 0 unregistered (§1) | RUNTIME VERIFIED |
| `[[ID]]` references resolve | `unresolved references: 0` (§1) | RUNTIME VERIFIED |

No reconstruction-from-scratch of `artifacts.json` was performed (that would discard `history`/`aliases`, which is not what "reconstruction" means for an identity manifest — the official mechanism for reconstructing it without losing identity is exactly `gtt-index.sh`/`gtt-reconcile.sh`, exercised above).

### 4. Session Memory — reproducibility

Ran `bash gtt/scripts/gtt-session-context.sh` (which internally calls `gtt-status.sh`) and independently re-derived each field from the repository to confirm the output is not invented text:

| Field in `session.md` | Independent check | Match |
|---|---|---|
| `pre-freeze` | `test -f .frozen` → absent | ✓ |
| Current work / Blocked: `none` | `grep` for `Status: In Progress\|Blocked` in `backlog.md` → no hits | ✓ |
| Pending proposals (7 files) | `find proposals -maxdepth 1 -type f ! -name README.md` | ✓ identical list |
| Change request: `empty (still template placeholders)` | `grep -c '^Change: <' change-request.md` → 1 | ✓ |
| `identity: 48 active, 0 retired`, `technical index: fresh`, `unresolved references: 0` | independent `gtt_artifacts.py summary` run (§1) | ✓ |
| `branch: dev; uncommitted paths: 15` | `git status --porcelain` → 15 lines | ✓ |
| recent commits (5) | `git log -5 --format='%h %s'` | ✓ identical |
| Markers `operational-only`, `NOT authority`, `NOT evidence`, `NOT a decision record`, `NOT a grounding source` | present verbatim in the delivered payload | ✓ |

All fields RUNTIME VERIFIED against independent ground truth. `session.md` carries no authority/evidence claim of its own (header states so explicitly) and none is asserted for it here.

### 5. This entry

Persisted because no existing document outside `proposals/` (out of scope for this task) served as a reproducible-evidence log. `docs/evidence.md` is the minimal new artifact created for that purpose; registered via `gtt/scripts/gtt-index.sh` like any other kit document.

### 6. Final validation (same state, after registering this file)

| Check | Result | Type |
|---|---|---|
| `gtt-check-integrity.sh` | PASS — 49 artifact(s) consistent; 2 pre-existing WARN (`readme-gtt.es.md` anchors, unrelated) | RUNTIME VERIFIED |
| `gtt-check-protection.sh` | PASS | RUNTIME VERIFIED |
| `gtt-check-session-adapter.sh claude` | PASS (`adapter=installed coverage=N1 static=PASS runtime-declared=runtime-verified`) | RUNTIME VERIFIED (static); runtime status itself is DOCUMENTED ONLY per `gtt/session-adapters/claude.json` |
| `gtt-check-session-adapter.sh codex` | PASS (`adapter=staged coverage=N1 static=PASS runtime-declared=not-verified`) | RUNTIME VERIFIED (static); `not-verified` = NO EVIDENCE of runtime |
| `gtt-check-session-adapter.sh copilot` | PASS (`adapter=staged coverage=N1 static=PASS runtime-declared=requires-interactive-session`) | RUNTIME VERIFIED (static); NO EVIDENCE of runtime |
| `gtt-check-session-adapter.sh kiro` | PASS (`adapter=staged coverage=N1 static=PASS runtime-declared=not-installed`) | RUNTIME VERIFIED (static); NO EVIDENCE of runtime |
| `gtt-validate.sh` | OK — every line PASS, one `SKIPPED gtt-check-adapter.sh (0 of 4 declared adapters match this workspace)` (expected: this repo is the multi-adapter catalog, not an installed project) | RUNTIME VERIFIED |

No FAIL occurred; nothing was converted to SKIPPED to hide a failure — the one SKIPPED line is `gtt-validate.sh`'s own pre-existing, documented behavior for a catalog repository.
