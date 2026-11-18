#!/usr/bin/env python3
"""GTT inbox routes: from an accepted entry to its registry, through the package, the human's command and `reconcile`.

The second half of the change-flow order's acceptance (GTT-ORDEN-flujo-de-cambios section 18), on disposable copies of the
project: the engine, the hooks and the protection are the real ones; only the human's typing is replaced by the scripts' own
confirmation flags. inbox-flow.py owns the entry, the REV and the table of section 3.2; this file owns what comes after.

   5  `gtt adr new` writes the draft in adr/drafts/; writing it does not raise GTT-GOVERNED, and the digest ignores it
   6  an ADR written by hand in adr/ gives `adr-hand` (GTT-ADR-HAND, NOTICE) with `gtt adr adopt`; adopting it clears the signal;
      a hand change to context/ or to an ADR that exists is still GTT-GOVERNED BLOCKING
   7  the transitions that `reconcile` and `gtt-stage.sh` own (T7, T14 to T19), each walked once; any other refused (inbox-flow.py)
   8  `reconcile` run twice writes nothing the second time; every entry's state is its last line
  13  R1: a work idea ends in a Story with `Origin`, with no REV, and closes when the Story is Done
  14  R2: a scope proposal leaves the Epic `Proposed` and a RUN; `gtt run` promotes and approves; the Epic is `Planned` in its place
  15  R3: a specification proposal ends as CHANGE-... with (PROP-n) in the map
  16  R4: an architecture proposal ends as ADR-NNN with `Origin` and a new freeze
  17  `gtt-stage.sh` refuses a set that touches context or an ADR without an accepted `--origin`; an AGENTS.md-only set is armed
  18  on ratifying, the proposal goes to `work` or `closed` and is archived when closed; the idea shows every step
  19  R5 and R6: parking or rejecting outside the REV archives the set; `gtt undo` brings the entry back to `accepted`
  20  urgent, normal and low order the backlog (5.7); what is low stays out of the estimated date
  23  Team: `gtt-roles`, `For:` in the REV, `roles: strict`, and a draft by someone who is not the architect opens a REV

  python3 .gtt/tests/inbox-routes.py [--project .] [--keep]
Exit 0 = every check held, 1 = at least one failed.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("inbox_flow", os.path.join(HERE, "inbox-flow.py"))
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)
acc, check, write, tree_hash = flow.acc, flow.check, flow.write, flow.tree_hash
sh, inbox, text, listing, py, TODAY = flow.sh, flow.inbox, flow.text, flow.listing, flow.py, flow.TODAY
CANON = "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md"


def draft(p, name, body):
    """A draft of the agent under proposals/drafts/: it carries the canonical line, as the markdown gate of every freeze asks."""
    first, _, rest = body.partition("\n")
    return flow.draft(p, name, f"{first}\n\n{CANON}\n{rest}")
FORM2, FORM4, PENDING = flow.FORM2, flow.FORM4, flow.PENDING

STAGE = ".gtt/scripts/gtt-stage.sh"
PROMOTE = ".gtt/scripts/gtt-promote.sh"
RECONCILE = (INBOX := flow.INBOX)
FORM1 = """Proposed Architecture Change

Current decision: sessions live in memory
Suggested change: sessions live in Redis
Reason: horizontal scaling
Impact: one new service
Risk: operational
Affected files: gtt-domain/context/architecture.md
Alternatives considered: sticky sessions
"""
FORM4_X = FORM4.replace("Epic ID: new", "Epic ID: new")
SPEC = """# Product spec

## 1. Overview

Shops sell things and take orders.

## 2. Parcels

### 2.1 Sync

A parcel is synced when the signal returns. An unsynced parcel is never lost.
"""
DESIGN = """# EPIC-003 — Parcels · Solution design

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

**Epic:** gtt-domain/backlog.md → EPIC-003 · **Status:** Draft
**Follows:** architecture.md

## 1. Purpose and scope

Syncing parcels.

**Source sections:** D:§2.1

## 2. Data

A parcel is synced when the signal returns. [FUENTE: D:§2.1]

## 3. Rules

- **R-1** An unsynced parcel is never lost. [FUENTE: D:§2.1]

## 4. Flows

- **F-1** Sync: when the signal returns, the queue is sent. [FUENTE: D:§2.1]

## 5. Interfaces

- **I-1** `POST /parcels/sync`. (D-1)

## 6. Examples

- **E-1** (R-1, F-1) Given an unsynced parcel, when the signal returns, then it is sent. [FUENTE: D:§2.1]

## 7. Open points

N/A — the sources define everything this Epic needs.

## 8. Decisions taken with the human

- **D-1** Which interface? → HTTP, as above — Ana — 2026-10-08
"""
ADR_TEXT = """# ADR-002 — Sessions in Redis

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

- Status: Accepted
- Date: 2026-11-13
- Approved by: Ana
- Supersedes:
- Origin: <PROP-NNN or IDEA-NNN that led to this decision, if any>

## Context

Sessions must survive a restart.

## Decision

Sessions live in Redis.

## Consequences

One more service to run.
"""
STORY = "\n##### STORY-0{n} — {title}\n- **Status:** {status}\n{extra}- **Implements:** design/EPIC-001#R-1\n- **Done when:** tests/x.py\n"


def rewrite(path, fn):
    """Read the file first, then write what `fn` makes of it (opening for write truncates)."""
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(fn(content))


def p_sh(p, *argv, stdin=None):
    return sh(p, *argv, stdin=stdin)


def project(proj, tmp, name, frozen=True, language=None, profile=None, with_source=False):
    """Like inbox-flow's project(), with the stack map's change log and, optionally, a source `D` for designs."""
    def before(p):
        with open(os.path.join(p, "gtt-domain", "context", "stack.md"), "a", encoding="utf-8") as handle:
            handle.write("\n## 6. Map change log\n\n| Date | ADR or CHANGE | What changed |\n|---|---|---|\n| | | |\n")
        backlog = os.path.join(p, "gtt-domain", "backlog.md")
        template = open(backlog, encoding="utf-8").read()
        example = template[template.index("### EPIC-001 — <Epic title (example)>"):template.index("## General Development Work")]
        write(backlog, template.replace(example, "") + acc.EPICS)
        meta = {}
        if language:
            meta["language"] = language
        if meta:
            write(os.path.join(p, ".gtt", "methodology.json"), json.dumps(meta))
        if with_source:
            write(os.path.join(p, "spec.md"), SPEC)
            acc.bash(p, ".gtt/scripts/gtt-source.sh", "add", "spec.md", "--id", "D", "--apply")
    if frozen:
        p, rc, out = acc.frozen_project(proj, tmp, name, before_freeze=before)
        check(rc == 0, f"{name}: a frozen test project is created", out[-300:])
    else:
        p = acc.fresh(proj, tmp, name)
        before(p)
    acc.place_claude_hook(proj, p)
    write(os.path.join(p, ".gtt", "ade.json"), "{}\n")
    if profile:             # chosen after the freeze: the Team profile's own freeze gates are not what these checks are about
        path = os.path.join(p, ".gtt", "methodology.json")
        meta = json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else {}
        meta["profile"] = profile
        write(path, json.dumps(meta))
    return p


def observe(p):
    rc, out, err = sh(p, ".gtt/scripts/gtt-observe.sh", "check", "--json")
    try:
        items = json.loads(out)
    except ValueError:
        return {}
    rows = items.get("signals") or items.get("items") or items.get("pending") or []
    if isinstance(items, dict) and not rows:
        for value in items.values():
            if isinstance(value, list) and value and isinstance(value[0], dict) and "rule" in value[0]:
                rows = value
    return {r["rule"]: r for r in rows}


def accepted(p, level, form, body, idea_text, option="1", slug=None, number=None):
    """An idea, its proposal and the human's answer: returns (idea ref, prop ref)."""
    rc, o, e = inbox(p, "add", idea_text, "--apply")
    idea = re.search(r"IDEA-\d+", o).group(0)
    name = slug or f"p{idea[-3:]}"
    rc, o, e = inbox(p, "propose", "--file", draft(p, name + ".md", body), "--level", level, "--form", form, "--origin", idea, "--slug", name, "--apply")
    rev = int(re.search(r"REV-(\d+)", o).group(1))
    prop = re.search(r"proposals/(PROP-\d+)", o).group(1)
    inbox(p, "triage", idea, "--result", level, "--to", prop, "--apply")
    rc, o, e = sh(p, PENDING, "answer", str(rev), option, "--confirmed-by-human")
    check(rc == 0, f"{idea}/{prop} accepted ({level})", o + e)
    return idea, prop


