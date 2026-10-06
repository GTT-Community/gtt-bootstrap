#!/usr/bin/env python3
"""GTT - backlog engine for gtt-domain/backlog.md.

The backlog has two kinds of entry and they are not governed alike (AGENTS.md -> Backlog):

  Epic    intent and scope. Governed: the human approves it. An Epic that is Planned, In Progress or
          Completed carries its Goal and `Approved` (who, YYYY-MM-DD); until then it stays Proposed.
  Story   the operating plan of whoever does the work. NOT governed: the ADE creates, splits,
          rewrites, implements and closes Stories on its own, with no approval.

  check   [backlog.md]   the structural rules below
  summary [backlog.md]   one line: Stories by status, and the Epics still waiting for approval
  json    [backlog.md]   the same, structured

What fails (structure that tooling and people rely on, never a judgment):

  * an Epic that is Planned, In Progress or Completed without its Goal or its `Approved`
  * an Epic marked Completed while one of its Stories is neither Done nor Cancelled

What is only reported, and never stops anything:

  * a Done Story without `Closed` (the date and what closed it: commit or PR, tests passed)
  * Stories being worked under an Epic that is still Proposed
  * an Epic whose Stories are all closed but is not marked Completed

Whether a Story is well written, or whether an approval really happened, is not checked here.
What the work actually does to the governed design is watched by observation
(.gtt/scripts/gtt-observe.sh), not by approving Stories in advance.

Exit 0 = ok (warnings allowed), 1 = violation, 2 = cannot determine.
"""

import json
import re
import sys

DEFAULT = "gtt-domain/backlog.md"
APPROVED_STATES = ("Planned", "In Progress", "Completed")
ACTIVE = ("In Progress", "Done")
LEGACY = {"Proposed": "Planned", "Undesigned": "Planned", "Ready": "Planned"}   # earlier vocabulary, still read

EPIC = re.compile(r"^### (EPIC-\d+)\b(.*)$")
EPIC_FIELD = re.compile(r"^\*\*([^*:]+):\*\*\s*(.*?)\s*$")
STORY = re.compile(r"^##### (STORY-\d+)\b(.*)$")
FIELD = re.compile(r"^- \*\*([^*:]+):\*\*\s*(.*)$")
PLACEHOLDER = re.compile(r"<[^<>]*>")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
EMPTY = {"", "-", "tbd", "todo", "pending", "pendiente", "none"}
SEPARATORS = " -—–,;:."


def blank(text):
    """True when the text says nothing: empty, a template placeholder, or a to-do stub."""
    return PLACEHOLDER.sub("", text).strip(SEPARATORS).lower() in EMPTY


def parse(path):
    """(stories, epics). Story: id, line, status, epic, fields. Epic: id, line, fields. Template
    examples (a heading that still holds a <placeholder>) are skipped."""
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().replace("\r\n", "\n").split("\n")
    stories, epics, story, epic, field = [], [], None, None, None
    for number, line in enumerate(lines, 1):
        head = STORY.match(line)
        if head:
            story = None
            if not PLACEHOLDER.search(line):
                story = {"id": head.group(1), "line": number, "status": "", "fields": {},
                         "epic": epic["id"] if epic else None}
                stories.append(story)
            field = None
            continue
        epic_head = EPIC.match(line)
        if epic_head:
            story = field = epic = None
            if not PLACEHOLDER.search(line):
                epic = {"id": epic_head.group(1), "line": number, "fields": {}}
                epics.append(epic)
            continue
        if line.startswith("#") or line.startswith("---"):
            if not line.startswith("####"):                  # `#### Stories` stays inside its Epic
                epic = None
            story = field = None
            continue
        if story is None:
            own = EPIC_FIELD.match(line)
            if epic is not None and own and own.group(1).strip() not in epic["fields"]:
                epic["fields"][own.group(1).strip()] = own.group(2)
            continue
        top = FIELD.match(line)
        if top:
            field = top.group(1).strip()
            story["fields"][field] = top.group(2).strip()
            if field == "Status":
                story["status"] = top.group(2).strip()
        elif field and line.strip():
            story["fields"][field] = (story["fields"][field] + " " + line.strip()).strip()
    for item in epics:
        item["status"] = item["fields"].get("Status", "")
    return stories, epics


