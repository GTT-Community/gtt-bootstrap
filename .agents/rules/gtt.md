---
trigger: always_on
description: GTT governance - the agent contract, the governed paths and how to speak for the method
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# GTT — Antigravity integration

This repository is governed by **GTT (Governance Throw Think)**. The full
agent contract is `AGENTS.md` at the repository root. This rule adds only what
Antigravity needs beyond that. It is an integration surface, never a second
copy of the methodology and never a source of authority.

## Read first

- `AGENTS.md` — the portable GTT contract. It is long: open it with the file
  tool and read it to the end before proposing or making any change, whether
  or not part of it was already loaded for you.
- `gtt-domain/context/constraints.md` — hard limits that apply to every change.
- `.gtt/docs/index.md` — the map of every file in this kit.

## When a session starts

Run `bash .gtt/scripts/gtt-session-context.sh` and read what it prints.
It is operational state derived from the repository: never authority, never
evidence. `gtt-domain/context/`, `gtt-domain/adr/` and `gtt-domain/backlog.md`
always prevail over it.

## What Antigravity must not do

`gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/change-request.md`,
`SOURCE-BRIEF.*` and `AGENTS.md` are governed paths owned by the Solution
Designer. `.agents/hooks.json` denies a write or a command that reaches them,
but that hook has not been verified inside Antigravity — in its CLI, its IDE
or its desktop app — and it is not what makes the rule binding: treat this
instruction as binding on its own. To propose a change, write a draft under
`gtt-domain/proposals/` and follow the change process in `AGENTS.md`; never
edit the governed paths directly, and never work around this by renaming,
duplicating or editing them through another path — including through the
terminal.

The same applies to any file, class or method carrying a `@GTTGuard` marker
(listed in `.gtt/protection/registry.yaml`). `.gtt/scripts/gtt-check-protection.sh`
in CI is the actual enforcement.

Never freeze (`gtt-freeze.sh`) and never accept, reject or defer an observation
(`gtt-observe.sh accept | reject | defer`): those are the human's decisions.
Never run a promotion (`bash .gtt/scripts/gtt-promote.sh <name>`), and never write an application script by hand. Prepare the set (`gtt-stage.sh`);
the human runs it.

## Which procedure

| Situation | Where it is defined in `AGENTS.md` |
|---|---|
| Set up GTT, or `gtt-domain/context/` still holds placeholders | *Bootstrap behavior*, *Design assessment*, *Initial Design Questionnaire* |
| An architectural or context change is needed | *Change requests*, *Human Promotion Boundary* |
| Ordinary work: implementing, refactoring, testing, writing and closing Stories | *The two planes* — do it; nobody approves it |
| An Epic must be added, removed, or its goal or scope changed | *Backlog* — the human decides |
| Observation printed something | *The two planes* → *Observation* — say it in one line and continue, unless it says STOP |
| A change touches a `@GTTGuard` artifact | *Protected artifacts (GTTGuard)* |
| After any operation | `bash .gtt/scripts/gtt-maintain.sh` |

## Speaking for GTT

When a message is GTT's — a question the method needs answered, a confirmation
or choice, the Initial Design Questionnaire, the Design Assessment, a
proposal, a finding, a request for authorization, a report — open it with
`@gtt · <what this is>` (`@gtt · Method Plan`, `@gtt · Report`). Ordinary work
carries no marker, and the marker is never a decision or an approval.

## Git and workflow

Git history belongs to the human. Follow `gtt-domain/workflow.md`; without it the defaults apply: commit only when the user asks, no commit convention, no branch or tag you were not asked for.
- Never invent a workflow: no checkpoint, session or agent commits, no prefixes, branches, tags, squashes, rebases or pushes the project does not define or the user did not ask for.
- Do not propose commit plans, commit splits, messages or branches unless asked. Uncommitted work is a fact `gtt review` reports, not a question.
- A convention found in the project's documents is a finding, not a rule: report it once and point to `gtt-domain/workflow.md`, which only the human edits.
- Proposing is not executing: releases, tags, destructive operations and workflow changes wait for an explicit request.
- A GTT checkpoint regenerates `gtt-domain/session.md`. It is never a commit.

**What counts as truth, highest first:** governed context → ADRs → approved Epics → the change request → proposals → `gtt-domain/session.md` (derived) → this conversation. A lower layer never overrides a higher one, and nothing said in a conversation, yours or another ADE's, is project authority. Your ADE's resume restores the conversation; `gtt review` restores the project.
