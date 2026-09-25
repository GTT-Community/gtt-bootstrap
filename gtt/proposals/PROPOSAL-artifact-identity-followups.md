# Proposal — artifact identity: items that need the Solution Designer

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Status: **Draft — not a decision.** Context: the artifact identity /
technical index / session-memory capability was implemented under
`gtt/scripts/`, `gtt/index/`, `gtt/docs/DOCS.md`, `gtt/INDEX.md`, and
`.claude/skills/gtt-retrieve/`. Two pieces touch paths an agent may not
write (the root `AGENTS.md`, and the Claude Code settings/hooks machinery),
so they are staged here for you to move into place.

## 1. Root `AGENTS.md` — add after *Session continuity*

```markdown
## Artifact identity and technical index

Every governed Markdown artifact has a stable identity (`gtt/index/artifacts.json`)
independent of its path: a move or rename is reconciled, never treated as delete
+ create. Reference an artifact as `[[ID]]` (e.g. `[[ADR-007]]`) so the reference
survives moves. `gtt/index/technical-index.json` is a DERIVED accelerator — for
locating concepts and sections (`gtt/scripts/gtt-query.sh`) — never a source of
truth, never evidence in itself; the Markdown it points to is authoritative.
Regenerate it with `gtt/scripts/gtt-index.sh`; never hand-edit it. After any move
run `gtt/scripts/gtt-reconcile.sh` (dry-run first). `gtt/scripts/gtt-check-integrity.sh`
(part of `gtt-validate.sh`) fails on unreconciled moves, duplicate logical identity,
broken or old-path references, unresolved `[[ID]]`, and a stale index. Agents
operate through these scripts and MUST NOT own an artifact's identity or authority,
and never rewrite frozen `gtt/context/` or `gtt/adr/` files to fix a reference.
```

## 2. SessionStart hook — warm start for Claude Code

New file `session-start.py` in the Claude hooks directory, registered in the
Claude settings file. It runs `gtt/scripts/gtt-status.sh` at session start and
surfaces `gtt/SESSION.md` as context, labelled operational-only. Advisory,
never blocks.

```python
#!/usr/bin/env python3
"""SessionStart: regenerate and surface gtt/SESSION.md (derived, non-authoritative)."""
import json, subprocess, sys

try:
    subprocess.run(["bash", "gtt/scripts/gtt-status.sh"], capture_output=True, timeout=30)
    text = open("gtt/SESSION.md", encoding="utf-8").read()
except Exception:
    sys.exit(0)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "GTT session state (derived, operational only - NOT authority, "
                         "evidence, or a decision record):\n" + text}}))
```

Settings entry, under `"hooks"`:

```json
"SessionStart": [
  { "hooks": [ { "type": "command",
      "command": "python3 -c '' >/dev/null 2>&1 && python3 .claude/hooks/session-start.py || python .claude/hooks/session-start.py" } ] }
]
```

## 2b. Update — SessionStart adapter (supersedes the hook in §2)

Status remains **Draft — not a decision.** The §2 hook was found fragile
(silent `except`, `python3 X || python X` fallback). Replacement, staged:
`gtt/scripts/gtt-session-context.sh` (ADE-independent service entry point),
`gtt/scripts/gtt-run-python.sh` (single Python resolution for hooks), and the
thin adapter `gtt/proposals/claude-adapter/session-start.py`. Promote with
`bash gtt/proposals/apply-claude-session-start-adapter.sh`, which changes only
the `SessionStart` registration. Separate, not included: the `UserPromptSubmit`
(`notify-change-request.py`) and `PostToolUse` (`detect-drift.py`) hooks call bare
`python3` and fail on Windows with the Store stub; they are unrelated to Session
Memory and were left untouched.

## 2c. Multi-ADE Session Memory adapters

Status remains **Draft — not a decision.** Working spec:
`gtt/docs/SESSION-ADAPTER-CONTRACT.md`. Declarations:
`gtt/session-adapters/*.json`. Staged adapters (Codex, Copilot, Kiro):
`gtt/proposals/session-adapters/`. Promotion, by a human, per adapter:
`bash gtt/proposals/apply-session-adapters.sh <codex|copilot|kiro>` (installs
files, flips the declaration; does not ratify anything).

