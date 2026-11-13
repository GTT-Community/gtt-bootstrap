#!/usr/bin/env python3
"""GTT - Inbox. One pipeline for everything that asks the design to change.

What a person writes is an IDEA-NNN (an idea, a change request, or an architect's ADR draft); what the agent
writes is a PROP-NNN. Both move through the same stages (new, review, accepted, ratify, work, closed, parked,
rejected) and every step leaves ONE line under the final `---` of the entry's own file. The state is the last
line, never stored apart. The transitions are read from .gtt/contract/inbox.json: any other is refused with
exit 1 and nothing written. Every command that changes something is a dry run until `--apply`.

  gtt_inbox.py add TEXT | --file PATH [--type solicitud --change X --reason Y ...] [--now] [--by NAME] [--apply]   (human)
  gtt_inbox.py adr-new TITLE [--file PATH] [--apply]          the architect's ADR draft in gtt-domain/adr/drafts/   (human)
  gtt_inbox.py adr-adopt FILE [--apply]                       an ADR written by hand in adr/ becomes a draft        (human)
  gtt_inbox.py propose --file DRAFT --level L --form N [--origin REF] [--apply]    the agent registers a PROP, opens its REV
  gtt_inbox.py supersede PROP-n --file DRAFT --level L --form N [--apply]          the agent replaces a PROP in review
  gtt_inbox.py triage IDEA-n --result R --to X [--apply]     the agent's line on a new entry
  gtt_inbox.py park REF | reopen REF | reject REF | drop REF | priority REF P  [--apply]   (human)
  gtt_inbox.py list [--json] [--all] [--origin human|agent] [--stage S]      what is in the inbox and where
  gtt_inbox.py show REF [--json]                              one entry with its whole trail
  gtt_inbox.py transitions [--json]                           the transition table the engine obeys
  gtt_inbox.py reconcile [--session] [--json] [--dry-run]     write down what the repo shows (deterministic; gtt_inbox_reconcile.py)
  gtt_inbox.py adr-hand [--json]                              the ADRs written by hand after the freeze (F5)

gtt-idea.sh is this engine with `--as-ideas`: the same acts, the old names and the old list format.
The author's text is never rewritten: the engine only appends lines. Exit 0 ok, 1 refused, 2 cannot run.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import gtt_pending as pend          # noqa: E402  the helpers every GTT engine shares: read, write_atomic, today, stamp, one_line

CONTRACT = ".gtt/contract/inbox.json"
LEGACY_CONTRACT = ".gtt/contract/ideas.json"
DELIVERY_LOG = "gtt-domain/delivery-log.jsonl"
BACKLOG = "gtt-domain/backlog.md"
FROZEN = "gtt-domain/.frozen"
ADE_STATE = ".gtt/ade.json"
STAGED = "gtt-domain/proposals/staged"
WITHDRAWN = "gtt-domain/proposals/withdrawn"
CANONICAL = "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md"
ARROW = "→"
PREFIX = "gtt-inbox"
TRANSITIONS = None

REF = re.compile(r"^(IDEA|PROP)-(\d{1,})$", re.IGNORECASE)
IDEA_FILE = re.compile(r"^IDEA-(\d{3,})(?:-(.+))?\.md$")
PROP_FILE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}-)?PROP-(\d{3,})-(.+)\.md$")
HEAD = re.compile(r"^# ((?:IDEA|PROP)-\d+) · (.*)$")
LINE = re.compile(r"^([^:\n·]{2,24}): (.*?) · (\d{4}-\d{2}-\d{2})(?: · ([^\s(]+)(?: \((.*)\))?)?$")
LINE_DATE_ONLY = re.compile(r"^([^:\n·]{2,24}): (\d{4}-\d{2}-\d{2})$")
MIRROR = re.compile(r"\s*\((PROP-\d+)\)$")
MARKER = re.compile(r"<[^<>\n]{1,80}>")


# ----------------------------------------------------------------------------------------------- basics

def die(message, code=1):
    print(f"{PREFIX}: {message}", file=sys.stderr)
    sys.exit(code)


def read(path):
    text = pend.read(path)
    return None if text is None else text.replace("\r\n", "\n")


def write(path, text):
    pend.write_atomic(path, text)


def contract():
    data = pend.read_json(CONTRACT)
    if not isinstance(data, dict):
        print(f"{PREFIX}: {CONTRACT} is missing or unreadable; this Bootstrap does not carry the inbox.", file=sys.stderr)
        sys.exit(2)
    return data


def lang():
    return pend.language()


def LB(c):
    return c["labels"][lang()]


def sha_of(text):
    return hashlib.sha256(text.rstrip("\n").encode("utf-8")).hexdigest()


def one_line(text):
    return pend.one_line(text).replace(" · ", " - ")


def reverse(table_by_lang, key):
    """Every spelling of a label, in every language -> its id."""
    out = {}
    for tables in table_by_lang.values():
        for ident, word in tables[key].items():
            out[word.lower()] = ident
    return out


def aliases(c, key):
    return reverse(c["labels"], key)


def frozen():
    return os.path.isfile(FROZEN)


def agent_name():
    state = pend.read_json(ADE_STATE) or {}
    return state.get("primary") or None


def human_name(by=None):
    if by:
        return one_line(by)
    if os.environ.get("GTT_BY"):
        return one_line(os.environ["GTT_BY"])
    try:
        out = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
        return one_line(out.stdout) if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


WORKING_AGREEMENTS = "gtt-domain/working-agreements.md"
METHODOLOGY = ".gtt/methodology.json"
LEVEL_ROLE = {"arch": "architecture", "spec": "specification", "scope": "scope", "non-goal": "specification", "work": "default"}


def roles():
    """The `gtt-roles` block of the working agreements as {architecture, specification, scope, default, roles}, or None when
    the project is not on the Team profile or declares none (Light, Medium and Hard use the same flow, without roles)."""
    if (pend.read_json(METHODOLOGY) or {}).get("profile") != "team":
        return None
    block = re.search(r"```gtt-roles\r?\n(.*?)```", read(WORKING_AGREEMENTS) or "", re.DOTALL)
    if not block:
        return None
    out = {}
    for line in block.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key.strip().startswith("#") and value.strip():
            out[key.strip().lower()] = one_line(value)
    return out or None


def role_for(level):
    """The person of the role that decides entries of this level (`Para:` in the REV): theirs, else `default`, else nobody."""
    found = roles()
    if not found:
        return None
    return found.get(LEVEL_ROLE.get(level, "default")) or found.get("default")


def role_name(level):
    return LEVEL_ROLE.get(level, "default")


def slugify(text, limit=40):
    ascii_text = re.sub(r"[^a-z0-9]+", "-", text.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))).strip("-")
    return (ascii_text[:limit].strip("-")) or "entry"


def title_of(text, c):
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    first = re.sub(r"\s+", " ", first)
    limit = c["title_chars"]
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


# ----------------------------------------------------------------------------------------------- the transition table

def table(c):
    """The transitions of inbox.json as flat rows: id, from, to, op, variant, actor, entry, line."""
    rows = []
    for t in c["transitions"]:
        parts = t.get("alts") or [t]
        for part in parts:
            rows.append({"id": t["id"], "from": part.get("from"), "to": part["to"], "op": part["op"], "variant": part.get("variant") or t.get("variant"),
                         "actor": t["actor"], "entry": part.get("entry") or t.get("entry") or ["IDEA", "PROP"], "line": part.get("line", t.get("line")),
                         "owner": t.get("owner")})
    return rows


def find_transition(c, stage, op, variant, kind):
    for row in table(c):
        if op not in row["op"] or kind not in row["entry"]:
            continue
        if row["variant"] is not None and variant not in row["variant"]:
            continue
        if (stage is None) != (row["from"] is None):
            continue
        if stage is not None and stage not in row["from"]:
            continue
        return row
    return None


def require(c, entry, op, variant=None, kind=None):
    """The transition row for this act, or exit 1: the table is the only authority."""
    stage = entry["stage"] if entry else None
    kind = kind or (entry["kind"] if entry else "IDEA")
    row = find_transition(c, stage, op, variant, kind)
    if row:
        return row
    if entry is None:
        die(f"`{op}` does not start an entry of this kind (inbox.json).")
    names = LB(c)["stage"]
    could = sorted({o for r in table(c) if r["from"] and entry["stage"] in r["from"] and kind in r["entry"] for o in r["op"]})
    die(f"{entry['ref']} stands as `{names[entry['stage']]}`: {op}{(' ' + variant) if variant else ''} is not a transition of the inbox"
        + (f" (from there: {', '.join(could)})." if could else " (nothing leaves that stage)."))


# ----------------------------------------------------------------------------------------------- reading entries

def idea_dirs(c):
    return list(c["entries"]["IDEA"]["dirs"]) + list(c["entries"]["IDEA"]["archive_dirs"])


def prop_dirs(c):
    spec = c["entries"]["PROP"]
    return list(spec["dirs"]) + list(spec["archive"].values())


def scan(c):
    """[(kind, number, path)] of every entry file, archived ones included: numbers are never reused."""
    out = []
    for folder in idea_dirs(c):
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                found = IDEA_FILE.match(name)
                if found and os.path.isfile(os.path.join(folder, name)):
                    out.append(("IDEA", int(found.group(1)), os.path.join(folder, name).replace("\\", "/")))
    for folder in prop_dirs(c):
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                found = PROP_FILE.match(name)
                if found and os.path.isfile(os.path.join(folder, name)):
                    out.append(("PROP", int(found.group(1)), os.path.join(folder, name).replace("\\", "/")))
    return out


def next_number(c, kind):
    return max([n for k, n, _ in scan(c) if k == kind] + [0]) + 1


def canon_ref(ref):
    found = REF.match((ref or "").strip())
    if not found:
        return None
    return f"{found.group(1).upper()}-{int(found.group(2)):03d}"


def path_of(ref, c):
    ref = canon_ref(ref)
    if not ref:
        return None
    kind, number = ref.split("-")[0], int(ref.split("-")[1])
    for k, n, path in scan(c):
        if k == kind and n == number:
            return path
    return None


def split_trail(text, c):
    """(body, [parsed trail lines], has_rule). The trail is the tail after the last `---` when EVERY line of it is a
    trail line; otherwise the rule belongs to the author's text and there is no trail yet."""
    if "\n---\n" not in text:
        return text, [], False
    body, tail = text.rsplit("\n---\n", 1)
    lines = [l for l in tail.split("\n") if l.strip()]
    parsed = [parse_line(l, c) for l in lines]
    if not lines or any(p is None for p in parsed):
        return text, [], False
    return body, parsed, True


