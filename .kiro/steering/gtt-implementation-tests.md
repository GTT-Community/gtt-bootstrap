---
inclusion: fileMatch
fileMatchPattern: 'tests/**/*'
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Implementation work (L3)

Mirror of `.claude/rules/implementation.md` for Kiro. Keep both in sync, or
delete the one for the tool you do not use.

Implementation code is freely editable, but it must stay aligned with the
governed context.

Before changing module boundaries, public interfaces, or the shape of a layer,
read `gtt-domain/context/stack.md` — sections 2 and 5 define the component map and the
dependency rules. If the change does not fit, stop and write a proposal.

Implement only against the written Story in `gtt-domain/backlog.md`: it must
be `Ready` or `In Progress` (designed and approved). An `Undesigned` Story is
not implementable. If something not written in the Story is needed, stop and
update the Story first through a proposal, then continue.

Read what the Story's `Governed by` points to before writing code. When its
tests pass and its acceptance criteria hold, close it in the backlog:
`Status: Done` and `Closed: <date> — <commit or PR> — <tests passed>`, from
what actually happened.

Stay inside the existing folder structure and paradigm. Do not add abstraction
layers or patterns that are not already present.

If code contradicts `gtt-domain/context/stack.md`, report it as a context conflict.
Do not assume the code is right.
