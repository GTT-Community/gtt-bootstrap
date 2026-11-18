#!/usr/bin/env python3
"""Fixture: a frozen GTT project with 8 problems planted on purpose (section 1 of GTT-ORDEN-sonar-herramienta).

  python3 .gtt/tests/fixtures/sonar-demo.py [DEST] [--full] [--snapshot] [--render]

Copies this Bootstrap into DEST (a new temp folder when omitted), writes a backlog, an Epic design, a gap register,
an incomplete ADR draft and a parallel-state file, marks it frozen and commits it. Prints DEST and the planted problems.
--full also plants every one of the 32 sources of the audit (SOURCES_32). --snapshot prints which of them `gtt-sonar.sh snapshot` carries today; --render writes .gtt/local/sonar.html.
Nothing here touches the Bootstrap it copies. The tests import `build()`."""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

# What is planted, where, and the finding the order says it must raise (4.3 / 4.4 / 11).
PLANTED = [
    {"n": 1, "code": "DEF-STORY-ESTIMATE", "ref": "STORY-003", "what": "`Estimate: ?`"},
    {"n": 2, "code": "DEF-STORY-DONE-WHEN", "ref": "STORY-004", "what": "`Done when:` deferred: \"se definen al implementar\""},
    {"n": 3, "code": "DEF-STORY-GAP", "ref": "STORY-005", "what": "cites GAP-004, which is OPEN"},
    {"n": 4, "code": "DEF-STORY-IMPLEMENTS", "ref": "STORY-006", "what": "no `Implements:`"},
    {"n": 5, "code": "DEF-STORY-BLOCKED-NOCAUSE", "ref": "STORY-007", "what": "`Blocked` with no ASK and no `Blocked by:`"},
    {"n": 6, "code": "DEF-EPIC-INTENT", "ref": "EPIC-002", "what": "a `Proposed` Epic with no Goal, Scope or Out of Scope"},
    {"n": 7, "code": "DEF-INBOX-ADR-DRAFT", "ref": "gtt-domain/adr/drafts/IDEA-001-cache-layer.md", "what": "an ADR draft with `<...>` and empty sections"},
    {"n": 8, "code": "GTT-SHADOW-STATE", "ref": "docs/PREGUNTAS.md", "what": "a questions file outside gtt-domain/ with refs and state words"},
]

BACKLOG = """# Project Backlog

**Last verified:** `2026-11-10`

## Development Line

Demo line.

## Epics

### EPIC-001 — Base platform
**Status:** In Progress
**Goal:** the platform runs and stores parcels
**Scope:** schema, endpoint, sync queue
**Out of Scope:** reports
**Design:** `gtt-domain/context/design/EPIC-001.md`
**Lane:** A
**Estimate:** 8h
**Touches:** src/parcelas
**Approved:** human — 2026-11-01

#### Stories

##### STORY-001 — Schema
- **Status:** Done
- **Implements:** design/EPIC-001#F-1
- **Estimate:** 2h
- **Done when:** `pytest tests/test_schema.py` passes
- **Closed:** 2026-11-02 — abc1234 — tests passed

##### STORY-002 — Endpoint
- **Status:** In Progress
- **Implements:** design/EPIC-001#F-2
- **Estimate:** 2h
- **Done when:** `pytest tests/test_endpoint.py` passes

##### STORY-003 — Validation rules
- **Status:** Planned
- **Implements:** design/EPIC-001#R-1
- **Estimate:** ?
- **Done when:** `pytest tests/test_rules.py` passes

##### STORY-004 — Audit trail
- **Status:** Planned
- **Implements:** design/EPIC-001#R-2
- **Estimate:** 2h
- **Done when:** se definen al implementar

##### STORY-005 — Offline queue
- **Status:** Planned
- **Implements:** design/EPIC-001#F-3
- **Estimate:** 2h
- **Done when:** `pytest tests/test_queue.py` passes
- **Blocked by:** GAP-004

##### STORY-006 — Export
- **Status:** Planned
- **Estimate:** 1h
- **Done when:** `pytest tests/test_export.py` passes

##### STORY-007 — Notifications
- **Status:** Blocked
- **Implements:** design/EPIC-001#F-4
- **Estimate:** 1h
- **Done when:** `pytest tests/test_notify.py` passes

##### STORY-009 — Payments
- **Status:** Blocked
- **Implements:** design/EPIC-001#F-2
- **Estimate:** 2h
- **Done when:** `pytest tests/test_payments.py` passes

### EPIC-002 — Sync offline
**Status:** Proposed
**Lane:** B
**Estimate:** 4h

#### Stories

##### STORY-008 — Conflict rules
- **Status:** Planned
- **Implements:** design/EPIC-002#F-1
- **Estimate:** 2h
- **Done when:** `pytest tests/test_conflicts.py` passes

## Current Focus

STORY-002.

## Next Work

STORY-003.

## Blocked

STORY-007.
"""

