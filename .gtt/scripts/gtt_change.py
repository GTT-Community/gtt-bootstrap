#!/usr/bin/env python3
"""GTT - the change flow during development (engine): request a change, follow its proposals, step back.

    gtt-domain/change-request.md     the front door: one request at a time, written by the human
    gtt-domain/proposals/            what the agent drafted: proposals, ADR drafts, staged promotion sets
    gtt-domain/proposals/withdrawn/  what the human withdrew - archived, never deleted
    .gtt/local/promote-backup/       what a promotion replaced - the way back

  gtt_change.py request --change TEXT --reason TEXT [--trigger --scope --impact --risk --priority] [--by NAME]
                        [--replace] [--apply]     write the request (the human's act); the agent is told to process it
  gtt_change.py state [--json]                    the request: absent | empty | pending | processed
  gtt_change.py next-action                       the one line the session context shows while a request waits
  gtt_change.py proposals [--json]                every draft under gtt-domain/proposals/, with its kind and state
  gtt_change.py show NAME [--json]                one of them
  gtt_change.py withdraw NAME [--by NAME] [--apply]   archive a draft nobody will promote (the human's act)
  gtt_change.py last [--json]                     the last promotion, and whether it can be undone
  gtt_change.py undo [NAME] [--apply]             put back what the last promotion replaced (the human's act)

A request is the human's intent, never a decision: the agent reads it, drafts a proposal citing the request id,
and the human decides. Stepping back is never an unfreeze: undoing a promotion that recorded a freeze records a
new freeze over the state that was there before, and the earlier baselines stay in the history. Only the last
promotion can be undone, and only while its files are as it left them. Every mutating command is a dry run
without --apply. Exit 0 ok, 1 refused or a violation, 2 cannot run.
"""

import argparse
import datetime
import glob
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

