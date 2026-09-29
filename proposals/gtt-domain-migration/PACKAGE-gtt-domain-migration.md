# ADR-004 migration package

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Status: staged, not a decision. Prepared by an agent; the migration is run only by the Solution Designer.
Approval of this package is not ratification of ADR-004: ratification is the `yes` answered inside the
ratification script the orchestrator calls.

## What it does

Moves the scaffold from the ADR-003 layout to the ADR-004 layout — `.gtt/` (Engine, with GTT's own
documentation in `.gtt/docs/`) and `gtt-domain/` (`context/`, `adr/`, `proposals/`, `backlog.md`,
`change-request.md`, `session.md`, `.frozen`) — and ratifies ADR-004 in the same guarded operation.

Run from the project root, after committing the current tree (the orchestrator refuses a dirty tree, exactly
like the ADR-003 one):

```bash
bash proposals/apply-gtt-domain-migration.sh
```

It preflights, takes a verified backup, lets you `plan`/`view`, then `apply`. The migration moves the files
(`git mv`), rewrites path references and relative links, applies the patches, installs the new protection
hook and the v2 scaffold manifest, re-registers artifact identity (same ids, new paths), and then calls the
ratification script, which shows the ADR and the exact diff of the six L0 files and asks
`view/yes/no`. Answering `no`, any failure, or an interruption restores the backup. After `yes` the hashes are
verified again, ADR-004 is stamped Accepted, the consumed ADR draft is retired from the identity manifest, the
derived state is regenerated, and every validation, the manifest check, the old-reference search, the `.frozen`
hash and the protection-hook smoke test must pass. It never freezes, commits or pushes.

## Contents

| Path | Role |
|---|---|
| `migrate.py` | the engine: `preflight`, `plan`, `apply`, `oldrefs`, `verify` (derived from the ADR-003 engine) |
| `overlay/claude-hooks/protect-l0.py` | the protection hook for the new paths (staged here because `.claude/hooks/` is denied to agents) |
| `overlay/manifest.yaml` | `.gtt/scaffold/manifest.yaml`, layout version 2 |
| `overlay.json` | which files are replaced wholesale, each with the hash of the file it replaces |
| `patches.json` | the code and prose edits a path rewrite cannot make (exact / block / regex / layout-tree) |
| `rehearsal-harness/` | the rehearsal, interruption and hook tests used to validate this package |
| `CLEANUP-gtt-domain-migration.md` | what to delete and which identities to retire afterwards |
| `PROVENANCE.txt`, `SHA256SUMS` | origin and hashes of every file |

The orchestrator is `proposals/apply-gtt-domain-migration.sh`; the ratification script is
`proposals/apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh`.

## Differences from the ADR-003 engine

- New path maps (`.gtt/`, `gtt-domain/`) and an unqualified-name rewrite with a strict word boundary, so a
  host project's own `src/context/` or `docs/` is never rewritten.
- The overlay mechanism gained `base_path` (the manifest is replaced at its new path but verified against the
  file at its old path); the two-step README rename, the `.gitignore` and manifest copy steps are gone.
- The old-reference search knows both new directories, treats unqualified domain names as errors unless the
  text is a member list of the new directories, and also reports stale wording of the old layout ("Project
  Governance", a bare `gtt/`, "four layers") as STALE.
- Preflight requires that neither `.gtt/` nor `gtt-domain/` exists yet, that every file under `gtt/` has a
  destination, and rejects CRLF scripts as before.
- Verification uses layout version 2 and `.gtt/index/artifacts.json`.
- The orchestrator additionally proves that `gtt-check-stack.sh` sees `gtt-domain/.frozen` (a check that says
  "not frozen yet" would pass vacuously) and smoke-tests the hook on the new paths.
- Fixed on the way: `gtt_guard.py` looked for ADR sources in a directory that had moved, and the identity
  scan would have registered the derived `gtt-domain/session.md` as an artifact.