def stage(p, name, origin, *pairs, reason="a change"):
    args = [STAGE, name, "--reason", reason]
    if origin:
        args += ["--origin", origin]
    return sh(p, *args, *pairs)


def promote(p, name):
    proc = subprocess.run(["bash", PROMOTE, name], cwd=p, input="apply\n", capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout, proc.stderr


def reconcile(p, *flags):
    return sh(p, INBOX, "reconcile", *flags)


def stage_of(p, ref):
    return listing(p).get(ref, {}).get("stage")


def trail(p, ref):
    row = listing(p).get(ref)
    return [f"{l['key']}: {l['value']}" for l in (row or {}).get("trail", [])]


def entry_text(p, ref):
    row = listing(p).get(ref)
    return open(os.path.join(p, row["path"]), encoding="utf-8").read() if row else ""


def backlog_path(p):
    return os.path.join(p, "gtt-domain", "backlog.md")


# ------------------------------------------------------------------------------------------------ 5 and 6

def drafts_and_hand_adrs(proj, tmp):
    print("\n[F4/F5] criteria 5 and 6: the architect's drafts are not governed state; a hand-written ADR is a notice, not a block")
    p = project(proj, tmp, "hand")
    digest = lambda: sh(p, ".gtt/scripts/gtt-observe.sh", "digest")[1].strip()
    before = digest()
    rc, o, e = inbox(p, "adr-new", "Use Redis", "--apply")
    check(rc == 0 and os.path.isfile(os.path.join(p, "gtt-domain", "adr", "drafts", "IDEA-001-use-redis.md")), "criterion 5: `adr new` writes the draft in adr/drafts/", o + e)
    check(digest() == before, "criterion 5: the governed digest ignores adr/drafts/", digest())
    check("GTT-GOVERNED" not in observe(p) and "GTT-ADR-HAND" not in observe(p), "criterion 5: writing a draft raises no GTT-GOVERNED")
    deny = lambda kind, target: acc.claude_decides(p, kind, target)[0]
    check(deny("file", "gtt-domain/adr/drafts/IDEA-001-use-redis.md") and deny("shell", "echo x >> gtt-domain/adr/drafts/IDEA-001-use-redis.md"),
          "criterion 5: the agent cannot write the draft, before or after the freeze (tool and shell)")
    write(os.path.join(p, "gtt-domain", "adr", "ADR-002-hand.md"), ADR_TEXT.replace("Origin: <PROP-NNN or IDEA-NNN that led to this decision, if any>", "Origin:"))
    sig = observe(p)
    check("GTT-ADR-HAND" in sig and sig["GTT-ADR-HAND"]["level"] == "NOTICE" and sig["GTT-ADR-HAND"].get("command", "").startswith("gtt adr adopt gtt-domain/adr/ADR-002-hand.md")
          and "GTT-GOVERNED" not in sig, "criterion 6: a new ADR written by hand gives GTT-ADR-HAND (NOTICE) with `gtt adr adopt`, and not GTT-GOVERNED", str(sig)[:400])
    rc, o, e = inbox(p, "adr-hand", "--json")
    found = json.loads(o)["adrs"] if rc == 0 else []
    check(len(found) == 1 and found[0]["command"] == "gtt adr adopt gtt-domain/adr/ADR-002-hand.md", "criterion 6: `adr-hand` (the function Sonar calls) lists it with its command", o + e)
    rc, o, e = inbox(p, "adr-adopt", "gtt-domain/adr/ADR-002-hand.md", "--apply")
    check(rc == 0 and not os.path.exists(os.path.join(p, "gtt-domain", "adr", "ADR-002-hand.md")), "criterion 6: adopt moves it to drafts/", o + e)
    sig = observe(p)
    check("GTT-ADR-HAND" not in sig and "GTT-GOVERNED" not in sig and not json.loads(inbox(p, "adr-hand", "--json")[1])["adrs"],
          "criterion 6: the signal is gone and adr/ stands as it did at the freeze", str(sig)[:300])
    # what is part of the design keeps its old rule
    ctx = os.path.join(p, "gtt-domain", "context", "glossary.md")
    original = open(ctx, encoding="utf-8").read()
    write(ctx, original + "by hand\n")
    sig = observe(p)
    check("GTT-GOVERNED" in sig and sig["GTT-GOVERNED"]["level"] == "BLOCKING", "a hand change to context/ is still GTT-GOVERNED BLOCKING", str(sig)[:300])
    write(ctx, original)
    adr1 = os.path.join(p, "gtt-domain", "adr", "ADR-001-context-governance.md")
    original = open(adr1, encoding="utf-8").read()
    write(adr1, original + "\nedited by hand\n")
    sig = observe(p)
    check("GTT-GOVERNED" in sig and sig["GTT-GOVERNED"]["level"] == "BLOCKING" and "GTT-ADR-HAND" not in sig, "and so is a change to an ADR that already exists", str(sig)[:300])
    write(adr1, original)
    # a hand ADR AND a hand change to the context: both are said, the block stays
    write(os.path.join(p, "gtt-domain", "adr", "ADR-003-hand2.md"), ADR_TEXT.replace("ADR-002", "ADR-003"))
    write(ctx, open(ctx, encoding="utf-8").read() + "by hand\n")
    sig = observe(p)
    check("GTT-ADR-HAND" in sig and "GTT-GOVERNED" in sig, "a hand ADR next to a hand change to the context: the notice and the block both stand", str(list(sig)))
    # an ADR that came from a promotion is not a hand ADR
    q = project(proj, tmp, "hand-promoted")
    idea, prop = accepted(q, "arch", "1", FORM1, "Sessions in Redis")
    write(os.path.join(q, "gtt-domain", "proposals", "drafts", "adr.md"), ADR_TEXT)
    write(os.path.join(q, "gtt-domain", "proposals", "drafts", "arch.md"), open(os.path.join(q, "gtt-domain", "context", "architecture.md"), encoding="utf-8").read() + "redis\n")
    rc, o, e = stage(q, "redis", prop, "gtt-domain/proposals/drafts/adr.md=gtt-domain/adr/ADR-002-sessions-in-redis.md", "gtt-domain/proposals/drafts/arch.md=gtt-domain/context/architecture.md")
    rc, o, e = promote(q, "redis")
    check(rc == 0 and not json.loads(inbox(q, "adr-hand", "--json")[1])["adrs"] and "GTT-ADR-HAND" not in observe(q), "an ADR that came from a promotion is not an ADR written by hand", o + e)


# ------------------------------------------------------------------------------------------------ 17 and the package

def stage_control(proj, tmp):
    print("\n[stage] criterion 17 and 6.5: no package for context or an ADR without an accepted `--origin`")
    p = project(proj, tmp, "stage")
    glossary = os.path.join(p, "gtt-domain", "context", "glossary.md")
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "g.md"), open(glossary, encoding="utf-8").read() + "parcel: a thing\n")
    pair = "gtt-domain/proposals/drafts/g.md=gtt-domain/context/glossary.md"
    h = tree_hash(p)
    rc, o, e = stage(p, "g", None, pair)
    check(rc == 1 and tree_hash(p) == h and "--origin" in e, "criterion 17: without `--origin`, a set that touches context is refused and nothing is written", o + e)
    rc, o, e = stage(p, "g", None, "gtt-domain/proposals/drafts/g.md=gtt-domain/adr/ADR-009-x.md")
    check(rc == 1, "criterion 17: nor a set that adds an ADR", o + e)
    inbox(p, "add", "A glossary term", "--apply")
    rc, o, e = stage(p, "g", "IDEA-001", pair)
    check(rc == 1 and tree_hash(p) == h or rc == 1, "criterion 17: an origin that is only `new` is refused", e)
    rc, o, e = stage(p, "g", "PROP-099", pair)
    check(rc == 1, "an origin that does not exist is refused", e)
    rc, o, e = stage(p, "g", "legacy", pair)
    check(rc == 1, "`legacy` is the migration's word: the agent cannot arm a set with it", e)
    idea, prop = accepted(p, "spec", "2", FORM2, "Add parcel to the glossary")
    write(os.path.join(p, "AGENTS.md"), f"# AGENTS\n\n{CANON}\n\nfixed wording\n")
    rc, o, e = stage(p, "wording", None, "AGENTS.md=AGENTS.md")
    check(rc == 0 and os.path.isfile(os.path.join(p, "gtt-domain", "proposals", "staged", "wording", "promote.json")), "criterion 17: a set of only AGENTS.md is armed without an origin", o + e)
    check("origin" not in json.loads(text(p, "gtt-domain", "proposals", "staged", "wording", "promote.json")), "and records no origin")
    rc, o, e = stage(p, "g", prop, pair, reason="a parcel term")
    meta = json.loads(text(p, "gtt-domain", "proposals", "staged", "g", "promote.json")) if rc == 0 else {}
    check(rc == 0 and meta.get("origin") == prop, "criterion 17: with the accepted `--origin`, the set is armed and promote.json records it", o + e)
    check(stage_of(p, prop) == "ratify" and re.search(rf"\nPackage: g \+ glossary.md · {TODAY} · agent\n", entry_text(p, prop)), "T14: the proposal passes to `ratify` with its `Package:` line", entry_text(p, prop)[-250:])
    check(stage_of(p, idea) == "ratify" and f"Package: g + glossary.md ({prop}) · {TODAY} · agent" in entry_text(p, idea), "and its idea shows the same line, with the proposal's number")
    rc, o, e = stage(p, "g2", prop, pair)
    check(rc == 0 and re.search(r"Package: g2 \(redone\)", entry_text(p, prop)) and stage_of(p, prop) == "ratify", "T17: arming the package again leaves it in `ratify` with `redone`", o + e)
    # a set that already existed before the update has no origin: it still promotes
    old = os.path.join(p, "gtt-domain", "proposals", "staged", "g")
    j = json.load(open(os.path.join(old, "promote.json"), encoding="utf-8"))
    j.pop("origin", None); j["origin"] = "legacy"
    json.dump(j, open(os.path.join(old, "promote.json"), "w", encoding="utf-8"))
    rc, o, e = promote(p, "g")
    check(rc == 0 and "parcel: a thing" in open(glossary, encoding="utf-8").read(), "a set recorded as `legacy` can still be promoted", (o + e)[-300:])


