#!/usr/bin/env python3
"""GTT Sonar - tests of the ideas (Prompt 3): criteria 4 and 9.

Criterion 4: the only command the page builds is `gtt idea add`, escaped so it pastes as is.
Criterion 9: `idea.add` writes IDEA-NNN.md with the human as author; an agent cannot create, park, drop or edit
an idea, and may only add a triage line through the engine.

Every scenario runs on a DISPOSABLE copy of this project. The escaping test runs the page's own function in Node
(skipped, and said so, when Node is not installed).

  python .gtt/tests/sonar-ideas.py [--project .]
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FAILS, COUNT = [], 0

spec = importlib.util.spec_from_file_location("snap", os.path.join(HERE, "sonar-snapshot.py"))
snap_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snap_tests)

TEXTS = ["simple", "con 'comillas' simples", 'dobles "así"', "dinero $HOME y $(echo pwned) y `date`", "acentos: ñ á é í ó ú ü ¿qué?", "dos\nlíneas\n\ny un salto vacío",
         "'", "''", "termina en barra \\", "; rm -rf / # y && || | > <", "- empieza con guion", "emoji-free ✓ ünïcödé", "tab\tentre", "{braces} [brackets] *glob* ?"]


def check(cond, label, detail=""):
    global COUNT
    COUNT += 1
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        FAILS.append(label)


def sh(cwd, *argv, stdin=None):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, input=stdin, timeout=120)


def digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=ROOT)
    args = parser.parse_args()
    tmp, dest, _ = snap_tests.make_project(os.path.abspath(args.project))
    try:
        template = open(os.path.join(dest, ".gtt", "sonar", "template.html"), encoding="utf-8").read()
        print("criterion 4 - the one command the page builds")
        found = re.search(r"/\*IDEA-CMD\*/(.*?)/\*END-IDEA-CMD\*/", template, re.S)
        check(found is not None, "the page has one marked command builder")
        builders = [b for b in re.findall(r'"gtt [a-z]+ [a-z]+', template)]
        check(builders == ['"gtt idea add'], "no other command is assembled in the page: only `gtt idea add`", str(builders))
        blocks = re.findall(r"cmdBlock\(([^)]*\)?)\)", template)
        allowed = {"text", "n.command", "p.command", "e.command", "info.command", "snap.compat.command", "snap.degraded.command", "ideaCommand(area.value)", "r.command)"}
        check(all(b.strip() in allowed or b.strip().startswith("ideaCommand") for b in blocks if not b.strip().startswith("text")), "every command block shows the snapshot's command or the idea command", str(blocks))
        check("command" in template and "n.command" in template and "p.command" in template and "e.command" in template, "every other act shows the snapshot's own `command`")
        node = shutil.which("node")
        if not node or not found:
            print("  skip  Node is not installed: the escaping of `gtt idea add` was not run")
        else:
            js = found.group(1) + "\nconst out = JSON.parse(require('fs').readFileSync(0, 'utf8')).map(ideaCommand); process.stdout.write(JSON.stringify(out));"
            built = subprocess.run([node, "-e", js], input=json.dumps(TEXTS), capture_output=True, text=True, timeout=30)
            check(built.returncode == 0, "the page's own function runs", built.stderr[-200:])
            commands = json.loads(built.stdout) if built.returncode == 0 else []
            for text, command in zip(TEXTS, commands):
                got = os.path.join(tmp, "argv.txt")
                script = f'gtt() {{ [ "$1" = idea ] && [ "$2" = add ] && [ "$#" -eq 3 ] && printf %s "$3" > "{got}"; }}\n{command}\n'
                ran = sh(tmp, "bash", "-c", script)
                ok = ran.returncode == 0 and os.path.exists(got) and open(got, encoding="utf-8", newline="").read() == text
                check(ok, f"pasted in bash it is one argument, exactly the text: {text[:28]!r}", ran.stderr[-120:])
                if os.path.exists(got):
                    os.remove(got)
                check(command.startswith("gtt idea add '") and command.endswith("'"), f"it is `gtt idea add '...'` and nothing else: {text[:20]!r}")
            check(commands and commands[1] == "gtt idea add 'con '\\''comillas'\\'' simples'", "a single quote is escaped as '\\''", str(commands[1:2]))

        print("criterion 9 - the human adds; the agent only triages, through the engine")
        gi = lambda *a: sh(dest, "bash", ".gtt/scripts/gtt-idea.sh", *a)
        r = gi("add", "Sincronizar parcelas\nsin señal con 'comillas' y $HOME")
        check(r.returncode == 0 and not [n for n in (os.listdir(os.path.join(dest, "docs", "ideas")) if os.path.isdir(os.path.join(dest, "docs", "ideas")) else []) if n.startswith("IDEA-")], "add is a dry run: nothing is written without --apply", r.stderr)
        r = gi("add", "Sincronizar parcelas\nsin señal con 'comillas' y $HOME", "--apply")
        path = os.path.join(dest, "docs", "ideas", "IDEA-001.md")
        check(r.returncode == 0 and os.path.exists(path), "idea.add creates docs/ideas/IDEA-001.md", r.stderr)
        text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        check(re.match(r"# IDEA-001 · Sincronizar parcelas\n\n> \*\*Canonical reference:\*\* \S+\n\n(Author|Autor): (human|humano)(?: \([^)]*\))? · (Created|Creada): \d{4}-\d{2}-\d{2} · (Type|Tipo): idea\n\n", text) is not None, "the file has the format of the design, author human", text[:120])
        check(text.endswith("Sincronizar parcelas\nsin señal con 'comillas' y $HOME\n"), "the text is kept exactly as written")
        gi("add", "segunda idea", "--apply")
        check(os.path.exists(os.path.join(dest, "docs", "ideas", "IDEA-002.md")), "numbers go up and are never reused")
        before = digest(path)
        r = gi("triage", "IDEA-001", "--result", "converted", "--to", "PROP-007")
        check(r.returncode == 0 and digest(path) == before, "triage is a dry run without --apply")
        r = gi("triage", "IDEA-001", "--result", "converted", "--to", "PROP-007", "--apply")
        after = open(path, encoding="utf-8").read()
        check(r.returncode == 0 and after.startswith(text.rstrip("\n")) and re.search(r"\n---\nTriage: (converted into|convertida en) PROP-007 · \d{4}-\d{2}-\d{2} · (agent|agente)\n$", after), "triage adds one line after a rule and leaves the text untouched", after[len(text) - 20:])
        check(gi("triage", "IDEA-001", "--result", "covered", "--to", "EPIC-001", "--apply").returncode == 1, "an idea is triaged once")
        check(gi("triage", "IDEA-002", "--result", "nonsense", "--to", "x", "--apply").returncode == 1, "an unknown triage result is refused")
        check(gi("triage", "IDEA-002", "--result", "covered", "--to", "not-an-epic", "--apply").returncode == 1, "the target must be the right kind of reference")
        listing = json.loads(gi("list", "--json").stdout)
        states = {i["ref"]: (i["state"], i["to"]) for i in listing["ideas"]}
        check(states.get("IDEA-001") == ("converted", "PROP-007") and states.get("IDEA-002") == ("new", None), "list reads the state from the file", str(states))
        check(gi("park", "IDEA-002", "--apply").returncode == 0 and gi("drop", "IDEA-002", "--apply").returncode == 0 and gi("park", "IDEA-002", "--apply").returncode == 1,
              "park and drop work for the human, and a dropped idea is closed")

        sys.path.insert(0, os.path.join(dest, ".gtt", "scripts"))
        import gtt_protect
        denied = lambda cmd: gtt_protect.decide_units(dest, cmd) is not None
        check(denied("bash .gtt/scripts/gtt-idea.sh add 'x' --apply"), "the hook refuses an agent running idea add")
        check(denied("bash .gtt/scripts/gtt-idea.sh park IDEA-001 --apply") and denied("bash .gtt/scripts/gtt-idea.sh drop IDEA-001 --apply"), "the hook refuses an agent parking or dropping")
        check(denied("gtt idea add 'x'") and denied("gtt idea park IDEA-001") and denied("gtt idea drop IDEA-001"), "the hook refuses the `gtt idea` human acts")
        check(not denied("bash .gtt/scripts/gtt-idea.sh triage IDEA-001 --result covered --to EPIC-001 --apply"), "an agent may triage, through the engine")
        check(not denied("bash .gtt/scripts/gtt-idea.sh list --json") and not denied("gtt idea list"), "an agent may read the ideas")
        mark = os.path.join(dest, gtt_protect.INSTALLED_MARK)      # the path rules apply to an installed project, not to the kit
        os.makedirs(os.path.dirname(mark), exist_ok=True)
        if not os.path.exists(mark):
            open(mark, "w").write("{}\n")
        shell_denied = lambda cmd: gtt_protect.decide_shell(dest, cmd) is not None
        check(shell_denied("echo x >> docs/ideas/IDEA-001.md") and shell_denied("sed -i s/a/b/ docs/ideas/IDEA-001.md") and shell_denied("rm docs/ideas/IDEA-001.md"),
              "the hook refuses an agent editing, creating or removing an idea through the shell")
        check(not shell_denied("cat docs/ideas/IDEA-001.md"), "reading an idea is free")
        settings = json.load(open(os.path.join(dest, ".claude", "settings.json"), encoding="utf-8"))["permissions"]["deny"]
        check("Write(/docs/ideas/**)" in settings and "Edit(/docs/ideas/**)" in settings, "the file tools are denied in settings too")
        ops = json.load(open(os.path.join(dest, ".gtt", "contract", "operations.json"), encoding="utf-8"))["operations"]
        check(all(ops[o]["human_authority"] for o in ("idea.add", "idea.park", "idea.drop")) and not ops["idea.triage"]["human_authority"] and not ops["idea.list"]["mutates"],
              "operations.json declares add, park and drop as human acts, triage as the engine's, list as read-only")

        print("the ideas reach Claude and the page")
        gi("add", "una idea nueva sin triage", "--apply")
        status = sh(dest, "bash", ".gtt/scripts/gtt-status.sh")
        session = open(os.path.join(dest, "gtt-domain", "session.md"), encoding="utf-8").read()
        check(status.returncode == 0 and re.search(r"## Inbox[^\n]*\n(Inbox|Bandeja): 1 (new|nuevas?)", session),
              "session.md shows the `Inbox` section counting the new idea (the section the inbox engine writes since 1.23)", session[-600:])
        audit = open(os.path.join(dest, ".claude", "skills", "gtt-audit", "SKILL.md"), encoding="utf-8").read()
        check(("docs/ideas/" in audit or "IDEA-NNN" in audit) and ("gtt-idea.sh triage" in audit or "gtt-inbox.sh triage" in audit), "the audit skill that contrasts the docs with the backlog includes the ideas")
        snap = json.loads(sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json").stdout)
        refs = {i["ref"]: i for i in snap["ideas"]}
        check(refs.get("IDEA-001", {}).get("state") == "converted" and refs["IDEA-001"]["to"] == "PROP-007" and "IDEA-002" not in refs and refs.get("IDEA-003", {}).get("state") == "new",
              "the snapshot carries the ideas (ref, title, state, to) and leaves out the dropped", str(snap["ideas"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{COUNT - len(FAILS)}/{COUNT} checks held" + (f"; FAILED: {', '.join(FAILS)}" if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
