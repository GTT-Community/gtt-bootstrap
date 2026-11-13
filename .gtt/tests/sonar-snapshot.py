#!/usr/bin/env python3
"""GTT Sonar - tests of the snapshot (Prompt 1): the sonar.v1 contract, criterion 1 (derived and disposable)
and criterion 8 (one state per repo with worktrees).

Every scenario runs on a DISPOSABLE copy of this project; the project itself is never modified.

  python .gtt/tests/sonar-snapshot.py [--project .]

Exit 0 = every check held, 1 = at least one failed.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

FAILS, COUNT = [], 0
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

BACKLOG = """# Backlog

## Epics

### EPIC-001 — Base platform
**Status:** In Progress
**Goal:** the platform runs
**Lane:** A
**Estimate:** 6h
**Approved:** human — 2026-11-01

#### Stories

##### STORY-001 — Schema
- **Status:** Done
- **Estimate:** 2h
- **Done when:** E-1 passes
- **Closed:** 2026-11-02 — abc1234 — tests passed

##### STORY-002 — Endpoint & "quotes" $HOME
- **Status:** In Progress
- **Estimate:** 2h

##### STORY-003 — Tests
- **Status:** Planned
- **Estimate:** 2h

### EPIC-002 — Sync offline
**Status:** Proposed
**Lane:** B
**Estimate:** 4h

#### Stories

