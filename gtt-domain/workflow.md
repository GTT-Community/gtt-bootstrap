# Workflow

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Human-owned. The ADE reads this file and never edits it. A missing value uses its default.

```gtt-workflow
commits: on-request          # on-request (default) | allowed | never
convention: none             # none (default) | conventional | custom: <path to the project's rule>
branches-tags: on-request    # on-request (default) | never
review-files: 10             # review threshold, changed files (informs, never blocks)
review-lines: 500            # review threshold, changed lines (informs, never blocks)
```

- `commits: on-request` — the ADE commits only when you ask for it in the conversation.
- `commits: allowed` — the ADE may commit finished work, with ordinary messages in the declared convention.
- `commits: never` — the hook denies the agent's `git commit`, `git tag` and `git push`.
- `branches-tags: never` — the hook denies creating branches and tags.
- `convention: conventional` — observation notes, and never blocks, a commit subject that is not a Conventional Commit.
- Without this file, or without the block, the defaults apply and nothing special happens.