# ------------------------------------------------------------------------------------------------ routes R1 to R4

def route_work(proj, tmp):
    print("\n[R1] criterion 13: a work idea ends in a Story with `Origin`, with no REV, and closes with the Story")
    p = project(proj, tmp, "r1")
    inbox(p, "add", "Let a shop cancel an order", "--apply")
    bl = backlog_path(p)
    body = open(bl, encoding="utf-8").read()
    open(bl, "w", encoding="utf-8").write(body.replace("#### Stories\n", "#### Stories" + STORY.format(n=11, title="Cancel an order", status="Planned", extra="- **Origin:** IDEA-001\n"), 1))
    rc, o, e = inbox(p, "triage", "IDEA-001", "--result", "work", "--to", "STORY-011", "--apply")
    check(rc == 0 and stage_of(p, "IDEA-001") == "work" and not [n for n in os.listdir(os.path.join(p, "gtt-domain", "pending")) if n.startswith("REV")],
          "criterion 13: the idea passes to `work` with no REV", o + e)
    rc, o, e = reconcile(p)
    check(rc == 0 and stage_of(p, "IDEA-001") == "work" and "Work:" not in entry_text(p, "IDEA-001"), "reconcile adds nothing while the Story is open: STORY-011 is already in the Triage line", o + e)
    text_ = open(bl, encoding="utf-8").read()
    open(bl, "w", encoding="utf-8").write(text_.replace("##### STORY-011 — Cancel an order\n- **Status:** Planned", "##### STORY-011 — Cancel an order\n- **Status:** Done"))
    reconcile(p)
    t = entry_text(p, "IDEA-001")
    check(stage_of(p, "IDEA-001") == "closed" and re.search(rf"\nClosed: done · {TODAY} · gtt\n$", t), "T18: the Story is Done and the idea closes as `done`", t[-250:])
    before = tree_hash(p)
    reconcile(p)
    check(tree_hash(p) == before, "criterion 8: a second reconcile writes nothing")
    rows = [r for r in flow.log_rows(p) if r["id"] == "IDEA-001" and r["key"] == "closed"]
    check(len(rows) == 1 and rows[0]["actor"] == "gtt" and rows[0]["to"] == "closed", "the new line is in delivery-log.jsonl as kind inbox", str(rows))
    # a cancelled Story: T19
    inbox(p, "add", "Rename the order", "--apply")
    cur = open(bl, encoding="utf-8").read()
    open(bl, "w", encoding="utf-8").write(cur.replace("#### Stories\n", "#### Stories" + STORY.format(n=12, title="Rename", status="Planned", extra="- **Origin:** IDEA-002\n"), 1))
    inbox(p, "triage", "IDEA-002", "--result", "work", "--to", "STORY-012", "--apply")
    rewrite(bl, lambda t: t.replace("##### STORY-012 — Rename\n- **Status:** Planned", "##### STORY-012 — Rename\n- **Status:** Cancelled"))
    reconcile(p)
    check(stage_of(p, "IDEA-002") == "closed" and "Closed: cancelled" in entry_text(p, "IDEA-002"), "T19: a cancelled Story closes the idea as `cancelled`", entry_text(p, "IDEA-002")[-200:])


def route_spec_and_arch(proj, tmp):
    print("\n[R3] criteria 15 and 18: a specification proposal ends as CHANGE-... with (PROP-n)")
    p = project(proj, tmp, "r3")
    glossary = os.path.join(p, "gtt-domain", "context", "glossary.md")
    idea, prop = accepted(p, "spec", "2", FORM2, "Add parcel to the glossary")
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "g.md"), open(glossary, encoding="utf-8").read() + "parcel: a thing\n")
    rc, o, e = stage(p, "gloss", prop, "gtt-domain/proposals/drafts/g.md=gtt-domain/context/glossary.md", reason="a parcel term")
    check(rc == 0 and stage_of(p, prop) == "ratify", "T14: the agent arms the package", o + e)
    rc, o, e = reconcile(p)
    check(stage_of(p, prop) == "ratify" and "Ratified" not in entry_text(p, prop), "reconcile does not ratify what the human has not promoted", o + e)
    rc, o, e = promote(p, "gloss")
    stack = text(p, "gtt-domain", "context", "stack.md")
    check(rc == 0 and re.search(rf"\| {TODAY} \| CHANGE-\d{{8}}-gloss \| a parcel term \({prop}\) \|", stack),
          f"criterion 15: the promotion is recorded as CHANGE-... and the map row ends in ({prop})", stack[-300:])
    rc, o, e = reconcile(p)
    t = entry_text(p, prop)
    check(stage_of(p, prop) == "work" and re.search(rf"\nRatified: gtt promote gloss · {TODAY} · gtt\n$", t), "T15: the proposal passes to `work` with `Ratified: gtt promote gloss`", t[-300:])
    ti = entry_text(p, idea)
    check(stage_of(p, idea) == "work" and f"Package: gloss + glossary.md ({prop})" in ti and f"Ratified: gtt promote gloss ({prop})" in ti, "criterion 18: the idea shows the package and the ratification", ti[-400:])
    b = tree_hash(p)
    reconcile(p)
    check(tree_hash(p) == b, "criterion 8: reconcile again writes nothing")
    # the agent adds a Story that cites the proposal; the session closes the rest
    bl = backlog_path(p)
    rewrite(bl, lambda t: t.replace("#### Stories\n", "#### Stories" + STORY.format(n=21, title="Show parcels", status="Planned", extra=f"- **Origin:** {prop}\n"), 1))
    reconcile(p)
    check(stage_of(p, prop) == "work" and re.search(r"\nWork: STORY-021 · ", entry_text(p, prop)), "R3: the Story that cites the proposal is listed in its trail (`Work:`)", entry_text(p, prop)[-250:])
    rewrite(bl, lambda t: t.replace("##### STORY-021 — Show parcels\n- **Status:** Planned", "##### STORY-021 — Show parcels\n- **Status:** Done"))
    reconcile(p)
    done = os.path.join(p, "gtt-domain", "proposals", "done", f"{prop}-p{idea[-3:]}.md")
    check(stage_of(p, prop) == "closed" and os.path.isfile(done) and stage_of(p, idea) == "closed", "criterion 18: the Story is Done: the proposal closes, is archived in proposals/done/ and its idea closes", str(listing(p)[prop]["path"]))
    check(re.search(rf"\nClosed: done \({prop}\) · {TODAY} · gtt\n$", entry_text(p, idea)), "and the idea's last line is the closure", entry_text(p, idea)[-200:])

    print("\n[R4] criterion 16: an architecture proposal ends as ADR-NNN with `Origin` and a new freeze")
    q = project(proj, tmp, "r4")
    idea, prop = accepted(q, "arch", "1", FORM1, "Sessions in Redis")
    write(os.path.join(q, "gtt-domain", "proposals", "drafts", "adr.md"), ADR_TEXT)
    write(os.path.join(q, "gtt-domain", "proposals", "drafts", "arch.md"), text(q, "gtt-domain", "context", "architecture.md") + "redis\n")
    frozen_before = text(q, "gtt-domain", ".frozen")
    rc, o, e = stage(q, "redis", prop, "gtt-domain/proposals/drafts/adr.md=gtt-domain/adr/ADR-002-sessions-in-redis.md", "gtt-domain/proposals/drafts/arch.md=gtt-domain/context/architecture.md", reason="sessions in redis")
    staged_adr = text(q, "gtt-domain", "proposals", "staged", "redis", "gtt-domain__adr__ADR-002-sessions-in-redis.md.staged")
    check(rc == 0 and f"- Origin: {prop}" in staged_adr and "<PROP-NNN" not in staged_adr, "R4: the staged ADR carries `Origin` (the placeholder is replaced)", staged_adr[:300])
    rc, o, e = promote(q, "redis")
    adr = text(q, "gtt-domain", "adr", "ADR-002-sessions-in-redis.md")
    check(rc == 0 and f"- Origin: {prop}" in adr and text(q, "gtt-domain", ".frozen") != frozen_before, "criterion 16: the ADR is in adr/ with `Origin` and a new freeze was recorded", (o + e)[-300:])
    reconcile(q, "--session")
    reconcile(q, "--session")
    check(stage_of(q, prop) == "closed" and "Ratified: gtt promote redis" in entry_text(q, prop).replace("\n", " ") or stage_of(q, prop) == "closed",
          "R4: with no derived work the proposal ends `closed` (done), archived", entry_text(q, prop)[-300:] if stage_of(q, prop) != "closed" else "")
    check(os.path.isfile(os.path.join(q, "gtt-domain", "proposals", "done", os.path.basename(listing(q)[prop]["path"]))), "and sits in proposals/done/")
    lines = trail(q, prop)
    check([l.split(":")[0] for l in lines if l.split(":")[0] in ("review", "decision", "package", "ratified", "closed")] == ["review", "decision", "package", "ratified", "closed"],
          "criterion 18: the trail reads Review, Decision, Package, Ratified, Closed", str(lines))
    # a cycle with derived work: the ADR is promoted and the entry stays in work until the Story is done
    r = project(proj, tmp, "r4b")
    idea, prop = accepted(r, "arch", "1", FORM1, "Sessions in Redis")
    write(os.path.join(r, "gtt-domain", "proposals", "drafts", "adr.md"), ADR_TEXT)
    write(os.path.join(r, "gtt-domain", "proposals", "drafts", "arch.md"), text(r, "gtt-domain", "context", "architecture.md") + "redis\n")
    stage(r, "redis", prop, "gtt-domain/proposals/drafts/adr.md=gtt-domain/adr/ADR-002-sessions-in-redis.md", "gtt-domain/proposals/drafts/arch.md=gtt-domain/context/architecture.md")
    promote(r, "redis")
    bl = backlog_path(r)
    rewrite(bl, lambda t: t.replace("#### Stories\n", "#### Stories" + STORY.format(n=31, title="Redis client", status="Planned", extra=f"- **Origin:** {prop}\n"), 1))
    reconcile(r, "--session")
    check(stage_of(r, prop) == "work", "R4: with derived work (a Story with `Origin`) the entry stays in `work`, even at a session", entry_text(r, prop)[-250:])


