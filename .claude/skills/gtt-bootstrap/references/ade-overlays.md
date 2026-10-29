# Step 0 - Detect candidate ADEs, let the human choose, and resolve the overlays

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

Part of the `gtt-bootstrap` skill ([SKILL.md](../SKILL.md), step 0). Follow it in full before step 1.

Do this before touching the filesystem, and before step 1. Three separate
questions: which ADEs look present (detection), which ones the human wants GTT
to govern (participation), and which one is the Primary.

GTT Bootstrap ships a portable core — `AGENTS.md` and `SOURCE-BRIEF.*` (if a
source document exists) at the project root, plus the governed domain
(`gtt-domain/`: `context/`, `adr/`, `proposals/`, `backlog.md`, `change-request.md`) and
the Engine (`.gtt/`, including its documentation in `.gtt/docs/`, defined by
`.gtt/scaffold/manifest.yaml`) — plus one adapter per
supported ADE. The source repository carries every adapter — it is a
catalog, not a package to install whole. A target project receives the
portable core plus the overlay of every ADE the human chose to have
participate, never the whole catalog. Workspace hygiene: the Engine and its
documentation stay in `.gtt/`, and the governed domain in `gtt-domain/`;
never mix them, and report (never merge) a collision with a `.gtt/` or
`gtt-domain/` the project already has.

What each ADE's adapter contains (a project with several participating ADEs
has the union of their rows; the registry itself is the `overlays:` section of
the manifest, read through `gtt-ade.sh list`):

| Host ADE | Adapter | `.claude/` | `.kiro/` | `AGENTS.md` | `.github/instructions/gtt.instructions.md` |
|---|---|---|---|---|---|
| Claude Code | Claude | YES | NO | YES | NO |
| Kiro | Kiro | NO | YES | YES | NO |
| Codex | Portable/AGENTS | NO | NO | YES | NO |
| GitHub Copilot | Copilot | NO | NO | YES | YES |
| Other supported ADE | Explicit adapter only | only if mapped | only if mapped | per support | per support |
| Unknown ADE | Portable/unknown | NO | NO | do not guess | NO |

**Detection is not participation.** From the project root, run
`bash <catalog>/.gtt/scripts/gtt-ade.sh detect --from <catalog>`. It lists every ADE in the
registry with the signals it found (an overlay path, an ADE binary on the PATH). Those
are *candidates* — nothing more: not installed, not authorized, not governed, not
participating. Never detect from the underlying model: a Claude model is not Claude Code,
a GPT model is not Codex, and an API alone is neither. The ADE executing this bootstrap
is self-evident to that ADE and is a sensible suggestion — still only a suggestion.

**Ask, do not assume.** Show the candidates (and the registry ADEs that were not
detected: the human may want one that is not installed yet) in this shape:

> Detected these possible ADEs.
>
> - Claude Code (signals: `.claude/`, binary `claude`)
> - Kiro (signals: `.kiro/`)
>
> Which of them should participate in this project? GTT installs and governs each
> one's integration. And which one is the Primary ADE — the principal environment of
> your workflow? (The Primary ADE has no extra authority.)

Silence is not an answer. Exactly one Primary, and it must be one of the participating
ADEs. If the human names no ADE, or the only ADE has no row above and none has been
explicitly mapped for it, install the portable core only, do not invent an adapter,
and report plainly that no native adapter exists (it falls back to `AGENTS.md` where it
can read that natively).

**The Primary ADE holds no authority.** It identifies the principal environment of the
workflow and nothing else. It does not outrank, approve or arbitrate for another ADE, and
no ADE — the Primary included — ratifies anything: every ADE prepares, the human decides.
Do not describe or behave as if there were an ADE hierarchy. `AGENTS.md`, `.claude/`,
`.kiro/`, `.github/instructions/`, `.codex/` and any ADE's memory or session history are integration
surfaces, never governance authority. Several ADEs may run at once (three terminals in one
editor), which is why every participating ADE gets its overlay.

**Install.** Once the portable core and the Engine are in place, with the choice made,
dry-run first, show the plan (a CONFLICT means an overlay file already exists — it is never
overwritten or merged; stop and report it), then apply:

```bash
bash <catalog>/.gtt/scripts/gtt-ade.sh install --from <catalog> --participating claude,codex --primary claude
bash <catalog>/.gtt/scripts/gtt-ade.sh install --from <catalog> --participating claude,codex --primary claude --apply
```

That copies only the participating overlays, writes `.gtt/ade.json` (participating, Primary,
the ADEs declined as excluded, and a ledger of the files it installed so a later clean removes
exactly those and never the host project's own ADE configuration), and validates the result,
rolling everything back on failure. Do not copy overlay files by hand and never hand-edit
`.gtt/ade.json`. Only Claude Code has a real-time write block; say so for every other
participating ADE (governed by instructions plus the CI gate, not hard-blocked).

**Re-running bootstrap.** Read the state first (`gtt-ade.sh state`). If `.gtt/ade.json`
exists: never drop a participating ADE, never re-add one recorded as excluded unless the
human says so (`--reinclude <ade>`), never change the Primary unless the human says so
(`gtt-ade.sh set-primary`). A project that predates `.gtt/ade.json` (an overlay present, no
state) is migrated with `gtt-ade.sh adopt` (dry run first): it records the existing ADE as
both Primary and participating only when exactly one overlay is present and intact; where
several are present, ask the human and pass `--participating a,b --primary a`. Never infer
an authorization the state does not show.

Once resolved, note the detected ADEs, the participating ADEs, the Primary, the files this
will install, and the ADEs this will exclude — this becomes part of the report after
step 6. Then continue to step 1.