REQUEST = "gtt-domain/change-request.md"
PROPOSALS = "gtt-domain/proposals"
WITHDRAWN = "gtt-domain/proposals/withdrawn"
STAGED = "gtt-domain/proposals/staged"
BACKUPS = ".gtt/local/promote-backup"
FROZEN = "gtt-domain/.frozen"
ADR_DIR = "gtt-domain/adr"
FIELDS = ("Change", "Reason", "Trigger", "Scope", "Impact", "Risk", "Priority")
PRIORITIES = ("critical", "high", "medium", "low")
REQUEST_ID = re.compile(r"\bCR-\d{8}-\d{4,6}\b")
BLOCK = re.compile(r"(##\s*GTT Request\s*\n+```text\n)(.*?)(\n```)", re.S)
PLACEHOLDER = re.compile(r"<[a-zA-Z][^>]*>")


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read().replace("\r\n", "\n")
    except OSError:
        return None


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def emit(obj):
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def sha256(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def now():
    return os.environ.get("GTT_NOW") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def one_line(text):
    return " ".join(str(text or "").split())


# ------------------------------------------------------------------------------- the request

def request_block():
    """(fields, raw block or None)."""
    found = BLOCK.search(read(REQUEST) or "")
    if not found:
        return {}, None
    fields = {}
    for line in found.group(2).split("\n"):
        m = re.match(r"^([A-Z][A-Za-z ]*):\s*(.*)$", line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields, found.group(2)


def drafts_citing(request_id):
    out = []
    for path in sorted(glob.glob(os.path.join(PROPOSALS, "**", "*"), recursive=True)):
        path = path.replace("\\", "/")  # Windows globs with backslashes
        if os.path.isfile(path) and not path.startswith(WITHDRAWN + "/") and request_id in (read(path) or ""):
            out.append(path)
    for path in sorted(glob.glob(os.path.join(ADR_DIR, "ADR-*.md"))):
        if request_id in (read(path) or ""):
            out.append(path.replace("\\", "/"))
    return out


def request_state():
    fields, raw = request_block()
    out = {"schema": 1, "kind": "gtt-change-request", "file": REQUEST, "state": "absent", "id": None, "fields": {},
           "proposals": [], "authority": "none - the human's intent; a proposal answers it and the human decides"}
    if read(REQUEST) is None:
        return out
    if raw is None or not fields.get("Change") or PLACEHOLDER.search(fields.get("Change", "")):
        out["state"] = "empty"
        return out
    out["fields"] = {k: v for k, v in fields.items() if k in FIELDS or k in ("Id", "Requested")}
    found = REQUEST_ID.search(fields.get("Id", ""))
    out["id"] = found.group(0) if found else None
    out["proposals"] = drafts_citing(out["id"]) if out["id"] else []
    out["state"] = "processed" if out["proposals"] else "pending"
    return out


def next_action():
    state = request_state()
    if state["state"] != "pending":
        return None
    cid = state["id"] or "the request"
    return (f"Change request {cid} pending ({one_line(state['fields'].get('Change'))[:90]}) -> {REQUEST}. "
            f"The human asked for it to be processed: on the user's first message, whatever it says, run "
            f"gtt-propose-change on it and write `Request: {cid}` in the proposal. Process it; never apply it.")


def cmd_request(args):
    values = {"Change": args.change, "Reason": args.reason, "Trigger": args.trigger, "Scope": args.scope,
              "Impact": args.impact, "Risk": args.risk, "Priority": args.priority}
    values = {k: one_line(v) for k, v in values.items() if v and one_line(v)}
    for required in ("Change", "Reason"):
        if not values.get(required):
            print(f"gtt-change: REFUSED - `{required}` is required: a request says what should change and why.", file=sys.stderr)
            return 1
    if values.get("Priority") and values["Priority"].lower() not in PRIORITIES:
        print(f"gtt-change: REFUSED - priority must be one of {', '.join(PRIORITIES)}.", file=sys.stderr)
        return 1
    if any(PLACEHOLDER.search(v) for v in values.values()):
        print("gtt-change: REFUSED - a field still holds template text (`<...>`).", file=sys.stderr)
        return 1
    text = read(REQUEST)
    if text is None or not BLOCK.search(text):
        print(f"gtt-change: cannot run - {REQUEST} has no `## GTT Request` block to write to.", file=sys.stderr)
        return 2
    current = request_state()
    if current["state"] == "pending" and not args.replace:
        print(f"gtt-change: REFUSED - request {current['id'] or ''} is still pending (no proposal answers it yet): "
              f"\"{one_line(current['fields'].get('Change'))[:80]}\". Let the agent process it, or pass --replace "
              "to discard it. Nothing was written.", file=sys.stderr)
        return 1
    stamp = datetime.datetime.now(datetime.timezone.utc)
    cid = os.environ.get("GTT_CHANGE_ID") or f"CR-{stamp.strftime('%Y%m%d')}-{stamp.strftime('%H%M%S')}"
    lines = [f"Id: {cid}", f"Requested: {now()} by {one_line(args.by) or 'the Solution Designer'}"]
    for name in FIELDS:
        lines.append(f"{name}: {values.get(name, '')}".rstrip())
    block = "\n".join(lines)
    print(f"gtt-change: request {cid}")
    for line in lines[2:]:
        print(f"  {line}")
    if current["state"] == "processed":
        print(f"  replaces the processed request {current['id']} (its proposals stay where they are)")
    elif current["state"] == "pending":
        print(f"  discards the pending request {current['id']} (--replace)")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    write(REQUEST, BLOCK.sub(lambda m: m.group(1) + block + m.group(3), text, count=1))
    print(f"gtt-change: written to {REQUEST}. The agent is told to process it at the start of its next session "
          "(the session context's Next action); it drafts a proposal and decides nothing.")
    return 0


def cmd_state(args):
    state = request_state()
    if args.json:
        emit(state)
    else:
        print(f"change request: {state['state']}" + (f" {state['id']}" if state["id"] else "")
              + (f" - {one_line(state['fields'].get('Change'))[:100]}" if state["fields"] else "")
              + (f"; answered by {', '.join(state['proposals'])}" if state["proposals"] else ""))
    return 0


def cmd_next_action(args):
    line = next_action()
    if line:
        print(line)
    return 0


# ------------------------------------------------------------------------------- the drafts

def kind_of(name, is_dir):
    if is_dir:
        return "promotion-set"
    if re.match(r"^PROPOSAL-", name):
        return "proposal"
    if re.match(r"^(ADR-DRAFT|ADR-\d+)", name):
        return "adr-draft"
    if re.match(r"^CHANGE-REQUEST-", name):
        return "change-request-draft"
    if re.match(r"^design-EPIC-\d+", name):
        return "design-draft"
    if name.endswith(".sh"):
        return "promotion-script"
    return "draft"


def title_of(path):
    for line in (read(path) or "").split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def drafts():
    out = []
    if not os.path.isdir(PROPOSALS):
        return out
    for name in sorted(os.listdir(PROPOSALS)):
        path = os.path.join(PROPOSALS, name)
        if name in ("README.md", "withdrawn", "staged", "bootstrap") or name.startswith("."):
            continue
        is_dir = os.path.isdir(path)
        if is_dir:
            continue                                    # adapter catalogs and other folders are not drafts
        text = read(path) or ""
        out.append({"name": name, "path": path.replace("\\", "/"), "kind": kind_of(name, False), "title": title_of(path),
                    "request": (REQUEST_ID.search(text).group(0) if REQUEST_ID.search(text) else None),
                    "state": "draft"})
    for folder in sorted(glob.glob(os.path.join(STAGED, "*"))):
        spec = None
        try:
            with open(os.path.join(folder, "promote.json"), encoding="utf-8") as handle:
                spec = json.load(handle)
        except (OSError, ValueError):
            pass
        name = os.path.basename(folder)
        out.append({"name": name, "path": folder.replace("\\", "/"), "kind": "promotion-set", "title": (spec or {}).get("reason", ""),
                    "request": None, "state": "ready to promote" if spec else "malformed",
                    "files": [f.get("to") for f in (spec or {}).get("files", [])],
                    "promote": f"gtt promote {name}"})
    if os.path.isdir(os.path.join(PROPOSALS, "bootstrap")):
        out.append({"name": "bootstrap", "path": f"{PROPOSALS}/bootstrap", "kind": "bootstrap-working-copies",
                    "title": "the bootstrap's working copies (removed by the freeze)", "request": None, "state": "working"})
    for path in sorted(glob.glob(os.path.join(WITHDRAWN, "*"))):
        out.append({"name": os.path.basename(path), "path": path.replace("\\", "/"), "kind": "withdrawn",
                    "title": title_of(path) if os.path.isfile(path) else "", "request": None, "state": "withdrawn"})
    return out


def cmd_proposals(args):
    items = drafts()
    if args.json:
        emit({"schema": 1, "kind": "gtt-proposals", "request": request_state(), "proposals": items})
        return 0
    if not items:
        print("no proposals")
    for item in items:
        extra = f" (request {item['request']})" if item.get("request") else ""
        print(f"{item['state']:17} {item['kind']:22} {item['name']}{extra}" + (f" - {item['title']}" if item.get("title") else ""))
    return 0


def find(name):
    return next((i for i in drafts() if i["name"] == name and i["kind"] not in ("withdrawn", "bootstrap-working-copies")), None)


def cmd_show(args):
    item = find(args.name)
    if item is None:
        print(f"gtt-change: no proposal `{args.name}` (gtt-change.sh proposals lists them).", file=sys.stderr)
        return 1
    if item["kind"] == "promotion-set":
        body = read(os.path.join(item["path"], "promote.json")) or ""
    else:
        body = read(item["path"]) or ""
    if args.json:
        emit({"schema": 1, "kind": "gtt-proposal", "proposal": item, "content": body})
    else:
        print(body)
    return 0


def cmd_withdraw(args):
    item = find(args.name)
    if item is None:
        print(f"gtt-change: REFUSED - no proposal `{args.name}` to withdraw. Nothing was changed.", file=sys.stderr)
        return 1
    stamp = datetime.date.today().isoformat()
    target = os.path.join(WITHDRAWN, f"{stamp}-{item['name']}")
    print(f"gtt-change: withdraw {item['kind']} {item['path']} -> {target} (archived, not deleted; promoted nothing)")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    os.makedirs(WITHDRAWN, exist_ok=True)
    if os.path.exists(target):
        print(f"gtt-change: REFUSED - {target} already exists. Nothing was changed.", file=sys.stderr)
        return 1
    shutil.move(item["path"], target)
    note = f"\n\n---\nWithdrawn: {now()} by {one_line(args.by) or 'the Solution Designer'}\n"
    if os.path.isfile(target):
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(note)
    else:
        write(os.path.join(target, "WITHDRAWN.md"), "# Withdrawn" + note)
    print(f"gtt-change: withdrawn. Nothing reached the governed context.")
    return 0


# ------------------------------------------------------------------------------- stepping back

def frozen_at():
    if not os.path.isfile(FROZEN):
        return None
    with open(FROZEN, encoding="utf-8") as handle:
        return handle.readline().strip() or None


def promotions():
    """The promotions that can be put back, newest first."""
    out = []
    for path in glob.glob(os.path.join(BACKUPS, "*", "backup.json")):
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError):
            continue
        record["folder"] = os.path.dirname(path)
        record["at"] = record.get("at") or datetime.datetime.fromtimestamp(os.path.getmtime(path), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(record)
    return sorted(out, key=lambda r: r["at"], reverse=True)


def undo_problems(record):
    """Why a promotion cannot be undone safely, or []."""
    problems = []
    for entry in record.get("files", []):
        after = entry.get("sha_after")
        if after is None:
            problems.append(f"{entry['to']}: this promotion did not record what it wrote, so a later edit cannot be ruled out "
                            f"(undo it by hand: bash .gtt/scripts/gtt-promote.sh --undo {record['name']})")
        elif sha256(entry["to"]) != after:
            problems.append(f"{entry['to']} changed after the promotion: undoing would discard that change")
    return problems


def cmd_last(args):
    items = promotions()
    last = items[0] if items else None
    out = {"schema": 1, "kind": "gtt-last-promotion", "promotion": None, "undoable": False, "problems": []}
    if last:
        out["promotion"] = {"name": last["name"], "at": last["at"], "files": [f["to"] for f in last.get("files", [])],
                            "froze": bool(last.get("froze"))}
        out["problems"] = undo_problems(last)
        out["undoable"] = not out["problems"]
    if args.json:
        emit(out)
    elif not last:
        print("no promotion to undo")
    else:
        print(f"last promotion: {last['name']} ({last['at']}); undo: {'possible' if out['undoable'] else 'not possible'}")
        for problem in out["problems"]:
            print(f"  {problem}")
    return 0


def cmd_undo(args):
    items = promotions()
    if not items:
        print("gtt-change: REFUSED - there is no promotion to undo.", file=sys.stderr)
        return 1
    last = items[0]
    if args.name and args.name != last["name"]:
        print(f"gtt-change: REFUSED - only the last promotion ({last['name']}) can be undone; `{args.name}` came before it. "
              "Going further back is a change request.", file=sys.stderr)
        return 1
    problems = undo_problems(last)
    if problems:
        for problem in problems:
            print(f"gtt-change: REFUSED - {problem}. Nothing was changed.", file=sys.stderr)
        return 1
    print(f"gtt-change: undo promotion {last['name']} ({last['at']})")
    for entry in last["files"]:
        print(f"  {'restores' if entry['existed'] else 'removes '} {entry['to']}")
    if last.get("froze"):
        print("  the promotion recorded a freeze: a new freeze records the earlier state again (no unfreeze; the history stays)")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    keep = {e["to"]: read(e["to"]) for e in last["files"] if os.path.isfile(e["to"])}
    import gtt_flow
    from gtt_bash import bash_executable
    # What a failed re-freeze must put back besides the files: the identity registry and the derived index
    # (an artifact the promotion created leaves with it), the governance backlog the freeze observes into,
    # and the promotion's own record, so the undo can be tried again.
    derived = (".gtt/index/artifacts.json", ".gtt/index/technical-index.json", "gtt-domain/governance-backlog.json")
    saved = {path: (open(path, "rb").read() if os.path.isfile(path) else None) for path in derived}
    record = os.path.join(gtt_flow.BACKUPS, last["name"])
    record_copy = os.path.join(".gtt", "local", "undo-in-progress")      # outside the backups: never listed as a promotion
    shutil.rmtree(record_copy, ignore_errors=True)
    shutil.copytree(record, record_copy)
    if gtt_flow.restore(last["name"], quiet=True) != 0:
        shutil.rmtree(record_copy, ignore_errors=True)
        return 1
    created = {e["to"] for e in last["files"] if not e["existed"]}
    if created:
        import gtt_artifacts
        manifest = gtt_artifacts.load_manifest()
        manifest["artifacts"] = [a for a in manifest.get("artifacts", []) if a.get("path") not in created]
        gtt_artifacts.save_manifest(manifest)
        subprocess.run([bash_executable(), os.path.join(".gtt", "scripts", "gtt-index.sh")], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if last.get("froze") and os.path.isfile(FROZEN):
        done = subprocess.run([bash_executable(), os.path.join(".gtt", "scripts", "gtt-freeze.sh")], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if done.returncode not in (0, 2):
            for path, text in keep.items():
                write(path, text)
            for path, data in saved.items():
                if data is None:
                    if os.path.isfile(path):
                        os.remove(path)
                else:
                    with open(path, "wb") as handle:
                        handle.write(data)
            shutil.rmtree(record, ignore_errors=True)
            os.replace(record_copy, record)
            print((done.stdout + done.stderr).rstrip(), file=sys.stderr)
            print("gtt-change: the new freeze failed, so nothing was undone: the promoted files are back. "
                  "Going back is then a change request.", file=sys.stderr)
            return 1
        print("A new freeze recorded the earlier state; the promotion stays in the freeze history.")
    shutil.rmtree(record_copy, ignore_errors=True)
    print(f"gtt-change: promotion {last['name']} undone - {len(last['files'])} file(s) as they were before it.")
    return 0


def main(argv):
    if not os.path.isdir(".gtt"):
        print("gtt-change: run from the project root (no .gtt/ directory here)", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog="gtt_change.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("request")
    for name in ("change", "reason", "trigger", "scope", "impact", "risk", "priority", "by"):
        p.add_argument("--" + name)
    p.add_argument("--replace", action="store_true"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_request)
    p = sub.add_parser("state"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_state)
    p = sub.add_parser("next-action"); p.set_defaults(func=cmd_next_action)
    p = sub.add_parser("proposals"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_proposals)
    p = sub.add_parser("show"); p.add_argument("name"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_show)
    p = sub.add_parser("withdraw"); p.add_argument("name"); p.add_argument("--by"); p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_withdraw)
    p = sub.add_parser("last"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_last)
    p = sub.add_parser("undo"); p.add_argument("name", nargs="?"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_undo)
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
