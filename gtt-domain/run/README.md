# gtt-domain/run/ — things for the human to run

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

When the human has to execute something that changes state or takes two or more commands, GTT hands over
one line and one command instead of a sequence:

```text
@gtt · To run
Starts the local environment and loads test data (changes your environment; does not touch the code)
gtt run 3
```

| File | What it is |
|---|---|
| `RUN-NNN-<slug>.md` | the **plan**: what it does, why, what it changes, and a `gtt-run` block of `check:`, `step:` and `next:` lines. The agent writes it |
| `RUN-NNN-<slug>.sh` | the **script**, generated from the plan by `gtt-run.sh generate` and sealed with the plan's sha256. Never edit it: a hand-edited script is refused |
| `log.jsonl` | one line per execution: id, time, duration, exit code, who |
| `done/` | plans and scripts already run successfully; the last 20 are kept |

`gtt run` lists what is pending; `gtt run <n>` shows the steps, asks once if it changes something, runs it and
archives it. Only the human runs it: the protection hook denies `gtt run <n>` and `gtt-run.sh execute` to agents.
Rules and details: `.gtt/docs/agents/operations.md` → *Simple execution*, and `.gtt/contract/run.json`.
