---
paths:
  - "src/**/*"
  - "tests/**/*"
  - "lib/**/*"
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Implementation work (L3)

You are editing implementation code. It is freely editable, but it must stay
aligned with the governed context.

Before changing module boundaries, public interfaces, or the shape of a layer,
read `gtt-domain/context/stack.md` — sections 2 and 5 define the component map and the
dependency rules. Confirm the change fits. If it does not, stop and use the
`gtt-propose-change` skill.

Implement only against the written Story in `gtt-domain/backlog.md`. The
Story must be `Ready` or `In Progress` — designed and approved — before you
write code for it; an `Undesigned` Story is not implementable. Do not fill a
gap from the chat, from memory, or from your own reading of a source: if
something that is not written in the Story turns out to be needed, stop and
update the Story first (`gtt-propose-change`, form 6), then continue.

Read what the Story's `Governed by` points to before writing code. When the
Story's tests pass and its acceptance criteria hold, close it in the
backlog: `Status: Done` and `Closed: <date> — <commit or PR> — <tests
passed>`, from what actually happened.

Stay inside the existing folder structure and the existing paradigm. Do not add
abstraction layers, dependency-injection frameworks, or new patterns that are
not already present in the codebase.

If you find code that contradicts `gtt-domain/context/stack.md` or
`gtt-domain/context/architecture.md`, report it as a context conflict. Do not assume
the code is right.
