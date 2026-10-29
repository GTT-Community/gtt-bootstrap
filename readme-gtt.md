# GTT Bootstrap

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

**GTT — Governance Through Thinking.** You decide what the system is supposed to be; the AI agent
builds it freely inside that design; GTT keeps the two apart.

> **Agent reasoning ≠ Change authorization.**

🇪🇸 [Español](readme-gtt.es.md) · Full guide: [.gtt/docs/guide.md](.gtt/docs/guide.md) · Apache-2.0

## How it works

1. **Setup** - `gtt init`: choose the ADEs you use (Claude Code, Kiro, Copilot, Cursor, Antigravity,
   OpenHands, Codex), how much GTT may do without asking (autonomy profile: Light, Medium, Hard, Team)
   and how the solution is organized (development method, e.g. Vertical Slice).
2. **Design** - open the project in your ADE and write anything. It starts from your design document,
   or interviews you with the Initial Design Questionnaire. Stack and datastore are always decided by you.
3. **Freeze** - `gtt freeze`: you ratify the design. It becomes the authority.
4. **Build** - the agent implements, refactors, tests and writes Stories without asking anyone.
5. **Observe** - GTT compares the work with the frozen design. A new datastore, framework or module the
   design does not declare, or a broken dependency rule, is reported; only what you declared BLOCKING stops.
6. **Change** - write what you want changed in `gtt-domain/change-request.md`; the agent proposes;
   `gtt promote <set>` applies your decision and freezes again. `gtt undo` reverts it.

## The commands you use

| Command | What it does |
|---|---|
| `gtt status` | Where the project is: freeze, observations, what GTT waits on |
| `gtt validate` | Every deterministic governance check (also in CI) |
| `gtt freeze` | Ratify the design (only a person, in a terminal) |
| `gtt change`, `gtt proposals`, `gtt promote`, `gtt undo` | The change flow |
| `gtt check` | Does the code respect the development method's dependency rules? |
| `gtt autonomy` | Show or change the autonomy profile |

## Where things live

| Path | What |
|---|---|
| `gtt-domain/context/` | The governed design (vision, architecture, stack, constraints...) - only you change it |
| `gtt-domain/backlog.md` | Epics (yours) and Stories (the agent's working plan) |
| `gtt-domain/change-request.md` | What you want changed |
| `gtt-domain/proposals/` | What the agent proposes |
| `AGENTS.md` | The contract every agent reads (joined to yours if you had one) |
| `.gtt/` | The engine: scripts, contracts, documentation |
| `.claude/`, `.kiro/`, `.cursor/`, `.agents/`, `.openhands/`, `.github/instructions/` | Each participating ADE's GTT integration, at the path that ADE reads (the dot is the ADE's convention, not GTT's). You may edit it by hand; the agent may not. Which files: [ADE adapters](.gtt/docs/guide.md#ade-adapters) |

More: [the full guide](.gtt/docs/guide.md) · [documentation index](.gtt/docs/index.md) ·
[development methods](.gtt/methods/README.md) · [the GTT canon](https://github.com/GTT-Community/gtt-method)
