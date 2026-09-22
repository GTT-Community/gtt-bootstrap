# GTT Bootstrap — Claude Execution Directive

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

## 1. Purpose

Evolve the existing `GTT-Community/gtt-bootstrap` implementation so that it operationalizes the GTT Canonical v2.1 more effectively for modern AI development environments (ADEs), including Claude Code, Codex, Kiro, GitHub Copilot and other compatible environments.

This is an **implementation task**.

The architectural and methodological direction in this document is authoritative for this task. Claude must execute it against the real repository state and must not redesign the methodology independently.

---

## 2. Authority and execution model

The authority chain for this task is:

```text
GTT Canonical v2.1
        ↓
This execution directive
        ↓
GTT Bootstrap implementation
        ↓
ADE integration
```

Claude must:

- inspect the real repository before changing it;
- implement the directives in this document;
- preserve existing valid functionality unless explicitly changed here;
- use the Canonical as the governing methodology;
- report concrete implementation results.

Claude must **not**:

- redefine GTT;
- invent new GTT principles;
- replace the Canonical with general AI-agent practices;
- decide new methodological questions on its own;
- create an independent agent framework;
- turn agents into authorities;
- infer that an implementation detail is canonical merely because it exists in code.

If an implementation issue requires a methodological decision that is not defined by this directive or the Canonical, stop at that point and report:

```text
DECISION REQUIRED
<description of the unresolved decision>
```

Do not silently choose a new rule.

---

# 3. First phase — inspect before modifying

Before making changes:

1. Inspect the complete current repository tree.
2. Read the current `README.md`.
3. Read `AGENTS.md` if present.
4. Inspect all existing agent-related files/directories.
5. Inspect current context/governance/protection/proposal/freeze mechanisms.
6. Inspect current validation/status mechanisms.
7. Inspect current session/state mechanisms, if present.
8. Inspect current ADE-specific integration files, if present.
9. Identify existing scripts/CLI commands.
10. Identify tests and validation commands.

Do not assume that a file or capability exists.

Produce an internal implementation map:

```text
EXISTING
MODIFY
ADD
REMOVE
UNCHANGED
```

Do not invent current-state functionality.

---

# 4. Core objective

The target architecture is:

```text
                    GTT
                     │
          ┌──────────┴──────────┐
          │                     │
      GOVERNANCE              RUNTIME
          │                     │
          ▼                     ▼
 evidence / context          ADE
 decisions / freeze        Claude Code
 proposals / validation    Codex
 session continuity        Kiro
          │                Copilot
          │                ...
          ▼
        AGENTS
          │
    ┌─────┼─────────┐
    ▼     ▼         ▼
Ground  Reasoning  Validation
```

The implementation must preserve the fundamental separation:

```text
Sources
   ↓
Grounding
   ↓
Evidence Dossier
   ↓
Reasoning / Think
   ↓
Proposal
   ↓
Human Decision
   ↓
Freeze
```

Agents may reason, analyze, identify gaps/conflicts, produce proposals and produce artifacts according to their permissions.

Agents do not acquire decision authority merely by producing output.

---

# 5. Agents — required evolution

Review the current agent model and evolve it toward explicit contracts.

Agents must be described by operational contracts rather than personalities.

Where applicable, an agent contract should make clear:

```text
identity
purpose
inputs
allowed context
prohibited context
capabilities
outputs
provenance requirements
write permissions
escalation rules
```

The implementation must clearly distinguish the following responsibilities.

## 5.1 Grounding

Grounding is an evidence boundary.

Its responsibility is to retrieve and expose authorized evidence faithfully.

It must not become an architecture decision-maker.

Conceptually:

```text
Authorized Sources
       ↓
   Grounding
       ↓
Evidence Dossier
```

Reasoning workers must not bypass this boundary by receiving raw source material merely "for context".

## 5.2 Reasoning / Think

Reasoning agents operate on the governed evidence/context made available to them.

They may:

- reason over evidence;
- identify gaps;
- identify conflicts;
- propose alternatives;
- propose resolutions;
- produce proposed artifacts.

They do not turn proposals into authorized decisions.

## 5.3 Validation

