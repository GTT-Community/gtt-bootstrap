#!/usr/bin/env python3
"""GTT Sonar - the served mode of the page, against a TEST server (not the one of the CLI): criteria 10 to 13 of the page side.

  python3 .gtt/tests/sonar-served.py

Renders the page of the demo project in `served` mode, serves it from a throwaway http.server together with /api/snapshot (with ETag) and
/api/act (which records what it receives), and drives headless Chrome through the DevTools protocol: it types in a form, saves, answers a
question, leaves an input on a gap, gets a refusal because the backlog changed, and lets the snapshot change under a form half written.
It needs Chrome and the `websockets` module; without either, the checks are reported as skipped. Writes nothing in this repository."""
import asyncio
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ.setdefault("GTT_SONAR_NO_WATCH", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
COUNT, FAILS = 0, []


def check(cond, label, detail=""):
    global COUNT
    COUNT += 1
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        FAILS.append(label)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class State:
    page_html = ""
    snapshot = None
    acts = []
    respond = (200, {"ok": True})
    version = 1


def payload():
    return {"schema": "sonar.page.v1", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "repos": [{"snapshot": State.snapshot}], "mode": "served"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/api/snapshot"):
            body = json.dumps(payload()).encode()
            tag = '"v%d"' % State.version
            if self.headers.get("If-None-Match") == tag:
                self.send_response(304)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("ETag", tag)
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(State.page_html.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode()
        State.acts.append({"path": self.path, "header": self.headers.get("X-GTT-Sonar"), "type": self.headers.get("Content-Type"), "body": json.loads(raw or "{}")})
        code, body = State.respond
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


class Page:
    """One tab of headless Chrome, driven through the DevTools protocol."""

    def __init__(self, chrome, url):
        self.port = free_port()
        self.profile = tempfile.mkdtemp(prefix="gtt-chrome-")
        self.proc = subprocess.Popen([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", f"--remote-debugging-port={self.port}", f"--user-data-dir={self.profile}", "--window-size=1440,1800", url],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.next_id = 0
        self.ws = None

    async def connect(self):
        import websockets
        target = None
        for _ in range(60):
            try:
                listing = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=2))
                pages = [t for t in listing if t.get("type") == "page"]
                if pages:
                    target = pages[0]
                    break
            except Exception:
                pass
            await asyncio.sleep(0.25)
        if target is None:
            raise RuntimeError("Chrome did not open")
        self.ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=None)

    async def ev(self, expression):
        self.next_id += 1
        mine = self.next_id
        await self.ws.send(json.dumps({"id": mine, "method": "Runtime.evaluate", "params": {"expression": expression, "returnByValue": True, "awaitPromise": True}}))
        while True:
            message = json.loads(await self.ws.recv())
            if message.get("id") == mine:
                return (message.get("result") or {}).get("result", {}).get("value")

    async def close(self):
        try:
            await self.ws.close()
        finally:
            self.proc.terminate()
            shutil.rmtree(self.profile, ignore_errors=True)


JS = """
window.__setv = function (id, v) { var e = document.getElementById(id); if (!e) return false; e.focus(); e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })); return true; };
window.__click = function (txt) { var b = [].slice.call(document.querySelectorAll('button')).filter(function (x) { return x.textContent.indexOf(txt) >= 0; })[0]; if (!b) return false; b.click(); return true; };
window.__save = function (id) { var e = document.getElementById(id); var f = e && e.closest('.form'); var b = f && [].slice.call(f.querySelectorAll('button')).filter(function (x) { return x.textContent.indexOf('save') >= 0; })[0]; if (!b) return false; b.click(); return true; };
window.__text = function () { return document.getElementById('app').innerText.replace(/\\s+/g, ' '); };
true;
"""


async def drive(chrome, port):
    page = Page(chrome, f"http://127.0.0.1:{port}/#/view=plan")
    try:
        await page.connect()
        await asyncio.sleep(2.5)
        await page.ev(JS)
        text = await page.ev("window.__text()")
        check("editable" in text and "save to the backlog" in text, "the served page is editable and shows the forms")
        print("criterion 10 - filling a Story saves only what was typed, through backlog.set, with the sha of what was seen")
        story = next(s for s in State.snapshot["stories"] if s["ref"] == "STORY-003")
        await page.ev("window.__setv('f-STORY-003-Estimate', '1.5h')")
        await page.ev("window.__save('f-STORY-003-Estimate')")
        await asyncio.sleep(1)
        got = State.acts[-1] if State.acts else {}
        check(got.get("path") == "/api/act" and got.get("header") == "1" and "json" in (got.get("type") or ""), "a POST to /api/act with the X-GTT-Sonar header", str(got)[:200])
        body = got.get("body", {})
        check(body.get("op") == "backlog.set" and body["args"]["ref"] == "STORY-003" and body["args"]["fields"] == {"Estimate": "1.5h"} and body["args"]["sha"] == story["sha"],
              "op backlog.set, the ref, only the field that was typed, and the sha of the block", str(body)[:240])
        check(body.get("repo") == State.snapshot["repo"]["path"], "and the repo it is for")
        print("criterion 11 - the backlog changed while you typed: refused, nothing lost on the page")
        State.respond = (409, {"error": "stale"})
        await page.ev("window.__setv('f-STORY-004-Done_when', 'E-1 passes · tests/test_audit.py')")
        await page.ev("window.__save('f-STORY-004-Done_when')")
        await asyncio.sleep(1)
        text = await page.ev("window.__text()")
        check("changed while you typed" in text and "nothing was saved" in text, "the page says so", text[-300:])
        kept = await page.ev("document.getElementById('f-STORY-004-Done_when') ? document.getElementById('f-STORY-004-Done_when').value : null")
        check(kept == "E-1 passes · tests/test_audit.py", "and what was typed is still there", str(kept))
        State.respond = (200, {"ok": True})
        print("a repaint never takes away a form half written")
        await page.ev("window.__setv('f-STORY-004-Done_when', 'half written')")
        State.snapshot = json.loads(json.dumps(State.snapshot))
        State.snapshot["stories"] = [dict(s, title=(s["title"] or "") + " (changed)") if s["ref"] == "STORY-002" else s for s in State.snapshot["stories"]]
        State.version += 1
        await asyncio.sleep(3.2)
        text = await page.ev("window.__text()")
        kept = await page.ev("document.getElementById('f-STORY-004-Done_when') ? document.getElementById('f-STORY-004-Done_when').value : null")
        check(kept == "half written", "the draft survives the next snapshot", str(kept))
        await page.ev("document.activeElement && document.activeElement.blur()")
        await asyncio.sleep(2.6)
        text = await page.ev("window.__text()")
        check("(changed)" in text, "and once you stop typing the page shows the new snapshot (every 2 s, with the ETag)", text[:200])
        kept = await page.ev("document.getElementById('f-STORY-004-Done_when') ? document.getElementById('f-STORY-004-Done_when').value : null")
        check(kept == "half written", "with the draft still in its field", str(kept))
        print("criterion 13 - answering a question from the page")
        before = len(State.acts)
        await page.ev("window.__click('1 · Yes')")
        await asyncio.sleep(1)
        got = State.acts[-1] if len(State.acts) > before else {}
        check(got.get("body", {}).get("op") == "pending.answer" and got["body"]["args"] == {"ref": "1", "answer": "1"}, "op pending.answer with the number of the event and the option", str(got)[:200])
        print("criterion 14 - an input on a gap goes to the Inbox with --about")
        await page.ev("window.__setv('ap-GAP-004', 'use a local file')")
        await asyncio.sleep(0.3)
        before = len(State.acts)
        await page.ev("window.__click('send to the Inbox')")
        await asyncio.sleep(1)
        got = State.acts[-1] if len(State.acts) > before else {}
        check(got.get("body", {}).get("op") == "inbox.add" and got["body"]["args"] == {"text": "use a local file", "about": "GAP-004"}, "op inbox.add with the text and `about`", str(got)[:200])
    finally:
        await page.close()


async def drive_lang(chrome, port):
    """The Go server serves the page with no data and the page fills itself by polling: the language must follow the snapshot (an English project is not shown in Spanish)."""
    page = Page(chrome, f"http://127.0.0.1:{port}/#/view=plan")
    try:
        await page.connect()
        await asyncio.sleep(3.5)
        await page.ev(JS)
        text = await page.ev("window.__text()")
        print("served with no initial data: the language comes from the snapshot")
        check("save to the backlog" in text and "inbox" in text and "bandeja" not in text and "guardar en el backlog" not in text, "an English project, polled in, is shown in English", text[:160])
    finally:
        await page.close()


def main():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    try:
        import websockets  # noqa: F401
    except ImportError:
        chrome = None
    if not chrome:
        print("  skip  headless Chrome or the websockets module is not installed: the served mode was not driven")
        return 0
    spec = importlib.util.spec_from_file_location("sonar_demo", os.path.join(HERE, "fixtures", "sonar-demo.py"))
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    project = demo.build(full=True)
    tmp = tempfile.mkdtemp(prefix="gtt-served-")
    try:
        snap = subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json", "--docs"], cwd=project, capture_output=True, text=True, timeout=120).stdout
        snap_path = os.path.join(tmp, "snap.json")
        open(snap_path, "w", encoding="utf-8").write(snap)
        out = os.path.join(tmp, "served.html")
        subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "render", "--served", "--out", out, snap_path], cwd=project, capture_output=True, text=True, timeout=120)
        State.page_html = open(out, encoding="utf-8").read()
        State.snapshot = json.loads(snap)
        port = free_port()
        server = HTTPServer(("127.0.0.1", port), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            asyncio.run(drive(chrome, port))
            State.page_html = re.sub(r'(<script[^>]*id="sonar-data"[^>]*>).*?(</script>)', lambda m: m.group(1) + '{"mode": "served", "repos": []}' + m.group(2), State.page_html, count=1, flags=re.S)
            assert '"repos": []' in State.page_html, 'the page with no initial data was not built'
            asyncio.run(drive_lang(chrome, port))
        finally:
            server.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(os.path.dirname(project), ignore_errors=True)
    print(f"\n{COUNT - len(FAILS)}/{COUNT} checks held" + (f"; FAILED: {', '.join(FAILS)}" if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
