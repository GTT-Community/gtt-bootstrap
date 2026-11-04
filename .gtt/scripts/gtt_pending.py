#!/usr/bin/env python3
"""GTT - pending events: one small file per thing the human must attend, only in gtt-domain/pending/.

The folder holds what is pending and nothing else. A question (ASK) is a decision only the human can take;
a decision (DEC) is something the agent decided that changes scope, time, cost, security or the design.
The human answers; the agent applies the answer where it belongs, cites it there and marks the event;
the next session deletes what is marked. Only this engine writes the folder.

  gtt_pending.py ask --type T --header "topic" --question "...?" --why W --option "A | what I do" --option "B | what I do" [--option "C | ..."]
                     --recommended N [--blocks STORY-NNN] [--apply]       an agent may run this
  gtt_pending.py decide --affects X --title T --what W --why W --where P [--apply]
                                                                         an agent may run this
  gtt_pending.py list [--json] [--all]                                   what is pending
  gtt_pending.py record REF|all ANSWER --quote "words" [--apply]         an agent records an answer given in the chat,
                                                                         with the human's exact words (checked)
  gtt_pending.py answer REF ANSWER | ok --confirmed-by-human             the human's act, never an agent's
  gtt_pending.py done REF --in WHERE [--apply]                           mark an answered event as applied
  gtt_pending.py clean [--apply]                                         delete what is marked and the decisions
                                                                         nobody objected to for 7 days
  gtt_pending.py check [--json]                                          the rules PEN-01 to PEN-07
  gtt_pending.py notice [--report|--due|--session] [--json]              the block that tells the human

REF is `14`, `ASK-14` or `DEC-015`. All texts, limits and labels are in .gtt/contract/pending.json.
Nothing here creates a commit. Exit 0 = ok, 1 = violation or refused, 2 = cannot run.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True

CONTRACT = ".gtt/contract/pending.json"
FILE_NAME = re.compile(r"^(ASK|DEC)-(\d+)\.md$")
HEADING = re.compile(r"^# (ASK|DEC)-(\d+) · (.+)$")
OPTION = re.compile(r"^(\d)\. (.+)$")
OK_WORD = re.compile(r"^\s*(?:ok|okay)\b", re.IGNORECASE)
WHERE_ID = re.compile(r"^(?:STORY|EPIC)-\d+$")


# ----------------------------------------------------------------------------- basics

def read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


def read_json(path):
    try:
        return json.loads(read(path) or "")
    except ValueError:
        return None


def write_atomic(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(tmp, path)


def contract():
    data = read_json(CONTRACT)
    if not isinstance(data, dict):
        print(f"gtt-pending: {CONTRACT} is missing or unreadable; this Bootstrap does not carry pending events.", file=sys.stderr)
        sys.exit(2)
    return data


def now_dt():
    stamp = os.environ.get("GTT_NOW")
    if stamp:
        try:
            return datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            pass
    return datetime.datetime.now(datetime.timezone.utc)


def today():
    return now_dt().strftime("%Y-%m-%d")


def stamp():
    return now_dt().strftime("%Y-%m-%dT%H:%M:%SZ")


def language():
    value = (read_json(".gtt/methodology.json") or {}).get("language")
    return value if value in ("en", "es") else "en"


def emit(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def one_line(text):
    return " ".join(str(text).split())


def folder(c):
    return c["locations"]["directory"]


def labels(c):
    return c["labels"][language()]


def messages(c):
    return c["message"][language()]


def label_map(c):
    """Every label of every language -> its key. A file written in one language is read in both."""
    out = {}
    for table in c["labels"].values():
        for key, text in table.items():
            out[text.lower()] = key
    return out


def type_id(value, table):
    low = one_line(value).lower()
    for row in table:
        if low in (row["id"], row["en"].lower(), row["es"].lower()):
            return row["id"]
    return None


def type_word(ident, table):
    for row in table:
        if row["id"] == ident:
            return row[language()]
    return ident


# ----------------------------------------------------------------------------- keys never go in an answer

def key_shaped(text, c):
    """The shape that made `text` look like a key, or None."""
    for shape in c["key_shapes"]:
        if re.search(shape, text or ""):
            return shape
    for token in re.findall(r"[A-Za-z0-9+_=-]{%d,}" % c["limits"].get("long_token", 40), text or ""):
        if re.search(r"\d", token) and re.search(r"[a-z]", token) and re.search(r"[A-Z]", token):
            return "long mixed token"
    return None


# ----------------------------------------------------------------------------- reading an event

def ref_number(ref):
    found = re.fullmatch(r"(?:ASK|DEC)?[- ]?0*(\d+)", str(ref).strip(), re.IGNORECASE)
    return int(found.group(1)) if found else None


def parse(path, c):
    """The event in `path`."""
    return parse_text(path, read(path) or "", c)


def parse_text(path, text, c):
    """The event in `text`. Never raises: what is wrong is listed in event['problems'] as (rule, message)."""
    lines = text.replace("\r\n", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    names = label_map(c)
    hints = {t["answer_hint"] for t in c["labels"].values()}
    ev = {"path": path.replace(os.sep, "/"), "name": os.path.basename(path), "kind": None, "number": None, "title": "",
          "fields": {}, "options": [], "notes": {}, "fixed": {}, "discuss": False, "recommended": None, "lines": lines, "answer": "", "answered": False,
          "attended": False, "mark": "", "answer_at": None, "problems": []}
    name = FILE_NAME.match(ev["name"])
    head = HEADING.match(lines[0]) if lines else None
    if not name:
        ev["problems"].append(("PEN-06", f"`{ev['name']}` is not ASK-NNN.md or DEC-NNN.md"))
    if head:
        ev["kind"], ev["number"], ev["title"] = head.group(1), int(head.group(2)), head.group(3).strip()
        if name and (name.group(1), int(name.group(2))) != (ev["kind"], ev["number"]):
            ev["problems"].append(("PEN-06", f"the heading `{ev['kind']}-{ev['number']:03d}` does not match the file name"))
    else:
        ev["problems"].append(("PEN-06", "the first line is not `# ASK-NNN · text` or `# DEC-NNN · text`"))
        if name:
            ev["kind"], ev["number"] = name.group(1), int(name.group(2))
    answer_label = None
    fixed_texts = {}
    for table in c["labels"].values():
        for kind in ("other", "chat"):
            fixed_texts[table[kind].lower()] = kind
    last_option = None
    for index, line in enumerate(lines[1:], 1):
        if line.startswith("   ") and last_option is not None:      # the description of the option above
            ev["notes"][last_option] = line.strip()
            continue
        last_option = None
        found = re.match(r"^(?P<label>[^:]{2,30}):\s*(?P<rest>.*)$", line)
        key = names.get(found.group("label").strip().lower()) if found else None
        if key == "answer":
            answer_label = index
            break
        option = OPTION.match(line)
        if option and option.group(2).strip().lower() in fixed_texts:
            ev["fixed"][int(option.group(1))] = fixed_texts[option.group(2).strip().lower()]
            continue
        if option:
            last_option = int(option.group(1))
            body, recommended = option.group(2), False
            for word in {t["recommended"] for t in c["labels"].values()}:
                if body.endswith(f" ({word})"):
                    body, recommended = body[: -len(word) - 3], True
            ev["options"].append((int(option.group(1)), body))
            if recommended:
                ev["recommended"] = (ev["recommended"] or []) + [int(option.group(1))]
            continue
        if not found or not key:
            continue
        if key in ("type", "affects"):                 # the meta line: `Type: x · Blocks: y · Created: z`
            for part in line.split(" · "):
                sub = re.match(r"^([^:]{2,30}):\s*(.*)$", part.strip())
                subkey = names.get(sub.group(1).strip().lower()) if sub else None
                if subkey:
                    ev["fields"][subkey] = sub.group(2).strip()
        else:
            ev["fields"][key] = found.group("rest").strip()
    ev["engine_lines"] = lines[: answer_label + 1] if answer_label is not None else lines
    if answer_label is None:
        ev["problems"].append(("PEN-01", "there is no answer line"))
        return ev
    first = re.match(r"^[^:]+:\s*(.*)$", lines[answer_label]).group(1)
    tail, mark = [first], []
    for line in lines[answer_label + 1:]:
        found = re.match(r"^([^:]{2,30}):", line)
        if found and names.get(found.group(1).strip().lower()) == "attended":
            ev["attended"], ev["mark"] = True, line
            break
        tail.append(line)
    answer = " ".join(part.strip() for part in tail if part.strip())
    ev["answer"] = "" if answer in hints else answer
    ev["answered"] = bool(ev["answer"])
    chat = [n for n, k in ev["fixed"].items() if k == "chat"]
    if ev["answered"] and ev["kind"] == "ASK" and chat and option_chosen(ev) == chat[0] and len(ev["answer"]) <= 12:
        ev["answered"], ev["discuss"] = False, True      # «talk about it in the chat» is not an answer
        ev["answer"] = ""
    ev["answer_lines"] = [part for part in tail if part.strip()] if ev["answered"] else []
    return ev


def events(c):
    """[event] sorted by number, from the folder."""
    out = []
    try:
        names = sorted(os.listdir(folder(c)))
    except OSError:
        return out
    for name in names:
        if FILE_NAME.match(name):
            out.append(parse(os.path.join(folder(c), name), c))
    return sorted(out, key=lambda e: (e["number"] or 0, e["name"]))


def state_of(ev):
    return "attended" if ev["attended"] else ("answered" if ev["answered"] else "open")


def option_chosen(ev):
    found = re.match(r"^\s*(?:option|opci[oó]n)?\s*(\d)\b", ev["answer"], re.IGNORECASE)
    return int(found.group(1)) if found and ev["kind"] == "ASK" else None


def is_ok(ev):
    return ev["kind"] == "DEC" and bool(OK_WORD.match(ev["answer"]))


def created(ev):
    return ev["fields"].get("created") or ""


def row(ev, c):
    table = c["ask_types"] if ev["kind"] == "ASK" else c["dec_affects"]
    raw = ev["fields"].get("type") or ev["fields"].get("affects") or ""
    return {"id": f"{ev['kind']}-{ev['number']:03d}", "number": ev["number"], "kind": ev["kind"], "title": ev["title"],
            "class": type_id(raw, table) or raw, "created": created(ev), "state": state_of(ev), "answer": ev["answer"],
            "blocks": blocks_of(ev, c), "recommended": (ev["recommended"] or [None])[0], "options": [o[1] for o in ev["options"]], "notes": ev["notes"], "topic": ev["fields"].get("topic"), "discuss": ev["discuss"],
            "closing": [labels(c)["other"], labels(c)["chat"]],
            "path": ev["path"], "problems": [{"rule": r, "message": m} for r, m in ev["problems"]]}


def blocks_of(ev, c):
    value = ev["fields"].get("blocks", "")
    if not value or one_line(value).lower() in {t["nothing"].lower() for t in c["labels"].values()}:
        return None
    return one_line(value)


# ----------------------------------------------------------------------------- the rules

def where_exists(value):
    """Every comma-separated place exists: a path, a Story or Epic of the backlog, an ADR."""
    parts = [p.strip() for p in str(value).split(",") if p.strip()]
    if not parts:
        return False
    backlog = read("gtt-domain/backlog.md") or ""
    for part in parts:
        if os.path.exists(part):
            continue
        if WHERE_ID.match(part) and re.search(rf"^#+\s*{re.escape(part)}\b", backlog, re.MULTILINE):
            continue
        if re.match(r"^ADR-\d+$", part) and os.path.isdir("gtt-domain/adr") and \
                any(n.upper().startswith(part.upper()) for n in os.listdir("gtt-domain/adr")):
            continue
        return False
    return True


def review(ev, c, strict_where=True):
    """[(rule, level, message)] for one event."""
    out = [(r, "fail", m) for r, m in ev["problems"]]
    lim = c["limits"]
    engine = ev.get("engine_lines", [])
    max_lines = lim["ask_max_lines"] if ev.get("kind") == "ASK" else lim["max_lines"]
    if len(engine) > max_lines:
        out.append(("PEN-01", "fail", f"{len(engine)} lines; the limit is {max_lines}"))
    for number, line in enumerate(engine, 1):
        if len(line) > lim["max_chars"]:
            out.append(("PEN-01", "fail", f"line {number} has {len(line)} characters; the limit is {lim['max_chars']}"))
    for number, line in enumerate(ev.get("answer_lines", []), 1):
        if len(line) > lim["answer_chars"]:
            out.append(("PEN-01", "fail", f"the answer's line {number} has {len(line)} characters; the limit is {lim['answer_chars']}"))
    if not ev["kind"]:
        return out
    if not created(ev):
        out.append(("PEN-06", "fail", "there is no creation date"))
    if ev["kind"] == "ASK":
        if not ev["title"].endswith("?"):
            out.append(("PEN-02", "fail", "the question does not end in «?»"))
        count = len(ev["options"])
        if not lim["options"]["min"] <= count <= lim["options"]["max"]:
            out.append(("PEN-02", "fail", f"{count} options; a question has {lim['options']['min']} or {lim['options']['max']}"))
        if [n for n, _ in ev["options"]] != list(range(1, count + 1)):
            out.append(("PEN-02", "fail", "the options are not numbered 1, 2, 3 in order"))
        if len(ev["recommended"] or []) != 1:
            out.append(("PEN-02", "fail", "exactly one option must be recommended"))
        topic = ev["fields"].get("topic", "")
        if not topic or len(topic) > lim["header_chars"]:
            out.append(("PEN-02", "fail", f"a question needs a Topic of at most {lim['header_chars']} characters"))
        for n, _ in ev["options"]:
            if not ev["notes"].get(n):
                out.append(("PEN-02", "fail", f"option {n} has no description line (what you will do if it is chosen)"))
        if ev["fixed"] != {count + 1: "other", count + 2: "chat"}:
            out.append(("PEN-02", "fail", f"the two closing lines are missing: {count + 1}. something else and {count + 2}. talk about it in the chat"))
        raw = ev["fields"].get("type", "")
        if not type_id(raw, c["ask_types"]):
            kinds = ", ".join(t[language()] for t in c["ask_types"])
            out.append(("PEN-03", "fail", f"the type `{raw}` is not one of: {kinds}"))
        if not ev["fields"].get("why_matters"):
            out.append(("PEN-02", "fail", "there is no `why it matters` line"))
        if ev["answered"] and option_chosen(ev) and option_chosen(ev) > max([n for n, _ in ev["options"]] or [0]) + 2:
            out.append(("PEN-02", "fail", f"the answer chooses option {option_chosen(ev)}, which does not exist"))
    else:
        raw = ev["fields"].get("affects", "")
        if not type_id(raw, c["dec_affects"]):
            kinds = ", ".join(t[language()] for t in c["dec_affects"])
            out.append(("PEN-03", "fail", f"`Affects: {raw}` is not one of: {kinds}"))
        for key in ("decided", "reason", "where"):
            if not ev["fields"].get(key):
                out.append(("PEN-04", "fail", f"the decision has no `{c['labels']['en'][key]}` line"))
        if ev["fields"].get("where") and strict_where and not where_exists(ev["fields"]["where"]):
            out.append(("PEN-04", "fail", f"`{ev['fields']['where']}` does not exist"))
    shape = key_shaped(ev["answer"], c) if ev["answered"] else None
    if shape:
        out.append(("PEN-05", "fail", "the answer looks like a key; put keys in .env.local and answer where they are"))
    if ev["answered"] and not ev["attended"]:
        out.append(("PEN-07", "warn", "answered and not applied yet"))
    return out


def review_all(c):
    found, seen = [], {}
    for ev in events(c):
        entries = review(ev, c)
        if ev["number"] in seen:
            entries.append(("PEN-06", "fail", f"the number {ev['number']} is also used by {seen[ev['number']]}"))
        seen.setdefault(ev["number"], ev["name"])
        found.append((ev, entries))
    return found


# ----------------------------------------------------------------------------- writing an event

def next_number(c):
    last = 0
    try:
        last = int((read(c["locations"]["counter"]) or "0").strip() or 0)
    except ValueError:
        pass
    return max([last] + [e["number"] or 0 for e in events(c)]) + 1


def render_ask(number, a, c):
    t = labels(c)
    kind = type_word(a["type"], c["ask_types"])
    blocks = a.get("blocks") or t["nothing"]
    out = [f"# ASK-{number:03d} · {one_line(a['question'])}", "",
           f"{t['type']}: {kind} · {t['topic']}: {one_line(a['header'])} · {t['blocks']}: {blocks} · {t['created']}: {today()}",
           f"{t['why_matters']}: {one_line(a['why'])}"]
    for index, option in enumerate(a["options"], 1):
        title, _, note = option.partition(" | ")
        mark = f" ({t['recommended']})" if index == a["recommended"] else ""
        out += [f"{index}. {one_line(title)}{mark}", f"   {one_line(note)}"]
    count = len(a["options"])
    out += [f"{count + 1}. {t['other']}", f"{count + 2}. {t['chat']}"]
    out += [f"{t['until']}: {t['option_word']} {a['recommended']}.", "", f"{t['answer']}:"]
    return "\n".join(out) + "\n"


def render_dec(number, d, c):
    t = labels(c)
    out = [f"# DEC-{number:03d} · {one_line(d['title'])}", "",
           f"{t['affects']}: {type_word(d['affects'], c['dec_affects'])} · {t['created']}: {today()}",
           f"{t['decided']}: {one_line(d['what'])}", f"{t['reason']}: {one_line(d['why'])}",
           f"{t['where']}: {one_line(d['where'])}", "", f"{t['answer']}: {t['answer_hint']}"]
    return "\n".join(out) + "\n"


def create(text, number, c, apply):
    """Check what would be written; write it only with apply. Returns (ok, path)."""
    kind = "ASK" if text.startswith("# ASK") else "DEC"
    path = os.path.join(folder(c), f"{kind}-{number:03d}.md").replace(os.sep, "/")
    problems = [p for p in review(parse_text(path, text, c), c) if p[1] == "fail"]
    if problems:
        print(f"gtt-pending: the event does not meet the limits ({len(text.splitlines())} lines):", file=sys.stderr)
        for rule, _level, message in problems:
            print(f"  {rule}: {message}", file=sys.stderr)
        print("Shorten it, split it in two events, or put the detail in the code.", file=sys.stderr)
        return False, path
    if apply:
        write_atomic(path, text)
        write_atomic(c["locations"]["counter"], f"{number}\n")
    return True, path


def refuse_key(texts, c):
    for text in texts:
        if key_shaped(text, c):
            print("gtt-pending: that text looks like a key. Keys go in .env.local, never in an event.", file=sys.stderr)
            return True
    return False


def cmd_ask(args):
    c = contract()
    if not type_id(args.type, c["ask_types"]):
        kinds = ", ".join(f"{t['id']} ({t['es']})" for t in c["ask_types"])
        print(f"gtt-pending: `{args.type}` is not a question type ({kinds}). If none fits, the question is not the human's: settle it yourself.", file=sys.stderr)
        return 1
    options = args.option or []
    lim = c["limits"]["options"]
    if not args.header or len(args.header) > c["limits"]["header_chars"]:
        print(f"gtt-pending: --header is the topic in a few words (at most {c['limits']['header_chars']} characters), e.g. \"pdfkit (PDF)\".", file=sys.stderr)
        return 1
    if any(" | " not in o or not o.partition(" | ")[2].strip() for o in options):
        print("gtt-pending: each --option is \"short answer | what I will do if you choose it\".", file=sys.stderr)
        return 1
    kind_id = type_id(args.type, c["ask_types"])
    if kind_id in c["necessity"]["requires_blocks"] and not args.blocks:
        print(f"gtt-pending: a {kind_id} question must name the Story or Epic it blocks (--blocks STORY-NNN). If nothing is blocked, "
              "it is not necessary: settle it yourself with the recommended option and, if it changes scope, time, cost, security or the design, tell it as a decision.", file=sys.stderr)
        return 1
    open_asks = [e for e in events(c) if e["kind"] == "ASK" and not e["attended"] and not e["answered"]]
    if len(open_asks) >= c["limits"]["max_open_asks"]:
        print(f"gtt-pending: {len(open_asks)} questions are already open (the limit is {c['limits']['max_open_asks']}): the human answers those first.", file=sys.stderr)
        return 1
    if any(one_line(e["title"]).lower() == one_line(args.question).lower() for e in open_asks):
        print("gtt-pending: that question is already open.", file=sys.stderr)
        return 1
    if not lim["min"] <= len(options) <= lim["max"] or not 1 <= (args.recommended or 0) <= len(options):
        print(f"gtt-pending: a question has {lim['min']} or {lim['max']} options (--option) and one --recommended N.", file=sys.stderr)
        return 1
    if args.blocks and not WHERE_ID.match(args.blocks):
        print("gtt-pending: --blocks is a Story or Epic id (STORY-066).", file=sys.stderr)
        return 1
    if refuse_key([args.question, args.why, args.header, *options], c):
        return 1
    number = next_number(c)
    text = render_ask(number, {"type": type_id(args.type, c["ask_types"]), "question": args.question, "why": args.why,
                               "options": options, "recommended": args.recommended, "blocks": args.blocks, "header": args.header}, c)
    ok, path = create(text, number, c, args.apply)
    if not ok:
        return 1
    print(f"gtt-pending: {'created' if args.apply else 'dry run - would create'} {path}")
    if not args.apply:
        print("(nothing written; re-run with --apply)")
    return 0


def cmd_decide(args):
    c = contract()
    if not type_id(args.affects, c["dec_affects"]):
        kinds = ", ".join(f"{t['id']} ({t['es']})" for t in c["dec_affects"])
        print(f"gtt-pending: `{args.affects}` is not one of {kinds}. A decision that affects none of them is not shown: do not create it.", file=sys.stderr)
        return 1
    if not where_exists(args.where):
        print(f"gtt-pending: `{args.where}` does not exist; a decision says where it landed (a path, STORY-NNN or ADR-NNN that exists).", file=sys.stderr)
        return 1
    if refuse_key([args.title, args.what, args.why], c):
        return 1
    number = next_number(c)
    text = render_dec(number, {"affects": type_id(args.affects, c["dec_affects"]), "title": args.title, "what": args.what,
                               "why": args.why, "where": args.where}, c)
    ok, path = create(text, number, c, args.apply)
    if not ok:
        return 1
    print(f"gtt-pending: {'created' if args.apply else 'dry run - would create'} {path}")
    if not args.apply:
        print("(nothing written; re-run with --apply)")
    return 0


# ----------------------------------------------------------------------------- answering

def find(ref, c):
    number = ref_number(ref)
    if number is None:
        print(f"gtt-pending: `{ref}` is not an event (14, ASK-14, DEC-015).", file=sys.stderr)
        return None
    for ev in events(c):
        if ev["number"] == number:
            return ev
    print(f"gtt-pending: there is no pending event {number}.", file=sys.stderr)
    return None


def normalise(text):
    text = one_line(text).strip("«»\"'“”`").strip()
    return text.casefold()


def clean_answer(reply, ev, c):
    """(text, error) - the answer as it will be written."""
    text = one_line(reply)
    if not text:
        return None, "the answer is empty"
    if len(text) > c["limits"]["answer_chars"]:
        return None, f"the answer has {len(text)} characters; the limit is {c['limits']['answer_chars']}"
    if key_shaped(text, c):
        return None, "the answer looks like a key; put keys in .env.local and answer where they are"
    if ev["kind"] == "ASK":
        found = re.match(r"^\s*(?:option|opci[oó]n)?\s*(\d)\b", text, re.IGNORECASE)
        if found and not 1 <= int(found.group(1)) <= len(ev["options"]):
            return None, f"{ev['kind']}-{ev['number']:03d} has options 1 to {len(ev['options'])}, not {found.group(1)}"
    return text, None


def write_answer(ev, text, c, suffix=""):
    t = labels(c)
    lines = ev["engine_lines"][:-1] + [f"{t['answer']}: {text}{suffix}"]
    write_atomic(ev["path"], "\n".join(lines) + "\n")


def mark(ev, c, where):
    t = labels(c)
    what = f"{t['option']} {option_chosen(ev)}" if option_chosen(ev) else ("ok" if is_ok(ev) else t["answer"].lower())
    lines = [l for l in ev["lines"] if not re.match(r"^(Attended|Atendida):", l)]
    lines.append(f"{t['attended']}: {today()} · {what} · {t['landed']}: {one_line(where)}")
    write_atomic(ev["path"], "\n".join(lines) + "\n")


def settle(ev, c):
    """A decision answered `ok` needs nothing applied: it is marked at once."""
    ev = parse(ev["path"], c)
    if is_ok(ev) and not ev["attended"]:
        mark(ev, c, ev["fields"].get("where") or "-")


def recent_prompts(c):
    out = []
    for line in (read(c["locations"]["prompts"]) or "").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out[-c["retention"]["quote_window"]:]


def quote_is_theirs(quote, answer, ev_created, c):
    """True when `quote` is inside one of the human's last messages (sent since the event was created)
    and the answer is what the quote says."""
    q = normalise(quote)
    if not q:
        return False
    token = normalise(answer)
    first = token.split(" ")[0] if token else ""
    says = (re.search(rf"(?<!\w){re.escape(first)}(?!\w)", q) if (first.isdigit() or first in ("ok", "okay")) else token in q)
    if not says:
        return False
    for message in recent_prompts(c):
        body = normalise(message.get("text", ""))
        if ev_created and str(message.get("at", ""))[:10] < ev_created:
            continue
        if q == body or (len(q) >= 4 and q in body):
            return True
    return False


def cmd_record(args):
    """An agent writes down an answer the human gave in the chat. It needs their exact words."""
    c = contract()
    if args.ref.lower() == "all":
        targets = [e for e in events(c) if e["kind"] == "DEC" and not e["answered"]]
        if not OK_WORD.match(args.answer):
            print("gtt-pending: `all` takes only «ok».", file=sys.stderr)
            return 1
        if not targets:
            print("gtt-pending: no decision is waiting for an answer.", file=sys.stderr)
            return 1
    else:
        ev = find(args.ref, c)
        if not ev:
            return 1
        targets = [ev]
    done = []
    for ev in targets:
        if ev["answered"]:
            print(f"gtt-pending: {ev['kind']}-{ev['number']:03d} already has an answer; only the human changes it (gtt answer).", file=sys.stderr)
            return 1
        text, error = clean_answer(args.answer, ev, c)
        if error:
            print(f"gtt-pending: {error}.", file=sys.stderr)
            return 1
        if not quote_is_theirs(args.quote or "", text, created(ev), c):
            print("gtt-pending: that quote is not in the human's last messages, or it does not say that answer. "
                  "Nothing was recorded: ask them to answer with `gtt answer`, or in the file.", file=sys.stderr)
            return 1
        done.append((ev, text))
    for ev, text in done:
        quote = one_line(args.quote).strip("«»\"")
        if args.apply:
            write_answer(ev, text, c, f" (chat: «{quote[:60]}»)")
            settle(ev, c)
        print(f"gtt-pending: {'recorded' if args.apply else 'dry run - would record'} {ev['kind']}-{ev['number']:03d} <- {text}")
    if not args.apply:
        print("(nothing written; re-run with --apply)")
    return 0


def cmd_answer(args):
    """The human's act. The CLI and the hook keep an agent away from it; the flag keeps a script honest."""
    c = contract()
    if not args.confirmed_by_human:
        print("gtt-pending: answering is the human's act. An agent never runs it: use `record` with the human's words.", file=sys.stderr)
        return 1
    if args.reply is None and OK_WORD.match(args.ref or ""):
        targets = [e for e in events(c) if e["kind"] == "DEC" and not e["attended"]]
        if not targets:
            print("gtt-pending: no decision is pending.")
            return 0
        reply = "ok"
    else:
        if args.reply is None:
            print("gtt-pending: gtt answer <n> <answer>, or gtt answer ok for every decision.", file=sys.stderr)
            return 1
        ev = find(args.ref, c)
        if not ev:
            return 1
        targets, reply = [ev], args.reply
    for ev in targets:
        text, error = clean_answer(reply, ev, c)
        if error:
            print(f"gtt-pending: {ev['kind']}-{ev['number']:03d}: {error}.", file=sys.stderr)
            return 1
        write_answer(ev, text, c)
        settle(ev, c)
        print(f"{ev['kind']}-{ev['number']:03d} · {ev['title']}  <-  {text}")
    return 0