DESIGN = """# EPIC-001 — Base platform: design

**Status:** Draft

## 1. Purpose and scope

## 2. Data

## 3. Rules
- **R-1** A parcel has a valid area. [FUENTE: SRC-1]
- **R-2** Every change leaves an audit line. [FUENTE: SRC-1]

## 4. Flows
- **F-1** The schema is created. [FUENTE: SRC-1]
- **F-2** The endpoint stores a parcel. [FUENTE: SRC-1]
- **F-3** The queue holds writes while offline. [FUENTE: SRC-1]
- **F-4** A notification goes out when a parcel changes. [FUENTE: SRC-1]

## 5. Interfaces
- **I-1** POST /parcels. [FUENTE: SRC-1]

## 6. Examples
- **E-1** A parcel of 2.5 ha is accepted. R-1 F-2 [FUENTE: SRC-1]

## 7. Open points

## 8. Decisions taken with the human
"""

QUESTIONS = """# Preguntas

- STORY-003: ¿qué rango de área es válido? estado: abierta (EPIC-001)
- STORY-005: ¿cola local o servidor? estado: abierta
- ASK-9 sigue pendiente, estado: abierta
"""

GAPS = "OPEN | GAP-004 | queue storage | scope: STORY-005 | affects: EPIC-001\n"


def sh(cwd, *argv):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)


def write(dest, rel, text):
    path = os.path.join(dest, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def build(dest=None, full=False):
    """Returns the folder of the demo project (a copy of this Bootstrap with the problems planted)."""
    dest = dest or os.path.join(tempfile.mkdtemp(prefix="gtt-sonar-demo-"), "proj")
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "local", "dev-notes"))
    write(dest, "gtt-domain/backlog.md", BACKLOG)
    write(dest, "gtt-domain/context/design/EPIC-001.md", DESIGN)
    write(dest, "docs/PREGUNTAS.md", QUESTIONS)
    stack = os.path.join(dest, "gtt-domain", "context", "stack.md")
    text = open(stack, encoding="utf-8").read()
    open(stack, "w", encoding="utf-8").write(text.replace("```gtt-gaps\n```", "```gtt-gaps\n" + GAPS + "```", 1))
    write(dest, "gtt-domain/.frozen", "2026-11-05T12:00:00Z demo fixture\n")
    plant_more(dest)
    made = sh(dest, "bash", ".gtt/scripts/gtt-inbox.sh", "adr-new", "Cache layer", "--by", "Ana", "--apply")   # the architect's draft, as the engine writes it
    assert made.returncode == 0, made.stderr or made.stdout
    git = lambda *a: sh(dest, "git", "-c", "user.name=demo", "-c", "user.email=demo@example.com", *a)
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-q", "-m", "demo")
    if full:
        plant_full(dest)
    return dest


def pending(dest, *argv):
    return sh(dest, "bash", ".gtt/scripts/gtt-pending.sh", *argv)


