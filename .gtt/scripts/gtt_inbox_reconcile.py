#!/usr/bin/env python3
"""GTT - Inbox reconcile: the deterministic half of the inspector (section 6.1 of the change-flow order).

It reads the repository and writes down what already happened, one line at a time, under the final `---` of the entry's
own file. It uses no model and no tokens, it never accepts, rejects, parks, reopens, re-prioritises or ratifies (those are
the human's), and it is idempotent: run twice, the second run writes nothing.

  gtt_inbox_reconcile.py [--session] [--json] [--dry-run]     bring every entry up to date; archive what ended
  gtt_inbox_reconcile.py adr-hand [--json]                    the ADRs written by hand after the freeze (F5), for Sonar

What it sees in the repo, and the line it adds (inbox.json carries the transitions; this file carries none of its own):

  a complete ADR draft                          Ready: complete draft                          -> accepted (T7), or a REV in Team
  a set with `origin` that was applied          Ratified: gtt promote <set>                    -> work (T15)
  an Epic with `Origin` that became Planned     Ratified: gtt approve EPIC-n                   -> work (T15)
  a RUN of the package that was executed        Ratified: gtt run n                            -> work (T15)
  Stories or Epics citing the entry             Work: <refs>                                   -> work
  all of them Done or Completed                 Closed: done                                   -> closed (T18)
  all of them Cancelled                         Closed: cancelled                              -> closed (T19)
  a promotion that was undone                   Undone: <set>                                  -> accepted (T16)
  a draft or a destination changed              Package: stale                                 -> ratify (asks T17)

`--session` also closes an entry that produced no work at all (an ADR with no derived Stories, T18): at a cut point, never
in the middle of the turn in which the agent is still writing them.
Every new line is written to gtt-domain/delivery-log.jsonl as {"kind": "inbox", ...} by the engine that appends it.
Exit 0 ok, 1 refused, 2 cannot run.
"""

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import gtt_inbox as inbox          # noqa: E402
import gtt_pending as pend         # noqa: E402

STAGED = "gtt-domain/proposals/staged"
BACKUPS = ".gtt/local/promote-backup"
UNDONE = ".gtt/local/promote-undone"
ADR_DIR = "gtt-domain/adr"
RUN_LOG = "gtt-domain/run/log.jsonl"
DONE_STATUS = ("Done", "Completed")
CANCELLED = ("Cancelled",)
MAX_PASSES = 6
REF_IN_ORIGIN = re.compile(r"\b(?:IDEA|PROP)-\d+\b")
OPTIONAL_LINES = re.compile(r"^\s*[-*]\s*(Origin|Supersedes|Approved by)\s*:", re.IGNORECASE)


# ----------------------------------------------------------------------------------------------- hand-written ADRs (F5)

def is_hand_adr(rel):
    """True for a file directly in gtt-domain/adr/ that did not come from a promotion and was not part of the freeze: the
    same two checks `gtt-inbox.sh adr-adopt` makes (the promotion backups, and `git cat-file` against the baseline commit)."""
    name = os.path.basename(rel)
    if not (rel.startswith(ADR_DIR + "/") and rel.endswith(".md")) or "/" in rel[len(ADR_DIR) + 1:]:
        return False
    if name.startswith(("ADR-TEMPLATE", "README")) or not os.path.isfile(rel):
        return False
    if rel in inbox.promoted_paths():
        return False
    commit = inbox.baseline_commit()
    if commit and subprocess.run(["git", "cat-file", "-e", f"{commit}:{rel}"], capture_output=True).returncode == 0:
        return False
    return True


def adr_hand():
    """The ADRs written by hand in gtt-domain/adr/ after the freeze, newest name last: [{path, name, command}].
    Empty before the freeze, and empty once a new freeze ratified what is there (the governed state equals the baseline)."""
    if not inbox.frozen() or not os.path.isdir(ADR_DIR):
        return []
    found = sorted(f"{ADR_DIR}/{n}" for n in os.listdir(ADR_DIR) if is_hand_adr(f"{ADR_DIR}/{n}"))
    if not found:
        return []
    try:
        import gtt_observe
        base = gtt_observe.baseline()
        if base.get("digest") and gtt_observe.governed_digest() == base["digest"]:
            return []
        if not inbox.baseline_commit():     # no commit to ask: only a file whose absence restores the baseline is new
            if gtt_observe.governed_digest(skip=set(found)) != base.get("digest"):
                return []
    except Exception:
        pass
    return [{"path": f, "name": os.path.basename(f), "command": f"gtt adr adopt {f}"} for f in found]


