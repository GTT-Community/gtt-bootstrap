#!/usr/bin/env python3
"""Why a freeze or a promotion failed after the person confirmed it, and what now stops that (GTT-FREEZE-DIAGNOSTICO.md).

  F1  the rehearsal that refuses an act BEFORE it is confirmed survives what a real project holds: a folder it cannot read
      (a database volume owned by root) no longer switches the rehearsal off, and it copies the kit, not the whole project
  F2  the Markdown gate and what the freeze repairs have one scope: a working draft under proposals/staged/ is not a kit
      document, and any other domain file the gate flags is repaired by the freeze (deterministic), not left to fail it
  F3  `core/kernel/plugins/...` importing its own files is not `core/ depends on plugins/`; a map left by the old resolver is not read
  F4  a reopened observation no longer carries the date it was resolved
  F5  a promotion's "every file was put back" is checked against the copies, and the copies stay when it cannot be
  F6  the sentinel lets pass what a human act wrote inside the window the act recorded, and puts back everything else

  python3 .gtt/tests/freeze-reliability.py [--project .] [--keep]
Exit 0 = every check held, 1 = at least one failed.
"""
import argparse
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
import time
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acc", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
write, bash, op, data = acc.write, acc.bash, acc.op, acc.data


def check(label, cond, detail=""):
    assert isinstance(label, str), "check(label, condition): the label comes first"
    acc.check(bool(cond), label, detail)


