#!/usr/bin/env python3
"""GTT - findings: criteria 1 to 9, 31, 33, 35 and 36 of GTT-ORDEN-sonar-herramienta.md, on the demo project and the full one.

  python3 .gtt/tests/findings.py

Builds a project with eight problems planted on purpose (fixtures/sonar-demo.py) and another with the 32 sources of the audit, and asks
`gtt-findings.sh` what it sees. Writes nothing in this repository."""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

os.environ.setdefault("GTT_SONAR_NO_WATCH", "1")
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
spec = importlib.util.spec_from_file_location("sonar_demo", os.path.join(ROOT, ".gtt", "tests", "fixtures", "sonar-demo.py"))
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


def findings(dest, *extra):
    proc = sh(dest, "bash", ".gtt/scripts/gtt-findings.sh", "list", "--json", *extra)
    return json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else {"findings": [], "readiness": {}, "counts": {}, "failed": ["run"]}


def by_code(data, code, ref=None):
    return [f for f in data["findings"] if f["code"] == code and (ref is None or f["ref"] == ref)]


def rewrite(dest, rel, fn):
    path = os.path.join(dest, rel)
    text = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(fn(text))


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def event(dest, tool, path=None, command=None, session="s1", ade="claude"):
    payload = {"tool_name": tool, "session_id": session, "tool_input": ({"file_path": path} if path else {"command": command})}
    return subprocess.run(["bash", ".gtt/scripts/gtt-activity.sh", "log", "--ade", ade], cwd=dest, input=json.dumps(payload), capture_output=True, text=True, timeout=60)


def journal(dest):
    path = os.path.join(dest, ".gtt", "local", "activity.jsonl")
    return [json.loads(l) for l in open(path, encoding="utf-8").read().splitlines()] if os.path.isfile(path) else []


