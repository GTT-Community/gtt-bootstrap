#!/usr/bin/env python3
"""GTT - findings: everything GTT detects, in one shape, stuck to a reference.

  gtt_findings.py list [--json] [--plane P] [--owner O] [--level L] [--ref REF]
  gtt_findings.py ready [REF] [--json]      what an Epic or Story still lacks, and whom it is up to
  gtt_findings.py line                      one line for session.md: what waits to be defined (empty when nothing does)

This module has no rules of its own. Each script that owns a fact emits its findings through `make()`
(`gtt_backlog.findings`, `gtt_design.findings`, `gtt_provenance.findings`, `gtt_pending.findings`,
`gtt_delivery.findings`, `gtt_observe.findings`, `gtt_run.findings`, `gtt_inbox.findings`); this one joins them,
puts the level of what comes next, names the person of the role in the Team profile and derives the situation
of each item: ready, to define or blocked. Codes, planes, owners, fix fields and texts (es/en) are data in
`.gtt/contract/findings.json`. Nothing is stored: a finding is computed from the files every time.

Exit 0 always for `list` and `ready`: a finding never stops anything.
"""
import argparse
import json
import os
import re
import sys
import time

CONTRACT = ".gtt/contract/findings.json"
OWNERS = ("gtt_backlog", "gtt_design", "gtt_provenance", "gtt_pending", "gtt_delivery", "gtt_observe", "gtt_run", "gtt_inbox", "gtt_health", "gtt_activity", "gtt_code")
ROLE_OF = {"GOV-GAP": "architecture", "DEF-INBOX-ADR-DRAFT": "architecture", "DEF-EPIC-DESIGN": "specification", "GOV-COVERAGE": "specification",
           "DEF-EPIC-INTENT": "scope", "DEF-EPIC-ESTIMATE": "scope", "DEF-EPIC-PROPOSED": "scope"}
_cache = {}


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def contract():
    if "c" not in _cache:
        _cache["c"] = read_json(CONTRACT) or {"codes": {}}
    return _cache["c"]


def language():
    value = (read_json(".gtt/methodology.json") or {}).get("language")
    return value if value in ("en", "es") else "en"


