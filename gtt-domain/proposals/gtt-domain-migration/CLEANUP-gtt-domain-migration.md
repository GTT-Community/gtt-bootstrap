# Cleanup after the ADR-004 migration

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Status: staged instruction for the Solution Designer. It is not a decision and nothing here is run by an
agent. Do it **after** the migration and the ratification of ADR-004 succeeded and you committed the result.

## 1. Delete the staged package

Everything below sits in `gtt-domain/proposals/` once the migration has run; none of it is needed afterwards
(ADR-004 itself now lives in `gtt-domain/adr/`, and the six context files were promoted from their staged
drafts):

- `apply-gtt-domain-migration.sh` — the orchestrator
- `apply-ADR-004-gtt-domain-and-dot-gtt-engine.sh` — the ratification script
- `context-architecture-adr-004.md`, `context-constraints-adr-004.md`, `context-glossary-adr-004.md`,
  `context-principles-adr-004.md`, `context-solution-vision-adr-004.md`, `context-stack-adr-004.md`
- `PROPOSAL-gtt-domain-and-dot-gtt-engine.md`
- `gtt-domain-migration/` — this package, including `PACKAGE-gtt-domain-migration.md` and this file
- `migration-engine-adr-003/` — the persisted ADR-003 engine and its rehearsal harness (historical, not
  product; nothing in `.gtt/` depends on it)

Both directories are deleted, not kept as history. Do not delete anything until the migration result is
**committed**, and until then keep the evidence needed to audit or undo it: the orchestrator's backup archive
(`backup.tar`, in the temporary directory the script printed as "Backup kept at"), the package's `SHA256SUMS`
and `PROVENANCE.txt`, and the rehearsal results. Once the commit exists, git history is the record.

## 2. Retire the identities of the deleted Markdown files

Staged Markdown files were registered in the identity manifest (`.gtt/index/artifacts.json`) while they were
staged. After deleting the files, retire their identities with the official mechanism (dry-run first, then
`--apply`), otherwise `gtt-index.sh` refuses to run on a manifest that lists files missing on disk:

```bash
bash .gtt/scripts/gtt-reconcile.sh           # dry-run: shows what would be retired
bash .gtt/scripts/gtt-reconcile.sh --apply \
  --retire PROP-CONTEXT-ARCHITECTURE-ADR-004 \
  --retire PROP-CONTEXT-CONSTRAINTS-ADR-004 \
  --retire PROP-CONTEXT-GLOSSARY-ADR-004 \
  --retire PROP-CONTEXT-PRINCIPLES-ADR-004 \
  --retire PROP-CONTEXT-SOLUTION-VISION-ADR-004 \
  --retire PROP-CONTEXT-STACK-ADR-004 \
  --retire PROP-PROPOSAL-GTT-DOMAIN-AND-DOT-GTT-ENGINE \
  --retire PROP-PACKAGE-GTT-DOMAIN-MIGRATION \
  --retire PROP-CLEANUP-GTT-DOMAIN-MIGRATION
bash .gtt/scripts/gtt-index.sh
bash .gtt/scripts/gtt-validate.sh
```

(`PROP-ADR-DRAFT-GTT-DOMAIN-AND-DOT-GTT-ENGINE` was already retired by the orchestrator, because the
ratification consumes that draft. `migration-engine-adr-003/` needs no retirement: it contains no Markdown,
so it has no identity.) Retired ids are never reused for a different file at the same path — the
reason the staged context drafts carry the `-adr-004` suffix.

## 3. Then

Regenerate the session state (`bash .gtt/scripts/gtt-status.sh`), review `git status`, and commit. The freeze
marker was moved byte for byte to `gtt-domain/.frozen`; `gtt-freeze.sh` is not part of this migration and must
not be run.
