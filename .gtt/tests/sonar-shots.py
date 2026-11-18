#!/usr/bin/env python3
"""GTT Sonar - captures of every view, in the two modes, for the projects you give it (the review of Prompt 3).

  python3 .gtt/tests/sonar-shots.py OUTDIR [--project NAME=PATH ...] [--demo]

--demo builds the fixture with its eight problems and the 32 sources. Each --project is a folder whose snapshot is taken by THIS Bootstrap's
scripts (a project with an older Bootstrap is read in degraded mode). For each project and each mode it writes OUTDIR/<name>-<mode>-<view>.png:
static (read only, commands and text to copy) and served (forms, from a throwaway local server with no operations behind it).
Needs headless Chrome and Pillow; it writes nothing in the projects."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
VIEWS = ("plan", "inbox", "activity", "health", "design", "help")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snapshot_of(project):
    env = dict(os.environ, GTT_SONAR_NO_WATCH="1")
    out = subprocess.run([sys.executable, os.path.join(ROOT, ".gtt", "scripts", "gtt_sonar.py"), "snapshot", "--json", "--docs"], cwd=project, capture_output=True, text=True, env=env, timeout=120)
    return out.stdout


def shot(chrome, url, path, width=1440, height=3400):
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}", "--virtual-time-budget=4000", f"--screenshot={path}", url],
                   capture_output=True, timeout=120)
    try:
        from PIL import Image, ImageChops
        im = Image.open(path).convert("RGB")
        bg = Image.new("RGB", im.size, im.getpixel((5, im.size[1] - 5)))
        box = ImageChops.difference(im, bg).getbbox()
        if box:
            im.crop((0, 0, width, min(im.size[1], box[3] + 40))).save(path)
    except Exception:
        pass


def main(argv):
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome or len(argv) < 1:
        print("usage: sonar-shots.py OUTDIR [--project NAME=PATH ...] [--demo]  (needs Chrome)")
        return 2
    out = os.path.abspath(argv[0])
    os.makedirs(out, exist_ok=True)
    projects, cleanup = [], []
    rest = argv[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--demo":
            demo = load("sonar_demo", os.path.join(HERE, "fixtures", "sonar-demo.py"))
            path = demo.build(full=True)
            projects.append(("demo", path))
            cleanup.append(os.path.dirname(path))
        elif rest[i] == "--project":
            i += 1
            name, _, path = rest[i].partition("=")
            projects.append((name, os.path.abspath(path)))
        i += 1
    served_mod = load("sonar_served", os.path.join(HERE, "sonar-served.py"))
    tmp = tempfile.mkdtemp(prefix="gtt-shots-")
    snaps = {}
    try:
        for name, path in projects:
            snaps[name] = os.path.join(tmp, name + ".json")
            open(snaps[name], "w", encoding="utf-8").write(snapshot_of(path))
        engine = os.path.join(ROOT, ".gtt", "scripts", "gtt_sonar.py")
        for name, path in projects:
            static, served = os.path.join(tmp, name + "-static.html"), os.path.join(tmp, name + "-served.html")
            subprocess.run([sys.executable, engine, "render", "--out", static, snaps[name]], cwd=ROOT, capture_output=True, timeout=120)
            subprocess.run([sys.executable, engine, "render", "--served", "--out", served, snaps[name]], cwd=ROOT, capture_output=True, timeout=120)
            for view in VIEWS:
                shot(chrome, f"file://{static}#/view={view}", os.path.join(out, f"{name}-static-{view}.png"))
            served_mod.State.page_html = open(served, encoding="utf-8").read()
            served_mod.State.snapshot = json.load(open(snaps[name], encoding="utf-8"))
            port = served_mod.free_port()
            server = HTTPServer(("127.0.0.1", port), served_mod.Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                for view in ("plan", "inbox"):
                    shot(chrome, f"http://127.0.0.1:{port}/#/view={view}", os.path.join(out, f"{name}-served-{view}.png"))
            finally:
                server.shutdown()
        if len(projects) > 1:
            both = os.path.join(tmp, "both.html")
            subprocess.run([sys.executable, engine, "render", "--out", both] + [snaps[n] for n, _ in projects], cwd=ROOT, capture_output=True, timeout=120)
            shot(chrome, f"file://{both}#/view=portfolio", os.path.join(out, "portfolio-static.png"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for d in cleanup:
            shutil.rmtree(d, ignore_errors=True)
    print("captures in", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