class Fill(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def fill(text, params):
    try:
        return text.format_map(Fill(params))
    except (ValueError, IndexError):
        return text


def make(code, ref, where, source, epic=None, level=None, owner=None, **params):
    """One finding, in the shape of section 4.1: plane, level, owner, text and fix come from the contract; the script passes only
    what it found (`ref`, `where` as file:line, and the placeholders of the text)."""
    codes = contract()["codes"]
    spec = codes.get(code) or (codes.get("DLV-FINDING") if code.startswith("DLV-") else None) or {"plane": "governance", "owner": None, "level": "NOTICE", "text": {"en": "{what}", "es": "{what}"},
                                            "fix": {"fields": [], "about": False, "command": None, "chat": {"en": "", "es": ""}}}
    lang = language()
    params = dict(params, ref=ref, epic=epic or "")
    fix = spec["fix"]
    command = fix.get("command")
    return {"code": code, "plane": spec["plane"], "level": level or spec["level"], "ref": ref, "epic": epic, "where": where,
            "owner": owner if owner is not None else spec["owner"], "for": None, "source": source,
            "text": fill(spec["text"][lang], params),
            "fix": {"fields": list(fix.get("fields") or []), "about": bool(fix.get("about")),
                    "command": fill(command, params) if command else None,
                    "chat": fill((fix.get("chat") or {}).get(lang, ""), params) if (fix.get("chat") or {}).get(lang) else None,
                    "ask": fill(fix["ask"][lang], params) if (fix.get("ask") or {}).get(lang) else None}}


def collect():
    """(findings, failed owners). A broken owner never takes the others down: its name goes in `failed`."""
    found, failed = [], []
    for name in OWNERS:
        try:
            module = __import__(name)
            fn = getattr(module, "findings", None)
            if fn is None:
                continue
            found.extend(fn() or [])
        except (Exception, SystemExit):
            failed.append(name)
    finish(found)
    return found, failed


def finish(found):
    """What only the join can know: the level of what comes next, and who of the team each human finding is for."""
    try:
        import gtt_backlog
        coming = gtt_backlog.next_refs(contract().get("next_per_front", 2))
    except (Exception, SystemExit):
        coming = set()
    team = None
    try:
        import gtt_inbox
        team = gtt_inbox.roles()
    except (Exception, SystemExit):
        pass
    for f in found:
        if f["plane"] == "definition" and f["level"] == "NOTICE" and (f["ref"] in coming or f["epic"] in coming and f["ref"] == f["epic"]):
            f["level"] = "WARNING"
        f["next"] = f["ref"] in coming
        if team and f["owner"] == "human":
            f["for"] = team.get({"architecture": "architecture", "specification": "specification", "scope": "scope"}.get(ROLE_OF.get(f["code"], "default"), "default")) or team.get("default")
    rank = {"BLOCKING": 0, "WARNING": 1, "NOTICE": 2}
    found.sort(key=lambda f: (rank.get(f["level"], 3), f["plane"], f["ref"] or "", f["code"]))


def situation(ref, found):
    """blocked when a BLOCKED finding sticks to it; else to define when it has a definition finding; else ready."""
    own = [f for f in found if f["ref"] == ref and f["plane"] == "definition"]
    if any(f["code"] == "DEF-STORY-BLOCKED" for f in own):
        return "blocked"
    return "to_define" if own else "ready"


def readiness(found):
    """The situation of every Epic and Story of the backlog; an Epic is ready when it has no finding of its own and all its open Stories are."""
    import gtt_backlog
    stories, epics = gtt_backlog.parse(gtt_backlog.DEFAULT)
    out = {}
    for s in stories:
        out[s["id"]] = {"kind": "story", "epic": s["epic"], "status": gtt_backlog.normal(s["status"]), "situation": situation(s["id"], found)}
    for e in epics:
        own = situation(e["id"], found)
        opened = [v for k, v in out.items() if v["epic"] == e["id"] and v["status"] not in ("Done", "Cancelled")]
        if own == "ready" and any(v["situation"] == "to_define" for v in opened):
            own = "to_define"
        if own != "blocked" and any(v["situation"] == "blocked" for v in opened) and not any(v["situation"] == "ready" for v in opened):
            own = "blocked" if opened else own
        out[e["id"]] = {"kind": "epic", "epic": e["id"], "status": gtt_backlog.normal(e.get("status", "")), "raw_status": e.get("status", ""), "situation": own}
    return out


def report():
    started = time.time()
    found, failed = collect()
    try:
        ready = readiness(found)
    except (Exception, SystemExit):
        ready = {}
    counts = {"to_define": 0, "blocked": 0, "ready": 0, "mine": 0}
    for ref, v in ready.items():
        if v["status"] in ("Done", "Cancelled", "Completed"):
            continue
        counts[v["situation"]] = counts.get(v["situation"], 0) + 1
    counts["inbox"] = sum(1 for f in found if f["code"].startswith("DEF-INBOX-"))
    counts["mine"] = sum(1 for f in found if f["owner"] == "human" and f["plane"] == "definition")
    return {"schema": 1, "kind": "gtt-findings", "findings": found, "readiness": ready, "counts": counts, "failed": failed,
            "ms": round((time.time() - started) * 1000)}


def cmd_list(args):
    data = report()
    rows = [f for f in data["findings"] if (not args.plane or f["plane"] == args.plane) and (not args.owner or f["owner"] == args.owner)
            and (not args.level or f["level"] == args.level.upper()) and (not args.ref or f["ref"] == args.ref or f["epic"] == args.ref)]
    if args.json:
        print(json.dumps(dict(data, findings=rows), indent=2, ensure_ascii=False))
        return 0
    for f in rows:
        who = {"human": "te toca" if language() == "es" else "yours", "agent": "le toca a claude" if language() == "es" else "the agent's"}.get(f["owner"], "-")
        print(f"{f['level']:8} {f['code']:26} {f['ref'] or '-':14} {who:18} {f['text']}  ({f['where'] or '-'})")
    if not rows:
        print("no findings")
    return 0


def cmd_ready(args):
    data = report()
    ref = args.ref
    found = [f for f in data["findings"] if not ref or f["ref"] == ref or f["epic"] == ref]
    state = data["readiness"].get(ref) if ref else None
    if args.json:
        print(json.dumps({"schema": 1, "ref": ref, "situation": state["situation"] if state else None, "findings": found,
                          "counts": data["counts"]}, indent=2, ensure_ascii=False))
        return 0
    if ref:
        print(f"{ref}: {state['situation'] if state else 'unknown'}")
    for f in found:
        print(f"  {f['code']} ({f['owner']}): {f['text']}")
    return 0


def line(data=None):
    """`Por definir: 2 épicas · 5 historias (2 siguientes) · 2 te tocan` for session.md; empty when nothing waits to be defined."""
    data = data or report()
    es = language() == "es"
    open_ = [(ref, v) for ref, v in data["readiness"].items() if v["status"] not in ("Done", "Cancelled", "Completed")]
    epics = [r for r, v in open_ if v["kind"] == "epic" and v["situation"] == "to_define"]
    stories = [r for r, v in open_ if v["kind"] == "story" and v["situation"] == "to_define"]
    coming = [r for r in stories if any(f["ref"] == r and f.get("next") for f in data["findings"])]
    mine = sum(1 for f in data["findings"] if f["owner"] == "human" and f["plane"] == "definition" and f["ref"] in dict(open_))
    if not (epics or stories):
        return ""
    if es:
        return f"Por definir: {len(epics)} {'épica' if len(epics) == 1 else 'épicas'} · {len(stories)} {'historia' if len(stories) == 1 else 'historias'} ({len(coming)} {'siguiente' if len(coming) == 1 else 'siguientes'}) · {mine} te {'toca' if mine == 1 else 'tocan'}"
    return f"To define: {len(epics)} Epic{'' if len(epics) == 1 else 's'} · {len(stories)} Stor{'y' if len(stories) == 1 else 'ies'} ({len(coming)} next) · {mine} yours"


def cmd_line(_args):
    text = line()
    if text:
        print(text)
    return 0


def main(argv):
    parser = argparse.ArgumentParser(prog="gtt_findings.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    one = sub.add_parser("list")
    one.add_argument("--json", action="store_true")
    for name in ("plane", "owner", "level", "ref"):
        one.add_argument("--" + name)
    two = sub.add_parser("ready")
    two.add_argument("ref", nargs="?")
    two.add_argument("--json", action="store_true")
    sub.add_parser("line")
    args = parser.parse_args(argv)
    return {"list": cmd_list, "ready": cmd_ready, "line": cmd_line}[args.cmd](args)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv[1:]))
