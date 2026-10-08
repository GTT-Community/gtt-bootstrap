# Proposals — staging area

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Agent-writable. This is the only governed place an agent may create files.

A proposal here is a **draft, not a decision**. Nothing in this directory
governs anything. It exists so the agent can hand you a complete, reviewable
artifact without ever touching `gtt-domain/context/` or `gtt-domain/adr/`.

## Flow

```
gtt-domain/change-request.md  →  gtt-domain/proposals/  →  you review, then `bash .gtt/scripts/gtt-promote.sh <name>`  →  gtt-domain/adr/ + gtt-domain/context/  →  new freeze
                                                or a direct edit (an approved Epic)     or gtt-domain/backlog.md
   you write intent         agent drafts             the Human Promotion Boundary
   (always writable)        (agent writable)
```

For an architecture/context/conflict change (`gtt-propose-change` forms 1-3,
or a `gtt-drift-response` track), once you approve the proposal the agent
stages a full **promotion package** here: the ADR draft, the full text of
every affected `gtt-domain/context/` file, staged as one promotion set under
`staged/ADR-NNN-<slug>/`. Review it, then apply it yourself with
`bash .gtt/scripts/gtt-promote.sh ADR-NNN-<slug>`: it shows the diff, asks for
`apply`, applies everything or nothing and prints its undo. The agent never runs
it and never writes an application script by hand — see `AGENTS.md` → *Human
Promotion Boundary*.

An Epic proposal (a new or removed Epic, or a material change to its goal or
scope — `gtt-propose-change` form 4) is written into `gtt-domain/backlog.md`
after you approve it, not via a script — it does not get an ADR unless it also
happens to touch governed context. Stories never pass through here at all:
they are the working plan of whoever does the work, and nobody approves one.

## A wording fix to the agent contract

`AGENTS.md` is written only by you, whatever the change. But a fix that changes no rule - a typo, a
path that moved, a clearer sentence - is not a governed change: it needs no proposal, no ADR and no
hand-written script. The agent stages the full corrected file as a promotion set and gives you the one command.
The detail of the contract under `.gtt/docs/agents/` is ordinary documentation in the Bootstrap
repository, and protected like the rest of the instruction plane in an installed project.

## Lifecycle

| State | Meaning |
|---|---|
| `PROPOSAL-<slug>.md` | awaiting your review |
| `ADR-DRAFT-<slug>.md` + any `context-<file>.md` drafts, then `staged/ADR-NNN-<slug>/` | an approved change's promotion package — review it, then run `bash .gtt/scripts/gtt-promote.sh ADR-NNN-<slug>` |
| `staged/<name>/` | a promotion set: `promote.json` (the reason, each file and where it goes) and the staged copies. Removed when it is applied |
| `bootstrap/` | the `gtt-bootstrap` skill's one-time draft of all six `gtt-domain/context/` files, plus `SOURCE-BRIEF.*` if a source document existed — the one case where a batch of files lands here instead of a single proposal |
| deleted | rejected, or promoted — the script's own output tells you it is safe to delete its staged files once it has applied them |

Delete proposals once resolved. A directory full of stale drafts is the same
failure as stale context: it makes the current state ambiguous.

## Naming

`PROPOSAL-<short-kebab-summary>.md` — no numbers. Numbering belongs to ADRs,
which are the permanent record. A proposal that never gets accepted should not
consume a number.

Once approved, the promotion package takes the ADR's reserved number:
`ADR-DRAFT-<slug>.md` and the set `staged/ADR-NNN-<slug>/`, matching the
`gtt-domain/adr/ADR-NNN-<slug>.md` filename the promotion will create.
