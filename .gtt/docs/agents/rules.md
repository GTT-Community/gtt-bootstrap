# GTT agent contract — every rule

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

Part of the agent contract: these rules bind exactly as `AGENTS.md`, which states them grouped as ten invariants. When a rule here is more specific, it is the one that applies.

## Every non-negotiable rule

- Never guess architecture.
- Never map a design below the minimum floor (stack and datastore decided) into governed context, and never let a confirmation that it is finished lift the floor.
- Never rewrite the human's design documents, never write a stack option or recommendation as a decision, and never recommend a stack that does not follow from what the project's own documents state.
- Never select, infer, raise or lower the THINK Depth on the human's behalf - not from the Autonomy Profile, not from the project's size - and never treat a depth as permission to skip the floor, a provenance tag, a human decision or the freeze.
- Never choose between several design documents, or between consolidating them and keeping them as sources, on the human's behalf.
- Never silently overwrite.
- Never silently move GTT artifacts.
- Never claim a decision was approved when it was not.
- Never treat generated context as ratified without human confirmation.
- Never run a promotion (`gtt-promote.sh`, or a promotion script), or apply its changes by any
  other means, on the agent's own initiative — see *Human Promotion Boundary*.
- Never treat a drafted proposal, ADR, or promotion set as approval for the
  next one; each governed promotion requires its own explicit human decision.
- Never delete `AGENTS.md`.
- Never bypass governed protection after freeze.
- Never treat a detected ADE as installed, authorized, governed or participating; only the human's explicit choice makes an ADE participate.
- Never install an adapter for an ADE the human did not choose, and never reintroduce one a prior run excluded unless the human says so.
- Never infer the participating or Primary ADE from the underlying model, from adapter files that merely happen to exist, or from a binary on the PATH; ask if it cannot be established with confidence.
- Never give the Primary ADE, or any ADE, authority over a governed artifact, and never introduce an ADE hierarchy, agent voting or arbitration.
- Never write a `[PROPUESTA]` inside governed context, never leave a `[VACÍO]` unclassified there, and never use an OPEN gap — or the precedence of a source — as authorisation to change a frozen design or to hide a `[CONFLICTO]`.
- Never let a working preference override governed context, never author your own preferences, and never commit `.gtt/local/preferences.md`.
- Never treat an instruction file or ADE overlay (`AGENTS.md`, `.claude/`, `.kiro/`, `.github/instructions/`, `.codex/`, ADE memory or session history) as governance authority.
- Never hand-edit `.gtt/ade.json`; write it only through `.gtt/scripts/gtt-ade.sh`. Never remove an ADE path GTT did not install.
- Never copy the Initial Design Questionnaire, or its methodology, out of the Bootstrap, and never write a `[PROPUESTA]` or an ADE inference as a confirmed decision.
- Never change the ratified development method; propose it via a change request.
- Never select, default, infer or change the Autonomy Profile on the human's behalf; never present a plan as a quality level; never report the unselected fallback as a choice; and never treat any plan as weakening an invariant or as permission to skip a human confirmation.
- Never turn deterministic work into a question, never stop at an intermediate mechanical step, and never use lower friction as a reason to skip a human confirmation, a gate or the Human Promotion Boundary.
- Never raise a question, a confirmation, a questionnaire turn, a proposal, an authorization request or a report on behalf of GTT without opening it with `@gtt · <what this is>`; never put the marker on ordinary work; and never treat the marker as a decision, an approval or evidence.
- Never ask for approval of ordinary work - implementation, refactors, tests, Stories - and never turn it into a proposal, a confirmation or a change request.
- Never stop work for an observation that is not `BLOCKING`, and never treat anything as blocking without an explicit governance basis you can name.
- Never decide an observation and never freeze: `gtt-observe.sh accept | reject | defer` and `gtt-freeze.sh` are the human's.
- Never establish by judgment a fact a script can compute, and never act as the governance supervisor of another agent.
- Never read freeze as "the code cannot change", and never look for an unfreeze: a governed change is completed by a new freeze.
- Never invent Epics and present them as user-defined requirements, never write an Epic's `Approved`, and never add or remove an Epic or change its goal or scope without the human's decision.
- Never let an Epic or a Story in `gtt-domain/backlog.md` silently override governed context or an accepted ADR.
- Never copy governed context into the backlog, and never treat the backlog as a source of architecture.
- Never write a Story's closure you did not verify, and never mark an Epic `Completed` while one of its Stories is open.
- Never generate a scaffold artifact (`gtt-domain/change-request.md`, `gtt-domain/backlog.md`, `gtt-domain/session.md`, or the files under `.gtt/docs/`) at a temporary location and move it into place afterward — write it where `.gtt/scaffold/manifest.yaml` places it, directly.
- Never bypass a GTTGuard-protected artifact's approval requirement — not by renaming or removing its marker without authorization, not by editing around the enforcing hook, and not by hand-editing `.gtt/protection/registry.yaml`.
- Never treat approval of one GTTGuard proposal as authorization for a different protected artifact, and never confuse its lightweight, in-conversation promotion with the L0/L1 Human Promotion Boundary.
