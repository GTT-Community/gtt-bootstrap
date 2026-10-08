---
name: gtt-drift-response
description: Use when observation reports drift (an `@gtt · Observation` at WARNING or above, a GOVERNANCE or BLOCKING item in the governance backlog), when gtt-audit reports a divergence, or when the user asks whether a change under src/, infra/, or a dependency manifest contradicts ratified architecture. Decides whether the governed design itself must change and, only then, produces a proposal under gtt-domain/proposals/ plus a promotion script the human runs. Never a reason to stop work that is not BLOCKING.
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# GTT drift response

> **Speaking for GTT.** Every message this skill raises to the human — a
> question, a confirmation, a proposal, a finding, a request for
> authorization, a report — opens with `@gtt · <what this is>`
> (e.g. `@gtt · Drift`). The marker says who is speaking; it is never a decision.

Observation (`.gtt/scripts/gtt-observe.sh`) found that the work crossed a
boundary of the frozen design. The fact is already established - a script
computed it. What is left is the part a script cannot do: whether it means the
governed design must change, and if so, preparing that decision for the human.

This skill is the single response path for drift, whichever way it was found:
observation after a write, at session start or in validation, a `gtt-audit`
sweep, or a direct question.

**The work continues.** Unless the observation says STOP, do not pause the task
to run this skill and do not wait for an answer: tell the human in one line,
keep working, and respond to the observation when the task allows. Read the
item first - `bash .gtt/scripts/gtt-observe.sh show OBS-NNNN` - for the rule it
crossed and what that rule guards.

## Step 1 — Assess

Read the changed file and compare it against `gtt-domain/context/stack.md`,
`gtt-domain/context/architecture.md`, `gtt-domain/context/constraints.md`, and any ADR under
`gtt-domain/adr/` whose subject covers the change.

Three outcomes:

- **No contradiction.** Say so in one line and write no proposal: a proposal
  for a non-issue is noise that trains the reader to ignore the next one. The
  observation stays in the governance backlog; tell the human they can clear it
  with `bash .gtt/scripts/gtt-observe.sh accept OBS-NNNN --by <name> --apply` -
  their decision, never run by you.
- **The code is what is wrong.** The boundary stands and the change should not
  have crossed it. Fix the code; the observation resolves itself the next time
  the engine runs. This is ordinary work: no proposal, no approval.
- **Fast track.** The decision is ratified in principle; only a detail moved —
  a version bump, an added service that fits an existing dependency rule.
- **Full track.** A ratified decision is being replaced. Alternatives and
  rejection reasons matter.

## Step 2 — Draft

Write to `gtt-domain/proposals/PROPOSAL-<short-kebab-summary>.md`. No numbers:
numbering belongs to ADRs, which are the permanent record, and choosing an ADR
number would mean reserving ratified identity for your own draft.

`gtt-domain/proposals/` is the only writable governed path.

**Fast track** — minimum viable delta:

- What changed: file, before, after
- Which L0 statement or ADR it contradicts, quoted with file and line
- What the map should say instead
- The exact change-log row for `stack.md`

**Full track** — follow `gtt-domain/adr/ADR-TEMPLATE.md`: context, decision,
alternatives considered with why each loses, consequences, risks.

Status line: `Status: Requires Architect approval`. Only the human accepts.

## Step 3 — Stage the promotion package, never execute it

If the proposal is accepted (or once you know it will need to be — ask if
unclear), stage the same promotion package the `gtt-adr` skill produces,
using the same shape it defines:

- `gtt-domain/proposals/ADR-DRAFT-<slug>.md` — the ADR, following
  `gtt-domain/adr/ADR-TEMPLATE.md` for the full track, or the fast-track minimum
  delta promoted into the same template shape
- `gtt-domain/proposals/context-<basename>.md` for every affected file (`stack.md`
  at minimum, changelog row included)
- the promotion set, staged with `bash .gtt/scripts/gtt-stage.sh ADR-NNN-<slug> --reason "..." <draft>=<destination> ...`
  (never an application script written by hand); the human applies it with `bash .gtt/scripts/gtt-promote.sh ADR-NNN-<slug>`

Take the ADR number from `bash .gtt/scripts/gtt-project.sh next-id --kind adr` - do not ask for it; the
human sees it when reviewing the package. Then deliver the same brief hand-off message
`gtt-adr` uses: where the script is, what it will change, that review comes
first, the exact command to run it, and that you have not promoted anything.

## Hard rule

An observation is a signal, never a decision: you never accept, reject or
defer one, and you never treat one that is not BLOCKING as a reason to stop.


You draft and stage. The human promotes by running the script themselves.
Running the promotion yourself — or applying its changes by any other means —
would make you the ratifier of your own assertion, which is the exact failure
GTT exists to prevent.