Validation must be as deterministic as practical.

It should verify structural/governance conditions such as:

- required artifacts;
- provenance structure;
- proposal structure;
- protected-artifact rules;
- freeze conditions;
- unresolved blocking items;
- invalid governance state;
- other checks supported by the existing implementation.

Validation must not pretend to make human architectural judgments.

## 5.4 Proposal

Protected-artifact changes must follow the GTT proposal/change path already established by the repository and Canon.

The implementation must preserve the distinction between:

```text
agent proposes
human authorizes
GTT records/governs
```

Do not create an agent mechanism that silently writes protected artifacts as if its output were already authorized.

---

# 6. Evidence boundary

Operationalize the evidence-boundary principle where the existing bootstrap architecture permits it.

The critical distinction is:

```text
Evidence retrieval
      ≠
Reasoning
      ≠
Decision authority
```

Do not create a direct conceptual path where raw sources become implicit authority for a reasoning agent.

If the current implementation cannot fully enforce a boundary mechanically, document the boundary in the appropriate governance contract and implement the strongest deterministic enforcement supported by the repository.

Do not invent an external retrieval framework merely to satisfy this directive.

---

# 7. AGENTS.md

Review and improve the repository's `AGENTS.md`.

It should function as the portable operational contract for ADEs.

It must be usable across:

- Claude Code
- Codex
- Kiro
- GitHub Copilot
- other compatible ADEs

It must communicate:

- GTT authority;
- context/governance loading;
- agent responsibilities;
- evidence boundary;
- protected artifacts;
- proposal path;
- validation;
- session continuity;
- ADE independence;
- forbidden behavior.

Keep it concise enough to function as an agent instruction file.

Do not duplicate the entire Canon inside `AGENTS.md`.

---

# 8. Session Continuity

Add or improve a GTT-managed session continuity capability.

The key requirement is:

> Session continuity must not depend on the private conversation memory of a particular ADE.

The same project should be resumable when work moves between:

```text
Claude Code → Codex
Codex → Kiro
Kiro → Copilot
Copilot → Claude Code
```

The session state should be generated from actual project/governance artifacts wherever possible.

It should capture, as applicable:

- current work;
- relevant recent state;
- decisions;
- pending items;
- proposals;
- changes;
- freeze state;
- other operational information needed to resume work.

The generated session state is:

```text
operational context
NOT architectural authority
NOT evidence
NOT a substitute for ADR/decision records
```

Do not make an agent responsible for inventing the authoritative session state.

Prefer deterministic derivation from repository state.

If the existing bootstrap already has a session mechanism, improve it rather than creating a competing mechanism.

---

# 9. Working preferences

Keep working preferences separate from session continuity.

Preferences are not:

- Canon;
- architecture;
- evidence;
- decisions;
- constraints.

They must never silently override governed context.

Where preferences are implemented, preserve clear precedence:

```text
GTT governed state / constraints
        ↓
working agreements/preferences
```

An agent must not author its own behavioral preferences.

Do not mix descriptive session state with prescriptive preferences in one ambiguous artifact.

---

# 10. ADE independence

The implementation must not become coupled to one ADE.

Use the repository's existing structure where possible.

If adapters are needed, their purpose is integration:

```text
                GTT
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
 Claude Code   Codex       Kiro
     │           │           │
     └───────────┼───────────┘
                 ▼
          SAME GTT CONTRACT
```

ADE-specific files may adapt invocation/loading behavior, but they must not redefine GTT governance.

Do not create four different versions of GTT methodology.

---

# 11. Capability model

Make a clear distinction between:

```text
CANONICAL
IMPLEMENTED
EXPERIMENTAL
PROPOSED
NOT IMPLEMENTED
```

Do not infer:

```text
implemented in bootstrap
        =
canonical GTT requirement
```

The Canon remains the methodological authority.

Where the repository already has a capability/feature/status mechanism, extend it rather than creating a competing registry.

---

# 12. Validation and status

Review existing status/validation functionality.

Where supported by the current architecture, provide a deterministic operational path equivalent to:

```text
gtt status
gtt validate
```

Do not invent commands that cannot be integrated into the actual CLI.

