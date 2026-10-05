# GTT — GitHub Copilot integration

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

> **Known limitation:** GitHub Copilot's actual, documented discovery path
> for repository-wide custom instructions is `.github/copilot-instructions.md`
> — Copilot does not read `.copilot/copilot-instructions.md` automatically.
> This project deliberately keeps the file at `copilot/` instead, for
> consistency with the other adapter directories (`.claude/`, `.kiro/`)
> being named after the tool. That trade-off is a project decision, not a
> GTT limitation: automatic loading does not happen at this path today: if
> you need Copilot to actually pick these instructions up on its own,
> mirror this file to `.github/copilot-instructions.md` as well.

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
are governed paths owned by the Solution Designer. GTT has no deterministic
write-block adapter for Copilot today — this is an instruction, not an
enforced guardrail, so treat it as binding anyway. To propose a change,
write a draft under `gtt-domain/proposals/` and follow the change process in
`AGENTS.md`; never edit the governed paths directly, and never work around
this by renaming, duplicating, or editing them through another path.

The same applies to any file, class, or method carrying a `@GTTGuard`
marker (listed in `.gtt/protection/registry.yaml`) — see `AGENTS.md` →
*Protected artifacts (GTTGuard)*. Copilot has no real-time block for this
either; `.gtt/scripts/gtt-check-protection.sh` in CI is the actual
enforcement, so treat the instruction as binding regardless.

## Implement against the written Story

Before writing code, establish the Story in `gtt-domain/backlog.md`. It must
be `Ready` or `In Progress` — designed and approved, with every field of the
*Story Ready* definition written. An `Undesigned` Story is not implementable:
its Epic goes through the design stage first (`AGENTS.md` → *Backlog
governance*). Implement only what is written; if something not written is
needed, stop and update the Story first.

Read what the Story's `Governed by` points to before writing code. When its
tests pass and its acceptance criteria hold, close it in the backlog:
`Status: Done` and `Closed: <date> — <commit or PR> — <tests passed>`, from
what actually happened. An Epic is `Completed` only when every one of its
Stories is `Done` or `Cancelled`.

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
