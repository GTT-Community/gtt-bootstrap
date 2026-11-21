#!/usr/bin/env python3
"""A report that names something carries its Sonar link (gtt-link.sh) and the pending questions come with theirs.

  K1  every kind of ref has its place in Sonar and a ref with none is left out
  K2  the address: the served page when Sonar answers, the static page when it does not, nothing for a project Sonar was never opened for
  K3  a review opens the card of the entry it is about
  K4  `gtt-pending.sh show` carries the link of each open question and review, and stays as it was when there is none to give
  K5  the contract every ADE reads says it

  python3 .gtt/tests/sonar-links.py [--project .] [--keep]
Exit 0 = every check held, 1 = at least one failed.
"""
import argparse
import http.server
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acc", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
write, bash = acc.write, acc.bash


def check(label, cond, detail=""):
    assert isinstance(label, str), "check(label, condition): the label comes first"
    acc.check(bool(cond), label, detail)


class Ping(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"sonar": true}' if self.path == "/_ping" else b"x"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def link(cwd, *refs, home=None):
    env = dict(os.environ)
    if home:
        env["GTT_HOME"] = home
    import subprocess
    done = subprocess.run(["bash", ".gtt/scripts/gtt-link.sh", *refs], cwd=cwd, capture_output=True, text=True, env=env)
    return done.returncode, done.stdout, done.stderr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-sonar-links-")
    here = os.getcwd()
    server = None
    try:
        # K1 ----------------------------------------------------------------------------------------------------
        print("K1  a place in Sonar for each kind of ref")
        sys.path.insert(0, os.path.join(project, ".gtt", "scripts"))
        import gtt_link
        cases = {"STORY-783": "view=plan&q=STORY-783", "STORY-ALR22c": "view=plan&q=STORY-ALR22c", "EPIC-032": "view=plan&q=EPIC-032",
                 "PROP-009": "view=inbox&card=PROP-009", "IDEA-004": "view=inbox&card=IDEA-004", "ASK-003": "view=plan&f=mine",
                 "DEC-012": "view=plan&f=mine", "ADR-013": "view=design&dt=adr", "GAP-006": "view=health&hq=GAP-006",
                 "GOV-GAP": "view=health&hq=GOV-GAP", "DLV-NO-PLAN": "view=health&hq=DLV-NO-PLAN"}
        for ref, want in cases.items():
            check(f"{ref} -> {want}", gtt_link.route(ref) == want, str(gtt_link.route(ref)))
        check("a ref that is not Sonar's is left out", gtt_link.route("P-783-1") is None and gtt_link.route("src/app.ts") is None and gtt_link.route("") is None)

        # K2 ----------------------------------------------------------------------------------------------------
        print("K2  the address")
        p = acc.fresh(project, tmp, "link")
        home = os.path.join(tmp, "home")
        os.makedirs(os.path.join(home, "sonar"))
        rc, out, err = link(p, "STORY-1", home=home)
        check("a project Sonar was never opened for gets no link, and is told how to open it", rc == 0 and out == "" and "gtt sonar" in err, out + err)
        write(os.path.join(p, ".gtt", "local", "sonar.html"), "<html></html>")
        rc, out, err = link(p, "STORY-1", "EPIC-2", "nonsense", "STORY-1", home=home)
        lines = out.strip().splitlines()
        check("with the page there and no server: the static page, one line per ref that has a place, without repeats",
              len(lines) == 2 and all("file://" in l and "sonar.html#/view=plan&q=" in l for l in lines), out)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Ping)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]
        write(os.path.join(home, "sonar", "server.json"), json.dumps({"pid": 1, "port": port}))
        rc, out, err = link(p, "STORY-1", home=home)
        check("with Sonar answering: the served address, naming the project", out.startswith(f"STORY-1  http://127.0.0.1:{port}/#/view=plan&q=STORY-1&repo=") and "repo=" in out, out)
        server.shutdown()
        server.server_close()
        server = None
        rc, out, err = link(p, "STORY-1", home=home)
        check("a server that stopped answering falls back to the static page", "file://" in out and "127.0.0.1" not in out, out)
        rc, out, err = link(p, "--json", "PROP-1", home=home)
        check("--json is machine readable", json.loads(out)["links"][0]["ref"] == "PROP-1", out)

        # K3 + K4 -----------------------------------------------------------------------------------------------
        print("K3  a review opens the card of its entry; K4  the pending questions carry their link")
        canon = "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md"
        write(os.path.join(p, "gtt-domain", "proposals", "drafts", "redis.md"),
              f"Proposed Context Change\n\n{canon}\nFile: gtt-domain/context/glossary.md\nCurrent statement: order\nSuggested change: add a term\nReason: new word\nImpact: low\nRisk: low\n")
        rc, o, e = bash(p, ".gtt/scripts/gtt-inbox.sh", "add", "Change for redis", "--apply")
        idea = re.search(r"IDEA-\d+", o).group(0)
        rc, o, e = bash(p, ".gtt/scripts/gtt-inbox.sh", "propose", "--file", "gtt-domain/proposals/drafts/redis.md", "--level", "spec", "--form", "2",
                        "--origin", idea, "--slug", "redis", "--apply")
        check("(a proposal with its review is open)", rc == 0 and "REV-" in o, o + e)
        rev = re.search(r"REV-(\d+)", o).group(0)
        prop = re.search(r"proposals/(PROP-\d+)", o).group(1)
        rc, out, err = link(p, rev, home=home)
        check(f"{rev} opens the card of {prop}", f"card={prop}" in out, out + err)
        rc, out, err = bash(p, ".gtt/scripts/gtt-pending.sh", "show")
        check("the pending batch carries the link of each question", "↳ Sonar:" in out and f"card={prop}" in out, out[-500:])
        os.remove(os.path.join(p, ".gtt", "local", "sonar.html"))
        rc, plain, err = bash(p, ".gtt/scripts/gtt-pending.sh", "show")
        check("without a page for the project the batch is exactly what it was: no link line", "↳ Sonar:" not in plain and "REV-" in plain, plain[-300:])

        # K5 ----------------------------------------------------------------------------------------------------
        print("K5  the contract every ADE reads")
        read = lambda rel: open(os.path.join(project, rel), encoding="utf-8").read()
        check("AGENTS.md says it and points at operations.md", "## Sonar links" in read("AGENTS.md") and "gtt-link.sh" in read("AGENTS.md") and "*Sonar links*" in read("AGENTS.md"))
        check("operations.md holds the table of refs", "## Sonar links" in read(".gtt/docs/agents/operations.md") and "`PROP-n`, `IDEA-n`, `REV-n`" in read(".gtt/docs/agents/operations.md"))
        check("the Claude table has a row for it", "gtt-link.sh" in read(".claude/CLAUDE.md"))
    finally:
        if server:
            server.shutdown()
        os.chdir(here)
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
