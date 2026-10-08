# Solution design of an Epic (template)

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Owned by the GTT Bootstrap. `bash .gtt/scripts/gtt-design.sh scaffold EPIC-NNN --apply` materializes
everything below the line into `gtt-domain/context/design/EPIC-NNN.md`. The design is the complete
specification of its Epic: everything the sources say about it - data, rules, flows, interfaces,
examples - carried over in full and cited, not summarised. A Story is built from the Story and this
file; a source is opened only to verify a citation. What the sources do not define is written as
`[VACÍO]`, never left out. Architecture is not decided here: that is an ADR. UI copy, cosmetic
detail and how something is built are not here either: that is work.

The eight sections always exist; one that does not apply says `N/A — <reason>`. Every R, F, I and E
carries a `[FUENTE]` or points to a `D-n`. Ids are stable and never reused. Every rule and every
flow appears in at least one example, and a flow includes its error path.

------------------------------------------------------------------------

# EPIC-NNN — <title> · Solution design

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

**Epic:** gtt-domain/backlog.md → EPIC-NNN · **Status:** Draft
**Follows:** <architecture.md#section · ADR-NNN>

## 1. Purpose and scope

<what this Epic delivers and where it stops>

**Source sections:** <every section of the sources that belongs to this Epic, e.g. D:§16–22 · ARQ:§3.4>

## 2. Data

<entities, fields, types, states, validations - each line with its [FUENTE: …]>

## 3. Rules

- **R-1** <rule> [FUENTE: <D:§…>]

## 4. Flows

- **F-1** <name>: <steps, including the error path> [FUENTE: <D:§…>]

## 5. Interfaces

- **I-1** <API, event, file or UI contract, with its fields> [FUENTE: <D:§…>]

## 6. Examples

- **E-1** (R-1, F-1) Given <…>, when <…>, then <…>. [FUENTE: <D:§…>]

## 7. Open points

- [VACÍO: GAP-NNN] <what the sources do not define>

## 8. Decisions taken with the human

- **D-1** <question> → <answer> — <who> — <YYYY-MM-DD>
