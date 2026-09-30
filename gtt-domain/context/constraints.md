# Constraints

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Hard limits this solution must respect. This file is loaded into every AI
session, so keep it short and concrete: only constraints that would change a
decision. Delete every line you have not actually committed to.

## Platform

- Cloud provider: <locked to X — reason>
- Compute model: <locked to X — reason>
- IaC tooling: <X, or "none: infrastructure is provisioned manually">

## Technical

- Runtime and language version: <X>
- Datastore: <X — reason>
- Communication style: <sync REST / async events / both, and where each applies>

## Regulatory and organizational

- Data residency: <region, reason>
- Compliance regime: <X>
- Budget or quota ceilings that constrain design: <X>

## Explicitly out of scope

- <thing the solution deliberately does not do>

---
Governance: L0. Read-only for AI agents. Changes require Solution Designer
approval via the `gtt-propose-change` skill.
