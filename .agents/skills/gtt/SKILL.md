---
name: gtt
description: Work inside a repository governed by GTT (Governance Throw Think). Use before changing architecture, the stack, governed context under gtt-domain/context/, an ADR, the backlog's Epics or Stories, or a GTTGuard-protected artifact; when bootstrapping GTT; when asked to process a change request; and before implementing a Story.
triggers:
  - gtt
  - gtt-domain
  - change request
  - backlog
  - ADR
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# GTT — OpenHands integration

This repository is governed by **GTT (Governance Throw Think)**. The full agent
contract is `AGENTS.md` at the repository root — OpenHands loads it into every
conversation; this skill adds only what OpenHands needs beyond that. It is an
integration surface, never a second copy of the methodology and never a source
of authority.

## Read first

- `AGENTS.md` — the portable GTT contract.
- `gtt-domain/context/constraints.md` — hard limits that apply to every change.
- `.gtt/docs/index.md` — the map of every file in this kit.

## What OpenHands must not do

`gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/change-request.md`,
`SOURCE-BRIEF.*` and `AGENTS.md` are governed paths owned by the Solution
Designer. `.openhands/hooks.json` denies a write or a command that reaches
them, but that hook has not been verified inside OpenHands and it is not what
makes the rule binding: treat this instruction as binding on its own —
including when you work autonomously with no human watching. To propose a
change, write a draft under `gtt-domain/proposals/` and follow the change
process in `AGENTS.md`; never edit the governed paths directly, never work
around this by renaming, duplicating or editing them through the terminal, and
never commit or open a pull request that changes them.

The same applies to any file, class or method carrying a `@GTTGuard` marker
(listed in `.gtt/protection/registry.yaml`). `.gtt/scripts/gtt-check-protection.sh`
in CI is the actual enforcement.

Never run a promotion script (`gtt-domain/proposals/apply-*.sh`). Prepare it
and stop; the human runs it. A governed decision is never taken in an
unattended run: when one is needed, stop and report.

## Which procedure

| Situation | Where it is defined in `AGENTS.md` |
|---|---|
| Set up GTT, or `gtt-domain/context/` still holds placeholders | *Bootstrap behavior*, *Design assessment*, *Initial Design Questionnaire* |
| An architectural or context change is needed | *Change requests*, *Human Promotion Boundary* |
| An Epic or Story must be added, removed or designed | *Backlog governance*, *Story Ready* |
| Before implementing a Story | *Story Ready* — it must be `Ready`; implement only against what is written |
| A change touches a `@GTTGuard` artifact | *Protected artifacts (GTTGuard)* |
| After any operation | `bash .gtt/scripts/gtt-maintain.sh` |

## Speaking for GTT

When a message is GTT's — a question the method needs answered, a confirmation
or choice, a proposal, a finding, a request for authorization, a report — open
it with `@gtt · <what this is>` (`@gtt · Authorization required`,
`@gtt · Report`). Ordinary work carries no marker, and the marker is never a
decision or an approval.
