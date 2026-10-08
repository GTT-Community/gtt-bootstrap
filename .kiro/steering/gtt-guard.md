---
inclusion: always
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Protected artifacts (GTTGuard)

Mirror of `AGENTS.md` → *Protected artifacts (GTTGuard)* for Kiro. Keep
both in sync, or delete this file if you do not use GTTGuard.

Before editing a file, check whether it (or a class/method inside it)
carries a `@GTTGuard` / `[GTTGuard]` / `// @GTTGuard` / `# @GTTGuard`
marker, or is listed with `protection: HUMAN_APPROVAL` in
`.gtt/protection/registry.yaml`. If so, do not edit it directly — draft a
proposal instead (`gtt-domain/change-request.md`-style flow, form 5 in the
`gtt-propose-change` procedure described in `AGENTS.md`).

**The real-time block on Kiro is unverified.** `.kiro/hooks/gtt-protect.json`
runs GTT's protection engine before a tool call, and that engine knows
`.gtt/protection/registry.yaml`; nobody has proven it inside Kiro. Kiro reads
no permission rules from the repository. `.gtt/scripts/gtt-check-protection.sh`
in CI is the enforcement that holds — treat this instruction as binding anyway.

Unrelated to `gtt-domain/context/`/`gtt-domain/adr/`: GTTGuard protects L3 code a
developer opted into protecting, not governed architecture. Once the
Solution Designer approves a protected-artifact change in conversation,
apply it directly and re-sync the registry — no ADR, no promotion script.
