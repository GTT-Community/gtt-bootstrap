# Staged files awaiting manual placement

`.claude/hooks/**` and `.claude/settings.json` are in this project's own
`permissions.deny` and `protect-l0.py` machinery list — unconditionally, no
regime exception — so the agent implementing GTTGuard could not write to
them directly. This is the system working as designed (see `AGENTS.md` →
*Non-negotiable rules*: never bypass the protection mechanism by writing
through an alternate path). The two files below are staged here instead.

## What to do

1. **`gtt/proposals/protect-guard.py`** → move to `.claude/hooks/protect-guard.py`
   (new file, the GTTGuard PreToolUse hook).
2. **`gtt/proposals/settings.json.new`** → replace `.claude/settings.json`
   with this content (adds one `hooks` entry registering `protect-guard.py`
   alongside the existing `protect-l0.py`; the `permissions.deny` list is
   unchanged). This also changes both hook `command` strings from a bare
   `python3 ...` to `python3 -c '' >/dev/null 2>&1 && python3 ... || python ...`:
   on Windows, `command -v python3` can succeed against a WindowsApps stub
   that only prints a Microsoft Store redirect and exits non-zero, which
   silently disabled `protect-l0.py` too (verified on this machine - see
   `gtt/GTT-COMPLETION.md`). The new form actually invokes the interpreter
   before trusting it, and falls back to `python`.

From the project root:

```bash
mv gtt/proposals/protect-guard.py .claude/hooks/protect-guard.py
cp gtt/proposals/settings.json.new .claude/settings.json
```

Then delete both staged files here (`rm gtt/proposals/protect-guard.py
gtt/proposals/settings.json.new gtt/proposals/STAGED-FILES-README.md`).

This is not the Human Promotion Boundary (no ADR, no `apply-*.sh` script) —
these are ordinary product files (a hook script and its registration),
just relocated here because the destination happens to be permission-denied
to the agent. No governed decision is being promoted.
