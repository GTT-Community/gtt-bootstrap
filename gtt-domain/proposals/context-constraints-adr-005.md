# Constraints

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Hard limits this solution must respect. This file is loaded into every AI
session, so keep it short and concrete: only constraints that would change a
decision. Delete every line you have not actually committed to.

## Platform

- Cloud provider: none
- Compute model: none — runs as scripts/tooling inside the repository; not
  deployed as a service (see `stack.md` → *Compute model*)
- IaC tooling: none: no infrastructure is provisioned

## Technical

- Runtime and language version: Bash (Core scripts, CI gate) + Python 3
  (engine components, hooks); no version pinned, no single application
  runtime (see `stack.md` → *Language / Runtime*)
- Datastore: none — filesystem-based; `.gtt/index/artifacts.json` (identity
  manifest) and `.gtt/index/technical-index.json` (derived index, never a
  source of truth) are the closest equivalent
- Communication style: neither — no network API and no messaging; components
  communicate via filesystem, Bash/Python script invocation, and
  Markdown/JSON artifacts (ADE adapters invoke `gtt-session-context.sh`
  directly)

## Regulatory and organizational

- Data residency: not applicable
- Compliance regime: none declared
- Budget or quota ceilings that constrain design: none declared

## Explicitly out of scope

- Not a deployable business application.
- Does not provision infrastructure.
- Does not define or implement an external identity service.
- Does not implement an external datastore.
- Does not implement messaging/events.
- Does not claim to verify the runtime of an ADE that is not
  installed/available.
- Does not turn Session Memory into agent memory or authority.
- Does not allow agents to ratify or freeze human decisions.
- Does not create ADE or agent governance: no ADE hierarchy, voting or arbitration. The Primary ADE is a workflow identifier and holds no authority; instruction files, overlays and ADE memory are integration surfaces, never governance authority.

---
Governance: L0. Read-only for AI agents. Changes require Solution Designer
approval via the `gtt-propose-change` skill.
