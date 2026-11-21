#!/usr/bin/env python3
"""What an update must survive: the leftovers of one that was interrupted, and the project's own staged files.

  U1  an ADE file that exists, was not installed by GTT and equals the catalog's is recorded (REFRESH), not a conflict;
      one that differs stays a conflict, and the apply then records the first and keeps the second untouched
  U2  two staged proposals with one name (two promotion sets stage the same destination) index without refusing: each
      gets an id, the plain one for the first and the folder's for the next, and a second run changes nothing

  U3  the inbox migration tells the identity registry what it moved and removed: the index works right after it

  U4  a record the project writes (the completion report) is declared state, so an update never offers to replace it

  U5  a session that was already open when the update ran hears the migration order once, at its next message

  python3 .gtt/tests/update-resilience.py [--project .] [--keep]
Exit 0 = every check held, 1 = at least one failed.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acc", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
write, make_host, bash = acc.write, acc.make_host, acc.bash


def check(label, cond, detail=""):
    assert isinstance(label, str), "check(label, condition): the label comes first"
    acc.check(bool(cond), label, detail)


def empty_registry(host):
    """A project's own registry, not the catalog's: it lists what that project has (the catalog's lists every ADE's files)."""
    write(os.path.join(host, ".gtt/index/artifacts.json"), json.dumps({"schema": 1, "artifacts": []}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-update-resilience-")
    try:
        print("U1  leftovers of an interrupted update")
        host = make_host(project, tmp, "leftover")
        empty_registry(host)
        rc, out, err = bash(host, ".gtt/scripts/gtt-ade.sh", "install", "--from", project, "--participating", "claude", "--primary", "claude", "--apply")
        check("the Claude adapter installs", rc == 0, out + err)
        state_path = os.path.join(host, ".gtt/ade.json")
        state = json.load(open(state_path, encoding="utf-8"))
        same, other = ".claude/hooks/detect-drift.py", ".claude/hooks/protect-guard.py"
        for rel in (same, other):
            check(f"{rel} is an installed hook of the ledger", rel in state["installed"]["claude"]["files"])
            state["installed"]["claude"]["files"].pop(rel)          # what a failed update leaves: the file on disk, the ledger without it
        write(state_path, json.dumps(state, indent=2))
        with open(os.path.join(host, other), "a", encoding="utf-8") as handle:
            handle.write("\n# the project's own change\n")
        before_other = open(os.path.join(host, other), encoding="utf-8").read()
        rc, out, err = bash(host, ".gtt/scripts/gtt-ade.sh", "update", "--from", project)
        text = out + err
        check("a leftover equal to the catalog's is recorded, not a conflict", f"REFRESH    claude   {same}" in text and f"CONFLICT   claude   {same}" not in text, text)
        check("a file that differs from the catalog's is still a conflict", f"CONFLICT   claude   {other}" in text, text)
        check("the dry run refuses because of that one only", rc == 1)
        state = json.load(open(state_path, encoding="utf-8"))
        shutil.copy2(os.path.join(project, other), os.path.join(host, other))       # the person resolves it: the catalog's file
        rc, out, err = bash(host, ".gtt/scripts/gtt-ade.sh", "update", "--from", project, "--apply")
        check("once it is resolved the update applies", rc == 0, out + err)
        recorded = json.load(open(state_path, encoding="utf-8"))["installed"]["claude"]["files"]
        check("both are recorded in the ledger afterwards", same in recorded and other in recorded)
        check("and an edited one is never overwritten while it is a conflict", before_other != open(os.path.join(project, other), encoding="utf-8").read())

        print("U2  two staged files with one name")
        proj = make_host(project, tmp, "staged")
        empty_registry(proj)
        for folder in ("set-a", "set-b", "set-c"):
            write(os.path.join(proj, f"gtt-domain/proposals/staged-x/{folder}/EPIC-023.md"), f"# EPIC-023 staged in {folder}\n")
        rc, out, err = bash(proj, ".gtt/scripts/gtt-index.sh")
        check("the index does not refuse a name that two promotion sets stage", rc == 0, out + err)
        entries = {e["path"]: e["id"] for e in json.load(open(os.path.join(proj, ".gtt/index/artifacts.json"), encoding="utf-8"))["artifacts"]
                   if "staged-x" in e["path"]}
        check("each of the three has an id", len(entries) == 3 and len(set(entries.values())) == 3, str(entries))
        check("the first (by path) keeps the plain id", entries.get("gtt-domain/proposals/staged-x/set-a/EPIC-023.md") == "PROP-EPIC-023", str(entries))
        snapshot = open(os.path.join(proj, ".gtt/index/artifacts.json"), encoding="utf-8").read()
        rc, out, err = bash(proj, ".gtt/scripts/gtt-index.sh")
        check("a second run changes nothing", rc == 0 and open(os.path.join(proj, ".gtt/index/artifacts.json"), encoding="utf-8").read() == snapshot, out + err)
        print("U3  the inbox migration and the identity registry")
        sspec = importlib.util.spec_from_file_location("inbox_session", os.path.join(HERE, "inbox-session.py"))
        isess = importlib.util.module_from_spec(sspec)
        sspec.loader.exec_module(isess)
        mig = make_host(project, tmp, "migrate")
        empty_registry(mig)
        canon = "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md"
        write(os.path.join(mig, "gtt-domain/change-request.md"), isess.DESK)
        write(os.path.join(mig, "gtt-domain/proposals/PROPOSAL-redis.md"), f"# PROPOSAL - Redis sessions\n\n{canon}\n\nRequest: CR-20261001-101500\n\n{isess.FORM1}")
        rc, out, err = bash(mig, ".gtt/scripts/gtt-index.sh")
        check("the old desk and proposal are registered before the migration", rc == 0, out + err)
        reg = lambda: {e["path"]: e for e in json.load(open(os.path.join(mig, ".gtt/index/artifacts.json"), encoding="utf-8"))["artifacts"]}
        check("(both are registered artifacts)", "gtt-domain/change-request.md" in reg() and "gtt-domain/proposals/PROPOSAL-redis.md" in reg())
        rc, out, err = bash(mig, ".gtt/scripts/gtt-inbox.sh", "migrate", "--apply")
        check("the migration runs", rc == 0, out + err)
        rc, out, err = bash(mig, ".gtt/scripts/gtt-index.sh")
        check("the index does not refuse after the migration", rc == 0 and "refusing" not in err, out + err)
        rc, out, err = bash(mig, ".gtt/scripts/gtt-reconcile.sh")
        check("and there is nothing to reconcile", rc == 0 and "nothing to reconcile" in out, out + err)
        now = reg()
        check("the removed desk is retired, the moved proposal keeps its identity at its new path",
              now.get("gtt-domain/change-request.md", {}).get("status") != "active"
              and any(path.startswith("gtt-domain/proposals/PROP-001") and e["status"] == "active" for path, e in now.items()), str(sorted(now)[:6]))
        print("U4  a record the project writes is never offered for replacement")
        manifest = open(os.path.join(project, ".gtt/scaffold/manifest.yaml"), encoding="utf-8").read()
        row = next((l for l in manifest.splitlines() if ".gtt/docs/gtt-completion.md" in l and "path:" in l), "")
        check("the completion report is declared state: it is the project's history, appended by the bootstrap", "state: true" in row, row)
        print("U5  a session that was already open hears the migration order")
        dspec = importlib.util.spec_from_file_location("domain_migration", os.path.join(HERE, "domain-migration.py"))
        dm = importlib.util.module_from_spec(dspec)
        dspec.loader.exec_module(dm)
        legacy = dm.fixture(project, tmp, "open-session")
        os.makedirs(os.path.join(legacy, ".claude/hooks"), exist_ok=True)
        shutil.copy2(os.path.join(project, ".claude/hooks/pending-watch.py"), os.path.join(legacy, ".claude/hooks/pending-watch.py"))

        def hear(session):
            done = subprocess.run([sys.executable, ".claude/hooks/pending-watch.py"], cwd=legacy, capture_output=True, text=True,
                                  input=json.dumps({"session_id": session, "prompt": "seguimos"}))
            return json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"] if done.stdout.strip() else ""
        first = hear("s1")
        check("the first message of an open session carries the migration order", "gtt-domain" in first and "migra" in first.lower(), first[:200])
        check("the second message of that session says nothing", hear("s1") == "")
        check("a different session hears it too", "gtt-domain" in hear("s2"))
        write(os.path.join(legacy, "gtt-domain/backlog.md"), dm.LEGACY + "\n")
        check("a changed backlog does not repeat it to a session that heard it", hear("s1") == "")
        write(os.path.join(legacy, ".gtt/domain-migration.json"), json.dumps({"schema": 1, "format": 1, "status": "done"}))
        check("once the migration is done nobody hears it", hear("s3") == "")
    finally:
        if args.keep:
            print(f"kept: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{acc.COUNT - len(acc.FAILS)}/{acc.COUNT} checks held")
    if acc.FAILS:
        print("FAILED:", "; ".join(acc.FAILS))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
