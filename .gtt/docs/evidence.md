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

**State:** branch `dev`, HEAD `b2cdceb` (GTT v2.1 technical checkpoint), working tree had uncommitted `.kiro/` and `.gtt/index/` changes from prior work in this same session (Kiro mirror-fidelity fixes, ADE-agnostic `gtt-validate.sh`). No freeze, no ratification.

### 1. Reconciliation

| Command | Result | Type |
|---|---|---|
| `bash .gtt/scripts/gtt-reconcile.sh` | `gtt-reconcile: nothing to reconcile - every registered path exists.` (exit 0) | RUNTIME VERIFIED |
| `python .gtt/scripts/gtt_artifacts.py summary` | `identity: 48 active artifact(s), 0 retired` / `technical index: fresh` / `unresolved references: 0` — no "unregistered artifacts" line printed | RUNTIME VERIFIED |

Missing (registered path, no file on disk): **0**. Extra (file on disk, unregistered): **0**. Filesystem and `.gtt/index/artifacts.json` are consistent as of this commit + uncommitted state. `artifacts.json` was not hand-edited.

### 2. Technical Index — reconstruction determinism

Procedure: ran `bash .gtt/scripts/gtt-index.sh` twice in immediate succession against the same repository state, hashing both derived files after each run.

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

Ran `bash .gtt/scripts/gtt-session-context.sh` (which internally calls `gtt-status.sh`) and independently re-derived each field from the repository to confirm the output is not invented text:

| Field in `gtt-domain/session.md` | Independent check | Match |
|---|---|---|
| `pre-freeze` | `test -f gtt-domain/.frozen` → absent | ✓ |
| Current work / Blocked: `none` | `grep` for `Status: In Progress\|Blocked` in `gtt-domain/backlog.md` → no hits | ✓ |
| Pending proposals (7 files) | `find proposals -maxdepth 1 -type f ! -name README.md` | ✓ identical list |
| Change request: `empty (still template placeholders)` | `grep -c '^Change: <' gtt-domain/change-request.md` → 1 | ✓ |
| `identity: 48 active, 0 retired`, `technical index: fresh`, `unresolved references: 0` | independent `gtt_artifacts.py summary` run (§1) | ✓ |
| `branch: dev; uncommitted paths: 15` | `git status --porcelain` → 15 lines | ✓ |
| recent commits (5) | `git log -5 --format='%h %s'` | ✓ identical |
| Markers `operational-only`, `NOT authority`, `NOT evidence`, `NOT a decision record`, `NOT a grounding source` | present verbatim in the delivered payload | ✓ |

All fields RUNTIME VERIFIED against independent ground truth. `gtt-domain/session.md` carries no authority/evidence claim of its own (header states so explicitly) and none is asserted for it here.

### 5. This entry

Persisted because no existing document outside `gtt-domain/proposals/` (out of scope for this task) served as a reproducible-evidence log. `.gtt/docs/evidence.md` is the minimal new artifact created for that purpose; registered via `.gtt/scripts/gtt-index.sh` like any other kit document.

### 6. Final validation (same state, after registering this file)

| Check | Result | Type |
|---|---|---|
| `gtt-check-integrity.sh` | PASS — 49 artifact(s) consistent; 2 pre-existing WARN (`readme-gtt.es.md` anchors, unrelated) | RUNTIME VERIFIED |
| `gtt-check-protection.sh` | PASS | RUNTIME VERIFIED |
| `gtt-check-session-adapter.sh claude` | PASS (`adapter=installed coverage=N1 static=PASS runtime-declared=runtime-verified`) | RUNTIME VERIFIED (static); runtime status itself is DOCUMENTED ONLY per `.gtt/session-adapters/claude.json` |
| `gtt-check-session-adapter.sh codex` | PASS (`adapter=staged coverage=N1 static=PASS runtime-declared=not-verified`) | RUNTIME VERIFIED (static); `not-verified` = NO EVIDENCE of runtime |
| `gtt-check-session-adapter.sh copilot` | PASS (`adapter=staged coverage=N1 static=PASS runtime-declared=requires-interactive-session`) | RUNTIME VERIFIED (static); NO EVIDENCE of runtime |
| `gtt-check-session-adapter.sh kiro` | PASS (`adapter=staged coverage=N1 static=PASS runtime-declared=not-installed`) | RUNTIME VERIFIED (static); NO EVIDENCE of runtime |
| `gtt-validate.sh` | OK — every line PASS, one `SKIPPED gtt-check-adapter.sh (0 of 4 declared adapters match this workspace)` (expected: this repo is the multi-adapter catalog, not an installed project) | RUNTIME VERIFIED |

No FAIL occurred; nothing was converted to SKIPPED to hide a failure — the one SKIPPED line is `gtt-validate.sh`'s own pre-existing, documented behavior for a catalog repository.

---

## Entry 2026-09-29T17:44 — ADR-005 package (Multi-ADE, Initial Design Questionnaire): pre-ratification checks