def load(path):
    try:
        return parse(path)
    except OSError as error:
        print(f"gtt-backlog: cannot read {path}: {error}", file=sys.stderr)
        return None


def normal(status):
    return LEGACY.get(status, status)


def cmd_check(path):
    loaded = load(path)
    if loaded is None:
        return 2
    stories, epics = loaded
    failed = 0
    for epic in epics:
        own = [s for s in stories if s["epic"] == epic["id"]]
        pending = [s["id"] for s in own if s["status"] not in ("Done", "Cancelled")]
        if epic["status"] in APPROVED_STATES:
            approved = epic["fields"].get("Approved", "")
            missing = [name for name, bad in (("Goal", blank(epic["fields"].get("Goal", ""))),
                                              ("Approved", blank(approved) or not DATE.search(approved)
                                               or blank(DATE.sub("", approved)))) if bad]
            if missing:
                failed += 1
                print(f"gtt-check-backlog: FAILED - {epic['id']} is `{epic['status']}` without "
                      f"{' or '.join('`' + m + '`' for m in missing)} ({path}:{epic['line']}). An Epic is intent and "
                      "scope: the human approves it (`**Approved:** who - YYYY-MM-DD`); until then it stays `Proposed`.",
                      file=sys.stderr)
        if epic["status"] == "Completed" and pending:
            failed += 1
            print(f"gtt-check-backlog: FAILED - {epic['id']} is `Completed` but {len(pending)} of its Story(ies) "
                  f"are neither Done nor Cancelled ({path}:{epic['line']}): {', '.join(pending)}", file=sys.stderr)
        elif own and not pending and epic["status"] not in ("Completed", "Cancelled"):
            print(f"gtt-check-backlog: NOTE - every Story of {epic['id']} is Done or Cancelled but the Epic is "
                  f"`{epic['status']}`: mark it Completed if it is")
        working = [s["id"] for s in own if s["status"] in ACTIVE]
        if epic["status"] == "Proposed" and working:
            print(f"gtt-check-backlog: NOTE - {epic['id']} is still `Proposed` (nobody approved its scope) while "
                  f"{', '.join(working)} is being worked")
    for story in stories:
        closed = story["fields"].get("Closed", "")
        if story["status"] == "Done" and (blank(closed) or not DATE.search(closed) or blank(DATE.sub("", closed))):
            print(f"gtt-check-backlog: NOTE - {story['id']} is `Done` without `Closed` (a YYYY-MM-DD date and what "
                  f"closed it: commit or PR, tests passed) ({path}:{story['line']})")
    return 1 if failed else 0


def facts(path):
    loaded = load(path)
    if loaded is None:
        return None
    stories, epics = loaded
    by_status = {}
    for story in stories:
        by_status.setdefault(normal(story["status"]) or "no status", []).append(story["id"])
    return {"stories": len(stories), "by_status": by_status,
            "epics": len(epics), "epics_awaiting_approval": [e["id"] for e in epics if e["status"] == "Proposed"]}


def cmd_summary(path):
    data = facts(path)
    if data is None:
        return 2
    order = ("In Progress", "Blocked", "Planned", "Done", "Cancelled", "no status")
    parts = [f"{len(data['by_status'][s])} {s}" for s in order if s in data["by_status"]]
    waiting = data["epics_awaiting_approval"]
    print(f"{data['stories']} Story(ies)" + (": " + ", ".join(parts) if parts else "")
          + f"; {data['epics']} Epic(s)" + (f", awaiting approval: {', '.join(waiting)}" if waiting else ""))
    return 0


def cmd_json(path):
    data = facts(path)
    if data is None:
        return 2
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def main(argv):
    commands = {"check": cmd_check, "summary": cmd_summary, "json": cmd_json}
    if len(argv) < 2 or argv[1] not in commands:
        print("usage: gtt_backlog.py check|summary|json [backlog.md]", file=sys.stderr)
        return 2
    return commands[argv[1]](argv[2] if len(argv) > 2 else DEFAULT)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
