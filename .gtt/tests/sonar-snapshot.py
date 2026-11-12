#!/usr/bin/env python3
"""GTT Sonar - tests of the snapshot (Prompt 1): the sonar.v1 contract, criterion 1 (derived and disposable)
and criterion 8 (one state per repo with worktrees).

Every scenario runs on a DISPOSABLE copy of this project; the project itself is never modified.

  python .gtt/tests/sonar-snapshot.py [--project .]

Exit 0 = every check held, 1 = at least one failed.
"""

import argparse
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
       "stories", "next", "needs_you", "repo_state", "signals", "health", "recent", "ideas", "docs"}


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