def cmd_done(args):
    c = contract()
    ev = find(args.ref, c)
    if not ev:
        return 1
    if not ev["answered"]:
        print(f"gtt-pending: {ev['kind']}-{ev['number']:03d} has no answer yet; there is nothing to mark.", file=sys.stderr)
        return 1
    if ev["attended"]:
        print(f"gtt-pending: {ev['kind']}-{ev['number']:03d} is already marked.")
        return 0
    if not where_exists(args.where):
        print(f"gtt-pending: `{args.where}` does not exist. Cite where the answer was applied: a path, STORY-NNN or ADR-NNN that exists.", file=sys.stderr)
        return 1
    if args.apply:
        mark(ev, c, args.where)
    print(f"gtt-pending: {'marked' if args.apply else 'dry run - would mark'} {ev['kind']}-{ev['number']:03d}; the next session deletes it.")
    if not args.apply:
        print("(nothing written; re-run with --apply)")
    return 0


# ----------------------------------------------------------------------------- clean, list, check

def days_old(ev):
    try:
        return (now_dt().date() - datetime.date.fromisoformat(created(ev))).days
    except ValueError:
        return 0


def cmd_clean(args):
    """Delete what is marked and the decisions nobody objected to. An answered event that is not marked stays."""
    c = contract()
    if args.apply:
        for ev in events(c):
            settle(ev, c)
    gone = []
    for ev in events(c):
        expired = ev["kind"] == "DEC" and not ev["answered"] and days_old(ev) >= c["retention"]["unanswered_decision_days"]
        if ev["attended"] or expired:
            gone.append(ev)
            if args.apply:
                os.remove(ev["path"])
    if args.json:
        emit({"schema": 1, "applied": bool(args.apply), "removed": [f"{e['kind']}-{e['number']:03d}" for e in gone]})
    elif gone:
        print(f"gtt-pending: {messages(c)['cleaned'].format(n=len(gone))}" + ("" if args.apply else " (dry run)"))
    return 0


