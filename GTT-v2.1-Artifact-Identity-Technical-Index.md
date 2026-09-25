# GTT v2.1 — Artifact Identity, Repository Integrity & Technical Index

> Canonical governance reference: https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

## Status

**Proposed for GTT v2.1 — high-priority capability**

This document captures an architectural improvement identified during the definition of the GTT v2.1 project model.

The objective is to ensure that GTT can safely evolve, move, reorganize, validate, and efficiently retrieve Markdown artifacts without losing their identity, relationships, provenance, or operational usefulness to agents and ADEs.

---

# 1. Problem

GTT relies heavily on Markdown artifacts distributed across a governed project repository.

As the project grows, artifacts may be:

- moved;
- renamed;
- reorganized into new directories;
- referenced by other artifacts;
- superseded;
- split or consolidated;
- incorporated into new architectural structures.

A simple filesystem operation such as:

```text
mv adr/ADR-007.md architecture/adr/ADR-007.md
```

must not be treated by GTT as an unrelated deletion and creation.

The artifact is still the same logical artifact.

If GTT loses that identity, the following can break:

- references;
- cross-links;
- provenance;
- relationships;
- agent retrieval;
- ADE navigation;
- traceability;
- historical understanding;
- document discoverability;
- contextual retrieval efficiency.

Therefore, **artifact identity must be independent from physical path**.

---

# 2. Core Principle

## Logical identity is not physical location

An artifact has a logical identity that survives changes to its filesystem path.

Example:

```text
Artifact ID: ADR-007
Type: architecture-decision
Old path: adr/ADR-007.md
New path: architecture/adr/ADR-007.md
```

GTT must recognize:

```text
same artifact
+
new location
```

and not:

```text
delete artifact
+
create new artifact
```

The path is a locator.

The artifact identity is the stable reference.

---

# 3. Artifact Identity

GTT v2.1 should define a minimal artifact identity model.

Conceptually:

```yaml
artifact:
  id: ADR-007
  type: architecture-decision
  path: architecture/adr/ADR-007.md
```

The exact serialization mechanism remains to be defined.

The important invariant is:

> Moving or renaming an artifact must not silently create a new logical artifact.

Artifact identity should support at least:

- stable identifier;
- artifact type;
- current path;
- historical paths when necessary;
- relationships;
- provenance;
- status;
- references.

---

# 4. Repository Moves Must Be Governed

A repository change such as:

```text
adr/ADR-007.md
```

to:

```text
architecture/adr/ADR-007.md
```

must trigger GTT reconciliation.

Conceptually:

```text
Filesystem / Git change
        ↓
GTT detects movement
        ↓
Artifact identity resolved
        ↓
Old path → new path
        ↓
References reconciled
        ↓
Relationships reconciled
        ↓
Technical index rebuilt/updated
        ↓
Provenance preserved
        ↓
Repository integrity validated
```

The operation must preserve the logical identity of the artifact.

---

# 5. What GTT Must Reconcile

When an artifact is moved or renamed, GTT should be able to identify and reconcile:

```text
artifact identity
references
relationships
cross-links
metadata
provenance
index entries
path references
dependency references
```

The objective is not merely to update a path.

The objective is to preserve the **knowledge graph represented by the repository**.

---

# 6. Artifact Relationships

GTT should be capable of representing relationships between artifacts.

For example:

```text
ADR-007
   │
   ├── supersedes → ADR-003
   ├── referenced-by → stack.md
   ├── referenced-by → proposal-012
   ├── affects → context/API.md
   └── related-to → architecture/views/system.md
```

A relationship should ideally refer to an artifact identity rather than relying exclusively on a physical path.

This allows directory reorganization without destroying semantic relationships.

---

# 7. Provenance Preservation

Artifact movement must not destroy provenance.

If an artifact was previously associated with:

```text
source
decision
proposal
human ratification
freeze
change request
```

those relationships must remain discoverable after the artifact moves.

This is especially important because GTT treats provenance as part of governance rather than optional metadata.

D11 establishes that generated claims must retain explicit provenance and that unmarked content cannot be assumed to be grounded. The same principle should extend to artifact relationships and history.

---

# 8. Technical Index for GTT Documentation

GTT also needs a **technical index for its own documentation and Markdown knowledge base**.

This is distinct from a project knowledge index.

Its purpose is to allow agents and ADEs to work efficiently with the GTT documentation without repeatedly loading or scanning every Markdown document.

Conceptually:

```text
GTT Documentation
        ↓
Technical Index
        ↓
Agent / ADE retrieval
        ↓
Relevant document / section / concept
```

The technical index should make it possible to determine efficiently:

- which document contains a concept;
- which section contains the relevant information;
- which documents depend on another document;
- which document is authoritative;
- which version applies;
- where a concept is referenced;
- which artifacts are related;
- which sections changed.

---

# 9. The Technical Index Is Not the Source of Truth

This distinction is mandatory.

