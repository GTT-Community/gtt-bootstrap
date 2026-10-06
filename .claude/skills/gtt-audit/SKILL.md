---
name: gtt-audit
description: Audit whether the governed context under gtt-domain/context/ still matches the actual codebase, and whether gtt-domain/backlog.md is reconciled with defined Epics. Use when the user asks to check context freshness, verify the docs are still accurate, review architectural drift, reconcile the backlog, or run a GTT audit — typically before a release, after a large merge, or when onboarding to an unfamiliar repo. The judgment counterpart of observation: the engine (gtt-observe.sh) computes what crossed a declared boundary; this audit judges what it means and what no boundary covers.
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Audit context freshness

> **Speaking for GTT.** Every message this skill raises to the human — a
> question, a confirmation, a proposal, a finding, a request for
> authorization, a report — opens with `@gtt · <what this is>`
> (e.g. `@gtt · Audit report`). The marker says who is speaking; it is never a decision.

Stale context is worse than no context: it makes every agent in the project
confidently wrong. This audit compares what the governed context claims against
what the repository actually does.

## Procedure

1. Read `gtt-domain/context/stack.md` first — it is the densest set of falsifiable
   claims and most drift shows up there.
2. Read `architecture.md`, `principles.md`, `constraints.md`, and
   `solution-vision.md`.
3. Read the accepted ADRs in `gtt-domain/adr/`.
4. Inspect the repository: dependency manifests, folder structure, deployment
   and pipeline definitions, module boundaries and their actual imports.
5. For each claim in the context, classify it.

## Checking the stack map specifically

| Map section | Check against |
|---|---|
| Stack at a glance | dependency manifests, lockfiles, image tags |
| Component map | actual network calls and client instantiations |
| Deployment topology | IaC files, pipeline definitions, or the live environment |
| Observability | actual exporters, collector config, alert rules in the repo |
| Dependency rules | real import graph |
| Map change log | one row per accepted ADR — missing rows mean skipped governance |

Every row in "Stack at a glance" with no ADR in its "Locked by" column is a
finding: a decision that entered the system without passing through governance.

## The boundaries sweep

This is not a second, independent drift mechanism - it is the full sweep of
the same observation loop that runs after a write. One boundaries block, one
engine, one response skill.

Run `bash .gtt/scripts/gtt-observe.sh observe --verbose`, then
`bash .gtt/scripts/gtt-observe.sh backlog`. The engine computes, against the
freeze baseline, every file that crossed a declared boundary, every dependency
added since the freeze, every forbidden pattern, a moved governed state and a
changed `@GTTGuard` artifact. Do not re-derive any of that by reading diffs:
facts a script can compute are the script's.

What is left for this audit is judgment the engine cannot make: for each open
observation, whether it contradicts `gtt-domain/context/` or an accepted ADR;
and what the declared boundaries do **not** cover - code that carries
architectural weight but that no rule watches is an *Orphaned* finding, and so
is an empty `gtt-boundaries` block in a project with real architecture.

If `stack.md` declares no boundaries, say so as a finding - observation then
only knows the built-in ones - and continue with the rest of the audit.

On finding a divergence, do not draft the proposal yourself. Invoke the
`gtt-drift-response` skill to assess and draft it. One skill writes proposals
for drift, regardless of whether it was found by a write-time warning, this
sweep, or a direct question — that is what keeps drift from being defined
twice and the two definitions ageing apart.

## Backlog reconciliation

`gtt-domain/backlog.md` is not architecture, but it is still expected to stay honest.
Run `.gtt/scripts/gtt-check-backlog.sh` first for the deterministic part
(duplicate Epic/Story IDs, invalid status values, an Epic that is `Planned`,
`In Progress` or `Completed` without its `Goal` or its `Approved`, a
`Completed` Epic with open Stories; and, reported without failing, a `Done`
Story without `Closed` and work under an Epic still `Proposed`) — do not
re-derive that by hand. Stories are the working plan: do not audit how they
are written. Then check what only judgment can catch:

| Check | How |
|---|---|
| Defined Epic absent from backlog | Compare against requirements docs, issue trackers, or prior conversation the Solution Designer points you at |
| Backlog Epic with no corresponding defined requirement | Ask whether it is real or should be removed — do not delete it yourself |
| Epic with no Stories | `gtt-check-backlog.sh` already warns; confirm whether that is temporary (freshly proposed) or stale |
| Completed work not reflected in backlog | Compare recent commits/PRs against Story status; a merged feature with no `Done` Story is a finding |
| Backlog references to obsolete artifacts | A Story naming a file, module, or decision that no longer exists |
| Work under an Epic that is still `Proposed` | `gtt-check-backlog.sh` reports it: the scope being built was never approved - a finding for the Solution Designer, not a reason to stop the work |
| An Epic whose goal or scope no longer matches what is being built | Compare the Epic's `Goal` / `Scope` with the Stories closed under it and with the code; scope that grew without a decision is a finding |
| Closure that the repository does not support | Open each `Done` Story's `Closed`: the commit or PR exists and the tests it names pass; a closure nobody can trace is a finding |
| Story contradicting governed context or an ADR | Same severity as architectural drift — see *Precedence* in `AGENTS.md` |

Report findings. An Epic is governed: do not add, remove or "fix" one
yourself — a correction to an Epic's goal, scope or approval goes through
`gtt-propose-change` (form 4). Stories are not audited as authority: they are
the working plan of whoever does the work, so code that goes beyond what a
Story says is not a finding, and neither is a Story nobody "defined". What
this audit does report about Stories are facts - a `Done` Story whose `Closed`
nobody can trace, a reference to an artifact that no longer exists - and
whoever does the work corrects them directly in `gtt-domain/backlog.md`; no
proposal and no approval are involved.

## Classification

| Verdict | Meaning |
|---|---|
| Confirmed | The code matches the claim |
| Drifted | The code contradicts the claim |
| Unverifiable | The claim is too vague to check against code |
| Orphaned | The code does something significant that no context file covers |

Drift and orphans are the findings that matter. `Unverifiable` is a finding too:
it means the context is written in language too soft to govern anything, and it
should be rewritten to be concrete.

## Output

```text
GTT Context Audit — <date>

Stack map
  <row> — map says X, repository shows Y — evidence: <path:line>
  Rows with no governing ADR: <list>

Drifted
  <file> — claims X, code does Y — evidence: <path:line>

Orphaned
  <what the code does that context never decided> — evidence: <path>

Unverifiable
  <file> — claim is not concrete enough to check

Observation
  gtt-observe.sh: <open observations by level; BLOCKING and rejected ones listed>
  Boundaries declared: <count> - not covered by any boundary: <list>

Confirmed
  <count> claims verified

Backlog
  gtt-check-backlog.sh: <OK / FAILED, summary>
  Epics awaiting approval: <list>
  Epics whose scope no longer matches the work: <list>
  Defined but missing from backlog: <list>
  In backlog but no defined requirement: <list>
  Stale / contradicts governed context: <list, with evidence>

Recommended action
  <per finding: update context, revert code, open an ADR, or process a
  backlog change through gtt-propose-change>
```

Report only. Do not edit `gtt-domain/context/`, do not fix the drift in code, and do
not soften a finding because the code looks reasonable. The Solution Designer
decides whether the context or the implementation is the thing that is wrong.
Divergences found by the boundaries sweep are handed to `gtt-drift-response`
to draft, not drafted here. Structural backlog findings are handed to
`gtt-propose-change` (form 4), not resolved here either.