def pending_rows(c, include_attended=False):
    rows = [row(e, c) for e in events(c)]
    return rows if include_attended else [r for r in rows if r["state"] != "attended"]


def cmd_list(args):
    c = contract()
    rows = pending_rows(c, args.all)
    if args.json:
        emit({"schema": 1, "events": rows, "open": sum(1 for r in rows if r["state"] == "open"),
              "threshold": c["threshold"]})
    elif not rows:
        print(messages(c)["nothing"])
    else:
        for r in rows:
            state = {"open": "", "answered": f"  [{messages(c)['applied']}]", "attended": "  [x]"}[r["state"]]
            print(f"{r['number']:<4}{r['kind']}  {r['title']}{state}")
    return 0


def cmd_check(args):
    c = contract()
    found = review_all(c)
    ok = not any(level == "fail" for _ev, entries in found for _r, level, _m in entries)
    if args.json:
        emit({"schema": 1, "ok": ok, "events": [{"id": f"{e['kind']}-{e['number']:03d}" if e["number"] else e["name"], "findings":
              [{"rule": r, "level": lv, "message": m} for r, lv, m in entries]} for e, entries in found]})
    else:
        if not found:
            print(messages(c)["nothing"])
        for ev, entries in found:
            print(f"{ev['name']}: {'ok' if not any(l == 'fail' for _r, l, _m in entries) else 'FAILED'}")
            for rule, level, message in entries:
                print(f"  {level.upper():4} {rule}: {message}")
    return 0 if ok else 1


