# gtt-domain/pending/ — what is waiting for you

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

One small file per thing you must attend. Normally this folder is empty.

| File | What it is | What you do |
|---|---|---|
| `ASK-NNN.md` | a **question**: a decision only you can take (an account, a key, money, a legal matter, a product matter, a governed file) | answer it |
| `DEC-NNN.md` | a **decision** the agent took that changes scope, time, cost, security or the design | say «ok», or what to change |

```text
@gtt · Needs you (1)
14 Manual billing with an invoice in v1? → I recommend 1 · blocks STORY-066
Answer here, in the file or with gtt answer
```

Answer in the chat («14: 1», «ok to all»), in the file after `Answer:`, or with `gtt answer 14 1` (`gtt answer ok` for every decision).
The agent applies your answer where it belongs, cites it there and marks the event; the next session deletes what is marked.
An unanswered question keeps its recommended option; an unanswered decision stands «without objection» after 7 days.

Only GTT writes here (`gtt-pending.sh`): an agent cannot edit these files or run `gtt answer`. Keys never go in an answer; use `.env.local`.
Rules and details: `.gtt/docs/agents/operations.md` → *Pending events*, and `.gtt/contract/pending.json`.