**State:** branch `main`, HEAD `5ef21f6`; working tree has uncommitted changes (`gtt-domain/session.md` modified; untracked package files under `gtt-domain/proposals/`, `.gtt/scaffold/templates/`, the task file). Project frozen. ADR-005 is **not ratified** and `apply-ADR-005-bootstrap-integration-contracts.sh` has **not been executed by anyone**. Platform: Windows 11, Git Bash, Python 3.13. Nothing below is evidence about the promoted tree.

### 1. What was run

| Command | Result | Type |
|---|---|---|
| `python gtt-domain/proposals/adr-005-package/rehearse-multi-ade.py --project .` | `103/103 checks held` (exit 0). Runs on a **temporary copy** of the project overlaid with the staged package: registry, init, re-run, status/inspect/resume, validate failures, primary, update, clean/export, migration, record, questionnaire, Core neutrality, `gtt-index.sh` + `gtt-validate.sh` (no FAIL) | RUNTIME VERIFIED (of the staged code in a copy, not of the repository) |
| `bash -n` on `apply-ADR-005-bootstrap-integration-contracts.sh` and `apply-session-adapters.sh` | exit 0 for both (syntax only; neither was run) | STATIC VERIFIED |
| `sha256sum` of each of the 20 MOD/L0 targets vs the hash table embedded in the promotion script | 20 of 20 identical | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-check-markdown.sh` | `gtt-check-markdown: OK` | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-validate.sh` (baseline, before the package, real repo) | PASS except `gtt-check-integrity.sh` FAIL: unregistered artifacts (questionnaire, staged drafts) + 2 pre-existing `readme-gtt.es.md` anchor WARNs; adapter check `SKIPPED` (catalog) | RUNTIME VERIFIED |
| `git status --short` after the package was built | only `gtt-domain/proposals/**` (new/edited), plus `.gtt/scaffold/templates/`, the task file and `__pycache__` untracked and `gtt-domain/session.md` modified — all present before the package. No governed file (`context/`, `adr/`, `.frozen`, `backlog.md`, `change-request.md`, `AGENTS.md`, hooks, settings) changed | RUNTIME VERIFIED |
| Diff of the questionnaire ignoring `{=html}` fences and blank lines, before vs. staged | empty (53 answer slots normalised to `<!-- ADE populates this section -->`) | RUNTIME VERIFIED |

### 2. What was not verified

| Claim | Status | Type |
|---|---|---|
| The promotion script's behaviour (prompt, backup, rollback, stamping, post-validation) | never executed; only `bash -n`, its hash table and its `sed` expressions were checked in isolation | NO EVIDENCE |
| Behaviour on Linux or macOS | not run | NO EVIDENCE |
| Codex, GitHub Copilot and Kiro runtimes | not exercised; `enforcement: ci-gate` restates `.gtt/docs/docs.md` | DOCUMENTED ONLY |
| An ADE following the questionnaire's Operating Contract | instruction plane only; no script can prove it | NO EVIDENCE |
| `gtt-check-stack.sh` against `origin/main` on the promoted tree | not determinable in the temporary copy (`CANNOT-DETERMINE`) | NO EVIDENCE |
| Claude Code hooks against the promoted tree | untouched by the package; not re-run | NO EVIDENCE |

No FAIL was hidden: the only non-PASS lines are the baseline `gtt-check-integrity.sh` (expected, resolved by `gtt-index.sh` in the rehearsal) and the catalog `SKIPPED` adapter check.

---

## Entry 2026-09-29T17:54 — ADR-005 promoted (Multi-ADE, Initial Design Questionnaire): post-ratification checks

**State:** branch `main`, HEAD `5ef21f6` (nothing committed since the earlier entry); working tree carries the promoted, uncommitted changes plus untracked files. ADR-005 `Status: Accepted`, ratified by the Solution Designer executing `apply-ADR-005-bootstrap-integration-contracts.sh` on 2026-09-29 (output of that run: 26 files written, `gtt-index` OK with 61 artifacts, `gtt-validate: OK`). This entry follows the pre-ratification entry above, which is history. Platform: Windows 11, Git Bash, Python 3.13.

### 1. What was run on the promoted tree

