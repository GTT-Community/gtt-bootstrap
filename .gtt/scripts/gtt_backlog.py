#!/usr/bin/env python3
"""GTT - Story readiness engine for gtt-domain/backlog.md.

The deterministic half of the "Story Ready" rule (AGENTS.md -> Backlog governance): a Story may be
Ready, In Progress or Done only if its design is WRITTEN in the backlog and approved by a human, so
that the next session - or the next person - implements against the document and never against a
conversation.

  check   [backlog.md]   fail when a Ready / In Progress / Done Story is not a complete definition
  summary [backlog.md]   one line: how many Stories are Undesigned, and which

A Story Ready definition is:

  Description, Scope, Out of Scope, Acceptance Criteria
                     non-empty, and EVERY item carries its origin:
                       [FUENTE: ref]   the statement comes from a source (id[:loc] or a path[:line])
                       [HUMANO]        the human decided it (optionally [HUMANO: who, date])
                       [PROPUESTA]     the agent proposed it; the Story's approval is what accepts it
  Tests              non-empty: the tests that close the Story
  Sources            non-empty: the sources the design was derived from, or `None`
  Governed by        the governed decisions that apply (ADR ids, context sections), or `None`;
                     a reference, never a copy - an ADR it cites must exist
  Design Approved    who approved the written design and when (a YYYY-MM-DD date)

and it carries no [VACIO] or [CONFLICTO]: a Story with an undecided point is not designed yet.

Closure is evidence too. A Done Story carries `Closed`: the date (YYYY-MM-DD) and what closed it
(commit or PR, tests passed). An Epic is Completed only when every one of its Stories is Done or
Cancelled.

This makes no judgment about whether a criterion is good, a source says what the tag claims, or the
approval really happened - those stay with the human and with the gtt-audit skill.

Exit 0 = ok (warnings allowed), 1 = violation, 2 = cannot determine.
"""

import glob
import os
import re
import sys

DEFAULT = "gtt-domain/backlog.md"
GATED = ("Ready", "In Progress", "Done")
TRACED = ("Description", "Scope", "Out of Scope", "Acceptance Criteria")
REQUIRED = TRACED + ("Tests", "Sources", "Governed by", "Design Approved")

EPIC = re.compile(r"^### (EPIC-\d+)\b(.*)$")
EPIC_STATUS = re.compile(r"^\*\*Status:\*\*\s*(.*?)\s*$")
STORY = re.compile(r"^##### (STORY-\d+)\b(.*)$")
FIELD = re.compile(r"^- \*\*([^*:]+):\*\*\s*(.*)$")
ITEM = re.compile(r"^\s+[-*] (.*)$")
PLACEHOLDER = re.compile(r"<[^<>]*>")
ORIGIN = re.compile(r"\[FUENTE:\s*[^\]\s][^\]]*\]|\[HUMANO(?::[^\]]*)?\]|\[PROPUESTA(?::[^\]]*)?\]")
UNDECIDED = re.compile(r"\[VAC[ÍI]O(?::[^\]]*)?\]|\[CONFLICTO(?::[^\]]*)?\]")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
ADR = re.compile(r"\bADR-\d+\b")
EMPTY = {"", "-", "tbd", "todo", "pending", "pendiente"}
SEPARATORS = " -—–,;:."


def blank(text):
    """True when the text says nothing: empty, a template placeholder, or a to-do stub."""
    return PLACEHOLDER.sub("", text).strip(SEPARATORS).lower() in EMPTY


def parse(path):
    """(stories, epics). Story: id, line, status, epic, fields {name: [items]}. Epic: id, line,
    status. Template examples are skipped."""
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().replace("\r\n", "\n").split("\n")
    stories, epics, story, field, epic = [], [], None, None, None
    for number, line in enumerate(lines, 1):
        head = STORY.match(line)
        if head:
            story = None
            if not PLACEHOLDER.search(line):                 # a template example is not a real Story
                story = {"id": head.group(1), "line": number, "status": "", "fields": {},
                         "epic": epic["id"] if epic else None}
                stories.append(story)
            field = None
            continue
        epic_head = EPIC.match(line)
        if epic_head:
            story = field = epic = None
            if not PLACEHOLDER.search(line):
                epic = {"id": epic_head.group(1), "line": number, "status": ""}
                epics.append(epic)
            continue
        if line.startswith("#") or line.startswith("---"):
            if not line.startswith("####"):                  # `#### Stories` stays inside its Epic
                epic = None
            story = field = None
            continue
        if story is None:
            status = EPIC_STATUS.match(line)
            if epic is not None and not epic["status"] and status:
                epic["status"] = status.group(1)
            continue
        top = FIELD.match(line)
        if top:
            field = top.group(1).strip()
            story["fields"][field] = [top.group(2)] if top.group(2).strip() else []
            if field == "Status":
                story["status"] = top.group(2).strip()
            continue
        if field is None or not line.strip():
            continue
        item = ITEM.match(line)
        indent = len(line) - len(line.lstrip())
        items = story["fields"][field]
        if item and indent <= 3:                             # a first-level item of the field
            items.append(item.group(1))
        elif items:                                          # continuation or nested detail
            items[-1] += " " + line.strip()
        else:
            items.append(line.strip())
    return stories, epics


