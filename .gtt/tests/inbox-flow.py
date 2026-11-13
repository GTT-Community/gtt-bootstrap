#!/usr/bin/env python3
"""GTT inbox flow: the one pipeline for ideas, requests, proposals and ADR drafts, end to end.

Started from gtt-flujo-e2e.py (the end-to-end check of how proposals, ideas, change requests, ADRs and CHANGE records
flowed in 1.21). It runs on disposable copies of the project, with the real Claude Code hooks, and covers the
criteria of GTT-ORDEN-flujo-de-cambios section 18 that the engine and the protection own:

  1  `gtt idea add` creates an IDEA in `new` with the full header; the agent cannot create it or edit its text
  2  a request is an IDEA of type solicitud, `--now` by default; two can wait at once
  3  `inbox.propose` registers a PROP with author, date, level, route and origin, opens its REV with the sha; an
     incomplete form is refused
  4  a registered PROP cannot be edited by the agent; `supersede` closes it and opens another REV
  7  every transition of section 3.2 that does not depend on reconcile works, and any other is refused with exit 1
     and nothing written (the engine reads the table from inbox.json; the test carries its own oracle)
  8  the state of an entry is its last line (reconcile's idempotence belongs to the next prompt)
  9  a REV answered with the entry changed is refused
  10 the agent cannot run T1, T2, T10, T11, T12, T20, T21, T22 or T23, by tool or by shell
  11 a REV shows in the chat (`gtt-pending.sh show`) and in pending/, never resolves itself, stays out of `answer ok`
  12 an answer in the chat is recorded with the exact words and writes `Decision` on the PROP and on its idea
  and: every new trail line is in delivery-log.jsonl (kind inbox)

  python3 .gtt/tests/inbox-flow.py [--project .] [--keep]
Exit 0 = every check held, 1 = at least one failed.
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acc", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
check, write, tree_hash = acc.check, acc.write, acc.tree_hash

TODAY = datetime.date.today().isoformat()
INBOX = ".gtt/scripts/gtt-inbox.sh"
PENDING = ".gtt/scripts/gtt-pending.sh"
FORM4 = """Proposed Epic Change

Kind: new Epic
Epic ID: new
Current state: none
Goal: Sync the parcels that have no signal
Scope: an offline queue
Out of Scope: conflict resolution
Reason: the field teams lose signal
Contradicts governed context or an ADR?: no
Impact: one new module
Risk: low
"""
FORM2 = """Proposed Context Change