# ----------------------------------------------------------------------------------------------- reading the repo

def read_json(path):
    return pend.read_json(path)


def package_tokens(e):
    """(set names, RUN ids) the entry's Package lines name: `<set> + files`, `RUN-n + <set>`, `<set> (redone)`."""
    sets, runs = [], []
    for line in e["trail"]:
        if line["key"] != "package":
            continue
        value = inbox.MIRROR.sub("", line["value"]).strip()
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", value)
        if not words:
            continue
        if re.fullmatch(r"RUN-\d+", words[0], re.IGNORECASE):
            runs.append(words[0].upper())
            after = value.split("+", 1)[1] if "+" in value else ""
            first = re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", after)
            if first:
                sets.append(first[0])
        else:
            sets.append(words[0])
    return list(dict.fromkeys(sets)), list(dict.fromkeys(runs))


def applied_sets(e, sets):
    out = []
    for name in sets:
        record = read_json(os.path.join(BACKUPS, name, "backup.json"))
        if isinstance(record, dict) and record.get("origin") == e["ref"]:
            out.append(name)
    return out


def undone_sets(e, sets):
    out = []
    for name in sets:
        record = read_json(os.path.join(UNDONE, name + ".json"))
        if isinstance(record, dict) and record.get("origin") == e["ref"]:
            out.append(name)
    return out


def runs_finished(runs):
    """The RUN ids that were executed with exit 0 (gtt-domain/run/log.jsonl)."""
    ok = set()
    for line in (inbox.read(RUN_LOG) or "").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("exit") == 0 and str(row.get("id", "")).upper() in runs:
            ok.add(str(row["id"]).upper())
    return [r for r in runs if r in ok]


def backlog_items():
    if not os.path.isfile(inbox.BACKLOG):
        return [], []
    import gtt_backlog
    return gtt_backlog.parse(inbox.BACKLOG)


def outputs_of(e, stories, epics):
    """The Stories and Epics that cite this entry in their `Origin`."""
    import gtt_backlog
    out = []
    for item in epics + stories:
        if e["ref"] in REF_IN_ORIGIN.findall(item["fields"].get("Origin") or ""):
            out.append({"id": item["id"], "status": gtt_backlog.normal(item.get("status", "")), "kind": "epic" if item["id"].startswith("EPIC") else "story",
                        "item": item})
    return out


def listed_refs(e):
    """Every STORY-n and EPIC-n the trail already names (Triage, Work)."""
    text = " ".join(l["value"] for l in e["trail"] if l["key"] in ("triage", "work"))
    return set(re.findall(r"(?:STORY|EPIC)-\d+", text))


def last_line(e, key):
    return next((l for l in reversed(e["trail"]) if l["key"] == key), None)


def draft_problems(e):
    """Why an ADR draft is not complete yet: `<...>` markers left, or an empty Context, Decision or Consequences."""
    body = e["body"]
    problems = []
    for number, line in enumerate(body.split("\n"), 1):
        if OPTIONAL_LINES.match(line):
            continue
        if inbox.MARKER.search(line):
            problems.append(f"line {number} still has a marker")
            break
    sections = {}
    current = None
    for line in body.split("\n"):
        head = re.match(r"^##\s+(.+?)\s*$", line)
        if head:
            current = head.group(1).strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    for names in (("context", "contexto"), ("decision", "decisión", "decision"), ("consequences", "consecuencias")):
        key = next((n for n in sections if n in names), None)
        text = "\n".join(sections.get(key, [])) if key else ""
        if not re.sub(r"<!--.*?-->|\s", "", text, flags=re.DOTALL):
            problems.append(f"the section {names[0]} is empty")
    return problems


# ----------------------------------------------------------------------------------------------- the passes

class Pass:
    def __init__(self, c, session, dry):
        self.c, self.session, self.dry = c, session, dry
        self.actions = []

    def line(self, e, key, value, actor="gtt", detail=None, **kw):
        self.actions.append(f"{e['ref']}: {inbox.LB(self.c)['trail'][key]}: {value}")
        if self.dry:
            return e
        return inbox.add_line(e, self.c, key, value, actor, detail, **kw)


def live_props_of(e, all_entries):
    return [p for p in all_entries if p["kind"] == "PROP" and p["origin"] == e["ref"]]


