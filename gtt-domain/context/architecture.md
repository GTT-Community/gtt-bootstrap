# Architecture

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

The current architecture of this solution. Loaded on demand, not at session
start — so it can be longer than `constraints.md`, but every section should
still be something an agent would act on.

## Architectural style

<layered / hexagonal / event-driven / microservices / modular monolith>

State the style explicitly. Ambiguity here is what produces silent paradigm
drift.

**Development method (Method Lock).** Say in words which method or combination
of Method Packs (`.gtt/methods/`) the design follows, and why. Then record the same
choice in the block below, which scripts read: `.gtt/methods/README.md` → *The Method
Lock* has the format. `OPEN` is a valid value; an empty block declares no method.
The freeze ratifies it; afterwards it changes only through a change request.

```gtt-method
# style: one or more Method Pack ids (question: development), comma separated - or OPEN
# start: a Method Pack id (question: start), direct - or OPEN
# status: ratified | open
# locked_by: ADR-NNN when a chosen pack requires an ADR, otherwise none - OPEN while open
# verification: the weakest verification level of the chosen packs
# gap: GAP-NNN - only while open: the OPEN gap whose topic is Development method
```

## Modules and boundaries

| Module | Responsibility | May depend on | Must not depend on |
|---|---|---|---|

## Integration strategy

How modules and external systems talk to each other. Protocols, contracts,
where the boundaries are enforced.

## Data model ownership

Which module owns which data. Where the write path is. What is derived.

## Deployment topology

What gets deployed as what, and to where.

## Known deviations

Places where the implementation knowingly diverges from the ideal, and why.
Recording these prevents an agent from "fixing" a deliberate trade-off.

---
Governance: L0. Read-only for AI agents. Changes go through a change request and the human's promotion;
architectural ones also need an ADR (AGENTS.md → Governed regime).