##### STORY-004 — Queue
- **Status:** Planned
"""

TOP = {"schema", "generated_at", "repo", "suite_version", "lang", "project", "summary", "columns", "lanes", "epics",
       "stories", "next", "needs_you", "repo_state", "signals", "health", "recent", "ideas", "docs",
       "working_now", "throughput", "refresh", "degraded", "inbox", "inbox_counts", "decisions", "me"}
HOSTILE = '<img src=x onerror="window.PWNED=9"> & <script>window.PWNED=8</script>'



def check(cond, label, detail=""):
    global COUNT
    COUNT += 1
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        FAILS.append(label)


def run(cwd, *argv, env=None):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=env, timeout=120)


def snapshot(cwd):
    proc = run(cwd, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json")
    return proc, (json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None)


def stable(snap):
    snap = dict(snap)
    snap.pop("generated_at", None)
    return snap


def make_project(project):
    tmp = tempfile.mkdtemp(prefix="gtt-sonar-test-")
    dest = os.path.join(tmp, "proj")
    shutil.copytree(project, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "local"))
    git = lambda *a: run(dest, "git", "-c", "user.name=t", "-c", "user.email=t@t", *a)
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    with open(os.path.join(dest, "gtt-domain", "backlog.md"), "w", encoding="utf-8") as handle:
        handle.write(BACKLOG)           # uncommitted: the main checkout holds the state
    ask = run(dest, "bash", ".gtt/scripts/gtt-pending.sh", "ask", "--type", "product", "--question", "<img src=x onerror=alert(1)> PowerSync on your server or in the cloud?",
              "--why", "it changes the deploy", "--option", "Server | I use your server", "--option", "Cloud | I use the cloud",
              "--recommended", "1", "--blocks", "STORY-002", "--header", "PowerSync", "--apply")
    return tmp, dest, ask


def ago(days):
    return (datetime.date.today() - datetime.timedelta(days=days)).isoformat()


def write(dest, path, text):
    full = os.path.join(dest, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def entry_text(ref, title, header, body, trail):
    return (f"# {ref} · {title}\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md\n\n"
            f"{header}\n\n{body}\n" + ("\n---\n" + "\n".join(trail) + "\n" if trail else ""))


def inbox_scenario(dest, hostile=True):
    """Every stage and every type of the Bandeja, on a project that speaks English: an idea, a request and an ADR draft
    written by a person; proposals of the agent in review, accepted, ready to ratify (a staged set, a run, an approval), in
    work, closed, parked and rejected; two REV (one for a person of the team); a hand-written ADR; decisions in the registries.
    With `hostile`, titles, bodies and trail lines carry markup that must stay text."""
    evil = HOSTILE if hostile else "plain"
    d = ago
    H = lambda who, day, kind: f"Author: {who} · Created: {day}" + (f" · Type: {kind}" if kind else "")
    P = lambda day, level, origin, extra="": f"Author: agent (claude) · Created: {day} · Level: {level} · Route: {({'specification': 'spec', 'architecture': 'arch', 'scope': 'scope'})[level]} · Origin: {origin}{extra}"
    files = {
        "docs/ideas/IDEA-001-new.md": entry_text("IDEA-001", "Sync plots without signal " + evil, H("human (Ana)", d(1), "idea"), "Plain idea text.\n" + evil, []),
        "docs/ideas/IDEA-002-request.md": entry_text("IDEA-002", "Offline orders request", H("human (Ana)", d(2), "request"), "Change: queue orders\nReason: no signal\nPriority: high", []),
        "gtt-domain/adr/drafts/IDEA-003-adr.md": entry_text("IDEA-003", "Use PowerSync for sync", H("human (Luis)", d(3), "adr") + " · Level: architecture", "## Context\n\nDraft of an ADR.", []),
        "docs/ideas/IDEA-004-review.md": entry_text("IDEA-004", "Split the billing module", H("human (Ana)", d(4), "idea"), "Body", [f"Triage: specification → PROP-001 · {d(3)} · agent"]),
        "gtt-domain/proposals/PROP-001-billing.md": entry_text("PROP-001", "Split the billing module " + evil, P(d(3), "specification", "IDEA-004", "\nForm: 4"), "Proposal body.\n" + evil,
                                                                [f"Review: REV-001 · {d(2)} · gtt"]),
        "gtt-domain/proposals/PROP-002-accepted.md": entry_text("PROP-002", "Cache the catalog", P(d(5), "scope", "OBS-1"), "Body", [f"Review: REV-009 · {d(4)} · gtt", f"Decision: accepted, priority urgent · {d(1)} · human (gtt answer 9 2)"]),
        "gtt-domain/proposals/PROP-003-set.md": entry_text("PROP-003", "Add audit trail", P(d(6), "specification", "session"), "Body",
                                                            [f"Review: REV-010 · {d(5)} · gtt", f"Decision: accepted, priority normal · {d(4)} · human", f"Package: ready-set · {d(1)} · agent"]),
        "gtt-domain/proposals/PROP-004-run.md": entry_text("PROP-004", "Offline mode epic", P(d(7), "scope", "STORY-001"), "Body",
                                                            [f"Review: REV-011 · {d(6)} · gtt", f"Decision: accepted, priority normal · {d(5)} · human", f"Package: RUN-004 (design-EPIC-009 + gtt approve EPIC-009) · {d(2)} · agent"]),
        "gtt-domain/proposals/PROP-005-approve.md": entry_text("PROP-005", "A new Epic to approve", P(d(7), "scope", "IDEA-009"), "Body",
                                                                [f"Decision: accepted, priority low · {d(5)} · human", f"Package: gtt approve EPIC-010 · {d(2)} · agent"]),
        "gtt-domain/proposals/PROP-006-work.md": entry_text("PROP-006", "Reports Epic in work", P(d(9), "scope", "IDEA-005"), "Body",
                                                             [f"Decision: accepted, priority normal · {d(8)} · human", f"Package: gtt approve EPIC-011 · {d(6)} · agent", f"Ratified: gtt approve EPIC-011 · {d(3)} · human", f"Work: EPIC-011 {evil} · {d(3)} · gtt"]),
        "gtt-domain/proposals/done/PROP-007-closed.md": entry_text("PROP-007", "Closed this week", P(d(12), "specification", "IDEA-006"), "Body", [f"Decision: accepted, priority normal · {d(10)} · human", f"Ratified: gtt promote x · {d(4)} · human", f"Closed: done (CHANGE-0001 recorded) · {d(2)} · gtt"]),
        "gtt-domain/proposals/done/PROP-008-oldclosed.md": entry_text("PROP-008", "Closed long ago", P(d(40), "specification", "IDEA-007"), "Body", [f"Decision: accepted, priority normal · {d(39)} · human", f"Closed: done · {d(30)} · gtt"]),
        "docs/ideas/IDEA-010-parked.md": entry_text("IDEA-010", "Parked idea", H("human (Ana)", d(20), "idea"), "Body", [f"Parked: {d(15)}"]),
        "gtt-domain/proposals/withdrawn/PROP-009-rejected.md": entry_text("PROP-009", "Rejected proposal", P(d(8), "scope", "IDEA-011"), "Body", [f"Review: REV-012 · {d(7)} · gtt", f"Rejected: no · {d(5)} · human"]),
    }
    for path, text in files.items():
        write(dest, path, text)
    os.makedirs(os.path.join(dest, "gtt-domain", "proposals", "staged", "ready-set"), exist_ok=True)
    json.dump({"reason": "Add the audit trail", "origin": "PROP-003", "files": []}, open(os.path.join(dest, "gtt-domain", "proposals", "staged", "ready-set", "promote.json"), "w"))
    os.makedirs(os.path.join(dest, "gtt-domain", "proposals", "staged", "orphan-set"), exist_ok=True)
    json.dump({"reason": "A set that names its origin", "origin": "IDEA-004", "files": []}, open(os.path.join(dest, "gtt-domain", "proposals", "staged", "orphan-set", "promote.json"), "w"))
    # two reviews: one for a person of the team
    code = ("import sys; sys.path.insert(0, '.gtt/scripts'); import gtt_pending as p; c = p.contract()\n"
            "for ref, title, level, who in (('PROP-001', %r, 'spec', 'Ana'), ('IDEA-001', 'Sync plots without signal', 'scope', 'Luis')):\n"
            "    p.open_rev(c, {'ref': ref, 'title': title, 'level': level, 'sha': '3f9a' * 16, 'origin': 'IDEA-004' if ref == 'PROP-001' else None, 'for': who}, True)\n") % ("Split billing " + evil[:40],)
    made = run(dest, sys.executable, "-c", code)
    # a hand-written ADR, and the registries
    write(dest, "gtt-domain/adr/ADR-002-queues.md", f"# ADR-002 — Use a queue for sync\n\n- Status: Accepted\n- Date: {d(3)}\n- Origin: PROP-001\n- Approved by: Solution Designer\n\n## Context\n\nc\n")
    write(dest, "gtt-domain/adr/ADR-003-" + "hand.md", f"# ADR-003 — Written by hand " + evil + f"\n\n- Status: Accepted\n- Date: {d(1)}\n- Approved by: Solution Designer\n")
    stack = os.path.join(dest, "gtt-domain", "context", "stack.md")
    text = open(stack, encoding="utf-8").read()
    text = text.replace("| Date | ADR or CHANGE | What changed |\n|---|---|---|\n| | | |\n", f"| Date | ADR or CHANGE | What changed |\n|---|---|---|\n| {d(2)} | CHANGE-0001 | the catalog gets a cache (PROP-007) |\n| {d(8)} | ADR-002 | queue for sync (PROP-001) |\n", 1)
    open(stack, "w", encoding="utf-8").write(text)
    return made


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=ROOT)
    args = parser.parse_args()
    tmp, dest, ask = make_project(os.path.abspath(args.project))
    try:
        print("snapshot - the sonar.v1 contract")
        check(ask.returncode == 0, "a pending question can be created for the scenario", ask.stderr[-200:])
        proc, snap = snapshot(dest)
        check(proc.returncode == 0 and snap is not None, "gtt-sonar.sh snapshot --json exits 0 with JSON", proc.stderr[-300:])
        if snap is None:
            return finish()
        check(set(snap) == TOP, "the document has exactly the sonar.v1 sections", str(set(snap) ^ TOP))
        check(snap["schema"] == "sonar.v1", "schema is sonar.v1")
        release = json.load(open(os.path.join(dest, ".gtt", "contract", "release.json"), encoding="utf-8"))
        check(snap["suite_version"] == release["bootstrap"]["version"], "suite_version comes from release.json")
        check(snap["lang"] in ("es", "en") and snap["project"]["phase"] in ("THINK", "DEV"), "lang and phase are valid")
        check([e["ref"] for e in snap["epics"]] == ["EPIC-001", "EPIC-002"], "epics come from the backlog")
        check(snap["epics"][0]["title"] == "Base platform" and snap["epics"][0]["state"] == "in_progress", "an Epic carries its title and state")
        check(snap["epics"][0]["stories"] == {"done": 1, "in_progress": 1, "blocked": 0, "planned": 1}, "an Epic counts its Stories by state", str(snap["epics"][0]["stories"]))
        check(any(s["ref"] == "STORY-002" and "$HOME" in (s["title"] or "") for s in snap["stories"]), "a title is carried as raw text for the page to escape")
        check(snap["summary"]["stories_done"] == 1 and snap["summary"]["stories_total"] == 4 and snap["summary"]["progress_pct"] == 25, "summary counts", str(snap["summary"]))
        check(snap["summary"]["deadline"] is None and snap["summary"]["calibration"]["ratio"] is None and snap["summary"]["calibration"]["uncalibrated"] is True, "what GTT does not yet calculate is null")
        check(next(s for s in snap["stories"] if s["ref"] == "STORY-001")["closed_by_evidence"] is True, "a Done Story with `Closed` counts as closed by evidence")
        check(next(s for s in snap["stories"] if s["ref"] == "STORY-002")["closed_by_evidence"] is False, "an open Story is not closed by evidence")
        check([e["ref"] for e in snap["next"]["epics_to_approve"]] == ["EPIC-002"], "a Proposed Epic with no movement waits, listed apart")
        cmds = {n["ref"]: n["command"] for n in snap["needs_you"]}
        check("EPIC-002" not in cmds, "a Proposed Epic with no movement is not 'I need you'", str(cmds))
        check(snap["next"]["epics_to_approve"][0]["command"] == f"cd '{dest}' && gtt approve EPIC-002", "its command carries the way to the project", snap["next"]["epics_to_approve"][0]["command"])
        ask_ref = next((r for r in cmds if r.startswith("ASK-")), None)
        check(ask_ref is not None and cmds[ask_ref].startswith(f"cd '{dest}' && gtt answer ") and cmds[ask_ref].endswith(" 1"), "a question brings its command with the recommended option", str(cmds))
        check(all(n["command"] for n in snap["needs_you"] if n["kind"] != "blocked"), "every act the human must do carries a command")
        ask_need = next(n for n in snap["needs_you"] if n["ref"] == ask_ref)
        check(ask_need["how"] in ("decide", "provide") and isinstance(ask_need["choices"], list), "a question says how the human unblocks it", str(ask_need))
        check(all(c["command"].startswith(f"cd '{dest}' && gtt answer ") for c in ask_need["choices"]), "each choice carries its own command")
        check(snap["repo_state"] is None or isinstance(snap["repo_state"]["uncommitted"], int), "repo_state is a count or no data, never a guess", str(snap["repo_state"]))
        started = subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "start"], cwd=dest, capture_output=True, text=True, timeout=60)
        lines = [l for l in started.stdout.splitlines() if l.strip()]
        check(started.returncode == 0 and len(lines) == 1 and lines[0].startswith("Sonar:") and "file://" in lines[0] and "sonar.html" in lines[0],
              "`start` prints exactly one line: where the page is and what waits", started.stdout + started.stderr)
        check(not os.path.exists(os.path.join(dest, ".gtt", "local", "sonar-opened")), "`start` opens nothing unless the human asked for it")
        prefs_run = subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "prefs", "--open-on-start", "on"], cwd=dest, capture_output=True, text=True, timeout=60)
        prefs_file = json.load(open(os.path.join(dest, ".gtt", "local", "sonar-prefs.json"), encoding="utf-8"))
        check(prefs_run.returncode == 0 and prefs_file == {"open_on_start": True}, "the preference is kept in .gtt/local/, outside git", str(prefs_file))
        subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "prefs", "--open-on-start", "off"], cwd=dest, capture_output=True, text=True, timeout=60)
        # the session start rewrites session.md: it runs on a copy so the criteria below see the project untouched
        copy = tempfile.mkdtemp(prefix="sonar-ctx-")
        shutil.copytree(dest, os.path.join(copy, "p"), symlinks=True)
        context = subprocess.run(["bash", ".gtt/scripts/gtt-session-context.sh"], cwd=os.path.join(copy, "p"), capture_output=True, text=True, timeout=120)
        shutil.rmtree(copy, ignore_errors=True)
        check("## Sonar (say this line once" in context.stdout, "the session context carries the Sonar line", context.stderr[-200:])
        # the backlog view: Epic and Story detail is in every snapshot; the documents only when asked (the portfolio stays light)
        e1 = next(e for e in snap["epics"] if e["ref"] == "EPIC-001")
        check(e1["goal"] == "the platform runs" and e1["approved"].startswith("human") and e1["status"] == "In Progress", "an Epic carries its goal, approval and status", str(e1))
        check(next(s for s in snap["stories"] if s["ref"] == "STORY-001")["done_when"] == "E-1 passes" and "tests passed" in next(s for s in snap["stories"] if s["ref"] == "STORY-001")["closed"],
              "a Story carries what makes it done and what closed it")
        check(snap["docs"] is None, "without --docs the snapshot carries no documents (null: no data)")
        hostile_doc = os.path.join(dest, "gtt-domain", "context", "glossary.md")
        q_glossary_original = open(hostile_doc, encoding="utf-8").read()
        with open(hostile_doc, "a", encoding="utf-8") as handle:
            handle.write("\n## Hostile <script>alert(1)</script>\n\n<img src=x onerror=alert(1)> and [a link](javascript:alert(1)) and `code`\n\n| a | b |\n|---|---|\n| <b>1</b> | 2 |\n")
        withdocs = subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json", "--docs"], cwd=dest, capture_output=True, text=True, timeout=60)
        dd = json.loads(withdocs.stdout)["docs"]
        groups = {i["group"] for i in dd["items"]}
        check({"context"} <= groups and all(i["blocks"] is not None for i in dd["items"]), "--docs brings the governed documents as blocks", str(groups))
        flat = json.dumps(next(i for i in dd["items"] if i["path"].endswith("glossary.md"))["blocks"])
        check("javascript:alert" not in flat and "alert(1)" in flat and any(b[0] == "table" for b in next(i for i in dd["items"] if i["path"].endswith("glossary.md"))["blocks"]),
              "hostile text stays plain text, a link keeps only its label and a table stays a table")
        tiny = subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json", "--docs"], cwd=dest, capture_output=True, text=True, timeout=60,
                              env=dict(os.environ, GTT_SONAR_DOCS_TOTAL_LIMIT="200"))
        omitted = [i for i in json.loads(tiny.stdout)["docs"]["items"] if i["omitted"]]
        check(omitted and all(i["blocks"] is None and i["path"] for i in omitted), "a document that does not fit is listed as omitted with its path, never dropped silently", str(len(omitted)))
        with open(hostile_doc, "w", encoding="utf-8") as handle:                      # put the project back for the criteria below
            handle.write(q_glossary_original)
        weights = [(n["weight"]["stories"] or 0) for n in snap["needs_you"]]
        check(weights == sorted(weights, reverse=True), "needs_you is ordered by weight", str(weights))
        check(all(r["actor"] in ("human", "agent", "gtt", None) for r in snap["recent"]), "actor is human, agent, gtt or unknown, never guessed")

        print("criterion 1 - derived and disposable")
        local = os.path.join(dest, ".gtt", "local")
        before = os.listdir(local) if os.path.isdir(local) else []
        _, again = snapshot(dest)
        after = os.listdir(local) if os.path.isdir(local) else []
        check(stable(again) == stable(snap), "running again gives the same snapshot")
        check(before == after, "the snapshot writes nothing", f"{before} -> {after}")
        for name in ("sonar.json", "sonar.html"):
            path = os.path.join(local, name)
            if os.path.exists(path):
                os.remove(path)
        _, third = snapshot(dest)
        check(stable(third) == stable(snap), "deleting .gtt/local/sonar.* loses nothing")

        print("criterion 8 - two worktrees, one state per repo")
        wt = os.path.join(tmp, "wt-b")
        made = run(dest, "git", "worktree", "add", "-q", wt, "-b", "gtt/b")
        check(made.returncode == 0, "a linked worktree can be created", made.stderr[-200:])
        if made.returncode == 0:
            proc, from_wt = snapshot(wt)
            check(proc.returncode == 0 and from_wt is not None, "the snapshot runs from the worktree", proc.stderr[-300:])
            if from_wt:
                check(from_wt["repo"]["path"] == snap["repo"]["path"], "the worktree reports the repo, not itself", from_wt["repo"]["path"])
                check(stable(from_wt) == stable(snap), "the worktree sees the same single state")

        print("'I need you' holds only what holds work back")
        epics = ""
        for n, states in ((10, ("Done", "Done", "Planned")), (11, ("In Progress", "Planned")), (12, ("Done",)), (13, ("Planned", "Planned"))):
            epics += f"### EPIC-0{n} — Epic {n}\n**Status:** Proposed\n**Lane:** A\n**Estimate:** 2h\n\n#### Stories\n\n"
            for i, s in enumerate(states):
                epics += f"##### STORY-{n}{i} — Story {n}{i}\n- **Status:** {s}\n- **Estimate:** 1h\n\n"
        with open(os.path.join(dest, "gtt-domain", "backlog.md"), "w", encoding="utf-8") as handle:
            handle.write("# Backlog\n\n## Epics\n\n" + epics)
        staged = os.path.join(dest, "gtt-domain", "proposals", "staged")
        os.makedirs(os.path.join(staged, "ready-set"), exist_ok=True)
        os.makedirs(os.path.join(staged, "leftover-folder"), exist_ok=True)
        json.dump({"reason": "a set", "files": []}, open(os.path.join(staged, "ready-set", "promote.json"), "w"))
        _, s2 = snapshot(dest)
        kinds = {n["ref"]: n for n in s2["needs_you"]}
        check({"EPIC-010", "EPIC-011", "EPIC-012"} <= set(kinds) and "EPIC-013" not in kinds, "Epics with work done or under way need you; the idle one does not", str(list(kinds)))
        check([e["ref"] for e in s2["next"]["epics_to_approve"]] == ["EPIC-013"], "the idle Epic is listed apart")
        check(kinds["EPIC-010"]["weight"]["stories"] == 1 and kinds["EPIC-012"]["weight"]["stories"] == 0, "the weight counts open Stories, not the finished ones", str(kinds["EPIC-010"]["weight"]))
        check(kinds["EPIC-011"]["unblocks"] == ["STORY-111"] or "STORY-110" in kinds["EPIC-011"]["unblocks"], "it says which Stories it unblocks", str(kinds["EPIC-011"]["unblocks"]))
        batch = [n for n in s2["needs_you"] if n["kind"] == "epic-batch"]
        check(len(batch) == 1 and batch[0]["refs"] == ["EPIC-010", "EPIC-011", "EPIC-012"] and s2["needs_you"][0]["kind"] == "epic-batch", "three or more are one batch, first", str(batch))
        check(batch and batch[0]["command"] == f"cd '{dest}' && for e in EPIC-010 EPIC-011 EPIC-012; do gtt approve $e; done", "the batch is one command", batch[0]["command"] if batch else "")
        props = {p["ref"]: p for p in s2["next"]["proposals"]}
        check("ready-set" in props and "leftover-folder" not in props and props["ready-set"]["command"].endswith("gtt promote ready-set"), "only a promotion set that is ready to apply is offered", str(list(props)))

        print("what the backlog already says: release, front, reason, hours, health, watcher")
        facts = """# Backlog