def put_journal(dest, entries):
    path = os.path.join(dest, ".gtt", "local", "activity.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("".join(json.dumps(e, sort_keys=True) + "\n" for e in entries))


def prompt2():
    import datetime
    utc = datetime.timezone.utc
    now = datetime.datetime.now(utc)
    print("criterion 19 - Now: with the hook it says claude; with the sampler, unattributed; with neither, no data")
    d = demo.build()
    event(d, "Edit", path=os.path.join(d, "src", "parcelas", "app.py"))
    state = json.loads(sh(d, "bash", ".gtt/scripts/gtt-activity.sh", "now", "--json").stdout)
    check(state["source"] == "claude" and state["attributed"] is True and state["last_source"] == "hook" and state["story"] == "STORY-002", "with the hook: attributed to claude, on STORY-002", str(state))
    d2 = demo.build()
    shutil.rmtree(os.path.join(d2, ".gtt", "local"), ignore_errors=True)
    none = json.loads(sh(d2, "bash", ".gtt/scripts/gtt-activity.sh", "now", "--json").stdout)
    check(none["source"] is None and none["last_t"] is None, "with neither hook nor sampler: no data", str(none))
    sys.path.insert(0, os.path.join(d2, ".gtt", "scripts"))
    cwd = os.getcwd()
    os.chdir(d2)
    import gtt_activity
    before = gtt_activity.porcelain()
    os.makedirs("src/parcelas", exist_ok=True)
    with open("src/parcelas/new.py", "w") as handle:
        handle.write("x = 1\n")
    gtt_activity.sample(before)
    os.chdir(cwd)
    sys.path.pop(0)
    sys.modules.pop("gtt_activity", None)
    sampled = json.loads(sh(d2, "bash", ".gtt/scripts/gtt-activity.sh", "now", "--json").stdout)
    check(sampled["source"] == "unattributed" and sampled["attributed"] is False and "src/parcelas/new.py" in sampled["files"], "with the sampler: the same files, unattributed", str(sampled))

    print("criterion 20 - code changing for 15 minutes with no Story In Progress; the agent hears it once per session")
    d3 = demo.build()
    rewrite(d3, "gtt-domain/backlog.md", lambda t: t.replace("- **Status:** In Progress", "- **Status:** Planned"))
    start = now - datetime.timedelta(minutes=16)
    put_journal(d3, [{"t": iso(start + datetime.timedelta(minutes=m)), "actor": "agent", "ade": "claude", "source": "hook", "tool": "Edit", "path": f"src/parcelas/f{m}.py", "stories": []} for m in (0, 5, 10, 16)])
    hit = by_code(findings(d3), "DEF-WORK-NO-STORY")
    check(len(hit) == 1 and hit[0]["level"] == "NOTICE" and hit[0]["owner"] == "agent", "after 16 minutes: a NOTICE of the agent's", str([h["text"] for h in hit]))
    put_journal(d3, [{"t": iso(now - datetime.timedelta(minutes=32 - m)), "actor": "agent", "ade": "claude", "source": "hook", "tool": "Edit", "path": f"src/parcelas/f{m}.py", "stories": []} for m in (0, 8, 16, 24, 32)])
    check(by_code(findings(d3), "DEF-WORK-NO-STORY")[0]["level"] == "WARNING", "after 30 minutes: a WARNING")
    first = event(d3, "Edit", path=os.path.join(d3, "src", "parcelas", "z.py"), session="abc")
    second = event(d3, "Edit", path=os.path.join(d3, "src", "parcelas", "y.py"), session="abc")
    other = event(d3, "Edit", path=os.path.join(d3, "src", "parcelas", "x.py"), session="def")
    check("In Progress" in first.stdout and second.stdout.strip() == "" and "In Progress" in other.stdout and first.stdout.count("\n") == 1, "the hook says it once per session, in one line", first.stdout[:200])
    check(event(d3, "Edit", path=os.path.join(d3, "gtt-domain", "backlog.md"), session="zzz").stdout.strip() == "", "changing the backlog is not code: silence")

    print("criterion 21 - the journal keeps no content or arguments, at most 1000 lines, and the agent cannot write it")
    d4 = demo.build()
    event(d4, "Bash", command="pytest -k secret=TOP-SECRET-KEY tests/")
    raw = open(os.path.join(d4, ".gtt", "local", "activity.jsonl"), encoding="utf-8").read()
    check("TOP-SECRET-KEY" not in raw and json.loads(raw.splitlines()[-1])["tool"] == "pytest", "a shell command keeps its first word only")
    put_journal(d4, [{"t": iso(now), "actor": "agent", "source": "hook", "tool": "Edit", "path": f"src/f{i}.py", "stories": ["STORY-002"]} for i in range(1100)])
    event(d4, "Edit", path=os.path.join(d4, "src", "last.py"))
    check(len(journal(d4)) <= 1000, "at most 1000 lines", str(len(journal(d4))))
    d4_ade = os.path.join(d4, ".gtt", "ade.json")
    open(d4_ade, "w").write(json.dumps({"schema": 1, "primary": "claude"}))
    sys.path.insert(0, os.path.join(d4, ".gtt", "scripts"))
    import gtt_protect
    check(bool(gtt_protect.protected_token(d4, ".gtt/local/activity.jsonl")) and bool(gtt_protect.protected_token(d4, ".gtt/local/activity-state.json")), "the decision core protects it")
    sys.path.pop(0)
    sys.modules.pop("gtt_protect", None)
    deny = json.load(open(os.path.join(ROOT, ".claude", "settings.json")))["permissions"]["deny"]
    check("Write(/.gtt/local/activity.jsonl)" in deny and "Edit(/.gtt/local/activity.jsonl)" in deny, "settings.json denies it")
    hooks = json.dumps(json.load(open(os.path.join(ROOT, ".claude", "settings.json")))["hooks"]["PostToolUse"])
    check("activity-log.py" in hooks and os.path.isfile(os.path.join(ROOT, ".kiro", "hooks", "gtt-activity-log.json")), "the hook is registered in Claude Code and in Kiro")

    print("criterion 22 - a Story from 18:00 to 10:00 the next day, with two hours of actions, has two active hours")
    d5 = demo.build()
    day = (now - datetime.timedelta(days=2)).replace(hour=18, minute=0, second=0, microsecond=0)
    nxt = day + datetime.timedelta(hours=16)
    put_journal(d5, [{"t": iso(day + datetime.timedelta(minutes=10 * i)), "actor": "agent", "source": "hook", "tool": "Edit", "path": "src/a.py", "stories": ["STORY-001"]} for i in range(7)]
                + [{"t": iso(nxt - datetime.timedelta(minutes=60 - 10 * i)), "actor": "agent", "source": "hook", "tool": "Edit", "path": "src/a.py", "stories": ["STORY-001"]} for i in range(7)])
    with open(os.path.join(d5, "gtt-domain", "delivery-log.jsonl"), "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"t": iso(day), "kind": "story", "id": "STORY-001", "from": "Planned", "to": "In Progress"}) + "\n")
        handle.write(json.dumps({"t": iso(nxt), "kind": "story", "id": "STORY-001", "from": "In Progress", "to": "Done"}) + "\n")
    report = json.loads(sh(d5, "bash", ".gtt/scripts/gtt-delivery.sh", "report", "--json").stdout)
    epic = next(e for e in report["epics"] if e["epic"] == "EPIC-001")
    row = next(s for s in epic["story_hours"] if s["story"] == "STORY-001")
    check(row["real_h"] == 16.0 and row["active_h"] == 2.0, "report --json: 16 clock hours, 2 active", str(row))
    check(report["calibration"]["basis"] == "active", "the calibration uses the active hours when the Story has a journal", str(report["calibration"]))
    nojournal = demo.build()
    with open(os.path.join(nojournal, "gtt-domain", "delivery-log.jsonl"), "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"t": iso(day), "kind": "story", "id": "STORY-001", "from": "Planned", "to": "In Progress"}) + "\n")
        handle.write(json.dumps({"t": iso(nxt), "kind": "story", "id": "STORY-001", "from": "In Progress", "to": "Done"}) + "\n")
    report2 = json.loads(sh(nojournal, "bash", ".gtt/scripts/gtt-delivery.sh", "report", "--json").stdout)
    check(report2["calibration"]["basis"] == "clock" and next(e for e in report2["epics"] if e["epic"] == "EPIC-001")["active_h"] is None, "without a journal it uses the clock, and says so")

    print("criterion 23 - with fewer than 3 Stories measured the date is a range, and it says uncalibrated")
    check(report["uncalibrated"] is True and isinstance(report["forecast"]["eta_range"], list) and len(report["forecast"]["eta_range"]) == 2
          and report["forecast"]["eta_range"][0] <= report["forecast"]["eta_range"][1], "the forecast is a range", str(report["forecast"]))
    check(all(e["eta_range"] is None or len(e["eta_range"]) == 2 for e in report["epics"]), "and so is each Epic's")

    print("DLV-EPIC-OVER and DLV-STORY-IDLE, from the journal")
    d6 = demo.build()
    start6 = now - datetime.timedelta(hours=30)
    with open(os.path.join(d6, "gtt-domain", "delivery-log.jsonl"), "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"t": iso(start6), "kind": "story", "id": "STORY-002", "from": "Planned", "to": "In Progress"}) + "\n")
    put_journal(d6, [{"t": iso(start6 + datetime.timedelta(minutes=10 * i)), "actor": "agent", "source": "hook", "tool": "Edit", "path": "src/a.py", "stories": ["STORY-002"]} for i in range(4)])
    codes = {f["code"] for f in findings(d6)["findings"]}
    check("DLV-STORY-IDLE" in codes, "an In Progress Story with no action for a day is idle")
    put_journal(d6, [{"t": iso(now - datetime.timedelta(minutes=10 * i)), "actor": "agent", "source": "hook", "tool": "Edit", "path": "src/a.py", "stories": ["STORY-002"]} for i in range(80)])
    check("DLV-EPIC-OVER" in {f["code"] for f in findings(d6)["findings"]}, "active hours past 1.2x the estimate of an open Epic")

    print("criterion 32 - next_action skips a Story that waits for the human and proposes the next ready one; session.md says what is to define")
    d7 = demo.build()
    open(os.path.join(d7, ".gtt", "ade.json"), "w").write(json.dumps({"schema": 1, "primary": "claude", "participating": ["claude"]}))
    os.remove(os.path.join(d7, "gtt-domain", "adr", "drafts", "IDEA-001-cache-layer.md"))      # a draft waiting for triage comes first: keep the inbox empty
    rewrite(d7, "gtt-domain/backlog.md", lambda t: t.replace("- **Status:** In Progress", "- **Status:** Done"))
    nxt7 = json.loads(sh(d7, "bash", ".gtt/scripts/gtt-project.sh", "next-action", "--json").stdout)["next_action"]
    check(nxt7 and nxt7["kind"] == "story" and "STORY-003" in nxt7["text"], "with no Story In Progress, GTT names the next one and says to define its gaps first", str(nxt7))
    rewrite(d7, "gtt-domain/backlog.md", lambda t: t.replace("##### STORY-003 — Validation rules\n- **Status:** Planned", "##### STORY-003 — Validation rules\n- **Status:** Planned\n- **Blocked by:** GAP-004"))
    rewrite(d7, "gtt-domain/backlog.md", lambda t: t.replace("- **Estimate:** ?", "- **Estimate:** 1h"))
    rewrite(d7, "gtt-domain/backlog.md", lambda t: t.replace("se definen al implementar", "`pytest tests/test_audit.py` passes"))
    nxt7 = json.loads(sh(d7, "bash", ".gtt/scripts/gtt-project.sh", "next-action", "--json").stdout)["next_action"]
    check(nxt7 and "STORY-003" in nxt7["text"] and "skipped" in nxt7["text"] and "STORY-004" in nxt7["text"], "a Story that waits for the human is skipped and said", str(nxt7))
    sh(d7, "bash", ".gtt/scripts/gtt-status.sh")
    session = open(os.path.join(d7, "gtt-domain", "session.md"), encoding="utf-8").read()
    check(re.search(r"To define: \d+ Epics? · \d+ Stor", session) is not None, "session.md carries the line `To define`", session[:80])

    print("criterion 37 - closing a Story brings one line with the offer of a review (once the code view exists)")
    d8 = demo.build()
    open(os.path.join(d8, ".gtt", "scripts", "gtt_code.py"), "w").write("# stub\n")
    sh(d8, "bash", ".gtt/scripts/gtt-delivery.sh", "log")
    rewrite(d8, "gtt-domain/backlog.md", lambda t: t.replace("##### STORY-002 — Endpoint\n- **Status:** In Progress", "##### STORY-002 — Endpoint\n- **Status:** Done"))
    hook = subprocess.run([sys.executable, os.path.join(d8, ".claude", "hooks", "delivery-log.py")], cwd=d8, input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(d8, "gtt-domain", "backlog.md")}}),
                          capture_output=True, text=True, timeout=60)
    said = json.loads(hook.stdout)["hookSpecificOutput"]["additionalContext"] if hook.stdout.strip() else ""
    check("Review what was built: Sonar → Code → STORY-002" in said and hook.stdout.count("\n") == 1, "one line", hook.stdout[:200])
    again = subprocess.run([sys.executable, os.path.join(d8, ".claude", "hooks", "delivery-log.py")], cwd=d8, input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(d8, "gtt-domain", "backlog.md")}}),
                           capture_output=True, text=True, timeout=60)
    check(again.stdout.strip() == "", "and only once per Story")
    for x in (d, d2, d3, d4, d5, nojournal, d6, d7, d8):
        shutil.rmtree(os.path.dirname(x), ignore_errors=True)


