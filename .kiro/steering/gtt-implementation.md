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
read `gtt-domain/context/stack.md` — sections 2 and 5 define the component map and the
dependency rules. If the change does not fit, that is a governance change, not an implementation detail: write a proposal.

The implementation is yours: write, refactor, test and commit without asking
for approval. `gtt-domain/backlog.md` is your working plan - create, split,
rewrite and close Stories as the work needs; nobody approves a Story. When one
is finished, close it: `Status: Done` and `Closed: <date> — <commit or PR> —
<tests passed>`, from what actually happened. An Epic is different: its goal
and scope are the human's decision.

After a change that could touch a boundary of the design, run
`bash .gtt/scripts/gtt-observe.sh observe`. What it prints is an observation,
not an order to stop: say it in one line and continue. Only a line marked STOP
interrupts the affected operation.

Stay inside the existing folder structure and paradigm. Do not add abstraction
layers or patterns that are not already present.

If code contradicts `gtt-domain/context/stack.md`, report it as a context conflict.
Do not assume the code is right.
