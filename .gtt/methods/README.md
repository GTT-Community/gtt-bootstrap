# Method Packs

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

The catalog of development methods GTT can govern - **Method Governance**: the human declares a method at
setup, the freeze ratifies it as the **Method Lock**, and **Method Conformance** checks it afterwards.

```text
declare (gtt init / THINK)  ->  ratify (freeze)  ->  verify (gtt-method.sh check, gtt check, CI, audit)
```

One file per method. A pack is the **single source** of a method's texts: the questionnaire of `gtt init`, the
THINK skills and the site read them from here (`gtt-method.sh list | show`, operations `method.list` and
`method.show`) and never write a parallel version. Adding a pack adds an option to the questionnaire without
changing the CLI. The questions themselves, and their extra options, are `.gtt/contract/methods.json`.

| Pack | Kind | Question | Recommended | ADR | Verification |
|---|---|---|---|---|---|
| [vertical-slice](vertical-slice.md) | architecture-style | development | yes | yes | partial |
| [layered](layered.md) | architecture-style | development | no | yes | partial |
| [ddd](ddd.md) | architecture-style | development | no | yes | partial |
| [hexagonal](hexagonal.md) | architecture-style | development | no | yes | partial |
| [event-first](event-first.md) | architecture-style | development | no | yes | partial |
| [walking-skeleton](walking-skeleton.md) | decomposition-strategy | start | yes | no | partial |

`bash .gtt/scripts/gtt-method.sh catalog` checks this directory: it is part of `gtt-validate.sh`.

## Pack format

A YAML frontmatter, then fixed sections. The frontmatter is read by scripts; keep every value on one line.

```yaml
---
id: vertical-slice                 # the file name without .md
name: Vertical Slice
kind: architecture-style           # architecture-style | decomposition-strategy
question: development              # development | start - the questionnaire question it appears in
recommended: true                  # shown as (recommended); never applied in silence
requires_adr: true                 # an architectural style is locked by an ADR; a decomposition strategy is not
compatible_with: [walking-skeleton, ddd]
incompatible_with: [layered]       # symmetric: if A lists B, B lists A
verification: partial              # verified | partial | declared-only
---
```

| Section | Required | Read by |
|---|---|---|
| `## Qué es` | yes - 2 to 3 lines | questionnaire (es), site |
| `## Conviene si` | yes - one line | questionnaire (es), site |
| `## What it is` | yes - the English text of *Qué es* | questionnaire (en) |
| `## Fits when` | yes - the English text of *Conviene si* | questionnaire (en) |
| `## Qué descarta` | yes - a method that discards nothing has not earned its place | THINK, site |
| `## Efecto en el diseño` | yes - how Epics are cut, how the Epic design is structured, what goes in architecture.md, what rules it adds to stack.md view 5 | THINK |
| `## Plantilla de diseño por Epic` | yes - one ```` ```gtt-epic-template ```` block | `gtt-design.sh scaffold` |
| `## Verificación` | yes - one ```` ```gtt-method-rules ```` and one ```` ```gtt-method-checks ```` block, then what freeze, `gtt check` / CI and audit each check | `gtt-method.sh check`, `gtt-method.sh rules` |

### `gtt-epic-template`

Inserted by `gtt-design.sh scaffold` into section 1 of the Epic design (`gtt-domain/context/design/EPIC-NNN.md`),
after `**Source sections:**`. The eight sections of the design are never changed: a method adds structure inside
section 1 and cites the items of sections 2 to 6 (`#R-n`, `#F-n`, `#I-n`, `#E-n`).

### `gtt-method-rules`

The method's rules in a neutral form, one per line:

```text
ID | FROM | MUST NOT DEPEND ON | MAY DEPEND ON | CHECK
VS-1 | slice | another slice | shared kernel | dependency
```