def parse_line(line, c):
    keys = aliases(c, "trail")
    actors = aliases(c, "actor")
    found = LINE.match(line)
    if found:
        key = keys.get(found.group(1).strip().lower())
        actor = actors.get((found.group(4) or "").lower()) if found.group(4) else None
        if key and (found.group(4) is None or actor):
            return {"key": key, "value": found.group(2).strip(), "at": found.group(3), "actor": actor, "detail": found.group(5), "raw": line}
    found = LINE_DATE_ONLY.match(line)
    if found:
        key = keys.get(found.group(1).strip().lower())
        if key in ("parked", "dropped"):
            return {"key": key, "value": "", "at": found.group(2), "actor": None, "detail": None, "raw": line}
    return None


def levelword_id(word, c):
    return aliases(c, "levelword").get((word or "").strip().lower())


def triage_info(value, c):
    """What a Triage line says: {result, to}. Legacy spellings of the ideas engine are read too."""
    value = MIRROR.sub("", value).strip()
    if ARROW in value:
        left, right = [x.strip() for x in value.split(ARROW, 1)]
        level = levelword_id(left, c)
        return {"result": "work" if level == "work" else level, "to": right.split()[0] if right else None}
    spell = {name: [t["labels"]["phrase"][name].lower() for t in [{"labels": v} for v in c["labels"].values()]]
             for name in ("covered_by", "question", "incorporated_in", "converted_into", "nongoal_in")}
    low = value.lower()
    for name, result in (("covered_by", "covered"), ("question", "ask"), ("incorporated_in", "incorporated"),
                         ("converted_into", "converted"), ("nongoal_in", "non-goal-legacy")):
        for word in spell[name]:
            if low.startswith(word + " "):
                return {"result": result, "to": value[len(word):].strip().split(" · ")[0] or None}
    return {"result": None, "to": None}


def decision_kind(value, c):
    low = MIRROR.sub("", value).strip().lower()
    for kind, name in (("accepted", "accepted"), ("parked", "parked"), ("rejected", "rejected"), ("closed", "closed_nongoal")):
        for table_ in c["labels"].values():
            if low.startswith(table_["phrase"][name].split(",")[0].lower()):
                return kind
    return None


def stage_after(stage, line, c):
    """The stage after one trail line."""
    rule = c["state_keys"][line["key"]]
    if rule == "same":
        return stage
    if rule == "by value":
        if line["key"] == "triage":
            result = triage_info(line["value"], c)["result"]
            return {"work": "work", "covered": "closed", "incorporated": "closed", "ask": "new", "converted": "review",
                    "non-goal-legacy": "closed", "spec": "review", "arch": "review", "scope": "review", "non-goal": "review"}.get(result, stage)
        return decision_kind(line["value"], c) or stage
    return rule


def priority_from(trail, c):
    prio = aliases(c, "priority")
    out = None
    for line in trail:
        value = MIRROR.sub("", line["value"]).strip().lower()
        if line["key"] == "priority":
            out = prio.get(value) or out
        elif line["key"] == "decision":
            found = re.search(r"(?:prioridad|priority) (\w+)", value)
            if found and prio.get(found.group(1)):
                out = prio[found.group(1)]
    return out


def header_fields(lines, c):
    """The meta lines under the title: {label id: value}. They end at the first line that is not one."""
    labels = aliases(c, "header")
    fields = {}
    index, seen = 1, False
    while index < len(lines) and index < 14:
        line = lines[index]
        index += 1
        if not line.strip() or line.startswith(">"):
            if seen and not line.strip():
                break
            continue
        head = line.split(":", 1)[0].strip().lower()
        if head not in labels:
            if seen:
                break
            continue
        seen = True
        for part in line.split(" · "):
            if ":" not in part:
                continue
            name, _, value = part.partition(":")
            key = labels.get(name.strip().lower())
            if key and key not in fields:
                fields[key] = value.strip()
    return fields


