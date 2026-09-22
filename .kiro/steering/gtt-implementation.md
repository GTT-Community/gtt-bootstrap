---
inclusion: fileMatch
fileMatchPattern: 'src/**/*'
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Implementation work (L3)

Mirror of `.claude/rules/implementation.md` for Kiro. Keep both in sync, or
delete the one for the tool you do not use.

Implementation code is freely editable, but it must stay aligned with the
governed context.

Before changing module boundaries, public interfaces, or the shape of a layer,
read `gtt/context/stack.md` — sections 2 and 5 define the component map and the
dependency rules. If the change does not fit, stop and write a proposal.

Stay inside the existing folder structure and paradigm. Do not add abstraction
layers or patterns that are not already present.

If code contradicts `gtt/context/stack.md`, report it as a context conflict.
Do not assume the code is right.
