#!/usr/bin/env python3
"""GTT - Ideas. The human's loose ideas, one file each: docs/ideas/IDEA-NNN.md.

  gtt_idea.py add TEXT | --file PATH [--apply]     the human writes an idea; the text is kept exactly as given
  gtt_idea.py triage REF --result R --to X [--apply]   the agent adds ONE line saying what became of it
  gtt_idea.py park REF [--apply] | drop REF [--apply]  the human's: set an idea aside, or discard it
  gtt_idea.py list [--json] [--all]                what the ideas are and where each stands

The idea's text is never rewritten: the engine only ever appends one line after a `---` rule. Every write
is a dry run until `--apply`. Adding, parking and dropping are acts of the human (declared in operations.json
and refused to an agent by the protection hook); triage is the agent's, and only through this engine.
"""

import argparse
import datetime
import json
import os
import re
import sys

CONTRACT = ".gtt/contract/ideas.json"
REF = re.compile(r"^IDEA-(\d{3,})$")
TRAILER = re.compile(r"^(Triage|Parked|Dropped|Triage|Aparcada|Descartada):", re.M)


def contract():
    with open(CONTRACT, encoding="utf-8") as handle:
        return json.load(handle)


def language():
    try:
        with open(".gtt/methodology.json", encoding="utf-8") as handle:
            value = json.load(handle).get("language")
    except (OSError, ValueError):
        value = None
    return value if value in ("en", "es") else "en"


def today():
    return datetime.date.today().isoformat()


def die(message, code=1):
    print(f"gtt-idea: {message}", file=sys.stderr)
    sys.exit(code)


def files(c):
    folder = c["dir"]
    if not os.path.isdir(folder):
        return []
    return sorted(n for n in os.listdir(folder) if re.match(r"^IDEA-\d{3,}\.md$", n))


def next_number(c):
    numbers = [int(REF.match(n[:-3]).group(1)) for n in files(c)]
    return max(numbers, default=0) + 1


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(tmp, path)


def title_of(text, c):
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    first = re.sub(r"\s+", " ", first)
    limit = c["title_chars"]
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def parse(name, c):
    """{ref, title, state, to, created, author, path}. The state is the last trailer line; no trailer = new."""
    path = os.path.join(c["dir"], name)
    text = read(path).replace("\r\n", "\n")
    lines = text.split("\n")
    head = re.match(r"^# (IDEA-\d+) · (.*)$", lines[0]) if lines else None
    ref = head.group(1) if head else name[:-3]
    title = head.group(2) if head else ref
    meta = re.search(r"^[^\n:]+: [^\n]*· [^\n:]+: (\d{4}-\d{2}-\d{2})", text, re.M)
    state, to = "new", None
    trailer = None
    if "\n---\n" in text:
        tail = text.rsplit("\n---\n", 1)[1]
        for line in tail.split("\n"):
            if TRAILER.match(line):
                trailer = line
    if trailer:
        key, _, rest = trailer.partition(":")
        key = key.strip()
        if key in ("Parked", "Aparcada"):
            state = "parked"
        elif key in ("Dropped", "Descartada"):
            state = "dropped"
        else:
            state = "triaged"
            for result, spec in c["triage_results"].items():
                for lang in ("es", "en"):
                    if rest.strip().startswith(spec[lang]):
                        state, to = {"covered": "covered", "converted": "converted", "non-goal": "non-goal", "ask": "ask"}[result], rest.strip()[len(spec[lang]):].split(" · ")[0].strip() or None
    return {"ref": ref, "title": title, "state": state, "to": to, "created": meta.group(1) if meta else None,
            "author": "human", "path": path.replace("\\", "/")}


def rows(c, include_closed=True):
    out = [parse(n, c) for n in files(c)]
    return out if include_closed else [r for r in out if r["state"] not in ("dropped",)]


def find(ref, c):
    ref = ref.upper()
    m = REF.match(ref)
    if not m:
        die(f"`{ref}` is not an idea reference (IDEA-NNN).")
    name = f"IDEA-{int(m.group(1)):03d}.md"
    if name not in files(c):
        die(f"no idea `{ref}` (gtt-idea.sh list shows them).")
    return name


