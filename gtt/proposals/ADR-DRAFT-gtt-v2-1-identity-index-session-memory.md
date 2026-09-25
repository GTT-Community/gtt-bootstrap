# ADR-002 — GTT v2.1: Artifact Identity, Repository Reconciliation, Technical Index & Session Memory Service

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

- Status: **Draft — not a decision**
- Date: 2026-09-25 (date prepared; not a decision date)
- Approved by: *nobody — pending the Solution Designer*
- Supersedes: none

> This is a draft prepared for human review. It records what was **built**
> and the reasoning behind it so a human can decide whether to ratify it.
> Nothing here is ratified, accepted, or frozen. It is staged in
> `gtt/proposals/`, not `gtt/adr/`, and no promotion script exists for it:
> per the `gtt-adr` skill, a promotion package is prepared only after a
> human approves the decision. The `Status` value the Solution Designer sets
> on ratification (`Proposed` / `Accepted`) is theirs to choose.

Sibling documents: `GOVERNANCE-PACKAGE-gtt-v2-1.md` (evidence, pending items,
human checklist) and `PROPOSAL-gtt-v2-1-backlog-epic-stories.md` (Epic and
Stories). Source design: `GTT-v2.1-Artifact-Identity-Technical-Index.md` at the
project root (status in that file: *Proposed for GTT v2.1*).

## Context

GTT governs a repository whose knowledge lives in Markdown: governed context,
ADRs, proposals, the backlog, instructions, skills. Three gaps followed from
treating those files as unrelated paths:

1. **Identity was the path.** Moving `adr/ADR-007.md` to
   `architecture/adr/ADR-007.md` was indistinguishable from deleting one
   artifact and creating another. References, relationships, and provenance
   did not survive a reorganisation, and nothing detected the damage — a clean
   `git status` says nothing about broken knowledge.
2. **Retrieval meant scanning.** Agents had no derived locator, so finding the
   section that governs a concept meant loading whole documents.
3. **Session continuity was a snapshot with no delivery contract.** A
   deterministic `gtt/SESSION.md` already existed (`gtt-status.sh`), but
   nothing defined how an ADE receives it, what it may claim, or how an
   adapter is kept honest — and `gtt-status.sh` itself named specific ADEs.

The source design document proposes the identity and index capability as
"high-priority" for v2.1 and names a Session Memory Service as the second v2.1
work item.

## Decision (as implemented — for ratification)

GTT v2.1 adds four capabilities to the GTT Core. **All are implemented; none is
ratified.** The Core stays ADE-agnostic; ADE-specific behaviour is confined to
adapters.

### 1. Artifact Identity

- `gtt/index/artifacts.json` is an **identity manifest**: each artifact has a
  stable `id`, `type`, current `path`, `history` (former paths), and `aliases`
  (intentional copies). It is authoritative for identity and changes only
  through `gtt-index.sh` / `gtt-reconcile.sh`, in a reviewable diff.
- The path is a locator; the `id` is the reference. ADR ids are
  path-independent (`ADR-007` wherever it lives). Other ids are assigned once,
  at registration.
- An artifact is referenced as `[[ID]]` and survives any move; relative links
  are reconciled on a move.
- Scope: the Markdown files of the GTT kit (`AGENTS.md`, the two READMEs,
  `gtt/**` minus the derived `SESSION.md`, and the tool instruction/skill/rule
  directories). Artifact Identity attaches no meaning to which tool owns a file.

### 2. Repository Reconciliation

- `gtt-reconcile.sh` detects a moved or renamed artifact (order: git rename
  hint → same derived identity → content similarity), records the old path as
  history, and rewrites relative links so they keep resolving. Dry-run by
  default; `--apply` writes; `--map OLD=NEW` and `--retire ID` are the human's
  answers for cases it will not guess.
- `gtt-index.sh` **refuses** to register new artifacts while any registered path
  is missing, so a move can never be silently recorded as delete + create.
- Frozen `gtt/context/` and `gtt/adr/` files are never rewritten by the tool;
  it reports them. A move of a governed file remains a human/governed act.