def settle_draft(e, p):
    """T7: a draft written by the architect that is complete passes to `accepted`; in Team, when the author is not the person of
    `architecture`, it opens a REV for that person instead."""
    L = inbox.LB(p.c)["phrase"]
    if draft_problems(e):
        return
    role = inbox.roles()
    architect = (role or {}).get("architecture") or (role or {}).get("default")
    e = p.line(e, "ready", L["ready_draft"], "gtt")
    if architect and (e["author"] or "").strip().lower() != architect.strip().lower() and not p.dry:
        rev = pend.open_rev(pend.contract(), {"ref": e["ref"], "title": e["title"], "level": "arch", "sha": inbox.sha_of(e["body"]),
                                              "origin": None, "for": inbox.role_for("arch")}, True)
        if rev is not None:
            p.line(e, "review", f"REV-{rev:03d}", "gtt")


def renew_draft_rev(e, p):
    """A draft in review whose text changed after the REV was opened: that REV can no longer be answered (invariant 3), so a new
    one opens for what the architect wrote now."""
    if e["type"] != "adr" or not inbox.roles() or e["stage"] != "review":
        return
    ev = pend.rev_for(e["ref"], pend.contract())
    if not ev or ev["fields"].get("sha") == inbox.sha_of(e["body"]) or p.dry:
        return
    pend.close_rev(pend.contract(), e["ref"], e["ref"], note="changed")
    rev = pend.open_rev(pend.contract(), {"ref": e["ref"], "title": e["title"], "level": "arch", "sha": inbox.sha_of(e["body"]),
                                          "origin": None, "for": inbox.role_for("arch")}, True)
    if rev is not None:
        p.line(e, "review", f"REV-{rev:03d}", "gtt")


def stale_package(e, sets):
    """Why the package no longer matches: the draft changed after it was armed, or a destination did."""
    for name in sets:
        spec = read_json(os.path.join(STAGED, name, "promote.json"))
        if not isinstance(spec, dict):
            continue
        if spec.get("origin_sha") and spec["origin_sha"] != inbox.sha_of(e["body"]):
            return True
        import hashlib
        for item in spec.get("files", []):
            now = None
            try:
                with open(item["to"], "rb") as handle:
                    now = hashlib.sha256(handle.read()).hexdigest()
            except OSError:
                pass
            if now != item.get("sha_before"):
                    return True
    return False


def handle_ratify(e, p, stories, epics):
    c = p.c
    sets, runs = package_tokens(e)
    staged = [n for n in sets if os.path.isfile(os.path.join(STAGED, n, "promote.json"))]
    applied = applied_sets(e, sets)
    undone = undone_sets(e, sets)
    done_runs = runs_finished(runs)
    outs = outputs_of(e, stories, epics)
    planned = [o for o in outs if o["kind"] == "epic" and o["status"] in ("Planned", "In Progress", "Completed")
               and (o["item"]["fields"].get("Approved") or "").strip()]
    waiting_epic = [o for o in outs if o["kind"] == "epic" and o["status"] == "Proposed"]
    command = None
    if done_runs:
        command = f"gtt run {int(done_runs[-1].split('-')[1])}"
    elif applied and not (runs and waiting_epic):
        command = f"gtt promote {applied[-1]}"
    elif planned:
        command = f"gtt approve {planned[0]['id']}"
    if command:
        return p.line(e, "ratified", command, "gtt")
    if undone and not staged and not applied:
        return p.line(e, "undone", undone[-1], "gtt")
    last = last_line(e, "package")
    if staged and stale_package(e, staged[-1:]) and not (last and last["value"].lower().startswith(inbox.LB(c)["phrase"]["package_stale"].lower())):
        return p.line(e, "package", inbox.LB(c)["phrase"]["package_stale"], "gtt")
    return e


