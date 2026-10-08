---
inclusion: always
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Speaking for GTT

When a message is GTT's — a question the method needs answered, a
confirmation or choice (ADE participation, Method Plan, Confirmation A or B),
the Initial Design Questionnaire, a proposal, an observation, a
finding, a request for authorization, a report — open it with:

```text
@gtt · <what this is>
```

For example `@gtt · Initial Design Questionnaire`, `@gtt · Method Plan`,
`@gtt · Authorization required`, `@gtt · Report`.

Ordinary work that GTT did not raise — explaining code, answering a question,
implementing a Story — carries no marker.

The marker says who is speaking. It is never a decision, an approval or
evidence. Full rule: `AGENTS.md` → *Working without unnecessary interruption*;
the policy is data in `.gtt/contract/profiles.json` → `developer_experience.dialogue`.

## Git and workflow

Git history belongs to the human. Follow `gtt-domain/workflow.md`; without it the defaults apply: commit only when the user asks, no commit convention, no branch or tag you were not asked for.
- Never invent a workflow: no checkpoint, session or agent commits, no prefixes, branches, tags, squashes, rebases or pushes the project does not define or the user did not ask for.
- Do not propose commit plans, commit splits, messages or branches unless asked. Uncommitted work is a fact `gtt review` reports, not a question.
- A convention found in the project's documents is a finding, not a rule: report it once and point to `gtt-domain/workflow.md`, which only the human edits.
- Proposing is not executing: releases, tags, destructive operations and workflow changes wait for an explicit request.
- A GTT checkpoint regenerates `gtt-domain/session.md`. It is never a commit.

**What counts as truth, highest first:** governed context → ADRs → approved Epics → the change request → proposals → `gtt-domain/session.md` (derived) → this conversation. A lower layer never overrides a higher one, and nothing said in a conversation, yours or another ADE's, is project authority. Your ADE's resume restores the conversation; `gtt review` restores the project.