def main():
    print("the demo project: eight problems planted on purpose")
    dest = demo.build()
    data = findings(dest)
    check(not data["failed"], "no owner script failed", str(data["failed"]))

    print("criterion 2 - the eight problems appear, each with its ref, owner, where and source")
    want = {"DEF-STORY-ESTIMATE": "STORY-003", "DEF-STORY-DONE-WHEN": "STORY-004", "DEF-STORY-GAP": "STORY-005", "DEF-STORY-IMPLEMENTS": "STORY-006",
            "DEF-STORY-BLOCKED-NOCAUSE": "STORY-007", "DEF-EPIC-INTENT": "EPIC-002", "DEF-INBOX-ADR-DRAFT": "IDEA-001", "GTT-SHADOW-STATE": "docs/PREGUNTAS.md"}
    for code, ref in want.items():
        hits = by_code(data, code, ref)
        f = hits[0] if hits else {}
        check(bool(hits) and f.get("owner") in ("human", "agent") and f.get("where") and f.get("source") and f.get("text"), f"{code} on {ref}, with owner, where and source", str(f))
    shape = {"code", "plane", "level", "ref", "epic", "where", "owner", "for", "source", "text", "fix"}
    check(all(shape <= set(f) and {"fields", "about", "command", "chat"} <= set(f["fix"]) for f in data["findings"]), "every finding has the shape of section 4.1")
    check({f["plane"] for f in data["findings"]} <= {"definition", "governance", "delivery", "code"}, "the planes are the four of the contract")

    print("criterion 3 - what the registry, the pending events, the runs, the sources and the gaps hold")
    for code, ref in (("GOV-OBSERVATION", "src/orphan/"), ("GOV-DEC", None), ("DEF-ANSWER-TO-APPLY", None), ("GOV-RUN", None), ("GOV-SOURCE", None), ("GOV-GAP", "GAP-004"), ("DEF-STORY-BLOCKED", "STORY-009")):
        check(bool(by_code(data, code, ref)), f"{code} shows up" + (f" on {ref}" if ref else ""))
    check(by_code(data, "DEF-STORY-BLOCKED", "STORY-009")[0]["owner"] == "human", "a Story an ASK blocks is the human's")
    check(by_code(data, "GOV-RUN")[0]["fix"]["command"] == "gtt run 1", "a run waiting for the human brings its command")

    print("criterion 9 - what comes next is a WARNING; the rest is a NOTICE; nothing new is BLOCKING")
    first = by_code(data, "DEF-STORY-ESTIMATE", "STORY-003")[0]
    check(first["level"] == "WARNING" and first.get("next") is True, "a definition finding on the Story that comes next is a WARNING", str(first["level"]))
    check(not [f for f in data["findings"] if f["level"] == "BLOCKING"], "no finding is BLOCKING")
    far = os.path.join(dest, "gtt-domain", "backlog.md")
    rewrite(dest, "gtt-domain/backlog.md", lambda t: t.replace("##### STORY-003", "##### STORY-020 — Far away\n- **Status:** Planned\n- **Implements:** EPIC-001#R-1\n- **Estimate:** ?\n- **Done when:** `pytest tests/x.py`\n\n##### STORY-003"))
    rewrite(dest, "gtt-domain/backlog.md", lambda t: t.replace("##### STORY-008", "##### STORY-021 — Later\n- **Status:** Planned\n- **Implements:** EPIC-001#R-1\n- **Estimate:** ?\n- **Done when:** `pytest tests/y.py`\n\n##### STORY-008"))
    # STORY-020 and STORY-003 are the next two of the front; STORY-004 and later are not
    more = findings(dest)
    check(by_code(more, "DEF-STORY-DONE-WHEN", "STORY-004")[0]["level"] == "NOTICE" or by_code(more, "DEF-STORY-DONE-WHEN", "STORY-004")[0].get("next") is False,
          "a Story beyond the next two of its front is a NOTICE")

    print("criterion 6 - Estimate: ? is a finding; without the field and without declared planning, nothing")
    d6 = demo.build()
    rewrite(d6, "gtt-domain/backlog.md", lambda t: t.replace("- **Estimate:** 1h\n- **Done when:** `pytest tests/test_export.py` passes", "- **Done when:** `pytest tests/test_export.py` passes"))
    check(not by_code(findings(d6), "DEF-STORY-ESTIMATE", "STORY-006"), "no `Estimate` field and no delivery planning declared: no finding")
    check(bool(by_code(findings(d6), "DEF-STORY-ESTIMATE", "STORY-003")), "`Estimate: ?` is a finding")
    os.makedirs(os.path.join(d6, ".gtt"), exist_ok=True)
    with open(os.path.join(d6, ".gtt", "delivery.json"), "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"schema": 1}))
    check(bool(by_code(findings(d6), "DEF-STORY-ESTIMATE", "STORY-006")), "with delivery planning declared, a Story with no `Estimate` field is a finding")
    shutil.rmtree(os.path.dirname(d6), ignore_errors=True)

    print("criterion 7 - a deferred `Done when` comes from the contract's patterns")
    d7 = demo.build()
    for phrase in ("se definen al implementar", "TBD", "to be defined"):
        rewrite(d7, "gtt-domain/backlog.md", lambda t, p=phrase: re.sub(r"(##### STORY-004.*?\*\*Done when:\*\* ).*?\n", lambda m: m.group(1) + p + "\n", t, count=1, flags=re.S))
        hits = by_code(findings(d7), "DEF-STORY-DONE-WHEN", "STORY-004")
        check(bool(hits), f"`Done when: {phrase}` is a DEF-STORY-DONE-WHEN")
    shutil.rmtree(os.path.dirname(d7), ignore_errors=True)

    print("criterion 8 - a GAP that is OPEN or BLOCKING is the human's; RESOLVED or absent is the agent's")
    d8 = demo.build()
    check(by_code(findings(d8), "DEF-STORY-GAP", "STORY-005")[0]["owner"] == "human", "OPEN: the human's")
    rewrite(d8, "gtt-domain/context/stack.md", lambda t: t.replace("OPEN | GAP-004 | queue storage | scope: STORY-005 | affects: EPIC-001", "RESOLVED | GAP-004 | queue storage | was: OPEN | by: ADR-001"))
    stale = by_code(findings(d8), "DEF-STORY-GAP-STALE", "STORY-005")
    check(bool(stale) and stale[0]["owner"] == "agent" and not by_code(findings(d8), "DEF-STORY-GAP", "STORY-005"), "RESOLVED: the agent's")
    rewrite(d8, "gtt-domain/context/stack.md", lambda t: re.sub(r"RESOLVED \| GAP-004[^\n]*\n", "", t))
    absent = by_code(findings(d8), "DEF-STORY-GAP-STALE", "STORY-005")
    check(bool(absent) and absent[0]["owner"] == "agent", "absent from the register: the agent's")
    shutil.rmtree(os.path.dirname(d8), ignore_errors=True)

    print("criterion 5 - a Proposed Epic is not called Planned")
    d5 = demo.build()
    rewrite(d5, "gtt-domain/backlog.md", lambda t: t.replace("**Lane:** B\n**Estimate:** 4h\n", "**Lane:** B\n"))
    proc = sh(d5, "bash", ".gtt/scripts/gtt-delivery.sh", "check")
    text = proc.stdout + proc.stderr
    check("EPIC-002" not in text or "EPIC-002 is Planned" not in text, "the delivery messages never say `EPIC-002 is Planned`", text[-300:])
    shutil.rmtree(os.path.dirname(d5), ignore_errors=True)

    print("criterion 31 - parallel state: PREGUNTAS.md and TABLERO.md are signalled; the agent cannot create them")
    d31 = demo.build()
    with open(os.path.join(d31, "docs", "TABLERO.md"), "w", encoding="utf-8") as handle:
        handle.write("# Tablero\n")
    shadow = {f["ref"] for f in by_code(findings(d31), "GTT-SHADOW-STATE")}
    check({"docs/PREGUNTAS.md", "docs/TABLERO.md"} <= shadow, "both files raise GTT-SHADOW-STATE", str(shadow))
    with open(os.path.join(d31, ".gtt", "ade.json"), "w", encoding="utf-8") as handle:                 # the mark of an installed project
        handle.write(json.dumps({"schema": 1, "primary": "claude"}))
    sys.path.insert(0, os.path.join(d31, ".gtt", "scripts"))
    import gtt_protect
    reasons = [gtt_protect.protected_token(d31, name) for name in ("docs/PREGUNTAS.md", "TABLERO.md", "docs/QUESTIONS.md", "BACKLOG.md", "docs/TODO.md")]
    check(all(reasons), "the decision core denies the agent those names", str(reasons))
    check(gtt_protect.protected_token(d31, "gtt-domain/backlog.md") is None and gtt_protect.protected_token(d31, "docs/notes.md") is None, "and denies nothing else")
    names = json.load(open(os.path.join(ROOT, ".gtt", "contract", "findings.json")))["shadow"]["names"]
    check(set(n.lower() for n in names) == set(gtt_protect.SHADOW_NAMES), "the names in the decision core are the names of the contract")
    settings = json.load(open(os.path.join(ROOT, ".claude", "settings.json")))["permissions"]["deny"]
    check(all(f"Edit(/docs/{n})" in settings and f"Write(/{n})" in settings for n in names), "settings.json denies them too")
    sys.path.pop(0)
    sys.modules.pop("gtt_protect", None)
    shutil.rmtree(os.path.dirname(d31), ignore_errors=True)

    print("the full project: the 32 sources")
    full = demo.build(full=True)
    check(demo.missing_sources(full) == [], "criterion 1: the project has the 32 sources of the table", str(demo.missing_sources(full)))
    fdata = findings(full)
    sources = {f["source"] for f in fdata["findings"]}
    expected = {"gtt_backlog", "gtt_design", "gtt_provenance", "gtt_pending", "gtt_delivery", "gtt_observe", "gtt_run", "gtt_inbox", "gtt_health"}
    check(expected <= sources, "criterion 1: every script that owns a source emits findings", str(sorted(expected - sources)))
    check(not fdata["failed"], "no owner failed on the full project", str(fdata["failed"]))

    print("criterion 4 - the health panel is not empty: validate writes one file per check")
    folder = os.path.join(full, ".gtt", "local", "health")
    files = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    parsed = [json.load(open(os.path.join(folder, n))) for n in files]
    check(len(files) >= 8 and all({"title", "status", "detail", "at"} <= set(p) and p["status"] in ("ok", "warn", "fail") for p in parsed), "one valid file per check", str(files[:5]))
    sys.path.insert(0, os.path.join(full, ".gtt", "scripts"))
    cwd = os.getcwd()
    os.chdir(full)
    import gtt_sonar
    shown = gtt_sonar.health_checks()
    os.chdir(cwd)
    sys.path.pop(0)
    check(bool(shown) and len(shown) == len(files), "Sonar reads them all", str(shown)[:120])

    print("criterion 35 - the inbox: an ADR draft says what it lacks; ideas, levels and packages are the agent's and count")
    draft = by_code(fdata, "DEF-INBOX-ADR-DRAFT")[0]
    check("context" in draft["text"] and "decision" in draft["text"] and "consequences" in draft["text"], "an ADR draft says which sections it lacks", draft["text"])
    for code in ("DEF-INBOX-UNTRIAGED", "DEF-INBOX-LEVEL", "DEF-INBOX-NO-PACKAGE", "DEF-INBOX-PACKAGE-STALE"):
        hits = by_code(fdata, code)
        check(bool(hits) and hits[0]["owner"] == "agent", f"{code} is the agent's")
    check(fdata["counts"].get("inbox", 0) >= 5, "and they count", str(fdata["counts"]))

    print("criterion 36 - in the Team profile each human finding says whom of the team it is for")
    meta = os.path.join(full, ".gtt", "methodology.json")
    cfg = json.load(open(meta))
    cfg["profile"] = "team"
    open(meta, "w").write(json.dumps(cfg))
    team = findings(full)
    gap = by_code(team, "GOV-GAP")[0]
    intent = by_code(team, "DEF-EPIC-INTENT")[0]
    check(gap["for"] == "Luis" and intent["for"] == "Ana", "a gap is for the architect, an Epic for the scope role", f"{gap['for']} {intent['for']}")
    check(all(f["for"] is None for f in team["findings"] if f["owner"] == "agent"), "nothing of the agent's carries a person")
    check(all(f["for"] is None for f in fdata["findings"]), "outside Team nobody is named")

    print("criterion 33 - findings and readiness in less than 1.5 s with 200 Stories")
    big = demo.build()
    stories = "".join(f"##### STORY-{100 + i} — Work {i}\n- **Status:** Planned\n- **Implements:** EPIC-001#R-1\n- **Estimate:** 1h\n- **Done when:** `pytest tests/t{i}.py` passes\n\n" for i in range(200))
    rewrite(big, "gtt-domain/backlog.md", lambda t: t.replace("### EPIC-002", stories + "### EPIC-002", 1))
    started = time.time()
    bigdata = findings(big)
    took = time.time() - started
    check(bigdata["counts"].get("ready", 0) >= 150 and took < 1.5, f"{len(bigdata['readiness'])} items in {took:.2f}s", str(bigdata["counts"]))

    prompt2()
    for d in (dest, full, big):
        shutil.rmtree(os.path.dirname(d), ignore_errors=True)
    print()
    print(f"{COUNT - len(FAILS)}/{COUNT} checks held")
    if FAILS:
        print("FAILED: " + "; ".join(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
