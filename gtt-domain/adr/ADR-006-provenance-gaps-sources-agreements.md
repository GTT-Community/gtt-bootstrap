# ADR-006 — Provenance, gaps (OPEN/BLOCKING), source manifest and working agreements

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

- Status: Accepted
- Date: 2026-09-29
- Approved by: Solution Designer (mgriott) - ratified by executing apply-ADR-006-provenance-gaps-sources-agreements.sh on 2026-09-29
- Supersedes: none


## Context

An audit of `main` at `3f35a95` against `GTT-CDAD-CONVERGENCE-WORKPLAN.md` found that GTT's modern core is complete (Engine/Domain/ADE split, artifact identity, derived
index, GTTGuard, human promotion boundary, session memory, status/query/reconcile/validate, two bootstrap confirmations) and that one family of semantic capabilities
that CDAD had is lost or diluted:

- **Provenance** exists only as an *elicitation* convention inside the Initial Design Questionnaire and the bootstrap skill; governed context has no canonical way to tell evidence from
  an agent's proposal, and nothing checks it.
- **OPEN vs BLOCKING** does not exist (no occurrence in the repository). The nearest thing is "an empty cell is a decision not yet made", which is invisible to status, query and freeze.
  `gtt-freeze.sh` only detects template placeholders.
- **Source authority and precedence** does not exist: with more than one candidate the skill asks which one, but nothing records authority, precedence or version, and nothing prevents a
  precedence being decided by reading order.
- **Working preferences** are reserved (`AGENTS.md`: "if ever introduced"; `docs.md`: PROPOSED) with no artifact, scope or check.
- The **evidence boundary** (Sources → Grounding → Dossier → Reasoning → Proposal → Human) is text only.

The remedy must be semantic and architectural, not a second system: no parallel `cdad/` folder, second index, second identity, second protection, second Session Memory or second source of truth.

## Decision

1. **Canonical provenance tags in governed context and ADRs.** `[FUENTE: ref]` (a declared source id with an optional `:location`, or a repository path with an optional `:line`),
   `[VACÍO: GAP-id]` (the authorised sources do not determine it; classified by a gap), `[CONFLICTO: a vs b]` (the named sources disagree), and `[PROPUESTA]`, which is reasoning output and is **never allowed
   inside governed context** — it stays in `gtt-domain/proposals/`. Code spans and fences are not scanned, so documents may discuss the tags. The taxonomy is kept as it already exists in the Questionnaire.
2. **Gap register: OPEN and BLOCKING, in the governed context.** A `gtt-gaps` block in `gtt-domain/context/stack.md` (new section 8; it already is "the single view of this solution"). One line per gap:
   `KIND | ID | topic | scope: ... | affects: ...`. **BLOCKING** = the design cannot be frozen without it: freeze is refused while one is pending, and a frozen design cannot carry one. **OPEN** = known, undecided and not needed
   for the current design: it must carry an explicit `scope:`, crosses freeze, stays visible in status and query, and is **never an authorisation** — anything outside its scope, and its resolution, follow the
   normal path (change request → proposal → human decision → promotion → new freeze). Resolution is traceable: the line becomes an append-only `RESOLVED | ID | topic | was: OPEN | by: ADR-NNN`; the gap is never
   deleted. An empty decision row in `stack.md` section 1 that is not classified as a gap is flagged.
3. **Source manifest, respecting the Engine/Domain boundary.** The declaration of which sources are authorised, with what authority and precedence, is a human decision about the project, so it lives in
   the **domain**, not the Engine: `gtt-domain/context/sources.md` (optional; a `gtt-sources` block: `id | path | version | authority | precedence | status`, plus `policy: provenance=advisory|required`), governed
   like the rest of L0 (before freeze written by the bootstrap; after it, only through an ADR). The Engine holds only the *template* (`.gtt/scaffold/templates/gtt-sources-manifest.md`) and the *reader*.
   Precedence must be an integer and unambiguous; it orders sources when interpreting a conflict and **never erases a `[CONFLICTO]`**. After freeze `SOURCE-BRIEF.*` is evidence and history, never an authority;
   declaring it `primary` or `secondary` in a frozen project is a finding. The index may locate the manifest and is never its authority.
