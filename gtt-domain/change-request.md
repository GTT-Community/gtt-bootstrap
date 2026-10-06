# Change Request

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

**This is the front door. To change anything governed — stack, architecture,
principles, constraints, vision, product-level design intent, or an Epic in
`gtt-domain/backlog.md` (adding or removing one, or materially changing its
goal or scope) — write it here and nowhere else.**

This file is not a decision log and not a pull request. It is a formal request
for a governance review. The agent may read it, analyze it, and draft a
proposal, but it does not modify the governed context, the ADRs or an Epic's
goal, scope or approval directly.

It is not a door in front of ordinary work. Implementation, refactors, tests
and Stories never pass through here: a Story is the working plan of whoever
does the work, and nobody approves one.

Overwrite the block below each time. This file is a desk, not an archive — the
history lives in `gtt-domain/adr/` for architecture and in `gtt-domain/backlog.md` itself
for Epics.

---

## GTT Request

```text
Change: <what needs to change in the design, the system architecture, or an Epic's goal or scope>
Reason: <why this change is needed>
Trigger: <what event caused the request: bug, cost, limit, requirement, review, etc.>
Scope: <what is included and what is intentionally out of scope>
Impact: <systems, modules, teams, dependencies, adoption cost, migration implications>
Risk: <technical, operational, delivery, and adoption risk>
Priority: <critical / high / medium / low>
```

### Example

```text
Change: Introduce OAuth2-based authentication with multi-tenant SSO support.
Reason: The current system depends on local credentials and does not scale for clients with centralized identity policies.
Trigger: New business requirement and a security audit.
Scope: Changes the authentication flow, the session layer, and provider configuration; does not modify internal domain business logic.
Impact: Affects access services, session management, environment configuration, and the onboarding experience.
Risk: High, due to compatibility with existing users, integration with external providers, and possible migration failures.
Priority: High
```

---

## How to use this

1. Fill in the request block above with the architectural intent, or the
   change to an Epic.
2. Tell your agent: *"process the change request"*.
3. The agent reads this file and the relevant governed context (or
   `gtt-domain/backlog.md`, for an Epic), then writes a full proposal to
   `gtt-domain/proposals/`.
4. Review the proposal. Reject it, request changes, or approve it.
5. On approval: an architecture/context change gets an ADR and the exact
   stack map delta, which you apply, and is completed by a new freeze
   (`gtt-freeze.sh`). An Epic change is written into `gtt-domain/backlog.md`
   with your approval — it does not get an ADR unless it also touches governed
   context.

If you are only asking a question ("is this even possible?", "what would this
cost us?"), ask in chat instead. This file is for changes you intend to make.

Stories do not belong here either. Creating, splitting, rewriting and closing
them (`Planned` → `In Progress` → `Done`) is the working plan of whoever does
the work — never a change request. In the backlog this file is only for
adding, removing or materially changing an Epic, the same bar as an
architectural change.

## What does not belong here

Implementation work. Bugs, feature requests, refactors inside existing
boundaries, and anything under `src/` never belongs here — that is L3 and can be
handled directly in implementation. Stories and their status don't belong
here either, for the same reason.

If you find yourself filling this in for routine work, the constraints in
`gtt-domain/context/` are written too broadly. Narrow them.
