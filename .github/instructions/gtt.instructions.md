---
applyTo: "**"
---

# GTT — GitHub Copilot integration

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> **Where this file lives.** `.github/instructions/gtt.instructions.md`, with
> `applyTo: "**"`: one of the paths GitHub documents Copilot as reading from a
> repository, next to `.github/copilot-instructions.md` and `AGENTS.md`. GTT
> owns this file and `.github/hooks/gtt-protect.json`, and nothing else under
> `.github/` — the project's own `.github/copilot-instructions.md` is the
> project's.

This repository is governed by **GTT (Governance Throw Think)**. The
full agent contract lives in `AGENTS.md` at the repository root — read it
before proposing or making any change. This file adds only what Copilot
needs beyond that; it is not a second copy of the methodology, and it
should never become one.

## Read first

- `AGENTS.md` — the portable GTT contract: mission, required workspace,
  bootstrap behavior, governed regime, change process, non-negotiable
  rules.
- `gtt-domain/context/constraints.md` — hard limits that apply to every change.
- `.gtt/docs/index.md` — map of every file in this kit.

## What Copilot must not do

`gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/change-request.md`, and `SOURCE-BRIEF.*`
are governed paths owned by the Solution Designer. GTT ships a pre-tool hook
for the Copilot cloud agent and the Copilot CLI
(`.github/hooks/gtt-protect.json`), built from GitHub's documented contract
and not verified inside Copilot; other Copilot surfaces have no hook at all.
So this is an instruction first — treat it as binding whether or not a hook
stops you. To propose a change,
write a draft under `gtt-domain/proposals/` and follow the change process in
`AGENTS.md`; never edit the governed paths directly, and never work around
this by renaming, duplicating, or editing them through another path.

The same applies to any file, class, or method carrying a `@GTTGuard`
marker (listed in `.gtt/protection/registry.yaml`) — see `AGENTS.md` →
*Protected artifacts (GTTGuard)*. The same unverified hook covers it where
it runs; `.gtt/scripts/gtt-check-protection.sh` in CI is the enforcement
that holds, so treat the instruction as binding regardless.

## Work on your own; GTT observes

The implementation is yours: write, refactor, test and commit without asking
for approval. `gtt-domain/backlog.md` is your working plan - create, split,
rewrite and close Stories as the work needs; nobody approves a Story. When one
is finished, close it: `Status: Done` and `Closed: <date> — <commit or PR> —
<tests passed>`, from what actually happened. An Epic is different: its goal
and scope are the human's decision (`AGENTS.md` → *Backlog*), and an Epic is
`Completed` only when every one of its Stories is `Done` or `Cancelled`.

After a change that could touch a boundary of the design, run
`bash .gtt/scripts/gtt-observe.sh observe`. What it prints is an observation,
not an order to stop: say it in one line and continue. Only a line marked STOP
interrupts the affected operation (`AGENTS.md` → *The two planes*).

## Speaking for GTT

When a message is GTT's — a question the method needs answered, a
confirmation or choice, the Initial Design Questionnaire, a proposal, a
finding, a request for authorization, a report — open it with
`@gtt · <what this is>` (`@gtt · Method Plan`, `@gtt · Report`). Ordinary
work carries no marker, and the marker is never a decision or an approval.

## Procedures

GTT's step-by-step procedures (bootstrap, propose a change, record an ADR,
audit context) are described at a high level in `AGENTS.md` — follow those
numbered steps directly. Copilot has no on-demand procedure loader
equivalent to a Claude Code skill, so there is no separate procedure file to
fetch here. When a step calls for judgment `AGENTS.md` doesn't resolve, ask
the Solution Designer rather than improvising.

## Git and workflow

Git history belongs to the human. Follow `gtt-domain/workflow.md`; without it the defaults apply: commit only when the user asks, no commit convention, no branch or tag you were not asked for.
- Never invent a workflow: no checkpoint, session or agent commits, no prefixes, branches, tags, squashes, rebases or pushes the project does not define or the user did not ask for.
- Do not propose commit plans, commit splits, messages or branches unless asked. Uncommitted work is a fact `gtt review` reports, not a question.
- A convention found in the project's documents is a finding, not a rule: report it once and point to `gtt-domain/workflow.md`, which only the human edits.
- Proposing is not executing: releases, tags, destructive operations and workflow changes wait for an explicit request.
- A GTT checkpoint regenerates `gtt-domain/session.md`. It is never a commit.

**What counts as truth, highest first:** governed context → ADRs → approved Epics → the change request → proposals → `gtt-domain/session.md` (derived) → this conversation. A lower layer never overrides a higher one, and nothing said in a conversation, yours or another ADE's, is project authority. Your ADE's resume restores the conversation; `gtt review` restores the project.