`status` should expose real repository/governance state.

`validate` should detect deterministic inconsistencies.

The output should help an ADE understand:

```text
What is the current state?
What is governed?
What is pending?
What is proposed?
What blocks?
What is frozen?
What requires human decision?
```

---

# 13. Protected artifacts and write permissions

Review existing protected-artifact rules.

Preserve the principle:

```text
Agent reasoning
      ↓
Proposal
      ↓
Human authorization
      ↓
Protected artifact change
```

If the current repository already uses a proposals directory or equivalent controlled mechanism, preserve and strengthen that mechanism.

Do not introduce a second competing proposal path.

---

# 14. File strategy

Do not blindly add files.

For every proposed modification or addition, determine:

```text
File
Purpose
Current state
Why modification/addition is required
Canon relationship
Runtime impact
```

Prefer improving existing artifacts over creating duplicates.

Potential areas to review include:

```text
AGENTS.md
agent definitions
context/governance
validation
status
session continuity
preferences
proposals
ADE integration
capabilities
documentation
tests
```

These are areas to inspect, not a command to create every item.

---

# 15. Markdown governance

Every new or materially modified `.md` produced for GTT must include at the top the canonical GTT reference:

```text
https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md
```

Do not reference the entire `gtt-method` repository as the canonical authority.

Do not substitute another GTT document for this Canonical reference.

---

# 16. Compatibility and non-regression

Do not break existing valid bootstrap behavior.

Before and after modification:

- run the repository's existing tests;
- run existing validation scripts;
- run relevant CLI checks;
- verify generated artifacts;
- verify protected-artifact behavior;
- verify ADE-facing instructions.

If tests are missing for a new deterministic behavior, add focused tests where the repository's current testing approach supports them.

Do not introduce an unrelated testing framework.

---

# 17. Explicit non-goals

This task does NOT authorize Claude to:

- redesign GTT methodology;
- modify the GTT Canonical;
- invent a new agent framework;
- create autonomous decision-making agents;
- make agents authoritative;
- replace human authorization;
- treat session memory as evidence;
- make ADE-specific governance variants;
- introduce RAG/vector databases unless already required by the existing implementation and this directive;
- rewrite the repository merely for stylistic reasons;
- add files only because they appear in this directive's conceptual examples.

---

# 18. Required execution sequence

Execute in this order:

```text
1. Inspect repository
        ↓
2. Map existing implementation
        ↓
3. Apply this directive against real files
        ↓
4. Modify existing artifacts
        ↓
5. Add only required artifacts
        ↓
6. Implement/strengthen validation
        ↓
7. Implement/strengthen session continuity
        ↓
8. Strengthen agent contracts
        ↓
9. Verify ADE independence
        ↓
10. Run tests and validation
        ↓
11. Report implementation
```

Do not reorder this into "design a new framework first".

---

# 19. Final report required from Claude

At completion, provide:

## Changed

List every modified file.

## Added

List every new file.

## Removed

List every removed file, if any, with reason.

## Implemented

For each directive area:

```text
Agents
Evidence Boundary
AGENTS.md
Validation
Session Continuity
Working Preferences
ADE Independence
Capabilities
Protected Artifacts
```

state exactly what was implemented.

## Validation

Report exact commands executed and their results.

## Remaining

List only genuine remaining issues.

## Decision Required

If any methodological decision was not covered by this directive or the Canon, list it here rather than deciding it autonomously.

---

# 20. Final constraint

The implementation must leave this relationship intact:

```text
                 GTT CANONICAL
                       │
                       ▼
              GOVERNED CONTEXT
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Grounding    Reasoning    Validation
          │            │            │
          └────────────┼────────────┘
                       ▼
                    Proposal
                       │
                       ▼
                Human Decision
                       │
                       ▼
                     Freeze
                       │
                       ▼
                 Work / Build
                       │
                       ▼
             Any compatible ADE
```

**Claude's role in this task is execution, not methodological authorship.**

If something is unclear: report `DECISION REQUIRED`.

If something is not present in the repository: inspect and report it.

If something is not supported by the Canon or this directive: do not invent it.
