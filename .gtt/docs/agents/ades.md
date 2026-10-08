# ADE adapters and multi-ADE participation

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Part of the agent contract. `AGENTS.md` points here, and what this file says binds exactly as if it
were written there. A section named in *italics* that is not in this file is a section of
`AGENTS.md` or of another file in this directory.

## Adapters vs. portable core

GTT ships a portable core — this file, `readme-gtt.md`, `readme-gtt.es.md`,
and `SOURCE-BRIEF.*` (if a source document existed) at the project root, plus
the governed domain (`gtt-domain/`) and the GTT Engine (`.gtt/`, including
`.gtt/docs/` and `scaffold/manifest.yaml`) — plus

one adapter per supported ADE: Claude Code → `.claude/`, Kiro → `.kiro/`,
Codex → `AGENTS.md` alone, GitHub Copilot → `.github/instructions/gtt.instructions.md`,
Cursor → `.cursor/rules/gtt.mdc`, `.cursor/rules/gtt-implementation.mdc` and
`.cursor/hooks.json`, OpenHands → `AGENTS.md` plus `.agents/skills/gtt/SKILL.md` and
`.openhands/hooks.json`, Antigravity → `AGENTS.md` plus `.agents/rules/gtt.md`,
`.agents/rules/gtt-implementation.md` and `.agents/hooks.json`. For Cursor, OpenHands and
Antigravity GTT owns exactly those files, never the rest of the host's `.cursor/`,
`.agents/` or `.openhands/`; `.agents/` is shared between ADEs and with the host.
The GTT Bootstrap source carries every adapter as a catalog; a target
project receives the portable core plus the adapter of every ADE its human
chose to have participate (see *Multi-ADE participation*) — never the whole
catalog, never an adapter nobody chose.

Detecting an ADE and choosing it are different acts. Base detection on the
environment actually present, never on the underlying model (a Claude model is
not Claude Code; a GPT model is not Codex). Adapter files that merely happen to
exist in the target repo, or an ADE binary on the PATH, make an ADE a
*candidate* — nothing more. Which ADEs participate and which one is Primary is
the human's decision; if it cannot be established, ask — do not guess. Full
resolution procedure: the `gtt-bootstrap` skill.

## Multi-ADE participation

One GTT governance model; several ADE integration surfaces; one Primary ADE. A
project may have one ADE or several — the governance, the governed artifacts and
the Human Promotion Boundary are the same for all of them.

| Term | Meaning | Recorded |
|---|---|---|
| Detected ADE | A candidate: its files or binary were observed. Never installed, authorized, governed or participating by itself. | never (an observation) |
| Participating ADE | An ADE the human explicitly chose to have GTT govern. It gets its overlay. | `.gtt/ade.json` |
| Primary ADE | Exactly one participating ADE, chosen by the human: the principal AI development environment of the project's workflow. | `.gtt/ade.json` |
| Excluded ADE | A registry ADE the human declined. A re-run never reintroduces it unless the human says so. | `.gtt/ade.json` |

**The Primary ADE holds no authority.** It identifies the principal environment of
the workflow and nothing else: it does not outrank, approve, arbitrate between or
speak for any other ADE, and it has no more authority over a governed artifact than
any participating ADE — which is none: every ADE prepares, none ratifies. GTT has no
ADE hierarchy, agent voting or arbitration, and none may be introduced.

Instruction files and overlays — `AGENTS.md`, `.claude/`, `.kiro/`, `.github/instructions/`,
`.codex/`, and any ADE's memory, session history or notes — are integration
surfaces. They let an ADE take part in GTT; they never become a source of
governance authority. Several agents may run at the same time (for example three
terminals in one editor), so every participating ADE receives its integration
surface; governance never depends on the Primary being the one that is active.

The ADE registry — which ADEs exist, where each integrates, what it owns, how it
is detected, what enforcement it really has — is the `overlays:` section of
`.gtt/scaffold/manifest.yaml`. The per-project choice is `.gtt/ade.json`. Both are
read and written only through `.gtt/scripts/gtt-ade.sh` (`list`, `detect`, `state`,
`validate`, `owned`, `install`, `adopt`, `set-primary`, `record`, `remove`,
`update`); a CLI or an agent consumes that contract and never invents an
ADE-specific path. Every mutating command is a dry run without `--apply`, never
overwrites a file GTT did not install, and rolls back on failure. `.gtt/ade.json`
records the files GTT itself installed, with hashes, so a clean or an
`export --clean` removes exactly those and never the host project's own ADE
configuration; a directory whose name merely resembles an ADE's is not GTT's.

Cursor, OpenHands and Antigravity document hooks that can block a tool call before it runs.
GTT ships one for each (`.cursor/hooks.json`, `.openhands/hooks.json`,
`.agents/hooks.json`), all pointing at
one ADE-neutral engine, `.gtt/scripts/gtt_protect.py`, which applies the same rules as
Claude Code's hooks - governed paths, the freeze regime, promotion scripts, GTTGuard -
answers in each ADE's own shape, fails open, and injects the session context at session
start where the ADE has such an event (Antigravity has none; its rule tells the agent to
run `.gtt/scripts/gtt-session-context.sh`). They are built from each ADE's documented contract and tested against it, but
not verified inside the ADE: the registry states `realtime-hook-unverified`, and until
one is proven there the CI gate is the only guaranteed layer for that ADE. The
instruction binds on its own, whether or not the hook fires. Antigravity documents its
hooks for its CLI, IDE and desktop app; none of the three is proven, and a host that
already has its own `.agents/hooks.json` is a conflict to report, never a merge.

Only Claude Code has a verified real-time write block. Every other participating ADE is
governed by its instructions plus the CI gate (`gtt-check-protection.sh`):
governed is not the same as hard-blocked, and no ADE is credited with a guarantee
it does not have.
