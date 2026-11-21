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
  M9  scale: an invented backlog of 12 Epics and 108 Stories in every shape; nothing lost, one change found by id

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
write = acc.write


def check(label, cond, detail=""):
    """The acceptance harness takes (condition, label); this file reads better label first. Swapping them
    silently makes every check pass (a non-empty string is true), so the adapter lives in one place."""
    assert isinstance(label, str), "check(label, condition): the label comes first"
    acc.check(bool(cond), label, detail)

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
        chk = ops.get("domain.check")
        check("the operation domain.check is declared: it takes the version the project was on and stamps the state", bool(chk) and chk["mutates"] is True
              and {a["name"] for a in chk["args"]} == {"from", "apply"})
        op = ops.get("domain.status")
        check("the operation domain.status is declared and read-only", bool(op) and op["mutates"] is False and op["human_authority"] is False)
        manifest = open(os.path.join(project, ".gtt/scaffold/manifest.yaml"), encoding="utf-8").read()
        check("the manifest names the contract, the state file and the backup folder",
              all(item in manifest for item in (".gtt/contract/domain.json", ".gtt/domain-migration.json", ".gtt/local/migrations/")))

        # M2 ----------------------------------------------------------------------------------------------------
        print("M2  status: only a structure a release declared is asked")
        empty = fixture(project, tmp, "empty", backlog="# Project Backlog\n\n## Epics\n")
        st = status(empty)
        check("a project with no Epic has nothing to migrate", st["needed"] is False and st["epics"] == 0)
        legacy = fixture(project, tmp, "legacy")
        st = status(legacy)
        check("a backlog with validator findings is work, not a migration: nothing is asked", st["needed"] is False and st["epics"] == 1)
        check("status never writes", not os.path.exists(os.path.join(legacy, STATE)))
        check("the contract declares the structural changes by release", bool(domain.get("format_changes")) and all("since" in c and "en" in c and "es" in c for c in domain["format_changes"]))
        code, out, _ = run(legacy, MIGRATE, "check", "--apply", "--from", "1.28.0")
        check("an update from a version after every declared change asks nothing", code == 0 and status(legacy)["needed"] is False
              and json.load(open(os.path.join(legacy, STATE), encoding="utf-8"))["status"] == "clean")
        unknown = fixture(project, tmp, "unknown")
        run(unknown, MIGRATE, "check", "--apply")
        check("with no version to compare nothing is guessed", status(unknown)["needed"] is False)
        run(unknown, MIGRATE, "check", "--apply", "--from", "garbage")
        check("an unreadable version asks nothing either", status(unknown)["needed"] is False)
        code, out, _ = run(legacy, MIGRATE, "check", "--apply", "--from", "1.16.0")
        st = status(legacy)
        check("an update from before a declared change stamps it pending and asks", st["needed"] is True and st["state"] == "pending" and st["from"] == "1.16.0", str(st))
        check("it says why: the structural change the release declared", any("Implements" in why for why in st["why"]) and any("Done when" in why for why in st["why"]), str(st["why"]))
        code, out, _ = run(legacy, MIGRATE, "status")
        check("the plain status tells the person the agent will ask first", code == 0 and "ask" in out and "1.16.0" in out, out)
        check("and lists what the validator finds, as evidence for the agent's judgment", "finds" in out and "Implements" in out, out)
        code, out, _ = run(empty, MIGRATE, "check", "--apply", "--from", "1.16.0")
        check("a project with no Epic is never asked even when a change was declared", status(empty)["needed"] is False)
        fine = fixture(project, tmp, "fine", backlog=migrated(LEGACY))
        ok_backlog = migrated(LEGACY)

        # M3 ----------------------------------------------------------------------------------------------------
        print("M3  the evaluation reaches the agent, and it asks first")
        code, out, _ = run(legacy, NEXT, "next-action", "--json")
        found = json.loads(out)["next_action"] if code == 0 else None
        check("the next action is the domain migration", bool(found) and found["kind"] == "domain-migration")
        check("it is an evaluation, never an order to rewrite", bool(found) and "EVALUATION" in found["text"] and "never an order to rewrite" in found["text"])
        check("it tells the agent to ask the human and never begin on its own", bool(found) and "ASK the human" in found["text"] and "never begin on your own" in found["text"])
        check("it carries the way out: dismiss when nothing is needed or the human declines", bool(found) and "dismiss" in found["text"])
        check("it carries the procedure and the zip advice", bool(found) and "gtt-domain-migrate.sh begin" in found["text"] and "copy" in found["text"])
        check("it never obstructs: it says a cut point", bool(found) and "cut point" in found["text"] or bool(found) and "middle of a Story" in found["text"])
        check("the person's line says the agent asks first", bool(found) and "ask you before" in (found["human"] or ""))
        code, out, _ = run(unknown, NEXT, "next-action", "--json")
        check("a backlog full of findings that no release declared gets no order", json.loads(out)["next_action"] is None or json.loads(out)["next_action"]["kind"] != "domain-migration")
        spanish = fixture(project, tmp, "spanish", lang="es")
        run(spanish, MIGRATE, "check", "--apply", "--from", "1.16.0")
        code, out, _ = run(spanish, NEXT, "next-action", "--json")
        found_es = json.loads(out)["next_action"]
        check("in Spanish when the project speaks it", found_es["kind"] == "domain-migration" and "EVALUACIÓN" in found_es["text"] and "PREGUNTA" in found_es["text"] and "otro lugar" in found_es["text"])
        check("and the person's line is in Spanish too", "te preguntará" in (found_es["human"] or ""))
        fresh = fixture(project, tmp, "fresh", backlog="# Project Backlog\n\n## Epics\n")
        code, out, _ = run(fresh, NEXT, "next-action", "--json", "--session-start")
        check("a project that begins with no Epic gets no order", json.loads(out)["next_action"] is None or json.loads(out)["next_action"]["kind"] != "domain-migration")
        stamp = json.load(open(os.path.join(fresh, STATE), encoding="utf-8")) if os.path.exists(os.path.join(fresh, STATE)) else {}
        check("it is stamped clean at the current format", stamp.get("status") == "clean" and stamp.get("format") == domain["format"])
        write(os.path.join(fresh, "gtt-domain/backlog.md"), LEGACY)
        code, out, _ = run(fresh, NEXT, "next-action", "--json", "--session-start")
        action = json.loads(out)["next_action"]
        check("a failure of ordinary work later is never mistaken for a legacy migration", action is None or action["kind"] != "domain-migration")
        dismissable = fixture(project, tmp, "dismiss")
        run(dismissable, MIGRATE, "check", "--apply", "--from", "1.16.0")
        code, out, _ = run(dismissable, MIGRATE, "dismiss")
        stamped = json.load(open(os.path.join(dismissable, STATE), encoding="utf-8"))
        check("dismiss records the human's decision: nothing is migrated and it is not asked again", code == 0 and status(dismissable)["needed"] is False
              and stamped["status"] == "done" and stamped.get("dismissed") is True, out)
        check("an unrelated later update (no change declared after it) keeps it quiet", run(dismissable, MIGRATE, "check", "--apply", "--from", stamped["bootstrap"])[0] == 0 and status(dismissable)["needed"] is False)

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

        # M9 ----------------------------------------------------------------------------------------------------
        print("M9  a large, varied backlog (scale)")
        import re
        import time
        gspec = importlib.util.spec_from_file_location("synthetic_backlog", os.path.join(HERE, "fixtures", "synthetic_backlog.py"))
        synth = importlib.util.module_from_spec(gspec)
        gspec.loader.exec_module(synth)
        template = open(os.path.join(project, "gtt-domain/backlog.md"), encoding="utf-8").read()
        big = synth.build(template, epics=12, stories=9)
        size = synth.counts(big)
        check("the synthetic project is large and invented", size == {"epics": 12, "stories": 108} and "ñ" in big and "(none)" in big, str(size))
        bigroot = fixture(project, tmp, "big", backlog=big)
        synth.write_designs(bigroot, epics=12, stories=9)
        bigfile = os.path.join(bigroot, "gtt-domain/backlog.md")
        t0 = time.time()
        code, out, err = run(bigroot, MIGRATE, "begin")
        check("begin takes the invariants of 108 Stories", code == 0, out + err)

        def rewrite(text):
            """What the agent does: give every Story that lacks anchors its Implements and Done when. Status and Epics stay."""
            parts = re.split(r"(?m)^(?=##### STORY-)", text)
            out_parts = [parts[0]]
            for part in parts[1:]:
                epic = re.search(r"STORY-(\d+)", part).group(1)
                if "- **Implements:** design/" not in part:
                    anchors = "- **Implements:** design/EPIC-001#R-1"
                    if "- **Implements:** (none)" in part:
                        part = part.replace("- **Implements:** (none)", anchors)
                    else:
                        part = re.sub(r"(- \*\*Status:\*\* [^\n]*\n)", lambda m: m.group(1) + anchors + "\n", part, count=1)
                    if "**Done when:**" not in part:
                        part = part.replace(anchors, anchors + "\n- **Done when:** E-1 - run: pytest", 1)
                out_parts.append(part)
            return "".join(out_parts)

        agent = rewrite(big)
        check("the rewrite changed something and kept every Story", agent != big and synth.counts(agent) == size)
        write(bigfile, agent)
        code, out, err = run(bigroot, MIGRATE, "verify")
        check("rewriting Stories across 12 Epics is accepted", code == 0 and "verify OK" in out, out + err)
        slow = time.time() - t0
        check("it stays fast (begin + verify under 20 s)", slow < 20, f"{slow:.1f}s")
        write(bigfile, agent.replace("línea 7, con acentos", "línea 7, sin acentos"))
        code, out, _ = run(bigroot, MIGRATE, "verify")
        check("one accent edited in one Epic Goal among 12 is refused", code == 1 and "EPIC-007" in out, out)
        victim = re.search(r"(?m)^##### STORY-053 — .*\n(?:.*\n)*?(?=\n##### STORY-|\n### EPIC-|\n---)", agent)
        check("(the Story to drop exists)", victim is not None)
        write(bigfile, agent.replace(victim.group(0), "", 1) if victim else agent)
        code, out, _ = run(bigroot, MIGRATE, "verify")
        check("one Story dropped in the middle of 108 is refused by id", code == 1 and "STORY-053" in out and "gone" in out, out)
        moved = re.sub(r"(##### STORY-077 — .*\n\n- \*\*Status:\*\* )(\w[\w ]*)", lambda m: m.group(1) + ("Done" if m.group(2) != "Done" else "Planned"), agent, count=1)
        write(bigfile, moved)
        code, out, _ = run(bigroot, MIGRATE, "verify")
        check("one Story moved to another status is refused by id", code == 1 and "STORY-077" in out and "status changed" in out, out)
        tampered = re.sub(r"\*\*Approved:\*\* ana", "**Approved:** bruno", agent, count=1)
        check("(the Approved line to change exists)", tampered != agent)
        write(bigfile, tampered)
        code, out, _ = run(bigroot, MIGRATE, "verify")
        check("a rewritten `Approved` among the Epics is refused", code == 1 and "EPIC-" in out, out)
        write(bigfile, agent)
        code, out, err = run(bigroot, MIGRATE, "done")
        check("done stamps the large project", code == 0 and json.load(open(os.path.join(bigroot, STATE)))["status"] == "done", out + err)
        code, out, err = run(bigroot, MIGRATE, "restore", "--apply")
        check("restore returns the backlog byte for byte", code == 0 and open(bigfile, encoding="utf-8").read() == big, out + err)

        # M8 ----------------------------------------------------------------------------------------------------
        print("M8  the contract every ADE reads")
        read = lambda rel: open(os.path.join(project, rel), encoding="utf-8").read()
        check("AGENTS.md carries the rule and points at operations.md", "## Domain migration" in read("AGENTS.md") and "*Domain migration*" in read("AGENTS.md"))
        check("operations.md holds the order of work", "## Domain migration" in read(".gtt/docs/agents/operations.md"))
        check("operations.md forbids what the migration may not do",
              "never edit an Epic's heading block" in read(".gtt/docs/agents/operations.md").replace("**Never", "Never").replace("Never edit", "never edit") or "Never edit an Epic's heading block" in read(".gtt/docs/agents/operations.md"))
        check("the Claude table has a row for it", "gtt-domain-migrate.sh status" in read(".claude/CLAUDE.md") and "ask the human" in read(".claude/CLAUDE.md"))
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
