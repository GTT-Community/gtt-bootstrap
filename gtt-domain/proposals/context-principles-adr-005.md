# Principles

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Design principles in force. A principle earns its place only if it rules
something out. If a principle would never cause you to reject a pull request,
delete it.

## Format

Each principle: the rule, then the trade-off it accepts. See *Principles in
force* below for real entries in this shape.

## Principles in force

- **GTT Core provides the service; ADE adapters provide the integration** —
  rules out duplicating GTT logic inside an adapter. Accepts an extra
  integration layer per ADE.
- **Indexes are derived, never a source of truth** — rules out using
  `technical-index.json` as authority for content or decisions. Accepts the
  cost of regenerating it after every Markdown change.
- **Identity is separate from content** — rules out relying on the physical
  path as an artifact's permanent identity. Accepts maintaining an identity
  manifest and path history.
- **Proposal ≠ decision** — rules out an agent automatically turning a
  proposal into ratified governance. Accepts requiring human intervention
  for promotion.
- **Evidence ≠ ratification** — rules out treating a technical execution or
  an adapter declaration as a human decision. Accepts keeping static/runtime
  evidence separate from authority.
- **Session Memory is operational state, not authority** — rules out using
  `gtt-domain/session.md` as a source of decisions, evidence, or grounding. Accepts it
  as an artifact derived from the repository's real state.
- **Human Promotion Boundary** — rules out agents automatically promoting
  context/ADRs to a ratified state. Accepts the cost of an explicit human
  promotion step.
- **GTT Core is repository-native and ADE-agnostic** — rules out the Core
  depending on any specific ADE. Accepts ADE-specific adapters for each tool.
- **One governance model, many integration surfaces** — rules out an
  ADE-specific governance path, an ADE hierarchy, and treating an instruction
  file, overlay or ADE memory as authority; the Primary ADE is a workflow
  identifier. Accepts that ADEs other than Claude Code are governed by
  instructions plus the CI gate, not a real-time block.
- **The Bootstrap owns its contracts; the CLI consumes them** — rules out a CLI
  carrying ADE-specific paths or a copy of a Bootstrap template. Accepts that
  every such interaction goes through a deterministic Engine script.
- **Detection is not participation** — rules out treating an ADE found on the
  machine or in the repository as installed, authorized or governed. Accepts a
  human confirmation step before any overlay is installed.

## Examples of the right shape

- **Boundaries are enforced at compile time, not by convention** — rules out
  cross-module imports that rely on discipline. Accepts: more ceremony when
  adding a module.
- **Failure is explicit in the type signature** — rules out exceptions as
  control flow. Accepts: more verbose call sites.

## Anti-examples

"Write clean code", "prefer simplicity", "follow best practices". These rule
nothing out and cost context tokens to carry.

---
Governance: L0. Read-only for AI agents.