# ----------------------------------------------------------------------------- the notice

def summary(c=None):
    """What the engine knows, for the status, the review and the delivery signals."""
    c = c or contract()
    rows = pending_rows(c)
    opened = [r for r in rows if r["kind"] == "ASK" and r["state"] == "open"]
    return {"asks": opened, "decisions": [r for r in rows if r["kind"] == "DEC" and r["state"] == "open"],
            "to_apply": [r for r in rows if r["state"] == "answered"],
            "blocking": [r for r in opened if r["blocks"]]}


def notice_text(c):
    s, m = summary(c), messages(c)
    lines = []
    if s["asks"]:
        lines.append(f"@gtt · {m['needs']} ({len(s['asks'])})")
        for r in s["asks"]:
            tail = f" → {m['recommend']} {r['recommended']}" + (f" · {m['blocks']} {r['blocks']}" if r["blocks"] else "")
            lines.append(f"{r['number']} {r['title']}{tail}")
    elif s["decisions"]:
        lines.append(f"@gtt · {m['fyi']}")
    for r in s["decisions"]:
        lines.append(f"{m['fyi']}: {r['number']} {r['title']}" if s["asks"] else f"{r['number']} {r['title']}")
    if lines:
        lines.append(m["tail"] if s["asks"] else m["tail_fyi"])
    return "\n".join(lines)