```text
Markdown / Canonical artifacts
        ↓
SOURCE OF TRUTH

Technical index
        ↓
DERIVED ACCELERATOR
```

The index must be:

- derived;
- rebuildable;
- disposable;
- version-aware;
- validated against the repository.

The index must never become a second authority competing with the canonical Markdown artifacts.

This follows the existing GTT evidence model: derived indexes may accelerate retrieval, but the underlying governed artifacts remain authoritative.

---

# 10. Technical Index Requirements

The GTT technical index should be able to represent, at minimum:

```text
document
section
heading
concept
artifact
artifact type
version
canonicality / authority
references
relationships
dependencies
path
identity
provenance
```

A future implementation may represent this as structured data, but the exact format should remain an implementation decision until the contract is finalized.

---

# 11. Section-Level Retrieval

File-level retrieval may be insufficient for large GTT documents.

For example:

```text
GTT-CANONICAL-v2.1.md
```

may contain many independent concepts.

An agent should ideally be able to retrieve:

```text
document
    ↓
section
    ↓
relevant subsection
```

instead of loading the entire document unnecessarily.

This improves:

- context efficiency;
- token consumption;
- retrieval precision;
- agent performance;
- ADE responsiveness.

---

# 12. Movement and Index Integrity

A movement operation should result in a deterministic reconciliation process.

Example:

```text
BEFORE

adr/ADR-007.md
```

After:

```text
architecture/adr/ADR-007.md
```

GTT should detect:

```text
Artifact: ADR-007
Previous path: adr/ADR-007.md
Current path: architecture/adr/ADR-007.md
```

Then verify:

```text
✓ identity preserved
✓ references reconciled
✓ cross-links reconciled
✓ relationships preserved
✓ provenance preserved
✓ technical index updated
✓ no orphaned references
✓ no duplicate artifact identity
```

---

# 13. No Orphaned References

GTT should detect references that point to artifacts that no longer resolve.

Examples:

```text
broken relative links
broken artifact references
missing ADR references
missing proposal references
stale documentation links
stale index entries
```

A repository should not be considered structurally healthy merely because Git reports a clean working tree.

Git integrity and GTT knowledge integrity are different concerns.

---

# 14. No Duplicate Logical Identity

GTT should also detect:

```text
ADR-007
```

appearing simultaneously as:

```text
architecture/adr/ADR-007.md
architecture/decisions/ADR-007.md
```

unless the relationship is explicitly valid.

The system should distinguish:

```text
duplicate artifact identity
```

from:

```text
intentional reference / alias
```

---

# 15. Git as the Persistence Layer

Git remains the primary persistence and history mechanism for governed project artifacts.

GTT should leverage Git for:

- history;
- commits;
- renames;
- branches;
- diffs;
- merges;
- change detection.

GTT adds a semantic layer above Git:

```text
Git
  ↓
filesystem history
  ↓
GTT artifact identity
  ↓
relationships
  ↓
provenance
  ↓
technical index
```

GTT should not attempt to replace Git.

---

# 16. Separation of GTT Core and Project

This capability belongs to the GTT engine/core rather than to an individual project.

Conceptually:

```text
GTT
│
├── engine/
│   ├── artifact identity
│   ├── indexing
│   ├── validation
│   ├── provenance
│   └── reconciliation
│
└── project/
    ├── architecture/
    ├── method/
    ├── docs/
    └── context/
```

The exact repository layout remains subject to the broader GTT v2.1 architecture decision.

The important separation is:

> GTT provides the governing engine; the project provides the governed artifacts.

---

# 17. Relationship With GTT Agents

Agents do not own artifact identity.

Agents operate through GTT.

For example:

```text
Architect Agent
      ↓
GTT Engine
      ↓
Project artifact
      ↓
architecture/adr/
```

Similarly:

```text
Analyst Agent
      ↓
GTT Engine
      ↓
Project artifact
      ↓
method/proposals/
```

The agent may propose or modify an artifact according to its permissions and workflow, but GTT remains responsible for maintaining repository-level structural integrity.

---

# 18. Proposed v3 Capabilities

GTT v2.1 should therefore consider the following capabilities part of the core:

### Artifact Management

- stable artifact identity;
- artifact type;
- path tracking;
- movement detection;
- rename detection;
- duplicate identity detection.

### Relationship Management

- references;
- cross-links;
- artifact relationships;
- dependency relationships;
- supersession relationships.

### Provenance

- preservation of provenance;
- relationship between proposals, decisions and governed context;
- traceability across movement.

### Technical Index

- document index;
- section index;
- concept index;
- relationship index;
- version awareness;
- authority metadata;
- rebuild capability.

### Integrity Validation

- orphan detection;
- broken-reference detection;
- duplicate identity detection;
- stale-index detection;
- path/reference reconciliation.

---

# 19. Performance Principle

GTT should avoid requiring agents or ADEs to repeatedly scan the entire repository.

The intended model is:

