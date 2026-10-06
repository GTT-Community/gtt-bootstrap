# PROPOSAL — Bootstrap 1.3.1 closure (Governance / Observation)

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Draft, not a decision. Date: 2026-10-06. Nothing here changes anything until the Solution
Designer runs the promotion script.

```text
Proposed Context Change

Files:              AGENTS.md
                    gtt-domain/change-request.md
                    .claude/settings.json
                    .claude/hooks/protect-l0.py
Current statement:  see "Current decision" below, per file
Suggested change:   see "Change" below, per file
Reason:             the two-plane architecture is in force, and these four files - which an agent
                    may not write - still carry one active contradiction of it, one overstated
                    claim, a missing ADE, and enforcement holes an audit reproduced
Impact:             instruction plane and Claude Code real-time enforcement; no governed context,
                    no ADR, no change to what the architecture is
Risk:               see "Risk"

Status: Requires Solution Designer approval - by running the promotion script
```

## Current decision

| File | What it says or does today |
|---|---|
| `AGENTS.md` | Does not name the Antigravity overlay that the registry, the overlay files and the suite already ship. States that "Git is the one enforcement point every ADE shares". Lists the human's decisions without the Git hook, the freeze marker or the governance ledger |
| `gtt-domain/change-request.md` | Sends "adding/removing an Epic/Story, or materially changing one" through a change request, and speaks of moving a Story `Ready` → `In Progress` → `Done`. This is the one **active** rule left that puts a Story behind governance |
| `.claude/settings.json` | Denies `Edit` / `Write` on the contract, the change request, the source brief and the hook machinery. Not on `gtt-domain/.frozen` and not on `gtt-domain/governance-backlog.json` |
| `.claude/hooks/protect-l0.py` | Reproduced with real PreToolUse payloads: lets an agent remove or write the freeze marker; edit the governance ledger; run a promotion script spelled any way but `bash <path>`; `git apply` a staged patch; overwrite a governed file when the same command names a file under `proposals/`; skip an installed Git hook; and loses `BLOCKING` boundaries without a word when the observation engine cannot be imported |

## Change

**`AGENTS.md`**

- The Antigravity overlay, exactly as designed in `PROPOSAL-antigravity-ade-support.md`: the
  workspace layout, *Adapters vs. portable core*, *Multi-ADE participation*, *Conflict policy*
  and the installed-overlay list. These are the five modifications of
  `AGENTS-antigravity.patch`, carried here because the closure is a single commit and that
  script needs a clean `AGENTS.md`.
- The Git hook is "the first control every ADE shares", not the one enforcement point: a local
  pre-commit hook is skipped with `--no-verify`. The guaranteed layer is CI.
- *The decisions are the human's* now also names `gtt-git-hook.sh install | remove --apply`,
  and that an agent never writes `gtt-domain/.frozen` or `gtt-domain/governance-backlog.json`.

Nothing in *The two planes* or *Backlog* changes meaning.

**`gtt-domain/change-request.md`**

- The front door is for the governed design and for Epics. Stories are out of it, explicitly.
- Vocabulary `Planned` → `In Progress` → `Done`; `Ready` is not reintroduced.
- A governed change ends in a new freeze.
- The template line `Change: <...>` stays in the form `gtt-status.sh` recognises as empty.

**`.claude/settings.json`**

- Four entries added to `permissions.deny`: `Edit` and `Write` on `/gtt-domain/.frozen` and on
  `/gtt-domain/governance-backlog.json`. Hook registrations are untouched.

**`.claude/hooks/protect-l0.py`** (whole file, staged)

Its decisions now come from one decision core that is byte-identical to the one in
`.gtt/scripts/gtt_protect.py`. Every denial names its rule.

