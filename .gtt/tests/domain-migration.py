#!/usr/bin/env python3
"""GTT domain migration: bring a project's gtt-domain to the format of the Bootstrap it now runs, losing nothing
(gtt-domain-migrate.sh, .gtt/contract/domain.json).

  M1  the contract: the format number, what a migration may and may never write, the operation and the manifest rows
  M2  status: nothing to migrate for a project with no Epic; the findings of a legacy backlog; json for the CLI
  M3  the order: reaches the agent as the next action in the project's language; a project that began empty is stamped
      `clean` and an ordinary failure later is never mistaken for a legacy one
  M4  begin: the zip holds gtt-domain and the ideas, the invariants are taken, a copy goes where the person says
  M5  verify: refuses a changed Epic, an Epic gone or added, a Story dropped or moved to another status, a frozen
      governed file changed; accepts rewritten Stories, new Stories and (before the freeze) context edits as notes
  M6  done: stamps the format; afterwards there is nothing to migrate and no order
  M7  restore: dry run changes nothing; --apply puts the backlog back and the migration is pending again
  M8  the contract every ADE reads: AGENTS.md, operations.md, the Claude table, the usage guides

  python3 .gtt/tests/domain-migration.py [--project .] [--keep]
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
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acc", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
check, write = acc.check, acc.write

MIGRATE = ".gtt/scripts/gtt-domain-migrate.sh"
NEXT = ".gtt/scripts/gtt-project.sh"
STATE = ".gtt/domain-migration.json"

LEGACY = """# Project Backlog

## Epics

### EPIC-001 — Pagos

**Status:** Planned
**Goal:** Cobrar a los clientes.
**Scope:** cobro simple y reembolso.
**Approved:** ana - 2026-01-02

#### Stories

##### STORY-001 — Cobro simple

- **Status:** In Progress
- **Implements:** (none)

##### STORY-002 — Reembolso

- **Status:** Planned
"""

DESIGN = """# EPIC-001 design

