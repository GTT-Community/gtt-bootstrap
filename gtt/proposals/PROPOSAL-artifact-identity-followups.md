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

## 3. Decision points

- Commit `gtt/index/technical-index.json` (current) vs. gitignore it. Committed
  means every Markdown edit needs a `gtt-index.sh` run or `gtt-check-integrity.sh`
  fails (same trade-off as `registry.yaml`).
- Known finding, untouched: the TOC in `README-GTT.es.md` links to
  `#instalación-manual` / `#instalación-asistida-por-agente`; the headings are
  numbered (`2. Instalación manual`), so the anchors are `#2-instalación-manual` etc.