- `gtt-check-integrity.sh` fails on: unreconciled paths, unregistered
  artifacts, duplicate logical identity (with `aliases` as the explicit
  exception), broken links, links using a former path, unresolved `[[ID]]`, and
  a stale index. It is part of `gtt-validate.sh`.
- Git is a rename *hint* only. Correctness never depends on it; GTT does not
  replace Git.

### 3. Technical Index

- `gtt/index/technical-index.json` is a **derived accelerator**: documents,
  sections (heading, anchor, line span), concepts, references / referenced-by,
  `supersedes`, provenance, authority, version, content hash. Deterministic (no
  timestamps), rebuildable from the Markdown alone, committed, and verified
  against a fresh rebuild.
- `gtt-query.sh` and the `gtt-retrieve` skill locate a section through the index
  and read only the needed lines from the Markdown, warning if the file changed
  since indexing.
- The index is **never** a source of truth and never evidence in itself; the
  Markdown it points to is authoritative.

### 4. Session Memory Service and the ADE Adapter Contract

- `gtt/scripts/gtt-session-context.sh` is the single, ADE-independent entry
  point: it resolves Python (`gtt-run-python.sh`, one probe), regenerates
  `gtt/SESSION.md` via `gtt-status.sh`, verifies it, and prints a payload headed
  *operational-only; NOT authority, NOT evidence, NOT a decision record, NOT a
  grounding source*. It fails loudly (non-zero exit, message on stderr), never
  with partial context.
- `SESSION.md` describes GTT's operational state only (freeze state, backlog
  focus, pending proposals, ADR statuses, GTTGuard count, identity/index state,
  repository resume hints) and carries the same non-authority markers in its
  own header. It names no ADE.
- `gtt/docs/SESSION-ADAPTER-CONTRACT.md` defines what every adapter must do: use
  only the service, preserve the authority boundary, fail visibly (never exit
  2), declare coverage (**N1** native injection / **N2** ADE-loaded file /
  **N3** instruction-based retrieval), declare per-event support
  (`verified` / `documented` / `unsupported` / `unknown`), and declare
  verification honestly.
- Each adapter is a *data* declaration, `gtt/session-adapters/<ade>.json`;
  `gtt-check-session-adapter.sh <ade>` (run per adapter by `gtt-validate.sh`)
  checks it statically without any ADE installed. Runtime verification by the
  real ADE is never run by the check and is always reported `SKIPPED`, as
  declared.
- **Adapters.** Claude Code: installed, N1, runtime-verified (startup, resume).
  Codex, GitHub Copilot, Kiro: **staged** under
  `gtt/proposals/session-adapters/` — implemented and statically checked, not
  installed at native paths, runtime not verified.

## Authority limits

| Artifact | Authority |
|---|---|
| `gtt/context/`, `gtt/adr/`, `gtt/backlog.md` | Authoritative as today (L0 / L1 / development line) |
| `gtt/index/artifacts.json` | Authoritative **for identity only** (id ↔ path); never for content or decisions |
| `gtt/index/technical-index.json` | None. Derived locator; deletable and rebuildable; stale = build fails |
| `gtt/SESSION.md` and the `gtt-session-context.sh` payload | None. Operational session memory; not evidence, not grounding, not a decision record; outranked by governed context on any conflict |
| `gtt/session-adapters/*.json` | Declarations (claims), not evidence: the runtime value must be backed by an actual run |
| An ADE adapter | Translates the service output for one ADE; owns no identity, no authority, no GTT logic |

Agents operate through these scripts and contracts; they do not own an
artifact's identity. None of this widens what an agent may write: the Human
Promotion Boundary, the freeze regime, and GTTGuard are unchanged.

## Relation to GTT Core and to ADE adapters

```text
GTT Core: Artifact Identity · Technical Index · Session Memory Service
   └── gtt-session-context.sh          (names no ADE, hook event, or format)
        └── ADE Adapter Contract       (this ADR's §4; the contract document)
             └── ADE adapters          (Claude installed; Codex, Copilot, Kiro staged)
```