def load_module(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def change_log(q):
    shutil.rmtree(os.path.join(q, ".gtt", "local", "promote-backup"), ignore_errors=True)
    with open(os.path.join(q, "gtt-domain", "context", "stack.md"), "a", encoding="utf-8") as handle:
        handle.write("\n## 6. Map change log\n\n| Date | ADR or CHANGE | What changed |\n|---|---|---|\n| | | |\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-freeze-reliability-")
    here = os.getcwd()
    locked = []
    try:
        # F1 ----------------------------------------------------------------------------------------------------
        print("F1  the rehearsal survives a real project")
        p, rc, out = acc.frozen_project(project, tmp, "rehearsal", before_freeze=change_log)
        check("(the disposable project is frozen)", rc == 0, out)
        volume = os.path.join(p, "infra", "volumes", "db", "data")
        os.makedirs(volume)
        write(os.path.join(volume, "pgdata"), "database file\n")
        write(os.path.join(p, "apps", "api", "main.ts"), "export const x = 1;\n")
        unreadable = os.geteuid() != 0
        if unreadable:
            os.chmod(volume, 0)
            locked.append(volume)
        glossary = os.path.join(p, "gtt-domain", "context", "glossary.md")
        original = open(glossary, encoding="utf-8").read()
        write(os.path.join(p, "bad-glossary.md"), original + "a term nobody defined yet: TODO\n")
        acc.bash(p, ".gtt/scripts/gtt-stage.sh", "bad", "--reason", "a term", "--origin", acc.accepted_prop(p, "spec", "bad"), "bad-glossary.md=gtt-domain/context/glossary.md")
        rc, env, _ = op(p, "promotion.apply", set="bad", confirmed_by_human=True)
        text = env.get("stdout", "") + env.get("stderr", "")
        check("a set the freeze would refuse is refused BEFORE the confirmation, even with a folder the copy cannot read",
              "would be refused" in text and "dry run" not in text, text[-500:])
        check("and nothing was written", open(glossary, encoding="utf-8").read() == original)
        write(os.path.join(p, "ok-glossary.md"), original + "a term nobody defined yet\n")
        acc.bash(p, ".gtt/scripts/gtt-stage.sh", "good", "--reason", "a term", "--origin", acc.accepted_prop(p, "spec", "good"), "ok-glossary.md=gtt-domain/context/glossary.md")
        rc, env, _ = op(p, "promotion.apply", set="good", confirmed_by_human=True)
        text = env.get("stdout", "") + env.get("stderr", "")
        check("a set that holds is shown as a dry run, not blocked by the rehearsal", "dry run" in text and "would be refused" not in text, text[-500:])
        os.chdir(p)
        sys.path.insert(0, os.path.join(p, ".gtt", "scripts"))
        import gtt_act
        copy = os.path.join(tmp, "light")
        skipped = gtt_act.light_copy(p, copy, writes=["gtt-domain/context/glossary.md"])
        check("the kit is copied for real", os.path.isdir(os.path.join(copy, ".gtt")) and not os.path.islink(os.path.join(copy, ".gtt"))
              and not os.path.islink(os.path.join(copy, "gtt-domain")))
        check("the rest of the project is linked, not copied", os.path.islink(os.path.join(copy, "infra")) and os.path.islink(os.path.join(copy, "apps")))
        check("a folder the act writes into is a real copy", not os.path.islink(os.path.join(copy, "gtt-domain")))
        check("the copy is tiny next to the project", sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(copy, followlinks=False) for f in fs
                                                           if not os.path.islink(os.path.join(d, f))) < 20 * 1024 * 1024)
        os.chdir(here)
        if unreadable:
            os.chmod(volume, stat.S_IRWXU)
            locked.remove(volume)

        # F2 ----------------------------------------------------------------------------------------------------
        print("F2  one scope for the Markdown gate and for what the freeze repairs")

        def drafts(q):
            change_log(q)
            write(os.path.join(q, "gtt-domain", "proposals", "staged", "work", "HISTORIAS-A.md"), "# Stories of the work\n\nno canonical line here\n")
            write(os.path.join(q, "gtt-domain", "proposals", "withdrawn", "old", "x.md"), "# a withdrawn file\n")
            write(os.path.join(q, "gtt-domain", "proposals", "PROP-009-note.md"), "# PROP-009 a note\n\nwritten by hand, no canonical line\n")
        q, rc, out = acc.frozen_project(project, tmp, "scope", before_freeze=drafts)
        check("the freeze goes through: working drafts and the archive are not what the gate asks for", rc == 0, out[-600:])
        staged = open(os.path.join(q, "gtt-domain", "proposals", "staged", "work", "HISTORIAS-A.md"), encoding="utf-8").read()
        check("a working draft is left exactly as it was", "Canonical reference" not in staged)
        note = open(os.path.join(q, "gtt-domain", "proposals", "PROP-009-note.md"), encoding="utf-8").read()
        check("another domain file the gate would flag is repaired by the freeze, under the title", "Canonical reference" in note and note.startswith("# PROP-009"), note[:200])
        rc, out, err = bash(q, ".gtt/scripts/gtt-check-markdown.sh")
        check("and the gate passes afterwards", rc == 0, out[-400:])

        # F3 ----------------------------------------------------------------------------------------------------
        print("F3  a dependency is read from the real path of the import")
        os.chdir(q)
        sys.path.insert(0, os.path.join(q, ".gtt", "scripts"))
        import gtt_code
        mods = [{"id": "core", "path": "core/", "may": [], "must_not": [], "has_rule": True, "none": False},
                {"id": "plugins", "path": "plugins/", "may": [], "must_not": [], "has_rule": True, "none": False}]
        inner = gtt_code.target_module("../../src/ejecutor.ts", "js", "core/kernel/plugins/spike-orm/drizzle/ejecutor.ts", mods)
        check("core/kernel/plugins/... importing its own files is core, not the plugins/ module", inner and inner["path"] == "core/", str(inner))
        outer = gtt_code.target_module("../../../plugins/bodega/index", "js", "core/kernel/x/a.ts", mods)
        check("a real import of plugins/ from core/ is still found", outer and outer["path"] == "plugins/", str(outer))
        py = gtt_code.target_module(".sibling", "python", "core/kernel/plugins/x/mod.py", mods)
        check("a Python relative import is read the same way", py and py["path"] == "core/", str(py))
        named = gtt_code.target_module("com.acme.plugins.Thing", "java", "core/App.java", mods)
        check("an import that names a package keeps the looser match", named and named["path"] == "plugins/", str(named))
        stale = os.path.join(q, ".gtt", "local", "code-map.json")
        write(stale, json.dumps({"schema": 1, "kind": "gtt-code-map", "modules": [{"path": "core/"}], "edges": [{"from": "core", "to": "plugins", "allowed": False,
                                                                                                          "count": 44, "example": "core/kernel/plugins/a.ts:1"}]}))
        check("a map left by an older resolver is not read", gtt_code.last_map() is None)
        write(stale, json.dumps({"schema": 1, "resolver": gtt_code.RESOLVER, "kind": "gtt-code-map", "modules": [], "edges": []}))
        check("a map of the current resolver is", gtt_code.last_map() is not None)
        os.chdir(here)

        # F4 ----------------------------------------------------------------------------------------------------
        print("F4  an open observation carries no resolved date")
        os.chdir(q)
        import gtt_observe
        sig = {"fingerprint": "f1", "level": "GOVERNANCE", "guards": "g", "detail": "d", "state": "s", "rule": "R", "kind": "k", "artifact": "a"}
        ledger = {"next": 9, "items": [{"id": "OBS-0008", "fingerprint": "f1", "status": "resolved", "level": "GOVERNANCE", "guards": "g", "detail": "d", "state": "s",
                                         "rule": "R", "kind": "k", "artifact": "a", "first_seen": "2026-10-30", "resolution": "no longer observed", "resolved": "2026-11-18"}]}
        gtt_observe.correlate(ledger, [sig])
        item = ledger["items"][0]
        check("it is open again", item["status"] == "open")
        check("and it no longer says when it was resolved", "resolved" not in item and "resolution" not in item, str(item))
        os.chdir(here)

        # F5 ----------------------------------------------------------------------------------------------------
        print("F5  `put back` is checked")
        r = acc.fresh(project, tmp, "restore")
        os.chdir(r)
        import gtt_flow
        target = os.path.join(r, "gtt-domain", "context", "glossary.md")
        write(target, "# glossary\n\nbefore\n")
        folder = os.path.join(r, gtt_flow.BACKUPS, "set1")
        os.makedirs(folder)
        shutil.copyfile(target, os.path.join(folder, "0.orig"))
        json.dump({"schema": 1, "name": "set1", "files": [{"to": "gtt-domain/context/glossary.md", "existed": True, "backup": "0.orig"}]}, open(os.path.join(folder, "backup.json"), "w"))
        write(target, "# glossary\n\npromoted\n")
        check("a restore that holds says so and removes the copy", gtt_flow.restore("set1", quiet=True) == 0 and open(target, encoding="utf-8").read().endswith("before\n")
              and not os.path.exists(folder))
        os.makedirs(folder)
        shutil.copyfile(target, os.path.join(folder, "0.orig"))
        json.dump({"schema": 1, "name": "set1", "files": [{"to": "gtt-domain/context/glossary.md", "existed": True, "backup": "0.orig"}]}, open(os.path.join(folder, "backup.json"), "w"))
        write(target, "# glossary\n\npromoted again\n")

        def broken(src, dst, *a, **k):
            with open(dst, "w", encoding="utf-8") as handle:
                handle.write("garbage")
        with mock.patch.object(gtt_flow.shutil, "copyfile", broken):
            code = gtt_flow.restore("set1", quiet=True)
        check("a restore that did not put the bytes back is a failure, not `every file was put back`", code == 1)
        check("and the copy of the originals is kept", os.path.isfile(os.path.join(folder, "0.orig")) and os.path.isfile(os.path.join(folder, "backup.json")))
        os.chdir(here)

        # F6 ----------------------------------------------------------------------------------------------------
        print("F6  the sentinel and a human act that overlapped an agent command")
        cache = os.path.join(tmp, "cache")
        os.environ["XDG_CACHE_HOME"] = cache
        os.environ.pop("LOCALAPPDATA", None)
        sentinel = load_module("sentinel", os.path.join(project, ".claude", "hooks", "governed-sentinel.py"))
        proot = os.path.join(tmp, "sentinel-project")
        context = os.path.join(proot, "gtt-domain", "context", "a.md")
        write(os.path.join(proot, "gtt-domain", ".frozen"), "frozen\n")
        write(context, "v1\n")
        sys.path.insert(0, os.path.join(project, ".gtt", "scripts"))
        import gtt_act as act
        os.chdir(proot)
        os.environ.pop("GTT_HUMAN_ACT", None)

        def agent_command(change):
            sentinel.pre(proot)
            change()
            return sentinel.post(proot, {})
        out = agent_command(lambda: write(context, "agent wrote\n"))
        check("an agent command that changes the frozen design is put back (as always)", out is not None and open(context, encoding="utf-8").read() == "v1\n", str(out))

        def human_during():
            with act.human_act("promote"):
                write(context, "promoted by the human\n")
        archive = os.path.join(proot, "gtt-domain", "proposals", "withdrawn")
        archived = len(os.listdir(archive)) if os.path.isdir(archive) else 0
        out = agent_command(human_during)
        check("a human act that ran while the command was in flight is kept, and nothing is archived",
              out is None and open(context, encoding="utf-8").read() == "promoted by the human\n"
              and (len(os.listdir(archive)) if os.path.isdir(archive) else 0) == archived, str(out))
        write(context, "v1\n")
        sentinel.pre(proot)

        def late_write():
            with act.human_act("promote"):
                pass
            time.sleep(0.2)
            write(context, "written after the act ended\n")
            os.utime(context, (time.time() + 30, time.time() + 30))
        out = agent_command(late_write)
        check("a write outside the window the act recorded is still the agent's and is put back", out is not None and open(context, encoding="utf-8").read() == "v1\n", str(out))
        os.chdir(here)
        os.environ.pop("XDG_CACHE_HOME", None)
    finally:
        os.chdir(here)
        for path in locked:
            try:
                os.chmod(path, stat.S_IRWXU)
            except OSError:
                pass
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
