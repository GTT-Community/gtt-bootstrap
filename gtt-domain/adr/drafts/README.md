# ADR drafts — where the architect writes

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

This is the architect's desk for an ADR written by hand. It is part of the Inbox: a draft here is an entry
(`IDEA-NNN-<slug>.md`, `Tipo: adr · Nivel: arquitectura`), never a decision. `gtt-domain/adr/` itself stays
as it was at the freeze and is changed only by `gtt promote`.

## Flow

1. **Create it:** `gtt adr new "<title>"` writes `IDEA-NNN-<slug>.md` from `ADR-TEMPLATE.md` (`--file F` registers one
   written elsewhere). Fill in Context, Decision and Consequences in your editor.
2. **Adopt a hand-written ADR:** a new file placed straight in `gtt-domain/adr/` after the freeze is not a promotion. Sonar shows it
   as "ADR written by hand"; `gtt adr adopt <file>` moves it here and `adr/` returns to its frozen state.
3. **It becomes `accepted` by itself** when no `<…>` marker is left and Context, Decision and Consequences are filled in: you already
   decided, so there is no review (in the Team profile, a draft by someone other than the `architecture` role opens a REV for that person).
4. **The agent packages it as written** (`gtt-stage.sh ... --origin IDEA-NNN`): your text unchanged as `ADR-NNN-<slug>.md`, the stack map
   delta, the change log row, and a "Clashes" section if it contradicts another ADR, a constraint or the code. It never touches your decision.
   If you edit the draft afterwards, GTT reports the package as out of date and the agent redoes it.
5. **You ratify:** `gtt promote ADR-NNN-<slug>`. The draft then moves to `done/`; nothing is deleted.

The agent can read these files but never write them. The trail of dated lines under the final `---` is added by the engine.
Details: `.gtt/docs/agents/operations.md` → *Inbox*.