The Core-ness of the Session Memory chain was checked by search: no Claude,
Codex, Copilot, or Kiro reference remains in `gtt-status.sh`,
`gtt-session-context.sh`, or `gtt-run-python.sh`. A path scope in the identity
engine lists tool directories; that is scope, not ADE logic. One residual is
recorded in *Known pending items* (`gtt-validate.sh`).

## Alternatives considered

The rationale below is what was recorded during implementation; it is for the
Solution Designer to confirm or overturn. The manifest choice was made in
conversation on 2026-09-25 — recorded as context, not as ratification.

| Option | Why it lost |
|---|---|
| Identity as front matter in each Markdown file | Needs edits to every artifact, including `gtt/context/` and `gtt/adr/`, which agents cannot write once frozen; identity would also change file content |
| Hybrid: front matter as truth + derived manifest | Two mechanisms for one fact; more moving parts than needed for this repository's size |
| Technical index as SQLite | Binary, not diff-able, adds a dependency |
| Technical index gitignored | Stale-index detection then depends on every consumer rebuilding first; the committed form gives one reviewable, checkable artifact (trade-off: every Markdown edit requires a `gtt-index.sh` run) |
| Engine in bash only | Front matter/heading/link parsing is fragile in bash; Python is already a stated dependency (GTTGuard) |
| Session continuity through each ADE's own memory | Not portable, not derivable from the repository, and not auditable |
| One bespoke integration per ADE with no contract | Each adapter would re-implement GTT logic and drift; nothing would keep the authority boundary or the honesty of claims |

## Consequences

- **Easier:** safe reorganisation of governed Markdown; targeted, section-level
  retrieval; deterministic detection of broken knowledge; one session-context
  service that any ADE can consume; adapter claims that are checkable.
- **Harder:** every Markdown edit requires `gtt-index.sh` or
  `gtt-check-integrity.sh` fails (same trade-off as `protection/registry.yaml`);
  a new artifact must be registered; adding an ADE means writing an adapter and
  a declaration.
- **Locked in:** the `[[ID]]` reference syntax; the manifest/index schemas
  (`schema: 1`); the adapter declaration schema; the N1/N2/N3 vocabulary.

## Risks

- The runtime value in a declaration is self-asserted; the static check cannot
  disprove a false `runtime-verified` (it reports `SKIPPED`, never `PASS`).
- Session memory could be mistaken for authority by a careless adapter or agent;
  mitigated by the markers, the contract, and the check, not eliminated.
- Regression evidence for reconcile, query, and duplicate detection is not
  persisted in the repository (see the evidence register).
- The open design questions of the source document (aliases beyond a path list,
  cross-repository references, version transitions, an index CLI/API) are not
  solved by this implementation.

## Affected context

- `gtt/context/*` in this repository still holds template placeholders; this ADR
  changes **no** governed context file and proposes no `stack.md` row. Whether
  the map should record these capabilities is the Solution Designer's call.
- `AGENTS.md`: the *Artifact identity and technical index* section is already
  present (promoted by the human). One stale phrase in *Session continuity*
  ("installed adapter") needs a **manual change** — exact text in
  `PROPOSAL-artifact-identity-followups.md` §2d.
- Only if the staged adapters are adopted: `AGENTS.md` adapter matrix and
  *Adapters vs. portable core*, `gtt-check-adapter.sh`, the `gtt-bootstrap`
  skill, and `README-GTT.md`. **This ADR does not decide that adoption**; it is a
  separate governed decision.

## Validation evidence and known pending items

Evidence and pending items are kept in one place so they are not restated here
inconsistently: see `GOVERNANCE-PACKAGE-gtt-v2-1.md` (*Evidence register* and
*Pending items*). Headline, from the repository as prepared: `gtt-validate.sh`
reports OK; runtime verification exists only for Claude Code; Codex, GitHub
Copilot, and Kiro runtime are **NOT VERIFIED**; the `AGENTS.md` manual change,
governance, human ratification, and freeze are **pending**.

## Status of this record

**Draft — not a decision.**
