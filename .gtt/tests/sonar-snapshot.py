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
       "stories", "next", "needs_you", "signals", "health", "recent", "ideas"}


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
        check(snap["epics"][0]["stories"] == {"done": 1, "in_progress": 1, "planned": 1}, "an Epic counts its Stories by state", str(snap["epics"][0]["stories"]))
        check(any(s["ref"] == "STORY-002" and "$HOME" in (s["title"] or "") for s in snap["stories"]), "a title is carried as raw text for the page to escape")
        check(snap["summary"]["stories_done"] == 1 and snap["summary"]["stories_total"] == 4 and snap["summary"]["progress_pct"] == 25, "summary counts", str(snap["summary"]))
        check(snap["summary"]["deadline"] is None and snap["summary"]["calibration"]["ratio"] is None and snap["summary"]["calibration"]["uncalibrated"] is True, "what GTT does not yet calculate is null")
        check(next(s for s in snap["stories"] if s["ref"] == "STORY-001")["closed_by_evidence"] is True, "a Done Story with `Closed` counts as closed by evidence")
        check(next(s for s in snap["stories"] if s["ref"] == "STORY-002")["closed_by_evidence"] is False, "an open Story is not closed by evidence")
        check([e["ref"] for e in snap["next"]["epics_to_approve"]] == ["EPIC-002"], "a Proposed Epic is to approve")
        cmds = {n["ref"]: n["command"] for n in snap["needs_you"]}
        check(cmds.get("EPIC-002") == "gtt approve EPIC-002", "an Epic to approve brings its command", str(cmds))
        ask_ref = next((r for r in cmds if r.startswith("ASK-")), None)
        check(ask_ref is not None and cmds[ask_ref].startswith("gtt answer ") and cmds[ask_ref].endswith(" 1"), "a question brings its command with the recommended option", str(cmds))
        check(all(n["command"] for n in snap["needs_you"]), "every act the human must do carries a command")
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
