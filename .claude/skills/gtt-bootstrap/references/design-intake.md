# Step 2 - The design intake

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

Part of the `gtt-bootstrap` skill ([SKILL.md](../SKILL.md), step 2): what to do with the design
once step 2 knows whether a document exists. Every message to the human still opens with
`@gtt · <what this is>`.

### Assess the design (a design document exists)

A document existing is not the same as a design being good enough to govern. Before
asking whether it is finished, read it — all of them, when there are several — and write
down how good it is. This is the first act of the Think stage, and it produces a document,
not a conversation.

1. Materialize the working copy: `bash .gtt/scripts/gtt-template.sh materialize design-assessment`
   (dry run), then `--apply`. It creates `gtt-domain/proposals/bootstrap/design-assessment.md`.
   Read its *Operating contract* and follow it.
   **Establish the THINK Depth before rating anything.** Ask once, showing the three levels
   as the template describes them — `QUICK` (simple or small designs: floor areas and
   critical gaps, a reduced questionnaire), `STANDARD` (ordinary projects: the complete
   assessment, stack alternatives with trade-offs, an adaptive questionnaire), `DEEP`
   (complex, critical or uncertain systems: exhaustive assessment, architectural as well as
   stack alternatives, dependencies and risks, a deep iterative questionnaire). Record the
   answer in the *THINK Depth* block with who and when. Never infer it — not from the
   project's size, not from the Autonomy Profile (a different thing; the two are independent),
   not from a previous project. If the human does not choose, leave it empty: `STANDARD`
   applies as a fallback and you report it as *not selected*, never as a choice.

   The depth changes how far you dig, never which rule you may skip. At `QUICK` the floor
   is still assessed line by line, a design below it is still `POOR`, and an area you did
   not assess is written `not assessed (QUICK)`, never `SOLID`.

   **Escalation is a proposal.** If what you find justifies a deeper level — regulated
   data, requirements that constrain the architecture, several integrations, documents
   that disagree on a structural point, a floor line with no obvious way to meet it — add
   a row to the *Escalation log* with the evidence, tell the human in one line, and keep
   working at the current depth until they decide. Only an accepted row changes the depth.
   `bash .gtt/scripts/gtt-project.sh think` reports the recorded depth and fails on a depth
   nobody decided or a verdict above `POOR` with the floor unmet.
