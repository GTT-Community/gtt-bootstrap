---
description: GTT - start or resume what GTT is waiting on (the Initial Design Questionnaire while it is open)
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

# /gtt

An entry point, never a second copy of the method: the procedure is in `AGENTS.md`.

1. Run `bash .gtt/scripts/gtt-session-context.sh` and read what it prints. It is
   operational state, never authority.
2. If it prints `## Next action` naming the Initial Design Questionnaire, start or
   resume it, opening every message with `@gtt · Initial Design Questionnaire`:
   - read the working copy it names, from its *Operating Contract for the ADE* on;
   - inspect the project and what the user already said, and record what that answers;
   - ask one question per message, in plain words, with numbered options the user can
     answer with a number (the last one "Other (write it)"), never a list or a whole section
     (the questionnaire's section 2 → *How each turn looks*);
   - write each round into the working copy before the next one, never ask again what
     it already answers, never overwrite a human answer, never turn a `[PROPUESTA]`
     into an answer or a decision.
   The rules are `AGENTS.md` → *Bootstrap behavior* and *Initial Design Questionnaire*,
   and `.gtt/contract/elicitation.json` → `start`, `state`, `persistence`.
3. If there is no `## Next action`, say in one line that GTT is waiting on nothing,
   summarize the `## Review` block of the session state, and continue with the user's request.
