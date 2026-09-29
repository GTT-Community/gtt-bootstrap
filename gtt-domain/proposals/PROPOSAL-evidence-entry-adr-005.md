# PROPOSAL — Evidence entry for the ADR-005 package

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Draft, not a decision. `.gtt/docs/evidence.md` was **not** modified. This is the proposed text of a new entry, in the file's existing contract.

## The contract `.gtt/docs/evidence.md` already imposes

- **Append-only**; one entry per pass, headed `## Entry <YYYY-MM-DDTHH:MM> — <title>`.
- A `**State:**` line (branch, HEAD, working-tree condition), then numbered `###` sections.
- Results as tables `| Command | Result | Type |`, with the **raw result** and exit status; each row carries exactly one of four types:
  `STATIC VERIFIED`, `RUNTIME VERIFIED`, `DOCUMENTED ONLY`, `NO EVIDENCE`. The `[EVIDENCIA]`/`[VACÍO]` tags are the questionnaire's provenance conventions, not this file's; `[VACÍO]` maps to `NO EVIDENCE`.
- It is not a decision record; it must not claim more than what was run. Rows must be reproducible commands.
- Timestamp: set when you append it. Rows below describe what was run on 2026-09-29 in the state given.

## Proposed entry (append at the end of `.gtt/docs/evidence.md`)

```markdown

---

## Entry <YYYY-MM-DDTHH:MM> — ADR-005 package (Multi-ADE, Initial Design Questionnaire): pre-ratification checks

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
```

## Notes on your draft

- The bullet "los scripts modificados" is narrowed to what was actually checked: `bash -n` covers the two scripts named above, not the new engine files (those are covered by the rehearsal).
- "git status confirma que no se modificaron archivos gobernados" is kept, with the pre-existing dirty files stated, so it cannot be read as a clean tree.
- After you run the promotion script, a **second entry** (post-promotion: `gtt-validate.sh`, `rehearse-multi-ade.py --catalog .`, `git status`) is what would upgrade any of these rows for the real tree; this one should not be edited then, only followed.