def load(path, c):
    """The entry in `path`: ref, kind, title, type, stage, trail... Never raises on a malformed file."""
    text = read(path) or ""
    lines = text.split("\n")
    head = HEAD.match(lines[0]) if lines else None
    name = os.path.basename(path)
    kind = "PROP" if PROP_FILE.match(name) else "IDEA"
    number = int((PROP_FILE if kind == "PROP" else IDEA_FILE).match(name).group(1)) if (PROP_FILE if kind == "PROP" else IDEA_FILE).match(name) else 0
    ref = head.group(1) if head else f"{kind}-{number:03d}"
    fields = header_fields(lines, c)
    body, trail, _ = split_trail(text, c)
    stage = "new"
    last_change = fields.get("created")
    for line in trail:
        after = stage_after(stage, line, c)
        if after != stage or line["key"] != "priority":
            last_change = line["at"] if after != stage else last_change
        stage = after
    author = fields.get("author", "")
    actors = aliases(c, "actor")
    author_word = re.split(r"\s*\(", author, maxsplit=1)[0].strip().lower()
    author_kind = actors.get(author_word, "human" if kind == "IDEA" else "agent")
    author_name = re.search(r"\((.*)\)", author)
    types = aliases(c, "type")
    etype = "proposal" if kind == "PROP" else types.get(fields.get("type", "idea").lower(), "idea")
    level = levelword_id(fields.get("level"), c)
    route = fields.get("route") if fields.get("route") in c["route_levels"] else level
    origin = (fields.get("origin") or "").split()[0] if fields.get("origin") else None
    open_rev = None
    if stage == "review":
        revs = [l for l in trail if l["key"] == "review"]
        open_rev = MIRROR.sub("", revs[-1]["value"]).strip() if revs else None
    return {"ref": ref, "kind": kind, "number": number, "path": path.replace("\\", "/"), "name": name, "title": head.group(2).strip() if head else ref,
            "type": etype, "author_kind": author_kind, "author": author_name.group(1) if author_name else "", "created": fields.get("created"),
            "level": level, "route": route, "origin": origin, "form": fields.get("form"), "request": fields.get("request"),
            "now": bool(fields.get("now")), "adopted": fields.get("adopted"), "body": body, "text": text, "trail": trail, "stage": stage,
            "priority": priority_from(trail, c), "rev": open_rev, "since": last_change or fields.get("created"),
            "where": os.path.dirname(path).replace("\\", "/")}


def entry(ref, c):
    path = path_of(ref, c)
    if not path:
        die(f"no entry `{ref}` (gtt-inbox.sh list shows them).")
    return load(path, c)


def entries(c):
    return [load(path, c) for _, _, path in sorted(scan(c), key=lambda t: (t[0], t[1]))]


def days_since(day):
    import datetime
    try:
        return (datetime.date.fromisoformat(pend.today()) - datetime.date.fromisoformat(day)).days
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------------------------- writing lines

def line_text(c, key, value, actor, detail=None):
    L = LB(c)
    out = f"{L['trail'][key]}: {one_line(value)} · {pend.today()} · {L['actor'][actor]}"
    return out + (f" ({one_line(detail)})" if detail else "")