| Command | Result | Type |
|---|---|---|
| The promotion script's own post-validation (`gtt-validate.sh`), as printed by the run | `gtt-check-backlog` PASS; `gtt-check-adapter` SKIPPED (catalog, no `.gtt/ade.json`); `gtt-check-protection` PASS; `gtt-check-stack` PASS; `gtt-check-markdown` PASS; `gtt-check-integrity` PASS; session-adapter checks PASS for claude, codex, copilot, kiro; `gtt-validate: OK` | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-validate.sh` (re-run afterwards) | identical: every line PASS or the one SKIPPED adapter check; `gtt-validate: OK` | RUNTIME VERIFIED |
| `python gtt-domain/proposals/adr-005-package/rehearse-multi-ade.py --catalog .` | `103/103 checks held` (temporary copy of the promoted tree; `gtt-check-stack` CANNOT-DETERMINE there, outside a checkout) | RUNTIME VERIFIED (engine, in a copy) |
| `bash .gtt/scripts/gtt-ade.sh state` | `ADE state: not configured (no .gtt/ade.json ...)` — expected: this repository is the catalog | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-template.sh list` | `initial-design-questionnaire  ok  .gtt/scaffold/templates/gtt-initial-design-questionnaire.md` | RUNTIME VERIFIED |
| ADR-005 header | `Status: Accepted`, `Date: 2026-09-29`, `Approved by: Solution Designer (mgriott) - ratified by executing apply-ADR-005-...sh` | RUNTIME VERIFIED |
| `git status --short` | modified: the 15 machinery/instruction/documentation files, the 5 L0 context files, `.gtt/docs/evidence.md` and `gtt-completion.md` (appends), the derived index and `session.md`; new: the 5 engine files, ADR-005, the questionnaire folder. `gtt-domain/.frozen`, `backlog.md`, `change-request.md`, `SOURCE-BRIEF.*`, hooks and settings not modified | RUNTIME VERIFIED |

### 2. Still not verified

| Claim | Status | Type |
|---|---|---|
| `gtt-ade.sh install/adopt/update/remove` against a real installed project (only temporary copies were used) | not run | NO EVIDENCE |
| Linux and macOS | not run | NO EVIDENCE |
| Codex, GitHub Copilot and Kiro runtimes; `enforcement: ci-gate` | restates the compatibility matrix | DOCUMENTED ONLY |
| An ADE following the questionnaire's Operating Contract | instruction plane only | NO EVIDENCE |
| `apply-session-adapters.sh` record step on a real install | rehearsed piecewise only; the script was never run | NO EVIDENCE |

The staged package files, the backlog proposal (`PROPOSAL-backlog-epic-multi-ade-questionnaire.md`) and the ADE state for this repository remain undecided; nothing here records them as done.

---

## Entry 2026-09-29T22:00 — ADR-006 promoted (provenance, gaps, sources, working agreements) and staging cleanup: post-ratification checks

**State:** branch `main`; commits `3f35a95` (ADR-005), `947c24a` (ADR-006) and `a94c7a4` (cleanup of the ratified staging). ADR-006 `Status: Accepted`, ratified by the Solution Designer executing its promotion script on 2026-09-29. Working tree clean apart from one unrelated untracked file (`GTT-BOOTSTRAP-RECIPE.md`). Platform: Windows 11, Git Bash, Python 3.13. Supersedes the "not verified" rows of the earlier ADR-005 entries only where stated below.

### 1. What was run on the promoted tree

| Command | Result | Type |
|---|---|---|
| Promotion script's post-validation, as printed by the run, and `bash .gtt/scripts/gtt-validate.sh` afterwards (also after the cleanup) | every line PASS (`gtt-check-provenance.sh` included) except the adapter check `SKIPPED` (catalog, no `.gtt/ade.json`); `gtt-validate: OK` | RUNTIME VERIFIED |
| `bash .gtt/scripts/gtt-check-provenance.sh` | `0 FAIL, 0 WARN`; no gap register entries, sources or agreements declared yet | RUNTIME VERIFIED |
| `python gtt-domain/proposals/adr-006-package/rehearse-provenance.py --catalog .` (before the package was removed) | `69/69 checks held`, including the nested ADR-005 rehearsal `103/103` | RUNTIME VERIFIED (engine, in a copy) |
| `gtt-query.sh --governance open` / `sources` | `no OPEN gaps` / `no source manifest` (expected: nothing adopted in this repository) | RUNTIME VERIFIED |
| `gtt-reconcile.sh --retire ... --apply` for the 14 removed staging artifacts, then `gtt-index.sh` and `gtt-validate.sh` | identities retired, index regenerated, `gtt-validate: OK` | RUNTIME VERIFIED |
| `git log` / `git status` | three commits above; only the unrelated untracked file remains | RUNTIME VERIFIED |

### 2. Still not verified

| Claim | Status | Type |
|---|---|---|
| `gtt-ade.sh install/adopt/update/remove` and the provenance gate on a real installed project (only temporary copies) | not run | NO EVIDENCE |
| Linux and macOS | not run | NO EVIDENCE |
| Codex, GitHub Copilot and Kiro runtimes; `enforcement: ci-gate` | restates the compatibility matrix | DOCUMENTED ONLY |
| An ADE following the Questionnaire's Operating Contract or the new provenance instructions in the bootstrap skill | instruction plane only | NO EVIDENCE |
| `apply-session-adapters.sh` record step on a real install | rehearsed piecewise only | NO EVIDENCE |
| Whether a `[FUENTE]` really supports a claim; whether an OPEN scope is wise | the gate is lexical and structural | NO EVIDENCE |

`PROPOSAL-backlog-epic-multi-ade-questionnaire.md` remains an undecided proposal; `gtt-domain/backlog.md` was not changed.