2. Fill sections 1–5: the documents assessed; how several documents are resolved (the
   Solution Designer's choice above); each area rated `SOLID`, `THIN` or `MISSING` with the
   `[FUENTE: file:line]` that supports the rating; the minimum floor; the verdict. Rate what
   the documents say, never what you assume the author meant.
3. The floor is not negotiable: the problem and scope are stated, the architectural style is
   stated, **the technology stack is decided** (language and runtime, framework, compute
   model) and **the datastore is decided** or explicitly not needed. A design below the
   floor is `POOR`, whatever else it gets right.
4. Fill section 6, the strengthening plan. For every stack layer that is undecided, or
   decided without a reason, give the options that fit **this** project — its requirements,
   constraints, team and scale as the documents state them — with the trade-offs of each
   and a recommendation that says what it optimises for and what it gives up. Each option
   and each recommendation is a `[PROPUESTA]`. When the documents do not say enough to
   recommend, say so and ask; never recommend a generic favourite, and never write a stack
   choice as decided because you recommended it.
5. Report the verdict in a few lines — verdict, what is thin or missing, what you recommend —
   and ask the Solution Designer how to proceed:
   - **`STRONG`** — offer strengthening; they may skip it.
   - **`ADEQUATE`** — offer strengthening and recommend it for the areas listed.
   - **`POOR`** — the design must be strengthened before it is used. Do not map it into the
     six files as it is; say plainly that the floor is not met and which line fails.
6. **Strengthening** is written, not talked about, and it reuses the one instrument the
   Bootstrap has for this: materialize the Initial Design Questionnaire (below), carry into it
   what the documents already establish — each statement with its `[FUENTE: file:line]` — and
   conduct the interview only for the areas rated `THIN` or `MISSING`. The decisions the
   Solution Designer takes on section 6 are recorded there as human decisions; an option
   nobody decided stays a `[PROPUESTA]` and maps to nothing. The original documents are never
   rewritten. The completed questionnaire is then the source document, exactly as when there
   was no document at all.

The assessment decides nothing and governs nothing. It is removed by `gtt-freeze.sh` with
the other bootstrap drafts.

### Help me choose: a development method that is still OPEN

When `gtt-method.sh get` shows the method `OPEN` - the human asked for help, or left a
question unanswered - THINK proposes; it never decides. Once the sources are read (the
assessment above, or the questionnaire's sections 4 to 13):

1. Read the packs (`bash .gtt/scripts/gtt-method.sh show <id>` for each candidate) and
   compare their *Conviene si* and *Qué descarta* with what the sources establish.
2. Propose one method - or one combination - under `@gtt · Development method` as a
   `[PROPUESTA]`: the packs, the reason in two or three lines, the `[FUENTE: file:line]`
   of the dossier each part of the reason rests on, and what the proposal discards. When
   the sources do not say enough to propose, say so and ask; never fall back on the
   recommended pack.
3. **Do not cut Epics or write any Epic design until the human answers.** A confirmed
   proposal is recorded with `gtt-method.sh select ... --apply`. If the human prefers to
   leave it open, it stays `OPEN` - typed and visible in step 4 - and the designs follow
   no method template.

A `[PROPUESTA]` never reaches governed context: only the human's answer does.

### Git workflow: report what the project says, adopt nothing

Run `bash .gtt/scripts/gtt-workflow.sh detect` once, while you read the sources. If the project's
documents mention a commit convention (Conventional Commits, commitlint, commitizen, a
`.gitmessage`), it prints one `@gtt · Finding` line - give it to the human as it is. Never adopt
it and never write `gtt-domain/workflow.md`: that file is the human's, and the finding already
names the line they would add. Without it the defaults hold: you commit only when asked.

### The Initial Design Questionnaire (no sufficient design document)

If the human has no design document, or the assessment above found it `POOR`, or they chose
to strengthen it, do not improvise an interview: offer the Bootstrap's Initial Design Questionnaire. It is owned
by the Bootstrap (`.gtt/scaffold/templates/gtt-initial-design-questionnaire.md`, declared
under `templates:` in the manifest); there is exactly one, and you never copy or
paraphrase it anywhere else.

1. Materialize the working copy: `bash .gtt/scripts/gtt-template.sh materialize initial-design-questionnaire`
   (dry run), then `--apply`. It creates `gtt-domain/proposals/bootstrap/initial-design-questionnaire.md`,
   never overwrites an existing one and registers it in the index. To resume an earlier
   session, open the existing copy instead.
2. Read the questionnaire's *Operating Contract* (section 1) and follow it: inspect the
   project before asking, ask progressively — never the whole form at once — and populate
   the document as the conversation goes. When there is no Design Assessment, establish the
   THINK Depth here before the first question — ask once, record it in the questionnaire's
   *THINK Depth* block, never infer it; with an assessment, the depth recorded there applies
   and this block stays empty. Escalation is proposed in the questionnaire's own log.
3. Keep provenance honest: `[FUENTE: archivo:línea]` for what the project shows, `[VACÍO]`
   for what is not established, `[CONFLICTO]` when sources or answers disagree,
   `[PROPUESTA]` for an option you suggest. A proposal is never a decision, an ADE
   inference is never a human decision, and you never fill `Human decision` for the human.
4. Stop when the human has reviewed the summary (section 24) and Readiness (section 23) is
   `READY` or `READY_WITH_OPEN_ITEMS`, or when they decide to continue later. `NOT_READY`
   is the same as an unfinished draft (step 3): stop.
5. From then on the questionnaire is the source document: step 3's confirmation is about
   it; step 4 maps it to the six files — a `[VACÍO]` becomes an empty cell, an unresolved
   `[CONFLICTO]` is asked again, and a `[PROPUESTA]` becomes context only if a
   `Human decision` records it; step 6 preserves the completed questionnaire verbatim as
   `SOURCE-BRIEF.md`. The working copy under `gtt-domain/proposals/bootstrap/` is removed
   by `gtt-freeze.sh` together with the other bootstrap drafts.

The questionnaire never becomes governed architecture by being filled in.
