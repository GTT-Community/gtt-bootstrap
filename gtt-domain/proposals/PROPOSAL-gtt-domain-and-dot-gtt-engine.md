# Proposal — `.gtt/` Engine and `gtt-domain/` governed domain

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Status: **design approved by the Solution Designer on 2026-09-29, with the decisions recorded in section 6.** It is still a
*proposal*: **the ADR-004 draft and its promotion package are staged (`Status: Proposed`, not ratified); no migration package exists, and no
path in the repository has been changed by it.** Ratification and the migration each need their own explicit human decision (Human Promotion Boundary).

Flow: design (this file, approved) → **ADR-004 draft + L0 drafts + ratification script (staged, under review)** → migration package staged from the
ADR-003 engine → rehearsal on a disposable copy → human-run apply (with ratification) → post-promotion cleanup → new frozen state.

## 1. Proposed change

Rename and regroup the scaffold around one idea: **GTT-Method separates how it works from what it is applied to.**

```text
/
├── AGENTS.md                       # portable agent contract (ADE discovery file)
├── readme-gtt.md   readme-gtt.es.md
├── SOURCE-BRIEF.*                  # if a source document existed
│
├── .gtt/                           # GTT-METHOD ENGINE (machinery, derived state, GTT's own documentation)
│   ├── index/                      #   artifact identity + derived technical index
│   ├── protection/                 #   GTTGuard registry (derived)
│   ├── scaffold/                   #   manifest.yaml — the canonical scaffold definition
│   ├── scripts/
│   ├── session-adapters/
│   └── docs/                       #   GTT documentation: index, installation, usage, docs, evidence,
│                                   #   gtt-completion, session-adapter-contract
│
├── gtt-domain/                     # THE DOMAIN GOVERNED BY GTT-METHOD
│   ├── context/                    #   L0 governed context
│   ├── adr/                        #   L1 accepted decisions
│   ├── proposals/                  #   agent drafts awaiting a human decision
│   ├── backlog.md
│   ├── change-request.md
│   ├── session.md                  #   derived operational state (never authority)
│   └── .frozen                     #   freeze marker, written by gtt-freeze.sh
│
└── .claude/ | .kiro/ | .copilot/   # ADE OVERLAY — exactly one per installed project
```

Relative to the layout applied by ADR-003:

| Layer | ADR-003 layout (current) | This design |
|---|---|---|
| Engine | `gtt/` | **`.gtt/`** |
| Project Governance | project root (`context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen`) | **`gtt-domain/`** (same members) |
| GTT Documentation | `docs/` at the root, a layer of its own | **`.gtt/docs/`**, part of the Engine (decision Q1) |
| ADE overlay | `.claude/ .kiro/ .copilot/` | unchanged |
| Entry points | root | unchanged (Q3, Q4) |

So the four layers of ADR-003 become **three physical groups plus the entry points**: Engine (with its documentation), Domain, ADE overlay.
Governance semantics, the Human Promotion Boundary, L0/L1 authority, the derived-index rule, Session Memory being operational-only and
the adapter contract are **unchanged**. Only locations, the documentation layer's placement, and one concept change.

## 2. The concept: `gtt-domain`

**`gtt-domain/` is GTT-Method's definition of the project — the domain — that the method governs. It is the contextual, governed space
over which GTT applies the method.**

- Context is the source of truth ([[ADR-001]]). `gtt-domain/context/` says what the system is; `gtt-domain/adr/` records why;
  `gtt-domain/proposals/` holds what waits for a human decision; `gtt-domain/backlog.md` is the development line;
  `gtt-domain/session.md` is the derived resume-state; `gtt-domain/.frozen` marks the moment the domain became governed.