def load_state(c):
    data = read_json(c["locations"]["state"])
    return data if isinstance(data, dict) else {}


def save_state(c, data):
    write_atomic(c["locations"]["state"], json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def hours_since(iso):
    try:
        then = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None
    return (now_dt() - then).total_seconds() / 3600


def reminder_due(c, state=None):
    """True when something blocks and the notice was last shown more than reminder_hours ago."""
    state = state if state is not None else load_state(c)
    if not summary(c)["blocking"]:
        return False
    waited = hours_since(state.get("last_shown"))
    return waited is None or waited >= c["retention"]["reminder_hours"]


def cmd_notice(args):
    c = contract()
    text = notice_text(c)
    state = load_state(c)
    if args.report and state.get("turn") and state.get("turn") == state.get("shown_turn"):
        text = ""                                   # never twice in the same turn
    if args.due and not reminder_due(c, state):
        text = ""
    if text and (args.report or args.due):
        state["shown_turn"] = state.get("turn")
        state["last_shown"] = stamp()
        try:
            save_state(c, state)
        except OSError:
            pass
    if args.json:
        emit({"schema": 1, "text": text, **{k: len(v) for k, v in summary(c).items()}})
    elif text:
        print(text)
    return 0


# ----------------------------------------------------------------------------- what the hook calls

def store_prompt(text, c=None):
    """Keep the human's last messages, locally, so a recorded quote can be checked against them."""
    c = c or contract()
    keep = recent_prompts(c)[-(c["retention"]["quote_window"] - 1):]
    keep.append({"at": stamp(), "text": str(text)[: c["retention"]["prompt_chars"]]})
    write_atomic(c["locations"]["prompts"], "".join(json.dumps(k, ensure_ascii=False) + "\n" for k in keep))


def begin_turn(session, text, c=None):
    """A new turn of the human: the notice may be shown once more."""
    c = c or contract()
    state = load_state(c)
    state["turn"] = hashlib.sha256(f"{session}|{stamp()}|{text}".encode("utf-8")).hexdigest()[:12]
    save_state(c, state)
    return state


def main(argv):
    parser = argparse.ArgumentParser(description="GTT pending events")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ask"); p.add_argument("--type", required=True); p.add_argument("--question", required=True)
    p.add_argument("--why", required=True); p.add_argument("--option", action="append"); p.add_argument("--header"); p.add_argument("--recommended", type=int)
    p.add_argument("--blocks"); p.add_argument("--apply", action="store_true")
    p = sub.add_parser("decide"); p.add_argument("--affects", required=True); p.add_argument("--title", required=True)
    p.add_argument("--what", required=True); p.add_argument("--why", required=True); p.add_argument("--where", required=True)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("list"); p.add_argument("--json", action="store_true"); p.add_argument("--all", action="store_true")
    p = sub.add_parser("record"); p.add_argument("ref"); p.add_argument("answer"); p.add_argument("--quote", required=True)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("answer"); p.add_argument("ref"); p.add_argument("reply", nargs="?"); p.add_argument("--confirmed-by-human", action="store_true")
    p.add_argument("--confirmed", action="store_true")
    p = sub.add_parser("done"); p.add_argument("ref"); p.add_argument("--in", dest="where", required=True); p.add_argument("--apply", action="store_true")
    p = sub.add_parser("clean"); p.add_argument("--apply", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("check"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("notice"); p.add_argument("--report", action="store_true"); p.add_argument("--due", action="store_true")
    p.add_argument("--session", action="store_true"); p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return {"ask": cmd_ask, "decide": cmd_decide, "list": cmd_list, "record": cmd_record, "answer": cmd_answer, "done": cmd_done,
            "clean": cmd_clean, "check": cmd_check, "notice": cmd_notice}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
