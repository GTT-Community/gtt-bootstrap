# Proposals — the agent's side of the Inbox

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

What you write is an `IDEA-NNN` (`docs/ideas/`); what the agent writes is a **`PROP-NNN`** here. A proposal is a
**draft, not a decision**: nothing in this directory governs anything. It exists so the agent can hand you a complete,
reviewable artifact without ever touching `gtt-domain/context/` or `gtt-domain/adr/`.

## Flow

```
docs/ideas/IDEA-NNN.md  →  triage (agent)  →  PROP-NNN + REV-NNN  →  you answer (gtt answer N k)  →  package (staged/)  →  you run gtt promote / approve / run  →  new freeze
   you write              agent              the engine writes it     accepted / parked / rejected    agent stages           the Human Promotion Boundary
```

1. The agent writes its draft in `drafts/<slug>.md` (free) and registers it with
   `bash .gtt/scripts/gtt-inbox.sh propose --file F --level arch|spec|scope --form N [--origin IDEA-n|OBS-n|STORY-n]`.
   The engine writes `PROP-NNN-<slug>.md` with its header and a trail, opens the `REV` and stores a sha of what you see.
   From then on the agent cannot edit it: to correct it, it uses `gtt-inbox.sh supersede PROP-n --file F`.
2. You answer the REV (accept with priority urgent, normal or low; park; reject). Each step adds a dated line to the
   trail (`Revisión`, `Decisión`, `Paquete`, `Ratificada`, `Trabajo`, `Cerrada`); the stage is the last line.
3. Accepted, the agent stages the **promotion package** with `gtt-stage.sh <name> --origin PROP-n ...`: for architecture
   (`gtt-propose-change` forms 1-3, `gtt-adr`, or a `gtt-drift-response` track) the ADR draft and the full text of every affected
   `gtt-domain/context/` file as one promotion set under `staged/ADR-NNN-<slug>/`. After the freeze `gtt-stage.sh` refuses a set that
   touches `gtt-domain/context/` or `gtt-domain/adr/` without an `--origin` that is `accepted`. You apply it with
   `gtt promote ADR-NNN-<slug>` (diff, `apply`, all or nothing, undo printed); the agent never runs it and never writes an
   application script by hand — see `AGENTS.md` → *Human Promotion Boundary*.
4. An Epic proposal (`gtt-propose-change` form 4, level scope): the agent writes the Epic `Proposed` with `Origin: PROP-n` and
   `Priority`, stages its design, and a `RUN-n` carries `gtt promote <set>` and `gtt approve EPIC-n`; you run `gtt run n`. A
   specification change to an existing Epic is staged without an ADR (the engine records a `CHANGE-…`). Stories never pass through
   here: they are the working plan of whoever does the work, and nobody approves one.

`gtt inbox --origin agent` (alias `gtt proposals`) lists them by stage. `gtt-domain/change-request.md` is retired:
`gtt change` is a shortcut for `gtt idea add --type solicitud`. Before the freeze there are no proposals: the agent writes the context
directly (`bootstrap/`), and the freeze ratifies it all.

## A wording fix to the agent contract

`AGENTS.md` is written only by you, whatever the change. But a fix that changes no rule - a typo, a
path that moved, a clearer sentence - is not a governed change: it needs no proposal, no ADR and no
hand-written script. The agent stages the full corrected file as a promotion set and gives you the one command.
The detail of the contract under `.gtt/docs/agents/` is ordinary documentation in the Bootstrap
repository, and protected like the rest of the instruction plane in an installed project.

## Lifecycle

| State | Meaning |
|---|---|
| `drafts/<slug>.md` | the agent's draft, before it is registered. Free |
| `PROP-NNN-<slug>.md` | a registered proposal; its trail says the stage. Written only by the engine |
| `ADR-DRAFT-<slug>.md` + any `context-<file>.md` drafts, then `staged/ADR-NNN-<slug>/` | an accepted change's promotion package — review it, then run `gtt promote ADR-NNN-<slug>` |
| `staged/<name>/` | a promotion set: `promote.json` (the reason, `origin`, each file and where it goes) and the staged copies. Removed when it is applied |
| `bootstrap/` | the `gtt-bootstrap` skill's one-time draft of all six `gtt-domain/context/` files, plus `SOURCE-BRIEF.*` if a source document existed |
| `done/` | proposals whose work finished (nothing is deleted) |
| `withdrawn/` | rejected proposals, and what a set held when it was withdrawn |

## Naming

`PROP-NNN-<slug>.md`. The number is the engine's and is never reused (it counts `done/` and `withdrawn/` too). The ADR number is taken
when the package is staged: `ADR-DRAFT-<slug>.md` and the set `staged/ADR-NNN-<slug>/` match the `gtt-domain/adr/ADR-NNN-<slug>.md` the
promotion will create.
