#!/usr/bin/env python3
"""GTT inbox in the session and the migration from 1.22 (criteria 21, 22 and 25 of GTT-ORDEN-flujo-de-cambios section 18).

  21  with a Story In Progress the next action asks no triage, except for an entry written with --now; at session start,
      or once the Story is Done, it does (and the hook that sees the Story close says so in one line)
  22  session.md shows `Bandeja: n nuevas · n en revisión · n por ratificar`
  25  a 1.22 project - one pending request, two PROPOSAL-*.md, one staged set - is migrated without losing anything,
      the desk is retired, and running the migration again changes nothing
  and: change-request.md is no longer a desk (the operation writes an IDEA; the desk's rules are gone)

  python3 .gtt/tests/inbox-session.py [--project .] [--keep]
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
spec = importlib.util.spec_from_file_location("acc", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
check, write, tree_hash = acc.check, acc.write, acc.tree_hash

INBOX = ".gtt/scripts/gtt-inbox.sh"
PROJECT = ".gtt/scripts/gtt-project.sh"
BACKLOG_HEAD = "# Backlog\n\n## Epics\n\n"
FORM1 = """Proposed Architecture Change

Current decision: monolith
Suggested change: split the billing module
Reason: it scales on its own
Impact: one new service
Risk: medium
Affected files: gtt-domain/context/architecture.md
Alternatives considered: none
"""
DESK = """# Change Request

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

## GTT Request