4. **Working agreements, separate from L0 and from Session Memory.** Team agreements: `gtt-domain/working-agreements.md` (optional; versioned and reviewed; a `gtt-preferences` block `id | scope | applies-to | text`).
   A person's own preferences: `.gtt/local/preferences.md` (optional, local, never committed; tracked by git is a WARN). Both sit **below** governed context (`AGENTS.md`'s existing precedence rule), are neither
   evidence nor decisions, are never loaded into Session Memory, and no agent authors its own. An entry that tries to override governed context or a decision is rejected by the gate. They are deliberately not in
   `gtt-domain/context/` (not L0) and not in `session.md` (not operational state).
5. **One gate, `gtt-check-provenance.sh`, with sub-checks** (`tags`, `gaps`, `sources`, `preferences`), backed by one engine `gtt_provenance.py`. Integrated, not duplicated: `gtt-validate.sh` runs it; `gtt-freeze.sh` runs it with
   `--pre-freeze` (a pending BLOCKING gap, an unresolved `[CONFLICTO]`, a `[PROPUESTA]` inside governed context or a malformed manifest refuse freeze; a valid OPEN does not); `gtt-status.sh` prints an *Evidence / Governance* section
   (sources, gaps, conflicts, tags, agreements — derived, never agent notes); `gtt-query.sh --governance open|blocking|resolved|conflicts|sources|agreements` answers governance questions **from the governed artifacts**, not from the index.
6. **Bootstrap.** The `gtt-bootstrap` skill classifies every empty decision as a gap, uses `[CONFLICTO]` where sources disagree, keeps `[PROPUESTA]` out of the six files, and offers the source-manifest template when
   several sources exist. The two confirmations, the questionnaire and Multi-ADE (ADR-005) are unchanged.
7. **Compatibility.** Everything is optional. A project with no gap block, no manifest and no agreements passes unchanged; `provenance=advisory` is the default; an install without the gate simply skips it at freeze.
8. **What does not change.** The freeze regime and its two regimes, GTTGuard, artifact identity, the derived index, Session Memory and its adapters, the Human Promotion Boundary, Multi-ADE (ADR-005), backlog governance.

## Alternatives considered

| Option | Why it lost |
|---|---|
| A separate `gaps.md` / `open.md` file | A second place to look and a second thing to freeze; `stack.md` already is the single map and already carries the analogous `gtt-drift-signals` block. |
| The source manifest in `.gtt/` (Engine) | It is a human declaration of authority over the project's design, i.e. domain content; putting it in the Engine would put a governed decision outside the freeze regime and blur ADR-004's boundary. |
| A YAML/JSON manifest and gap register | Needs a parser in the ADE-agnostic Core and is not reviewable prose; a fenced block of pipe-separated lines follows the existing `gtt-drift-signals` and `gtt-sources` style. |
| Four scripts (`provenance`, `gaps`, `sources`, `preferences`) | Four gates to wire and keep consistent; one script with sub-checks shares the parser and keeps `gtt-validate.sh` simple. |
| Store gaps/sources/provenance in the technical index | The index is derived and must never become an authority; it may locate them, nothing more. |
| Working preferences inside `session.md` or L0 | Session Memory is operational and derived; L0 is authority. Preferences are neither. |
| Copy CDAD's structure (`cdad/`, its agents, its index) | Duplicates identity, index and protection that GTT does better; only the semantics are recovered. |
| Make `provenance=required` the default | Would break every existing project; advisory by default, required by declaration. |

## Consequences

