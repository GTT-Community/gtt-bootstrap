# Step 6 - Register the sources and write the design of each Epic

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

Part of the `gtt-bootstrap` skill ([SKILL.md](../SKILL.md), step 6), after the six context files
are written.


- **Sources.** Register each one with `bash .gtt/scripts/gtt-source.sh add <file> --id <ID> --apply` (it copies the
  file to `docs/sources/<ID>/v1/` and records its hash) or `adopt <path> --id <ID> --apply` for one that stays
  where it is. The completed questionnaire is a source too: add it as `IDQ`. Never edit a source afterwards.
- **The method cuts the Epics.** Before cutting Epics or writing a design, read every chosen
  pack (`bash .gtt/scripts/gtt-method.sh show <id>`) and follow its *Efecto en el diseño*. With
  Vertical Slice there are no horizontal Epics - no "data model", "API", "backend" or
  "frontend" Epic: each Epic is a business result cut into end-to-end slices, the first one the
  thinnest that crosses the whole stack. With Walking Skeleton the first Epic is the skeleton
  and says `**Kind:** skeleton`. With DDD each Epic names its `**Bounded context:**`; combined
  with Vertical Slice, DDD defines the Epics and Vertical Slice cuts them. The Epics you derive
  stay `Proposed`: the cut is a proposal, the human approves each Epic. With the method `OPEN`,
  or when none is declared, cut by the sources alone and say so.
- **One design per Epic.** For every `Proposed` Epic in scope run
  `bash .gtt/scripts/gtt-design.sh scaffold EPIC-NNN --apply`, then fill
  `gtt-domain/context/design/EPIC-NNN.md`: list under *Source sections* every section of the sources that belongs
  to the Epic and carry its content over **in full** - data, rules (`R-n`), flows (`F-n`, with their error path),
  interfaces (`I-n`), examples (`E-n`) - a `[FUENTE: ID:§…]` on every line. Do not summarise and do not decide:
  what the sources do not define is a `[VACÍO]`. When a method is declared, the scaffold has already put the
  pack's *Plantilla de diseño por Epic* in section 1 (with Vertical Slice, one `### S-n` per slice: use case,
  input / output, logic, data it touches, acceptance criterion, out of this slice); fill it from the sources with
  the same marks (`[FUENTE]`, `[VACÍO]`, `[CONFLICTO]`; a `[PROPUESTA]` only while it is a draft) and point it at
  the items of sections 2 to 6. A slice is design, not a Story: THINK does not turn slices into executable
  Stories.
- **Ask.** Turn the `[VACÍO]`s into questions under `@gtt · Design EPIC-NNN`: at most five a turn, grouped by
  Epic, with options where the source suggests them. Each answer is written in section 8 as `D-n`, with who and
  when, and closes its `[VACÍO]`.
- **Check.** `bash .gtt/scripts/gtt-check-design.sh` must pass: eight sections, every listed source section
  cited, every rule and flow in an example. This is the same in every Autonomy Profile and at every THINK Depth.
  `bash .gtt/scripts/gtt-method.sh check` must hold too: no Epic cut by layer when the method forbids it, the
  skeleton first, every slice with its fields. It reports; it never corrects the backlog or a design for you.
- **Stories.** Write them in the backlog's format: `Implements: design/EPIC-NNN#R-2, #F-1, #E-1`, a `Context:` of
  at most five lines each ending with its anchor, and `Done when:` naming an example of the design and its test
  file. A Story cites the design; it never cites a source and never decides.
- **Approval is the human's.** Give the command - `bash .gtt/scripts/gtt-approve.sh EPIC-NNN` - and never write
  `Approved` yourself.