def plant_more(dest):
    """What the order asks the fixture to carry besides the eight problems: an ASK that blocks a Story, an open DEC, an answered event nobody
    applied, a run plan ready for the human, a source that changed after it was registered and an observation in the governance backlog."""
    out = {}
    out["ask"] = pending(dest, "ask", "--type", "product", "--question", "Does the owner approve payments by card?", "--why", "it changes the scope",
                         "--option", "Yes | I build card payments", "--option", "No | I leave them out", "--recommended", "2", "--blocks", "STORY-009",
                         "--header", "Payments", "--apply")
    out["dec"] = pending(dest, "decide", "--affects", "design", "--title", "Queue uses a local file", "--what", "the offline queue is a file",
                         "--why", "no server is needed", "--where", "STORY-005", "--apply")
    pending(dest, "ask", "--type", "product", "--question", "Which date format?", "--why", "reports", "--option", "ISO | 2026-11-01", "--option", "Local | 01/11/2026",
            "--recommended", "1", "--blocks", "STORY-004", "--header", "Dates", "--apply")
    out["answer"] = pending(dest, "answer", "3", "1", "--confirmed-by-human", "--by", "Ana")
    write(dest, "gtt-domain/run/RUN-001-env.md",
          "# RUN-001\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md\n\n"
          "- **What it does:** Prepares the local environment\n- **Why:** STORY-002\n- **Changes:** environment\n\n```gtt-run\n"
          "check: bash --version\nstep: Say hi | echo hi\nnext: Open it\n```\n")
    out["run"] = sh(dest, "bash", ".gtt/scripts/gtt-run.sh", "generate", "RUN-001", "--apply")
    write(dest, "docs/sources/brief.md", "# Brief\n\nversion one\n")
    out["source"] = sh(dest, "bash", ".gtt/scripts/gtt-source.sh", "add", "docs/sources/brief.md", "--id", "SRC-1", "--apply")
    with open(os.path.join(dest, "docs", "sources", "SRC-1", "v1", "brief.md"), "a", encoding="utf-8") as handle:   # the registered copy is immutable
        handle.write("edited after it was registered\n")
    write(dest, "gtt-domain/governance-backlog.json", json.dumps({"schema": 1, "notice": "demo", "next": 2, "items": [
        {"id": "OBS-0001", "fingerprint": "demo0001", "rule": "GTT-MODULES", "kind": "modules", "level": "GOVERNANCE", "artifact": "src/orphan/",
         "guards": "stack.md 5", "detail": "code outside every declared module: src/orphan/a.py", "state": "present", "status": "open", "first_seen": "2026-11-10"}]},
        indent=2, sort_keys=True) + "\n")
    return out


# The 32 sources of the audit (table 1.1 of GTT-ORDEN-sonar-herramienta.md) and where the full project keeps each one.
SOURCES_32 = [
    (1, "backlog.md: Epics", "gtt-domain/backlog.md"), (2, "backlog.md: Stories", "gtt-domain/backlog.md"),
    (3, "Current Focus, Next Work, Blocked", "gtt-domain/backlog.md"), (4, "design of an Epic", "gtt-domain/context/design/EPIC-001.md"),
    (5, "the six context files", "gtt-domain/context/stack.md"), (6, "stack.md 5. Dependency rules", "gtt-domain/context/stack.md"),
    (7, "stack.md 6. Map change log", "gtt-domain/context/stack.md"), (8, "stack.md 7. Boundaries", "gtt-domain/context/stack.md"),
    (9, "stack.md 8. Gap register", "gtt-domain/context/stack.md"), (10, "sources", "docs/sources/SRC-1/v1/brief.md"),
    (11, "ADR", "gtt-domain/adr/ADR-001-context-governance.md"), (12, "ADR drafts", "gtt-domain/adr/drafts"),
    (13, ".frozen", "gtt-domain/.frozen"), (14, "pending: ASK", "gtt-domain/pending/ASK-001.md"), (15, "pending: REV", "gtt-domain/pending"),
    (16, "pending: DEC", "gtt-domain/pending/DEC-002.md"), (17, "pending: answered, not applied", "gtt-domain/pending/ASK-003.md"),
    (18, "proposals", "gtt-domain/proposals"), (19, "run/RUN-n", "gtt-domain/run/RUN-001-env.md"), (20, "delivery-log.jsonl", "gtt-domain/delivery-log.jsonl"),
    (21, "governance-backlog.json", "gtt-domain/governance-backlog.json"), (22, "last-validation.json and health/", ".gtt/local/health"),
    (23, "methodology.json", ".gtt/methodology.json"), (24, "ade.json", ".gtt/ade.json"), (25, "docs/ideas/", "docs/ideas"),
    (26, "parallel state in docs/", "docs/PREGUNTAS.md"), (27, "the code", "src/parcelas/app.py"), (28, "git", ".git"),
    (29, "workflow.md", "gtt-domain/workflow.md"), (30, "working-agreements.md", "gtt-domain/working-agreements.md"),
    (31, "session.md", "gtt-domain/session.md"), (32, "run/log.jsonl", "gtt-domain/run/log.jsonl"),
]