`FROM` and the other columns name roles (slice, domain, bounded context), not paths. `CHECK` is `dependency` -
a dependency rule a language adapter can verify - or `audit: <what a human judges>`. When the method is ratified,
every `dependency` rule is written into `gtt-domain/context/stack.md` section 5 with the project's real paths, as
`architecture.md` declares them, and the rule id in the *Rule* column.

### `gtt-method-checks`

What the freeze checks of the backlog and the Epic designs, one `key: value` per line. Every key is optional.

| Key | Fails the freeze when |
|---|---|
| `epic-forbidden-kind: layer` | an Epic that is not `Cancelled` has `**Kind:** layer` |
| `epic-forbidden-title: term, term` | an Epic's title starts with one of the terms (a technical layer) |
| `epic-required-fields: Field` | an approved Epic (`Planned`, `In Progress`, `Completed`) lacks the field |
| `first-epic-kind: skeleton` | the first Epic (lowest number, not `Cancelled`) does not have `**Kind:** skeleton` |
| `first-epic-design-fields: Field, Field` | the approved design of the first Epic lacks one of the fields in section 1 |
| `design-fields: Field, Field` | an approved design lacks `**Field:**` (with content) in section 1 |
| `design-unit: S` and `design-unit-fields: Field, Field` | an approved design has no `### S-n` subsection, or one of them lacks a field |

A draft design is reported, never failed: the freeze fails only on approved designs, as the design gate does.

## The Method Lock

The ratified choice. It lives in the governed context, so after the freeze an agent never writes it: a change
goes through `gtt-domain/proposals/` (`gtt-propose-change`, with an impact analysis) and a new freeze.

**Readable by people** - the section `## Architectural style` of `gtt-domain/context/architecture.md` states the
method or the combination, and why.

**Readable by machines** - in that same section, one block:

```gtt-method
style: vertical-slice, ddd
start: walking-skeleton
status: ratified
locked_by: ADR-002
verification: partial
```

| Key | Value |
|---|---|
| `style` | one or more ids of packs with `question: development`, comma separated, or `OPEN` |
| `start` | the id of a pack with `question: start`, `direct` (straight to the main functionality), or `OPEN` |
| `status` | `ratified`, or `open` while `style` or `start` is `OPEN` |
| `locked_by` | `ADR-NNN` when a chosen pack has `requires_adr: true`, otherwise `none`; `OPEN` while `status: open` |
| `verification` | the weakest `verification` of the chosen packs (`verified` > `partial` > `declared-only`) |
| `gap` | only while `status: open`: the `GAP-NNN` of an `OPEN` gap in the `gtt-gaps` register whose topic is `Development method` |

**Visible in the map** - `gtt-domain/context/stack.md` section 1 carries the row `Development method`: the chosen
ids under *Technology* and `locked_by` under *Locked by*. An open method leaves *Technology* empty and shows
`OPEN` under *Locked by* - never an empty cell. Its dependency rules are in section 5, and the map change log has
the row of the ADR that locks it.

An open method does not block the freeze: it is typed (an `OPEN` gap with its scope) and visible. It never
authorises anything: until the human decides, no pack's template or rule applies.

`bash .gtt/scripts/gtt-method.sh check` validates all of this (`--pre-freeze` is what `gtt-freeze.sh` runs);
`gtt-method.sh lock --json` and `gtt-method.sh rules --json` are what the CLI reads. A project with no
`gtt-method` block and no setup selection declares no method: nothing is checked, and that is reported.

## The setup selection

Before the freeze, the answers of the questionnaire are recorded with
`bash .gtt/scripts/gtt-method.sh select --style <ids|help> --start <id|direct|help> --apply` in
`.gtt/development-method.json`. It is a setup answer, never governed context: the bootstrap carries it into the
Method Lock with the human's confirmation. `help` decides nothing - THINK proposes a method as `[PROPUESTA]`
with its reason and the human confirms - and an unanswered question is `OPEN`. The recommended packs are shown
as recommended and never applied in silence. After the freeze `select` is refused: changing the ratified method
is a change request.