def findings(story, adr_dir):
    fields, out = story["fields"], []
    for name in REQUIRED:
        items = [i for i in fields.get(name, []) if not blank(i)]
        if not items:
            out.append(f"`{name}` is missing or empty")
            continue
        if name in TRACED:
            untraced = [i for i in items if not ORIGIN.search(i)]
            if untraced:
                out.append(f"`{name}` has {len(untraced)} item(s) without an origin "
                           f"([FUENTE: ref], [HUMANO] or [PROPUESTA]): \"{untraced[0][:70]}\"")
    for name, items in fields.items():
        if any(UNDECIDED.search(i) for i in items):
            out.append(f"`{name}` carries a [VACIO] or [CONFLICTO]: an undecided point is not a design")
    approved = " ".join(fields.get("Design Approved", []))
    if not blank(approved) and not DATE.search(approved):
        out.append("`Design Approved` must name who approved and a YYYY-MM-DD date")
    for adr in sorted(set(ADR.findall(" ".join(fields.get("Governed by", []))))):
        if not glob.glob(os.path.join(adr_dir, adr + "*.md")):
            out.append(f"`Governed by` cites {adr}, which does not exist in {adr_dir}/")
    if story["status"] == "Done":
        closed = " ".join(fields.get("Closed", []))
        if blank(closed):
            out.append("`Closed` is missing or empty: a Done Story records when and with what it was closed")
        elif not DATE.search(closed) or blank(DATE.sub("", closed)):
            out.append("`Closed` must carry a YYYY-MM-DD date and the evidence (commit or PR, tests passed)")
    return out


def load(path):
    try:
        return parse(path)
    except OSError as error:
        print(f"gtt-backlog: cannot read {path}: {error}", file=sys.stderr)
        return None


def cmd_check(path):
    loaded = load(path)
    if loaded is None:
        return 2
    stories, epics = loaded
    adr_dir = os.path.join(os.path.dirname(path) or ".", "adr")
    failed = 0
    for story in stories:
        if story["status"] not in GATED:
            continue
        problems = findings(story, adr_dir)
        if problems:
            failed += 1
            print(f"gtt-check-backlog: FAILED - {story['id']} is `{story['status']}` but is not a Story Ready "
                  f"definition ({path}:{story['line']}):", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
    for epic in epics:
        own = [s for s in stories if s["epic"] == epic["id"]]
        pending = [s["id"] for s in own if s["status"] not in ("Done", "Cancelled")]
        if epic["status"] == "Completed" and pending:
            failed += 1
            print(f"gtt-check-backlog: FAILED - {epic['id']} is `Completed` but {len(pending)} of its Story(ies) "
                  f"are neither Done nor Cancelled ({path}:{epic['line']}): {', '.join(pending)}", file=sys.stderr)
        elif own and not pending and epic["status"] not in ("Completed", "Cancelled"):
            print(f"gtt-check-backlog: WARNING - every Story of {epic['id']} is Done or Cancelled but the Epic is "
                  f"`{epic['status']}`: mark it Completed if it is")
    undesigned = [s["id"] for s in stories if s["status"] == "Undesigned"]
    if undesigned:
        print(f"gtt-check-backlog: WARNING - {len(undesigned)} Story(ies) not designed yet (title only; "
              f"design and approve before implementing): {', '.join(undesigned)}")
    return 1 if failed else 0


def cmd_summary(path):
    loaded = load(path)
    if loaded is None:
        return 2
    stories = loaded[0]
    undesigned = [s["id"] for s in stories if s["status"] == "Undesigned"]
    print(f"{len(undesigned)} of {len(stories)} Story(ies) not designed" + (f": {', '.join(undesigned)}" if undesigned else ""))
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] not in ("check", "summary"):
        print("usage: gtt_backlog.py check|summary [backlog.md]", file=sys.stderr)
        return 2
    path = argv[2] if len(argv) > 2 else DEFAULT
    return cmd_check(path) if argv[1] == "check" else cmd_summary(path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