def plant_full(dest):
    """--full: a project that has every one of the 32 sources, so a test can walk the table. Adds what plant_more does not: the modules and the code,
    the boundaries, the ADE and method records, the working agreements, an idea nobody triaged, proposals that lack their level or their package,
    a review, the run log, and one run of `gtt-validate.sh` (its health files and last-validation.json)."""
    day = lambda n: (datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=n)).isoformat()
    head = lambda ref, title, header, body, trail: (f"# {ref} · {title}\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md\n\n"
                                                   f"{header}\n\n{body}\n" + ("\n---\n" + "\n".join(trail) + "\n" if trail else ""))
    stack = os.path.join(dest, "gtt-domain", "context", "stack.md")
    text = open(stack, encoding="utf-8").read()
    rules = ("| Module | May depend on | Must not depend on |\n|---|---|---|\n| src/parcelas/ | src/core/ | src/sync/ |\n| src/sync/ | src/core/ | - |\n| src/core/ | - | - |\n")
    text = text.replace("## 5. Dependency rules\n", "## 5. Dependency rules\n\n" + rules, 1) if "| src/parcelas/ |" not in text else text
    open(stack, "w", encoding="utf-8").write(text)
    write(dest, "src/parcelas/app.py", "from src.core import base\n\n\ndef run():\n    return base\n")
    write(dest, "src/core/base.py", "base = 1\n")
    write(dest, "src/sync/queue.py", "from src.core import base\n")
    write(dest, ".gtt/methodology.json", json.dumps({"schema": 1, "language": "en", "profile": "light", "set_at": "2026-11-01T10:00:00Z"}) + "\n")
    write(dest, ".gtt/ade.json", json.dumps({"schema": 1, "primary": "claude", "participating": ["claude"], "excluded": [], "installed": {}}, indent=2) + "\n")
    write(dest, "gtt-domain/working-agreements.md", "# Working agreements\n\n```gtt-roles\ndefault: Ana\narchitecture: Luis\nspecification: Ana\nscope: Ana\n```\n")
    write(dest, "gtt-domain/run/log.jsonl", json.dumps({"t": "2026-11-12T10:00:00Z", "run": "RUN-000", "ok": True}) + "\n")
    write(dest, "docs/ideas/IDEA-002-reports.md", head("IDEA-002", "Weekly reports", f"Author: human (Ana) · Created: {day(4)} · Type: idea", "A weekly report of the parcels.", []))
    write(dest, "gtt-domain/proposals/PROP-001-level.md", head("PROP-001", "Billing split", f"Author: agent (claude) · Created: {day(3)} · Level: por confirmar · Route: spec · Origin: IDEA-002", "Body", []))
    write(dest, "gtt-domain/proposals/PROP-002-nopkg.md", head("PROP-002", "Cache the catalog", f"Author: agent (claude) · Created: {day(5)} · Level: scope · Route: scope · Origin: IDEA-002", "Body",
                                                              [f"Decision: accepted, priority normal · {day(4)} · human"]))
    write(dest, "gtt-domain/proposals/PROP-003-stale.md", head("PROP-003", "Audit trail", f"Author: agent (claude) · Created: {day(6)} · Level: scope · Route: scope · Origin: IDEA-002", "Body",
                                                              [f"Decision: accepted, priority normal · {day(5)} · human", f"Package: stale · {day(1)} · gtt"]))
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = lambda minutes: (now - datetime.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(dest, "gtt-domain", "delivery-log.jsonl"), "a", encoding="utf-8") as handle:     # STORY-001 closed yesterday, STORY-002 started two hours ago
        handle.write(json.dumps({"t": stamp(1700), "kind": "story", "id": "STORY-001", "from": "Planned", "to": "In Progress", "actor": "agent"}) + "\n")
        handle.write(json.dumps({"t": stamp(1560), "kind": "story", "id": "STORY-001", "from": "In Progress", "to": "Done", "actor": "agent"}) + "\n")
        handle.write(json.dumps({"t": stamp(125), "kind": "story", "id": "STORY-002", "from": "Planned", "to": "In Progress", "actor": "agent"}) + "\n")
    tools = [("Edit", "src/parcelas/app.py"), ("Edit", "src/parcelas/forms.py"), ("pytest", None), ("Edit", "tests/test_edicion.py"), ("Edit", "src/parcelas/app.py")]
    journal = [{"t": stamp(120 - 9 * i), "actor": "agent", "ade": "claude", "source": "hook", "tool": tools[i % 5][0], "path": tools[i % 5][1], "stories": ["STORY-002"]} for i in range(13)]
    journal.append({"t": stamp(40), "actor": "human", "via": "sonar", "op": "pending.answer", "ref": "ASK-003"})
    journal.append({"t": stamp(2), "actor": None, "ade": None, "source": "sample", "tool": None, "path": "src/parcelas/edit.py", "stories": ["STORY-002"]})
    os.makedirs(os.path.join(dest, ".gtt", "local"), exist_ok=True)
    with open(os.path.join(dest, ".gtt", "local", "activity.jsonl"), "w", encoding="utf-8") as handle:
        handle.write("".join(json.dumps(r, sort_keys=True) + "\n" for r in sorted(journal, key=lambda r: r["t"])))
    code = ("import sys; sys.path.insert(0, '.gtt/scripts'); import gtt_pending as p; c = p.contract()\n"
            "p.open_rev(c, {'ref': 'PROP-001', 'title': 'Billing split', 'level': 'spec', 'sha': '3f9a' * 16, 'origin': 'IDEA-002', 'for': 'Ana'}, True)\n")
    sh(dest, sys.executable, "-c", code)
    sh(dest, "bash", ".gtt/scripts/gtt-validate.sh")
    subprocess.run(["git", "-c", "user.name=demo", "-c", "user.email=demo@example.com", "add", "-A"], cwd=dest, capture_output=True)
    subprocess.run(["git", "-c", "user.name=demo", "-c", "user.email=demo@example.com", "commit", "-q", "-m", "full"], cwd=dest, capture_output=True)


