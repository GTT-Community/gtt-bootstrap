# PROPOSAL — Backlog: Epic "GTT — Antigravity ADE Support"

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

**Status: Superseded (2026-10-06).** Esta propuesta se escribió bajo el modelo anterior, en el que cada
Story se diseñaba y se aprobaba una por una antes de implementarla (`Undesigned`, `Design Approved`,
"Story by Story"). La arquitectura de dos planos lo reemplazó: nadie aprueba una Story, y solo una Epic
es gobernada (`AGENTS.md` → *The two planes*, *Backlog*). Nada de lo que sigue está vigente ni pide una
decisión. El trabajo que describía la STORY-001 está hecho; la verificación en ejecución que describían
la STORY-002 y la STORY-003 sigue pendiente y figura como tal en `.gtt/docs/evidence.md`. Se conserva
como registro.

Borrador original, no decisión. Fecha: 2026-10-05.
Diseño de referencia: `gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md`.

```text
Proposed Backlog Change

Kind: new Epic + three new Stories
Epic/Story ID: EPIC-001, STORY-001, STORY-002, STORY-003
               (los ids que da `gtt-project.sh next-id`; el EPIC-001 / STORY-001 que hoy muestra
               gtt-domain/backlog.md es el ejemplo de la plantilla y quedaría reemplazado)
Current state: none — el backlog solo contiene el ejemplo de la plantilla
Suggested change: añadir el Epic y las tres Stories de abajo
Resulting Story status: Undesigned hasta que cada una se apruebe por separado; entonces Ready
Reason: el Solution Designer aprobó el diseño base el 2026-10-05 y pidió la línea de desarrollo
Contradicts governed context or an ADR?: no — gtt-domain/context/ es todavía la plantilla y
               ADR-001 no trata de ADEs
Impact: da a la implementación una Story escrita contra la que trabajar; sin ella no se puede
        implementar
Risk: STORY-002 y STORY-003 necesitan Antigravity instalado; en esta máquina no hay binario
      `agy` ni `antigravity` en el PATH. Si nadie puede ejecutarlas, el Epic no se cierra.

Status: Requires Solution Designer approval
```

```text
Proposed Epic Design

Epic: EPIC-001 — GTT — Antigravity ADE Support
Sources read: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md, .gtt/scaffold/manifest.yaml,
              .gtt/scripts/gtt_ade.py, .gtt/scripts/gtt_protect.py, .gtt/tests/bootstrap-acceptance.py,
              AGENTS.md, documentación pública de Antigravity (hooks, rules, skills)

Gaps and conflicts: none dentro de las Stories. Lo que no se sabe de Antigravity no se rellena:
              es exactamente lo que STORY-002 y STORY-003 salen a observar.
Agent proposals to decide: cada línea marcada [PROPUESTA] abajo. Las tres de más peso:
              (1) la división en tres Stories y su orden;
              (2) STORY-001 sale con código 2 al denegar, igual que Cursor y OpenHands, y
                  STORY-002 lo corrige si Antigravity no lo respeta;
              (3) el Epic no se cierra, ni se anuncia el soporte, sin STORY-002 y STORY-003.
Contradicts governed context or an ADR?: no

Status: Requires Solution Designer approval, Story by Story
```

Los bloques van en inglés porque se copian tal cual a `gtt-domain/backlog.md`.

---

### EPIC-001 — GTT — Antigravity ADE Support

**Status:** Proposed
**Goal:** Google Antigravity is a registered GTT ADE with its own id, governed by the same
contract as every other ADE, and every claim GTT makes about its real-time enforcement is
backed by an observed run or stated as unverified.

#### Stories

##### STORY-001 — Antigravity overlay v1: registry, rules, hook format, tests, docs

- **Status:** Undesigned
- **Priority:** High
- **Description:**
  - Antigravity becomes a GTT ADE with its own registry id `antigravity`; `codex` is not used as an alias or approximation. [HUMANO: Solution Designer, 2026-10-05]
  - GTT integrates Antigravity inside its existing model: one registry line, three overlay files, one format in the shared protection engine. No new capability model and no change to the registry schema. [HUMANO: Solution Designer, 2026-10-05]
  - "Supported" in this Story means GTT's integration support — registry, detection, install/update/remove, participating, Primary, the contract through `AGENTS.md` plus a specific rule, validation and CI. It never means real-time enforcement guaranteed by Antigravity. [HUMANO: Solution Designer, 2026-10-05]
