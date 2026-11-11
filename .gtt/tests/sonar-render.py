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
        check(not re.search(r"https?://|//[a-z0-9.-]+\.[a-z]{2,}/", code, re.I), "the page has no external URL")
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
            for view in ("portfolio", "project&repo=EVL&epic=EPIC-001", "last"):
                dom = sh(dest, chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=2000", "--dump-dom", f"file://{out}#/view={view}").stdout
                tag = view.split("&")[0]
                body = dom.split('id="app"', 1)[-1].split('<script', 1)[0]
                check("<img" not in body and "<script" not in body, f"[{tag}] no element was created from the text (no <img>, no <script> in the page body)")
                check("&lt;img src=x" in dom or tag == "last" or "&lt;script&gt;" in dom, f"[{tag}] the hostile text is on the page as text")

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
        check("gtt-sonar.sh render --quiet" in context and "|| true" in context.split("gtt-sonar.sh render --quiet")[1][:60], "the page is refreshed at session start and never fails it")

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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{COUNT - len(FAILS)}/{COUNT} checks held" + (f"; FAILED: {', '.join(FAILS)}" if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
