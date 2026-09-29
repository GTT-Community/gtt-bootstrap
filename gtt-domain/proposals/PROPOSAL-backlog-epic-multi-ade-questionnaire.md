# PROPOSAL — Backlog: Epic for Multi-ADE and the Initial Design Questionnaire

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Form 4 — Development-line change (add an Epic and its Stories). **Draft, not a decision.** `gtt-domain/backlog.md` is **not** edited by this proposal; on approval the Solution Designer
(or the agent, once told) adds the block below directly, as `AGENTS.md` → *Backlog governance* prescribes for approved form-4 changes. No ADR and no script.

```text
Proposed Development-Line Change

Current backlog:
  EPIC-001 (STORY-001..005): artifact identity, technical index, session memory, ADE adapter contract. Nothing covers Multi-ADE
  participation or the Initial Design Questionnaire, although the task GTT_BOOTSTRAP_TASK_QUESTIONNAIRE_MULTI_ADE.md defines both.

Requested change:
  Add EPIC-002 with four Stories, all Status: Proposed (accepting them is separate from choosing each Story's real status).

Reason:
  The work exists as a task and a staged ADR-005 package; AGENTS.md requires an applicable Epic/Story before development work.

Precedence check:
  Contradicts no governed context. The Stories implement ADR-005 once ratified; until then they stay Proposed.

Status: Requires Solution Designer approval
```

## Block to add under `## Epics`

### EPIC-002 — Multi-ADE participation and the Initial Design Questionnaire

**Status:** Proposed
**Goal:** Let one GTT governance model serve several ADEs at once (one Primary, no extra authority) and let a project without a design document start through a Bootstrap-owned,
ADE-guided questionnaire — with every contract owned by the Bootstrap and consumed, not duplicated, by the CLI.
**Implementation state:** ADR-005 package staged in `gtt-domain/proposals/`; not ratified, nothing applied.

#### Stories

##### STORY-006 — ADE registry and per-project ADE state

- **Status:** Proposed
- **Priority:** High
- **Description:** The manifest `overlays:` section as the ADE registry; `.gtt/ade.json` for participating, primary and excluded ADEs and the ledger of GTT-installed files; `gtt-ade.sh list|detect|state`.
- **Scope:** registry keys, state schema, manifest reader, detection as candidates only. Out of scope: ADE hierarchy, authority, agent voting or arbitration.
- **Acceptance Criteria:**
  - Detection never writes and never makes an ADE participating.
  - Exactly one Primary, and it participates; an inconsistent state fails validation.
  - `.gtt/ade.json` is written only by `gtt-ade.sh`.
- **Dependencies:** STORY-005

##### STORY-007 — Multi-ADE lifecycle contract

- **Status:** Proposed
- **Priority:** High
- **Description:** `install`, `validate`, `status`, `inspect`, `resume`, `update`, `clean` and `export --clean` understand participating ADEs.
- **Scope:** `gtt-ade.sh install|update|remove|owned|set-primary`, state-driven `gtt-check-adapter.sh`, the ADE section in `gtt-status.sh`, `gtt-validate.sh`. Out of scope: the CLI itself.
- **Acceptance Criteria:**
  - A missing or inconsistent participating integration FAILS; a detected non-participating ADE WARNs.
  - `update` never overwrites a locally modified file that also changed upstream.
  - `clean` and `export --clean` remove only ledger-recorded, unmodified files and never the host project's own ADE configuration.
  - Changing the Primary is a direct operation recorded in `.gtt/ade.json`.
- **Dependencies:** STORY-006

##### STORY-008 — Migration and ownership ledger

- **Status:** Proposed
- **Priority:** Medium
- **Description:** Single-ADE projects keep working and migrate with `gtt-ade.sh adopt`; installers record what they install (`gtt-ade.sh record`), including `apply-session-adapters.sh`.
- **Scope:** legacy matrix retained; adopt refuses to infer among several overlays; adopted ADEs carry no fabricated install record.
- **Acceptance Criteria:**
  - A project without `.gtt/ade.json` validates exactly as before.
  - `adopt` touches no governed file.
  - Files installed by the session-adapter installer appear in `gtt-ade.sh owned`.
- **Dependencies:** STORY-006

##### STORY-009 — Initial Design Questionnaire as a Bootstrap contract

- **Status:** Proposed
- **Priority:** High
- **Description:** The existing questionnaire is declared under `templates:` and requested through `gtt-template.sh`; the Primary ADE conducts it; the reviewed copy becomes `SOURCE-BRIEF.md` (source material, never governed architecture).
- **Scope:** `gtt-template.sh list|show|materialize`, the bootstrap skill and `AGENTS.md` procedure, plain-comment answer slots. Out of scope: any CLI copy of the questionnaire; a second questionnaire.
- **Acceptance Criteria:**
  - Exactly one questionnaire exists, at its canonical path.
  - `materialize` never overwrites a filled copy.
  - `[VACÍO]`, `[CONFLICTO]` and `[PROPUESTA]` never map to a confirmed decision.
- **Dependencies:** STORY-005
