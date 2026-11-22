#!/usr/bin/env python3
"""The consultation thread: the questions that need thinking go to ONE conversation in Claude web (gtt-consult.sh, Sonar's top bar).

  C1  the URL of the thread: only a Claude web conversation or project, cleaned; anything else is refused
  C2  the first message: summaries with their anchors, within the size a link can carry, the mandatory parts always, no provenance noise
  C3  the batch: each open question with its options and the proposal behind a review, the design changes since the last answer, the answer block
  C4  the thread is registered, forgotten and taken as up to date; what changed is what the person has not seen
  C5  the answer block the person pastes is read and recorded, always in their words, and the question is answered
  C6  Sonar: the bar is at the top of EVERY view, with the first message when there is no thread and the thread when there is; each question points to it

  python3 .gtt/tests/consult.py [--project .] [--keep]
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

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acc", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
write, bash = acc.write, acc.bash
CANON = "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md"
THREAD = "https://claude.ai/chat/0b6e1f2a-4c3d-4e5f-8a9b-1c2d3e4f5a6b"


def check(label, cond, detail=""):
    assert isinstance(label, str), "check(label, condition): the label comes first"
    acc.check(bool(cond), label, detail)


def script(p, *args, stdin=None):
    done = subprocess.run(["bash", ".gtt/scripts/gtt-consult.sh", *args], cwd=p, capture_output=True, text=True, input=stdin)
    return done.returncode, done.stdout, done.stderr


def build_project(project, tmp, name):
    p = acc.fresh(project, tmp, name)
    ctx = os.path.join(p, "gtt-domain", "context")
    write(os.path.join(ctx, "solution-vision.md"), f"# Solution vision\n\n{CANON}\n\n## Problem\n\nFarm data lives in spreadsheets and chats, so nobody sees a field from the soil to the market. "
          "[FUENTE: MAE:L148] More text that goes on.\n\n## Users\n\nProducers without a digital tool; voice capture in the field is the hook.\n")
    write(os.path.join(ctx, "architecture.md"), f"# Architecture\n\n{CANON}\n\n## Architectural style\n\nModular monolith: a core plus plug-in modules.\n\n## Integration strategy\n\n"
          "Asynchronous events through an outbox, delivered at least once.\n")
    write(os.path.join(ctx, "constraints.md"), f"# Constraints\n\n{CANON}\n\n## Platform\n\nSelf-hosted server in Chile, no cloud.\n")
    write(os.path.join(ctx, "stack.md"), f"# Stack\n\n{CANON}\n\n| Layer | Choice |\n|---|---|\n| Language | Strict TypeScript |\n| Datastore | PostgreSQL with PostGIS |\n")
    write(os.path.join(ctx, "glossary.md"), f"# Glossary\n\n{CANON}\n\n- **Cuartel**: a block of a field planted with one variety.\n- **Predio**: a farm.\n")
    write(os.path.join(p, "gtt-domain", "adr", "ADR-002-modular-monolith.md"), f"# ADR-002 — Modular monolith\n\n{CANON}\n\n- Status: Accepted\n\n## Decision\n\nOne deployable.\n")
    return p


def open_questions(p):
    """An ASK and a REV, both open: the two kinds of question the thread takes."""
    rc, o, e = bash(p, ".gtt/scripts/gtt-pending.sh", "ask", "--type", "product", "--header", "Billing", "--question", "Do we bill by field or by farm?",
                    "--why", "It decides the data model of the invoices.", "--option", "By field | One invoice line per field.",
                    "--option", "By farm | One line per farm.", "--recommended", "2", "--blocks", "STORY-001", "--apply")
    ok_ask = rc == 0
    write(os.path.join(p, "gtt-domain", "proposals", "drafts", "redis.md"),
          f"Proposed Context Change\n\n{CANON}\nFile: gtt-domain/context/glossary.md\nCurrent statement: a farm is a predio\nSuggested change: add the term sector\nReason: the field team says sector\nImpact: low\nRisk: low\n")
    rc, o, e = bash(p, ".gtt/scripts/gtt-inbox.sh", "add", "Add the term sector", "--apply")
    idea = re.search(r"IDEA-\d+", o).group(0)
    rc, o, e = bash(p, ".gtt/scripts/gtt-inbox.sh", "propose", "--file", "gtt-domain/proposals/drafts/redis.md", "--level", "spec", "--form", "2",
                    "--origin", idea, "--slug", "sector", "--apply")
    return ok_ask and rc == 0 and "REV-" in o, re.search(r"proposals/(PROP-\d+)", o).group(1) if rc == 0 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-consult-")
    here = os.getcwd()
    try:
        # C1 ----------------------------------------------------------------------------------------------------
        print("C1  the URL of the thread")
        p = build_project(project, tmp, "thread")
        os.chdir(p)
        sys.path.insert(0, os.path.join(p, ".gtt", "scripts"))
        import gtt_consult
        good = {THREAD: THREAD, THREAD + "/": THREAD, THREAD + "?utm=x#frag": THREAD, "https://claude.ai/project/0b6e1f2a-4c3d-4e5f": "https://claude.ai/project/0b6e1f2a-4c3d-4e5f"}
        for given, want in good.items():
            check(f"{given[:60]} -> a clean thread URL", gtt_consult.thread_url(given) == want, str(gtt_consult.thread_url(given)))
        for bad in ("http://claude.ai/chat/0b6e1f2a-4c3d", "https://evil.example/chat/0b6e1f2a-4c3d", "https://claude.ai.evil.com/chat/0b6e1f2a-4c3d",
                    "https://claude.ai/new", "https://claude.ai/chat/", "javascript:alert(1)", "", "claude://claude.ai/chat/0b6e1f2a-4c3d"):
            check(f"refused: {bad[:50] or '(empty)'}", gtt_consult.thread_url(bad) is None)
        rc, out, err = script(p, "set", "https://evil.example/chat/0b6e1f2a-4c3d")
        check("`set` of something that is not a Claude conversation saves nothing", rc == 1 and not os.path.exists(os.path.join(p, ".gtt", "local", "consult.json")), out + err)

        # C2 ----------------------------------------------------------------------------------------------------
        print("C2  the first message")
        sd = gtt_consult.seed()
        text = sd["text"]
        check("it holds a summary per document, each with its anchor (file#section)", "solution-vision.md#problem" in text and "architecture.md#integration-strategy" in text, text[:300])
        check("the stack, the glossary and the decisions are in it", "Strict TypeScript" in text and "Cuartel" in text and "ADR-002" in text and "Modular monolith" in text)
        check("the provenance tags are the design's bookkeeping and stay out", "[FUENTE" not in text and "MAE:L148" not in text)
        check("it tells Claude how to work here and how to answer GTT", "You cannot see the repository" in text and "Respuesta para GTT:" in text)
        check("it fits what a link to Claude Desktop can carry", sd["chars"] <= 12000 and sd["desktop_ok"] is True, str(sd["chars"]))
        gtt_consult.contract()["seed"]["max_chars"] = 2500
        small = gtt_consult.seed()
        check("under a small budget the mandatory parts stay and what does not fit is named as left out",
              small["chars"] <= 2700 and "Respuesta para GTT:" in small["text"] and "Left out for size" in small["text"] and small["omitted"], str(small["chars"]) + str(small["omitted"]))
        gtt_consult.contract()["seed"]["max_chars"] = 12000
        write(os.path.join(p, ".gtt", "methodology.json"), json.dumps({"language": "es"}))
        es = gtt_consult.seed()["text"]
        check("in Spanish when the project speaks it", "Hilo de consulta de GTT" in es and "No ves el repositorio" in es)
        os.remove(os.path.join(p, ".gtt", "methodology.json"))

        # C3 ----------------------------------------------------------------------------------------------------
        print("C3  the batch of open questions")
        none, refs = gtt_consult.batch()
        check("with nothing open there is no batch", none is None and refs == [])
        opened, prop = open_questions(p)
        check("(an ASK and a REV are open)", opened and prop, str(prop))
        text, refs = gtt_consult.batch()
        check("both questions are in the batch", len(refs) == 2 and any(r.startswith("ASK-") for r in refs) and any(r.startswith("REV-") for r in refs), str(refs))
        check("each carries its options and its way of answering", "By field" in text and "By farm" in text and re.search(r"Answer with: `\d+: <option number or short answer>`", text), text[:600])
        check("a review carries the proposal behind it, so the person can judge it without the repository", "Context of the proposal:" in text and "add the term sector" in text, text[-900:])
        check("it ends with the block the person pastes back", text.rstrip().endswith("Yo lo pego en mi agente") is False and "Respuesta para GTT:" in text)
        only, ones = gtt_consult.batch(refs[0])
        check("one question can be asked alone", ones == [refs[0]] and only.count("### ") == 1, str(ones))
        rc, out, err = script(p, "batch", "--json")
        check("the batch is available as JSON for Sonar and agents", rc == 0 and json.loads(out)["refs"] == refs, out[:200])

        # C4 ----------------------------------------------------------------------------------------------------
        print("C4  the thread, and what the person has not seen")
        check("with no baseline nothing is said to have changed", gtt_consult.changes() == [])
        rc, out, err = script(p, "set", THREAD)
        check("a Claude conversation is registered", rc == 0 and "registered" in out, out + err)
        st = json.load(open(os.path.join(p, ".gtt", "local", "consult.json"), encoding="utf-8"))
        check("it lives in the person's own state (never committed)", st["thread"]["url"] == THREAD and ".gtt/local" in gtt_consult.contract()["state_file"])
        check("registering it takes the thread as up to date with today's design", gtt_consult.changes() == [])
        write(os.path.join(p, "gtt-domain", "context", "constraints.md"), open(os.path.join(p, "gtt-domain", "context", "constraints.md"), encoding="utf-8").read() + "\n## Budget\n\nA ceiling per month.\n")
        write(os.path.join(p, "gtt-domain", "adr", "ADR-003-events.md"), f"# ADR-003 — Events\n\n{CANON}\n\n- Status: Accepted\n")
        ch = gtt_consult.changes()
        kinds = {c["path"]: c["kind"] for c in ch}
        check("what the design did since is listed: a document changed, an ADR new", kinds.get("gtt-domain/context/constraints.md") == "changed" and kinds.get("gtt-domain/adr/ADR-003-events.md") == "added", str(kinds))
        text, refs = gtt_consult.batch()
        check("the next batch says it before the questions", text.index("What changed in the design") < text.index("### ") and "ADR-003" in text and "constraints.md" in text)
        rc, out, err = script(p, "seen")
        check("`seen` takes the thread as up to date again", rc == 0 and gtt_consult.changes() == [])
        rc, out, err = script(p, "status")
        check("status says where things stand", THREAD in out and "2 open question" in out, out)
        rc, out, err = script(p, "clear")
        check("clearing forgets the thread and keeps the baseline", rc == 0 and "thread" not in json.load(open(os.path.join(p, ".gtt", "local", "consult.json"), encoding="utf-8")))

        # C5 ----------------------------------------------------------------------------------------------------
        print("C5  the answer block")
        text, refs = gtt_consult.batch()
        numbers = [int(re.search(r"(\d+)$", r).group(1)) for r in refs]
        asked = next(int(re.search(r"(\d+)$", r).group(1)) for r in refs if r.startswith("ASK-"))
        reviewed = next(int(re.search(r"(\d+)$", r).group(1)) for r in refs if r.startswith("REV-"))
        pasted = f"Claude says: both are fine.\n\nRespuesta para GTT:\n{asked}: 2\n{reviewed}: 1\n"
        rows = gtt_consult.parse_answers(pasted)
        check("the block is read: the number and the answer of each line", [(n, a) for n, a, _ in rows] == [(asked, "2"), (reviewed, "1")], str(rows))
        check("a conversation without the block is not read as one", gtt_consult.parse_answers("we should do 3: it depends\nyes") == [])
        rc, out, err = script(p, "answers", "--text", pasted)
        check("without --apply it only says what it would do, and gives the person's own command for each valid answer",
              "dry run" in out and f"gtt answer {asked} 2" in out and f"gtt answer {reviewed} 1" in out, out + err)
        rc, out, err = script(p, "answers", "--text", f"Respuesta para GTT:\n{reviewed}: 9")
        check("a dry run checks the answer against the question: option 9 of a review with four is refused", rc == 1 and "options 1 to" in out, out + err)
        # The agent records the human's words: the hook keeps their last messages; the quote must be in them.
        import gtt_pending
        c = gtt_pending.contract()
        gtt_pending.store_prompt(pasted, c)
        rc, out, err = script(p, "answers", "--text", pasted, "--apply")
        events = {int(e["number"]): e for e in gtt_pending.events(c)}
        check("applied, each answer is recorded and the question is answered", rc == 0 and events[asked]["answered"] and events[reviewed]["answered"], out + err)
        check("the answered questions are no longer open", gtt_consult.batch()[0] is None)
        rc, out, err = script(p, "answers", "--text", "Respuesta para GTT:\\n99: 1")
        check("a block whose line breaks come as the text `\\n` (how an operation argument carries it) is read the same",
              rc == 1 and "99" in out and "no open question" in out, out + err)
        rc, out, err = script(p, "answers", "--text", "no block here")
        check("text with no answer lines is refused with the format", rc == 1 and "13: 1" in err, out + err)
        rc, out, err = script(p, "answers", "--text", "Respuesta para GTT:\n99: 1", "--apply")
        check("an answer to a question that is not open is refused, never invented", rc == 1 and "no open question" in out, out + err)
        os.chdir(here)

        # C6 ----------------------------------------------------------------------------------------------------
        print("C6  Sonar: the bar on top of every view, and the questions pointing to the thread")
        chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
        q = build_project(project, tmp, "sonar")
        opened, prop = open_questions(q)

        def render(project_dir, out):
            snap = subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json"], cwd=project_dir, capture_output=True, text=True)
            open(os.path.join(project_dir, "snap.json"), "w", encoding="utf-8").write(snap.stdout)
            subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "render", "--out", out, "snap.json"], cwd=project_dir, capture_output=True, text=True)
            return json.loads(snap.stdout)
        page = os.path.join(tmp, "sonar-nothread.html")
        snap = render(q, page)
        cs = snap.get("consult") or {}
        check("the snapshot carries the consultation: first message, questions, no thread yet", cs.get("thread") is None and cs.get("count") == 2 and "Respuesta para GTT:" in cs.get("seed", ""), str(list(cs)))
        check("each question is there by its ref, the review also by its proposal's", any(k.startswith("ASK-") for k in cs.get("items", {})) and prop in cs.get("items", {}), str(list(cs.get("items", {}))))
        if not chrome:
            print("  skip  headless Chrome not installed: the DOM checks of the bar were not run")
        else:
            def dom(path, fragment):
                return subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=3000", "--dump-dom", f"file://{path}#/view={fragment}"],
                                      capture_output=True, text=True).stdout

            def words(html):
                return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.split('id="app"', 1)[-1].split("<script", 1)[0]))
            for view in ("plan", "inbox", "activity", "health", "design", "help"):
                html = dom(page, view)
                body = html.split('id="app"', 1)[-1]
                check(f"{view}: the bar is the first thing under the header", 'class="consult"' in body and body.index('class="consult"') < body.index("<main"), view)
            html = dom(page, "plan")
            w = words(html)
            check("with no thread: it offers to create it (copy the first message, open Claude), and says how to register its URL",
                  "Create the thread" in w and "gtt-consult.sh set" in w and "claude://claude.ai/new?q=" in html, w[:300])
            inbox = dom(page, "inbox")
            check("the Inbox card of the proposal has its Consult button", inbox.count("Consult in Claude") >= 1, str(inbox.count("Consult in Claude")))
            check("the I-need-you block has one on the question", html.count("Consult in Claude") >= 1, str(html.count("Consult in Claude")))
            sh = subprocess.run(["bash", ".gtt/scripts/gtt-consult.sh", "set", THREAD], cwd=q, capture_output=True, text=True)
            page2 = os.path.join(tmp, "sonar-thread.html")
            snap = render(q, page2)
            check("registered, the snapshot carries the thread", (snap.get("consult") or {}).get("thread", {}).get("url") == THREAD, sh.stdout + sh.stderr)
            html = dom(page2, "plan")
            w = words(html)
            check("with the thread: a link to it, and the open questions go in one click", f'href="{THREAD}"' in html and "Open the thread" in w and "Consult the open ones (2)" in w, w[:300])
            check("it no longer offers to create one", "Create the thread" not in w)
            # The click, for real: the page runs in Chrome with window.open and the clipboard replaced by recorders (the CSP meta is dropped for the
            # test only, to let the probe run); each button must open the right address and copy the right text.
            def click(page_path, fragment, selector_js, wait=400):
                raw = open(page_path, encoding="utf-8").read()
                raw = re.sub(r"<meta[^>]*Content-Security-Policy[^>]*>", "", raw, flags=re.I)
                probe = ("<script>window.__o=[];window.open=function(u){window.__o.push(u);return null};window.__c=[];"
                         "Object.defineProperty(navigator,'clipboard',{value:{writeText:function(t){window.__c.push(t);return Promise.resolve()}}});"
                         f"setTimeout(function(){{var b={selector_js};if(!b){{document.title=JSON.stringify({{error:'no button'}});return}}b.click();"
                         "setTimeout(function(){document.title=JSON.stringify({open:window.__o,copied:window.__c[0]||'',label:b.textContent})},60)},"
                         f"{wait});</script></body>")
                raw = raw.replace("</body>", probe)
                path = os.path.join(tmp, "probe.html")
                open(path, "w", encoding="utf-8").write(raw)
                out = subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=4000", "--dump-dom", f"file://{path}#/view={fragment}"],
                                     capture_output=True, text=True).stdout
                m = re.search(r"<title>(.*?)</title>", out, re.S)
                import html as _html
                try:
                    return json.loads(_html.unescape(m.group(1)))
                except Exception:
                    return {"error": (m.group(1) if m else out[:200])}
            snapthread = json.load(open(os.path.join(q, "snap.json"), encoding="utf-8"))["consult"]
            all_btn = "Array.prototype.filter.call(document.querySelectorAll('.consult button'),function(x){return /Consult the open/.test(x.textContent)})[0]"
            res = click(page2, "plan", all_btn)
            check("`Consult the open ones` opens the thread and copies the whole batch", res.get("open") == [THREAD] and res.get("copied") == snapthread["batch"], str(res)[:300])
            check("and tells the person to paste", "paste it in the thread" in res.get("label", ""), res.get("label", ""))
            one = "document.querySelector('.needs .consult-q, .nrow .consult-q')"
            res = click(page2, "plan", one)
            check("a question's own button opens the SAME thread and copies that question", res.get("open") == [THREAD] and "### ASK-001" in res.get("copied", "") and "### REV" not in res.get("copied", ""), str(res)[:300])
            card = "document.querySelector('.icard .consult-q')"
            res = click(page2, "inbox", card)
            check("the proposal's card in the Inbox points to it too", res.get("open") == [THREAD] and "### REV-002" in res.get("copied", ""), str(res)[:300])
            res = click(page2, "health", "Array.prototype.filter.call(document.querySelectorAll('.consult button'),function(x){return /First message/.test(x.textContent)})[0]")
            check("`First message` (to start another thread) opens Claude's new chat with the first message", res.get("open") == ["https://claude.ai/new"] and res.get("copied") == snapthread["seed"], str(res)[:300])
            res = click(page, "design", "Array.prototype.filter.call(document.querySelectorAll('.consult button'),function(x){return /Create the thread/.test(x.textContent)})[0]")
            check("with no thread, `Create the thread` opens Claude's new chat with the first message", res.get("open") == ["https://claude.ai/new"] and "GTT consultation thread" in res.get("copied", ""), str(res)[:300])
    finally:
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