def missing_sources(dest):
    """The sources of SOURCES_32 this project does not have (a folder counts when it is not empty)."""
    out = []
    for n, name, path in SOURCES_32:
        full_path = os.path.join(dest, path)
        if not (os.path.isfile(full_path) or (os.path.isdir(full_path) and os.listdir(full_path))):
            out.append((n, name, path))
    return out


def snapshot(dest):
    proc = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json")
    return json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None


def main(argv):
    flags = [a for a in argv if a.startswith("--")]
    rest = [a for a in argv if not a.startswith("--")]
    dest = build(os.path.abspath(rest[0]) if rest else None, full="--full" in flags)
    print(dest)
    for p in PLANTED:
        print(f"  {p['n']}. {p['code']:<28} {p['ref']:<42} {p['what']}")
    if "--render" in flags:
        env = dict(os.environ, GTT_SONAR_NO_WATCH="1")
        proc = subprocess.run(["bash", ".gtt/scripts/gtt-sonar.sh", "render"], cwd=dest, capture_output=True, text=True, env=env, timeout=120)
        print("render:", "ok" if proc.returncode == 0 else proc.stderr[-300:], os.path.join(dest, ".gtt/local/sonar.html"))
    if "--snapshot" in flags:
        snap = snapshot(dest)
        snap = snap or {}
        flagged = json.dumps([snap.get(k) for k in ("signals", "needs_you", "quality", "inbox", "health")] + [[s.get("flags") for s in snap.get("stories") or [] if s.get("flags")]])
        print("what Sonar flags today (the ref appears in signals, needs_you, quality, inbox, health or a Story's flags):")
        for p in PLANTED:
            print(f"  {p['n']}. {p['ref']}: {'flagged' if p['ref'] in flagged else 'not flagged'}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