def handle_work(e, p, stories, epics):
    c = p.c
    L = inbox.LB(c)["phrase"]
    ratified = last_line(e, "ratified")
    if ratified:
        sets = [m for m in re.findall(r"gtt promote ([A-Za-z0-9._-]+)", ratified["value"])]
        undone = [n for n in sets if os.path.isfile(os.path.join(UNDONE, n + ".json")) and not os.path.isfile(os.path.join(STAGED, n, "promote.json"))
                  and (read_json(os.path.join(UNDONE, n + ".json")) or {}).get("origin") == e["ref"]]
        if undone:
            return p.line(e, "undone", undone[-1], "gtt")
    outs = outputs_of(e, stories, epics)
    seen = listed_refs(e)
    new = [o["id"] for o in outs if o["id"] not in seen]
    if new:
        e = p.line(e, "work", ", ".join(new), "gtt")
    if outs:
        states = [o["status"] for o in outs]
        if all(s in DONE_STATUS + CANCELLED for s in states):
            if any(s in DONE_STATUS for s in states):
                return p.line(e, "closed", L["done"], "gtt")
            return p.line(e, "closed", L["cancelled"], "gtt")
    elif p.session and ratified:
        return p.line(e, "closed", L["done"], "gtt")
    return e


def sync_priorities(entries_, stories, epics, c, dry):
    """The backlog items an entry produced take the priority its trail holds (while they have not started), then the order
    follows (section 5.7). Returns True when the backlog changed."""
    import gtt_backlog
    changed = False
    for e in entries_:
        if e["stage"] not in ("accepted", "ratify", "work") or not e["priority"]:
            continue
        for o in outputs_of(e, stories, epics):
            if o["status"] in ("In Progress", "Done", "Completed", "Cancelled", "Blocked"):
                continue
            if gtt_backlog.priority_of(o["item"]) != e["priority"] and (e["priority"] != "normal" or (o["item"]["fields"].get("Priority") or "").strip()):
                if dry:
                    changed = True
                elif gtt_backlog.set_field(inbox.BACKLOG, o["id"], "Priority", e["priority"]):
                    changed = True
    if os.path.isfile(inbox.BACKLOG):
        with open(inbox.BACKLOG, encoding="utf-8", newline="") as handle:
            text = handle.read()
        new, moved = gtt_backlog.reorder_text(text)
        if moved:
            changed = True
            if not dry:
                with open(inbox.BACKLOG, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(new)
    return changed


def one_pass(c, session, dry):
    p = Pass(c, session, dry)
    stories, epics = backlog_items()
    every = inbox.entries(c)
    for e in every:
        if e["kind"] == "IDEA" and live_props_of(e, every):
            continue                       # its proposal carries the line, and the engine copies it here
        if e["stage"] == "new" and e["type"] == "adr" and e["where"].endswith("adr/drafts"):
            settle_draft(e, p)
        elif e["stage"] == "review":
            renew_draft_rev(e, p)
        elif e["stage"] == "ratify":
            handle_ratify(e, p, stories, epics)
        elif e["stage"] == "work":
            handle_work(e, p, stories, epics)
        elif e["stage"] in ("closed", "rejected") and not dry:
            path = inbox.archive(e, c)
            if path != e["path"]:
                p.actions.append(f"{e['ref']}: archived in {os.path.dirname(path)}")
    if sync_priorities(inbox.entries(c), stories, epics, c, dry):
        p.actions.append("backlog: priorities and order follow the entries")
    return p.actions


def reconcile(session=False, dry=False):
    """Run until nothing more is true to say; returns the actions taken (empty when everything was already written)."""
    c = inbox.contract()
    if not os.path.isdir(os.path.join("gtt-domain")):
        return []
    out = []
    for _ in range(MAX_PASSES):
        actions = one_pass(c, session, dry)
        out += actions
        if not actions or dry:
            break
    return out


def cmd_reconcile(args):
    actions = reconcile(args.session, args.dry_run)
    if args.json:
        pend.emit({"schema": 1, "kind": "gtt-inbox-reconcile", "actions": actions, "dry_run": bool(args.dry_run)})
    elif actions:
        for a in actions:
            print(f"gtt-inbox: {a}")
    else:
        print("gtt-inbox: nothing to reconcile")
    return 0


def cmd_adr_hand(args):
    found = adr_hand()
    if args.json:
        pend.emit({"schema": 1, "kind": "gtt-adr-hand", "adrs": found})
    elif found:
        for f in found:
            print(f"{f['path']}  ->  {f['command']}")
    else:
        print("no ADR written by hand")
    return 0


def main(argv):
    parser = argparse.ArgumentParser(prog="gtt_inbox_reconcile.py")
    sub = parser.add_subparsers(dest="cmd")
    parser.add_argument("--session", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    x = sub.add_parser("adr-hand")
    x.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "adr-hand":
        return cmd_adr_hand(args)
    return cmd_reconcile(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