- It is the one place an agent is told to read before acting and forbidden to rewrite once frozen. It is *not* documentation about GTT.
- **Invariants: authority and logic stay apart** (the reason the split exists):
  1. **Architectural authority (L0/L1) lives only in `gtt-domain/context/` and `gtt-domain/adr/`** (protected by the freeze regime). Nothing in
     `.gtt/` is a governed decision: `index/` and `protection/` are derived, `docs/` is reference, `scripts/` and `session-adapters/` are logic
     and data declarations.
  2. **Executable GTT logic lives in `.gtt/`.** The domain holds none *in operation*: `gtt-domain/proposals/` holds governed **drafts** —
     proposals, ADR drafts, staged context files and promotion scripts — that the domain never executes and an agent never runs (a human does,
     under the Human Promotion Boundary).
  3. **`AGENTS.md` and the ADE overlay are instructions to agents.** They belong to neither group and are not architectural authority.
  4. **The code the project builds (L3: `src/`, `tests/`, infrastructure) belongs to neither.** The domain governs it by reference
     (map, dependency rules, drift signals) and never contains it.
  Everything else in the scaffold is derived, a draft, a reference, or logic.

The concept is already stated in `docs/docs.md` → *The governed domain (`gtt-domain`)*, flagged as design direction not yet applied, and
reconciled with the decisions below. Its L0 counterpart (a glossary term and wording in `architecture.md` / `stack.md`) can only land through
the ADR-004 promotion (section 5).

## 3. Complete path map (current → approved design)

| Current | New | Group |
|---|---|---|
| `gtt/index/` | `.gtt/index/` | Engine |
| `gtt/protection/` | `.gtt/protection/` | Engine |
| `gtt/scaffold/manifest.yaml` | `.gtt/scaffold/manifest.yaml` | Engine |
| `gtt/scripts/` | `.gtt/scripts/` | Engine |
| `gtt/session-adapters/` | `.gtt/session-adapters/` | Engine |
| `gtt/README.md` (documented for host projects; absent here) | `.gtt/README.md` | Engine |
| `docs/` (9 files) | `.gtt/docs/` | Engine (documentation) |
| `context/` | `gtt-domain/context/` | Domain |
| `adr/` | `gtt-domain/adr/` | Domain |
| `proposals/` | `gtt-domain/proposals/` | Domain |
| `backlog.md` | `gtt-domain/backlog.md` | Domain |
| `change-request.md` | `gtt-domain/change-request.md` | Domain |
| `session.md` | `gtt-domain/session.md` | Domain |
| `.frozen` | `gtt-domain/.frozen` | Domain |
| `AGENTS.md`, `readme-gtt.md`, `readme-gtt.es.md`, `SOURCE-BRIEF.*`, `.claude/`, `.kiro/`, `.copilot/`, `LICENSE`, `.gitignore` | unchanged | root |

Every current path appears once; nothing is dropped and nothing is duplicated. `.gtt/` and `gtt-domain/` are the only two new root names.
Artifact ids do not change (identity follows the artifact, not the path); every moved artifact keeps its current path in `history`,
as the ADR-003 migration did.

## 4. What this touches (audit of the repository as it is today)

Read-only scan of the 98 text files in the repository after the ADR-003 post-promotion cleanup (this proposal included; counts are files that
mention a family at least once, so families overlap):

| Family | Files that mention it |
|---|---|
| **Engine** (`gtt/scripts`, `gtt/index`, `gtt/protection`, `gtt/scaffold`, `gtt/session-adapters` → `.gtt/…`) | **66** (`scripts` 62, `protection` 27, `index` 19, `session-adapters` 18, `scaffold` 14) |
| `docs/` (→ `.gtt/docs/`) | 28 |
| **Domain** `context/` · `adr/` · `proposals/` (→ `gtt-domain/…`) | 60 · 49 · 44 |
| **Domain** `backlog.md` · `change-request.md` · `session.md` · `.frozen` | 36 · 34 · 26 · 27 |
| Active artifact identities that get a new path (ids unchanged) | **50** today (55 before the ADR-003 cleanup) |

Machinery that hard-codes paths, by number of path mentions:

| Hooks / config | Mentions | Engine script | Mentions |
|---|---|---|---|
| `.claude/hooks/protect-l0.py` | 25 | `gtt_artifacts.py` | 28 |
| `.claude/CLAUDE.md` | 11 | `gtt-status.sh` | 26 |
| `.claude/hooks/detect-drift.py` | 6 | `gtt-session-context.sh` | 23 |
| `.claude/hooks/protect-guard.py`, `session-start.py` | 5, 5 | `gtt-validate.sh` | 13 |
| `.claude/settings.json`, `notify-change-request.py` | 3, 3 | `gtt-freeze.sh` | 11 |
| `.kiro/permissions.yaml` | 2 | `gtt_session_adapter.py`, `gtt-check-markdown.sh` | 10, 10 |
| | | `gtt_guard.py`; `gtt-check-backlog/-stack/-protection.sh` | 9; 5, 5, 5 |

That is the same order of magnitude as the ADR-003 migration (35 files moved, about 60 rewritten, 17 patched): large but mechanical, provided
it is done by the same kind of map-driven, rehearsed, roll-back-safe package.

Components whose **logic** (not just path text) must change, because they encode where things are:

- **Protection hook** `.claude/hooks/protect-l0.py`: `REGIME_DIRS` → `gtt-domain/context`, `gtt-domain/adr`; the always-writable directory →
  `gtt-domain/proposals`; `FROZEN_MARKER` → `gtt-domain/.frozen`. The root-resolution design from ADR-003 (resolve every token against the project
  root; the MSYS `/c/…` conversion only on Windows) carries over unchanged and is what makes the new anchors safe. `.gtt/docs/` stays outside the
  freeze regime, as `docs/` is today (L2: editable with review).
- **`.claude/settings.json`** static deny (`/change-request.md` → `/gtt-domain/change-request.md`) and every hook command that runs `gtt/scripts/…`
  (→ `.gtt/scripts/…`); `.kiro/permissions.yaml` likewise; `.claude/CLAUDE.md` import `@../context/constraints.md` → `@../gtt-domain/context/constraints.md`.
- **Engine scripts and engines** (`gtt_artifacts.py`, `gtt_guard.py`, `gtt_session_adapter.py`, the `gtt-*.sh`): `MANIFEST`, `INDEX`, `FROZEN`,
  `GOVERNED_PREFIXES`, the artifact scan roots (now `.gtt`, `gtt-domain`, and the ADE directories), `derive()` (id rules by path prefix, including
  `.gtt/docs/` → `DOC-…` and the remaining `.gtt/` fallback), the GTTGuard scan exclusions, the adapter-check sandbox layout,
  `gtt-check-markdown.sh`'s `find` roots (must name `.gtt` and `gtt-domain` explicitly).
- **GTTGuard marker scan**: `.gtt` is already skipped by the existing "directory starts with `.`" rule; `gtt-domain` must be skipped **at the project
  root only**, replacing ADR-003's root-only set (`context adr proposals docs`), so a host's own `src/docs/` or `docs/` code stays scanned.
- **Relative links** inside the moved documents (`docs/index.md` links to `../context/`, `../backlog.md`, …) are recomputed from both the old and the new
  location, as before.
- **Session adapters** (declarations, staged adapters, `session-start.py`): install/staged paths and the `session.md` name.
- **ADE overlays, skills, READMEs (EN/ES), `AGENTS.md`, `.gtt/docs/*`, `gtt-domain/context/*` (L0)** and **`ADR-003`** (see section 5).
- **The scaffold manifest**: paths, `scaffold.version` 1 → 2, layers reduced to `engine` (with documentation), `domain`, `overlay`
  (the separate `documentation` section folds into the Engine).

## 4b. What the split buys — and what it costs

**Buys**
- **Collision surface at a host project's root drops from four generic names to two specific ones.** Under ADR-003 an adopting project could already own
  `docs/`, `context/`, `adr/` or `proposals/`; with this design only `.gtt/` and `gtt-domain/` are GTT's, and both are unlikely to exist. The collision
  policy (report, never merge) stays, but stops being routine.
- **One directory is "the project as GTT sees it".** Freezing, protecting, backing up, or excluding the governed subject becomes a single path.
- **The root reads like the project**: entry points, two GTT names, one ADE overlay.
- **GTT's own documentation is with GTT** (`.gtt/docs/`), so removing or upgrading the Engine takes its documentation along and leaves the domain
  untouched.

