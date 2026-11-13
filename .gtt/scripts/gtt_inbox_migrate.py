#!/usr/bin/env python3
"""GTT - inbox migration: a 1.22 project becomes a 1.23 one (`gtt-inbox.sh migrate`, called by `gtt update`).

  gtt-inbox.sh migrate            what it would do (a dry run: nothing is written)
  gtt-inbox.sh migrate --apply    do it, then print the report

What it moves, and where it goes (GTT-ORDEN-flujo-de-cambios.md, section 14):

  gtt-domain/change-request.md   a request with content becomes an IDEA of type `solicitud` (the block as it was,
                                 `Solicitud: CR-...`); then the desk is removed. Empty, or still the template: removed.
  gtt-domain/proposals/PROPOSAL-*.md  each becomes PROP-NNN-<slug>.md: the body as it was, `Creada:` from Git, the level
                                 from the title of its form (or `por confirmar`), `Origen: IDEA-n` when it cites
                                 `Request: CR-...`; and opens its REV.
  gtt-domain/proposals/staged/*  each set gets `"origin": "legacy"` so it can still be promoted.
  ADR-DRAFT-*.md of the agent    untouched: they are part of packages.
  IDEA-NNN.md that exist         untouched: still valid.

Nothing is deleted without its content being somewhere else first, and running it twice changes nothing. The engine's
own rules apply to what it writes (the trail, the numbers, the REV); the migration only decides what the old files
mean in the new model. Exit 0 ok (also when there is nothing to do), 1 refused, 2 cannot run.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import gtt_change as change          # noqa: E402  (the 1.22 desk: its path and its block)
import gtt_inbox as eng              # noqa: E402
import gtt_pending as pend           # noqa: E402

PROPOSALS = "gtt-domain/proposals"
OLD_PROPOSAL = re.compile(r"^PROPOSAL-(.+)\.md$")
CR_ID = re.compile(r"\bCR-\d{8}-\d{4,6}\b")
REQUESTED = re.compile(r"^(\d{4}-\d{2}-\d{2})\S*(?:\s+by\s+(.+))?$")


def git_date(path):
    """The day the file was first committed (`Creada:`), or None when Git cannot say."""
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--follow", "--format=%as", "--", path],
                             capture_output=True, text=True, timeout=15)
        days = [d for d in out.stdout.split() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)]
        return days[-1] if out.returncode == 0 and days else None
    except (OSError, subprocess.SubprocessError):
        return None


def form_of(body, c):
    """(form number, spec) named by the title of the form in the body, or (None, None)."""
    for number, spec in c["forms"].items():
        if number == "closure":
            continue
        if re.search(re.escape(spec["title"]), body, re.IGNORECASE):
            return number, spec
    return None, None


def proposals_to_move():
    out = []
    if os.path.isdir(PROPOSALS):
        for name in sorted(os.listdir(PROPOSALS)):
            found = OLD_PROPOSAL.match(name)
            path = os.path.join(PROPOSALS, name).replace("\\", "/")
            if found and name != "README.md" and os.path.isfile(path):
                out.append((name, found.group(1), path))
    return out


def sets_to_mark():
    out = []
    for folder in sorted(os.listdir(eng.STAGED)) if os.path.isdir(eng.STAGED) else []:
        path = os.path.join(eng.STAGED, folder, "promote.json")
        spec = pend.read_json(path)
        if isinstance(spec, dict) and "origin" not in spec:
            out.append((folder, path, spec))
    return out


def desk_plan():
    """('none'|'remove'|'migrate'|'keep', fields)"""
    text = change.read(change.REQUEST)
    if text is None:
        return "none", None
    fields = change.has_request()
    if fields is not None:
        return "migrate", fields
    if change.BLOCK.search(text) or re.search(r"(?m)^Change: <", text):
        return "remove", None                       # the template, or a block with no real request
    return "keep", None                             # not the template and not a request: it is the human's text


def idea_of_request(cr, c):
    """The IDEA that already carries `Solicitud: cr` (an earlier run, or one written by hand)."""
    for e in eng.entries(c):
        if e["kind"] == "IDEA" and e["request"] and e["request"].split()[0] == cr:
            return e["ref"]
    return None


def run(args, c):
    L = eng.LB(c)
    apply = bool(args.apply)
    report, notes = [], []
    mark = "" if apply else "would "

    # -------------------------------------------------- 1. the desk
    kind, fields = desk_plan()
    created_idea = {}                                        # CR id -> IDEA ref
    if kind == "migrate":
        found = change.BLOCK.search(change.read(change.REQUEST) or "")
        block = found.group(2).rstrip("\n")
        cr = (CR_ID.search(fields.get("Id", "")) or [None])[0] if fields.get("Id") else None
        when = REQUESTED.match(fields.get("Requested", ""))
        day = (when.group(1) if when else None) or git_date(change.REQUEST) or pend.today()
        who = (when.group(2).strip() if when and when.group(2) else None) or eng.human_name() or ""
        existing = idea_of_request(cr, c) if cr else None
        if existing:
            report.append(f"{existing}: the request {cr} is already in the inbox; the desk is removed")
            created_idea[cr] = existing
            number = None
        else:
            number = eng.next_number(c, "IDEA")
            idea_ref = f"IDEA-{number:03d}"
            report.append(f"{idea_ref}: a request ({eng.title_of(fields['Change'], c)}) from gtt-domain/change-request.md" + (f", {cr}" if cr else ""))
            if cr:
                created_idea[cr] = idea_ref
    elif kind == "remove":
        report.append("gtt-domain/change-request.md: empty or still the template, removed")
    elif kind == "keep":
        notes.append("gtt-domain/change-request.md holds text that is not a request block: left where it is; read it and add what matters with `gtt idea add`.")

    # -------------------------------------------------- 2. the proposals
    moves = proposals_to_move()
    plan_props = []
    next_prop = eng.next_number(c, "PROP")
    for name, stem, path in moves:
        raw = eng.read(path) or ""
        body = eng.draft_body(raw)
        number, spec = form_of(body, c)
        levels = spec["levels"] if spec else []
        determined = levels[0] if len(levels) == 1 else None
        route = determined or (levels[0] if levels else "scope")
        cited = CR_ID.search(body)
        origin = None
        if cited:
            origin = created_idea.get(cited.group(0)) or idea_of_request(cited.group(0), c)
        slug = eng.slugify(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem))
        ref = f"PROP-{next_prop:03d}"
        next_prop += 1
        plan_props.append({"name": name, "path": path, "raw": raw, "body": body, "form": number, "spec": spec, "route": route,
                           "determined": bool(determined), "origin": origin, "slug": slug, "ref": ref,
                           "created": git_date(path) or pend.today()})
        report.append(f"{ref}: {name} -> {c['entries']['PROP']['dirs'][0]}/{ref}-{slug}.md ({'level ' + route if determined else 'level por confirmar' if lang_es() else 'level to confirm'}"
                      + (f", from {origin}" if origin else "") + ", opens its REV)")

    # -------------------------------------------------- 3. the staged sets
    sets = sets_to_mark()
    for folder, _path, _spec in sets:
        report.append(f"staged/{folder}: marked \"origin\": \"legacy\" (it can still be promoted)")

    # -------------------------------------------------- nothing to do?
    if not (kind in ("migrate", "remove") or plan_props or sets):
        print("gtt-inbox: nothing to migrate: the inbox is already the 1.23 one.")
        for note in notes:
            print(f"  note: {note}")
        return 0

    print(f"gtt-inbox: migrate - {mark}do:" if not apply else "gtt-inbox: migrate")
    for line in report:
        print(f"  {mark}{line}" if not apply else f"  {line}")
    for note in notes:
        print(f"  note: {note}")
    print("  unchanged: IDEA-NNN.md, the agent's ADR-DRAFT-*.md and everything under proposals/withdrawn/ and bootstrap/")
    if not apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0

    # -------------------------------------------------- apply: the desk first, so the proposals can cite its idea
    if kind == "migrate" and not existing:
        header = eng.header_line(c, author=eng.author_value(c, "human", who), created=day, type=L["type"]["solicitud"],
                                 now=L["yes"] if not any(p["origin"] == idea_ref for p in plan_props) else None, request=cr)
        title = eng.title_of(fields["Change"], c)
        idea_path = os.path.join(c["entries"]["IDEA"]["dirs"][0], f"{idea_ref}.md").replace("\\", "/")
        eng.write(idea_path, eng.render_entry(c, idea_ref, title, block, header))
        eng.log_event(idea_ref, None, "new", "human", "created")
    if kind in ("migrate", "remove"):
        if kind == "migrate":
            target = idea_path if not existing else path_of_idea(created_idea, cr, c)
            written = eng.read(target) if target else None
            if written is not None and (block in written or existing):
                os.remove(change.REQUEST)
            else:
                notes.append("the desk was kept: the idea could not be confirmed to hold its block")
        else:
            os.remove(change.REQUEST)

    # -------------------------------------------------- apply: the proposals
    pc = pend.contract()
    for p in plan_props:
        ref, route, spec = p["ref"], p["route"], p["spec"]
        origin = p["origin"] or ("sesión" if eng.lang() == "es" else "session")
        level_word = L["levelword"][route] if p["determined"] else ("por confirmar" if eng.lang() == "es" else "to confirm")
        header = eng.header_line(c, author=eng.author_value(c, "agent", eng.agent_name()), created=p["created"], level=level_word,
                                 route=route, origin=origin)
        second = f"{L['header']['form']}: {p['form']} ({spec['name']})" if spec else None
        title = eng.draft_title(p["raw"], p["body"], c)
        text = eng.render_entry(c, ref, title, p["body"], header, second)
        target = os.path.join(c["entries"]["PROP"]["dirs"][0], f"{ref}-{p['slug']}.md").replace("\\", "/")
        sha = eng.sha_of(text)
        rev = pend.open_rev(pc, {"ref": ref, "title": title, "level": route, "sha": sha,
                                 "origin": origin if origin.startswith(("IDEA", "OBS", "STORY")) else None}, True)
        if rev is None:
            rev = pend.open_rev(pc, {"ref": ref, "title": eng.title_of(title, {"title_chars": 40}), "level": route, "sha": sha,
                                     "origin": None}, True)
        if rev is None:
            print(f"gtt-inbox: REFUSED - the REV of {p['name']} does not meet the limits of pending.json. Nothing of it was moved.", file=sys.stderr)
            continue
        eng.write(target, text)
        e = eng.load(target, c)
        eng.add_line(e, c, "review", f"REV-{rev:03d}", "gtt")
        if (eng.read(target) or "").find(p["body"][:200]) >= 0:
            os.remove(p["path"])
        report.append(f"{ref}: REV-{rev:03d} waits for the human (gtt answer {rev} 1)")
        idea = p["origin"] and eng.path_of(p["origin"], c)
        if idea and p["determined"]:
            ie = eng.load(idea, c)
            if ie["stage"] == "new":
                eng.add_line(ie, c, "triage", f"{L['levelword'][route]} {eng.ARROW} {ref}", "agent", mirror=False)

    # -------------------------------------------------- apply: the staged sets
    for folder, path, spec in sets:
        spec["origin"] = "legacy"
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(spec, handle, indent=2)
            handle.write("\n")

    print("gtt-inbox: migrated. Report:")
    for line in report:
        print(f"  {line}")
    for note in notes:
        print(f"  note: {note}")
    return 0


def lang_es():
    return eng.lang() == "es"


def path_of_idea(created, cr, c):
    ref = created.get(cr)
    return eng.path_of(ref, c) if ref else None
