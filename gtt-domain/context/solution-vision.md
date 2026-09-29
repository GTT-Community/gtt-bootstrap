# Solution Vision

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

## Problem

As stated in `gtt-domain/adr/ADR-001-context-governance.md` → *Context*: "AI agents
generate implementation faster than humans review it. Without a governed
reference, the codebase becomes the de facto specification, and
architectural intent erodes one reasonable-looking commit at a time. The
erosion is invisible because every individual change is defensible."

GTT's Artifact Identity, Technical Index, and Session Memory Service (see
`.gtt/docs/docs.md` → *Artifact identity and the technical index* and
`.gtt/docs/session-adapter-contract.md`) address three further, related gaps:
identity tied to a file's path (a move looked like delete + create),
retrieval requiring whole-document scans, and session continuity with no
delivery contract to any ADE.

## Users

Per `AGENTS.md` (Mission, Agent roles, and throughout): the **Solution
Designer** (the human who owns architectural decisions, ratifies ADRs, and
runs promotion scripts and `gtt-freeze.sh`), and **AI coding agents**
operating under the Grounding/Reasoning/Validation split across the
supported ADEs — Claude Code, Codex, Kiro, and GitHub Copilot
(`AGENTS.md` → *Adapters vs. portable core*).

## What success looks like

None declared as a dedicated success-criteria statement. The closest
already-ratified, explicit statement is `ADR-001` → *Decision* and
*Consequences*: the governed context under `gtt-domain/context/` stays the source
of truth, generated code never replaces it, and disagreement between code
and context is escalated to a human rather than resolved by an agent. This
is cited here as the nearest existing signal, not restated as a new vision.

## Non-goals

See `gtt-domain/context/constraints.md` → *Explicitly out of scope* — established
during this Bootstrap by the Solution Designer. Not duplicated here to avoid
two documents that could drift apart; that section is authoritative.

---
Governance: L0. Read-only for AI agents.
