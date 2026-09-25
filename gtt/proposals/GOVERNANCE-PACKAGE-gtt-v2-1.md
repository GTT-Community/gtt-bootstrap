# GTT v2.1 — Governance package (for human review)

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

**Status: Draft — not a decision.**

This package prepares the formal record for two GTT v2.1 improvements that are
already implemented: **(1)** Artifact Identity + Repository Reconciliation +
Technical Index, and **(2)** the Session Memory Service (with its ADE Adapter
Contract). It contains no new development and ratifies nothing. It exists so a
human can review the decision, and ratify it — or not.

## Contents

| File | What it is | State |
|---|---|---|
| `ADR-DRAFT-gtt-v2-1-identity-index-session-memory.md` | Draft ADR-002: context, problem, decision, authority limits, relation to Core and adapters, alternatives, consequences, risks | Draft — not a decision |
| `PROPOSAL-gtt-v2-1-backlog-epic-stories.md` | Form-4 proposal: EPIC-001 and STORY-001…005, with a backlog-ready block | Draft — Requires Solution Designer approval |
| `GOVERNANCE-PACKAGE-gtt-v2-1.md` | This file: evidence register, pending items, human checklist | Draft — not a decision |
| `PROPOSAL-artifact-identity-followups.md` (existing) | Earlier working proposal; §2d holds the exact `AGENTS.md` text to change by hand | Draft — not a decision |

No promotion script was generated for the ADR: the `gtt-adr` skill prepares
one only for a decision a human has already approved.

## Evidence register

Only evidence that exists in the repository is cited as evidence. Each row says
how to reproduce it and what it does **not** show.