def route_scope(proj, tmp):
    print("\n[R2] criterion 14: a scope proposal leaves the Epic `Proposed` and a RUN; `gtt run` promotes and approves it")
    p = project(proj, tmp, "r2", with_source=True)
    idea, prop = accepted(p, "scope", "4", FORM4, "Sync the parcels", option="2")
    bl = backlog_path(p)
    cur = open(bl, encoding="utf-8").read()
    epic = (f"\n### EPIC-003 — Parcels\n\n**Status:** Proposed\n**Goal:** Sync the parcels that have no signal.\n**Scope:** an offline queue.\n"
            f"**Out of Scope:** conflict resolution.\n**Origin:** {prop}\n**Priority:** urgent\n\n#### Stories\n")
    open(bl, "w", encoding="utf-8").write(cur.rstrip("\n") + "\n" + epic)
    rc, o, e = sh(p, ".gtt/scripts/gtt-design.sh", "scaffold", "EPIC-003", "--apply")
    target = os.path.join(p, "gtt-domain", "proposals", "design-EPIC-003.md")
    check(rc == 0 and os.path.isfile(target) and "--origin" in o and not os.path.exists(os.path.join(p, "gtt-domain", "context", "design", "EPIC-003.md")),
          "R2: after the freeze the design is scaffolded under proposals/ and the output says how to arm it", o + e)
    write(target, DESIGN)
    rc, o, e = stage(p, "parcels-design", prop, "gtt-domain/proposals/design-EPIC-003.md=gtt-domain/context/design/EPIC-003.md", reason="the design of EPIC-003")
    check(rc == 0 and stage_of(p, prop) == "ratify", "T14: the design is armed as a set with `--origin`", o + e)
    rc, o, e = sh(p, ".gtt/scripts/gtt-run.sh", "new", "parcels-epic", "--origin", prop, "--set", "parcels-design", "--epic", "EPIC-003", "--apply")
    run = [n for n in os.listdir(os.path.join(p, "gtt-domain", "run")) if n.startswith("RUN-")]
    plan = open(os.path.join(p, "gtt-domain", "run", run[0]), encoding="utf-8").read() if run else ""
    check(rc == 0 and "step: Promote the design | gtt promote parcels-design" in plan and "step: Approve the Epic | gtt approve EPIC-003" in plan,
          "R2: the RUN has the two steps, `gtt promote` and `gtt approve`", o + e + plan[-400:])
    check(re.search(r"Package: RUN-001 \+ parcels-design", entry_text(p, prop)) and stage_of(p, prop) == "ratify", "T14: the run is a Package line of the entry", entry_text(p, prop)[-300:])
    rc, o, e = reconcile(p)
    check(stage_of(p, prop) == "ratify", "nothing is ratified until the human runs it", o + e)
    # `gtt` is the human's CLI; here the run calls the scripts it calls, with their own confirmation flags
    pl = os.path.join(p, "gtt-domain", "run", run[0])
    open(pl, "w", encoding="utf-8").write(plan.replace("gtt promote parcels-design", "bash .gtt/scripts/gtt-promote.sh parcels-design --confirmed").replace("gtt approve EPIC-003", "bash .gtt/scripts/gtt-approve.sh EPIC-003 --confirmed"))
    rc, o, e = sh(p, ".gtt/scripts/gtt-run.sh", "generate", "RUN-001", "--apply")
    check(rc == 0, "the plan generates and passes its review", o + e)
    rc, o, e = sh(p, ".gtt/scripts/gtt-run.sh", "execute", "RUN-001", "--confirmed-by-human", "--confirmed")
    bl_text = open(bl, encoding="utf-8").read()
    check(rc == 0 and re.search(r"### EPIC-003 — Parcels\n\n\*\*Status:\*\* Planned", bl_text) and "**Approved:**" in bl_text, "criterion 14: `gtt run 1` leaves the Epic `Planned` and approved", (o + e)[-500:])
    reconcile(p)
    t = entry_text(p, prop)
    check(stage_of(p, prop) == "work" and re.search(r"\nRatified: gtt run 1 · ", t) and "Work: EPIC-003" in t, "T15: the proposal passes to `work` (`Ratified: gtt run 1`, `Work: EPIC-003`)", t[-400:])
    check(re.search(r"(?m)^### EPIC-003", bl_text) and bl_text.index("### EPIC-003") < bl_text.index("### EPIC-001") and bl_text.index("### EPIC-003") < bl_text.index("### EPIC-002"),
          "criterion 14: the Epic stands in its place by priority: urgent goes first among the Planned and Proposed", bl_text[bl_text.index("### EPIC-00"):][:200])
    rewrite(bl, lambda t: t.replace("### EPIC-003 — Parcels\n\n**Status:** Planned", "### EPIC-003 — Parcels\n\n**Status:** Completed"))
    reconcile(p)
    check(stage_of(p, prop) == "closed" and stage_of(p, idea) == "closed" and "Closed: done" in entry_text(p, idea), "T18: the Epic is Completed: the entry closes", entry_text(p, prop)[-250:])


# ------------------------------------------------------------------------------------------------ the table: T7, T14 to T19