## Epics

### EPIC-020 — Facts
**Status:** In Progress
**Goal:** facts
**Approved:** human — 2026-11-01

#### Stories

##### STORY-201 — One
- **Status:** Done
- **Estimate:** 2h
- **Release:** v1 · **Frente:** A
- **Closed:** 2026-11-02 — abc1234 — tests passed

##### STORY-202 — Two
- **Status:** In Progress
- **Estimate:** 6h
- **Release:** v1 · **Frente:** B

##### STORY-203 — Three
- **Status:** Blocked
- **Estimate:** 2h
- **Release:** v1.1; rigor
- **Blocked by:** waits for the owner's decision on the limit (2026-11-05)

##### STORY-204 — Four
- **Status:** Planned
- **Release:** post-v1 (fuera del alcance de v1, decidido el 2026-11-10)
- **Blocked by:** — (nothing)
"""
        with open(os.path.join(dest, "gtt-domain", "backlog.md"), "w", encoding="utf-8") as handle:
            handle.write(facts)
        os.makedirs(os.path.join(dest, ".gtt", "local", "health"), exist_ok=True)
        with open(os.path.join(dest, ".gtt", "local", "health", "audit.json"), "w", encoding="utf-8") as handle:
            json.dump({"title": "Audit", "status": "warn", "detail": "22 of 24 alarms closed", "at": "2020-01-01T00:00:00Z"}, handle)
        with open(os.path.join(dest, ".gtt", "local", "health", "broken.json"), "w", encoding="utf-8") as handle:
            handle.write("{not json")
        _, s3 = snapshot(dest)
        by = {x["ref"]: x for x in s3["stories"]}
        check(by["STORY-201"]["release"] == "v1" and by["STORY-201"]["front"] == "A", "a Story carries its release and its front", str(by["STORY-201"]))
        check(by["STORY-203"]["release"] == "v1.1", "a release name stops at the first separator", str(by["STORY-203"]["release"]))
        check(by["STORY-203"]["blocked_by"].startswith("waits for the owner"), "a blocked Story carries the author's reason")
        check(by["STORY-204"]["blocked_by"] is None and by["STORY-204"]["out_of_scope"] is True, "a `—` reason is no reason; `post-` is out of scope")
        blocked = [n for n in s3["needs_you"] if n["kind"] == "blocked"]
        check(blocked and blocked[0]["note"].startswith("waits for the owner"), "the blocked row says why, not 'no question explains it'", str(blocked))
        sm = s3["summary"]
        check(sm["in_scope"] == {"done": 1, "total": 3, "pct": 33, "excluded": 1}, "progress in scope leaves out what is out of scope", str(sm["in_scope"]))
        check(sm["hours"]["done"] == 2.0 and sm["hours"]["total"] == 10.0 and sm["hours"]["pct"] == 20, "hours done over hours estimated", str(sm["hours"]))
        check([r["name"] for r in sm["releases"]] == ["v1", "v1.1", "post-v1"], "progress by release, in order of appearance", str(sm["releases"]))
        check([w["ref"] for w in s3["working_now"]] == ["STORY-202"] and s3["working_now"][0]["front"] == "B", "what is in progress now is listed with its front")
        check([h["id"] for h in s3["health"]] == ["audit"] and s3["health"][0]["status"] == "warn" and s3["health"][0]["stale"] is True, "a health file is read, an unreadable one is skipped, an old one is stale", str(s3["health"]))
        check(any(r["ref"] == "STORY-201" and r.get("derived") for r in s3["recent"]), "without a log, the `Closed` lines say what was finished")
        check(s3["throughput"]["days"] and len(s3["throughput"]["days"]) == 14, "throughput covers fourteen days")
        check(s3["degraded"] is None and s3["refresh"] == "hook", "a complete Bootstrap is not degraded; no watcher means refresh by hook")
        os.remove(os.path.join(dest, ".gtt", "contract", "pending.json"))
        _, s4 = snapshot(dest)
        check(s4["degraded"] and "pending" in s4["degraded"]["missing"] and s4["degraded"]["command"].endswith("gtt update"), "a Bootstrap without pending events says what is missing and the act that fixes it", str(s4["degraded"]))
        w = run(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "watch", "--hours", "0.002", env=dict(os.environ, GTT_SONAR_NO_WATCH="1"))
        check(w.returncode == 0 and not os.path.exists(os.path.join(dest, ".gtt", "local", "sonar-watch.pid")), "the watcher renders, ends by itself and leaves no pid file", w.stderr[-200:])
        check(os.path.isfile(os.path.join(dest, ".gtt", "local", "sonar.html")), "the watcher wrote the page")

        print("criterion 24 - the Bandeja in the snapshot")
        before_inbox = {n: os.path.getmtime(os.path.join(dest, "gtt-domain", "proposals", n)) for n in os.listdir(os.path.join(dest, "gtt-domain", "proposals")) if n.endswith(".md")}
        _, empty = snapshot(dest)
        check(empty["inbox"] == [] and empty["decisions"] is not None and set(empty["inbox_counts"]) >= {"new", "review", "accepted", "ratify", "work"}, "an empty inbox is a list, not null", str(empty["inbox"]))
        shutil.copyfile(os.path.join(os.path.abspath(args.project), ".gtt", "contract", "pending.json"), os.path.join(dest, ".gtt", "contract", "pending.json"))   # the degraded scenario removed it
        made = inbox_scenario(dest)
        check(made.returncode == 0, "the scenario can open its reviews", made.stderr[-300:])
        recon = os.path.join(dest, ".gtt", "scripts", "gtt_inbox_reconcile.py")
        if True:     # the real reconcile lists nothing before a freeze: a stub, in the disposable copy, says which ADR was written by hand (same shape: path, name, command)
            with open(recon, "w", encoding="utf-8") as handle:
                handle.write('def adr_hand():\n    return [{"path": "gtt-domain/adr/ADR-003-hand.md", "name": "ADR-003-hand.md", "command": "gtt adr adopt gtt-domain/adr/ADR-003-hand.md"}]\n')
        proc, s24 = snapshot(dest)
        check(proc.returncode == 0 and s24 is not None and "inbox" in s24, "the snapshot carries inbox, inbox_counts and decisions", proc.stderr[-300:])
        rows = {r["ref"]: r for r in s24["inbox"]}
        check({"IDEA-001", "IDEA-002", "IDEA-003", "PROP-001", "PROP-002", "PROP-003", "PROP-006", "PROP-007", "IDEA-010", "PROP-009"} <= set(rows), "every stage and type is listed", str(sorted(rows)))
        check({r["type"] for r in rows.values()} == {"idea", "solicitud", "adr", "proposal"}, "the four types appear", str({r["type"] for r in rows.values()}))
        check({r["stage"] for r in rows.values()} == {"new", "review", "accepted", "ratify", "work", "closed", "parked", "rejected"}, "the eight stages appear", str({r["stage"] for r in rows.values()}))
        check("IDEA-004" not in rows and rows["PROP-001"]["from"] == "IDEA-004", "an idea that became a proposal is not listed twice: the card says `from IDEA-n`")
        check("PROP-008" not in rows, "a proposal closed long ago leaves the board")
        want = {"ref", "type", "origin", "from", "title", "level", "stage", "priority", "days_in_stage", "event", "for", "command", "trail"}
        check(all(want <= set(r) for r in rows.values()), "every card has the fields of section 11.5")
        check(rows["IDEA-001"]["origin"] == "human" and rows["PROP-001"]["origin"] == "agent", "origin says who wrote it: human or agent")
        check(rows["PROP-002"]["priority"] == "urgent" and rows["PROP-001"]["priority"] is None, "priority comes from the trail, null when none")
        check((rows["PROP-001"]["event"] or "").startswith("REV-") and rows["PROP-001"]["for"] == "Ana" and " gtt answer " in rows["PROP-001"]["command"] and rows["PROP-001"]["command"].endswith(" 1"), "a card in review names its REV, who it is for and the act", str(rows["PROP-001"]))
        check(rows["PROP-001"]["days_in_stage"] == 2 and rows["IDEA-010"]["days_in_stage"] == 15, "days in the stage count from the last change", str((rows["PROP-001"]["days_in_stage"], rows["IDEA-010"]["days_in_stage"])))
        check(rows["PROP-003"]["command"].endswith("gtt promote ready-set") and rows["PROP-004"]["command"].endswith("gtt run 4") and rows["PROP-005"]["command"].endswith("gtt approve EPIC-010"),
              "a package to ratify brings promote, run or approve", str([rows[k]["command"] for k in ("PROP-003", "PROP-004", "PROP-005")]))
        check(rows["IDEA-001"]["command"] is None and rows["PROP-006"]["command"] is None, "what asks nothing of the human has no command")
        check(len(rows["PROP-006"]["trail"]) == 4 and rows["PROP-006"]["trail"][0]["key"] == "decision" and rows["PROP-006"]["trail"][0]["label"] == "Decision", "the full trail travels, with the label of the project's language")
        check("<img" in rows["IDEA-001"]["title"] and "<script>" in rows["IDEA-001"]["text"], "titles and texts travel raw: the page escapes them")
        c24 = s24["inbox_counts"]
        check(c24["new"] == 3 and c24["review"] == 1 and c24["accepted"] == 1 and c24["ratify"] == 3 and c24["work"] == 1 and c24["closed"] == 1, "inbox_counts counts each stage", str(c24))
        by_kind = {}
        for n in s24["needs_you"]:
            by_kind.setdefault(n["kind"], []).append(n)
        revs = by_kind.get("review", [])
        check(len(revs) == 2 and all(len(n["choices"]) == 5 and n["choices"][0]["command"].endswith(f" gtt answer {int(n['ref'][4:])} 1") for n in revs), "needs_you: a review brings one `gtt answer N k` per option", str(revs[:1]))
        check({n["for"] for n in revs} == {"Ana", "Luis"}, "a review says who it is for")
        rat = {n["ref"]: n for n in by_kind.get("ratify", [])}
        check({"PROP-003", "PROP-004", "PROP-005", "orphan-set"} <= set(rat), "needs_you: a package ready to ratify waits for the human, also a set that names its origin", str(list(rat)))
        check(rat["PROP-003"]["command"].endswith("gtt promote ready-set") and rat["PROP-004"]["command"].endswith("gtt run 4") and rat["PROP-005"]["command"].endswith("gtt approve EPIC-010"), "ratify commands: promote <set>, run n, approve EPIC-n")
        hand = by_kind.get("adr-hand", [])
        check(len(hand) == 1 and hand[0]["command"].endswith("gtt adr adopt gtt-domain/adr/ADR-003-hand.md"), "needs_you: an ADR written by hand brings `gtt adr adopt <file>`", str(hand))
        order24 = [n["kind"] for n in s24["needs_you"]]
        check(order24.index("review") < order24.index("ratify") < order24.index("adr-hand"), "at equal weight: reviews, then ratify, then hand-written ADRs", str(order24))
        dec = {d["ref"]: d for d in s24["decisions"]}
        check({"ADR-002", "ADR-003", "CHANGE-0001"} <= set(dec) and list(dec.values()) == sorted(dec.values(), key=lambda d: (d["at"] or "", d["ref"]), reverse=True), "decisions: ADR and CHANGE, newest first", str(list(dec)))
        check(dec["ADR-002"]["origin"] == "PROP-001" and dec["ADR-002"]["entry"] == "PROP-001" and dec["CHANGE-0001"]["origin"] == "PROP-007" and dec["CHANGE-0001"]["kind"] == "change", "a decision names its origin and links the entry that produced it", str(dec["CHANGE-0001"]))
        check(dec["ADR-003"]["origin"] is None and dec["ADR-003"]["entry"] is None, "an ADR with no origin says null")
        check(len(s24["decisions"]) <= 10, "decisions are at most 10")
        check(isinstance(s24["me"], (str, type(None))), "`me` is the git user name or null")
        check(all(k in s24 for k in TOP), "sonar.v1 keeps every field of before (`ideas` among them)")
        after_inbox = {n: os.path.getmtime(os.path.join(dest, "gtt-domain", "proposals", n)) for n in os.listdir(os.path.join(dest, "gtt-domain", "proposals")) if n.endswith(".md") and n in before_inbox}
        check(after_inbox == before_inbox, "the snapshot writes nothing")
        # an Epic carries its Origin and Priority
        with open(os.path.join(dest, "gtt-domain", "backlog.md"), "w", encoding="utf-8") as handle:
            handle.write("# Backlog\n\n## Epics\n\n### EPIC-030 — With origin\n**Status:** Proposed\n**Origin:** PROP-005\n**Priority:** urgent\n\n### EPIC-031 — Without\n**Status:** Proposed\n**Origin:** —\n")
        _, s25 = snapshot(dest)
        e30, e31 = s25["epics"][0], s25["epics"][1]
        check(e30["origin"] == "PROP-005" and e30["priority"] == "urgent" and e31["origin"] is None and e31["priority"] is None, "each Epic carries Origin and Priority, null when absent", str((e30, e31)))
        # a Bootstrap without the inbox: no data, never a guess
        os.rename(os.path.join(dest, ".gtt", "contract", "inbox.json"), os.path.join(dest, ".gtt", "contract", "inbox.json.off"))
        _, s26 = snapshot(dest)
        check(s26 is not None and s26["inbox"] is None and s26["inbox_counts"] is None and not [n for n in s26["needs_you"] if n["kind"] in ("review", "ratify")], "without the inbox contract: null, and the rest still comes", str(s26 and s26["inbox"]))
        os.rename(os.path.join(dest, ".gtt", "contract", "inbox.json.off"), os.path.join(dest, ".gtt", "contract", "inbox.json"))

        print("budget")
        started = time.time()
        snapshot(dest)
        elapsed = time.time() - started
        print(f"  info  snapshot of a small project: {elapsed:.2f}s")
        check(elapsed < 1.5, "the snapshot of a small project is under 1.5s", f"{elapsed:.2f}s")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return finish()


def finish():
    print(f"\n{COUNT - len(FAILS)}/{COUNT} checks held" + (f"; FAILED: {', '.join(FAILS)}" if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