| Fix | What is denied | Rule named |
|---|---|---|
| F1 | Writing or removing `gtt-domain/.frozen`, in both regimes, by tool or by shell (`rm`, `mv`, `cp`, `tee`, redirect, `git rm`, removing `gtt-domain/` whole) | `freeze-semantics` |
| F2 | Writing `gtt-domain/governance-backlog.json` directly, by tool or by shell | `human-decision-authority` |
| F3 | Running `gtt-domain/proposals/apply-*.sh` as `bash`, `sh`, `source`, `.`, `./path`, an absolute path, `env bash`, `cat … \| bash`, `bash -c "…"`; `git apply` / `git am` / `patch` on a file staged under `proposals/` (not with `--check`, `--stat`, `--numstat`, `--summary`, `--dry-run`) | Human Promotion Boundary |
| F3 | A governed path named in a command that also names a file under `proposals/` (each path is now judged on its own) | governed paths |
| F5 | Only while the GTT pre-commit hook is installed: `git commit --no-verify` / `-n`, `core.hooksPath` by `git config` or `git -c`, deleting the hook. Always: `gtt-git-hook.sh install \| remove --apply` | `explicit-blocking`, `human-decision-authority` |
| F6 | Nothing is denied. If the project is frozen, `stack.md` declares a `BLOCKING` boundary and `gtt_observe` cannot be imported, the write is allowed **with a visible warning** that it was not checked | `explicit-blocking` |
| F7 | Nothing new is denied: the two engines now decide alike. The portable engine stops denying a read-only command that merely redirects its own output; the Claude hook additionally protects `.cursor/hooks.json`, `.openhands/hooks.json`, `.agents/hooks.json` and `gtt_protect.py`, as the portable engine already did | parity |

What keeps working, and is tested: `src/` and `gtt-domain/proposals/` writable; the pre-freeze
regime writable; reading governed files, scripts and patches; `gtt-observe.sh observe | check |
backlog`; `git apply --check`; a non-blocking boundary; an ordinary `git commit`.

## Reason

`profiles.json` declares `freeze-semantics`, `human-decision-authority`, `explicit-blocking`
and `protected-artifacts` as invariants enforced by hook. The audit showed the Claude Code hook
- the only overlay the registry declares `realtime-hook` - did not do what those invariants say,
and that it had no test at all. The fixes are not new capabilities: each closes the distance
between what the contract declares and what happens.

## Impact

- Agents on Claude Code lose seven ways of rewriting the authority they work under. Ordinary
  work is unaffected.
- `AGENTS.md` grows by about 20 lines. It was already over Codex's 32 KiB limit (decision D-2).
- No governed context changes, no ADR is recorded, the freeze state is untouched.
- The already-applied two-planes package is not touched.

## Risk

| Risk | How it would show | Mitigation |
|---|---|---|
| The new hook denies legitimate work | A denial that names a rule, on a command that only reads | 59 shared cases run against both engines, including the positives that must not break; the hook fails open on any unexpected input |
| The hook is proven only outside Claude Code | The suite feeds it the PreToolUse payload on stdin; it does not run Claude Code | After applying, the acceptance suite runs against the installed hook; the registry keeps `realtime-hook` only for what was verified in runtime before |
| A write the hook cannot see | `python -c "open(...)"`, `git checkout <ref> -- <path>` | Not chased with patterns: `gtt-check-stack.sh` fails in CI on a removed or rewritten freeze marker |
| The patch no longer applies | `git apply --check` fails | The script stops before writing anything |

## Alternatives considered

| Alternative | Why it loses |
|---|---|
| Run `apply-AGENTS-antigravity.sh`, then a closure package | That script requires `AGENTS.md` without uncommitted changes, which a single final commit rules out. One package, one human act |
| Make the Claude hook import the portable engine | A missing or broken `.gtt/scripts/` would then switch all of Claude Code's protection off. Two copies of one core, with a test that fails when they differ, keeps the hook standalone |
| Deny more shell patterns for the residual (interpreters, Git plumbing) | An arms race with regexes, and more false positives on ordinary work. CI is the layer that holds |
| Protect `.gtt/scripts/**` and the instruction plane too | That is decision D-1 and is the Solution Designer's; this package does not take it |

## Affected files

```text
AGENTS.md                         42 lines changed (patch)
gtt-domain/change-request.md      49 lines changed (patch)
.claude/settings.json             4 lines added (patch)
.claude/hooks/protect-l0.py       whole file, from closure-1.3.1/claude-adapter/protect-l0.py
```

Exact numbers: `git apply --stat gtt-domain/proposals/closure-1.3.1/closure-1.3.1.patch`.

## To apply

```bash
bash gtt-domain/proposals/apply-bootstrap-1.3.1-closure.sh
```

It shows the full diff, asks you to type `apply`, and applies everything or nothing. Running it
is your decision. The agent has not promoted anything.