```text
Id: CR-20261001-101500
Requested: 2026-10-01T10:15:00Z by Ana
Change: Move sessions to Redis
Reason: Horizontal scaling
Trigger: latency
Scope:
Impact:
Risk:
Priority: high
```
"""


def sh(cwd, *argv, env=None):
    p = subprocess.run(["bash", *argv], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, **(env or {})))
    return p.returncode, p.stdout, p.stderr


def text(p, *parts):
    path = os.path.join(p, *parts)
    return open(path, encoding="utf-8").read() if os.path.isfile(path) else ""


def listing(p, folder):
    path = os.path.join(p, folder)
    return sorted(os.listdir(path)) if os.path.isdir(path) else []


def next_action(p, *flags, env=None):
    rc, out, err = sh(p, PROJECT, "next-action", "--json", *flags, env=env)
    try:
        return (json.loads(out) or {}).get("next_action")
    except ValueError:
        check(False, "next-action prints JSON", out + err)
        return None


def set_story(p, status):
    write(os.path.join(p, "gtt-domain", "backlog.md"),
          BACKLOG_HEAD + f"#### Stories\n\n##### STORY-001 - Work in hand\n- **Status:** {status}\n")


def session(project, tmp):
    print("[session] the inbox in the next action and in session.md")
    p = acc.fresh(project, tmp, "session")
    for stale in ("gtt-domain/session.md",):
        if os.path.isfile(os.path.join(p, stale)):
            os.remove(os.path.join(p, stale))
    check(not os.path.exists(os.path.join(p, "gtt-domain", "change-request.md")), "the Bootstrap carries no change-request.md template")
    check(not os.path.exists(os.path.join(p, ".claude", "hooks", "notify-change-request.py"))
          and "notify-change-request" not in text(p, ".claude", "settings.json"), "the notice hook of the desk is gone")
    check("change-request" not in text(p, ".gtt", "scaffold", "manifest.yaml"), "the manifest no longer lists the desk")

    rc, out, err = sh(p, INBOX, "add", "Cache the catalogue", "--apply")
    check(rc == 0, "an idea is added", out + err)
    set_story(p, "In Progress")
    check(next_action(p) is None, "21: with a Story In Progress the next action asks no triage")
    found = next_action(p, "--session-start")
    check(found and found["kind"] == "inbox" and "IDEA-001" in found["text"], "21: at session start the idea is to be triaged", str(found))
    rc, out, err = sh(p, INBOX, "add", "Fix the login now", "--now", "--apply")
    found = next_action(p)
    check(found and found["kind"] == "inbox" and "IDEA-002" in found["text"] and "IDEA-001" not in found["text"],
          "21: an entry with --now is the first answer even with a Story In Progress", str(found))
    rc, out, err = sh(p, INBOX, "triage", "IDEA-002", "--result", "incorporated", "--to", "AGENTS.md", "--apply")
    # the idea written with --now is triaged by hand: the next action goes back to nothing while the Story is open
    set_story(p, "In Progress")
    rc, out, err = sh(p, PROJECT, "inbox-line")
    check(out.startswith("Inbox: ") or out.startswith("Bandeja: "), "the inbox line is one line", out + err)
    set_story(p, "Done")
    found = next_action(p)
    check(found and found["kind"] == "inbox" and "IDEA-001" in found["text"], "21: with the Story Done the idea is to be triaged", str(found))

    rc, out, err = sh(p, ".gtt/scripts/gtt-status.sh")
    md = text(p, "gtt-domain", "session.md")
    check(re.search(r"^(Inbox: 1 new · 0 in review · 0 to ratify|Bandeja: 1 nuevas · 0 en revisión · 0 por ratificar)$", md, re.M),
          "22: session.md shows the inbox line", md[-900:])
    check("## Change request" not in md and "## New ideas" not in md, "session.md no longer carries the desk or the old ideas block")

    print("[session] the hook that sees a Story close says what waits")
    set_story(p, "In Progress")
    sh(p, ".gtt/scripts/gtt-delivery.sh", "log")
    set_story(p, "Done")
    event = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(p, "gtt-domain", "backlog.md")}})
    proc = subprocess.run([sys.executable, ".claude/hooks/delivery-log.py"], cwd=p, input=event, capture_output=True, text=True)
    check(proc.returncode == 0 and "additionalContext" in proc.stdout and re.search(r"(Inbox: 1 without triage|Bandeja: 1 sin triage)", proc.stdout),
          "a Story moving to Done adds one line: how many entries have no triage", proc.stdout + proc.stderr)
    proc = subprocess.run([sys.executable, ".claude/hooks/delivery-log.py"], cwd=p, input=event, capture_output=True, text=True)
    check(proc.returncode == 0 and proc.stdout.strip() == "", "and says nothing when nothing changed")

    print("[session] gtt change is a shortcut: the operation writes an IDEA of type request, written now")
    q = acc.fresh(project, tmp, "change-shortcut")
    rc, env, _ = acc.op(q, "change.request", change="Move sessions to Redis", reason="Horizontal scaling")
    check(rc == 4, "writing a request is the human's act (confirmed_by_human)")
    rc, env, _ = acc.op(q, "change.request", change="Move sessions to Redis", reason="Horizontal scaling", priority="high", apply=True, confirmed_by_human=True)
    ideas = listing(q, "docs/ideas")
    body = text(q, "docs", "ideas", "IDEA-001.md")
    check(rc == 0 and "IDEA-001.md" in ideas and "Change: Move sessions to Redis" in body and re.search(r"(Now|Ahora): (yes|sí)", body),
          "the request is an IDEA with its fields, written with --now", body[:400])
    check(not os.path.exists(os.path.join(q, "gtt-domain", "change-request.md")), "and no desk is written")


def migration(project, tmp):
    print("[migration] a 1.22 project: one request, two PROPOSAL-*.md, one staged set")
    p = acc.fresh(project, tmp, "migrate")
    write(os.path.join(p, "gtt-domain", "change-request.md"), DESK)
    prop = os.path.join(p, "gtt-domain", "proposals")
    canon = "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md"
    write(os.path.join(prop, "PROPOSAL-redis.md"), f"# PROPOSAL - Redis sessions\n\n{canon}\n\nRequest: CR-20261001-101500\n\n{FORM1}")
    write(os.path.join(prop, "PROPOSAL-odd-thing.md"), f"# PROPOSAL - Something odd\n\n{canon}\n\nFree text a person wrote, no form.\n")
    write(os.path.join(prop, "ADR-DRAFT-0002-x.md"), f"# ADR-DRAFT x\n\n{canon}\n\nstays\n")
    write(os.path.join(prop, "staged", "term", "glossary.md"), "term\n")
    write(os.path.join(prop, "staged", "term", "promote.json"),
          json.dumps({"schema": 1, "name": "term", "reason": "a term", "files": [{"from": "glossary.md", "to": "gtt-domain/context/glossary.md", "sha_before": None}]}, indent=2) + "\n")
    before = {n: text(p, "gtt-domain", "proposals", n) for n in ("PROPOSAL-redis.md", "PROPOSAL-odd-thing.md", "ADR-DRAFT-0002-x.md")}

    rc, out, err = sh(p, INBOX, "migrate")
    check(rc == 0 and "dry run" in out and os.path.isfile(os.path.join(p, "gtt-domain", "change-request.md"))
          and os.path.isfile(os.path.join(prop, "PROPOSAL-redis.md")) and not listing(p, "docs/ideas")[1:2] ,
          "25: the first run is a dry run: it says what it will do and writes nothing", out + err)
    check("IDEA-001" in out and "PROP-001" in out and "PROP-002" in out and "legacy" in out, "the dry run names the refs it will create", out)

    rc, env, _ = acc.op(p, "inbox.migrate", apply=True)
    check(rc == 4, "migrating is the human's act (confirmed_by_human)")
    rc, out, err = sh(p, INBOX, "migrate", "--apply")
    check(rc == 0, "25: the migration runs", out + err)
    check(not os.path.exists(os.path.join(p, "gtt-domain", "change-request.md")), "the desk is removed")
    idea = text(p, "docs", "ideas", "IDEA-001.md")
    check("Id: CR-20261001-101500" in idea and "Change: Move sessions to Redis" in idea and "Priority: high" in idea
          and re.search(r"(Request|Solicitud): CR-20261001-101500", idea), "the request lives on as an IDEA with its block as it was", idea[:500])
    check(not os.path.exists(os.path.join(prop, "PROPOSAL-redis.md")) and not os.path.exists(os.path.join(prop, "PROPOSAL-odd-thing.md")),
          "the old PROPOSAL files are gone")
    names = [n for n in listing(p, "gtt-domain/proposals") if n.startswith("PROP-")]
    check(len(names) == 2 and any("redis" in n for n in names) and any("odd-thing" in n for n in names), "each became PROP-NNN-<slug>.md", str(names))
    redis = text(p, "gtt-domain", "proposals", next(n for n in names if "redis" in n))
    odd = text(p, "gtt-domain", "proposals", next(n for n in names if "odd" in n))
    check("Current decision: monolith" in redis and "Request: CR-20261001-101500" in redis and "Alternatives considered: none" in redis,
          "the body is kept as it was", redis[:600])
    check(re.search(r"(Origin|Origen): IDEA-001", redis) and re.search(r"(Level|Nivel): (architecture|arquitectura)", redis),
          "it cites the migrated request and takes its level from the title of its form", redis[:400])
    check(re.search(r"(Level|Nivel): (to confirm|por confirmar)", odd) and "Free text a person wrote" in odd,
          "a proposal with no form keeps its text and its level is left to confirm", odd[:400])
    check("Created" in redis or "Creada" in redis, "the creation date is written")
    rc, out, err = sh(p, ".gtt/scripts/gtt-pending.sh", "list", "--json")
    revs = [r for r in json.loads(out)["events"] if r["kind"] == "REV"] if rc == 0 and out.strip().startswith("{") else []
    check(len(revs) == 2, "each proposal opened its REV", out[:300] + err)
    check(text(p, "gtt-domain", "proposals", "ADR-DRAFT-0002-x.md") == before["ADR-DRAFT-0002-x.md"], "an agent's ADR draft is not touched")
    staged = json.loads(text(p, "gtt-domain", "proposals", "staged", "term", "promote.json"))
    check(staged.get("origin") == "legacy" and staged["files"][0]["to"] == "gtt-domain/context/glossary.md", "the staged set is marked legacy and keeps its files")
    rc, out, err = sh(p, ".gtt/scripts/gtt-change.sh", "proposals", "--json")
    check(rc == 0 and "term" in out, "the set is still listed to promote", out + err)

    after = tree_hash(p)
    rc, out, err = sh(p, INBOX, "migrate", "--apply")
    check(rc == 0 and "nothing to migrate" in out and tree_hash(p) == after, "25: running it again changes nothing", out + err)

    print("[migration] a desk that is empty or the template is removed without a trace; free text is never deleted")
    q = acc.fresh(project, tmp, "migrate-empty")
    write(os.path.join(q, "gtt-domain", "change-request.md"), DESK.replace("Change: Move sessions to Redis", "Change: <what needs to change>"))
    rc, out, err = sh(q, INBOX, "migrate", "--apply")
    check(rc == 0 and not os.path.exists(os.path.join(q, "gtt-domain", "change-request.md")) and not listing(q, "docs/ideas")[1:], "the template is removed, no idea is made", out + err)
    r = acc.fresh(project, tmp, "migrate-text")
    write(os.path.join(r, "gtt-domain", "change-request.md"), "# Change Request\n\nA note somebody wrote by hand.\n")
    rc, out, err = sh(r, INBOX, "migrate", "--apply")
    check(os.path.isfile(os.path.join(r, "gtt-domain", "change-request.md")) and "left where it is" in out, "text that is not a request is left where it is, and said", out + err)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.path.join(HERE, "..", ".."))
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    proj = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-inbox-session-")
    try:
        for scenario in (session, migration):
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