- **R-1** the system charges a customer
- **E-1** a customer pays 10 and the account shows 10
"""


def run(cwd, script, *args):
    done = subprocess.run(["bash", script, *args], cwd=cwd, capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def fixture(project, tmp, name, backlog=LEGACY, lang=None, frozen=False):
    """A throwaway project: the engine of this Bootstrap, a backlog, one governed design file."""
    root = os.path.join(tmp, name)
    shutil.copytree(os.path.join(project, ".gtt"), os.path.join(root, ".gtt"), ignore=shutil.ignore_patterns("local", "__pycache__", "tests"))
    write(os.path.join(root, "gtt-domain/backlog.md"), backlog)
    write(os.path.join(root, "gtt-domain/context/design/EPIC-001.md"), DESIGN)
    write(os.path.join(root, "gtt-domain/context/stack.md"), "# stack\n")
    write(os.path.join(root, "docs/ideas/IDEA-001.md"), "an idea\n")
    if lang:
        write(os.path.join(root, ".gtt/methodology.json"), json.dumps({"language": lang}))
    if frozen:
        write(os.path.join(root, "gtt-domain/.frozen"), "{}\n")
    return root


def status(root):
    code, out, _ = run(root, MIGRATE, "status", "--json")
    return json.loads(out)


def migrated(backlog):
    """The legacy backlog with its Stories rewritten to the new format: Epics untouched."""
    return backlog.replace("- **Implements:** (none)", "- **Implements:** design/EPIC-001#R-1\n- **Done when:** E-1 - run: pytest tests/test_cobro.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-domain-migration-")
    try:
        # M1 ----------------------------------------------------------------------------------------------------
        print("M1  the contract")
        domain = json.load(open(os.path.join(project, ".gtt/contract/domain.json"), encoding="utf-8"))
        check("the contract states an integer format", isinstance(domain.get("format"), int) and domain["format"] >= 1)
        check("a migration may write the backlog and nothing else", domain.get("may_write") == ["gtt-domain/backlog.md"])
        check("the Epic heading and everything governed are never written",
              any("Epic" in item for item in domain["never_write"]) and "gtt-domain/context/" in domain["never_write"])
        release = json.load(open(os.path.join(project, ".gtt/contract/release.json"), encoding="utf-8"))
        check("release.json lists the contract", release["contracts"].get("domain") == 1)
        ops = json.load(open(os.path.join(project, ".gtt/contract/operations.json"), encoding="utf-8"))["operations"]
        op = ops.get("domain.status")
        check("the operation domain.status is declared and read-only", bool(op) and op["mutates"] is False and op["human_authority"] is False)
        manifest = open(os.path.join(project, ".gtt/scaffold/manifest.yaml"), encoding="utf-8").read()
        check("the manifest names the contract, the state file and the backup folder",
              all(item in manifest for item in (".gtt/contract/domain.json", ".gtt/domain-migration.json", ".gtt/local/migrations/")))

        # M2 ----------------------------------------------------------------------------------------------------
        print("M2  status")
        empty = fixture(project, tmp, "empty", backlog="# Project Backlog\n\n## Epics\n")
        st = status(empty)
        check("a project with no Epic has nothing to migrate", st["needed"] is False and st["epics"] == 0)
        legacy = fixture(project, tmp, "legacy")
        st = status(legacy)
        check("a legacy backlog needs a migration", st["needed"] is True and st["epics"] == 1)
        check("it says why, in the validator's own words", any("Implements" in why for why in st["why"]) and any("Done when" in why for why in st["why"]))
        check("the findings are clean lines, not the validator's footer", all(not why.startswith("gtt-check-backlog") for why in st["why"]))
        code, out, _ = run(legacy, MIGRATE, "status")
        check("the plain status is one readable paragraph with the way to begin", code == 0 and "gtt-domain-migrate.sh begin" in out)
        check("status never writes", not os.path.exists(os.path.join(legacy, STATE)))
        ok_backlog = migrated(LEGACY)
        fine = fixture(project, tmp, "fine", backlog=ok_backlog)
        check("a backlog that already passes needs nothing", status(fine)["needed"] is False)

        # M3 ----------------------------------------------------------------------------------------------------
        print("M3  the order reaches the agent")
        code, out, _ = run(legacy, NEXT, "next-action", "--json")
        found = json.loads(out)["next_action"] if code == 0 else None
        check("the next action is the domain migration", bool(found) and found["kind"] == "domain-migration")
        check("it carries the procedure and the zip advice", bool(found) and "gtt-domain-migrate.sh begin" in found["text"] and "copy" in found["text"])
        check("it never obstructs: it says a cut point", bool(found) and "cut point" in found["text"])
        spanish = fixture(project, tmp, "spanish", lang="es")
        code, out, _ = run(spanish, NEXT, "next-action", "--json")
        found_es = json.loads(out)["next_action"]
        check("in Spanish when the project speaks it", found_es["kind"] == "domain-migration" and "migración" in found_es["text"] and "otro lugar" in found_es["text"])
        check("and the person's line is in Spanish too", "primera respuesta" in (found_es["human"] or ""))
        fresh = fixture(project, tmp, "fresh", backlog="# Project Backlog\n\n## Epics\n")
        code, out, _ = run(fresh, NEXT, "next-action", "--json", "--session-start")
        check("a project that begins with no Epic gets no order", json.loads(out)["next_action"] is None or json.loads(out)["next_action"]["kind"] != "domain-migration")
        stamp = json.load(open(os.path.join(fresh, STATE), encoding="utf-8")) if os.path.exists(os.path.join(fresh, STATE)) else {}
        check("it is stamped clean at the current format", stamp.get("status") == "clean" and stamp.get("format") == domain["format"])
        write(os.path.join(fresh, "gtt-domain/backlog.md"), LEGACY)
        code, out, _ = run(fresh, NEXT, "next-action", "--json", "--session-start")
        action = json.loads(out)["next_action"]
        check("a failure of ordinary work later is never mistaken for a legacy migration", action is None or action["kind"] != "domain-migration")

        # M4 ----------------------------------------------------------------------------------------------------
        print("M4  begin")
        root = fixture(project, tmp, "work")
        elsewhere = os.path.join(tmp, "elsewhere")
        os.makedirs(elsewhere)
        code, out, err = run(root, MIGRATE, "begin", "--to", elsewhere)
        check("begin succeeds", code == 0, out + err)
        base = os.path.join(root, ".gtt/local/migrations")
        folders = sorted(os.listdir(base)) if os.path.isdir(base) else []
        check("it keeps one folder per begin", len(folders) == 1)
        archive = os.path.join(base, folders[0], "gtt-domain.zip") if folders else ""
        names = zipfile.ZipFile(archive).namelist() if os.path.isfile(archive) else []
        check("the zip holds the backlog, the governed design and the ideas",
              {"gtt-domain/backlog.md", "gtt-domain/context/design/EPIC-001.md", "docs/ideas/IDEA-001.md"} <= set(names))
        check("the invariants are taken", os.path.isfile(os.path.join(base, folders[0], "invariants.json")) if folders else False)
        copies = [n for n in os.listdir(elsewhere) if n.endswith(".zip")]
        check("a copy went where the person said", len(copies) == 1)
        check("it tells the person to keep a copy somewhere else too", "somewhere else" in out)
        check("and how to undo", "restore --apply" in out)
        state = json.load(open(os.path.join(root, STATE), encoding="utf-8"))
        check("the state is in-progress", state["status"] == "in-progress")
        check("an unfinished migration keeps the order alive",
              json.loads(run(root, NEXT, "next-action", "--json")[1])["next_action"]["kind"] == "domain-migration")
        code, _, err = run(root, MIGRATE, "begin", "--to", os.path.join(tmp, "does-not-exist"))
        check("a destination that is not a folder is refused", code == 2)

        # M5 ----------------------------------------------------------------------------------------------------
        print("M5  verify")
        backlog = os.path.join(root, "gtt-domain/backlog.md")
        code, out, _ = run(root, MIGRATE, "verify")
        check("before any work it refuses: the validator still fails", code == 1 and "check-backlog" in out)
        write(backlog, ok_backlog)
        code, out, _ = run(root, MIGRATE, "verify")
        check("rewriting only the Stories is accepted", code == 0 and "verify OK" in out, out)
        write(backlog, ok_backlog + "\n##### STORY-003 — Recibo\n\n- **Status:** Planned\n- **Implements:** design/EPIC-001#R-1\n- **Done when:** E-1 - run: pytest tests/test_recibo.py\n")
        code, out, _ = run(root, MIGRATE, "verify")
        check("a new Story is a note, not a problem", code == 0 and "new Story" in out, out)
        write(backlog, ok_backlog.replace("Cobrar a los clientes.", "Cobrar y devolver."))
        code, out, _ = run(root, MIGRATE, "verify")
        check("an edited Epic is refused", code == 1 and "EPIC-001" in out and "never edits" in out)
        write(backlog, ok_backlog.replace("**Approved:** ana - 2026-01-02", "**Approved:** ana - 2026-02-03"))
        code, out, _ = run(root, MIGRATE, "verify")
        check("a rewritten `Approved` is refused", code == 1 and "EPIC-001" in out)
        write(backlog, ok_backlog.replace("##### STORY-002 — Reembolso\n\n- **Status:** Planned\n", ""))
        code, out, _ = run(root, MIGRATE, "verify")
        check("a Story dropped is refused", code == 1 and "STORY-002" in out and "gone" in out)
        write(backlog, ok_backlog.replace("- **Status:** Planned", "- **Status:** Done"))
        code, out, _ = run(root, MIGRATE, "verify")
        check("a Story moved to another status is refused", code == 1 and "status changed" in out)
        write(backlog, ok_backlog + "\n### EPIC-002 — Otro\n\n**Status:** Proposed\n**Goal:** algo.\n")
        code, out, _ = run(root, MIGRATE, "verify")
        check("a new Epic is refused: adding one is the human's decision", code == 1 and "EPIC-002" in out)
        write(backlog, ok_backlog)
        write(os.path.join(root, "gtt-domain/context/stack.md"), "# stack changed\n")
        code, out, _ = run(root, MIGRATE, "verify")
        check("before the freeze a context edit is a note", code == 0 and "allowed before the freeze" in out)
        write(os.path.join(root, "gtt-domain/.frozen"), "{}\n")
        code, out, _ = run(root, MIGRATE, "verify")
        check("once frozen the same edit is refused", code == 1 and "frozen" in out)
        os.remove(os.path.join(root, "gtt-domain/.frozen"))
        write(os.path.join(root, "gtt-domain/context/stack.md"), "# stack\n")

        # M6 ----------------------------------------------------------------------------------------------------
        print("M6  done")
        write(backlog, LEGACY)
        code, out, _ = run(root, MIGRATE, "done")
        check("done does not stamp a migration that does not verify", code == 1 and json.load(open(os.path.join(root, STATE)))["status"] == "in-progress")
        write(backlog, ok_backlog)
        code, out, _ = run(root, MIGRATE, "done")
        stamped = json.load(open(os.path.join(root, STATE), encoding="utf-8"))
        check("done stamps the format", code == 0 and stamped["status"] == "done" and stamped["format"] == domain["format"], out)
        check("the zip stays after it", os.path.isfile(archive))
        check("afterwards there is nothing to migrate", status(root)["needed"] is False)
        check("and no order reaches the agent", (json.loads(run(root, NEXT, "next-action", "--json")[1])["next_action"] or {}).get("kind") != "domain-migration")
        write(backlog, LEGACY)
        check("a stamped project is not asked again for ordinary work", status(root)["needed"] is False)
        write(backlog, ok_backlog)

        # M7 ----------------------------------------------------------------------------------------------------
        print("M7  restore")
        write(backlog, ok_backlog.replace("Cobrar a los clientes.", "Cobrar y devolver."))
        edited = open(backlog, encoding="utf-8").read()
        code, out, _ = run(root, MIGRATE, "restore")
        check("the dry run says what it would do and changes nothing", code == 0 and "dry run" in out and open(backlog, encoding="utf-8").read() == edited)
        code, out, _ = run(root, MIGRATE, "restore", "--apply")
        check("--apply puts the backlog back as the zip held it", code == 0 and open(backlog, encoding="utf-8").read() == LEGACY)
        check("the migration is pending again", json.load(open(os.path.join(root, STATE)))["status"] == "pending")
        nothing = fixture(project, tmp, "nothing")
        code, _, err = run(nothing, MIGRATE, "restore", "--apply")
        check("with no backup there is nothing to restore", code == 1)

        # M8 ----------------------------------------------------------------------------------------------------
        print("M8  the contract every ADE reads")
        read = lambda rel: open(os.path.join(project, rel), encoding="utf-8").read()
        check("AGENTS.md carries the rule and points at operations.md", "## Domain migration" in read("AGENTS.md") and "*Domain migration*" in read("AGENTS.md"))
        check("operations.md holds the order of work", "## Domain migration" in read(".gtt/docs/agents/operations.md"))
        check("operations.md forbids what the migration may not do",
              "never edit an Epic's heading block" in read(".gtt/docs/agents/operations.md").replace("**Never", "Never").replace("Never edit", "never edit") or "Never edit an Epic's heading block" in read(".gtt/docs/agents/operations.md"))
        check("the Claude table has a row for it", "gtt-domain-migrate.sh begin" in read(".claude/CLAUDE.md"))
        check("the usage guides explain it in both languages",
              "gtt-domain" in read(".gtt/docs/usage.md") and "gtt-domain" in read(".gtt/docs/usage.es.md"))
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