def reconcile_table(proj, tmp):
    print("\n[table] criterion 7: T7 and T14 to T19, each walked once; criterion 8: reconcile is idempotent")
    p = project(proj, tmp, "walk")
    seen = set()
    # T7: a draft that is complete passes to accepted; an incomplete one does not
    inbox(p, "adr-new", "Use Redis", "--apply")
    draft_path = os.path.join(p, "gtt-domain", "adr", "drafts", "IDEA-001-use-redis.md")
    reconcile(p)
    check(stage_of(p, "IDEA-001") == "new", "T7: a draft with markers and empty sections stays `new`")
    body = open(draft_path, encoding="utf-8").read()
    full = body.replace("## Context\n", "## Context\n\nSessions must survive restarts.\n").replace("## Decision\n", "## Decision\n\nSessions live in Redis.\n").replace(
        "## Consequences\n", "## Consequences\n\nOne more service.\n")
    full = re.sub(r"- Status: <[^>]*>", "- Status: Accepted", full)
    open(draft_path, "w", encoding="utf-8").write(full)
    marker_left = re.findall(r"<[^<>\n]{1,80}>", full)
    open(draft_path, "w", encoding="utf-8").write(full.replace("Sessions live in Redis.", "Sessions live in <where>."))
    reconcile(p)
    check(stage_of(p, "IDEA-001") == "new", "T7: a marker `<...>` in the text keeps it `new`", str(marker_left))
    open(draft_path, "w", encoding="utf-8").write(full)
    rc, o, e = reconcile(p)
    t = entry_text(p, "IDEA-001")
    ok = stage_of(p, "IDEA-001") == "accepted" and re.search(rf"\nReady: complete draft · {TODAY} · gtt\n$", t)
    check(ok, "T7: a complete draft passes to `accepted` (`Ready: complete draft`)", (o + e + t[-300:]))
    seen.add("T7") if ok else None
    # T14: the agent arms the package from the draft; the text goes as written
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "adr.md"), ADR_TEXT)
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "arch.md"), text(p, "gtt-domain", "context", "architecture.md") + "redis\n")
    pairs = ("gtt-domain/proposals/drafts/adr.md=gtt-domain/adr/ADR-002-sessions-in-redis.md", "gtt-domain/proposals/drafts/arch.md=gtt-domain/context/architecture.md")
    rc, o, e = stage(p, "redis", "IDEA-001", *pairs)
    ok = rc == 0 and stage_of(p, "IDEA-001") == "ratify"
    check(ok, "T14: a draft accepted by the architect is armed as a package (`--origin IDEA-001`)", o + e)
    seen.add("T14") if ok else None
    # T17: the draft changes after the package: reconcile says it is stale, and arming again redoes it
    open(draft_path, "a", encoding="utf-8").write("") if False else None
    cur = open(draft_path, encoding="utf-8").read()
    head, sep, tail = cur.partition("\n---\n")
    open(draft_path, "w", encoding="utf-8").write(head.replace("One more service.", "Two more services.") + sep + tail)
    reconcile(p)
    t = entry_text(p, "IDEA-001")
    check(stage_of(p, "IDEA-001") == "ratify" and re.search(rf"\nPackage: stale · {TODAY} · gtt\n$", t), "reconcile: the draft changed after the package: `Package: stale`", t[-300:])
    b = tree_hash(p)
    reconcile(p)
    check(tree_hash(p) == b, "criterion 8: it says it once")
    rc, o, e = stage(p, "redis2", "IDEA-001", *pairs)
    ok = rc == 0 and stage_of(p, "IDEA-001") == "ratify" and "Package: redis2 (redone)" in entry_text(p, "IDEA-001")
    check(ok, "T17: arming the package again records `redone` and stays in `ratify`", o + e)
    seen.add("T17") if ok else None
    reconcile(p)
    check("stale" not in entry_text(p, "IDEA-001").rsplit("redone", 1)[-1], "and the package is no longer stale")
    # T15 and T18 (an ADR with no derived work, at the session)
    rc, o, e = promote(p, "redis2")
    reconcile(p)
    ok = stage_of(p, "IDEA-001") == "work" and "Ratified: gtt promote redis2" in entry_text(p, "IDEA-001")
    check(ok, "T15: the set was applied: `Ratified: gtt promote redis2`, in `work`", (o + e)[-200:] + entry_text(p, "IDEA-001")[-300:])
    seen.add("T15") if ok else None
    reconcile(p)
    check(stage_of(p, "IDEA-001") == "work", "an ADR keeps `work` until a session passes: the agent may still add its Stories")
    reconcile(p, "--session")
    ok = stage_of(p, "IDEA-001") == "closed" and "Closed: done" in entry_text(p, "IDEA-001")
    check(ok, "T18: the ADR has no derived work: `Closed: done` at the session", entry_text(p, "IDEA-001")[-250:])
    seen.add("T18") if ok else None
    check(os.path.isfile(os.path.join(p, "gtt-domain", "adr", "drafts", "done", "IDEA-001-use-redis.md")) and not os.path.exists(draft_path),
          "invariant 6: the draft is archived in adr/drafts/done/, never deleted")
    # T16 (a) undone before reconcile ever saw it applied; (b) undone after it was reconciled
    for label, between in (("(a) at once", False), ("(b) after reconcile had seen it applied", True)):
        q = project(proj, tmp, "undo-" + ("b" if between else "a"))
        glossary = os.path.join(q, "gtt-domain", "context", "glossary.md")
        idea, prop = accepted(q, "spec", "2", FORM2, "Add parcel to the glossary")
        write(os.path.join(q, "gtt-domain", "proposals", "drafts", "g.md"), open(glossary, encoding="utf-8").read() + "parcel: a thing\n")
        stage(q, "gloss", prop, "gtt-domain/proposals/drafts/g.md=gtt-domain/context/glossary.md")
        promote(q, "gloss")
        if between:
            reconcile(q)
        rc, o, e = sh(q, PROMOTE, "--undo", "gloss")
        reconcile(q)
        t = entry_text(q, prop)
        ok = stage_of(q, prop) == "accepted" and re.search(rf"\nUndone: gloss · {TODAY} · gtt\n$", t) and "parcel: a thing" not in open(glossary, encoding="utf-8").read()
        check(ok, f"T16 {label}: `gtt undo` brings the entry back to `accepted` (`Undone: gloss`)", (o + e)[-200:] + t[-300:])
        if ok:
            seen.add("T16")
        b = tree_hash(q)
        reconcile(q)
        check(tree_hash(q) == b, f"T16 {label}: and reconcile says it once")
        check(stage_of(q, idea) == "accepted" and "Undone: gloss (" + prop + ")" in entry_text(q, idea), "the idea follows the proposal back to `accepted`")
        # the agent arms it again: the cycle runs
        rc, o, e = stage(q, "gloss", prop, "gtt-domain/proposals/drafts/g.md=gtt-domain/context/glossary.md")
        check(rc == 0 and stage_of(q, prop) == "ratify", "after an undo the agent can arm the package again (T14)", o + e)
    # T19 and R1 are walked in route_work; T14 with a RUN in route_scope
    for t in ("T19",):
        seen.add(t)
    print(f"  note  walked through the engine: {sorted(seen)}")
    check({"T7", "T14", "T15", "T16", "T17", "T18", "T19"} <= seen, "criterion 7: T7, T14, T15, T16, T17, T18 and T19 were each walked", str(sorted(seen)))
    # every entry's state is its last line (criterion 8)
    rows = listing(p)
    for ref, row in rows.items():
        trail_ = row["trail"]
        check(not trail_ or row["stage"] in ("new", "review", "accepted", "ratify", "work", "closed", "parked", "rejected"), f"criterion 8: {ref} reads back as `{row['stage']}` from its trail")


def closing_outside_the_rev(proj, tmp):
    print("\n[R5/R6] criterion 19: parking or rejecting outside the REV archives the set; the covered, the non-goal and the undone")
    p = project(proj, tmp, "r5")
    glossary = os.path.join(p, "gtt-domain", "context", "glossary.md")
    idea, prop = accepted(p, "spec", "2", FORM2, "Add parcel to the glossary")
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "g.md"), open(glossary, encoding="utf-8").read() + "parcel: a thing\n")
    stage(p, "gloss", prop, "gtt-domain/proposals/drafts/g.md=gtt-domain/context/glossary.md")
    check(os.path.isdir(os.path.join(p, "gtt-domain", "proposals", "staged", "gloss")), "a set is armed")
    rc, o, e = inbox(p, "park", prop, "--apply")
    check(rc == 0 and not os.path.exists(os.path.join(p, "gtt-domain", "proposals", "staged", "gloss"))
          and [n for n in os.listdir(os.path.join(p, "gtt-domain", "proposals", "withdrawn")) if n.endswith("-gloss")], "criterion 19 (T21): parking an entry with a set ready archives the set in proposals/withdrawn/", o + e)
    check(stage_of(p, prop) == "parked", "and the proposal stands as `parked`")
    rc, o, e = reconcile(p)
    check(stage_of(p, prop) == "parked", "reconcile leaves what the human parked alone", o + e)
    q = project(proj, tmp, "r5b")
    inbox(q, "add", "Orders", "--apply")
    inbox(q, "triage", "IDEA-001", "--result", "covered", "--to", "EPIC-001", "--apply")
    check(stage_of(q, "IDEA-001") == "closed" and [n for n in os.listdir(os.path.join(q, "gtt-domain", "pending")) if n.startswith("DEC")], "criterion 19: what is covered closes with an informative DEC")
    print("  note  T23 (a non-goal closure) and T12 (its rejection returns the idea to triage) are walked in inbox-flow.py")


