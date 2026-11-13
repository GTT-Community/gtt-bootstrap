# Ideas — what you want changed

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

Each file here is an `IDEA-NNN.md`: your own words, exactly as you wrote them. It is the input door of the Inbox, the
one pipeline for every change.

- **Write:** `gtt idea add "<text>"` (or `--file F`), or a request with fields: `gtt idea add --type solicitud --change "…" --reason "…"`
  (`gtt change` is a shortcut for it; `gtt-domain/change-request.md` is retired). `--now` asks for triage in the agent's first answer.
- **Never edited:** GTT and the agent only append dated lines under the final `---`: `Triage`, `Revisión`, `Decisión`, `Paquete`,
  `Ratificada`, `Trabajo`, `Cerrada`. The stage (`new`, `review`, `accepted`, `ratify`, `work`, `closed`, `parked`, `rejected`) is the last line.
- **Triage** is the agent's: a Story (no question), covered by an Epic, a question, or a proposal (`PROP-NNN`) with a review for you.
- **Yours:** `gtt answer N k` (the review), `gtt inbox park|reopen|reject REF`, `gtt inbox priority REF urgent|normal|low`, `gtt idea drop REF`.
- **See them:** `gtt inbox` (by stage), `gtt inbox show IDEA-NNN` (with its trail), or Sonar's Inbox panel.

An idea is a source, so it is never deleted and its number is never reused. The architect's ADR drafts live in `gtt-domain/adr/drafts/`.