**What needs the governed path** (`Proposal → Epic/Story → ADR → ratification`)
before any of this is more than a draft:

- `AGENTS.md`: the adapter matrix and *Adapters vs. portable core* ("Codex takes
  no adapter file beyond AGENTS.md" is contradicted by `.codex/`).
- `gtt/scripts/gtt-check-adapter.sh`: its Codex row, and its detection list
  (`.github/hooks/`, `.codex/`).
- The `gtt-bootstrap` skill step 0 and `README-GTT.md` ADE-adapter table.
- The `Compatibility matrix` earlier in `gtt/docs/DOCS.md` (Copilot hook row is
  likely stale).

> **Superseded by `PROPOSAL-gtt-v2-1-backlog-epic-stories.md`.** The Epic/Story
> draft below reuses the same ids for a narrower scope; do not apply both. Kept
> only as history.

**Backlog (form 4) — proposed, not defined.** `gtt/backlog.md` has no real
Epics/Stories, so per `AGENTS.md` → *Backlog governance* these are drafts only
and must stay `Status: Proposed` until you accept them:

```markdown
### EPIC-001 — GTT v2.1 Session Memory across ADEs
**Status:** Proposed
**Goal:** Session continuity for every supported ADE through one ADE-agnostic
service, with adapters that are checked, honestly declared, and never authority.

##### STORY-001 — Adapter contract and conformance check
- **Status:** Proposed  - **Priority:** High
- **Acceptance Criteria:** contract documented; `gtt-check-session-adapter.sh`
  passes for every declared adapter and fails on each mutation of the contract.
##### STORY-002 — Claude Code adapter (SessionStart)
- **Status:** Proposed  - **Priority:** High
##### STORY-003 — Codex adapter
- **Status:** Proposed  - **Priority:** Medium
- **Dependencies:** STORY-001. **Notes:** runtime verification needs the user to
  trust the project and approve the hook.
##### STORY-004 — GitHub Copilot adapter
- **Status:** Proposed  - **Priority:** Medium
- **Notes:** verification requires an interactive Copilot CLI session; resume is
  documented as unsupported.
##### STORY-005 — Kiro adapter
- **Status:** Proposed  - **Priority:** Low
- **Notes:** Kiro not installed here; its docs conflict on `agentSpawn` stdout.
```

No ADR has been drafted: `gtt-adr` is for decisions the Solution Designer has
already approved.

## 2d. `AGENTS.md` — manual change required (stale reference)

Status remains **Draft — not a decision.** `gtt-status.sh` no longer detects or
reports an installed adapter (the Session Memory chain names no ADE), so the
*Session continuity* paragraph is stale. `AGENTS.md` is outside the agent's write
zone; the Solution Designer applies this by hand.

In `## Session continuity`, replace exactly:

```text
deterministic snapshot (freeze state, backlog focus, pending proposals,
protected-artifact count, installed adapter) derived from repository
artifacts, never from any ADE's private conversation memory — the same
```

with:

```text
deterministic snapshot (freeze state, backlog focus, pending proposals,
protected-artifact count, artifact identity and index state) derived from
repository artifacts, never from any ADE's private conversation memory — the same
```

The rest of that paragraph (naming the ADEs to explain ADE-independence) is
documentation and stays. After editing, run `gtt/scripts/gtt-index.sh` —
`AGENTS.md` is an indexed artifact, so the index goes stale until it is rebuilt.

## 3. Decision points

- Commit `gtt/index/technical-index.json` (current) vs. gitignore it. Committed
  means every Markdown edit needs a `gtt-index.sh` run or `gtt-check-integrity.sh`
  fails (same trade-off as `registry.yaml`).
- Known finding, untouched: the TOC in `README-GTT.es.md` links to
  `#instalación-manual` / `#instalación-asistida-por-agente`; the headings are
  numbered (`2. Instalación manual`), so the anchors are `#2-instalación-manual` etc.
