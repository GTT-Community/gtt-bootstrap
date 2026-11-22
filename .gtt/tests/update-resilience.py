#!/usr/bin/env python3
"""What an update must survive: the leftovers of one that was interrupted, and the project's own staged files.

  U1  an ADE file that exists, was not installed by GTT and equals the catalog's is recorded (REFRESH), not a conflict;
      one that differs stays a conflict, and the apply then records the first and keeps the second untouched
  U2  two staged proposals with one name (two promotion sets stage the same destination) index without refusing: each
      gets an id, the plain one for the first and the folder's for the next, and a second run changes nothing

  U3  the inbox migration tells the identity registry what it moved and removed: the index works right after it

  U4  a record the project writes (the completion report) is declared a record: shipped, and never offered for replacement; no shipped document links a never-shipped file

  U5  a session that was already open when the update ran hears the migration order once, at its next message

  U6  a [FUENTE: path] of a governed document follows a file the inbox migration renamed instead of failing

  U7  a ledger that is ahead of a protection hook (an update cut short by the sentinel of a running agent session) is repaired by the next
      update, keeping the file that was there; an edited instruction file is still kept as it was; the update records its human window

  U8  a pending event (ASK/DEC/REV) is never an artifact: one an older release registered and the session then cleaned is retired
      by the next index instead of leaving a ghost (reconcile MISSING, index refusing, integrity FAIL); a file that really went
      missing is still refused

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
        check("the completion report is declared a record: shipped as a template, never offered for replacement", "record: true" in row and "state: true" not in row, row)
        import re as _re
        state_paths = [m.group(1).strip() for m in _re.finditer(r"path:\s*([^,}]+),(?:[^}]*,)?\s*state:\s*true", manifest)]
        linked = []
        for base_dir, _dirs, names in os.walk(os.path.join(project, ".gtt", "docs")):
            for name in names:
                if not name.endswith(".md"):
                    continue
                full = os.path.join(base_dir, name)
                for target in _re.findall(r"\]\(([^)#\s]+)\)", open(full, encoding="utf-8", errors="replace").read()):
                    if "://" in target:
                        continue
                    rel = os.path.relpath(os.path.normpath(os.path.join(base_dir, target)), project).replace(os.sep, "/")
                    if any(rel == s or rel.startswith(s) for s in state_paths):
                        linked.append(f"{os.path.relpath(full, project)} -> {target}")
        check("no shipped document links a file that is never shipped (a project initialised from this package would fail its own integrity check)", not linked, "; ".join(linked))
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
        silent = hear("s0")
        check("with no structural change declared since the project's version, the hook says nothing", silent == "", silent[:120])
        bash(legacy, ".gtt/scripts/gtt-domain-migrate.sh", "check", "--apply", "--from", "1.16.0")      # what `gtt update` does after the update
        first = hear("s1")
        check("the first message of an open session carries the evaluation, and it asks the human first", "gtt-domain" in first and "ASK the human" in first, first[:200])
        check("the second message of that session says nothing", hear("s1") == "")
        check("a different session hears it too", "gtt-domain" in hear("s2"))
        write(os.path.join(legacy, "gtt-domain/backlog.md"), dm.LEGACY + "\n")
        check("a changed backlog does not repeat it to a session that heard it", hear("s1") == "")
        write(os.path.join(legacy, ".gtt/domain-migration.json"), json.dumps({"schema": 1, "format": 1, "status": "done"}))
        check("once the migration is done nobody hears it", hear("s3") == "")
        print("U6  a governed citation of a file the inbox migration moved")
        cite = make_host(project, tmp, "cited")
        empty_registry(cite)
        write(os.path.join(cite, "gtt-domain/change-request.md"), isess.DESK)
        write(os.path.join(cite, "gtt-domain/proposals/PROPOSAL-redis.md"), f"# PROPOSAL - Redis sessions\n\n{canon}\n\nRequest: CR-20261001-101500\n\n{isess.FORM1}")
        write(os.path.join(cite, "gtt-domain/context/architecture.md"),
              "# Architecture\n\nSessions live in Redis. [FUENTE: gtt-domain/proposals/PROPOSAL-redis.md]\n")
        bash(cite, ".gtt/scripts/gtt-index.sh")
        rc, out, err = bash(cite, ".gtt/scripts/gtt-check-provenance.sh")
        check("before the migration the citation resolves (the file is there)", "PROPOSAL-redis.md] does not resolve" not in out + err, out + err)
        rc, out, err = bash(cite, ".gtt/scripts/gtt-inbox.sh", "migrate", "--apply")
        check("the migration runs", rc == 0, out + err)
        check("the proposal was renamed", not os.path.exists(os.path.join(cite, "gtt-domain/proposals/PROPOSAL-redis.md")))
        rc, out, err = bash(cite, ".gtt/scripts/gtt-check-provenance.sh")
        check("after it the same citation still resolves, following the move", "PROPOSAL-redis.md] does not resolve" not in out + err, out + err)
        write(os.path.join(cite, "gtt-domain/context/architecture.md"), "# Architecture\n\nSessions. [FUENTE: gtt-domain/proposals/NOPE.md]\n")
        rc, out, err = bash(cite, ".gtt/scripts/gtt-check-provenance.sh")
        check("a citation of a file that never existed still fails", "NOPE.md] does not resolve" in out + err, out + err)

        print("U7  a ledger ahead of a protection hook")
        ahead = make_host(project, tmp, "ahead")
        empty_registry(ahead)
        rc, out, err = bash(ahead, ".gtt/scripts/gtt-ade.sh", "install", "--from", project, "--participating", "claude", "--primary", "claude", "--apply")
        check("(the Claude adapter installs)", rc == 0, out + err)
        hook, doc = ".claude/hooks/pending-watch.py", ".claude/CLAUDE.md"
        older = "# the release before this one shipped this\n"
        write(os.path.join(ahead, hook), older)                    # what is left after a sentinel put the old hook back
        with open(os.path.join(ahead, doc), "a", encoding="utf-8") as handle:
            handle.write("\nthe project's own note\n")
        ledger_before = json.load(open(os.path.join(ahead, ".gtt/ade.json"), encoding="utf-8"))["installed"]["claude"]["files"]
        rc, out, err = bash(ahead, ".gtt/scripts/gtt-validate.sh")
        rc2, o2, e2 = bash(ahead, ".gtt/scripts/gtt-ade.sh", "validate")
        check("(the state is the one that made `gtt update` fail: the validator refuses the hook)", rc2 == 1 and f"protection hook changed since install: {hook}" in o2 + e2, o2 + e2)
        cache = os.path.join(tmp, "cache")
        env = dict(os.environ, XDG_CACHE_HOME=cache, LOCALAPPDATA="")
        done = subprocess.run(["bash", ".gtt/scripts/gtt-ade.sh", "update", "--from", project], cwd=ahead, capture_output=True, text=True, env=env)
        text = done.stdout + done.stderr
        check("the dry run names the repair and refuses nothing", f"REPAIR     claude   {hook}" in text and done.returncode == 0, text)
        check("an edited instruction file is still kept as it was", f"KEEP       claude   {doc}" in text, text)
        check("the dry run wrote nothing", open(os.path.join(ahead, hook), encoding="utf-8").read() == older)
        done = subprocess.run(["bash", ".gtt/scripts/gtt-ade.sh", "update", "--from", project, "--apply"], cwd=ahead, capture_output=True, text=True, env=env)
        check("the apply succeeds", done.returncode == 0, done.stdout + done.stderr)
        check("the hook is the catalog's again", open(os.path.join(ahead, hook), "rb").read() == open(os.path.join(project, hook), "rb").read())
        kept = os.path.join(ahead, ".gtt/local/replaced", hook)
        check("the file that was there is kept, not lost", os.path.isfile(kept) and open(kept, encoding="utf-8").read() == older)
        check("the instruction file the project edited is untouched", "the project's own note" in open(os.path.join(ahead, doc), encoding="utf-8").read())
        check("the ledger did not move", json.load(open(os.path.join(ahead, ".gtt/ade.json"), encoding="utf-8"))["installed"]["claude"]["files"].get(hook) == ledger_before[hook])
        rc2, o2, e2 = bash(ahead, ".gtt/scripts/gtt-ade.sh", "validate")
        check("and the validator is satisfied", rc2 == 0, o2 + e2)
        leases = [os.path.join(r, f) for r, _, fs in os.walk(cache) for f in fs if f == "human-act.json"]
        lease = json.load(open(leases[0], encoding="utf-8")) if leases else {}
        check("the update recorded its human window, and closed it", lease.get("act") == "ade-update" and lease.get("ended") is not None, str(lease))
        print("U8  pending events are never artifacts")
        pend = make_host(project, tmp, "pending-ghosts")
        empty_registry(pend)
        rc, out, err = bash(pend, ".gtt/scripts/gtt-index.sh")
        check("(a project with no pending event indexes)", rc == 0, out + err)
        manifest_path = os.path.join(pend, ".gtt/index/artifacts.json")
        manifest = json.load(open(manifest_path, encoding="utf-8"))
        ghosts = {"REV-001": "gtt-domain/pending/REV-001.md", "ASK-002": "gtt-domain/pending/ASK-002.md"}
        for ref, rel in ghosts.items():          # what 1.31.1 and before did: register the event, then delete it once attended
            manifest["artifacts"].append({"id": "ART-GTT-DOMAIN-PENDING-" + ref, "type": "documentation", "path": rel,
                                          "status": "active", "history": [], "aliases": []})
        write(manifest_path, json.dumps(manifest, indent=2))
        write(os.path.join(pend, ghosts["REV-001"]), "# REV-001 · a review still waiting\n")     # still open: on disk
        write(os.path.join(pend, "gtt-domain/pending/DEC-003.md"), "# DEC-003 · a new decision\n")   # never registered
        rc, out, err = bash(pend, ".gtt/scripts/gtt-reconcile.sh")
        check("reconcile does not report an event as missing", rc == 0 and "MISSING" not in out + err, out + err)
        rc, out, err = bash(pend, ".gtt/scripts/gtt-check-integrity.sh")
        check("integrity does not fail for an event that was cleaned", "pending/" not in out + err and "unreconciled" not in out + err, out + err)   # (a bare fixture lacks readme-gtt.md: not this check's business)
        rc, out, err = bash(pend, ".gtt/scripts/gtt-index.sh")
        check("the index retires what an older release registered, and refuses nothing", rc == 0 and "retired     2 pending event(s)" in out, out + err)
        registered = {e["id"]: e for e in json.load(open(manifest_path, encoding="utf-8"))["artifacts"]}
        check("both old entries are retired (an id is never reused), the new event was not registered",
              all(registered["ART-GTT-DOMAIN-PENDING-" + r]["status"] == "retired" for r in ghosts)
              and not any(e["path"].endswith("DEC-003.md") for e in registered.values()), str(sorted(registered)))
        rc, out, err = bash(pend, ".gtt/scripts/gtt-index.sh")
        check("a second run changes nothing", rc == 0 and "retired" not in out and "registered" not in out, out + err)
        os.remove(os.path.join(pend, ghosts["REV-001"]))                                              # the session cleans it
        rc, out, err = bash(pend, ".gtt/scripts/gtt-check-integrity.sh")
        check("and cleaning the event afterwards leaves nothing to reconcile", "pending/" not in out + err and "unreconciled" not in out + err, out + err)
        write(os.path.join(pend, "gtt-domain/notes.md"), "# Notes\n")
        rc, out, err = bash(pend, ".gtt/scripts/gtt-index.sh")
        check("(an ordinary document registers)", rc == 0 and "gtt-domain/notes.md" in out, out + err)
        os.remove(os.path.join(pend, "gtt-domain/notes.md"))
        rc, out, err = bash(pend, ".gtt/scripts/gtt-index.sh")
        check("a document that really went missing is still refused", rc == 1 and "gtt-domain/notes.md" in err, out + err)
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