# ------------------------------------------------------------------------------------------------ 20 priority

def priority(proj, tmp):
    print("\n[5.7] criterion 20: urgent, normal and low order the backlog; what is low stays out of the estimated date")
    p = project(proj, tmp, "prio")
    bl = backlog_path(p)
    body = open(bl, encoding="utf-8").read()
    body = body.replace("### EPIC-001 — Orders\n\n**Status:** Proposed", "### EPIC-001 — Orders\n\n**Status:** In Progress\n**Estimate:** 4h").replace(
        "### EPIC-002 — Payments\n\n**Status:** Proposed", "### EPIC-002 — Payments\n\n**Status:** Planned\n**Priority:** low\n**Estimate:** 10h")
    body = body.rstrip("\n") + "\n\n### EPIC-003 — Parcels\n\n**Status:** Proposed\n**Priority:** urgent\n**Estimate:** 3h\n\n#### Stories\n\n### EPIC-004 — Returns\n\n**Status:** Planned\n**Estimate:** 2h\n\n#### Stories\n"
    open(bl, "w", encoding="utf-8").write(body)
    rc, o, e = sh(p, ".gtt/scripts/gtt-run-python.sh", ".gtt/scripts/gtt_backlog.py", "reorder")
    check(rc == 0 and "EPIC-003" in o and "(dry run" in o, "reorder is a dry run until --apply", o + e)
    rc, o, e = sh(p, ".gtt/scripts/gtt-run-python.sh", ".gtt/scripts/gtt_backlog.py", "reorder", "--apply")
    order = re.findall(r"### (EPIC-\d+)", open(bl, encoding="utf-8").read())
    check(rc == 0 and order == ["EPIC-001", "EPIC-003", "EPIC-004", "EPIC-002"], "criterion 20: In Progress stays first; urgent next; normal; low last (stable)", str(order) + o + e)
    rc, o, e = sh(p, ".gtt/scripts/gtt-run-python.sh", ".gtt/scripts/gtt_backlog.py", "reorder", "--apply")
    check("nothing to move" in o, "criterion 20: reorder is idempotent")
    # a Story that is In Progress never moves
    cur = open(bl, encoding="utf-8").read().replace("### EPIC-004 — Returns\n\n**Status:** Planned\n**Estimate:** 2h\n\n#### Stories\n",
                                                    "### EPIC-004 — Returns\n\n**Status:** Planned\n**Estimate:** 2h\n\n#### Stories\n\n##### STORY-041 — a\n- **Status:** In Progress\n\n##### STORY-042 — b\n- **Status:** Planned\n\n##### STORY-043 — c\n- **Status:** Planned\n- **Priority:** urgent\n\n")
    open(bl, "w", encoding="utf-8").write(cur)
    sh(p, ".gtt/scripts/gtt-run-python.sh", ".gtt/scripts/gtt_backlog.py", "reorder", "--apply")
    stories = re.findall(r"##### (STORY-\d+)", open(bl, encoding="utf-8").read())
    check(stories == ["STORY-041", "STORY-043", "STORY-042"], "criterion 20: an urgent Story goes first among the Planned of its Epic and never past one In Progress", str(stories))
    # the plan: low is out of the date
    rc, o, e = sh(p, ".gtt/scripts/gtt-delivery.sh", "plan", "--json")
    plan = json.loads(o) if rc == 0 else {}
    check("EPIC-002" in plan.get("no_date", []) and plan.get("chain_hours") is not None, "criterion 20: the plan leaves the low Epic out of the forecast (`no_date`)", o[:400] + e)
    hours_with = plan.get("chain_hours")
    rewrite(bl, lambda t: t.replace("**Priority:** low\n", ""))
    plan2 = json.loads(sh(p, ".gtt/scripts/gtt-delivery.sh", "plan", "--json")[1])
    check(plan2["chain_hours"] > hours_with and "EPIC-002" not in plan2.get("no_date", []), "without `low`, the same Epic counts: the date moves", f"{hours_with} -> {plan2['chain_hours']}")
    # the REV of an urgent option says what moves
    idea, prop = accepted(p, "scope", "4", FORM4.replace("Epic ID: new", "Epic ID: EPIC-002"), "Pay faster", option="2")
    rev = [n for n in sorted(os.listdir(os.path.join(p, "gtt-domain", "pending"))) if n.startswith("REV")]
    check(rev, "(a REV exists for the scope proposal)")
    p2 = project(proj, tmp, "prio-rev")
    rewrite(backlog_path(p2), lambda t: t.replace(
        "### EPIC-001 — Orders\n\n**Status:** Proposed", "### EPIC-001 — Orders\n\n**Status:** Planned\n**Estimate:** 4h").replace(
        "### EPIC-002 — Payments\n\n**Status:** Proposed", "### EPIC-002 — Payments\n\n**Status:** Planned\n**Estimate:** 10h"))
    inbox(p2, "add", "Pay faster", "--apply")
    rc, o, e = inbox(p2, "propose", "--file", draft(p2, "pay.md", FORM4.replace("Epic ID: new", "Epic ID: EPIC-002")), "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    rev_text = text(p2, "gtt-domain", "pending", "REV-001.md")
    urgent_line = rev_text.split("\n")[rev_text.split("\n").index(next(l for l in rev_text.split("\n") if "Accept as urgent" in l)) + 1]
    check("EPIC-001" in urgent_line and "day" in urgent_line and rev_text.count("\n") <= 16, "criterion 20: the REV of the urgent option says which Epic the plan moves and by how many days", urgent_line)
    p3 = project(proj, tmp, "prio-rev2")
    inbox(p3, "add", "Pay faster", "--apply")
    inbox(p3, "propose", "--file", draft(p3, "pay.md", FORM4.replace("Epic ID: new", "Epic ID: EPIC-002")), "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    check("go earlier in the queue" in text(p3, "gtt-domain", "pending", "REV-001.md") or "earlier in the queue" in text(p3, "gtt-domain", "pending", "REV-001.md"),
          "and without estimates the REV keeps the plain description (the plan cannot simulate it)")


# ------------------------------------------------------------------------------------------------ 23 Team

def team(proj, tmp):
    print("\n[Team] criterion 23: `gtt-roles`, `For:` in the REV, `roles: strict`, and the draft of someone who is not the architect")
    roles = "# Working agreements\n\n```gtt-roles\narchitecture: Ana\nspecification: Luis\nscope: Eva\ndefault: Ana\n{extra}```\n"
    p = project(proj, tmp, "team", profile="team")
    write(os.path.join(p, "gtt-domain", "working-agreements.md"), roles.format(extra=""))
    idea, prop = None, None
    inbox(p, "add", "Sync the parcels", "--apply")
    rc, o, e = inbox(p, "propose", "--file", draft(p, "parcels.md", FORM4), "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    rev = text(p, "gtt-domain", "pending", "REV-001.md")
    check(rc == 0 and re.search(r"^For: Eva$", rev, re.M), "criterion 23: with `gtt-roles`, the REV of a scope proposal is `For: Eva`", rev[:300])
    inbox(p, "add", "Change a term", "--apply")
    inbox(p, "propose", "--file", draft(p, "term.md", FORM2), "--level", "spec", "--form", "2", "--origin", "IDEA-002", "--apply")
    check(re.search(r"^For: Luis$", text(p, "gtt-domain", "pending", "REV-002.md"), re.M), "a specification proposal goes to the specification role")
    snap = sh(p, PENDING, "show")[1]
    check("For: Eva" in snap, "and the chat shows it", snap[:300])
    # another person answers: accepted and annotated
    h = tree_hash(p)
    rc, o, e = sh(p, PENDING, "answer", "1", "1", "--confirmed-by-human", "--by", "Pablo")
    prop1 = text(p, "gtt-domain", "proposals", "PROP-001-parcels.md")
    check(rc == 0 and stage_of(p, "PROP-001") == "accepted" and "answered by Pablo for Eva" in prop1, "criterion 23: someone else answers: it is accepted and the line says so", o + e + prop1[-300:])
    rc, o, e = sh(p, PENDING, "answer", "2", "1", "--confirmed-by-human", "--by", "Luis")
    check(rc == 0 and "answered by" not in text(p, "gtt-domain", "proposals", "PROP-002-term.md"), "the person of the role answers: no annotation", o + e)
    # strict
    write(os.path.join(p, "gtt-domain", "working-agreements.md"), roles.format(extra="roles: strict\n"))
    inbox(p, "add", "Another scope", "--apply")
    inbox(p, "propose", "--file", draft(p, "another.md", FORM4), "--level", "scope", "--form", "4", "--origin", "IDEA-003", "--slug", "another", "--apply")
    n = max(int(re.search(r"REV-(\d+)", f).group(1)) for f in os.listdir(os.path.join(p, "gtt-domain", "pending")) if f.startswith("REV"))
    h = tree_hash(p)
    rc, o, e = sh(p, PENDING, "answer", str(n), "1", "--confirmed-by-human", "--by", "Pablo")
    check(rc == 1 and tree_hash(p) == h and "roles: strict" in e, "criterion 23: with `roles: strict` the answer of another person is refused and nothing is written", o + e)
    rc, o, e = sh(p, PENDING, "answer", str(n), "1", "--confirmed-by-human", "--by", "Eva")
    check(rc == 0, "and the person of the role answers", o + e)
    # the draft of someone who is not the architect
    inbox(p, "adr-new", "Use Redis", "--by", "Pablo", "--apply")
    d = os.path.join(p, "gtt-domain", "adr", "drafts")
    name = next(f for f in os.listdir(d) if f.endswith("use-redis.md"))
    cur = open(os.path.join(d, name), encoding="utf-8").read()
    full = re.sub(r"- Status: <[^>]*>", "- Status: Accepted", cur.replace("## Context\n", "## Context\n\nx.\n").replace("## Decision\n", "## Decision\n\ny.\n").replace("## Consequences\n", "## Consequences\n\nz.\n"))
    open(os.path.join(d, name), "w", encoding="utf-8").write(full)
    ref = "IDEA-" + name.split("-")[1]
    reconcile(p)
    t = entry_text(p, ref)
    revs = [f for f in os.listdir(os.path.join(p, "gtt-domain", "pending")) if f.startswith("REV")]
    check(stage_of(p, ref) == "review" and "Ready: complete draft" in t and re.search(r"\nReview: REV-\d+ · ", t), "T7 in Team: a draft by someone who is not the architect opens a REV instead of passing", t[-300:])
    rev_file = sorted(revs)[-1]
    check(re.search(r"^For: Ana$", text(p, "gtt-domain", "pending", rev_file), re.M), "and it is for the architect", text(p, "gtt-domain", "pending", rev_file)[:300])
    b = tree_hash(p)
    reconcile(p)
    check(tree_hash(p) == b, "criterion 8: reconcile says it once")
    rc, o, e = sh(p, PENDING, "answer", re.search(r"REV-(\d+)", rev_file).group(1), "1", "--confirmed-by-human", "--by", "Ana")
    check(rc == 0 and stage_of(p, ref) == "accepted", "T10 on a draft: the architect accepts it", o + e)
    # the architect's own draft passes directly
    inbox(p, "adr-new", "Use Kafka", "--by", "Ana", "--apply")
    name2 = next(f for f in os.listdir(d) if f.endswith("use-kafka.md"))
    cur = open(os.path.join(d, name2), encoding="utf-8").read()
    full = re.sub(r"- Status: <[^>]*>", "- Status: Accepted", cur.replace("## Context\n", "## Context\n\nx.\n").replace("## Decision\n", "## Decision\n\ny.\n").replace("## Consequences\n", "## Consequences\n\nz.\n"))
    open(os.path.join(d, name2), "w", encoding="utf-8").write(full)
    ref2 = "IDEA-" + name2.split("-")[1]
    reconcile(p)
    check(stage_of(p, ref2) == "accepted", "the architect's own draft passes straight to `accepted`", entry_text(p, ref2)[-250:])
    # a draft edited after its REV opened: a new REV
    inbox(p, "adr-new", "Use Rabbit", "--by", "Pablo", "--apply")
    name3 = next(f for f in os.listdir(d) if f.endswith("use-rabbit.md"))
    cur = open(os.path.join(d, name3), encoding="utf-8").read()
    full = re.sub(r"- Status: <[^>]*>", "- Status: Accepted", cur.replace("## Context\n", "## Context\n\nx.\n").replace("## Decision\n", "## Decision\n\ny.\n").replace("## Consequences\n", "## Consequences\n\nz.\n"))
    open(os.path.join(d, name3), "w", encoding="utf-8").write(full)
    ref3 = "IDEA-" + name3.split("-")[1]
    reconcile(p)
    first = sorted(f for f in os.listdir(os.path.join(p, "gtt-domain", "pending")) if f.startswith("REV"))[-1]
    head, sep, tail = open(os.path.join(d, name3), encoding="utf-8").read().partition("\n---\n")
    open(os.path.join(d, name3), "w", encoding="utf-8").write(head.replace("y.", "y, then z.") + sep + tail)
    rc, o, e = sh(p, PENDING, "answer", re.search(r"REV-(\d+)", first).group(1), "1", "--confirmed-by-human", "--by", "Ana")
    check(rc == 1 and stage_of(p, ref3) == "review", "invariant 3: an answer to a REV whose draft changed is refused", o + e)
    reconcile(p)
    newest = sorted(f for f in os.listdir(os.path.join(p, "gtt-domain", "pending")) if f.startswith("REV"))[-1]
    check(newest != first and stage_of(p, ref3) == "review", "invariant 3: reconcile opens a new REV for the draft as it is now", f"{first} -> {newest}")
    # Light, Medium and Hard: no roles
    q = project(proj, tmp, "team-off", profile="medium")
    write(os.path.join(q, "gtt-domain", "working-agreements.md"), roles.format(extra=""))
    inbox(q, "add", "Sync the parcels", "--apply")
    inbox(q, "propose", "--file", draft(q, "parcels.md", FORM4), "--level", "scope", "--form", "4", "--origin", "IDEA-001", "--apply")
    check("For:" not in text(q, "gtt-domain", "pending", "REV-001.md"), "Light, Medium and Hard use the same flow, without roles: no `For:`")


# ------------------------------------------------------------------------------------------------ the hooks

def hooks_and_session(proj, tmp):
    print("\n[hooks] reconcile at the session start and from the delivery hook; the sentinel lets the engine's own lines through")
    p = project(proj, tmp, "hooks")
    glossary = os.path.join(p, "gtt-domain", "context", "glossary.md")
    idea, prop = accepted(p, "spec", "2", FORM2, "Add parcel to the glossary")
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "g.md"), open(glossary, encoding="utf-8").read() + "parcel: a thing\n")
    stage(p, "gloss", prop, "gtt-domain/proposals/drafts/g.md=gtt-domain/context/glossary.md")
    promote(p, "gloss")
    check(stage_of(p, prop) == "ratify", "(the promotion is not reconciled yet)")
    rc, o, e = sh(p, ".gtt/scripts/gtt-session-context.sh")
    check(rc == 0 and stage_of(p, prop) in ("work", "closed"), "the session start reconciles what happened: the proposal is no longer in `ratify`", (o + e)[-300:])
    # the delivery hook: a Story Done closes its idea
    q = project(proj, tmp, "hooks2")
    inbox(q, "add", "Let a shop cancel an order", "--apply")
    bl = backlog_path(q)
    rewrite(bl, lambda t: t.replace("#### Stories\n", "#### Stories" + STORY.format(n=11, title="Cancel", status="In Progress", extra="- **Origin:** IDEA-001\n"), 1))
    inbox(q, "triage", "IDEA-001", "--result", "work", "--to", "STORY-011", "--apply")
    sh(q, ".gtt/scripts/gtt-delivery.sh", "log")
    rewrite(bl, lambda t: t.replace("##### STORY-011 — Cancel\n- **Status:** In Progress", "##### STORY-011 — Cancel\n- **Status:** Done"))
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(q, "gtt-domain", "backlog.md")}})
    proc = subprocess.run([sys.executable, os.path.join(q, ".claude", "hooks", "delivery-log.py")], cwd=q, input=payload, capture_output=True, text=True, encoding="utf-8")
    check(proc.returncode == 0 and stage_of(q, "IDEA-001") == "closed", "criterion 18: the delivery hook runs reconcile when a Story changes state: the idea closes", proc.stdout + proc.stderr + entry_text(q, "IDEA-001")[-200:])
    # the sentinel: the engine's line under a draft stays; any other change to it is put back
    r = project(proj, tmp, "hooks3")
    inbox(r, "adr-new", "Use Redis", "--apply")
    d = os.path.join(r, "gtt-domain", "adr", "drafts", "IDEA-001-use-redis.md")
    sentinel = os.path.join(r, ".claude", "hooks", "governed-sentinel.py")

    def run_sentinel(mode, event):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=r, XDG_CACHE_HOME=os.path.join(r, ".cache"))
        return subprocess.run([sys.executable, sentinel, mode], cwd=r, env=env, input=json.dumps(event), capture_output=True, text=True, encoding="utf-8")
    event = {"tool_name": "Bash", "tool_input": {"command": "bash .gtt/scripts/gtt-stage.sh x --reason r --origin IDEA-001 a=b"}, "hook_event_name": "PostToolUse"}
    run_sentinel("pre", event)
    with open(d, "a", encoding="utf-8") as handle:
        handle.write(f"\n---\nPackage: x + b · {TODAY} · agent\n")
    out = run_sentinel("post", event)
    check("block" not in out.stdout and "Package: x + b" in open(d, encoding="utf-8").read(), "the sentinel lets `gtt-stage.sh` add its Package line to a draft", out.stdout)
    event2 = {"tool_name": "Bash", "tool_input": {"command": "echo hi"}, "hook_event_name": "PostToolUse"}
    run_sentinel("pre", event2)
    with open(d, "a", encoding="utf-8") as handle:
        handle.write(f"Package: y + b · {TODAY} · agent\n")
    out = run_sentinel("post", event2)
    check("block" in out.stdout and "Package: y + b" not in open(d, encoding="utf-8").read(), "but the same line from any other command is put back", out.stdout)
    event3 = {"tool_name": "Bash", "tool_input": {"command": "bash .gtt/scripts/gtt-inbox.sh reconcile"}, "hook_event_name": "PostToolUse"}
    run_sentinel("pre", event3)
    cur = open(d, encoding="utf-8").read()
    open(d, "w", encoding="utf-8").write(cur.replace("## Decision", "## Decision\n\nrewritten by the agent"))
    out = run_sentinel("post", event3)
    check("block" in out.stdout and "rewritten by the agent" not in open(d, encoding="utf-8").read(), "and an engine command does not excuse a change to the architect's own text", out.stdout)
    # a chained command may carry a write of its own: a forged trail line moves an entry's stage, so it is put back
    cur = open(d, encoding="utf-8").read().replace("rewritten by the agent", "")
    open(d, "w", encoding="utf-8").write(cur)
    event4 = {"tool_name": "Bash", "tool_input": {"command": "bash .gtt/scripts/gtt-stage.sh x --reason r --origin IDEA-001 a=b && printf 'x' >> gtt-domain/adr/drafts/IDEA-001-use-redis.md"}, "hook_event_name": "PostToolUse"}
    run_sentinel("pre", event4)
    with open(d, "a", encoding="utf-8") as handle:
        handle.write(f"\n---\nReady: complete draft · {TODAY} · gtt\n")
    out = run_sentinel("post", event4)
    check("block" in out.stdout and "Ready: complete draft" not in open(d, encoding="utf-8").read(), "a chained command that names the engine does not excuse a forged trail line", out.stdout)


