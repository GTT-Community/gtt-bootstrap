#!/usr/bin/env python3
"""GTT - the Sonar link of what the agent names to the human.

  gtt_link.py REF [REF ...] [--json]     one line per ref that has a place in Sonar: `REF  URL`; a ref with none is left out

A report that says STORY-783, PROP-009 or REV-011 makes the person go and look for it. Sonar already has a place for each of these - the
Plan for an Epic or a Story, the Inbox for a proposal, an idea or a review, Design for a decision, Health for a gap or a finding code -
and the page is addressed by its own address (`#/view=plan&q=STORY-783`), so a link costs one call and nothing is searched or invented.

The address is the one Sonar is served at when it is running (`gtt sonar`: the port its server announced, checked with a ping) and
otherwise the static page the watcher keeps (.gtt/local/sonar.html). For a project Sonar was never opened for it prints nothing and says how
to start it: a link that leads nowhere is worse than none.

DATA-FREE HELPER: it reads what the project already knows (the pending events, to find the proposal a review is about) and decides nothing.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request


def quote(value):
    return urllib.parse.quote(str(value), safe="")


def _review_entry(number):
    """The proposal or idea a REV is about, from its event file; None when it cannot be told."""
    try:
        import gtt_pending
        contract = gtt_pending.contract()
        for event in gtt_pending.events(contract):
            if event["kind"] == "REV" and int(event["number"]) == int(number):
                return event["fields"].get("entry")
    except Exception:
        return None
    return None


def route(ref):
    """The address inside Sonar's page for a ref (`view=...&...`), or None when Sonar has no place for it."""
    r = ref.strip()
    if re.fullmatch(r"(?:EPIC|STORY)-[A-Za-z0-9]+", r):
        return f"view=plan&q={quote(r)}"
    if re.fullmatch(r"(?:PROP|IDEA)-\d+", r):
        return f"view=inbox&card={quote(r)}"
    m = re.fullmatch(r"REV-(\d+)", r)
    if m:
        entry = _review_entry(m.group(1))
        return f"view=inbox&card={quote(entry)}" if entry else "view=inbox"
    if re.fullmatch(r"(?:ASK|DEC)-\d+", r):
        return "view=plan&f=mine"                                    # what waits for the person
    if re.fullmatch(r"ADR-\d+", r):
        return "view=design&dt=adr"
    if re.fullmatch(r"(?:GAP|OBS)-\d+", r) or re.fullmatch(r"(?:GOV|DEF|DLV|GTT|CODE)-[A-Z0-9-]+", r):
        return f"view=health&hq={quote(r)}"
    return None


def gtt_home():
    return os.environ.get("GTT_HOME") or os.path.join(os.path.expanduser("~"), ".gtt")


def served_port():
    """The port a running Sonar server answers on, or None."""
    try:
        with open(os.path.join(gtt_home(), "sonar", "server.json"), encoding="utf-8") as handle:
            port = int(json.load(handle)["port"])
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_ping", timeout=0.6) as answer:
            return port if answer.status == 200 and b'"sonar"' in answer.read(256) else None
    except Exception:
        return None


def base():
    """(address up to the `#`, whether it is the served page) or (None, False). Only for a project Sonar was opened for (its watcher keeps
    .gtt/local/sonar.html): for any other the page has nothing at that address."""
    page = os.path.abspath(os.path.join(".gtt", "local", "sonar.html"))
    if not os.path.isfile(page):
        return None, False
    port = served_port()
    if port:
        return f"http://127.0.0.1:{port}/", True
    return "file://" + urllib.parse.quote(page), False


def url_for(ref, prefix, served):
    """The link of one ref against an address `base()` gave, or None."""
    where = route(ref.strip().strip(".,;:()[]"))
    if where is None:
        return None
    if served:                                                       # a served page may hold several projects: say which
        where += "&repo=" + quote(os.path.abspath("."))
    return prefix + "#/" + where


def links(refs):
    """([(ref, url)], available): the refs that have a place, in the order given and without repeats."""
    prefix, served = base()
    if prefix is None:
        return [], False
    out, seen = [], set()
    for ref in refs:
        ref = (ref or "").strip().strip(".,;:()[]")
        if not ref or ref in seen:
            continue
        seen.add(ref)
        url = url_for(ref, prefix, served)
        if url:
            out.append((ref, url))
    return out, True


def main(argv):
    as_json = "--json" in argv
    refs = [a for a in argv[1:] if not a.startswith("--")]
    if not refs:
        print("usage: gtt-link.sh REF [REF ...] [--json]", file=sys.stderr)
        return 0
    found, available = links(refs)
    if not available:
        print("gtt-link: Sonar was not opened for this project: `gtt sonar` opens it (no link was made).  |  Sonar no se abrió para este proyecto: `gtt sonar` lo abre.", file=sys.stderr)
        return 0
    if as_json:
        print(json.dumps({"schema": 1, "links": [{"ref": r, "url": u} for r, u in found]}, indent=2, ensure_ascii=False))
    else:
        for ref, url in found:
            print(f"{ref}  {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