- **Scope:**
  - Add the `antigravity` entry to `overlays:` in `.gtt/scaffold/manifest.yaml` with `path: .agents/rules/gtt.md`, `entry: AGENTS.md`, `owned: [.agents/rules/gtt.md, .agents/rules/gtt-implementation.md, .agents/hooks.json]`, `detect: [.agents/rules/, .agents/hooks.json, .agents/workflows/, .agent/]`, `enforcement: realtime-hook-unverified`. [FUENTE: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md]
  - Add `.agents/rules/gtt.md` to the catalog: frontmatter `trigger: always_on`; short; refers to `AGENTS.md` instead of copying it; states the governed paths, the promotion-script rule, the `@gtt ·` marker, the situation-to-section table, and the instruction to run `bash .gtt/scripts/gtt-session-context.sh` when a session starts. [FUENTE: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md]
  - Add `.agents/rules/gtt-implementation.md` to the catalog: frontmatter `trigger: glob`, mirroring `.cursor/rules/gtt-implementation.mdc`. [PROPUESTA]
  - Add `.agents/hooks.json` to the catalog: one named hook, event `PreToolUse`, matcher `run_command|write_to_file|replace_file_content|multi_replace_file_content`, command pointing at `gtt_protect.py hook --format antigravity`. [FUENTE: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md]
  - Add the `antigravity` format to `.gtt/scripts/gtt_protect.py`: project root from `workspacePaths[0]`; a pre-tool event is recognised by the presence of `toolCall`; file path from `toolCall.args.TargetFile`; command from `toolCall.args.CommandLine`; edit extent from `TargetContent`, or each chunk of `ReplacementChunks`, failing safe to the whole file when the shape is not the expected one; answer `{"decision": "deny", "reason": ...}`. [FUENTE: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md]
  - A denial exits 2, as the Cursor and OpenHands formats do. Whether Antigravity honours that is not known and is not claimed. [PROPUESTA]
  - Add `.agents/hooks.json` to the machinery pattern of `gtt_protect.py`, so an agent cannot disarm its own hook. [FUENTE: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md]
  - GTT owns the three files, never `.agents/`. A pre-existing `.agents/hooks.json` or `.agents/rules/gtt*.md` is a conflict that is reported and writes nothing; no merge is implemented. [HUMANO: Solution Designer, 2026-10-05]
  - Update the acceptance tests and add the Antigravity ones listed under Tests. [FUENTE: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md]
  - Update `readme-gtt.md`, `readme-gtt.es.md`, `.gtt/docs/docs.md`, `.gtt/docs/index.md`, `.gtt/docs/installation.md`, `.gtt/docs/installation.es.md` and `.gtt/docs/evidence.md`: the support levels, the shared `.agents/` directory, the `hooks.json` conflict, and every unverified point said as unverified. [FUENTE: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md]
- **Out of Scope:**
  - Editing `AGENTS.md`: the Solution Designer applies `gtt-domain/proposals/apply-AGENTS-antigravity.sh`. [HUMANO: Solution Designer, 2026-10-05]
  - Session Memory consolidation, checkpointing or handoff: `gtt-domain/proposals/PROPOSAL-session-memory-consolidation.md`. [HUMANO: Solution Designer, 2026-10-05]
  - A new capability model or any new registry key. [HUMANO: Solution Designer, 2026-10-05]
  - Automatic merge into an existing `.agents/hooks.json`. [HUMANO: Solution Designer, 2026-10-05]
  - Native Antigravity skills or workflows, and context injection at session start. [HUMANO: Solution Designer, 2026-10-05]
  - A `.gtt/session-adapters/antigravity.json` declaration. [PROPUESTA]
  - Any observation of the hook inside Antigravity: STORY-002 and STORY-003. [PROPUESTA]
  - Changes to `gtt_ade.py`, `gtt_manifest.py`, `gtt-check-adapter.sh`, `gtt-validate.sh` or any existing overlay. [PROPUESTA]