Makes easy: telling evidence from proposal in governed context; seeing every undecided item, its scope and what resolved it; refusing to freeze a design with a real hole while letting a scoped OPEN through;
declaring sources with an unambiguous precedence; writing team agreements without them ever becoming authority; asking status/query governance questions with one command.

Makes hard: writing a claim in governed context now has a small syntax when a tag is used; a project that adopts `provenance=required` must cite a source or ADR for every technology row; resolving a gap needs a
change request and an ADR, by design.

Locked in: `[PROPUESTA]` never appears in governed context; OPEN authorises nothing; BLOCKING refuses freeze; precedence never erases a conflict; the source manifest is domain, not Engine; working agreements are below L0
and outside Session Memory; one gate.

## Risks

- **The checks are lexical and structural.** They cannot judge that a `[FUENTE]` really supports a claim, that an OPEN scope is wise, or that a preference is harmless; the override and "authorisation" detectors are
  keyword heuristics (English and Spanish) with false negatives. The human remains the judge; the docs say so.
- **The gap block and manifest are hand-maintained fenced blocks.** A typo is caught (wrong field count, unknown kind), a wrong-but-well-formed entry is not.
- **`stack.md` and `sources.md` are L0.** Changing either after freeze needs an ADR; the gap register therefore changes only through the governed path, which is intended.
- **Working agreements are not hook-protected.** No hook blocks an agent from writing `working-agreements.md`; "no agent authors its own" is an instruction plus a review, and the gate only rejects overriding text.
- **`.gtt/local/preferences.md` relies on the person not committing it.** The gate warns if git tracks it; there is no ignore file in this repository.
- **Freeze in an existing project.** `gtt-freeze.sh` gains a call to the gate; a project frozen before this ADR is unaffected until it freezes again.
- **Verification scope.** Rehearsed in a disposable copy (Windows / Git Bash / Python 3.13) only; not run on Linux or macOS, on a real installed project, or with any ADE actually following the new bootstrap instructions.

## Stack map delta

| Section | Row | Before | After |
|---|---|---|---|
| header | Governing ADRs | `ADR-001, ADR-003, ADR-004, ADR-005` | `ADR-001, ADR-003, ADR-004, ADR-005, ADR-006` |
| 5. Dependency rules | provenance engine, gap register, `sources.md`, working agreements | *(absent)* | new row: reads governed artifacts only; must not own or duplicate them, be read as authority, or write to `gtt-domain/` |
| 5. Dependency rules | templates | the Initial Design Questionnaire | also the two ADR-006 templates |
| 5. Dependency rules | note under the table | Core/adapter, Engine/domain and Multi-ADE rules | also the evidence rule |
| 8. Gap register | new section | — | the `gtt-gaps` block (empty) with the OPEN/BLOCKING/RESOLVED definitions |
| 6. Map change log | new row | — | ADR-006 |

## Affected context

Full-file drafts `context-<name>-adr-006.md`, applied only by `apply-ADR-006-provenance-gaps-sources-agreements.sh` (which checks each replaced file's hash, shows every diff, and asks for `ratify`):
`context/stack.md` (the delta above), `context/architecture.md` (modules row, a fourth governing rule, data-ownership bullet), `context/glossary.md` (Provenance tag, BLOCKING gap, OPEN gap, Source manifest, Working agreement),
`context/constraints.md` (one line: OPEN, precedence and preferences never authorise or override), `context/principles.md` (three principles that each rule something out). `solution-vision.md` is unchanged.

Machinery and instructions staged under `adr-006-package/tree/` and placed by the same script: `AGENTS.md`, the manifest, `gtt-validate.sh`, `gtt-status.sh`, `gtt-query.sh`, `gtt-freeze.sh`, the `gtt-bootstrap` skill, `docs.md`, `index.md`;
new: `gtt_provenance.py`, `gtt-check-provenance.sh`, and the templates `gtt-sources-manifest.md` and `gtt-working-agreements.md`. ADR-001 to ADR-005 are not edited.
