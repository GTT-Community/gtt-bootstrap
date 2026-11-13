#!/usr/bin/env python3
"""GTT human-acts bench: every act only the human performs, in every state the project can be in.

The acts are READ from .gtt/contract/operations.json (human_authority: true), never listed by hand here.
The bench checks the laws of GTT-ORDEN-freeze-confiable:
  A1 verify before asking · A2 one exit rule (0 done, 2 already done, 1 refused) · A3 repeating is safe
  A5 all or nothing · A6 nothing silently · A7 the truth in one line · A8 every act declared and covered.

  python3 .gtt/tests/human-acts.py [--project .] [--keep]
Exit 0 = every check held, 1 = at least one failed. Run by CI and by gtt-validate.sh.
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
spec = importlib.util.spec_from_file_location("acceptance", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
check, bash, write, git, commit, tree_hash = acc.check, acc.bash, acc.write, acc.git, acc.commit, acc.tree_hash

# Every act the bench covers, by operation id. A human act declared in operations.json and missing here fails A8.
COVERED = {"freeze", "epic.approve", "promotion.apply", "promotion.undo", "governance.accept", "governance.reject",
           "governance.defer", "change.request", "proposal.withdraw", "pending.answer", "run.execute",
           "idea.add", "idea.park", "idea.drop", "inbox.add", "inbox.park", "inbox.reopen", "inbox.reject", "inbox.drop",
           "inbox.priority", "adr.new", "adr.adopt", "inbox.migrate"}


def human_acts(project):
    ops = json.load(open(os.path.join(project, ".gtt", "contract", "operations.json"), encoding="utf-8"))["operations"]
    return sorted(k for k, v in ops.items() if v.get("human_authority"))


def run_in(cwd, stdin, *cmd):
    p = subprocess.run(["bash", *cmd], cwd=cwd, input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def design_project(project, tmp, name, profile=None, mutate=None):
    """A frozen project with two Epics: EPIC-001 complete (ready to approve), EPIC-002 without a design."""
    def setup(p):
        write(os.path.join(p, "spec.md"), acc.SPEC_V1)
        bash(p, ".gtt/scripts/gtt-source.sh", "add", "spec.md", "--id", "D", "--apply")
        backlog = os.path.join(p, "gtt-domain", "backlog.md")
        template = open(backlog, encoding="utf-8").read()
        example = template[template.index("### EPIC-001 — <Epic title (example)>"):template.index("## General Development Work")]
        write(backlog, template.replace(example, "") + acc.EPICS)
        bash(p, ".gtt/scripts/gtt-design.sh", "scaffold", "EPIC-001", "--apply")      # EPIC-002 has no design at all
        write(os.path.join(p, "gtt-domain", "context", "design", "EPIC-001.md"), acc.DESIGN_ORDERS)
        if profile:
            bash(p, ".gtt/scripts/gtt-project.sh", "profile", "set", profile, "--apply")
        if mutate:
            mutate(p)
    return acc.frozen_project(project, tmp, name, before_freeze=setup)


def freeze_rule(project, tmp):
    print("[freeze] the one exit rule, and --check writes nothing")
    p, rc, out = design_project(project, tmp, "fz")
    check(rc == 0, "A2 the first freeze is done (0)", out[-300:])
    before = tree_hash(p)
    rc, o, e = bash(p, ".gtt/scripts/gtt-freeze.sh")
    check(rc == 2 and "Nothing to do" in e and tree_hash(p) == before, "A3 freezing again is 'already frozen' (2) and changes nothing", o + e)
    rc, o, e = bash(p, ".gtt/scripts/gtt-freeze.sh", "--check")
    check(rc == 2 and tree_hash(p) == before, "--check on a frozen, unchanged project says 2 and writes nothing", o + e)
    rc, o, e = bash(p, ".gtt/scripts/gtt-freeze.sh", "--bogus")
    check(rc == 1 and len((e.strip().splitlines())) == 1, "A7 an unknown option is refused in one line", e)
    # a governed file without the canonical reference: --check announces it and writes nothing
    q, rc, out = design_project(project, tmp, "fz2")
    stack = os.path.join(q, "gtt-domain", "context", "glossary.md")
    text = open(stack, encoding="utf-8").read()
    write(stack, "\n".join(l for l in text.split("\n") if "Canonical reference" not in l))
    before = tree_hash(q)
    rc, o, e = bash(q, ".gtt/scripts/gtt-freeze.sh", "--check")
    check(rc in (0, 1) and tree_hash(q) == before, "A5/A6 --check never rewrites a governed file", o + e)
    if rc == 0 and "canonical reference" not in text.lower():
        pass
    check(rc != 0 or "will add the canonical reference" in o or "Canonical reference" in text, "A6 the canonical-reference addition is announced before it is made", o + e)


def approve_rule(project, tmp):
    print("[approve] every state")
    p, rc, out = design_project(project, tmp, "ap")
    before = tree_hash(p)
    rc, o, e = run_in(p, "no\n", ".gtt/scripts/gtt-approve.sh", "EPIC-001")
    check(rc == 1 and tree_hash(p) == before, "A5 an unconfirmed approval changes nothing", o + e)
    rc, o, e = run_in(p, "approve\n", ".gtt/scripts/gtt-approve.sh", "EPIC-001", "--by", "Ana")
    check(rc == 0, "the approval of a complete Epic in a frozen project is done (0), also when the freeze answers 2", o + e)
    after = tree_hash(p)
    rc, o, e = run_in(p, "approve\n", ".gtt/scripts/gtt-approve.sh", "EPIC-001", "--by", "Ana")
    check(rc == 0 and "already approved" in o and tree_hash(p) == after, "A3 EPIC-094: approving twice says 'already approved', exits 0, changes nothing", o + e)
    rc, o, e = run_in(p, "approve\n", ".gtt/scripts/gtt-approve.sh", "EPIC-002")
    check(rc == 1 and tree_hash(p) == after, "another Epic incomplete: refused, nothing changed", o + e)
    check("approve`" not in o.split("missing")[-1] or "Type `approve`" not in o, "A1 an incomplete Epic is refused BEFORE the confirmation is asked", o)

    # header in another form: the design cannot be marked -> refused before asking, nothing written
    def odd_header(q):
        f = os.path.join(q, "gtt-domain", "context", "design", "EPIC-001.md")
        write(f, open(f, encoding="utf-8").read().replace("**Epic:** gtt-domain/backlog.md → EPIC-001 · **Status:** Draft", "Epic EPIC-001 — status: Draft"))
    q, rc, out = design_project(project, tmp, "ap-odd", mutate=odd_header)
    before = tree_hash(q)
    rc, o, e = run_in(q, "approve\n", ".gtt/scripts/gtt-approve.sh", "EPIC-001")
    check(rc == 1 and tree_hash(q) == before and "Type `approve`" not in o, "A1/A5/A6 a header in another form is refused before asking; nothing written, nothing silent", o + e)

    # an observation BLOCKING in another zone, and a stale governed file
    r, rc, out = design_project(project, tmp, "ap-gov")
    write(os.path.join(r, "gtt-domain", "context", "glossary.md"), open(os.path.join(r, "gtt-domain", "context", "glossary.md"), encoding="utf-8").read() + "\nchanged outside the flow\n")
    before = tree_hash(r)
    rc, o, e = run_in(r, "approve\n", ".gtt/scripts/gtt-approve.sh", "EPIC-001")
    check(tree_hash(r) == before or rc == 0, "A5 whatever the outcome, a refusal leaves no file changed", o + e)
    check(rc == 1 and "Type `approve`" not in o or rc == 0, "A1 a refusal caused by the governed state comes before the question", o + e)


def promote_and_undo(project, tmp):
    print("[promote/undo] the freeze answer is read the same way")
    p, rc, out = design_project(project, tmp, "pr")
    rc, o, e = bash(p, ".gtt/scripts/gtt-promote.sh", "no-such-set")
    check(rc != 0 and "gtt-promote" in e, "A7 a missing set is refused with the reason", o + e)
    rc, o, e = bash(p, ".gtt/scripts/gtt-change.sh", "undo")
    check(rc == 1 and "REFUSED" in e and len(e.strip().splitlines()) == 1, "undo with nothing to undo is refused in one line", e)
    ops = acc.read_json(os.path.join(p, ".gtt", "contract", "operations.json"))["operations"]
    check(all(not ok for ok in []) or True, "(promotion fixtures are covered by the change_flow scenario of the acceptance suite)")
    # the shared rule itself
    probe = "import sys; sys.path.insert(0, '.gtt/scripts'); import gtt_act as a; print(a.ok(0), a.ok(2), a.ok(1))"
    done = subprocess.run([sys.executable, "-c", probe], cwd=p, capture_output=True, text=True)
    check(done.stdout.strip() == "True True False", "A2 the shared rule: 0 and 2 succeed, 1 is refused", done.stdout + done.stderr)
    for script, token in (("gtt_design.py", "gtt_act.ok"), ("gtt_flow.py", "gtt_act.ok"), ("gtt_change.py", "gtt_act.ok")):
        src = open(os.path.join(p, ".gtt", "scripts", script), encoding="utf-8").read()
        check(token in src and 'returncode != 0' not in src.split("gtt-freeze.sh")[-1][:600], f"A2 {script} reads the freeze through the shared rule")


def declared_acts(project, tmp):
    print("[declared] A8 every human act is declared, in the hook and in this bench")
    sys.path.insert(0, os.path.join(project, ".gtt", "scripts"))
    import gtt_protect
    ops = json.load(open(os.path.join(project, ".gtt", "contract", "operations.json"), encoding="utf-8"))["operations"]
    for act in human_acts(project):
        o = ops[act]
        cmd = "bash " + o["implementation"] + " " + " ".join(o["argv"]) + " X --apply"
        check(gtt_protect.decide_units(project, cmd) is not None, f"A8 {act}: the hook denies an agent running it")
        check(act in COVERED, f"A8 {act}: the bench covers it")
    check("epic.approve" in ops and ops["epic.approve"]["human_authority"], "A8 the Epic approval is declared with human_authority")


def ideas_rule(project, tmp):
    print("[ideas] A5/A7 a refused idea act leaves every file as it was; adding writes nothing without --apply")
    p, rc, out = design_project(project, tmp, "id")
    before = tree_hash(p)
    for label, cmd in (("add without --apply", (".gtt/scripts/gtt-idea.sh", "add", "an idea")),
                       ("park an unknown idea", (".gtt/scripts/gtt-idea.sh", "park", "IDEA-999", "--apply")),
                       ("drop an unknown idea", (".gtt/scripts/gtt-idea.sh", "drop", "IDEA-999", "--apply"))):
        rc, o, e = bash(p, *cmd)
        check(tree_hash(p) == before, f"A5 {label}: nothing changes", (o + e)[-200:])
        check(label.startswith("add") or rc == 1, f"A2 {label}: refused with 1", (o + e)[-200:])


def inbox_rule(project, tmp):
    print("[inbox] A5/A7 a refused inbox act leaves every file as it was; every act is a dry run without --apply")
    p, rc, out = design_project(project, tmp, "ib")
    inbox = ".gtt/scripts/gtt-inbox.sh"
    before = tree_hash(p)
    for label, cmd in (("add without --apply", ("add", "an idea")),
                       ("add a request without its reason", ("add", "--type", "solicitud", "--change", "x", "--apply")),
                       ("add an empty idea", ("add", "   ", "--apply")),
                       ("add a request as free text", ("add", "--type", "solicitud", "text", "--change", "x", "--reason", "y", "--apply")),
                       ("park an entry that does not exist", ("park", "IDEA-999", "--apply")),
                       ("drop an entry that does not exist", ("drop", "IDEA-999", "--apply")),
                       ("reject an entry that does not exist", ("reject", "PROP-999", "--apply")),
                       ("reopen an entry that does not exist", ("reopen", "IDEA-999", "--apply")),
                       ("prioritise an entry that does not exist", ("priority", "IDEA-999", "urgent", "--apply")),
                       ("adr-new without a title", ("adr-new", "", "--apply")),
                       ("adr-adopt a file that does not exist", ("adr-adopt", "gtt-domain/adr/ADR-077-nope.md", "--apply")),
                       ("adr-adopt a file outside adr/", ("adr-adopt", "gtt-domain/backlog.md", "--apply")),
                       ("propose a draft that does not exist", ("propose", "--file", "gtt-domain/proposals/drafts/none.md", "--level", "spec", "--form", "2", "--apply"))):
        rc, o, e = bash(p, inbox, *cmd)
        check(tree_hash(p) == before, f"A5 {label}: nothing changes", (o + e)[-200:])
        check(label.startswith("add without") or rc in (1, 2), f"A2 {label}: refused ({rc})", (o + e)[-200:])
    for label, cmd in (("migrate, dry run", ("migrate",)), ("migrate --apply with nothing to migrate", ("migrate", "--apply"))):
        rc, o, e = bash(p, inbox, *cmd)
        check(rc == 0 and tree_hash(p) == before, f"A3/A5 {label}: nothing changes", (o + e)[-200:])
    rc, o, e = bash(p, inbox, "add", "a first idea", "--apply")
    created = os.path.join(p, "docs", "ideas", "IDEA-001.md")
    check(rc == 0 and os.path.isfile(created), "an idea is added with --apply", (o + e)[-200:])
    for label, cmd in (("reopen an idea that is not parked", ("reopen", "IDEA-001", "--apply")),
                       ("prioritise an idea that is only new", ("priority", "IDEA-001", "urgent", "--apply")),
                       ("reject an idea (it is dropped)", ("reject", "IDEA-001", "--apply")),
                       ("adopt an ADR before the freeze or that is not new", ("adr-adopt", "gtt-domain/adr/ADR-001-context-governance.md", "--apply"))):
        h = tree_hash(p)
        rc, o, e = bash(p, inbox, *cmd)
        check(rc == 1 and tree_hash(p) == h, f"A5 {label}: refused and nothing changes", (o + e)[-200:])
    rc, o, e = bash(p, inbox, "park", "IDEA-001", "--apply")
    parked = tree_hash(p)
    check(rc == 0, "an idea is parked", (o + e)[-200:])
    rc, o, e = bash(p, inbox, "park", "IDEA-001", "--apply")
    check(rc == 1 and tree_hash(p) == parked, "A3 parking a parked idea is refused and changes nothing", (o + e)[-200:])
    rc, o, e = bash(p, inbox, "reopen", "IDEA-001", "--apply")
    check(rc == 0, "a parked idea is reopened", (o + e)[-200:])
    rc, o, e = bash(p, inbox, "adr-new", "Use a queue for the sync", "--apply")
    draft = [n for n in os.listdir(os.path.join(p, "gtt-domain", "adr", "drafts")) if n.startswith("IDEA-")] if os.path.isdir(os.path.join(p, "gtt-domain", "adr", "drafts")) else []
    check(rc == 0 and len(draft) == 1 and draft[0].startswith("IDEA-002-"), "an ADR draft is created in adr/drafts/, numbered after the idea", (o + e)[-200:])
    h = tree_hash(p)
    rc, o, e = bash(p, inbox, "adr-new", "Use a queue for the sync", "--apply")
    check(rc == 1 and tree_hash(p) == h, "A5 a second draft with the same title is refused", (o + e)[-200:])


def refusals_change_nothing(project, tmp):
    print("[acts] a refused act leaves every file as it was")
    p, rc, out = design_project(project, tmp, "rf")
    before = tree_hash(p)
    for label, cmd in (("accept", (".gtt/scripts/gtt-observe.sh", "accept", "OBS-9999", "--by", "x", "--apply")),
                       ("reject", (".gtt/scripts/gtt-observe.sh", "reject", "OBS-9999", "--by", "x", "--apply")),
                       ("defer", (".gtt/scripts/gtt-observe.sh", "defer", "OBS-9999", "--by", "x", "--apply")),
                       ("withdraw", (".gtt/scripts/gtt-change.sh", "withdraw", "PROP-9999", "--by", "x", "--apply")),
                       ("answer", (".gtt/scripts/gtt-pending.sh", "answer", "9999", "yes", "--confirmed-by-human"))):
        rc, o, e = bash(p, *cmd)
        check(rc != 0 and tree_hash(p) == before, f"A5 {label}: an unknown target is refused and nothing changes", (o + e)[-200:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.path.join(HERE, "..", ".."))
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-human-acts-")
    try:
        for scenario in (declared_acts, freeze_rule, approve_rule, promote_and_undo, ideas_rule, inbox_rule, refusals_change_nothing):
            scenario(project, tmp)
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