- **Acceptance Criteria:**
  - `gtt-ade.sh list` shows `antigravity` with exactly the three owned files and enforcement `realtime-hook-unverified`. [PROPUESTA]
  - A host containing only `.agents/skills/` does not report Antigravity as a candidate; a host containing `.agents/rules/` does, as a candidate and never as participating. [PROPUESTA]
  - `install --participating antigravity --primary antigravity` is a dry run without `--apply`; with it, the three files are copied and recorded, and the project validates with Antigravity as its only ADE and its Primary. [PROPUESTA]
  - `antigravity` and `openhands` install together with no conflict; removing either leaves the other's files in place. [PROPUESTA]
  - A host that already has `.agents/hooks.json`, or `.agents/rules/gtt.md`, gets a reported conflict, nothing written and its file unchanged. [HUMANO: Solution Designer, 2026-10-05]
  - A host's own files under `.agents/` survive install and remove untouched. [HUMANO: Solution Designer, 2026-10-05]
  - Given Antigravity's documented payload, the engine denies a write to `AGENTS.md`, a shell command that mutates a governed path, the execution of a promotion script and a shell command that removes `.agents/hooks.json`; it allows a write to `src/` and to `gtt-domain/proposals/`, and a read of a governed file. [PROPUESTA]
  - The freeze regime holds: a write under `gtt-domain/context/` is allowed before `gtt-domain/.frozen` exists and denied after. [PROPUESTA]
  - An edit inside a `@GTTGuard`-protected symbol is denied and one outside it is allowed; an edit of unknown extent on such a file is denied. [PROPUESTA]
  - An event without `toolCall`, a malformed event and an unknown tool all exit 0 with no output. [PROPUESTA]
  - `.agents/rules/gtt.md` is short and contains no section copied from `AGENTS.md`. [HUMANO: Solution Designer, 2026-10-05]
  - "Short" is measured as under 12,000 characters, the lowest per-file limit any source reports for an Antigravity rule. [PROPUESTA]
  - Every acceptance check that passed for the six existing ADEs before this Story still passes, with no change other than the four assertions that enumerate ADE ids. [PROPUESTA]
  - No document states or implies that Antigravity's real-time block is verified. [HUMANO: Solution Designer, 2026-10-05]
  - `bash .gtt/scripts/gtt-maintain.sh` passes. [PROPUESTA]
- **Tests:**
  - `.gtt/tests/bootstrap-acceptance.py`: a new `antigravity` function covering every criterion above, positive and negative.
  - `.gtt/tests/bootstrap-acceptance.py`: `any_ade_alone` extended with `antigravity`; the id lists at lines 246, 258 and 300 updated.
  - `bash .gtt/scripts/gtt-validate.sh` and `bash .gtt/scripts/gtt-maintain.sh`.
- **Sources:** gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md; https://antigravity.google/docs/hooks; https://antigravity.google/docs/rules
- **Governed by:** None
- **Design Approved:**
- **Dependencies:** None
- **Notes:** The overlay is built from Antigravity's documented contract. Documentation is not evidence of support; nothing here is to be reported as verified.

##### STORY-002 — Verify the Antigravity hook in the CLI

- **Status:** Undesigned
- **Priority:** High
- **Description:**
  - Practical verification of the hook is a requirement of the implementation, not an optional follow-up. Documentation and community reports are not evidence of verified support. [HUMANO: Solution Designer, 2026-10-05]
  - This Story observes the shipped overlay inside the Antigravity CLI and records what actually happens. [PROPUESTA]
- **Scope:**
  - In a disposable project with the overlay installed, run the Antigravity CLI and record: the working directory the hook runs in; the real payload the hook receives for each of the four matched tools; what Antigravity does when the hook answers `deny` and exits 2, and when it answers `deny` and exits 0; whether a denied tool call is in fact not executed. [HUMANO: Solution Designer, 2026-10-05]
  - Record whether `AGENTS.md` reaches the agent in full, by asking it to quote the last non-negotiable rule. [HUMANO: Solution Designer, 2026-10-05]
  - Record the result in `.gtt/docs/evidence.md` with the Antigravity version, the date and who ran it. [PROPUESTA]
  - If the observed payload, working directory or exit-code behaviour differs from what STORY-001 assumed, correct the `antigravity` format, the hook command and their tests in this Story. [PROPUESTA]
