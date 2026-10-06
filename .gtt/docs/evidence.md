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

## 2026-10-05 — Antigravity overlay (`antigravity`), working tree on `main` after 66b7e15

| Claim | Check | Result | Evidence type |
|---|---|---|---|
| The overlay installs, validates, can be Primary, coexists with OpenHands in `.agents/`, and reports a pre-existing `.agents/hooks.json` or `.agents/rules/gtt.md` as a conflict without writing | `python3 .gtt/tests/bootstrap-acceptance.py` — scenario `antigravity` | PASS | RUNTIME VERIFIED (on disposable copies of this repository) |
| Given Antigravity's documented `PreToolUse` payload, `gtt_protect.py hook --format antigravity` denies governed writes, promotion scripts and edits to GTTGuard symbols, and allows the rest | same suite — scenario `protection_hooks` | PASS | RUNTIME VERIFIED (the engine, with a payload written from the documentation) |
| The payload, tool names and deny shape are the ones Antigravity uses | Antigravity's published hooks documentation | not re-run here | DOCUMENTED ONLY |
| Antigravity invokes the hook, in its CLI, its IDE or its desktop app | none — no Antigravity binary on this machine | not run | NO EVIDENCE |
| Antigravity honours a denial that exits 2 | none | not run | NO EVIDENCE |
| The directory Antigravity runs the hook in is the project root | none | not run | NO EVIDENCE |
| Antigravity loads the agent contract in full | none | not run | NO EVIDENCE |

## 2026-10-06 — Two-plane architecture (Governance / Observation), working tree on `main` after 66b7e15

| Claim | Check | Result | Evidence type |
|---|---|---|---|
| Observation is deterministic, silent on compliant work, idempotent, and stops only on a boundary ratified as `BLOCKING` or an observation the human rejected | `python3 .gtt/tests/bootstrap-acceptance.py` — scenario `observation` | PASS | RUNTIME VERIFIED (on disposable frozen copies of this repository) |
| Freeze records a governance baseline (commit, digest), a promoted change is completed by a new freeze that keeps the earlier one, and an unchanged governed state is not re-frozen | same scenario | PASS | RUNTIME VERIFIED |
| A Story needs no approval; an Epic that is `Planned` / `In Progress` / `Completed` needs its `Goal` and `Approved` | same suite — scenario `backlog_model` | PASS | RUNTIME VERIFIED |
| The shared pre-write engine denies a write under a `BLOCKING` path boundary, naming the rule, and denies an agent freezing or deciding an observation | same suite — scenario `observation` (`gtt_protect.py decide`) | PASS | RUNTIME VERIFIED (the engine) |
| The staged Claude Code hooks behave as described | simulated tool events against the staged copies under `gtt-domain/proposals/claude-adapter/` | PASS (23 cases) | RUNTIME VERIFIED (the staged copies; NOT the installed hooks, which are unchanged until the human applies them) |
| The new hooks behave the same inside Claude Code | none | not run | NO EVIDENCE |
| Observation after a write reaches the agent on Kiro (`.kiro/hooks/detect-drift.json`) | none | not run | NO EVIDENCE |

## 2026-10-06 — Bootstrap 1.3.1 closure (enforcement F1–F8), branch `release/bootstrap-1.3.1`, working tree after 66b7e15

| Claim | Check | Result | Evidence type |
|---|---|---|---|
| The decision core is byte-identical in the staged Claude Code hook and in `gtt_protect.py`, and 59 cases get the same decision from both, each denial naming its rule | `GTT_TEST_CLAUDE_HOOK=gtt-domain/proposals/closure-1.3.1/claude-adapter/protect-l0.py python3 .gtt/tests/bootstrap-acceptance.py` — scenario `enforcement` | PASS — 419/419 | RUNTIME VERIFIED (the staged hook, fed Claude Code's PreToolUse payload on stdin, on disposable copies; not inside Claude Code) |
| The same suite against the hook installed before the package | `python3 .gtt/tests/bootstrap-acceptance.py` | 379/419 — the 40 that fail are all in scenario `enforcement`: F1 7, F2 3, F3 13, F5 7, F6 1, F7 2, and 7 where the installed hook denies correctly but its message does not name the rule | RUNTIME VERIFIED |
| CI fails on a removed freeze marker and on a rewritten freeze history, and passes a new freeze that keeps the earlier one | same suite — `gtt-check-stack.sh <base>` on a frozen copy with a base ref | PASS | RUNTIME VERIFIED |
| With the Git pre-commit hook installed in a frozen copy, a non-blocking change is committed and a `BLOCKING` boundary stops the commit, naming its rule | same suite — real `git commit` | PASS | RUNTIME VERIFIED |
| A broken observation engine does not block a session and is not silent about `BLOCKING` | same suite — `gtt_observe.py` corrupted in a frozen copy | PASS | RUNTIME VERIFIED |
| The hooks behave the same inside Claude Code, Cursor, OpenHands, Antigravity or Kiro | none | not run | NO EVIDENCE |
| A write by an interpreter or by Git plumbing is stopped in real time | none — by design it is not; CI is the layer | not applicable | NO EVIDENCE |

## 2026-10-06 — Bootstrap 1.3.1 closure, after promotion (the human ran `apply-bootstrap-1.3.1-closure.sh`)

| Claim | Check | Result | Evidence type |
|---|---|---|---|
| The installed Claude Code hook is the staged one and the suite passes against it | `cmp` of the two files; `python3 .gtt/tests/bootstrap-acceptance.py` with no override | identical; PASS — 419/419 | RUNTIME VERIFIED |
| `gtt-validate.sh` | run in this repository | OK — 12 PASS, 1 SKIPPED (adapter check, normal in the catalog) | RUNTIME VERIFIED |
| Inside a real Claude Code session an agent cannot run a promotion script spelled `./path` | the agent attempted `./gtt-domain/proposals/apply-AGENTS-antigravity.sh` | denied by the PreToolUse hook, naming *Human Promotion Boundary* | RUNTIME VERIFIED (inside Claude Code) |
| ... cannot remove the freeze marker through the shell | the agent attempted `rm gtt-domain/.frozen` | denied by the PreToolUse hook, naming `freeze-semantics` | RUNTIME VERIFIED (inside Claude Code) |
| ... cannot edit the governance ledger through the shell | the agent attempted `sed -i ... gtt-domain/governance-backlog.json` | denied by the PreToolUse hook, naming `human-decision-authority` | RUNTIME VERIFIED (inside Claude Code) |
| ... cannot write either file with the Write tool | the agent attempted both | denied by `permissions.deny` before the hook ran | RUNTIME VERIFIED (inside Claude Code; the hook's own answer to a Write was therefore not exercised live) |
| The F5 (Git-hook bypass), F6 (warning) and `BLOCKING` path-boundary denials inside Claude Code | none - they need the Git hook installed or a frozen project | not run | NO EVIDENCE (covered by the suite on disposable copies only) |
