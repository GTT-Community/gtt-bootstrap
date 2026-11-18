#!/usr/bin/env python3
"""GTT Sonar - tests of the page, the render and the hook (Prompt 2): criteria 2, 3, 5, 6 and 10.

Every scenario runs on a DISPOSABLE copy of this project; the project itself is never modified.
Criterion 3 loads the page in headless Chrome when it is installed (reported as skipped when it is not).

  python .gtt/tests/sonar-render.py [--project .]

Exit 0 = every check held, 1 = at least one failed.
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FAILS, COUNT = [], 0

spec = importlib.util.spec_from_file_location("snap", os.path.join(HERE, "sonar-snapshot.py"))
snap_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snap_tests)

EVIL = ['<script>window.PWNED=1</script>', '<img src=x onerror="window.PWNED=2">', '</script><script>window.PWNED=3</script>', '<!-- x', '"\'&`${1+1}']


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


def luminance(hexcolor):
    rgb = [int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def many_stories(path, count):
    out = ["# Backlog", "", "## Epics", ""]
    for e in range(1, 11):
        out += [f"### EPIC-{e:03d} — Epic {e}", "**Status:** In Progress", "**Goal:** g", f"**Lane:** {'AB'[e % 2]}", "**Approved:** human — 2026-11-01", "", "#### Stories", ""]
        for s in range(count // 10):
            n = (e - 1) * (count // 10) + s + 1
            status = "Done" if s % 3 == 0 else "Planned"
            out += [f"##### STORY-{n:03d} — Story {n}", f"- **Status:** {status}", "- **Estimate:** 1h", ("- **Closed:** 2026-11-02 — abc1234 — ok" if status == "Done" else ""), ""]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")


def load_fixture():
    spec = importlib.util.spec_from_file_location("sonar_demo", os.path.join(HERE, "fixtures", "sonar-demo.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plan_checks(tmp, chrome):
    demo = load_fixture()
    project = demo.build(full=True)
    hostile_title = "<script>window.PWNED=7</script>"
    bl = os.path.join(project, "gtt-domain", "backlog.md")
    # a heading with <...> is a template example to the backlog parser and is skipped, so the hostile text goes in fields the Plan paints
    text = open(bl, encoding="utf-8").read().replace("- **Done when:** `pytest tests/test_rules.py` passes", "- **Done when:** `pytest tests/test_rules.py` passes " + hostile_title).replace("**Goal:** the platform runs and stores parcels", "**Goal:** " + hostile_title)
    open(bl, "w", encoding="utf-8").write(text)
    snap_path = os.path.join(tmp, "plan.json")
    proc = sh(project, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json", "--docs")
    open(snap_path, "w", encoding="utf-8").write(proc.stdout)
    static, served = os.path.join(tmp, "plan-static.html"), os.path.join(tmp, "plan-served.html")
    check(sh(project, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--out", static, snap_path).returncode == 0 and
          sh(project, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--served", "--out", served, snap_path).returncode == 0, "the same template renders in static and in served mode")
    s_text, v_text = open(static, encoding="utf-8").read(), open(served, encoding="utf-8").read()
    code = re.sub(r'<script type="application/json".*?</script>', "", s_text, flags=re.S)
    print("   ", [w for w in ("fetch(", "XMLHttpRequest", "/api/", "connect-src") if w in (code if w != "connect-src" else s_text)])
    check("fetch(" not in code and "XMLHttpRequest" not in code and "/api/" not in code and "connect-src" not in s_text, "the static page has no network code and its CSP has no connect-src")
    check("connect-src 'self'" in v_text and "fetch(" in v_text and "/api/act" in v_text, "the served page may talk to its own origin only")
    check(re.search(r"script-src 'sha256-[A-Za-z0-9+/=]{20,}'", s_text) and re.search(r"script-src 'sha256-[A-Za-z0-9+/=]{20,}'", v_text), "each mode has the hash of its own script")
    if not chrome:
        print("  skip  headless Chrome not installed: the DOM checks of the Plan were not run")
        return

    def dom(path, frag):
        return sh(project, chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=3000", "--dump-dom", f"file://{path}#/view={frag}").stdout

    def body_of(page):
        return page.split('id="app"', 1)[-1].split("<script", 1)[0]

    def words(page):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_of(page)))
    plan = dom(static, "plan")
    body = body_of(plan)
    check("<script" not in body and "&lt;script&gt;window.PWNED=7" in plan, "criterion 28: a text with <script> is text, in the Plan", "")
    check("window.PWNED=7" not in re.sub(r'<script type="application/json".*?</script>', "", plan.split('id="app"', 1)[0], flags=re.S), "and it ran nothing")
    for view in ("plan", "inbox", "activity", "health", "design", "help"):
        page = dom(static, view)
        check(len(body_of(page)) > 1500 and 'class="bar"' in body_of(page), f"criterion 28: the view `{view}` is drawn")
    w = words(plan)
    for needle in ("progress", "estimated date", "I need you", "to define", "alerts", "now", "last events", "plan", "front A", "EPIC-001", "EPIC-002", "STORY-003"):
        check(needle in w, f"criterion 28: the Plan shows `{needle}`")
    check(re.search(r"to define \d+", w) and re.search(r"yours \d+", w) and "with alerts" in w and "in progress" in w and "blocked" in w and "done" in w, "criterion 28: the filters are there, with their counts")
    check('class="epic prop"' in body and 'class="srow2 undef' in body, "criterion 28: the proposed Epic is dashed and a Story to define has its own form")
    print("criterion 29 - static mode: commands and text to copy instead of forms")
    check("save to the backlog" not in w and "or ask claude" not in w and 'id="f-STORY-003-Estimate"' not in body, "no form to fill in the static page")
    check("copy for the chat" in w and "gtt idea add --about GAP-004" not in w, "a text for the chat is there for what is the agent's")
    check("gtt approve EPIC-002" in w or "gtt answer 1 1" in w, "the act that is the human's comes as a command to copy, shown short")
    check("cd '" not in w, "and without the `cd`")
    check("This page is read only" in w and "read only" in w, "the page says it is read only")
    print("criterion 29 - served mode: the forms are there")
    sv = dom(served, "plan")
    svw = words(sv)
    check('id="f-STORY-003-Estimate"' in body_of(sv) and 'id="f-STORY-004-Done_when"' in body_of(sv) and "save to the backlog" in svw and "or ask claude: copy for the chat" in svw, "the Story to define has its fields and its two ways out")
    check('id="f-EPIC-002-Goal"' in body_of(sv) and 'id="f-EPIC-002-Out_of_Scope"' in body_of(sv), "the Proposed Epic has the form of its intent")
    check("editable" in svw, "the page says it is editable")
    check('id="ap-GAP-004"' in body_of(sv), "an open gap takes your input in the page")
    print("criterion 30 - with an older Bootstrap the Plan says so")
    old = json.load(open(snap_path, encoding="utf-8"))
    for key in ("readiness", "findings", "activity", "project_extra", "agreements", "shadow", "forecast_range", "sources", "mode"):
        old[key] = None
    for e in old["epics"]:
        for key in ("ready", "codes", "percent", "real_h", "active_h", "eta", "eta_range", "sha"):
            e[key] = None
    for s in old["stories"]:
        for key in ("ready", "codes", "next", "implements", "origin", "active_h", "real_h", "sha"):
            s[key] = None
    old["degraded"] = {"version": "1.23.0", "missing": ["findings"], "command": "gtt update"}
    old_path = os.path.join(tmp, "old.json")
    json.dump(old, open(old_path, "w"))
    oldhtml = os.path.join(tmp, "old.html")
    sh(project, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--served", "--out", oldhtml, old_path)
    ow = words(dom(oldhtml, "plan"))
    check("no data: update GTT in this repo" in ow and "read only" in ow and "EPIC-001" in ow, "the Plan draws what there is, says `no data: update GTT`, and is read only even when served")
    check('id="f-STORY-003-Estimate"' not in dom(oldhtml, "plan"), "and offers no form")
    print("1.26 - the Code view")
    sh(project, "bash", ".gtt/scripts/gtt-code.sh", "refresh", "--quiet")
    snap2 = os.path.join(tmp, "plan2.json")
    open(snap2, "w", encoding="utf-8").write(sh(project, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json", "--docs").stdout)
    page2 = os.path.join(tmp, "plan2.html")
    sh(project, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--out", page2, snap2)
    cw = words(dom(page2, "code&ce=EPIC-001&cm=src%2Fparcelas%2F"))
    check("module map" in cw and "src/parcelas" in cw and "src/core" in cw and "does it respect the architecture" in cw and "from design to code" in cw, "the Code view draws the map, the findings and design to code")
    check("code" in words(dom(page2, "plan")).split("activity")[1][:30], "the Code tab appears when the project has a code map")
    print("criterion 38 - Activity: what claude saw, the runs, and who did what")
    act = words(dom(static, "activity"))
    check("what claude saw" in act and "session.md" in act and "GTT Session State" in act, "what claude saw in its last session, read only")
    check("gtt run: result" in act and "RUN-000" in act, "the result of each `gtt run`")
    check("claude" in act and "you" in act and "unattributed" in act, "the filters by who did it")
    check("source: unattributed (sampling)" in words(dom(static, "plan")) or "source: claude (hook)" in words(dom(static, "plan")), "Now says where its data comes from")
    print("criterion 39 - every Epic and Story has `copy ref`")
    check(len(re.findall(r'aria-label="copy ref (?:EPIC|STORY)-\d+"', body)) >= 10, "copy ref on each Epic and Story", str(len(re.findall(r'aria-label="copy ref', body))))
    health = words(dom(static, "health"))
    check("governance" in health and "delivery" in health and "definition" in health and "GOV-GAP" in health and "DEF-STORY-ESTIMATE" in health, "Health shows the findings by plane")
    check(re.search(r'href="#/view=plan&amp;q=STORY-003"', dom(static, "health")) is not None, "each finding links to its item")
    shutil.rmtree(os.path.dirname(project), ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=ROOT)
    args = parser.parse_args()
    tmp, dest, _ = snap_tests.make_project(os.path.abspath(args.project))
    try:
        template = open(os.path.join(dest, ".gtt", "sonar", "template.html"), encoding="utf-8").read()
        run_render = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "render")
        check(run_render.returncode == 0, "render writes the page", run_render.stderr[-300:])
        html_path, json_path = (os.path.join(dest, ".gtt", "local", n) for n in ("sonar.html", "sonar.json"))
        page = open(html_path, encoding="utf-8").read() if os.path.exists(html_path) else ""
        check(os.path.exists(json_path), "render writes sonar.json next to it")
        check(sh(dest, "git", "check-ignore", "-q", ".gtt/local/sonar.html").returncode == 0 and sh(dest, "git", "check-ignore", "-q", ".gtt/local/sonar.json").returncode == 0,
              "sonar.html and sonar.json are outside git")

        print("criterion 2 - no network")
        code = re.sub(r'<script type="application/json".*?</script>', "", page, flags=re.S)
        for word in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "import(", "importScripts", "<iframe", "<link ", "<img "):
            check(word not in code, f"the page has no `{word}`")
        # The only addresses are plain links to the method's own site (home and guide): an <a href> the person clicks, never loaded by the page.
        loose = re.sub(r'href: "https://gtt-method\.org/(sonar/)?"', "", code)
        check(not re.search(r"https?://|//[a-z0-9.-]+\.[a-z]{2,}/", loose, re.I), "the page loads no external URL (only links to gtt-method.org)")
        check('href: "https://gtt-method.org/"' in code, "the page links home to gtt-method.org")
        check(not re.search(r"url\((?!['\"]?(\.\./|fonts/|\.\./sonar/fonts/))", code), "every url() is a local font")
        csp = re.search(r'Content-Security-Policy" content="([^"]*)"', page)
        csp = csp.group(1) if csp else ""
        check("default-src 'none'" in csp and "connect-src" not in csp and "script-src 'sha256-" in csp, "the CSP is default-src 'none' with the script by hash and no connect-src", csp)
        check("'unsafe-eval'" not in csp and "script-src 'unsafe-inline'" not in csp, "the CSP allows no eval and no inline script")
        check("innerHTML" not in template and "outerHTML" not in template and "insertAdjacentHTML" not in template and "document.write" not in template,
              "the template never builds markup from data (no innerHTML)")

        print("criterion 3 - hostile text is text")
        hostile = {"schema": "sonar.v1", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "repo": {"path": "/x", "key": "EVL", "name": EVIL[0]},
                   "suite_version": "1.0.0", "lang": "en", "project": {"phase": "DEV", "frozen_at": None, "profile": EVIL[1]},
                   "summary": {"progress_pct": 10, "stories_done": 1, "stories_total": 2, "forecast": None, "deadline": None, "on_time": None, "calibration": {"ratio": None, "uncalibrated": True}},
                   "columns": ["Planned", "In Progress", "Done"], "lanes": [{"id": "A", "name": "A"}],
                   "epics": [{"ref": "EPIC-001", "title": EVIL[2], "lane": EVIL[3], "state": "in_progress", "start": None, "end": None, "stories": {"done": 0, "in_progress": 1, "planned": 0}, "flags": []}],
                   "stories": [{"ref": "STORY-001", "epic": "EPIC-001", "title": EVIL[1], "status": "In Progress", "estimate_h": 1, "elapsed_h": None, "closed_by_evidence": False, "flags": []}],
                   "next": {"proposals": [{"ref": "P", "kind": "x", "title": EVIL[0], "command": EVIL[4]}], "epics_to_approve": [], "planned_epics": []},
                   "needs_you": [{"ref": "ASK-001", "kind": "ask", "title": EVIL[1], "weight": {"stories": 1, "hours": 1}, "command": EVIL[4]}],
                   "signals": [{"code": "X", "level": "WARNING", "ref": "STORY-001", "text": EVIL[2]}], "health": [],
                   "recent": [{"at": "2026-11-11T10:00:00Z", "actor": "agent", "action": "a", "ref": "STORY-001", "text": EVIL[0] + EVIL[3]}], "ideas": []}
        src = os.path.join(tmp, "hostile.json")
        json.dump(hostile, open(src, "w"))
        out = os.path.join(tmp, "hostile.html")
        made = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--out", out, src)
        check(made.returncode == 0, "a page can be rendered from a snapshot file", made.stderr[-200:])
        text = open(out, encoding="utf-8").read()
        data = re.search(r'<script type="application/json" id="sonar-data">(.*?)</script>', text, re.S)
        check(data is not None and "</script" not in data.group(1).lower() and "<!--" not in data.group(1), "the embedded JSON holds no `</script` and no `<!--`")
        check(data is not None and json.loads(data.group(1))["repos"][0]["snapshot"]["repo"]["name"] == EVIL[0], "the embedded JSON still parses back to the exact text")
        chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
        if not chrome:
            print("  skip  headless Chrome not installed: the DOM check of criterion 3 was not run")
        else:
            for view in ("plan&repo=%2Fx", "inbox&repo=%2Fx", "activity&repo=%2Fx", "health&repo=%2Fx", "design&repo=%2Fx", "design&dt=adr&repo=%2Fx", "help"):
                dom = sh(dest, chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=2000", "--dump-dom", f"file://{out}#/view={view}").stdout
                tag = view.split("&")[0]
                body = dom.split('id="app"', 1)[-1].split('<script', 1)[0]
                check("<img" not in body and "<script" not in body, f"[{tag}] no element was created from the text (no <img>, no <script> in the page body)")
                check("&lt;img src=x" in dom or tag not in ("plan",) or "&lt;script&gt;" in dom, f"[{tag}] the hostile text is on the page as text")

        print("criterion 24 - the Bandeja, Te necesito, Decisiones, the portfolio column and the Backlog fields, with test data")
        sh(dest, "git", "config", "user.name", "Ana")
        snap_tests.inbox_scenario(dest)
        shutil.copyfile(os.path.join(os.path.abspath(args.project), ".gtt", "contract", "pending.json"), os.path.join(dest, ".gtt", "contract", "pending.json"))
        recon = os.path.join(dest, ".gtt", "scripts", "gtt_inbox_reconcile.py")
        if True:     # the real reconcile lists nothing before a freeze: a stub, in the disposable copy, says which ADR was written by hand (same shape: path, name, command)
            with open(recon, "w", encoding="utf-8") as handle:
                handle.write('def adr_hand():\n    return [{"path": "gtt-domain/adr/ADR-003-hand.md", "name": "ADR-003-hand.md", "command": "gtt adr adopt gtt-domain/adr/ADR-003-hand.md"}]\n')
        with open(os.path.join(dest, "gtt-domain", "backlog.md"), "w", encoding="utf-8") as handle:
            handle.write("# Backlog\n\n## Epics\n\n### EPIC-030 — With origin\n**Status:** Proposed\n**Origin:** PROP-005\n**Priority:** urgent\n\n#### Stories\n\n##### STORY-300 — s\n- **Status:** Planned\n")
        snap24 = os.path.join(tmp, "snap24.json")
        proc = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json")
        open(snap24, "w", encoding="utf-8").write(proc.stdout)
        page24 = os.path.join(tmp, "page24.html")
        made = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--out", page24, snap24)
        check(proc.returncode == 0 and made.returncode == 0, "a page can be drawn from the Bandeja test data", made.stderr[-200:])
        text24 = open(page24, encoding="utf-8").read()
        check("</script" not in re.search(r'id="sonar-data">(.*?)</script>', text24, re.S).group(1).lower(), "the hostile titles and trail lines leave no `</script` in the embedded data")
        # the render files the inbox first (order 6.1) when the subcommand exists, and never fails when it does not or breaks
        stub = os.path.join(dest, ".gtt", "scripts", "gtt-inbox.sh")
        original = open(stub, encoding="utf-8").read()
        marker = os.path.join(dest, "reconciled.txt")
        open(stub, "w", encoding="utf-8").write('#!/usr/bin/env bash\n[ "$1 $2" = "reconcile --apply" ] && echo ran >> "$(dirname "$0")/../../reconciled.txt"\nexit 1\n')
        sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json")
        check(not os.path.exists(marker), "the snapshot never runs the reconcile (it writes nothing)")
        r = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--quiet")
        check(r.returncode == 0 and r.stdout == "" and r.stderr == "" and os.path.exists(marker), "the render runs `gtt-inbox.sh reconcile --apply` in silence, and a failing one does not break it", f"rc={r.returncode} {r.stderr[:80]}")
        r = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "render")
        check(r.returncode == 0, "the render of a project works with a failing reconcile")
        open(stub, "w", encoding="utf-8").write(original)
        if not chrome:
            print("  skip  headless Chrome not installed: the DOM checks of criterion 24 were not run")
        else:
            def dom_of(frag):
                return sh(dest, chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=2000", "--dump-dom", f"file://{page24}#/view={frag}").stdout
            def body_of(dom):
                return dom.split('id="app"', 1)[-1].split("<script", 1)[0]
            dom = dom_of("inbox&card=PROP-006")
            body = body_of(dom)
            check("<img" not in body and "<script" not in body, "[bandeja] no element was created from a title, a text or a trail line")
            check("&lt;img src=x" in dom and "PWNED=9" in dom, "[bandeja] the hostile text is on the page as text")
            for word in ("New", "In review", "To ratify", "In work", "Closed (7 days)"):
                check(f">{word}<" in re.sub(r"<span[^>]*>\d+</span>", "", body), f"[bandeja] the column `{word}` is there")
            check(">Parked<" not in body and ">Rejected<" not in body, "[bandeja] parked and rejected are not on the board until `all`")
            check('class="icard agent"' in body and 'class="icard"' in body, "[bandeja] a card of the agent and a card of a person differ (dashed / solid)")
            check("border:1px dashed var(--agent)" in template and ".icard{background:var(--surface);border:1px solid" in template, "[bandeja] the template gives the agent a dashed border and a person a solid one")
            for ref in ("IDEA-001", "IDEA-002", "IDEA-003", "PROP-001", "PROP-002", "PROP-003", "PROP-006", "PROP-007"):
                check(f'id="card-{ref}"' in body, f"[bandeja] the card of {ref} is drawn")
            check("from IDEA-004" in body and "your move" in body and "gtt promote ready-set" in body, "[bandeja] a card says where it came from and the act that is yours")
            check("trail" in body and "Work: EPIC-011" in body, "[bandeja] an open card shows the trail")
            alldom = body_of(dom_of("inbox&ia=1"))
            check(">Parked<" in re.sub(r"<span[^>]*>\d+</span>", "", alldom) and ">Rejected<" in re.sub(r"<span[^>]*>\d+</span>", "", alldom) and 'id="card-IDEA-010"' in alldom and 'id="card-PROP-009"' in alldom, "[bandeja] `all` adds the parked and the rejected")
            needs = body_of(dom_of("plan&na=1"))
            check("decide" in needs and "REV-" in needs and "ratify" in needs and "adopt" in needs, "[te necesito] review, ratify and adr-hand are drawn")
            check("gtt adr adopt" in needs and "gtt run 4" in needs and "gtt approve EPIC-010" in needs, "[te necesito] each act brings its command, shown short")
            check("cd '" not in re.sub(r"<[^>]+>", " ", needs) or "&amp;&amp;" not in re.sub(r"<[^>]+>", " ", needs), "[te necesito] the command is shown without the `cd`")
            mine = body_of(dom_of("inbox&mine=1"))
            check("for Ana" in mine and "for Luis" not in mine, "[para mí] the filter keeps what is for the git user (and what has no owner)")
            adr = body_of(dom_of("design&dt=adr"))
            check("CHANGE-0001" in adr and "ADR-002" in adr and "produced by PROP-001" in adr, "[decisiones] the list shows ADR and CHANGE with their origin")
            check("ADR-002" in adr and any(w in adr for w in ("accepted", "aceptado", "no state", "sin estado")), "[diseño] the Decisions tab lists every ADR with its state")
            two = os.path.join(tmp, "two.html")
            sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--out", two, snap24, snap24)
            port = sh(dest, chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=2000", "--dump-dom", f"file://{two}#/view=portfolio").stdout
            port = body_of(port)
            check("3 new · 1 to review · 3 to ratify" in port and ">inbox<" in port, "[portafolio] with two repos the column `inbox` says what waits", re.sub(r"<[^>]+>", " ", port)[:300])
            single = body_of(dom_of("portfolio"))
            check(">portfolio<" not in single, "[portafolio] with one repo there is no portfolio")
            plan = body_of(dom_of("plan"))
            check("origin: PROP-005" in plan and "priority: urgent" in plan, "[plan] each Epic shows its Origin and Priority")
            check(all(w in plan for w in ("EPIC-030", "STORY-300")), "[plan] the Epic and its Story are drawn")

        print("criterion 5 - a story closed by evidence appears at the next reload; the hook is fast")
        many_stories(os.path.join(dest, "gtt-domain", "backlog.md"), 200)
        event = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(dest, "gtt-domain", "backlog.md")}})
        started = time.time()
        hook = sh(dest, sys.executable, ".claude/hooks/sonar-render.py", stdin=event)
        elapsed = time.time() - started
        print(f"  info  hook with 200 stories: {elapsed:.2f}s")
        check(hook.returncode == 0 and elapsed < 1.5, "the hook regenerates in under 1.5s with 200 stories", f"{elapsed:.2f}s rc={hook.returncode}")
        first = json.load(open(json_path, encoding="utf-8"))
        check(first["summary"]["stories_total"] == 200 and len(first["stories"]) == 200, "the snapshot holds the 200 stories", str(first["summary"]))
        backlog = open(os.path.join(dest, "gtt-domain", "backlog.md"), encoding="utf-8").read()
        target = "##### STORY-002 — Story 2\n- **Status:** Planned\n- **Estimate:** 1h\n"
        check(target in backlog, "the scenario story is Planned")
        open(os.path.join(dest, "gtt-domain", "backlog.md"), "w", encoding="utf-8").write(backlog.replace(target, target.replace("Planned", "Done") + "- **Closed:** 2026-11-11 — def5678 — tests passed\n"))
        os.utime(os.path.join(dest, ".gtt", "local"), None)
        for name in os.listdir(os.path.join(dest, ".gtt", "local")):
            if name.endswith(".lock"):
                os.remove(os.path.join(dest, ".gtt", "local", name))
        sh(dest, sys.executable, ".claude/hooks/sonar-render.py", stdin=event)
        second = json.load(open(json_path, encoding="utf-8"))
        s2 = next(s for s in second["stories"] if s["ref"] == "STORY-002")
        check(s2["status"] == "Done" and s2["closed_by_evidence"] is True, "a story closed by evidence is in sonar.json after the hook", str(s2))
        check("STORY-002" in open(html_path, encoding="utf-8").read(), "and in sonar.html, which the page reloads")
        check(not re.search(r"http-equiv=.refresh", open(html_path, encoding="utf-8").read(), re.I) and "location.reload()" in template and "}, 5000)" in template,
              "the page reloads every 5 seconds, with a pause button")

        print("criterion 6 - the hook never fails, prints nothing, does not pile up")
        for label, stdin in (("a write that matters", event), ("garbage on stdin", "{not json"), ("empty stdin", ""),
                             ("a write that does not matter", json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/etc/hostname"}}))):
            r = sh(dest, sys.executable, ".claude/hooks/sonar-render.py", stdin=stdin)
            check(r.returncode == 0 and r.stdout == "" and r.stderr == "", f"exit 0 and silent: {label}", f"rc={r.returncode} out={r.stdout[:80]!r} err={r.stderr[:80]!r}")
        template_path = os.path.join(dest, ".gtt", "sonar", "template.html")
        os.rename(template_path, template_path + ".off")
        r = sh(dest, sys.executable, ".claude/hooks/sonar-render.py", stdin=event)
        check(r.returncode == 0 and r.stdout == "" and r.stderr == "", "exit 0 and silent even when the render itself fails")
        q = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--quiet")
        check(q.returncode == 0 and q.stdout == "" and q.stderr == "", "`render --quiet` exits 0 and prints nothing when it fails")
        os.rename(template_path + ".off", template_path)
        before = os.path.getmtime(json_path)
        with open(os.path.join(dest, ".gtt", "local", "sonar.lock"), "w") as handle:
            handle.write("1")
        time.sleep(0.05)
        sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "render", "--quiet")
        check(os.path.getmtime(json_path) == before, "a render already running is not repeated")
        os.remove(os.path.join(dest, ".gtt", "local", "sonar.lock"))
        settings = json.load(open(os.path.join(dest, ".claude", "settings.json"), encoding="utf-8"))
        cmds = [h["command"] for entry in settings["hooks"]["PostToolUse"] for h in entry["hooks"]]
        check(any("sonar-render.py" in c for c in cmds), "the hook is registered in PostToolUse")
        context = open(os.path.join(dest, ".gtt", "scripts", "gtt-session-context.sh"), encoding="utf-8").read()
        check("gtt-sonar.sh start" in context and "|| true" in context.split("gtt-sonar.sh start")[1][:60], "the page is refreshed at session start and never fails it")

        print("criterion 10 - contrast and keyboard")
        tokens = dict(re.findall(r"--([a-z-]+):(#[0-9A-Fa-f]{6})", template.split("</style>")[0]))
        pairs = [("text", "bg", 4.5), ("muted", "bg", 4.5), ("dim", "bg", 4.5), ("agent", "bg", 4.5), ("needs", "bg", 4.5), ("danger", "bg", 4.5),
                 ("text", "surface", 4.5), ("muted", "surface", 4.5), ("dim", "surface", 4.5), ("agent", "surface", 4.5), ("dim", "rail", 4.5), ("muted", "rail", 4.5),
                 ("needs", "needs-bg", 4.5), ("agent", "agent-bg", 4.5), ("text", "agent-bg", 4.5), ("text", "cmd", 4.5), ("dim", "cmd", 4.5), ("agent", "surface", 4.5), ("danger", "surface", 4.5)]
        for fg, bg, need in pairs:
            r = ratio(tokens[fg], tokens[bg])
            check(r >= need, f"{fg} on {bg} is {r:.1f}:1 (needs {need}:1)")
        check("#5F738A" not in template.upper(), "the old 5F738A text colour is gone")
        check(not re.search(r"onclick=|tabindex=\"-", template) and "addEventListener(\"click\"" in template, "actions are real buttons and links, not clickable divs")
        check(":focus-visible{outline:2px solid var(--agent)" in template, "the focus is visible: 2px in agent")
        check("animation" not in template and "transition" not in template, "no animations")

        print("1.25 - the Plan, Activity, Health: criteria 28 to 30, 38 and 39 (the fixture with its eight problems)")
        plan_checks(tmp, chrome)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{COUNT - len(FAILS)}/{COUNT} checks held" + (f"; FAILED: {', '.join(FAILS)}" if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