def emit(obj):
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def cmd_add(args):
    c = contract()
    if args.file:
        try:
            text = read(args.file)
        except OSError as exc:
            die(f"cannot read {args.file}: {exc}", 2)
    else:
        text = args.text
    if text is None:
        die("give the idea as text or with --file.")
    text = text.replace("\r\n", "\n").rstrip("\n")
    if not text.strip():
        die("an empty idea is not added.")
    if len(text) > c["max_chars"]:
        die(f"the idea is {len(text)} characters; the limit is {c['max_chars']}. Split it in two.")
    L = c["labels"][language()]
    number = next_number(c)
    ref = f"IDEA-{number:03d}"
    path = os.path.join(c["dir"], f"{ref}.md")
    body = f"# {ref} · {title_of(text, c)}\n\n{L['author']}: {L['human']} · {L['created']}: {today()}\n\n{text}\n"
    if not args.apply:
        print(f"gtt-idea: dry run - would create {path}\n(nothing written; re-run with --apply)")
        return 0
    write(path, body)
    print(f"gtt-idea: created {path}")
    return 0


def append_trailer(name, line, c, apply, what):
    path = os.path.join(c["dir"], name)
    text = read(path).replace("\r\n", "\n")
    if not apply:
        print(f"gtt-idea: dry run - would add to {name}: {line}\n(nothing written; re-run with --apply)")
        return 0
    if "\n---\n" in text and TRAILER.search(text.rsplit("\n---\n", 1)[1]):
        write(path, text if text.endswith("\n") else text + "\n")  # keep as is, then add under the same rule
        text = read(path)
        write(path, text + line + "\n")
    else:
        write(path, text.rstrip("\n") + "\n\n---\n" + line + "\n")
    print(f"gtt-idea: {what} {name}")
    return 0


def cmd_triage(args):
    c = contract()
    name = find(args.ref, c)
    row = parse(name, c)
    if row["state"] != "new":
        die(f"{row['ref']} already stands as `{row['state']}`: an idea is triaged once.")
    spec = c["triage_results"].get(args.result)
    if spec is None:
        die(f"result must be one of: {', '.join(c['triage_results'])}.")
    if not re.fullmatch(spec["to"], args.to or ""):
        die(f"`--to` for `{args.result}` must match {spec['to']}.")
    L = c["labels"][language()]
    line = f"{L['triage']}: {spec[language()]} {args.to} · {today()}"
    return append_trailer(name, line, c, args.apply, "triaged")


def cmd_close(args, key, state):
    c = contract()
    name = find(args.ref, c)
    row = parse(name, c)
    if row["state"] in ("dropped",) or row["state"] == state:
        die(f"{row['ref']} already stands as `{row['state']}`.")
    L = c["labels"][language()]
    return append_trailer(name, f"{L[key]}: {today()}", c, args.apply, state)


def cmd_list(args):
    c = contract()
    found = rows(c, include_closed=args.all)
    if args.json:
        emit({"schema": 1, "kind": "gtt-ideas", "ideas": found, "new": sum(1 for r in found if r["state"] == "new")})
    elif not found:
        print(c["labels"][language()]["empty"])
    else:
        for r in found:
            print(f"{r['ref']}  {r['state']:10} {r['title']}" + (f"  -> {r['to']}" if r["to"] else ""))
    return 0


def main(argv):
    p = argparse.ArgumentParser(prog="gtt_idea.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("text", nargs="?"); a.add_argument("--file"); a.add_argument("--apply", action="store_true"); a.set_defaults(func=cmd_add)
    t = sub.add_parser("triage"); t.add_argument("ref"); t.add_argument("--result", required=True); t.add_argument("--to", required=True); t.add_argument("--apply", action="store_true"); t.set_defaults(func=cmd_triage)
    for name, key, state in (("park", "parked", "parked"), ("drop", "dropped", "dropped")):
        x = sub.add_parser(name); x.add_argument("ref"); x.add_argument("--apply", action="store_true")
        x.set_defaults(func=(lambda k, s: (lambda args: cmd_close(args, k, s)))(key, state))
    l = sub.add_parser("list"); l.add_argument("--json", action="store_true"); l.add_argument("--all", action="store_true"); l.set_defaults(func=cmd_list)
    args = p.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