def log_event(ref, before, after, actor, key):
    os.makedirs(os.path.dirname(DELIVERY_LOG), exist_ok=True)
    row = {"t": pend.stamp(), "kind": "inbox", "id": ref, "from": before, "to": after, "actor": actor, "key": key}
    with open(DELIVERY_LOG, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def archive(e, c):
    """Invariant 6: nothing is deleted; what ended moves to its archive. Returns the new path."""
    spec = c["entries"]["PROP"]["archive"]
    target = None
    if e["kind"] == "PROP":
        target = spec.get(e["stage"])
    elif e["where"].endswith("adr/drafts") and e["stage"] == "closed":
        target = c["entries"]["IDEA"]["archive_dirs"][0]
    if not target or e["where"] == target:
        return e["path"]
    os.makedirs(target, exist_ok=True)
    dest = os.path.join(target, e["name"]).replace("\\", "/")
    shutil.move(e["path"], dest)
    return dest


def add_line(e, c, key, value, actor, detail=None, mirror=True, move=True):
    """Append one trail line to the entry, log it, archive it if it ended, and copy the key lines to the idea it
    came from. Returns the reloaded entry."""
    line = line_text(c, key, value, actor, detail)
    text = read(e["path"]) or ""
    body, trail, has_rule = split_trail(text, c)
    new = (text.rstrip("\n") + "\n" + line + "\n") if has_rule else (text.rstrip("\n") + "\n\n---\n" + line + "\n")
    write(e["path"], new)
    after = load(e["path"], c)
    log_event(e["ref"], e["stage"], after["stage"], actor, key)
    path = archive(after, c) if move else after["path"]
    after = load(path, c) if path != after["path"] else after
    if mirror and e["kind"] == "PROP" and e["origin"] and e["origin"].startswith("IDEA-") and key in c["mirror_keys"] + ["priority"]:
        if not (key == "closed" and "→" in value):
            idea = path_of(e["origin"], c)
            if idea:
                add_line(load(idea, c), c, key, f"{one_line(value)} ({e['ref']})", actor, detail, mirror=False)
    return after


# ----------------------------------------------------------------------------------------------- headers and bodies

def header_line(c, **kv):
    L = LB(c)["header"]
    return " · ".join(f"{L[k]}: {v}" for k, v in kv.items() if v not in (None, ""))


def author_value(c, actor, name):
    word = LB(c)["actor"][actor]
    return f"{word} ({name})" if name else word


def render_entry(c, ref, title, body, header, second=None):
    out = [f"# {ref} · {title}", "", CANONICAL, "", header]
    if second:
        out.append(second)
    out += ["", body.rstrip("\n"), ""]
    return "\n".join(out)


# ----------------------------------------------------------------------------------------------- add

def cmd_add(args, c):
    L = LB(c)
    kind = args.type or "idea"
    if kind not in ("idea", "solicitud"):
        die("--type is `idea` or `solicitud` (an ADR draft is `adr-new`).")
    require(c, None, "inbox.add")
    if kind == "solicitud":
        if args.text or args.file:
            die("a request is written with --change and --reason, not as free text.")
        if not (args.change and args.reason):
            die("a request needs --change and --reason (--trigger --scope --impact --risk --priority are optional).")
        names = [("Change", args.change), ("Reason", args.reason), ("Trigger", args.trigger), ("Scope", args.scope),
                 ("Impact", args.impact), ("Risk", args.risk), ("Priority", args.priority)]
        text = "\n".join(f"{k}: {one_line(v)}" for k, v in names if v)
        title = title_of(args.change, c)
        now = True
    else:
        if args.change or args.reason:
            die("--change and --reason belong to `--type solicitud`.")
        if args.file:
            text = read(args.file)
            if text is None:
                die(f"cannot read {args.file}.", 2)
        else:
            text = args.text
        if text is None:
            die("give the idea as text or with --file.")
        text = text.replace("\r\n", "\n").rstrip("\n")
        title = title_of(text, c)
        now = bool(args.now)
    if not text.strip():
        die("an empty idea is not added.")
    if len(text) > c["max_chars"]:
        die(f"the entry is {len(text)} characters; the limit is {c['max_chars']}. Split it in two.")
    number = next_number(c, "IDEA")
    ref = f"IDEA-{number:03d}"
    path = os.path.join(c["entries"]["IDEA"]["dirs"][0], f"{ref}.md").replace("\\", "/")
    header = header_line(c, author=author_value(c, "human", human_name(args.by)), created=pend.today(), type=L["type"][kind],
                         now=L["yes"] if now else None, request=getattr(args, "request", None))
    if not args.apply:
        print(f"{PREFIX}: dry run - would create {path}\n(nothing written; re-run with --apply)")
        return 0
    write(path, render_entry(c, ref, title, text, header))
    log_event(ref, None, "new", "human", "created")
    print(f"{PREFIX}: created {path}")
    return 0


# ----------------------------------------------------------------------------------------------- ADR drafts

def cmd_adr_new(args, c):
    L = LB(c)
    title = one_line(args.title)
    if not title:
        die("give the ADR a title.")
    if len(title) > c["title_chars"]:
        die(f"the title is {len(title)} characters; the limit is {c['title_chars']}.")
    if any(e["type"] == "adr" and e["title"].lower() == title.lower() for e in entries(c)):
        die(f"an ADR draft titled `{title}` already exists.")
    require(c, None, "adr.new")
    if args.file:
        body = read(args.file)
        if body is None:
            die(f"cannot read {args.file}.", 2)
    else:
        template = read(c["adr_template"])
        if template is None:
            die(f"cannot read {c['adr_template']}.", 2)
        body = template.split("\n", 1)[1] if template.startswith("# ") else template
        body = "\n".join(l for l in body.split("\n") if "Canonical reference" not in l).strip("\n")
    number = next_number(c, "IDEA")
    ref = f"IDEA-{number:03d}"
    path = os.path.join("gtt-domain/adr/drafts", f"{ref}-{slugify(title)}.md").replace("\\", "/")
    header = header_line(c, author=author_value(c, "human", human_name(args.by)), created=pend.today(), type=L["type"]["adr"], level=L["levelword"]["arch"])
    if not args.apply:
        print(f"{PREFIX}: dry run - would create {path}\n(nothing written; re-run with --apply)")
        return 0
    write(path, render_entry(c, ref, title, body, header))
    log_event(ref, None, "new", "human", "created")
    print(f"{PREFIX}: created {path}")
    return 0


def promoted_paths():
    """Every path a promotion has written, from the backups the engine keeps."""
    out = set()
    folder = ".gtt/local/promote-backup"
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            text = read(os.path.join(folder, name, "backup.json")) or ""
            out.update(re.findall(r"gtt-domain/adr/[^\"\s]+\.md", text))
    return out


def baseline_commit():
    for line in (read(FROZEN) or "").splitlines():
        if line.startswith("#"):
            break
        key, _, value = line.partition(":")
        if key.strip() == "Baseline commit" and value.strip() not in ("", "none"):
            return value.strip()
    return None


def cmd_adr_adopt(args, c):
    L = LB(c)
    rel = os.path.relpath(args.file).replace("\\", "/") if os.path.exists(args.file) else args.file.replace("\\", "/")
    if not (rel.startswith("gtt-domain/adr/") and rel.endswith(".md")) or rel.startswith("gtt-domain/adr/drafts/") or "/" in rel[len("gtt-domain/adr/"):]:
        die("adopt takes a file written by hand directly in gtt-domain/adr/ (not in drafts/).")
    if os.path.basename(rel).startswith(("ADR-TEMPLATE", "README")):
        die(f"{rel} is not an ADR.")
    if not os.path.isfile(rel):
        die(f"no such file: {rel}.")
    if not frozen():
        die("before the freeze the ADRs live in gtt-domain/adr/ and the freeze ratifies them: there is nothing to adopt.")
    if rel in promoted_paths():
        die(f"{rel} came from a promotion; it is part of the governed design, not a hand-written ADR.")
    commit = baseline_commit()
    if commit and subprocess.run(["git", "cat-file", "-e", f"{commit}:{rel}"], capture_output=True).returncode == 0:
        die(f"{rel} is part of the frozen baseline; only a new ADR can be adopted.")
    require(c, None, "adr.adopt")
    text = read(rel)
    heading = next((l[2:].strip() for l in text.split("\n") if l.startswith("# ")), os.path.basename(rel)[:-3])
    title = title_of(re.sub(r"^ADR-\d+\s*[—:-]\s*", "", heading), c)
    number = next_number(c, "IDEA")
    ref = f"IDEA-{number:03d}"
    slug = slugify(re.sub(r"^ADR-\d+-", "", os.path.basename(rel)[:-3]))
    dest = f"gtt-domain/adr/drafts/{ref}-{slug}.md"
    header = header_line(c, author=author_value(c, "human", human_name(args.by)), created=pend.today(), type=L["type"]["adr"],
                         level=L["levelword"]["arch"], adopted=os.path.basename(rel))
    if not args.apply:
        print(f"{PREFIX}: dry run - would move {rel} -> {dest}; gtt-domain/adr/ stays as it was at the freeze\n(nothing written; re-run with --apply)")
        return 0
    write(dest, render_entry(c, ref, title, text, header))
    os.remove(rel)
    log_event(ref, None, "new", "human", "created")
    print(f"{PREFIX}: adopted {rel} -> {dest}")
    return 0


# ----------------------------------------------------------------------------------------------- proposals and their REV

def form_check(c, form, level, text):
    """The problems of a draft against its form: [] when it is complete."""
    if form in c["refused_forms"]:
        return [c["refused_forms"][form]]
    spec = c["forms"].get(form)
    if not spec:
        return [f"form `{form}` is not one of {', '.join(sorted(c['forms']))}"]
    if level not in spec["levels"]:
        return [f"form {form} ({spec['name']}) is for level {'/'.join(spec['levels'])}, not `{level}`"]
    lines = text.split("\n")
    problems = []
    for field in spec["fields"]:
        index = next((i for i, l in enumerate(lines) if re.match(rf"^\s*{re.escape(field)}\s*:", l, re.IGNORECASE)), None)
        if index is None:
            problems.append(f"the field `{field}` is missing")
            continue
        value = lines[index].split(":", 1)[1].strip() if ":" in lines[index] else ""
        if not value:
            nxt = next((l.strip() for l in lines[index + 1:] if l.strip()), "")
            value = "" if (not nxt or re.match(r"^[A-Z][A-Za-z ?]{1,45}:", nxt)) else nxt
        if not value or re.fullmatch(r"<[^<>]*>", value.strip()):
            problems.append(f"the field `{field}` is empty")
    return problems


def draft_body(text):
    lines = text.replace("\r\n", "\n").split("\n")
    while lines and (not lines[0].strip() or lines[0].startswith("# ") or "Canonical reference" in lines[0]):
        lines.pop(0)
    return "\n".join(lines).strip("\n")


def draft_title(text, body, c, explicit=None):
    if explicit:
        return title_of(explicit, c)
    head = next((l[2:].strip() for l in text.replace("\r\n", "\n").split("\n") if l.startswith("# ")), "")
    if head:
        return title_of(head, c)
    for field in ("Suggested change", "Goal", "Kind", "File", "Context file", "Proposed method", "Proposed plan", "Non-goal"):
        found = re.search(rf"^\s*{re.escape(field)}\s*:\s*(.+)$", body, re.MULTILINE | re.IGNORECASE)
        if found:
            return title_of(found.group(1), c)
    return title_of(body, c)


def origin_check(c, origin, allow_review_idea=False):
    """The origin value as written in the header, after the T9 guard."""
    L = LB(c)
    if not origin or origin.lower() in ("session", "sesión", "sesion"):
        return "sesión" if lang() == "es" else "session"
    found = re.match(r"^(IDEA|OBS|STORY)-(\d+)$", origin.strip(), re.IGNORECASE)
    if not found:
        die("--origin is IDEA-n, OBS-n, STORY-n or session.")
    kind, number = found.group(1).upper(), int(found.group(2))
    if kind == "IDEA":
        ref = f"IDEA-{number:03d}"
        idea = path_of(ref, c)
        if not idea:
            die(f"the origin {ref} does not exist.")
        stage = load(idea, c)["stage"]
        if stage != "new" and not (allow_review_idea and stage == "review"):
            die(f"{ref} stands as `{L['stage'][stage]}`: a proposal that cites an idea needs it in `{L['stage']['new']}` (T9).")
        return ref
    if kind == "STORY":
        import gtt_backlog
        stories = gtt_backlog.parse(BACKLOG)[0] if os.path.isfile(BACKLOG) else []
        if not any(s["id"] == f"STORY-{number:03d}" or s["id"] == f"STORY-{number}" for s in stories):
            die(f"the origin STORY-{number:03d} is not in the backlog.")
        return f"STORY-{number:03d}"
    ref = f"OBS-{number:03d}"
    if ref not in (read("gtt-domain/governance-backlog.json") or "") and f"OBS-{number}" not in (read("gtt-domain/governance-backlog.json") or ""):
        die(f"the origin {ref} is not in the governance backlog.")
    return ref


def build_prop(c, args, number, origin, rev_ref=None):
    """(path, text, body_sha, title, level) of the PROP an agent asks for, or exit 1."""
    L = LB(c)
    level = args.level
    if level == "work":
        die("work-level changes need no proposal: write the Story (R1).")
    if level not in c["route_levels"]:
        die(f"--level is one of {', '.join(c['route_levels'])}.")
    form = args.form or ("closure" if level == "non-goal" else None)
    if not form:
        die("give the form of gtt-propose-change with --form N.")
    if level == "non-goal" and form != "closure":
        die("a non-goal proposal is a closure: do not give --form.")
    raw = read(args.file)
    if raw is None:
        die(f"cannot read {args.file}.", 2)
    body = draft_body(raw)
    problems = form_check(c, form, level, body)
    if problems:
        die("the draft is not a complete form:\n  " + "\n  ".join(problems))
    title = draft_title(raw, body, c, args.title)
    slug = slugify(args.slug or re.sub(r"^(PROPOSAL|PROP)-", "", os.path.splitext(os.path.basename(args.file))[0]))
    ref = f"PROP-{number:03d}"
    path = os.path.join(c["entries"]["PROP"]["dirs"][0], f"{ref}-{slug}.md").replace("\\", "/")
    spec = c["forms"][form]
    header = header_line(c, author=author_value(c, "agent", agent_name()), created=pend.today(), level=L["levelword"][level],
                         route=level, origin=origin)
    form_line = f"{L['header']['form']}: {form if form != 'closure' else 0} ({spec['name']})" if form != "closure" else f"{L['header']['form']}: {spec['name']}"
    text = render_entry(c, ref, title, body, header, form_line)
    return path, text, sha_of(text), title, level


def urgent_effect_text(c, level, text):
    """The line the urgent option of a REV shows: which Epic the plan moves and by how many days, or only the hours when
    the plan cannot simulate it (section 5.7). None when there is nothing to say."""
    if level != "scope":
        return None
    found = re.search(r"^\s*Epic ID\s*:\s*(EPIC-\d+)", text or "", re.MULTILINE | re.IGNORECASE)
    if not found:
        return None
    try:
        import gtt_delivery
        effect = gtt_delivery.urgent_effect(found.group(1).upper(), None)
    except Exception:
        return None
    if not effect:
        return None
    E = LB(c)["effect"]
    if effect["moves"]:
        top = effect["moves"][0]
        more = E["more"].format(n=len(effect["moves"]) - 1) if len(effect["moves"]) > 1 else ""
        return E["moves"].format(epic=top["epic"], days=top["days"], more=more)
    return E["hours"].format(hours=f"{effect['hours']:g}")


def cmd_propose(args, c):
    L = LB(c)
    require(c, None, "inbox.propose", kind="PROP")
    origin = origin_check(c, args.origin)
    number = next_number(c, "PROP")
    path, text, sha, title, level = build_prop(c, args, number, origin)
    ref = f"PROP-{number:03d}"
    if not args.apply:
        print(f"{PREFIX}: dry run - would register {path} and open its REV (sha {sha[:12]})\n(nothing written; re-run with --apply)")
        return 0
    rev = pend.open_rev(pend.contract(), {"ref": ref, "title": title, "level": level, "sha": sha, "origin": origin if origin.startswith(("IDEA", "OBS", "STORY")) else None,
                                          "for": role_for(level), "effect": urgent_effect_text(c, level, text)}, True)
    if rev is None:
        die("the REV does not meet the limits of pending.json; shorten the proposal's title.")
    write(path, text)
    e = load(path, c)
    add_line(e, c, "review", f"REV-{rev:03d}", "gtt")
    print(f"{PREFIX}: registered {path}; REV-{rev:03d} waits for the human (gtt answer {rev} 1)")
    return 0


def cmd_supersede(args, c):
    L = LB(c)
    old = entry(args.ref, c)
    if old["kind"] != "PROP":
        die(f"{old['ref']} is not a proposal.")
    require(c, old, "inbox.supersede")
    origin = old["origin"] or ("sesión" if lang() == "es" else "session")
    if origin.startswith("IDEA-"):
        origin = origin_check(c, origin, allow_review_idea=True)
    number = next_number(c, "PROP")
    path, text, sha, title, level = build_prop(c, args, number, origin)
    ref = f"PROP-{number:03d}"
    if not args.apply:
        print(f"{PREFIX}: dry run - would close {old['ref']} (superseded by {ref}), mark its REV attended and open another for {ref}\n(nothing written; re-run with --apply)")
        return 0
    pc = pend.contract()
    rev = pend.open_rev(pc, {"ref": ref, "title": title, "level": level, "sha": sha, "origin": origin if origin.startswith(("IDEA", "OBS", "STORY")) else None,
                             "for": role_for(level), "effect": urgent_effect_text(c, level, text)}, True)
    if rev is None:
        die("the REV does not meet the limits of pending.json; shorten the proposal's title.")
    pend.close_rev(pc, old["ref"], f"{ref}", note=L["phrase"]["superseded_by"].format(r=ref))
    write(path, text)
    new = load(path, c)
    add_line(new, c, "review", f"REV-{rev:03d}", "gtt")
    add_line(old, c, "closed", L["phrase"]["superseded_by"].format(r=ref), "agent")
    if old["origin"] and old["origin"].startswith("IDEA-") and path_of(old["origin"], c):
        add_line(load(path_of(old["origin"], c), c), c, "review", f"REV-{rev:03d} ({ref})", "gtt", mirror=False)
    print(f"{PREFIX}: {old['ref']} closed; registered {path}; REV-{rev:03d} waits for the human (gtt answer {rev} 1)")
    return 0


# ----------------------------------------------------------------------------------------------- triage

def backlog_has(ident, c, origin=None):
    if not os.path.isfile(BACKLOG):
        return False
    import gtt_backlog
    stories, epics = gtt_backlog.parse(BACKLOG)
    for item in stories + epics:
        if item["id"] == ident:
            return origin is None or origin in (item["fields"].get("Origin") or "")
    return False


def cmd_triage(args, c):
    L = LB(c)
    e = entry(args.ref, c)
    if e["kind"] != "IDEA":
        die(f"{e['ref']} is a proposal: only an idea is triaged.")
    result = args.result
    spec = c["triage_results"].get(result)
    if spec is None:
        die(f"result must be one of: {', '.join(r for r in c['triage_results'] if not c['triage_results'][r].get('legacy'))}.")
    if not args.to:
        die("--to is required.")
    legacy_nongoal = result == "non-goal" and args.to == "solution-vision.md"
    if legacy_nongoal and not LEGACY:
        die("a non-goal is a closure proposal: `--result non-goal --to PROP-n` (propose it first).")
    if spec.get("legacy") and not LEGACY:
        die("`converted` is the ideas engine's word: use the level (`spec`, `arch`, `scope`) with `--to PROP-n`.")
    target = r"solution-vision\.md" if legacy_nongoal else c["triage_targets"][result]
    if not re.fullmatch(target, args.to):
        die(f"`--to` for `{result}` must match {target}.")
    variant = "covered" if legacy_nongoal else ("spec" if result == "converted" else result)
    row = require(c, e, "inbox.triage", variant)
    if not LEGACY:
        if result == "work":
            if not backlog_has(args.to, c, origin=e["ref"]):
                die(f"{args.to} does not exist or does not cite `Origin: {e['ref']}` (T3).")
        elif result == "covered":
            kind = args.to.split("-")[0]
            if (kind == "EPIC" and not backlog_has(args.to, c)) or (kind != "EPIC" and not path_of(args.to, c)):
                die(f"{args.to} does not exist (T4).")
            if args.to == e["ref"]:
                die("an entry is not covered by itself.")
        elif result in ("spec", "arch", "scope", "non-goal"):
            p = path_of(args.to, c)
            if not p:
                die(f"{args.to} does not exist: register it with `propose` first (T5).")
            prop = load(p, c)
            if prop["origin"] != e["ref"] or prop["stage"] != "review":
                die(f"{args.to} must cite `Origen: {e['ref']}` and be in review (T5).")
            if prop["route"] != result:
                die(f"{args.to} was proposed at level `{prop['route']}`, not `{result}`.")
        elif result == "ask":
            if not os.path.isfile(os.path.join("gtt-domain/pending", f"{args.to}.md")):
                die(f"{args.to} does not exist (T6).")
        elif result == "incorporated":
            if frozen():
                die("the project is frozen: an idea is no longer incorporated into the draft design (T8).")
            if not os.path.exists(args.to):
                die(f"{args.to} does not exist (T8).")
    ph = L["phrase"]
    if legacy_nongoal:
        value = f"{ph['nongoal_in']} {args.to}"
    elif result == "work":
        value = f"{L['levelword']['work']} {ARROW} {args.to}"
    elif result == "covered":
        value = f"{ph['covered_by']} {args.to}"
    elif result == "converted":
        value = f"{ph['converted_into']} {args.to}"
    elif result == "ask":
        value = f"{ph['question']} {args.to}"
    elif result == "incorporated":
        value = f"{ph['incorporated_in']} {args.to}"
    else:
        value = f"{L['levelword'][result]} {ARROW} {args.to}"
    if not args.apply:
        print(f"{PREFIX}: dry run - would add to {e['name']}: {line_text(c, 'triage', value, 'agent')}\n(nothing written; re-run with --apply)")
        return 0
    add_line(e, c, "triage", value, "agent")
    if result == "covered" and not LEGACY:
        decide = argparse.Namespace(affects="scope", title=f"{e['ref']} covered by {args.to}",
                                what=f"{e['ref']} needs no change of its own: {args.to} already covers it",
                                why="the idea asks for what already exists", where=e["path"], apply=True)
        pend.cmd_decide(decide)
    print(f"{PREFIX}: triaged {e['ref']}")
    return 0


# ----------------------------------------------------------------------------------------------- the human's maintenance acts

def linked_props(e, c):
    return [p for p in entries(c) if p["kind"] == "PROP" and p["origin"] == e["ref"] and p["stage"] in ("review", "accepted", "ratify", "work")]


def set_names(e):
    names = []
    for line in e["trail"]:
        if line["key"] == "package":
            names += re.findall(r"[A-Za-z0-9._-]+", MIRROR.sub("", line["value"]))
    return [n for n in names if os.path.isdir(os.path.join(STAGED, n))]


def cmd_park(args, c, op="inbox.park", key="parked"):
    L = LB(c)
    e = entry(args.ref, c)
    require(c, e, op)
    if e["kind"] == "IDEA" and op in ("inbox.park", "inbox.drop"):
        live = linked_props(e, c)
        if live:
            die(f"{e['ref']} has {live[0]['ref']} in progress: act on {live[0]['ref']}, not on the idea.")
    value = L["phrase"]["from_stage"].format(s=L["stage"][e["stage"]])
    if args.reason:
        value = one_line(args.reason)
    if not args.apply:
        print(f"{PREFIX}: dry run - would add to {e['name']}: {line_text(c, key, value, 'human')}\n(nothing written; re-run with --apply)")
        return 0
    if e["stage"] == "review" and e["kind"] == "PROP":
        pend.close_rev(pend.contract(), e["ref"], e["ref"], note=key)
    if e["stage"] in ("ratify", "accepted"):
        for name in set_names(e):
            os.makedirs(WITHDRAWN, exist_ok=True)
            shutil.move(os.path.join(STAGED, name), os.path.join(WITHDRAWN, f"{pend.today()}-{name}"))
    add_line(e, c, key, value, "human")
    print(f"{PREFIX}: {e['ref']} {key}")
    return 0


def cmd_drop(args, c):
    e = entry(args.ref, c)
    if e["kind"] != "IDEA":
        die(f"{e['ref']} is a proposal: use `reject`.")
    return cmd_park(args, c, "inbox.drop", "dropped")


def cmd_reject(args, c):
    e = entry(args.ref, c)
    if e["kind"] != "PROP":
        die(f"{e['ref']} is an idea: use `drop`.")
    return cmd_park(args, c, "inbox.reject", "rejected")


def cmd_reopen(args, c):
    L = LB(c)
    e = entry(args.ref, c)
    require(c, e, "inbox.reopen")
    last = next((l for l in reversed(e["trail"]) if l["key"] in ("parked", "dropped")), None)
    mirrored = MIRROR.search(last["value"]) if last else None
    if e["kind"] == "IDEA" and mirrored:
        die(f"{e['ref']} was parked with {mirrored.group(1)}: reopen {mirrored.group(1)}.")
    value = L["phrase"]["from_stage"].format(s=L["stage"][e["stage"]])
    if not args.apply:
        print(f"{PREFIX}: dry run - would add to {e['name']}: {line_text(c, 'reopened', value, 'human')}"
              + (" and open a new REV" if e["kind"] == "PROP" else "") + "\n(nothing written; re-run with --apply)")
        return 0
    if e["kind"] == "PROP":
        title, level = e["title"], e["route"]
        rev = pend.open_rev(pend.contract(), {"ref": e["ref"], "title": title, "level": level, "sha": sha_of(e["body"]),
                                              "origin": e["origin"] if (e["origin"] or "").startswith(("IDEA", "OBS", "STORY")) else None,
                                              "for": role_for(level), "effect": urgent_effect_text(c, level, e["body"])}, True)
        if rev is None:
            die("the REV does not meet the limits of pending.json.")
        e = add_line(e, c, "reopened", value, "human", mirror=False)
        add_line(e, c, "review", f"REV-{rev:03d}", "gtt", mirror=False)
        if e["origin"] and e["origin"].startswith("IDEA-") and path_of(e["origin"], c):
            add_line(load(path_of(e["origin"], c), c), c, "review", f"REV-{rev:03d} ({e['ref']})", "gtt", mirror=False)
    else:
        add_line(e, c, "reopened", value, "human")
    print(f"{PREFIX}: {e['ref']} reopened")
    return 0


def cmd_priority(args, c):
    L = LB(c)
    e = entry(args.ref, c)
    require(c, e, "inbox.priority")
    word = aliases(c, "priority").get(args.priority.lower())
    if not word:
        die(f"priority is one of {', '.join(c['priorities'])} ({', '.join(L['priority'].values())}).")
    if e["stage"] == "work":
        import gtt_backlog
        stories, epics = gtt_backlog.parse(BACKLOG) if os.path.isfile(BACKLOG) else ([], [])
        refs = set(re.findall(r"(?:STORY|EPIC)-\d+", " ".join(l["value"] for l in e["trail"] if l["key"] == "work")))
        refs |= {i["id"] for i in stories + epics if e["ref"] in (i["fields"].get("Origin") or "")}
        busy = [i["id"] for i in stories + epics if i["id"] in refs and (i.get("status") in ("In Progress", "Done", "Completed"))]
        if busy:
            die(f"{', '.join(busy)} is already underway: the priority of {e['ref']} no longer moves it (T22).")
    value = L["priority"][word]
    if not args.apply:
        print(f"{PREFIX}: dry run - would add to {e['name']}: {line_text(c, 'priority', value, 'human')}\n(nothing written; re-run with --apply)")
        return 0
    add_line(e, c, "priority", value, "human")
    __import__("gtt_inbox_reconcile").reconcile()           # the backlog takes the new priority and the order follows (5.7)
    print(f"{PREFIX}: {e['ref']} priority {value}")
    return 0


# ----------------------------------------------------------------------------------------------- answering a REV (called by gtt_pending)

def decide(c, ref, option, sha, how):
    """Apply the human's answer to an open REV on `ref`: the Decision line on the entry and on its idea, the archive.
    Returns (ok, message, where). Writes nothing when it refuses."""
    L = LB(c)
    path = path_of(ref, c)
    if not path:
        return False, f"{ref} does not exist.", None
    e = load(path, c)
    if e["stage"] != "review":
        return False, f"{ref} no longer stands in review ({L['stage'][e['stage']]}): this REV is stale.", None
    if sha_of(e["body"]) != sha:
        return False, f"{ref} changed since the REV was opened (sha256): what you would accept is not what you saw. The agent supersedes it and a new REV opens.", None
    if option == "close" and e["route"] != "non-goal":
        return False, f"{ref} is not a closure proposal.", None
    if option in ("accept", "accept-urgent", "accept-low") and e["route"] == "non-goal":
        return False, "a closure proposal is answered close, park or reject.", None
    row = find_transition(c, "review", "pending.answer", option, e["kind"])
    if not row:
        return False, f"`{option}` is not a transition of the inbox from review.", None
    ph = L["phrase"]
    if option.startswith("accept"):
        value = ph["accepted"].format(p=L["priority"][c["rev"]["priority_of"][option]])
    elif option == "park":
        value = ph["parked"]
    elif option == "reject":
        value = ph["rejected"]
    else:
        value = ph["closed_nongoal"]
    after = add_line(e, c, "decision", value, "human", detail=how)
    if option == "reject" and e["route"] == "non-goal" and e["origin"] and e["origin"].startswith("IDEA-"):
        idea = path_of(e["origin"], c)
        if idea:
            idea_entry = load(idea, c)
            # the idea got `Decisión: rechazada (PROP-n)` above: it goes back to triage instead of staying rejected
            add_line(idea_entry, c, "reopened", f"{ph['nongoal_reopened']} ({e['ref']})", "human", mirror=False)
    return True, f"{ref}: {value}", after["path"]


# ----------------------------------------------------------------------------------------------- list, show, transitions

def command_for(e, c):
    if e["stage"] == "review" and e["rev"]:
        number = re.sub(r"\D", "", e["rev"].split()[0])
        return f"gtt answer {int(number)} 1" if number else None
    if e["stage"] == "ratify":
        for line in reversed(e["trail"]):
            if line["key"] == "package":
                names = set_names(e)
                return f"gtt promote {names[0]}" if names else None
    return None


def row_of(e, c):
    L = LB(c)
    return {"ref": e["ref"], "type": e["type"], "origin": e["author_kind"], "from": e["origin"] if (e["origin"] or "").startswith("IDEA-") else None,
            "title": e["title"], "level": e["route"], "stage": e["stage"], "priority": e["priority"], "days_in_stage": days_since(e["since"]),
            "event": e["rev"], "for": None, "command": command_for(e, c), "path": e["path"], "created": e["created"], "now": e["now"],
            "trail": [{"key": l["key"], "value": l["value"], "at": l["at"], "actor": l["actor"]} for l in e["trail"]]}


def cmd_list(args, c):
    L = LB(c)
    rows = [row_of(e, c) for e in entries(c)]
    if not args.all:
        rows = [r for r in rows if r["stage"] not in ("closed", "parked", "rejected")]
    if args.origin:
        rows = [r for r in rows if r["origin"] == args.origin]
    if args.stage:
        rows = [r for r in rows if r["stage"] == args.stage]
    order = {s: i for i, s in enumerate(c["stages"])}
    rows.sort(key=lambda r: (order[r["stage"]], r["ref"]))
    if args.json:
        counts = {s: sum(1 for r in rows if r["stage"] == s) for s in ("new", "review", "accepted", "ratify", "work")}
        pend.emit({"schema": 1, "kind": "gtt-inbox", "entries": rows, "counts": counts})
    elif not rows:
        print(L["empty"])
    else:
        for r in rows:
            extra = f"  <- {r['from']}" if r["from"] else ""
            print(f"{r['ref']}  {L['stage'][r['stage']]:14} {r['title']}{extra}")
    return 0


def cmd_show(args, c):
    e = entry(args.ref, c)
    if args.json:
        data = row_of(e, c)
        data["text"] = e["text"]
        pend.emit({"schema": 1, "kind": "gtt-inbox-entry", "entry": data})
    else:
        print(e["text"], end="")
    return 0


def cmd_transitions(args, c):
    rows = table(c)
    if args.json:
        pend.emit({"schema": 1, "kind": "gtt-inbox-transitions", "transitions": rows, "ids": sorted({r["id"] for r in rows}, key=lambda i: int(i[1:]))})
    else:
        for r in rows:
            print(f"{r['id']:4} {','.join(r['from'] or ['-']):38} -> {r['to'] if isinstance(r['to'], str) else '|'.join(r['to']):16} {','.join(r['op'])}")
    return 0


# ----------------------------------------------------------------------------------------------- the ideas engine's old face

LEGACY = False


def legacy_contract():
    data = pend.read_json(LEGACY_CONTRACT)
    if not isinstance(data, dict):
        print(f"gtt-idea: {LEGACY_CONTRACT} is missing or unreadable.", file=sys.stderr)
        sys.exit(2)
    return data


def legacy_rows(c=None, include_closed=True):
    """The rows gtt_idea.py used to give: {ref, title, state, to, created, author, path}, for the ideas of docs/ideas/."""
    c = contract()
    out = []
    for e in entries(c):
        if e["kind"] != "IDEA" or not e["path"].startswith("docs/ideas/"):
            continue
        triage = next((l for l in reversed(e["trail"]) if l["key"] == "triage"), None)
        info = triage_info(triage["value"], c) if triage else {"result": None, "to": None}
        state = {"new": "new", "review": "converted", "accepted": "converted", "ratify": "converted", "work": "converted",
                 "parked": "parked", "rejected": "dropped"}.get(e["stage"])
        if e["stage"] == "new" and e["trail"] and e["trail"][-1]["key"] == "triage" and info["result"] == "ask":
            state = "ask"
        if e["stage"] == "closed":
            state = "non-goal" if info["result"] == "non-goal-legacy" else "covered"
        out.append({"ref": e["ref"], "title": e["title"], "state": state, "to": info["to"] if state != "new" else None,
                    "created": e["created"], "author": "human", "path": e["path"]})
    return out if include_closed else [r for r in out if r["state"] != "dropped"]


def cmd_legacy_list(args, c):
    found = legacy_rows(c, include_closed=args.all)
    L = LB(c)
    if args.json:
        pend.emit({"schema": 1, "kind": "gtt-ideas", "ideas": found, "new": sum(1 for r in found if r["state"] == "new")})
    elif not found:
        print(pend.read_json(LEGACY_CONTRACT)["labels"][lang()]["empty"])
    else:
        for r in found:
            print(f"{r['ref']}  {r['state']:10} {r['title']}" + (f"  -> {r['to']}" if r["to"] else ""))
    return 0


# ----------------------------------------------------------------------------------------------- main

def build_parser():
    p = argparse.ArgumentParser(prog="gtt_inbox.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    def act(name, func, *flags):
        x = sub.add_parser(name)
        for f in flags:
            f(x)
        x.add_argument("--apply", action="store_true")
        x.set_defaults(func=func)
        return x

    def text(x):
        x.add_argument("text", nargs="?")
        x.add_argument("--file")
        x.add_argument("--type", choices=["idea", "solicitud"])
        for field in ("change", "reason", "trigger", "scope", "impact", "risk", "priority", "by", "request"):
            x.add_argument(f"--{field}")
        x.add_argument("--now", action="store_true")

    def ref(x):
        x.add_argument("ref")

    def proposal(x):
        x.add_argument("--file", required=True)
        x.add_argument("--level", required=True)
        x.add_argument("--form")
        x.add_argument("--origin")
        x.add_argument("--title")
        x.add_argument("--slug")

    act("add", cmd_add, text)
    x = act("adr-new", cmd_adr_new, lambda x: x.add_argument("title"))
    x.add_argument("--file"); x.add_argument("--by")
    x = act("adr-adopt", cmd_adr_adopt, lambda x: x.add_argument("file"))
    x.add_argument("--by")
    act("propose", cmd_propose, proposal)
    act("supersede", cmd_supersede, ref, proposal)
    x = act("triage", cmd_triage, ref)
    x.add_argument("--result", required=True); x.add_argument("--to", required=True)
    for name, func in (("park", cmd_park), ("reopen", cmd_reopen), ("reject", cmd_reject), ("drop", cmd_drop)):
        x = act(name, func, ref)
        x.add_argument("--reason")
    x = act("priority", cmd_priority, ref)
    x.add_argument("priority")
    x = sub.add_parser("list"); x.add_argument("--json", action="store_true"); x.add_argument("--all", action="store_true")
    x.add_argument("--origin", choices=["human", "agent"]); x.add_argument("--stage"); x.set_defaults(func=cmd_list)
    x = sub.add_parser("show"); x.add_argument("ref"); x.add_argument("--json", action="store_true"); x.set_defaults(func=cmd_show)
    x = sub.add_parser("transitions"); x.add_argument("--json", action="store_true"); x.set_defaults(func=cmd_transitions)
    x = sub.add_parser("reconcile"); x.add_argument("--session", action="store_true"); x.add_argument("--json", action="store_true")
    x.add_argument("--dry-run", action="store_true"); x.add_argument("--apply", action="store_true", help="accepted for the operations contract; reconcile always writes unless --dry-run")
    x.set_defaults(func=lambda args, c: __import__("gtt_inbox_reconcile").cmd_reconcile(args))
    x = sub.add_parser("adr-hand"); x.add_argument("--json", action="store_true")
    x.set_defaults(func=lambda args, c: __import__("gtt_inbox_reconcile").cmd_adr_hand(args))
    x = sub.add_parser("migrate"); x.add_argument("--apply", action="store_true")
    x.set_defaults(func=lambda args, c: __import__("gtt_inbox_migrate").run(args, c))
    return p


def main(argv):
    global LEGACY, PREFIX
    if argv and argv[0] == "--as-ideas":
        LEGACY, PREFIX, argv = True, "gtt-idea", argv[1:]
    args = build_parser().parse_args(argv)
    if LEGACY and args.cmd not in ("add", "triage", "park", "drop", "list"):
        die(f"`{args.cmd}` is not an ideas command; use gtt-inbox.sh.")
    c = contract()
    if LEGACY and args.cmd == "list":
        return cmd_legacy_list(args, c)
    if args.cmd in ("add",) and not hasattr(args, "request"):
        args.request = None
    return args.func(args, c)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