- **Out of Scope:**
  - The IDE and the desktop app: STORY-003. [PROPUESTA]
  - Changing `enforcement` in the registry: that is a separate governed change, and only when every surface is verified. [PROPUESTA]
  - Bypassing any Antigravity trust, approval or permission control in order to make the hook run. [PROPUESTA]
- **Acceptance Criteria:**
  - `.gtt/docs/evidence.md` states, for the CLI, each of the five observations above as observed, with version, date and who ran it — or states that it could not be observed and why. [PROPUESTA]
  - Whatever the result, no document claims more than what was observed. [HUMANO: Solution Designer, 2026-10-05]
  - If the format or the hook command was corrected, the acceptance tests use the observed payload and pass. [PROPUESTA]
  - `bash .gtt/scripts/gtt-maintain.sh` passes. [PROPUESTA]
- **Tests:**
  - The recorded CLI run itself (manual; it needs Antigravity installed and cannot run in the acceptance suite).
  - `.gtt/tests/bootstrap-acceptance.py`, re-run after any correction.
- **Sources:** gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md
- **Governed by:** None
- **Design Approved:**
- **Dependencies:** STORY-001
- **Notes:** Needs a machine with the Antigravity CLI. A human runs it, or supervises an agent that does.

##### STORY-003 — Verify the Antigravity hook in the IDE and the desktop app

- **Status:** Undesigned
- **Priority:** Medium
- **Description:**
  - The same verification as STORY-002 for the Antigravity IDE and, if it applies, the desktop app. Hook behaviour proven in the CLI is never extended to the other surfaces by assumption. [HUMANO: Solution Designer, 2026-10-05]
- **Scope:**
  - For the IDE, and for the desktop app if it applies: record whether the `PreToolUse` hook is invoked at all, and if it is, the same observations as STORY-002. [HUMANO: Solution Designer, 2026-10-05]
  - Record whether `AGENTS.md` reaches the agent in full on each surface. [PROPUESTA]
  - Record the result per surface in `.gtt/docs/evidence.md` and in the Antigravity section of `.gtt/docs/docs.md`, with version, date and who ran it. [PROPUESTA]
- **Out of Scope:**
  - Making the hook work on a surface where Antigravity does not run it. [PROPUESTA]
  - Changing `enforcement` in the registry. [PROPUESTA]
- **Acceptance Criteria:**
  - For each surface, `.gtt/docs/evidence.md` says one of: hook observed to block; hook observed not to be invoked; not tested, and why. [PROPUESTA]
  - The Antigravity section of `.gtt/docs/docs.md` and both READMEs say, per surface, exactly what was observed. [PROPUESTA]
  - `bash .gtt/scripts/gtt-maintain.sh` passes. [PROPUESTA]
- **Tests:**
  - The recorded IDE and desktop runs themselves (manual).
- **Sources:** gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md
- **Governed by:** None
- **Design Approved:**
- **Dependencies:** STORY-002
- **Notes:** "Hook not invoked on this surface" is a valid closing result: the Story verifies, it does not promise a block.

---

## Orden y cierre

| Paso | Qué | Quién |
|---|---|---|
| 1 | Aprobar cada Story por separado | Solution Designer |
| 2 | Escribir en `gtt-domain/backlog.md` las aprobadas, como `Ready` | agente, tras cada aprobación |
| 3 | Implementar STORY-001 | agente |
| 4 | `bash gtt-domain/proposals/apply-AGENTS-antigravity.sh` | Solution Designer |
| 5 | STORY-002, luego STORY-003 | humano con Antigravity instalado |

El Epic queda `Completed` solo con las tres Stories `Done` o `Cancelled`. Propongo además no
anunciar el soporte de Antigravity en una versión del Bootstrap hasta que STORY-002 esté
cerrada. [PROPUESTA]