```text
Repository
     ↓
GTT indexing / reconciliation
     ↓
Efficient technical index
     ↓
Targeted retrieval
     ↓
Agent / ADE
```

The index is an optimization layer.

Correctness must always be recoverable from the repository itself.

---

# 20. Rebuildability

The technical index must be reconstructible from canonical repository artifacts.

Conceptually:

```text
delete index
      ↓
run GTT index/rebuild
      ↓
reconstruct index
      ↓
validate
```

A corrupted or stale index must never require manual reconstruction of project knowledge.

---

# 21. Version Scope

This capability is proposed as a **GTT v2.1 capability** because it is foundational to:

- repository-native governance;
- multi-agent workflows;
- ADE interoperability;
- project-scale Markdown documentation;
- architectural traceability;
- efficient context retrieval;
- safe repository restructuring.

Deferring artifact identity and repository reconciliation would create structural debt that becomes more expensive as the GTT artifact ecosystem grows.

---

# 22. Open Design Questions

The following should remain open until the GTT v2.1 architecture is formally defined:

1. Exact artifact identity format.
2. Whether identity is explicit in Markdown front matter or maintained externally.
3. Exact technical index format.
4. Whether the index is stored locally, generated in CI, or both.
5. Exact CLI/API for reconciliation.
6. How Git rename detection participates in identity resolution.
7. How aliases are represented.
8. How cross-repository references are handled.
9. How version transitions affect identity.
10. How section-level indexing is represented.
11. Whether the project documentation directory belongs inside the GTT Project Knowledge Space.
12. Exact separation between GTT Engine, Agents, Governance, and Indexing modules.

---

# 23. Architectural Invariants Proposed for GTT v2.1

The following are candidates for formal GTT v2.1 invariants:

### I — Identity

> An artifact's logical identity MUST survive a valid path or directory change.

### II — Traceability

> Moving an artifact MUST NOT silently destroy its references, relationships, or provenance.

### III — Integrity

> GTT MUST be able to detect unresolved references and duplicate logical identities.

### IV — Derived Index

> The technical index MUST remain derived from canonical repository artifacts and MUST be reconstructible.

### V — Separation of Authority

> The technical index MUST NOT become an independent source of truth.

### VI — Agent Independence

> Agents MUST operate through GTT artifact contracts and MUST NOT own the identity or authority of project artifacts.

---

# 24. Relationship to the GTT v2.1 Project Model

The proposed project structure currently under exploration is:

```text
project/
│
├── architecture/
│   ├── adr/
│   ├── diagrams/
│   ├── models/
│   ├── principles/
│   └── views/
│
├── method/
│   ├── backlog.md
│   ├── change-request.md
│   └── proposals/
│
├── docs/
│   └── README.md
│
└── context/
```

This structure is **not frozen by this document**.

It represents the current architectural direction being explored for GTT v2.1.

The important principle is that GTT must be able to maintain the identity and relationships of these artifacts even when their physical organization evolves.

---

# 25. Summary

GTT should not treat a repository as a collection of unrelated Markdown files.

It should treat it as a structured set of **identifiable, related, traceable artifacts**.

The target model is:

```text
Git Repository
      ↓
GTT Engine
      ↓
Artifact Identity
      ↓
Relationships + Provenance
      ↓
Technical Index
      ↓
Efficient Agent / ADE Retrieval
```

The fundamental rule is:

> **Paths may change. Artifact identity, traceability and provenance must not be lost.**

This capability should be considered a high-priority architectural improvement for GTT v2.1.


## Primary Consumer / Work Target

The principal serious consumer/work environment for this capability is **Claude Code**.

GTT remains the governing methodology and mechanism; Claude Code is the primary agent/ADE through which this improvement is expected to be used operationally. The design should therefore be practical for Claude Code while preserving a clean architectural boundary so the capability is not conceptually limited to Claude Code.

Claude Code is the immediate work target for implementation and validation of this improvement.


## Second v2.1 Work Item — Session Memory Service

The second work item for GTT v2.1 is the definition and implementation of a **GTT Session Memory Service** for ADE/agent session continuity.

This service is intended to:

- preserve and reconstruct useful session state for the ADE/agent;
- support session resumption / warm start across sessions;
- derive session state from actual governed project artifacts and repository state;
- remain independent of Claude Code's own memory/session mechanisms;
- work with Claude Code as the primary serious consumer/work environment;
- remain outside the grounding/evidence corpus;
- never become an authority of governance or replace the governed project state.

The service should be deterministic or derivable from authoritative artifacts wherever possible. Agent-authored memory must not silently become project authority.

### v2.1 work plan for the next session

1. Define the Session Memory Service boundary.
2. Define the session-state artifacts and their relationship to repository state.
3. Define how GTT generates/reconstructs the session memory.
4. Define how Claude Code consumes the resulting session context.
5. Define persistence, refresh, and recovery behavior.
6. Define the boundary between session memory, working preferences, grounding/evidence, and governed project state.

This is a **v2.1 work item**, not a v3 item.