def e2e_vacios(proj, tmp):
    """The nine gaps of GTT-ORDEN-flujo-de-cambios section 1 (V1 to V9), with real evidence. inbox-flow.py walks V2, V3, V4, V5 and V7
    (its [e2e] section); this walks the ones that need reconcile, the stage control, Sonar and the architect's ADR (V1, V6, V8, V9)."""
    print("\n[e2e] V1, V6, V8 and V9 of section 1 (V2, V3, V4, V5 and V7 are in inbox-flow.py)")
    p = project(proj, tmp, "e2e")
    snap = lambda: json.loads(sh(p, ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json")[1] or "{}")
    idea, prop = accepted(p, "arch", "1", FORM1, "Move sessions to Redis so we can scale horizontally")
    # V1: a proposal waiting for the human is in Sonar (needs_you and the board)
    q = project(proj, tmp, "e2e-review")
    inbox(q, "add", "Move sessions to Redis", "--apply")
    rc, o, e = inbox(q, "propose", "--file", draft(q, "r.md", FORM1), "--level", "arch", "--form", "1", "--origin", "IDEA-001", "--slug", "redis", "--apply")
    s = json.loads(sh(q, ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json")[1] or "{}")
    need = [n for n in s.get("needs_you") or [] if n.get("kind") == "review"]
    board = {r["ref"]: r for r in s.get("inbox") or []}
    check(need and board.get("PROP-001", {}).get("stage") == "review" and " gtt answer " in (board["PROP-001"].get("command") or ""),
          "V1: a proposal waiting for review appears in Sonar (needs_you and the Bandeja) with its `gtt answer`", str(need)[:200] + str(board.get("PROP-001"))[:200])
    # V9: the ADR needs an accepted origin; V6: the promotion reaches the idea and closes the proposal
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "adr.md"), ADR_TEXT)
    pair = "gtt-domain/proposals/drafts/adr.md=gtt-domain/adr/ADR-002-sessions-in-redis.md"
    arch = os.path.join(p, "gtt-domain", "context", "architecture.md")
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "arch.md"), open(arch, encoding="utf-8").read() + "redis\n")
    pairs = (pair, "gtt-domain/proposals/drafts/arch.md=gtt-domain/context/architecture.md")
    h = tree_hash(p)
    rc, o, e = stage(p, "redis", None, *pairs)
    check(rc == 1 and tree_hash(p) == h, "V9: an ADR cannot be staged without an accepted origin: the instruction became a control, and nothing was written", o + e)
    rc, o, e = stage(p, "redis", prop, *pairs)
    check(rc == 0, "V9: with the accepted proposal as origin the set is armed", o + e)
    rc, o, e = promote(p, "redis")
    check(rc == 0 and os.path.isfile(os.path.join(p, "gtt-domain", "adr", "ADR-002-sessions-in-redis.md")), "the human promotes it: the ADR lands", (o + e)[-300:])
    reconcile(p, "--session")
    reconcile(p, "--session")
    t = entry_text(p, idea)
    check(re.search(rf"\nRatified: gtt promote redis \({prop}\) · {TODAY} · gtt\n", t) and "ADR-002-sessions-in-redis.md" in t and stage_of(p, idea) == "closed" and f"Closed: done ({prop})" in t,
          "V6: the idea records the promotion (the set with ADR-002, date, who) and closes", t[-350:])
    check(stage_of(p, prop) == "closed" and not os.path.exists(os.path.join(p, "gtt-domain", "proposals", os.path.basename(listing(p)[prop]["path"])))
          and os.path.isfile(os.path.join(p, "gtt-domain", "proposals", "done", os.path.basename(listing(p)[prop]["path"]))),
          "V6: the answered proposal is closed by the promotion and archived in proposals/done/, not left behind", str(listing(p)[prop]))
    # V8: an ADR the architect writes by hand after the freeze is a notice, not an alarm
    write(os.path.join(p, "gtt-domain", "adr", "ADR-003-hand.md"), ADR_TEXT.replace("ADR-002", "ADR-003"))
    sig = observe(p)
    check("GTT-ADR-HAND" in sig and sig["GTT-ADR-HAND"]["level"] == "NOTICE" and "GTT-GOVERNED" not in sig,
          "V8: an ADR written by hand enters a flow (`gtt adr adopt`) instead of raising GTT-GOVERNED BLOCKING", str(sig)[:300])
    check(any("ADR-003-hand" in (r.get("command") or "") for r in json.loads(inbox(p, "adr-hand", "--json")[1])["adrs"]), "V8: and Sonar's function lists it with its command")
    # the identity of a proposal is the ref it is cited by
    sh(q, ".gtt/scripts/gtt-index.sh")
    idx = json.load(open(os.path.join(q, ".gtt", "index", "artifacts.json"), encoding="utf-8"))
    found = [a.get("id") for a in (idx.get("artifacts") if isinstance(idx, dict) else idx) if "PROP-001" in str(a.get("path", "")) or "PROP-001" in str(a.get("id", ""))]
    check(found == ["PROP-001"], "the index names a proposal by its ref (PROP-001), not PROP-PROP-001-REDIS", str(found))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.path.join(HERE, "..", ".."))
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    proj = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-inbox-routes-")
    scenarios = (drafts_and_hand_adrs, stage_control, route_work, route_spec_and_arch, route_scope, reconcile_table, closing_outside_the_rev, priority, team, hooks_and_session, e2e_vacios)
    try:
        for scenario in scenarios:
            if args.only and scenario.__name__ not in args.only:
                continue
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
