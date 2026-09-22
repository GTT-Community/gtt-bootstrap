---
inclusion: fileMatch
fileMatchPattern: 'src/**/*'
---

# Protected artifacts (GTTGuard)

Mirror of `AGENTS.md` → *Protected artifacts (GTTGuard)* for Kiro. Keep
both in sync, or delete this file if you do not use GTTGuard.

Before editing a file, check whether it (or a class/method inside it)
carries a `@GTTGuard` / `[GTTGuard]` / `// @GTTGuard` / `# @GTTGuard`
marker, or is listed with `protection: HUMAN_APPROVAL` in
`gtt/protection/registry.yaml`. If so, do not edit it directly — draft a
proposal instead (`gtt/CHANGE-REQUEST.md`-style flow, form 5 in the
`gtt-propose-change` procedure described in `AGENTS.md`).

**No real-time block exists on Kiro.** `gtt/protection/registry.yaml` is
dynamic content that `.kiro/permissions.yaml` cannot evaluate the way it
does a fixed path, the same gap that already exists for the two-regime
`gtt/context/`/`gtt/adr/` condition. `gtt/scripts/gtt-check-protection.sh`
in CI is the actual enforcement — treat this instruction as binding anyway.

Unrelated to `gtt/context/`/`gtt/adr/`: GTTGuard protects L3 code a
developer opted into protecting, not governed architecture. Once the
Solution Designer approves a protected-artifact change in conversation,
apply it directly and re-sync the registry — no ADR, no promotion script.
