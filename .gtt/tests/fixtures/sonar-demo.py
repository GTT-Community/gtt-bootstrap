#!/usr/bin/env python3
"""Fixture: a frozen GTT project with 8 problems planted on purpose (section 1 of GTT-ORDEN-sonar-herramienta).

  python3 .gtt/tests/fixtures/sonar-demo.py [DEST] [--snapshot] [--render]

Copies this Bootstrap into DEST (a new temp folder when omitted), writes a backlog, an Epic design, a gap register,
an incomplete ADR draft and a parallel-state file, marks it frozen and commits it. Prints DEST and the planted problems.
--snapshot prints which of them `gtt-sonar.sh snapshot` carries today; --render writes .gtt/local/sonar.html.
Nothing here touches the Bootstrap it copies. The tests import `build()`."""
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
    {"n": 7, "code": "DEF-INBOX-ADR-DRAFT", "ref": "gtt-domain/adr/drafts/ADR-draft-cache.md", "what": "an ADR draft with `<...>` and empty sections"},
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
- **Implements:** EPIC-001#F-1
- **Estimate:** 2h
- **Done when:** `pytest tests/test_schema.py` passes
- **Closed:** 2026-11-02 — abc1234 — tests passed

##### STORY-002 — Endpoint
- **Status:** In Progress
- **Implements:** EPIC-001#F-2
- **Estimate:** 2h
- **Done when:** `pytest tests/test_endpoint.py` passes

##### STORY-003 — Validation rules
- **Status:** Planned
- **Implements:** EPIC-001#R-1
- **Estimate:** ?
- **Done when:** `pytest tests/test_rules.py` passes

##### STORY-004 — Audit trail
- **Status:** Planned
- **Implements:** EPIC-001#R-2
- **Estimate:** 2h
- **Done when:** se definen al implementar

##### STORY-005 — Offline queue
- **Status:** Planned
- **Implements:** EPIC-001#F-3
- **Estimate:** 2h
- **Done when:** `pytest tests/test_queue.py` passes
- **Blocked by:** GAP-004

##### STORY-006 — Export
- **Status:** Planned
- **Estimate:** 1h
- **Done when:** `pytest tests/test_export.py` passes

##### STORY-007 — Notifications
- **Status:** Blocked
- **Implements:** EPIC-001#F-4
- **Estimate:** 1h
- **Done when:** `pytest tests/test_notify.py` passes

### EPIC-002 — Sync offline
**Status:** Proposed
**Lane:** B
**Estimate:** 4h

#### Stories

##### STORY-008 — Conflict rules
- **Status:** Planned
- **Implements:** EPIC-002#F-1
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

## Requirements
- R-1: a parcel has a valid area.
- R-2: every change leaves an audit line.

## Flows
- F-1: schema is created.
- F-2: the endpoint stores a parcel.
- F-3: the queue holds writes while offline.
- F-4: a notification goes out when a parcel changes.

## Interfaces
- I-1: POST /parcels.

## Examples
- E-1: a parcel of 2.5 ha is accepted.
"""

DRAFT = """# ADR-draft — Cache layer

- Status: <Proposed>
- Date: <YYYY-MM-DD>

## Context

## Decision

## Consequences
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


def build(dest=None):
    """Returns the folder of the demo project (a copy of this Bootstrap with the problems planted)."""
    dest = dest or os.path.join(tempfile.mkdtemp(prefix="gtt-sonar-demo-"), "proj")
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "local", "dev-notes"))
    write(dest, "gtt-domain/backlog.md", BACKLOG)
    write(dest, "gtt-domain/context/design/EPIC-001.md", DESIGN)
    write(dest, "gtt-domain/adr/drafts/ADR-draft-cache.md", DRAFT)
    write(dest, "docs/PREGUNTAS.md", QUESTIONS)
    stack = os.path.join(dest, "gtt-domain", "context", "stack.md")
    text = open(stack, encoding="utf-8").read()
    open(stack, "w", encoding="utf-8").write(text.replace("```gtt-gaps\n```", "```gtt-gaps\n" + GAPS + "```", 1))
    write(dest, "gtt-domain/.frozen", "2026-11-05T12:00:00Z demo fixture\n")
    git = lambda *a: sh(dest, "git", "-c", "user.name=demo", "-c", "user.email=demo@example.com", *a)
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-q", "-m", "demo")
    return dest


def snapshot(dest):
    proc = sh(dest, "bash", ".gtt/scripts/gtt-sonar.sh", "snapshot", "--json")
    return json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None


def main(argv):
    flags = [a for a in argv if a.startswith("--")]
    rest = [a for a in argv if not a.startswith("--")]
    dest = build(os.path.abspath(rest[0]) if rest else None)
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