| # | Evidence | Where / how to reproduce | Shows | Does not show |
|---|---|---|---|---|
| E1 | `gtt-validate.sh` OK, as prepared: backlog, protection, stack, markdown, integrity PASS; four adapter checks PASS; adapter-matrix check SKIPPED (catalog repo) | `bash gtt/scripts/gtt-validate.sh` | Every deterministic gate passes on the current tree, including identity/index integrity and adapter conformance | That any ADE loads the context (runtime), or that freeze would pass |
| E2 | Identity manifest and derived index | `gtt/index/artifacts.json`, `gtt/index/technical-index.json`; `gtt-check-integrity.sh` confirms they are consistent and fresh | The artifacts registered and indexed (37 before this package's three documents were added) | Anything about retrieval quality |
| E3 | Claude Code runtime record | `gtt/session-adapters/claude.json` → `verification.notes` | Real `claude -p` sessions on 2026-09-25: startup and resume fired the hook (`session_source` observed) and the agent quoted the payload | clear / compact / fork (documented only); delivery on resume distinct from the resumed transcript |
| E4 | Codex not verified, with cause | `gtt/session-adapters/codex.json` → `verification.notes` | In a sandbox the hook never executed; the documented hook-approval requirement is the probable cause; bypass flag deliberately not used | Which of project trust or hook approval blocked it |
| E5 | Declared adapter state | `gtt/session-adapters/{claude,codex,copilot,kiro}.json`; matrix in `gtt/docs/DOCS.md` → *Session Memory adapter matrix* | Coverage, per-event status, limitations, verification status per ADE | Runtime truth — declarations are claims |
| E6 | Contract and conformance check | `gtt/docs/SESSION-ADAPTER-CONTRACT.md`; `bash gtt/scripts/gtt-check-session-adapter.sh <ade>` | What an adapter must satisfy, and that all four currently satisfy it statically | That the check detects violations (see N2) |
| E7 | Core neutrality | `grep -Eni "claude|codex|kiro|copilot" gtt/scripts/gtt-status.sh gtt/scripts/gtt-session-context.sh gtt/scripts/gtt-run-python.sh` returns nothing | The Session Memory chain names no ADE | That every Core-adjacent script is neutral (see pending P8) |
| E8 | Commit history | `git log`: `81bf8df` *Artifact Identity + Technical Index* | What the human has already committed (identity, index, reconcile, query, Claude adapter, first wrapper) | That the later work is committed (see below) |

**Commit state as prepared.** `81bf8df` holds the identity/index/reconcile/query
scripts, both index files, the Claude adapter and registration, and the first
Session Memory wrapper. Uncommitted when this package was prepared: the adapter
contract, its check and declarations, the staged adapters and promotion script,
the ADE-neutral clean-up of the Core, and the derived files that follow from
them. `git status` is the authority on this, not this sentence.

**Evidence that is NOT in the repository** (so not relied on):

| # | What was done | Why it is not evidence |
|---|---|---|
| N1 | Scenarios on throwaway copies: an ADR moved with `mv` and reconciled; a duplicate ADR detected; an unresolved `[[ID]]` detected; broken-engine and no-Python failure paths of the service | The copies and their output were not kept; no test file exists for them |
| N2 | A mutation suite of the adapter check — 10 deliberate violations, all detected, and an unmutated control that passed | The suite was a scratch file outside the repository; a reader cannot rerun it |
| N3 | The raw transcripts of the Claude and Codex runs | Only the summaries in the declarations (E3, E4) are kept |

## Pending items

Classification: **Blocks a v2.1 component?** Only where the evidence in the
register shows it. Items marked *no* are not defects of the implementation.

| # | Item | State | Blocks a v2.1 component? | Owner |
|---|---|---|---|---|
| P1 | Codex runtime | **NOT VERIFIED** — needs the user to trust the project and approve the hook in an interactive session | No. Blocks only claiming Codex support | Human |
| P2 | GitHub Copilot runtime | **NOT VERIFIED** — verification requires an interactive Copilot CLI session; resume is documented as unsupported | No. Blocks only claiming Copilot support | Human |
| P3 | Kiro runtime | **NOT VERIFIED** — statically validated only; Kiro not installed; its documentation is internally inconsistent | No. Blocks only claiming Kiro support | Human |
| P4 | `AGENTS.md` | **Manual change pending** — stale phrase "installed adapter" in *Session continuity*; exact text in `PROPOSAL-artifact-identity-followups.md` §2d. Then run `gtt/scripts/gtt-index.sh` | No (documentation drift) | Solution Designer |
| P5 | Governance | **Pending** — no ADR accepted, no Epic/Story in `gtt/backlog.md` | Blocks calling v2.1 *ratified*, not its function | Solution Designer |
| P6 | Human ratification | **Pending** — nothing in this package is ratified | Same as P5 | Solution Designer |
| P7 | Freeze | **Pending, not this package's action.** As prepared, `gtt/context/constraints.md` still holds template placeholders, which `gtt-freeze.sh` rejects by its own rules; the script was not run | No | Solution Designer |
| P8 | `gtt-validate.sh` | **Technical follow-up, non-blocking.** It still detects which ADE adapter directory is installed (to choose whether to run `gtt-check-adapter.sh`); ideally that script would self-detect so the aggregator names no ADE | No — it is validation tooling, not the identity/index/session-memory Core | Maintainer |
| P9 | Regression evidence not persisted | N1/N2 above are not reproducible from the repository; persisting them as tests is not done here (no code changes in this task) | No | Maintainer |
| P10 | Staged adapters not installed | Codex, Copilot, Kiro adapters live under `gtt/proposals/session-adapters/`; installing them changes the adapter matrix (`AGENTS.md`, `gtt-check-adapter.sh`, `gtt-bootstrap` skill, `README-GTT.md`). `apply-session-adapters.sh` was **never executed** (it is barred to the agent) and its behaviour is untested beyond `bash -n` | No | Solution Designer |

Known issues **outside v2.1's scope**, not addressed: `notify-change-request.py`
and `detect-drift.py` invoke bare `python3` and fail on Windows with the Store
stub; `README-GTT.es.md`'s table of contents links to anchors that do not match
its headings (reported by the integrity check as warnings).

## What the human needs to review and ratify

In this order; each is a separate decision, and none is implied by another.

1. **Read the ADR** (`ADR-DRAFT-…`). Decide: ratify, amend, or reject. If
   ratified, set its `Status`, `Date`, and `Approved by` yourself. Only then does
   `gtt-adr` prepare the promotion package (`apply-ADR-NNN-…sh`) — which you run.
2. **Decide the `stack.md` question** in the ADR's *Affected context*: whether the
   L0 map should record these capabilities. This repository's L0 is still
   placeholders.
3. **Apply the manual `AGENTS.md` change** (P4), then run `gtt-index.sh`.
4. **Accept or amend the Epic and Stories.** If accepted, apply the backlog-ready
   block to `gtt/backlog.md` directly (no ADR, no script for a development-line
   change) and choose each Story's real status. Do not apply the older block in
   `PROPOSAL-artifact-identity-followups.md` §2c as well.
5. **Decide adoption of the staged adapters** (P10) one ADE at a time; each needs
   the matrix change and its own decision. Verify runtime yourself where required
   (P1–P3) and record the outcome in the declaration.
6. **Commit** what you accept. As prepared, part of the work is uncommitted (see
   *Commit state*).
7. **Freeze last**, and only when L0 holds real content (P7).

Questions this package cannot answer for you: whether the manifest-over-front-matter
choice stands; whether committing the technical index is the right trade-off;
whether v2.1 should be called complete before Codex, Copilot, and Kiro runtime are
verified.

## Status

**Draft — not a decision.**
