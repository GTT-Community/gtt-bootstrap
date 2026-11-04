#!/usr/bin/env python3
"""GTT - pending events (UserPromptSubmit hook).

On every message of the human it does three small things and nothing else:

  1. keeps the human's last messages, locally (.gtt/local/prompts.jsonl), so that an answer the agent records
     from the chat can be checked against their exact words (gtt-pending.sh record --quote);
  2. opens a new turn, so that the notice (gtt-pending.sh notice --report) is shown once per turn at most;
  3. tells the agent, in a few lines, what waits in gtt-domain/pending/: an answer to apply and mark, the events it
     may record an answer to, and - when something blocks and 24 h have passed - that the notice is overdue.

It says nothing when the folder is empty, and it does not repeat itself inside a session unless what is pending
changed or the 24 h reminder is due. The logic lives in .gtt/scripts/gtt_pending.py and the texts in
.gtt/contract/pending.json; this file carries none of its own.

Exit 0 always. A broken hook must never block a prompt from being submitted.
"""

import hashlib
import json
import os
import sys

SCRIPTS = os.path.join(".gtt", "scripts")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    if not os.path.isfile(os.path.join(".gtt", "contract", "pending.json")):
        return 0
    try:
        sys.path.insert(0, SCRIPTS)
        sys.dont_write_bytecode = True
        import gtt_pending as engine

        c = engine.contract()
        session = str(event.get("session_id") or "unknown")
        prompt = str(event.get("prompt") or "")
        if prompt:
            engine.store_prompt(prompt, c)
        state = engine.begin_turn(session, prompt, c)

        s = engine.summary(c)
        open_events = s["asks"] + s["decisions"]
        if not open_events and not s["to_apply"]:
            return 0
        apply_lines = [f"{r['id']} is answered («{r['answer'][:60]}»): apply it where it belongs, cite it there, then "
                       f"`bash .gtt/scripts/gtt-pending.sh done {r['number']} --in <where> --apply`." for r in s["to_apply"]]
        wait_lines = []
        if open_events:
            names = ", ".join(r["id"] for r in open_events)
            wait_lines.append(f"Waiting for the human: {names}. If their message answers one, write it down with "
                              f"`bash .gtt/scripts/gtt-pending.sh record <n> <answer> --quote \"<their exact words>\" --apply` "
                              f"(`record all ok` for «ok» to every decision); never write the answer yourself. If you have not shown them yet, show the open questions "
                              f"to the human in the chat as one batch: run `bash .gtt/scripts/gtt-pending.sh show` and show its output. The files are the "
                              f"silent record: do not announce them.")
        due = engine.reminder_due(c, state)
        # What waits for the human is said once per session unless it changes; an answer to apply is said every turn.
        digest = hashlib.sha256("\n".join(wait_lines).encode("utf-8")).hexdigest()[:12]
        seen = state.setdefault("sessions", {})
        if seen.get(session) == digest and not due:
            wait_lines = []
        seen[session] = digest
        for old in list(seen)[:-5]:
            seen.pop(old)
        lines = apply_lines + wait_lines
        if due:
            lines.append("The human has not seen the pending block for 24 h and something blocks: end your report with "
                         "`bash .gtt/scripts/gtt-pending.sh show`, shown in the chat.")
        if not lines:
            engine.save_state(c, state)
            return 0
        engine.save_state(c, state)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": "GTT pending: " + " ".join(lines)}}))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
