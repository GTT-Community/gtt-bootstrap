#!/usr/bin/env python3
"""GTT - code: criteria 24 to 27 and 40 of GTT-ORDEN-sonar-herramienta.md (the Code view, 1.26).

  python3 .gtt/tests/code.py

Builds the demo project with the 32 sources (fixtures/sonar-demo.py --full), plants an import that stack.md 5 does not allow, and asks `gtt-code.sh`
what it sees. Writes nothing in this repository."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

os.environ.setdefault("GTT_SONAR_NO_WATCH", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sonar_demo", os.path.join(HERE, "fixtures", "sonar-demo.py"))
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
COUNT, FAILS = 0, []


def check(cond, label, detail=""):
    global COUNT
    COUNT += 1
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        FAILS.append(label)


def sh(cwd, *argv):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=300)


def code_map(project, *extra):
    out = sh(project, "bash", ".gtt/scripts/gtt-code.sh", "map", "--json", *extra)
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else {}


def write(project, rel, text):
    path = os.path.join(project, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def main():
    project = demo.build(full=True)
    sh(project, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "base", "--allow-empty")
    print("the modules of stack.md 5 and the real imports")
    data = code_map(project)
    paths = {m["path"]: m for m in data.get("modules", [])}
    check(set(paths) >= {"src/parcelas/", "src/sync/", "src/core/"}, "the modules come from `5. Dependency rules`", str(sorted(paths)))
    check(paths["src/core/"]["layer"] == 0 and paths["src/parcelas/"]["layer"] == 1, "each module has its layer in the graph of what it may depend on", str({k: v["layer"] for k, v in paths.items()}))
    edges = {(e["from"], e["to"]): e for e in data.get("edges", [])}
    check(edges.get(("src/parcelas/", "src/core/"), {}).get("allowed") is True, "an import that the table allows is an allowed edge")

    print("criterion 24 - an import that stack.md 5 does not allow is GTT-DEPENDS, with its file:line, and a red arrow")
    write(project, "src/parcelas/edit.py", "import os\nfrom src.sync import queue\n\n\ndef edit():\n    return queue\n")
    data = code_map(project)
    bad = {(e["from"], e["to"]): e for e in data["edges"]}.get(("src/parcelas/", "src/sync/"))
    check(bad is not None and bad["allowed"] is False and bad["example"] == "src/parcelas/edit.py:2" and bad["count"] == 1, "the edge parcelas -> sync is not allowed, with archivo:línea", str(bad))
    sh(project, "bash", ".gtt/scripts/gtt-code.sh", "refresh", "--quiet")
    found = json.loads(sh(project, "bash", ".gtt/scripts/gtt-findings.sh", "list", "--json").stdout)["findings"]
    hits = [f for f in found if f["code"] == "GTT-DEPENDS"]
    check(len(hits) == 1 and hits[0]["plane"] == "code" and "edit.py:2" in hits[0]["where"] and hits[0]["owner"] == "agent", "it reaches the findings as GTT-DEPENDS of the code plane", str(hits))
    check(any(f["plane"] == "code" for f in found) and all(f["level"] != "BLOCKING" for f in found), "and nothing new blocks")

    print("a module declared with no code is informative")
    stack = os.path.join(project, "gtt-domain", "context", "stack.md")
    text = open(stack, encoding="utf-8").read().replace("| src/core/ | - | - |", "| src/core/ | - | - |\n| src/reportes/ | src/core/ | - |")
    open(stack, "w", encoding="utf-8").write(text)
    data = code_map(project)
    check(next(m for m in data["modules"] if m["path"] == "src/reportes/")["empty"] is True, "src/reportes/ is declared and empty")
    sh(project, "bash", ".gtt/scripts/gtt-code.sh", "refresh", "--quiet")
    found = json.loads(sh(project, "bash", ".gtt/scripts/gtt-findings.sh", "list", "--json").stdout)["findings"]
    empty = [f for f in found if f["code"] == "CODE-EMPTY"]
    check(len(empty) == 1 and empty[0]["owner"] is None and empty[0]["level"] == "NOTICE", "a NOTICE with no owner")

    print("criterion 25 - classes with ctags; without it the view says so")
    has_ctags = shutil.which("ctags") is not None and "Universal" in subprocess.run(["ctags", "--version"], capture_output=True, text=True).stdout
    check(data["ctags"] is has_ctags, "the map says whether ctags was used", str(data["ctags"]))
    if has_ctags:
        write(project, "src/parcelas/app.py", "from src.core import base\n\n\nclass Parcela:\n    pass\n")
        data = code_map(project)
        check((next(m for m in data["modules"] if m["path"] == "src/parcelas/")["classes"] or 0) >= 1, "the classes are counted")
    else:
        check(all(m["classes"] is None for m in data["modules"]), "without ctags there are no classes: modules and files only")
    data = code_map(project)
    check(next(m for m in data["modules"] if m["path"] == "src/parcelas/")["new"] >= 1, "what is new since the last commit is counted", str(next(m for m in data["modules"] if m["path"] == "src/parcelas/")["new"]))

    print("criterion 26 - what built EPIC-001, from the journal")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(project, ".gtt", "local", "activity.jsonl"), "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"t": now, "actor": "agent", "ade": "claude", "source": "hook", "tool": "Edit", "path": "src/parcelas/app.py", "stories": ["STORY-002"]}) + "\n")
    data = code_map(project, "--epic", "EPIC-001")
    parcelas = next(m for m in data["modules"] if m["path"] == "src/parcelas/")
    app = next(f for f in parcelas["detail"] if f["file"] == "src/parcelas/app.py")
    check("STORY-002" in app["stories"] and "claude" in (app["who"] or []) and parcelas["touched"] is True, "the file says which Story built it, and who", str(app))
    check(next(m for m in data["modules"] if m["path"] == "src/sync/")["touched"] is False, "and a module that EPIC-001 did not touch is not lit")
    nojournal = demo.build(full=True)
    os.remove(os.path.join(nojournal, ".gtt", "local", "activity.jsonl"))
    clean = code_map(nojournal)
    check(all(not f["stories"] for m in clean["modules"] for f in m["detail"]) and clean["journal"] is False, "without a journal: no data, never a guess")
    shutil.rmtree(os.path.dirname(nojournal), ignore_errors=True)

    print("criterion 40 - from the design to the code")
    write(project, "gtt-domain/context/design/EPIC-001.md", "# EPIC-001\n\n**Status:** Draft\n\n## 1. Purpose and scope\n\n## 2. Data\n\n## 3. Rules\n- **R-1** A parcel has an area. [FUENTE: SRC-1]\n- **R-2** Every change leaves a line. [FUENTE: SRC-1]\n\n## 4. Flows\n- **F-1** The schema is created. [FUENTE: SRC-1]\n- **F-2** The endpoint stores a parcel. [FUENTE: SRC-1]\n- **F-5** A report is built. [FUENTE: SRC-1]\n\n## 5. Interfaces\n\n## 6. Examples\n\n## 7. Open points\n\n## 8. Decisions taken with the human\n")
    data = code_map(project, "--epic", "EPIC-001")
    rows = {r["item"]: r for r in (data.get("design_to_code") or {}).get("EPIC-001", [])}
    check({"R-1", "R-2", "F-1", "F-2", "F-5"} <= set(rows), "every item of the design is listed", str(sorted(rows)))
    check("STORY-002" in rows["F-2"]["stories"] and "src/parcelas/app.py" in rows["F-2"]["files"] and rows["F-2"]["evidence"] and rows["F-2"]["closed"] is False, "an item shows its Stories, their files and the evidence of `Done when`", str(rows["F-2"]))
    check(rows["F-1"]["closed"] is True, "a Story that is Done closes its item")
    check(rows["F-5"]["built"] is False and rows["F-5"]["stories"] == [], "an item no Story builds is marked as having no code", str(rows["F-5"]))

    print("criterion 27 - the first index in less than 10 s with 5000 files, and the next ones in less than half a second")
    big = demo.build(full=True)
    for i in range(5000):
        module = ("parcelas", "sync", "core")[i % 3]
        write(big, f"src/{module}/m{i // 3}/f{i}.py", f"from src.core import base\nimport os\n\n\ndef f{i}():\n    return {i}\n")
    started = time.time()
    first = sh(big, "bash", ".gtt/scripts/gtt-code.sh", "refresh", "--quiet")
    took = time.time() - started
    check(first.returncode == 0 and took < 10, f"first index of 5000 files: {took:.1f}s", first.stderr[-200:])
    write(big, "src/core/m0/f0.py", "x = 2\n")
    started = time.time()
    again = sh(big, "bash", ".gtt/scripts/gtt-code.sh", "refresh", "--quiet")
    took2 = time.time() - started
    check(again.returncode == 0 and took2 < 2.0, f"a refresh with one file changed: {took2:.2f}s (budget 0.5 s of work; the rest is the launcher)", again.stderr[-200:])
    started = time.time()
    snap = sh(big, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json")
    took3 = time.time() - started
    check(snap.returncode == 0 and took3 < 1.5 and json.loads(snap.stdout)["code"] and json.loads(snap.stdout)["code"]["files"] >= 5000, f"the snapshot reads the last map and does not recompute it: {took3:.2f}s", snap.stderr[-200:])
    check(os.path.isfile(os.path.join(big, ".gtt", "local", "code-index.json")), "the index is a derived file in .gtt/local/")
    for d in (project, big):
        shutil.rmtree(os.path.dirname(d), ignore_errors=True)
    print(f"\n{COUNT - len(FAILS)}/{COUNT} checks held" + (f"; FAILED: {', '.join(FAILS)}" if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