**Costs / risks**
- Every path in every file changes a second time within days; identity, index, session adapters, hooks and docs all re-migrate. The ADR-003 engine makes this
  mechanical, but it is a full governed change, not an edit.
- **`.gtt/` is hidden, and now so is GTT's documentation.** Less discoverable, and some tools ignore dot-directories. Mitigation: the root READMEs and
  `AGENTS.md` stay visible and link into `.gtt/docs/`; this is why decision Q4 matters.
- `.gtt/docs/` holds two per-project records — `gtt-completion.md` (this project's bootstrap record) and `evidence.md` (its verification evidence) —
  next to method documentation. They are records, not architectural authority, so invariant 1 holds; if they should live with the domain instead, that is a small
  follow-up decision, not a structural one.
- It supersedes part of ADR-003, which is dated 2026-09-28 and was ratified on 2026-09-29 — hours before this design was approved. That is legitimate
  — decisions may be revised — but it should be a deliberate, recorded decision and not a quiet drift (section 5).

## 5. Governance: an ADR is required — ADR-004 (draft staged, not ratified)

Same reasoning as ADR-003, from rules already in force:

1. **L0 changes — six files.** `architecture.md` (modules table, and the authority/logic rule), `stack.md` (dependency rules, drift-signals wording, map change
   log), `glossary.md` (new terms *Engine* and *Domain*, re-pathed entries), `constraints.md` (the datastore bullet names `gtt/index/…`; it is the file loaded
   into every session and imported by `.claude/CLAUDE.md`), `solution-vision.md` and `principles.md` all state locations.
2. **`stack.md` §6:** every change to the map needs a change-log row, and a row needs an accepted ADR.
3. **ADR-003 records the layout** (Engine in `gtt/`; governance and documentation at the root). This design reverses those parts, so ADR-004 must say so
   explicitly (its `Supersedes:` line names the affected decision of ADR-003). What ADR-003 decided and this design keeps: one canonical scaffold declared in
   `gtt/scaffold/manifest.yaml`, ADEs only as overlays, root-anchored protection, the collision policy (now over two names), and the naming exceptions.
4. It changes what the **protection hook** matches.

**Numbering:** ADR-004 (ADR-002 is a retired identity; ADR-003 is accepted).

**Governed form** (as for ADR-003 — **now staged**): ADR draft (`Status: Proposed`, `Approved by: pending`); six full-file L0 drafts named
**`context-<name>-adr-004.md`** (decision Q6); an `apply-ADR-004-…sh` promotion script (view/yes/no, base-hash guard checked before the prompt and again
after `yes`, restore on failure); and an orchestrating migration script that calls it and rolls everything back on `no`, on failure or on interruption.
L0 text changes only through the ADR script.

## 6. Decisions (approved by the Solution Designer, 2026-09-29)

| # | Question | Decision | Effect on this design |
|---|---|---|---|
| Q1 | GTT's own documentation inside `gtt-domain/docs/`? | **NO** — it stays in **`.gtt/docs/`**; it does not belong to `gtt-domain/` | `docs/` → `.gtt/docs/`; documentation stops being a layer of its own; invariant 1 restated |
| Q2 | `session.md` inside the domain? | **YES** — `gtt-domain/session.md` | in the map |
| Q3 | `SOURCE-BRIEF.*` | **YES** — stays at the root | unchanged; protection by filename keeps working |
| Q4 | `AGENTS.md`, `readme-gtt*.md` | **YES** — stay at the root | unchanged (ADE discovery; entry points) |
| Q5 | Manifest layout version 2 | **YES** | `scaffold.version: 2`; layers `engine` / `domain` / `overlay` |
| Q6 | Staged names with `-adr-004`; identity limitation left for a separate change | **YES** | `context-<name>-adr-004.md`; the retired-identity limitation stays open, out of scope |
| Q7 | Reuse the ADR-003 engine as the base of a new staged package | **YES** | new package rebuilt from it (section 7) |

## 7. How it would be executed (only step 1 has been prepared)

1. **Done (staged, under review):** `gtt-adr` drafted ADR-004, the six L0 drafts (`context-*-adr-004.md`) and the promotion script
   `apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh`. Nothing has been executed or ratified.
2. **New migration package**, rebuilt from the ADR-003 engine (`migrate.py`, the overlay/patch/tree mechanisms, the orchestrator and its fixes: baseline output,
   CRLF preflight, interruption traps, identity reconcile, hash re-check after `yes`, no bytecode). What changes in it: the old→new map is section 3 (from the
   *current* layout, so the source paths are the ADR-003 ones); L0 text stays deferred to the ADR script; historical patterns now include ADR-003 and
   ADR-004 drafts; the hook overlay is regenerated from the current hook; the manifest becomes v2; the doc patches describe the new layout in EN/ES.
   *State of the engine copy:* the ADR-003 package was removed from `proposals/` in the cleanup and was never committed; it is now persisted verbatim,
   with a provenance file and checksums, in `proposals/migration-engine-adr-003/` (untracked until you commit).
3. **Rehearsal** on a disposable copy of the real working tree (real identity manifest): success path, `no`, injected failure, interruption, hook cases
   including POSIX, CRLF, and the identity/`.frozen`/L0-hash checks — the evidence standard of ADR-003.
4. **You run the apply** (`!` needs piped answers, which makes the ratification yours — or run it in a normal terminal), then the post-promotion cleanup.

**Not done, deliberately:** no ratification of ADR-004, no migration package, no migration, no L0 change. The edits made for this decision are this proposal,
the flagged concept section in `docs/docs.md`, and the staged ADR-004 package in `proposals/`.

## 8. Consistency check of this design

| Aspect | Statement | Holds because |
|---|---|---|
| Map ↔ tree | every path in section 3 appears once in the tree of section 1, and vice versa | section 3 lists 14 current locations + unchanged root entries; the tree lists exactly their new homes |
| Engine/domain separation | no domain artifact is under `.gtt/`, no executable GTT logic in operation under `gtt-domain/` | `context adr proposals backlog change-request session .frozen` are all domain; `index protection scaffold scripts session-adapters docs README` are all engine; the promotion scripts in `gtt-domain/proposals/` are drafts a human runs |
| Authority | architectural authority (L0/L1) lives only in `gtt-domain/context/` and `gtt-domain/adr/` (freeze regime) | `.gtt/index`, `.gtt/protection` derived; `.gtt/docs` reference; `gtt-domain/proposals` drafts; `backlog.md` development line; `session.md` derived; `AGENTS.md` and the overlay are instructions to agents |
| Protection anchors | hook regime dirs, always-writable dir and freeze marker are all under `gtt-domain/` | the only governed paths are the ones being anchored |
| Root footprint | two GTT directory names at the root | `.gtt/`, `gtt-domain/`; the rest are entry points and the ADE overlay |
| `docs/docs.md` concept section | states the same split (docs in the Engine, domain without docs) | edited to match decisions Q1 and the restated invariant |

## 9. Carry-over from the ADR-003 restructure

- Naming exceptions kept on purpose: `AGENTS.md`, `ADR-*`, `PROPOSAL-*`, `SOURCE-BRIEF.*`, `CLAUDE.md`, `SKILL.md`.
- The identity registry keeps retired identities and refuses to register a new file at a retired identity's path: use distinct staged names (`-adr-004`), and retire
  staged files with `gtt-reconcile.sh --retire` after promotion. **Fixing that limitation is a separate change (Q6).**
- Lessons that shaped the scripts: a validation that hides its output hides the cause; a CRLF script breaks bash; a consumed staged file leaves a dangling
  identity unless reconciled; an interrupted run must roll back; L0 hashes are re-checked after `yes`.
- Known gaps still open: the two pre-existing `WARN`s on `readme-gtt.es.md` anchors; `gtt-check-adapter.sh` SKIPPED in a catalog repository; host-project
  collisions handled by instruction only; Claude Code hooks have no live-session verification of the new hook.