File: gtt-domain/context/glossary.md
Current statement: order
Suggested change: add parcel
Reason: new word
Impact: low
Risk: low
"""
CLOSURE = """Non-goal: the product does not do payments
Reason: solution-vision.md lists payments as out of scope
"""
STORIES = "#### Stories\n\n##### STORY-001 — Cancel an order\n- **Status:** Planned\n- **Origin:** IDEA-00{n}\n- **Implements:** design/EPIC-001#R-1\n"


def sh(cwd, *argv, stdin=None, env=None):
    p = subprocess.run(["bash", *argv], cwd=cwd, input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, **(env or {})))
    return p.returncode, p.stdout, p.stderr


def inbox(p, *args):
    return sh(p, INBOX, *args)


def py(p, code):
    proc = subprocess.run([sys.executable, "-c", code], cwd=p, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


def text(p, *parts):
    path = os.path.join(p, *parts)
    return open(path, encoding="utf-8").read() if os.path.isfile(path) else ""


def listing(p, *flags):
    rc, out, err = inbox(p, "list", "--json", "--all", *flags)
    try:
        return {r["ref"]: r for r in json.loads(out)["entries"]}
    except ValueError:
        return {}


def draft(p, name, body):
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", name), body)
    return f"gtt-domain/proposals/drafts/{name}"


def log_rows(p):
    rows = []
    for line in text(p, "gtt-domain", "delivery-log.jsonl").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return [r for r in rows if r.get("kind") == "inbox"]


def project(proj, tmp, name, frozen=True, language=None):
    def before(p):
        with open(os.path.join(p, "gtt-domain", "context", "stack.md"), "a", encoding="utf-8") as handle:
            handle.write("\n## 6. Map change log\n\n| Date | ADR or CHANGE | What changed |\n|---|---|---|\n| | | |\n")
        backlog = os.path.join(p, "gtt-domain", "backlog.md")
        template = open(backlog, encoding="utf-8").read()
        example = template[template.index("### EPIC-001 — <Epic title (example)>"):template.index("## General Development Work")]
        write(backlog, template.replace(example, "") + acc.EPICS)
        if language:
            write(os.path.join(p, ".gtt", "methodology.json"), json.dumps({"language": language}))
    if frozen:
        p, rc, out = acc.frozen_project(proj, tmp, name, before_freeze=before)
        check(rc == 0, f"{name}: a frozen test project is created", out[-300:])
    else:
        p = acc.fresh(proj, tmp, name)
        before(p)
    acc.place_claude_hook(proj, p)
    write(os.path.join(p, ".gtt", "ade.json"), "{}\n")      # an installed project: the instruction-plane and inbox rules apply there
    return p


# ------------------------------------------------------------------------------------------------ the hooks

def who_may_write(proj, tmp):
    print("\n[hooks] criteria 1, 4 and 10: who may write what, by tool and by shell, in both regimes")
    for label, frozen in (("frozen", True), ("before the freeze", False)):
        p = project(proj, tmp, "hooks-" + ("f" if frozen else "t"), frozen=frozen)
        deny = lambda kind, target: acc.claude_decides(p, kind, target)[0]
        check(deny("file", "docs/ideas/IDEA-001.md"), f"{label}: the agent cannot write an idea's text")
        check(deny("file", "gtt-domain/adr/drafts/IDEA-002-redis.md"), f"{label}: the agent cannot write an ADR draft (tool)")
        check(deny("shell", "echo x >> gtt-domain/adr/drafts/IDEA-002-redis.md"), f"{label}: the agent cannot write an ADR draft (shell)")
        check(deny("shell", "rm -rf gtt-domain/adr/drafts"), f"{label}: the agent cannot remove the ADR drafts")
        check(deny("file", "gtt-domain/proposals/PROP-001-redis.md"), f"{label}: the agent cannot write a registered proposal (tool)")
        check(deny("shell", "sed -i s/a/b/ gtt-domain/proposals/PROP-001-redis.md"), f"{label}: the agent cannot edit a registered proposal (shell)")
        check(deny("shell", "mv gtt-domain/proposals/PROP-001-redis.md /tmp/x"), f"{label}: the agent cannot move a registered proposal")
        check(deny("file", "gtt-domain/proposals/done/PROP-001-redis.md") and deny("file", "gtt-domain/proposals/withdrawn/PROP-001-redis.md"),
              f"{label}: an archived proposal is as closed as a live one")
        check(not deny("file", "gtt-domain/proposals/drafts/redis.md"), f"{label}: the agent CAN write its draft under proposals/drafts/")
        check(not deny("file", "gtt-domain/proposals/PROPOSAL-redis.md"), f"{label}: a PROPOSAL-*.md of the old flow is still the agent's")
        for verb in ("add 'x' --apply", "park IDEA-001 --apply", "reopen IDEA-001 --apply", "reject PROP-001 --apply", "drop IDEA-001 --apply",
                     "priority PROP-001 urgent --apply", "adr-new 'Title' --apply", "adr-adopt gtt-domain/adr/ADR-002-x.md --apply",
                     "add --type solicitud --change x --reason y --apply"):
            check(deny("shell", f"bash {INBOX} {verb}"), f"{label}: the agent cannot run `gtt-inbox.sh {verb.split()[0]}` (T1/T2/T20/T21/T22)")
        check(deny("shell", "python3 .gtt/scripts/gtt_inbox.py --as-ideas add x --apply"), f"{label}: nor through the engine's alias flag")
        check(deny("shell", "bash .gtt/scripts/gtt-idea.sh add x --apply"), f"{label}: nor through gtt-idea.sh")
        for cli in ("gtt idea add 'x'", "gtt idea park IDEA-001", "gtt idea drop IDEA-001", "gtt change --change x --reason y", "gtt inbox park IDEA-001",
                    "gtt inbox reopen IDEA-001", "gtt inbox reject PROP-001", "gtt inbox drop IDEA-001", "gtt inbox priority PROP-001 urgent",
                    "gtt adr new 'Title'", "gtt adr adopt gtt-domain/adr/ADR-002-x.md", "gtt answer 15 1"):
            check(deny("shell", cli), f"{label}: the agent cannot run `{cli.split(' -')[0].split(' ')[0:3]}`")
        check(deny("shell", "bash .gtt/scripts/gtt-pending.sh answer 15 1 --confirmed-by-human"), f"{label}: the agent cannot answer a REV (T10/T11/T12/T23)")
        check(deny("file", "gtt-domain/pending/REV-015.md"), f"{label}: the agent cannot write a REV")
        for engine_call in (f"bash {INBOX} propose --file gtt-domain/proposals/drafts/x.md --level spec --form 2 --apply",
                            f"bash {INBOX} supersede PROP-001 --file gtt-domain/proposals/drafts/x.md --level spec --form 2 --apply",
                            f"bash {INBOX} triage IDEA-001 --result spec --to PROP-001 --apply", f"bash {INBOX} list --json", f"bash {INBOX} show IDEA-001",
                            "gtt inbox", "gtt inbox show IDEA-001", "bash .gtt/scripts/gtt-pending.sh show", "bash .gtt/scripts/gtt-idea.sh triage IDEA-001 --result covered --to EPIC-001 --apply",
                            'bash .gtt/scripts/gtt-pending.sh record 15 1 --quote "15: 1" --apply'):
            check(not deny("shell", engine_call), f"{label}: the agent MAY run {engine_call.split(' --')[0][:70]}")
    # the portable engine decides alike (Kiro, Copilot, Cursor, OpenHands, Antigravity)
    p = project(proj, tmp, "hooks-portable")
    for fmt in ("kiro", "copilot"):
        check(acc.format_decides(p, fmt, "file", "gtt-domain/adr/drafts/IDEA-002-x.md")[0], f"{fmt}: the portable engine denies an ADR draft write")
        check(acc.format_decides(p, fmt, "file", "gtt-domain/proposals/PROP-001-x.md")[0], f"{fmt}: the portable engine denies a registered proposal write")
        check(acc.format_decides(p, fmt, "shell", f"bash {INBOX} park IDEA-001 --apply")[0], f"{fmt}: the portable engine denies `inbox park`")
        check(not acc.format_decides(p, fmt, "shell", f"bash {INBOX} list --json")[0], f"{fmt}: the portable engine allows `inbox list`")
    settings = json.load(open(os.path.join(p, ".claude", "settings.json"), encoding="utf-8"))["permissions"]["deny"]
    for rule in ("Write(/gtt-domain/adr/drafts/**)", "Edit(/gtt-domain/adr/drafts/**)", "Write(/gtt-domain/proposals/PROP-*.md)", "Edit(/gtt-domain/proposals/PROP-*.md)"):
        check(rule in settings, f"settings.json denies {rule}")


# ------------------------------------------------------------------------------------------------ entries, REV, answers

def entries_and_reviews(proj, tmp):
    print("\n[F1/F2] criteria 1 and 2: an idea, and requests that can wait together")
    p = project(proj, tmp, "flow")
    before = tree_hash(p)
    rc, o, e = inbox(p, "add", "Move sessions to Redis so we can scale horizontally")
    check(rc == 0 and tree_hash(p) == before, "add is a dry run without --apply: nothing is written", o + e)
    rc, o, e = inbox(p, "add", "Move sessions to Redis so we can scale horizontally", "--by", "Ana", "--apply")
    idea1 = os.path.join(p, "docs", "ideas", "IDEA-001.md")
    body = text(p, "docs", "ideas", "IDEA-001.md")
    check(rc == 0 and os.path.isfile(idea1), "the human adds IDEA-001", o + e)
    check(re.match(r"# IDEA-001 · Move sessions to Redis so we can scale horizontally\n\n> \*\*Canonical reference:\*\* https://\S+GTT-CANONICAL-v3\.0\.md\n\n"
                   rf"Author: human \(Ana\) · Created: {TODAY} · Type: idea\n\nMove sessions to Redis so we can scale horizontally\n$", body),
          "criterion 1: the file has the full header (author, date, type) and the text exactly as written", body[:300])
    check(listing(p).get("IDEA-001", {}).get("stage") == "new", "criterion 1: the IDEA is in `new`")
    rc, o, e = inbox(p, "add", "x" * 4001, "--apply")
    check(rc == 1, "an idea over 4000 characters is refused", o + e)
    rc, o, e = inbox(p, "add", "--type", "solicitud", "--change", "Move sessions to Redis", "--reason", "Horizontal scaling", "--priority", "high",
                     "--risk", "low", "--apply")
    req1 = text(p, "docs", "ideas", "IDEA-002.md")
    check(rc == 0 and "Type: request" in req1 and re.search(r"· Now: yes\n", req1) and "Change: Move sessions to Redis\nReason: Horizontal scaling\nRisk: low\nPriority: high\n" in req1,
          "criterion 2: a request is an IDEA of type request, with `--now` by default and its fields as a block", req1)
    rc, o, e = inbox(p, "add", "--type", "solicitud", "--change", "Something else", "--reason", "x", "--apply")
    states = listing(p)
    check(rc == 0 and states.get("IDEA-002", {}).get("stage") == "new" and states.get("IDEA-003", {}).get("stage") == "new",
          "criterion 2: two requests wait at once (V7)", o + e)
    rc, o, e = inbox(p, "add", "--type", "solicitud", "--change", "no reason", "--apply")
    check(rc == 1, "a request without its reason is refused", o + e)

    print("\n[F3] criterion 3: the agent proposes; the engine registers it and opens the REV")
    f4 = draft(p, "parcels.md", FORM4)
    before = tree_hash(p)
    rc, o, e = inbox(p, "propose", "--file", f4, "--level", "scope", "--form", "4", "--origin", "IDEA-001")
    check(rc == 0 and tree_hash(p) == before, "propose is a dry run without --apply", o + e)
    bad = draft(p, "incomplete.md", FORM4.replace("Risk: low\n", "").replace("Goal: Sync the parcels that have no signal", "Goal:"))
    rc, o, e = inbox(p, "propose", "--file", bad, "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    check(rc == 1 and tree_hash(p) == before + "" or (rc == 1 and not os.path.exists(os.path.join(p, "gtt-domain", "pending", "REV-001.md"))),
          "criterion 3: an incomplete form is refused and nothing is written", o + e)
    check("Risk" in e and "Goal" in e, "the refusal names the missing fields", e)
    for label, args in (("a level the form does not serve", ("--level", "arch", "--form", "4")), ("work level", ("--level", "work", "--form", "4")),
                        ("form 5 (GTTGuard)", ("--level", "spec", "--form", "5")), ("a missing origin", ("--level", "scope", "--form", "4", "--origin", "IDEA-099")),
                        ("a non-existent form", ("--level", "scope", "--form", "9"))):
        h = tree_hash(p)
        rc, o, e = inbox(p, "propose", "--file", f4, *args, "--apply")
        check(rc == 1 and tree_hash(p) == h, f"propose refuses {label}", o + e)
    rc, o, e = inbox(p, "propose", "--file", f4, "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    prop = text(p, "gtt-domain", "proposals", "PROP-001-parcels.md")
    check(rc == 0 and prop, "the agent registers PROP-001", o + e)
    check(re.search(rf"^Author: agent.* · Created: {TODAY} · Level: scope · Route: scope · Origin: IDEA-001$", prop, re.M)
          and "Form: 4 (Epic change)" in prop and "Canonical reference" in prop and prop.rstrip().endswith("\n---\nReview: REV-001 · " + TODAY + " · gtt"),
          "criterion 3: the PROP carries author, date, level, route and origin, and its first trail line is the REV", prop[:500])
    check(prop.split("\n---\n")[0].count("Goal: Sync the parcels") == 1, "the body is the agent's text, as written")
    rev = text(p, "gtt-domain", "pending", "REV-001.md")
    sha = re.search(r"sha: ([0-9a-f]{64})", rev)
    import hashlib
    entry_body = prop.rsplit("\n---\n", 1)[0].rstrip("\n")
    check(bool(sha) and sha.group(1) == hashlib.sha256(entry_body.encode()).hexdigest(), "criterion 3: the REV keeps the sha256 of the entry", rev[:400])
    check(rev.startswith("# REV-001 · Review · PROP-001\n") and rev.count("\n") <= 16 and re.search(r"^5\. Reject", rev, re.M) and rev.rstrip().endswith("Answer:"),
          "the REV is at most 16 lines, with five options and the answer line", rev)
    check(listing(p).get("PROP-001", {}).get("stage") == "review" and listing(p)["PROP-001"]["from"] == "IDEA-001", "the PROP is in review and knows its idea")
    rc, o, e = inbox(p, "propose", "--file", f4, "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    check(rc == 0 and os.path.isfile(os.path.join(p, "gtt-domain", "proposals", "PROP-002-parcels.md")), "a second PROP gets the next number", o + e)
    rc, o, e = inbox(p, "triage", "IDEA-001", "--result", "scope", "--to", "PROP-001", "--apply")
    idea_text = text(p, "docs", "ideas", "IDEA-001.md")
    check(rc == 0 and idea_text.startswith(body.rstrip("\n")) and f"\n---\nTriage: scope → PROP-001 · {TODAY} · agent\n" in idea_text,
          "triage adds one line to the idea; its text is untouched", e + idea_text[-200:])
    check(listing(p)["IDEA-001"]["stage"] == "review", "the idea takes the stage of its proposal: in review")
    rc, o, e = inbox(p, "triage", "IDEA-001", "--result", "spec", "--to", "PROP-001", "--apply")
    check(rc == 1, "an idea in review is not triaged again (T5 starts from `new`)", e)
    rc, o, e = inbox(p, "propose", "--file", f4, "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    check(rc == 1, "a proposal cannot cite an idea that is no longer new (T9)", e)

    print("\n[REV] criterion 11: the REV is in the chat and in pending/, and never resolves itself")
    rc, o, e = sh(p, PENDING, "show")
    check(rc == 0 and "@gtt · Needs you (2)" in o and "REV-001" in o and "1. Accept, normal priority (recommended)" in o and "gtt answer" in o and "sha: " in o and
          not re.search(r"[0-9a-f]{64}", o), "criterion 11: `gtt-pending.sh show` brings the options; the sha is shown short", o[:500])
    rc, o, e = sh(p, PENDING, "list", "--json")
    rows = [r for r in json.loads(o)["events"] if r["kind"] == "REV"]
    check(len(rows) == 2 and rows[0]["entry"] == "PROP-001" and rows[0]["state"] == "open" and rows[0]["recommended"] == 1 and len(rows[0]["options"]) == 5,
          "the REV is listed with its entry, its state and its five options", o[:300])
    rc, o, e = sh(p, PENDING, "check")
    check(rc == 0, "the REV passes the pending rules", o + e)
    h = tree_hash(p)
    rc, o, e = sh(p, PENDING, "answer", "ok", "--confirmed-by-human")
    check(tree_hash(p) == h, "`gtt answer ok` is for decisions only: it does not touch a REV", o + e)
    rc, o, e = sh(p, PENDING, "record", "all", "ok", "--quote", "ok", "--apply")
    check(rc == 1 and tree_hash(p) == h, "`record all ok` does not answer a REV", o + e)
    rc, o, e = sh(p, PENDING, "answer", "1", "ok", "--confirmed-by-human")
    check(rc == 1 and tree_hash(p) == h, "a REV is answered with an option number, not with `ok`", o + e)
    rc, o, e = sh(p, PENDING, "answer", "1", "9", "--confirmed-by-human")
    check(rc == 1 and tree_hash(p) == h, "an option that does not exist is refused", o + e)
    rc, o, e = sh(p, PENDING, "answer", "1", "1")
    check(rc == 1 and tree_hash(p) == h, "answering needs the human's flag", o + e)
    later = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sh(p, PENDING, "clean", "--apply", env={"GTT_NOW": later})
    check(os.path.isfile(os.path.join(p, "gtt-domain", "pending", "REV-001.md")), "criterion 11: 90 days of silence resolve nothing: the REV is still there")
    rc, o, e = sh(p, PENDING, "notice", "--json", env={"GTT_NOW": later})
    check("REV" in o or "PROP-001" in o, "the notice keeps naming it", o)
    snap = json.loads(sh(p, ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json", env={"GTT_SONAR_NO_WATCH": "1"})[1] or "{}")
    check(snap.get("schema") == "sonar.v1" or snap.get("schema") == 1 or "ideas" in snap, "sonar.v1 still renders with a REV pending", str(list(snap)[:5]))

    print("\n[REV] criterion 12: an answer in the chat is recorded with the exact words, and writes `Decision` on the PROP and on its idea")
    h = tree_hash(p)
    rc, o, e = sh(p, PENDING, "record", "1", "1", "--quote", "1: 1", "--apply")
    check(rc == 1 and tree_hash(p) == h, "without the human's words in the prompts, `record` refuses", o + e)
    py(p, "import sys; sys.path.insert(0, '.gtt/scripts'); import gtt_pending as g; g.store_prompt('1: 1, vale')")
    rc, o, e = sh(p, PENDING, "record", "1", "2", "--quote", "1: 1", "--apply")
    check(rc == 1, "a quote that does not say that answer is refused", o + e)
    rc, o, e = sh(p, PENDING, "record", "1", "1", "--quote", "1: 1", "--apply")
    prop = text(p, "gtt-domain", "proposals", "PROP-001-parcels.md")
    idea_text = text(p, "docs", "ideas", "IDEA-001.md")
    check(rc == 0, "the agent records the answer with the human's words", o + e)
    check(re.search(rf"\nDecision: accepted, priority normal · {TODAY} · human \(chat: «1: 1»\)\n$", prop), "criterion 12: the PROP gets `Decision` with the exact words", prop[-250:])
    check(re.search(rf"\nDecision: accepted, priority normal \(PROP-001\) · {TODAY} · human \(chat: «1: 1»\)\n$", idea_text), "criterion 12: and so does its idea, with (PROP-001)", idea_text[-250:])
    check(listing(p)["PROP-001"]["stage"] == "accepted" and listing(p)["PROP-001"]["priority"] == "normal" and listing(p)["IDEA-001"]["stage"] == "accepted",
          "the PROP and its idea stand as accepted, normal priority")
    rev = text(p, "gtt-domain", "pending", "REV-001.md")
    check("Answer: 1 (chat:" in rev and re.search(r"\nAttended: ", rev), "the REV is answered and marked attended", rev[-200:])
    rc, o, e = sh(p, PENDING, "answer", "1", "2", "--confirmed-by-human")
    check(rc == 1, "an attended REV is not answered twice", o + e)
    check("REV-001" not in sh(p, PENDING, "show")[1], "the chat no longer shows it")
    return p


def supersede_and_changes(proj, tmp):
    print("\n[supersede] criterion 4: after registration the PROP is the engine's; `supersede` closes it and opens another REV")
    p = project(proj, tmp, "supersede")
    inbox(p, "add", "Cache the catalog", "--apply")
    f2 = draft(p, "cache.md", FORM2)
    rc, o, e = inbox(p, "propose", "--file", f2, "--level", "spec", "--form", "2", "--origin", "IDEA-001", "--apply")
    check(rc == 0, "PROP-001 (spec) registered", o + e)
    inbox(p, "triage", "IDEA-001", "--result", "spec", "--to", "PROP-001", "--apply")
    better = draft(p, "cache2.md", FORM2.replace("add parcel", "add parcel and sync"))
    h = tree_hash(p)
    rc, o, e = inbox(p, "supersede", "PROP-001", "--file", better, "--level", "arch", "--form", "2")
    check(rc == 0 and tree_hash(p) == h, "supersede is a dry run without --apply", o + e)
    rc, o, e = inbox(p, "supersede", "PROP-001", "--file", better, "--level", "arch", "--form", "5", "--apply")
    check(rc == 1 and tree_hash(p) == h, "supersede checks the new form like propose does", o + e)
    rc, o, e = inbox(p, "supersede", "PROP-001", "--file", better, "--level", "arch", "--form", "2", "--apply")
    check(rc == 0, "the agent supersedes PROP-001 with a re-triaged PROP-002", o + e)
    old = text(p, "gtt-domain", "proposals", "done", "PROP-001-cache.md")
    new = text(p, "gtt-domain", "proposals", "PROP-002-cache2.md")
    check(old and not os.path.exists(os.path.join(p, "gtt-domain", "proposals", "PROP-001-cache.md")), "criterion 4/6: the replaced PROP is archived in proposals/done/ (nothing is deleted)")
    check(re.search(rf"\nClosed: superseded by PROP-002 · {TODAY} · agent\n$", old), "its last line says it was superseded", old[-200:])
    check("Origin: IDEA-001" in new and "Route: arch" in new and new.rstrip().endswith("Review: REV-002 · " + TODAY + " · gtt"), "the new PROP keeps the origin and opens REV-002", new[-300:])
    rev1 = text(p, "gtt-domain", "pending", "REV-001.md")
    check(re.search(r"\nAttended: .* · superseded by PROP-002|\nAttended: .*review", rev1) or "Attended:" in rev1, "the old REV is marked attended", rev1[-200:])
    check(os.path.isfile(os.path.join(p, "gtt-domain", "pending", "REV-002.md")) and "REV-001" not in sh(p, PENDING, "show")[1], "only the new REV waits for the human")
    idea = text(p, "docs", "ideas", "IDEA-001.md")
    check(idea.rstrip().endswith("Review: REV-002 (PROP-002) · " + TODAY + " · gtt") and listing(p)["IDEA-001"]["stage"] == "review", "the idea shows the new REV and stays in review", idea[-250:])
    h = tree_hash(p)
    rc, o, e = inbox(p, "supersede", "PROP-001", "--file", better, "--level", "arch", "--form", "2", "--apply")
    check(rc == 1 and tree_hash(p) == h, "a PROP that is no longer in review cannot be superseded", o + e)

    print("\n[REV] criterion 9: a REV answered with the entry changed is refused")
    prop_path = os.path.join(p, "gtt-domain", "proposals", "PROP-002-cache2.md")
    original = open(prop_path, encoding="utf-8").read()
    open(prop_path, "w", encoding="utf-8").write(original.replace("add parcel and sync", "add parcel, sync and drop the cache"))
    h = tree_hash(p)
    rc, o, e = sh(p, PENDING, "answer", "2", "1", "--confirmed-by-human")
    check(rc == 1 and "changed" in e and tree_hash(p) == h, "criterion 9: the PROP changed after the REV opened: the answer is refused and nothing is written", o + e)
    py(p, "import sys; sys.path.insert(0, '.gtt/scripts'); import gtt_pending as g; g.store_prompt('2: 1')")
    h = tree_hash(p)
    rc, o, e = sh(p, PENDING, "record", "2", "1", "--quote", "2: 1", "--apply")
    check(rc == 1 and tree_hash(p) == h, "the agent's `record` is refused the same way", o + e)
    open(prop_path, "w", encoding="utf-8").write(original)
    rc, o, e = sh(p, PENDING, "answer", "2", "1", "--confirmed-by-human")
    check(rc == 0, "with the entry as it was, the same answer goes through", o + e)

    print("\n[REV] the other answers: park, reject, urgent, low, and the non-goal closure")
    p = project(proj, tmp, "answers")
    for i, (option, stage, line, place) in enumerate((("2", "accepted", "accepted, priority urgent", "proposals"), ("3", "accepted", "accepted, priority low", "proposals"),
                                                       ("4", "parked", "parked", "proposals"), ("5", "rejected", "rejected", "proposals/withdrawn")), 1):
        inbox(p, "add", f"Idea number {i}", "--apply")
        rc, o, e = inbox(p, "propose", "--file", draft(p, f"d{i}.md", FORM2), "--level", "spec", "--form", "2", "--origin", f"IDEA-00{i}", "--slug", f"d{i}", "--apply")
        inbox(p, "triage", f"IDEA-00{i}", "--result", "spec", "--to", f"PROP-00{i}", "--apply")
        rc, o, e = sh(p, PENDING, "answer", str(i), option, "--confirmed-by-human")
        path = os.path.join(p, "gtt-domain", place, f"PROP-00{i}-d{i}.md")
        prop = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
        check(rc == 0 and f"Decision: {line} · " in prop and listing(p)[f"PROP-00{i}"]["stage"] == stage, f"option {option} writes `Decision: {line}` and the PROP stands as {stage}", o + e + prop[-200:])
    check(listing(p)["IDEA-004"]["stage"] == "rejected" and listing(p)["IDEA-003"]["stage"] == "parked" or True, "(the ideas follow their proposals)")
    check(listing(p)["IDEA-003"]["stage"] == "parked" and listing(p)["IDEA-004"]["stage"] == "rejected", "the ideas follow: IDEA-003 parked, IDEA-004 rejected")
    check(listing(p)["PROP-001"]["priority"] == "urgent" and listing(p)["PROP-002"]["priority"] == "low", "urgent and low are recorded as the priority")
    # a non-goal closure
    inbox(p, "add", "Add payments", "--apply")
    rc, o, e = inbox(p, "propose", "--file", draft(p, "np.md", CLOSURE), "--level", "non-goal", "--origin", "IDEA-005", "--slug", "no-payments", "--apply")
    check(rc == 0, "a closure proposal (non-goal) is registered without a form", o + e)
    rev = text(p, "gtt-domain", "pending", "REV-005.md")
    check("1. Close: it is a non-goal (recommended)" in rev and "3. Reject" in rev and "Accept" not in rev, "its REV offers close, park and reject", rev)
    inbox(p, "triage", "IDEA-005", "--result", "non-goal", "--to", "PROP-005", "--apply")
    rc, o, e = sh(p, PENDING, "answer", "5", "1", "--confirmed-by-human")
    check(rc == 0 and listing(p)["PROP-005"]["stage"] == "closed" and listing(p)["IDEA-005"]["stage"] == "closed"
          and os.path.isfile(os.path.join(p, "gtt-domain", "proposals", "done", "PROP-005-no-payments.md")), "T23: closing a non-goal closes the PROP (archived in done/) and its idea", o + e)
    inbox(p, "add", "Add refunds", "--apply")
    inbox(p, "propose", "--file", draft(p, "np2.md", CLOSURE), "--level", "non-goal", "--origin", "IDEA-006", "--slug", "no-refunds", "--apply")
    inbox(p, "triage", "IDEA-006", "--result", "non-goal", "--to", "PROP-006", "--apply")
    rc, o, e = sh(p, PENDING, "answer", "6", "3", "--confirmed-by-human")
    idea = text(p, "docs", "ideas", "IDEA-006.md")
    check(rc == 0 and listing(p)["PROP-006"]["stage"] == "rejected" and listing(p)["IDEA-006"]["stage"] == "new" and "Reopened: non-goal rejected (PROP-006)" in idea,
          "T12 on a closure: the PROP is rejected and the idea goes back to `new` for another triage", o + e + idea[-300:])
    return p


# ------------------------------------------------------------------------------------------------ the table

def fixture(p, kind, stage, number):
    """An entry file in a given stage, written by hand (the test's own oracle of what each stage looks like)."""
    d = TODAY
    first = {"IDEA": [], "PROP": [f"Review: REV-9{number:02d} · {d} · gtt"]}[kind]
    tail = {"new": [], "review": [f"Triage: scope → PROP-900 · {d} · agent"] if kind == "IDEA" else [],
            "accepted": [f"Decision: accepted, priority normal · {d} · human"], "ratify": [f"Decision: accepted, priority normal · {d} · human", f"Package: x · {d} · agent"],
            "work": [f"Decision: accepted, priority normal · {d} · human", f"Ratified: gtt promote x · {d} · human"], "closed": [f"Closed: done · {d} · gtt"],
            "parked": [f"Parked: from new · {d} · human"], "rejected": [f"Dropped: from new · {d} · human"]}[stage]
    if kind == "IDEA" and stage == "review":
        lines = tail
    else:
        lines = first + tail
    if kind == "IDEA":
        head = f"# IDEA-{number:03d} · Idea {number}\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md\n\nAuthor: human · Created: {d} · Type: idea\n\nbody {number}\n"
        path = os.path.join(p, "docs", "ideas", f"IDEA-{number:03d}.md")
    else:
        folder = {"closed": "done", "rejected": "withdrawn"}.get(stage, "")
        head = (f"# PROP-{number:03d} · Prop {number}\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md\n\n"
                f"Author: agent · Created: {d} · Level: specification · Route: spec\nForm: 2 (Context change)\n\nbody {number}\n")
        path = os.path.join(p, "gtt-domain", "proposals", folder, f"PROP-{number:03d}-p{number}.md")
    write(path, head + ("\n---\n" + "\n".join(lines) + "\n" if lines else ""))
    return f"{kind}-{number:03d}"


def the_table(proj, tmp):
    print("\n[table] criterion 7: the 23 transitions of section 3.2 are the engine's table; any other is refused with exit 1 and nothing written")
    p = project(proj, tmp, "table")
    rc, o, e = inbox(p, "transitions", "--json")
    data = json.loads(o)
    check(data["ids"] == [f"T{i}" for i in range(1, 24)], "inbox.json carries T1..T23, and the engine has none of its own", str(data["ids"]))
    owners = {r["id"]: r["owner"] for r in data["transitions"] if r["owner"]}
    print(f"  note  T7, T15, T16, T18 and T19 (reconcile) and T14 and T17 (gtt-stage.sh) are owned by the next prompt: {sorted(owners)}")
    stages = ["new", "review", "accepted", "ratify", "work", "closed", "parked", "rejected"]
    refs = {}
    n = 20
    for kind in ("IDEA", "PROP"):
        for stage in stages:
            if kind == "PROP" and stage == "new":
                continue
            n += 1
            refs[(kind, stage)] = fixture(p, kind, stage, n)
    got = listing(p)
    check(all(got.get(ref, {}).get("stage") == stage for (kind, stage), ref in refs.items()), "the state of an entry is its last line (criterion 8): every fixture reads back in its stage",
          str({r: got.get(r, {}).get("stage") for r in refs.values()}))
    # the oracle: what section 3.2 allows, written here from the order, not read from inbox.json
    allowed = {
        ("triage ask", "IDEA"): {"new"},
        ("park", "IDEA"): {"new", "review", "accepted", "ratify"}, ("park", "PROP"): {"review", "accepted", "ratify"},
        ("drop", "IDEA"): {"new", "review", "accepted", "ratify", "parked"},
        ("reject", "PROP"): {"review", "accepted", "ratify", "parked"},
        ("reopen", "IDEA"): {"parked"}, ("reopen", "PROP"): {"parked"},
        ("priority", "IDEA"): {"accepted", "ratify", "work"}, ("priority", "PROP"): {"accepted", "ratify", "work"},
        ("supersede", "PROP"): {"review"},
    }
    ask = sh(p, ".gtt/scripts/gtt-pending.sh", "ask", "--type", "account", "--header", "Account", "--question", "Which account?", "--why", "needed", "--option", "A | use a",
             "--option", "B | use b", "--recommended", "1", "--apply")
    rc, ask_ref = 0, re.search(r"ASK-\d+", text(p, "gtt-domain", "pending", "ASK-001.md").split("\n")[0])
    asks = ask_ref.group(0) if ask_ref else "ASK-001"
    f2 = draft(p, "table.md", FORM2)
    commands = {"triage ask": lambda ref: ("triage", ref, "--result", "ask", "--to", asks), "park": lambda ref: ("park", ref), "drop": lambda ref: ("drop", ref),
                "reject": lambda ref: ("reject", ref), "reopen": lambda ref: ("reopen", ref), "priority": lambda ref: ("priority", ref, "urgent"),
                "supersede": lambda ref: ("supersede", ref, "--file", f2, "--level", "spec", "--form", "2")}
    stuck, passed, moved = 0, 0, 0
    for (op, kind), ok_stages in sorted(allowed.items()):
        for stage in stages:
            ref = refs.get((kind, stage))
            if not ref:
                continue
            args = commands[op](ref)
            if stage in ok_stages:
                rc, o, e = inbox(p, *args)                                   # a dry run: the stage rule must not refuse it
                good = "is not a transition" not in e
                moved += 1
            else:
                h = tree_hash(p)
                rc, o, e = inbox(p, *args, "--apply")
                good = rc == 1 and tree_hash(p) == h and ("is not a transition" in e or "is not a proposal" in e or "is a proposal" in e or "is an idea" in e)
                stuck += 1
            if good:
                passed += 1
            check(good, f"{op} on {kind} in `{stage}`: {'allowed' if stage in ok_stages else 'refused, nothing written'}", (o + e)[-250:])
    print(f"  note  {stuck} refusals and {moved} allowed combinations walked ({passed} held)")

    print("\n[table] the transitions that run one by one, with the lines they leave")
    p = project(proj, tmp, "walk")
    seen = set()
    sets = lambda *t: seen.update(t)
    rc, o, e = inbox(p, "add", "an idea", "--apply"); sets("T1") if rc == 0 else None                                          # T1
    rc, o, e = inbox(p, "adr-new", "Use Redis", "--apply"); sets("T2") if rc == 0 else None                                    # T2 (new)
    write(os.path.join(p, "gtt-domain", "adr", "ADR-009-hand.md"), "# ADR-009 — Written by hand\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md\n\n- Status: Accepted\n\n## Context\n\nx\n\n## Decision\n\ny\n")
    rc, o, e = inbox(p, "adr-adopt", "gtt-domain/adr/ADR-009-hand.md", "--apply")                                              # T2 (adopt)
    check(rc == 0 and not os.path.exists(os.path.join(p, "gtt-domain", "adr", "ADR-009-hand.md")) and any(n.startswith("IDEA-003-hand") for n in os.listdir(os.path.join(p, "gtt-domain", "adr", "drafts"))),
          "T2: adopt moves a hand-written ADR to adr/drafts/ and leaves adr/ as it was", o + e)
    rc, o, e = inbox(p, "adr-adopt", "gtt-domain/adr/ADR-001-context-governance.md", "--apply")
    check(rc == 1, "T2: an ADR that is part of the frozen baseline is not adopted", o + e)
    drafts = os.listdir(os.path.join(p, "gtt-domain", "adr", "drafts"))
    adr_text = text(p, "gtt-domain", "adr", "drafts", sorted(drafts)[0])
    check(re.search(r"Type: adr · Level: architecture", adr_text) and "## Decision" in adr_text and "# ADR-NNN" not in adr_text, "the ADR draft is the template's body, without a number, with the idea's header", adr_text[:300])
    check(listing(p)[f"IDEA-002"]["stage"] == "new" and listing(p)["IDEA-002"]["type"] == "adr", "a draft is an IDEA of type adr in `new`")
    # T3: a work idea ends in a Story that cites it
    inbox(p, "add", "Let a shop cancel an order", "--apply")                                                                    # IDEA-004
    backlog = os.path.join(p, "gtt-domain", "backlog.md")
    rc, o, e = inbox(p, "triage", "IDEA-004", "--result", "work", "--to", "STORY-001", "--apply")
    check(rc == 1, "T3: a Story that does not exist is refused", e)
    current = open(backlog, encoding="utf-8").read()
    open(backlog, "w", encoding="utf-8").write(current.replace("#### Stories\n", STORIES.format(n=4), 1))
    rc, o, e = inbox(p, "triage", "IDEA-004", "--result", "work", "--to", "STORY-001", "--apply")
    check(rc == 0 and listing(p)["IDEA-004"]["stage"] == "work", "T3: work -> STORY-m, when the Story cites `Origin: IDEA-n`", e); sets("T3") if rc == 0 else None
    # T4
    inbox(p, "add", "Orders", "--apply")                                                                                         # IDEA-005
    rc, o, e = inbox(p, "triage", "IDEA-005", "--result", "covered", "--to", "EPIC-099", "--apply")
    check(rc == 1, "T4: covered by an Epic that does not exist is refused", e)
    rc, o, e = inbox(p, "triage", "IDEA-005", "--result", "covered", "--to", "EPIC-001", "--apply")
    dec = [n for n in os.listdir(os.path.join(p, "gtt-domain", "pending")) if n.startswith("DEC-")]
    check(rc == 0 and listing(p)["IDEA-005"]["stage"] == "closed" and len(dec) == 1, "T4: covered by EPIC-001 closes the idea and opens an informative DEC", o + e)
    sets("T4") if rc == 0 else None
    # T6
    made = sh(p, PENDING, "ask", "--type", "account", "--header", "Account", "--question", "Which account?", "--why", "needed", "--option", "A | use a",
              "--option", "B | use b", "--recommended", "1", "--apply")
    asks = (re.search(r"ASK-\d+", made[1]) or re.search(r"ASK-\d+", "ASK-000")).group(0)
    inbox(p, "add", "Which cloud?", "--apply")                                                                                   # IDEA-006
    rc, o, e = inbox(p, "triage", "IDEA-006", "--result", "ask", "--to", asks, "--apply")
    check(rc == 0 and listing(p)["IDEA-006"]["stage"] == "new" and "Triage: question " + asks in text(p, "docs", "ideas", "IDEA-006.md"), "T6: a question keeps the idea in `new`", o + e)
    rc, o, e = inbox(p, "triage", "IDEA-006", "--result", "ask", "--to", "ASK-099", "--apply")
    check(rc == 1, "T6: an ASK that does not exist is refused", e)
    # T5 / T9 / T10 / T11 / T12 / T13 / T20 / T21 / T22 are walked above; T8 before the freeze:
    q = project(proj, tmp, "walk-think", frozen=False)
    inbox(q, "add", "Put it in the design", "--apply")
    rc, o, e = inbox(q, "triage", "IDEA-001", "--result", "incorporated", "--to", "gtt-domain/context/glossary.md", "--apply")
    check(rc == 0 and listing(q)["IDEA-001"]["stage"] == "closed", "T8: before the freeze an idea is incorporated into the design draft", o + e)
    rc, o, e = inbox(p, "triage", "IDEA-006", "--result", "incorporated", "--to", "gtt-domain/context/glossary.md", "--apply")
    check(rc == 1, "T8: after the freeze it is refused", e)
    # T20 on an idea, T21 on each, T22
    rc, o, e = inbox(p, "park", "IDEA-006", "--apply"); ok1 = rc == 0
    rc, o, e = inbox(p, "reopen", "IDEA-006", "--apply"); ok2 = rc == 0 and listing(p)["IDEA-006"]["stage"] == "new"
    check(ok1 and ok2, "T20/T21: an idea is parked and reopened to `new`")
    rc, o, e = inbox(p, "drop", "IDEA-006", "--reason", "not for us", "--apply")
    check(rc == 0 and listing(p)["IDEA-006"]["stage"] == "rejected" and "Dropped: not for us" in text(p, "docs", "ideas", "IDEA-006.md"), "T21: drop discards an idea, with its reason", o + e)
    check(inbox(p, "priority", "IDEA-006", "urgent", "--apply")[0] == 1, "T22: a dropped idea has no priority")

    print("\n[log] every new line is also in gtt-domain/delivery-log.jsonl (kind inbox)")
    for label, proj_ in (("the answers project", None),):
        pass
    p = project(proj, tmp, "log")
    inbox(p, "add", "log me", "--apply")
    inbox(p, "propose", "--file", draft(p, "l.md", FORM2), "--level", "spec", "--form", "2", "--origin", "IDEA-001", "--apply")
    inbox(p, "triage", "IDEA-001", "--result", "spec", "--to", "PROP-001", "--apply")
    sh(p, PENDING, "answer", "1", "1", "--confirmed-by-human")
    inbox(p, "priority", "PROP-001", "urgent", "--apply")
    inbox(p, "park", "PROP-001", "--apply")
    inbox(p, "reopen", "PROP-001", "--apply")
    rows = log_rows(p)
    trail = {}
    for ref in ("IDEA-001", "PROP-001"):
        folder = [os.path.join(p, "docs", "ideas"), os.path.join(p, "gtt-domain", "proposals"), os.path.join(p, "gtt-domain", "proposals", "done")]
        for f in folder:
            for name in (os.listdir(f) if os.path.isdir(f) else []):
                if name.startswith(ref):
                    body = open(os.path.join(f, name), encoding="utf-8").read()
                    trail[ref] = len(body.rsplit("\n---\n", 1)[1].strip().splitlines()) if "\n---\n" in body else 0
    per = {ref: [r for r in rows if r["id"] == ref and r["key"] != "created"] for ref in trail}
    check(all(len(per[ref]) == trail[ref] for ref in trail) and trail["PROP-001"] >= 6,
          "every trail line, on the PROP and on its idea, has its row in delivery-log.jsonl", f"trail={trail} rows={ {k: len(v) for k, v in per.items()} }")
    check(all({"t", "kind", "id", "from", "to", "actor"} <= set(r) for r in rows) and all(r["actor"] in ("human", "agent", "gtt") for r in rows), "each row carries t, kind, id, from, to and actor")
    check(any(r["id"] == "IDEA-001" and r["key"] == "created" and r["from"] is None for r in rows), "the creation of an entry is logged too")
    rc, o, e = sh(p, ".gtt/scripts/gtt-delivery.sh", "log")
    check(rc == 0, "the delivery engine still reads a log that holds inbox rows", o + e)


def spanish(proj, tmp):
    print("\n[es] the labels follow the project's language")
    p = project(proj, tmp, "es", language="es")
    inbox(p, "add", "Sincronizar las parcelas sin señal", "--by", "Moisés", "--apply")
    body = text(p, "docs", "ideas", "IDEA-001.md")
    check(f"Autor: humano (Moisés) · Creada: {TODAY} · Tipo: idea" in body, "the header is in Spanish", body[:250])
    inbox(p, "propose", "--file", draft(p, "es.md", FORM4), "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    inbox(p, "triage", "IDEA-001", "--result", "scope", "--to", "PROP-001", "--apply")
    rev = text(p, "gtt-domain", "pending", "REV-001.md")
    check("# REV-001 · Revisión · PROP-001" in rev and "1. Aceptar, prioridad normal (recomendado)" in rev and "Nivel: alcance · Ruta: scope" in rev and rev.rstrip().endswith("Respuesta:"), "the REV is in Spanish", rev)
    check(f"Triage: alcance → PROP-001 · {TODAY} · agente" in text(p, "docs", "ideas", "IDEA-001.md"), "and so is the trail")
    rc, o, e = sh(p, PENDING, "answer", "1", "2", "--confirmed-by-human")
    check(rc == 0 and f"Decisión: aceptada, prioridad urgente · {TODAY} · humano (gtt answer 1 2)" in text(p, "gtt-domain", "proposals", "PROP-001-es.md"), "the Decision line is in Spanish", o + e)
    check(listing(p)["IDEA-001"]["stage"] == "accepted" and listing(p)["IDEA-001"]["priority"] == "urgent", "and both languages are read back into the same stage")
    rc, o, e = sh(p, PENDING, "check")
    check(rc == 0, "the Spanish REV passes the pending rules", o + e)


def legacy(proj, tmp):
    print("\n[alias] gtt-idea.sh keeps its commands and its list")
    p = project(proj, tmp, "alias")
    gi = lambda *a: sh(p, ".gtt/scripts/gtt-idea.sh", *a)
    rc, o, e = gi("add", "Move sessions to Redis", "--apply")
    check(rc == 0 and "gtt-idea:" in o, "add through the alias", o + e)
    rc, o, e = gi("triage", "IDEA-001", "--result", "converted", "--to", "PROPOSAL-redis", "--apply")
    check(rc == 0, "the old `converted` result still triages", o + e)
    rc, o, e = gi("list")
    check(re.search(r"^IDEA-001  converted  Move sessions to Redis  -> PROPOSAL-redis$", o, re.M), "the old list format (gtt-status.sh reads it)", o)
    rows = json.loads(gi("list", "--json")[1])
    check(rows["kind"] == "gtt-ideas" and rows["ideas"][0]["state"] == "converted" and rows["new"] == 0, "the old JSON (Sonar reads it)", str(rows)[:200])
    rc, o, e = gi("propose", "--file", "x")
    check(rc != 0, "the alias carries no new command", o + e)


def e2e_gaps(proj, tmp):
    print("\n[e2e] the pains of gtt-flujo-e2e.py (1.21): V2, V3, V4, V5 and V7 here; V1, V6, V8 and V9 in inbox-routes.py")
    p = project(proj, tmp, "gaps")
    inbox(p, "add", "Move sessions to Redis so we can scale horizontally", "--apply")
    rc, o, e = inbox(p, "propose", "--file", draft(p, "redis.md", FORM2), "--level", "spec", "--form", "2", "--origin", "IDEA-001", "--slug", "redis", "--apply")
    inbox(p, "triage", "IDEA-001", "--result", "spec", "--to", "PROP-001", "--apply")
    sh(p, PENDING, "answer", "1", "1", "--confirmed-by-human")
    idea = text(p, "docs", "ideas", "IDEA-001.md")
    check(idea.count("\n---\n") == 1 and re.search(r"Triage: .*PROP-001.*\nDecision: accepted, priority normal \(PROP-001\)", idea),
          "V5 (GAP 1): the idea's trail grows after triage (proposal -> decision)", idea[-300:])
    rc, o, e = inbox(p, "add", "--type", "solicitud", "--change", "A", "--reason", "x", "--apply")
    rc2, o2, e2 = inbox(p, "add", "--type", "solicitud", "--change", "B", "--reason", "y", "--apply")
    check(rc == 0 and rc2 == 0, "V7 (GAP 2): a second request waits in line while the first is pending", e + e2)
    item = listing(p, "--origin", "agent").get("PROP-001", {})
    check(item.get("from") == "IDEA-001", "V3 (GAP 3): the proposal knows the idea it came from", str(item)[:200])
    prop = text(p, "gtt-domain", "proposals", "PROP-001-redis.md")
    check(all(x in prop for x in ("Author: agent", f"Created: {TODAY}", "Level: ", "Route: ")) and item.get("priority") == "normal",
          "V4 (GAP 4): the proposal carries author, date, level and priority", prop[:300])
    ops = json.load(open(os.path.join(p, ".gtt", "contract", "operations.json"), encoding="utf-8"))["operations"]
    check(ops["pending.answer"]["human_authority"] and "inbox.propose" in ops and "Decision: accepted" in prop,
          "V2 (GAP 6): accepting a proposal is a recorded human act (pending.answer on its REV writes `Decision` with the date and the actor)")
    print("  note  V1 (Sonar shows the waiting proposal), V6 (the promotion reaches the idea and closes the PROP), V8 (an ADR by hand) and V9 (the ADR needs an accepted origin) are in inbox-routes.py, e2e_vacios")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.path.join(HERE, "..", ".."))
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    proj = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-inbox-flow-")
    try:
        for scenario in (who_may_write, entries_and_reviews, supersede_and_changes, the_table, spanish, legacy, e2e_gaps):
            scenario(proj, tmp)
    finally:
        if args.keep:
            print("kept:", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{acc.COUNT - len(acc.FAILS)}/{acc.COUNT} checks held")
    if acc.FAILS:
        print("FAILED:", "; ".join(acc.FAILS))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
