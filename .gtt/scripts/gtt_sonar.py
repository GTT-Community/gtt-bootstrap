#!/usr/bin/env python3
"""GTT Sonar - the snapshot: one JSON, calculated by the scripts that own each fact.

  gtt_sonar.py snapshot [--json] [--docs]   the `sonar.v1` document (read-only; writes nothing); --docs adds the
                                    governed documents, already turned into safe blocks (the project page has them)
  gtt_sonar.py render [--quiet]     writes .gtt/local/sonar.html and sonar.json (derived, disposable, outside git)
  gtt_sonar.py render --out HTML [--fonts DIR] FILE...   a page from several snapshots (the portfolio)
  gtt_sonar.py start                renders, then prints ONE line saying where the page is and what waits for the human
                                    (the session start uses it); opens the page once if the human asked for it
  gtt_sonar.py watch [--hours N]    keeps the page fresh: re-renders when the backlog, the pending events, the health
                                    files or git change (and every minute), then exits by itself; one per project
  gtt_sonar.py prefs [--open-on-start on|off] [--watch on|off]   the human's own preferences, kept in .gtt/local/ (never versioned)

This file gathers; it does not calculate. Percentages, forecasts, signals, weights and commands come from
gtt_delivery.py, gtt_pending.py, gtt_backlog.py and gtt_change.py. A fact GTT does not yet calculate is `null`:
the page says "no data" and never estimates it.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCHEMA = "sonar.v1"
RELEASE = ".gtt/contract/release.json"
FROZEN = "gtt-domain/.frozen"
RECENT = 40
TEMPLATE = ".gtt/sonar/template.html"
FONTS = ".gtt/sonar/fonts"
LOCAL = ".gtt/local"
LOCK = ".gtt/local/sonar.lock"
LOCK_SECONDS = 10
DOC_SOURCE_LIMIT = int(os.environ.get("GTT_SONAR_DOC_SOURCE_LIMIT") or 60000)    # bytes of one document
DOCS_TOTAL_LIMIT = int(os.environ.get("GTT_SONAR_DOCS_TOTAL_LIMIT") or 900000)  # bytes of JSON for all of them
PREFS = ".gtt/local/sonar-prefs.json"
OPENED = ".gtt/local/sonar-opened"
OPEN_EVERY_HOURS = 12
COLUMNS = ["Planned", "In Progress", "Done"]
HEALTH_DIR = ".gtt/local/health"
WATCH_PID = ".gtt/local/sonar-watch.pid"
WATCH_EVERY = 2            # seconds between looks at the inputs
WATCH_BEAT = 60            # seconds: a render at least this often, so the page never looks abandoned
WATCH_HOURS = 8
STALE_AFTER_H = 48         # a health file older than this is reported as stale
THROUGHPUT_DAYS = 14
SCOPE_OUT = re.compile(r"(^|[\s(])(post-|fuera del alcance|out of scope|deferred|diferid)", re.I)
NO_REASON = re.compile(r"^\s*([-—–]|none\b|ninguno|n/?a\b)", re.I)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def safe(fn, default=None):
    """A section that cannot be read is `null`, never a failure: the page shows the rest."""
    try:
        return fn()
    except (Exception, SystemExit):
        return default


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_root():
    """One state per repo, not per worktree: the main checkout holds the shared state (git common directory)."""
    try:
        out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True, timeout=10)
        common = out.stdout.strip()
        if out.returncode == 0 and common.endswith("/.git"):
            return common[:-5]
    except (OSError, subprocess.SubprocessError):
        pass
    return os.getcwd()


def project_key(name):
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name) if w]
    if len(words) > 1:
        return "".join(w[0] for w in words).upper()[:4]
    return (words[0] if words else "GTT")[:3].upper()


def day(stamp):
    return stamp[:10] if isinstance(stamp, str) and len(stamp) >= 10 else None


def actor_kind(raw):
    raw = (raw or "").lower()
    if raw.startswith("ade:") or raw in ("agent", "claude"):
        return "agent"
    if raw in ("human", "you"):
        return "human"
    if raw == "gtt":
        return "gtt"
    return None            # unknown: Sonar never guesses who did something


def repo_state(root):
    """Paths with uncommitted changes, or None outside git (no data, never a guess)."""
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return {"uncommitted": len([l for l in out.stdout.splitlines() if l.strip()])}


# ------------------------------------------------------------------------------- facts the backlog already carries
# A Story may say which release it belongs to, which front carries it and why it is blocked. GTT keeps every field of
# a Story; these read the ones a human manages by. Nothing is guessed: a missing field is `null`.

def plain(text):
    return re.sub(r"\s+", " ", str(text or "").replace("**", "").replace("`", "")).strip()


def release_of(fields):
    """(name, out_of_scope) from `Release:` / `Milestone:`. `v1 · Frente: A` is the release v1; `post-v1 (fuera del
    alcance...)` is the release post-v1 and is marked out of scope (a name or note that says post-, out of scope, deferred)."""
    raw = plain(fields.get("Release") or fields.get("Milestone") or "")
    if not raw:
        return None, False
    name = re.split(r"\s*[;,·|—–(]|\s+-\s+", raw, maxsplit=1)[0].strip()[:30]
    return (name or None), bool(SCOPE_OUT.search(raw))


def front_of(fields):
    """The front that carries a Story: `Frente:` / `Front:` / `Lane:` field, or the same word inside the Release line."""
    for key in ("Frente", "Front", "Lane"):
        value = plain(fields.get(key))
        if value:
            return re.split(r"[\s,;·(]", value, maxsplit=1)[0][:12] or None
    found = re.search(r"(?:Frente|Front|Lane):?\s*([A-Za-z0-9_-]{1,12})", plain(fields.get("Release")))
    return found.group(1) if found else None


def blocked_by(fields):
    """Why a Story waits, in the author's words (`Blocked by:`); None when empty or `—`."""
    for key, value in fields.items():
        if key.strip().lower() in ("blocked by", "blocked-by", "bloqueada por", "bloqueo"):
            return None if NO_REASON.match(value or "") else short(plain(value), 220)
    return None


def closed_day(text):
    found = re.match(r"\s*(\d{4}-\d{2}-\d{2})", str(text or ""))
    return found.group(1) if found else None


def throughput(stories, today):
    """Stories closed per day over the last THROUGHPUT_DAYS days, from the date each `Closed:` line starts with."""
    counts = {}
    for s in stories:
        if s["status"] == "Done":
            d = closed_day(s.get("closed"))
            if d:
                counts[d] = counts.get(d, 0) + 1
    days = []
    for back in range(THROUGHPUT_DAYS - 1, -1, -1):
        d = (today - datetime.timedelta(days=back)).isoformat()
        days.append({"day": d, "closed": counts.get(d, 0)})
    return {"days": days, "total": sum(x["closed"] for x in days)}


def health_checks():
    """Results the project's own checks leave in .gtt/local/health/<id>.json:
    {"title": "...", "status": "ok|warn|fail", "detail": "...", "at": "2026-11-13T10:00:00Z"}. Sonar only reads them;
    it never runs a command of the project. None when the folder does not exist (nobody reports health)."""
    import glob
    if not os.path.isdir(HEALTH_DIR):
        return None
    out = []
    for path in sorted(glob.glob(os.path.join(HEALTH_DIR, "*.json")))[:30]:
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        ident = os.path.basename(path)[:-5]
        status = str(data.get("status") or "").lower()
        at = data.get("at") if isinstance(data.get("at"), str) else None
        stale = False
        if at:
            try:
                then = datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                stale = (datetime.datetime.now(datetime.timezone.utc) - then).total_seconds() > STALE_AFTER_H * 3600
            except ValueError:
                pass
        out.append({"id": ident, "title": short(data.get("title"), 80) or ident, "status": status if status in ("ok", "warn", "fail") else "unknown",
                    "detail": short(data.get("detail"), 240), "at": at, "stale": stale})
    rank = {"fail": 0, "warn": 1, "unknown": 2, "ok": 3}
    out.sort(key=lambda c: (rank[c["status"]], c["id"]))
    return out


def degraded(version):
    """What this project's Bootstrap cannot give the page, and the act that fixes it. None when nothing is missing."""
    missing = []
    if not os.path.isfile(".gtt/contract/delivery.json"):
        missing.append("forecast")
    if not os.path.isfile(".gtt/contract/pending.json"):
        missing.append("pending")
    if not os.path.isfile(".gtt/scripts/gtt_sonar.py"):
        missing.append("refresh")
    here = read_json(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "contract", "release.json")) or {}
    tool = (here.get("bootstrap") or {}).get("version")
    if not missing:
        return None
    return {"project": version, "tool": tool, "missing": missing}


def watcher_alive():
    try:
        with open(WATCH_PID, encoding="utf-8") as handle:
            pid = int(handle.read().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, IndexError):
        return False


# ------------------------------------------------------------------------------------ documents as safe blocks
# The page never interprets markdown: this turns a document into plain blocks (text only, no markup, no links that
# lead anywhere) and the page paints them with textContent. Raw HTML in a document stays text.

INLINE = re.compile(r"(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)]*\))")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def inline(text):
    """[[kind, text]...]: kind t (text), b (bold) or c (code). A link keeps its label only."""
    out, pos = [], 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            out.append(["t", text[pos:m.start()]])
        token = m.group(0)
        if token.startswith("`"):
            out.append(["c", token[1:-1]])
        elif token.startswith("**"):
            out.append(["b", token[2:-2]])
        else:
            out.append(["t", re.match(r"\[([^\]]+)\]", token).group(1)])
        pos = m.end()
    if pos < len(text):
        out.append(["t", text[pos:]])
    return out or [["t", ""]]


def cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)]


def markdown_blocks(text):
    """Blocks: ["h", level, inl] ["p", inl] ["list", ordered, [[depth, inl]...]] ["code", text] ["quote", inl]
    ["table", [inl...], [[inl...]...]] ["hr"]."""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
        elif stripped.startswith("<!--"):
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
        elif stripped.startswith("```") or stripped.startswith("~~~"):
            fence, body = stripped[:3], []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                body.append(lines[i])
                i += 1
            i += 1
            blocks.append(["code", "\n".join(body)])
        elif re.match(r"^#{1,6}\s+", stripped):
            level = len(stripped) - len(stripped.lstrip("#"))
            blocks.append(["h", level, inline(stripped[level:].strip().rstrip("#").strip())])
            i += 1
        elif re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            blocks.append(["hr"])
            i += 1
        elif stripped.startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
            head = [inline(c) for c in cells(stripped)]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([inline(c) for c in cells(lines[i])])
                i += 1
            blocks.append(["table", head, rows])
        elif stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append(["quote", inline(" ".join(q for q in quote if q))])
        elif LIST_ITEM.match(line):
            items, ordered = [], bool(re.match(r"\d", LIST_ITEM.match(line).group(2)))
            while i < len(lines) and (LIST_ITEM.match(lines[i]) or (lines[i].startswith("  ") and lines[i].strip() and items)):
                found = LIST_ITEM.match(lines[i])
                if found:
                    items.append([min(len(found.group(1).replace("\t", "  ")) // 2, 4), inline(found.group(3))])
                else:                                   # a continuation line belongs to the item above
                    items[-1][1].append(["t", " " + lines[i].strip()])
                i += 1
            blocks.append(["list", ordered, items])
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6}\s|```|~~~|>|\||---|\*\*\*)", lines[i].strip()) and not LIST_ITEM.match(lines[i]):
                para.append(lines[i].strip())
                i += 1
            if not para:                                # a line no rule claims: never loop on it
                para.append(lines[i].strip())
                i += 1
            blocks.append(["p", inline(" ".join(para))])
    return blocks


def short(value, limit):
    """One line, cut at `limit`; None when empty (no data, never an empty guess)."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return None
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def first_heading(text, fallback):
    for line in text.splitlines():
        found = re.match(r"^#\s+(.*)$", line.strip())
        if found:
            return found.group(1).strip()[:120]
    return fallback


def collect_docs():
    """The governed documents of the project as blocks, within a size budget: context, then ADRs, then Epic designs.
    One that does not fit is listed with `omitted` and its path, never silently dropped."""
    import glob
    order = ["solution-vision", "architecture", "stack", "constraints", "principles", "glossary"]
    context = sorted(glob.glob("gtt-domain/context/*.md"), key=lambda p: (order.index(os.path.basename(p)[:-3]) if os.path.basename(p)[:-3] in order else 99, p))
    adrs = [p for p in sorted(glob.glob("gtt-domain/adr/ADR-*.md")) if "TEMPLATE" not in p]
    designs = sorted(glob.glob("gtt-domain/context/design/EPIC-*.md"))
    items, used = [], 0
    for group, paths in (("context", context), ("adr", adrs), ("design", designs)):
        for path in paths:
            path = path.replace("\\", "/")
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            size = len(text.encode("utf-8"))
            truncated = size > DOC_SOURCE_LIMIT
            if truncated:
                text = text[:DOC_SOURCE_LIMIT].rsplit("\n", 1)[0]
            blocks = markdown_blocks(text)
            weight = len(json.dumps(blocks, ensure_ascii=False))
            item = {"id": path, "group": group, "path": path, "title": first_heading(text, os.path.basename(path)), "bytes": size,
                    "truncated": truncated, "omitted": False, "blocks": blocks}
            if used + weight > DOCS_TOTAL_LIMIT:
                item.update({"omitted": True, "blocks": None, "truncated": False})
            else:
                used += weight
            items.append(item)
    return {"items": items, "limit_bytes": DOCS_TOTAL_LIMIT}


# ------------------------------------------------------------------------------------------- the inbox (the Bandeja)
# Every fact comes from gtt_inbox.py (the entries and their trail), gtt_pending.py (the REV) and the registries (ADR,
# the map change log). The page only paints what is here; what is not known is `null`.

CLOSED_DAYS = 7            # a closed entry stays in the Bandeja this many days
REJECTED_DAYS = 30
INBOX_LIMIT = 200
TEXT_LIMIT = 4000
KIND_RANK = {"review": 1, "ratify": 2, "adr-hand": 3}      # at equal weight, what holds work back comes first
PRIORITIES = ("urgent", "normal", "low")


def origin_of(value):
    """The entry an Epic came from (`Origin:`), its first word; None when empty or `—`."""
    text = plain(value)
    return None if not text or NO_REASON.match(text) else short(text.split(" ")[0], 40)


def priority_of(value):
    """urgent | normal | low as written in the Epic; anything else is shown as the author wrote it; None when empty."""
    text = plain(value).lower()
    return (text if text in PRIORITIES else short(text, 20)) if text else None


def git_user():
    try:
        out = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def ratify_command(e, engine):
    """The act that ratifies a ready package: its staged set (`gtt promote`), else its run (`gtt run n`), else the Epic
    to approve (`gtt approve EPIC-n`). None when the `Package` line names nothing the human can run."""
    names = engine.set_names(e)
    if names:
        return f"gtt promote {names[0]}"
    value = " ".join(l["value"] for l in e["trail"] if l["key"] == "package")
    run = re.search(r"\bRUN-0*(\d+)", value)
    if run:
        return f"gtt run {int(run.group(1))}"
    epic = re.search(r"gtt approve (EPIC-\d+)", value) or re.search(r"\b(EPIC-\d+)\b", value)
    return f"gtt approve {epic.group(1)}" if epic else None


def staged_sets():
    """Promotion sets that are ready and say where they come from (`origin` in promote.json): {name: (origin, reason)}."""
    import glob
    out = {}
    for path in sorted(glob.glob("gtt-domain/proposals/staged/*/promote.json")):
        spec = read_json(path)
        if isinstance(spec, dict) and isinstance(spec.get("origin"), str) and spec["origin"].strip():
            out[os.path.basename(os.path.dirname(path))] = (spec["origin"].strip(), short(spec.get("reason"), 120))
    return out


def adr_hand_items():
    """ADRs written by hand straight into adr/ that wait for `gtt adr adopt`: the reconcile module says which (it is
    written apart); without it, none. Accepts paths or {path, title}."""
    try:
        import gtt_inbox_reconcile as rec
    except (Exception, SystemExit):
        return []
    fn = getattr(rec, "adr_hand", None)
    if not callable(fn):
        return []
    try:
        found = fn()
    except TypeError:
        try:
            import gtt_inbox
            found = fn(gtt_inbox.contract())
        except (Exception, SystemExit):
            return []
    except (Exception, SystemExit):
        return []
    out = []
    for item in found or []:
        path = item if isinstance(item, str) else (item.get("path") or item.get("file")) if isinstance(item, dict) else None
        if not path:
            continue
        title = item.get("title") if isinstance(item, dict) else None
        if not title:
            try:
                with open(path, encoding="utf-8") as handle:
                    title = first_heading(handle.read(), os.path.basename(path))
            except OSError:
                title = os.path.basename(path)
        out.append({"path": path.replace("\\", "/"), "title": title})
    return out


def inbox_section(at, pend):
    """(inbox rows, counts, needs, me) from the engine. rows is None when this Bootstrap has no inbox (no data)."""
    import gtt_inbox
    c = gtt_inbox.contract()
    L = gtt_inbox.LB(c)
    ents = gtt_inbox.entries(c)
    by_ref = {e["ref"]: e for e in ents}
    revs = {r["entry"]: r for r in pend.get("reviews", []) if r.get("entry")}
    # An idea that became a proposal is that proposal: its card carries `de IDEA-n`, so the idea is not listed twice.
    converted = {e["origin"] for e in ents if e["kind"] == "PROP" and (e["origin"] or "").startswith("IDEA-")}
    rows, ratify_names = [], set()
    needs = []
    for e in ents:
        shown = e["ref"] not in converted
        command = None
        rev = revs.get(e["ref"])
        if e["stage"] == "review" and rev:
            command = at(f"gtt answer {rev['number']} {rev.get('recommended') or 1}")
        elif e["stage"] == "ratify":
            raw = ratify_command(e, gtt_inbox)
            command = at(raw) if raw else None
            if raw and raw.startswith("gtt promote "):
                ratify_names.add(raw.split()[-1])
            if raw and shown:
                needs.append({"ref": e["ref"], "kind": "ratify", "how": "ratify", "title": e["title"], "weight": {"stories": 0, "hours": None}, "unblocks": [],
                              "note": None, "for": None, "entry": e["ref"], "command": command})
        age = gtt_inbox.days_since(e["since"])
        if not shown:
            continue
        if e["stage"] == "closed" and (age is None or age > CLOSED_DAYS):
            continue
        if e["stage"] == "rejected" and age is not None and age > REJECTED_DAYS:
            continue
        rows.append({"ref": e["ref"], "type": e["type"], "origin": e["author_kind"],
                     "from": e["origin"] if (e["origin"] or "").startswith("IDEA-") else None,
                     "title": short(e["title"], 160) or e["ref"], "level": e["route"], "stage": e["stage"], "priority": e["priority"],
                     "days_in_stage": age, "event": e["rev"], "for": rev.get("for") if rev and e["stage"] == "review" else None,
                     "command": command, "path": e["path"],
                     "trail": [{"key": l["key"], "label": (L.get("trail") or {}).get(l["key"], l["key"]), "value": l["value"], "at": l["at"], "actor": l["actor"], "detail": l["detail"]} for l in e["trail"]],
                     "text": (e["body"] or "")[:TEXT_LIMIT]})
    order = {s: i for i, s in enumerate(c["stages"])}
    rank = {p: i for i, p in enumerate(PRIORITIES)}
    rows.sort(key=lambda r: (order.get(r["stage"], 99), rank.get(r["priority"], 1), r["days_in_stage"] if r["days_in_stage"] is not None else 0, r["ref"]))
    rows = rows[:INBOX_LIMIT]
    counts = {s: sum(1 for r in rows if r["stage"] == s) for s in c["stages"]}
    # One decision per open REV, with an act per option.
    for r in pend.get("reviews", []):
        options = r.get("options") or []
        choices = [{"label": o, "command": at(f"gtt answer {r['number']} {i}")} for i, o in enumerate(options, 1)]
        best = r.get("recommended") or 1
        needs.append({"ref": r["id"], "kind": "review", "how": "decide", "title": r["title"], "weight": {"stories": 0, "hours": None}, "unblocks": [],
                      "note": by_ref[r["entry"]]["route"] if r.get("entry") in by_ref else None, "for": r.get("for"), "entry": r.get("entry"),
                      "choices": choices, "command": at(f"gtt answer {r['number']} {best}")})
    # A ready package that names its origin but whose entry is not (yet) in `ratify` still waits for the human.
    for name, (origin, reason) in staged_sets().items():
        if name not in ratify_names:
            needs.append({"ref": name, "kind": "ratify", "how": "ratify", "title": reason or name, "weight": {"stories": 0, "hours": None}, "unblocks": [],
                          "note": origin, "for": None, "entry": origin if origin in by_ref else None, "command": at(f"gtt promote {name}")})
    import shlex
    for item in adr_hand_items():
        needs.append({"ref": os.path.basename(item["path"])[:-3] if item["path"].endswith(".md") else item["path"], "kind": "adr-hand", "how": "adopt", "title": item["title"],
                      "weight": {"stories": 0, "hours": None}, "unblocks": [], "note": None, "for": None, "entry": None,
                      "command": at("gtt adr adopt " + shlex.quote(item["path"]))})
    return rows, counts, needs, by_ref


def decisions_list(by_ref, limit=10):
    """The last ADRs and CHANGEs: ADR files plus the rows of the map change log, newest first, each with the entry
    that produced it when the registry says so."""
    import glob
    items, seen = [], {}
    for path in sorted(glob.glob("gtt-domain/adr/ADR-*.md")):
        base = os.path.basename(path)
        if "TEMPLATE" in base:
            continue
        found = re.match(r"(ADR-\d+)", base)
        text = read_text(path) or ""
        if not found:
            continue
        title = re.sub(r"^ADR-\d+\s*[-—–:·.]*\s*", "", first_heading(text, base)).strip() or found.group(1)
        date = re.search(r"^[-*]\s*Date:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
        origin = re.search(r"^[-*]\s*Origin:\s*([A-Za-z0-9-]+)", text, re.M)
        item = {"ref": found.group(1), "kind": "adr", "at": date.group(1) if date else None, "title": short(title, 160),
                "origin": origin.group(1) if origin else None}
        seen[item["ref"]] = item
        items.append(item)
    rows = safe(lambda: __import__("gtt_method").change_log_rows(), []) or []
    for cells in rows:
        if len(cells) < 3 or not (cells[1] or "").strip():
            continue
        ident = re.sub(r"[`*]", "", cells[1]).strip().split()[0]
        what = cells[2].strip()
        tail = re.search(r"\(((?:PROP|IDEA)-\d+)\)\s*$", what)
        origin = tail.group(1) if tail else None
        day_ = re.match(r"\d{4}-\d{2}-\d{2}", cells[0].strip())
        if ident in seen:
            if not seen[ident]["origin"] and origin:
                seen[ident]["origin"] = origin
            if not seen[ident]["at"] and day_:
                seen[ident]["at"] = day_.group(0)
            continue
        item = {"ref": ident, "kind": "adr" if ident.upper().startswith("ADR-") else "change", "at": day_.group(0) if day_ else None,
                "title": short(re.sub(r"\s*\((?:PROP|IDEA)-\d+\)\s*$", "", what), 160) or ident, "origin": origin}
        seen[ident] = item
        items.append(item)
    for item in items:
        item["entry"] = item["origin"] if item["origin"] in by_ref else None
    items.sort(key=lambda i: (i["at"] or "", i["ref"]), reverse=True)
    return items[:limit]


def build(root, docs=False):
    import gtt_backlog
    import gtt_delivery as dl
    import gtt_pending
    import gtt_change

    release = read_json(RELEASE) or {}
    lang = safe(gtt_pending.language, "en")
    name = os.path.basename(root.rstrip("/")) or "project"
    frozen = os.path.isfile(FROZEN)
    loaded = safe(dl.backlog)
    stories, epics = loaded if loaded else ([], [])
    times = safe(dl.timeline, {}) or {}
    # The delivery view folds `Proposed` into `Planned`; the Epic still waiting for approval is the raw status.
    raw_epics = {e["id"]: e for e in (safe(lambda: gtt_backlog.parse(dl.BACKLOG)[1], []) or [])}
    raw = {k: v["status"] for k, v in raw_epics.items()}
    raw_stories = {x["id"]: x for x in (safe(lambda: gtt_backlog.parse(dl.BACKLOG)[0], []) or [])}
    for e in epics:
        e["status"] = raw.get(e["id"]) or e["status"]
    report = safe(lambda: dl.build_plan()) or {}
    calibration = report.get("calibration") or {}
    forecast = report.get("eta")
    deadline = report.get("deadline")

    live_stories = [s for s in stories if s["status"] != "Cancelled"]
    done = [s for s in live_stories if s["status"] == "Done"]
    pct = round(100 * len(done) / len(live_stories)) if live_stories else None

    signals = safe(dl.signals, []) or []
    flags = {}
    for sig in signals:
        flags.setdefault(sig["artifact"], []).append(sig["rule"])

    sorted_epics = []
    for e in epics:
        own = [s for s in stories if s["epic"] == e["id"] and s["status"] != "Cancelled"]
        started = [times.get(s["id"], {}).get("started") for s in own]
        closed = [times.get(s["id"], {}).get("closed") for s in own]
        started = [t for t in started if t]
        closed = [t for t in closed if t]
        state = {"Completed": "done", "In Progress": "in_progress", "Planned": "planned", "Proposed": "proposed"}.get(e["status"], "planned")
        sorted_epics.append({
            "ref": e["id"], "title": e.get("title"), "lane": e["lane"] or "main", "state": state,
            "start": day(min(started).isoformat()) if started else None,
            "end": day(max(closed).isoformat()) if closed and state == "done" else None,
            "stories": {"done": sum(1 for s in own if s["status"] == "Done"),
                        "in_progress": sum(1 for s in own if s["status"] == "In Progress"),
                        "blocked": sum(1 for s in own if s["status"] == "Blocked"),
                        "planned": sum(1 for s in own if s["status"] not in ("Done", "In Progress", "Blocked"))},
            "flags": flags.get(e["id"], []),
            "status": e["status"], "owner": e.get("owner") or None, "estimate_h": e.get("estimate_h"), "depends": e.get("depends") or [],
            "goal": short((raw_epics.get(e["id"], {}).get("fields") or {}).get("Goal"), 400),
            "approved": short((raw_epics.get(e["id"], {}).get("fields") or {}).get("Approved"), 80),
            "origin": origin_of((raw_epics.get(e["id"], {}).get("fields") or {}).get("Origin")),
            "priority": priority_of((raw_epics.get(e["id"], {}).get("fields") or {}).get("Priority"))})

    out_stories = []
    for s in stories:
        t = times.get(s["id"], {})
        fields = (raw_stories.get(s["id"]) or {}).get("fields") or {}
        rel_name, out_of_scope = release_of(fields)
        elapsed = None
        if t.get("started") and t.get("closed"):
            elapsed = round((t["closed"] - t["started"]).total_seconds() / 3600.0, 1)
        out_stories.append({"ref": s["id"], "epic": s["epic"], "title": s.get("title"), "status": s["status"],
                            "estimate_h": s["estimate_h"], "elapsed_h": elapsed,
                            "closed_by_evidence": bool(s["closed"].strip()) if s["status"] == "Done" else False,
                            "owner": s.get("owner") or "agent", "done_when": short(s.get("done_when"), 300), "closed": short(s.get("closed"), 200),
                            "flags": flags.get(s["id"], []),
                            "release": rel_name, "out_of_scope": out_of_scope, "front": front_of(fields),
                            "blocked_by": blocked_by(fields) if s["status"] in ("Blocked", "Planned", "In Progress") else None})
    by_id = {x["ref"]: x for x in out_stories}

    lanes = [{"id": k, "name": k} for k in sorted({e["lane"] for e in sorted_epics})]

    words = {"es": {"batch": "Epics con trabajo hecho o en curso, sin aprobar", "sealed": "ya construido: falta tu sello", "open": "stories abiertas", "nocause": "bloqueada sin una pregunta que lo explique"},
             "en": {"batch": "Epics with work done or under way, not approved", "sealed": "already built: needs your seal", "open": "open stories", "nocause": "blocked with no question explaining it"}}.get(lang or "en", {})
    here = os.getcwd()

    def at(command):
        """Every act runs in the project's folder: the command carries the way there."""
        return "cd '" + here.replace("'", "'\\''") + "' && " + command

    def is_open(s):
        return s["status"] not in ("Done", "Cancelled")

    ctx = safe(gtt_pending.contract)
    pend = safe(lambda: gtt_pending.summary(ctx), {}) or {}
    waits = {w.get("ask"): w for w in (safe(lambda: dl.human_waits(stories, times), []) or []) if w.get("ask")}
    needs = []
    for r in pend.get("asks", []):
        wait = waits.get(r["id"], {})
        blocked = [s for s in stories if r.get("blocks") and s["id"] == r["blocks"] and is_open(s)]
        number = r["number"]
        # What the human must do follows the kind of question: a key or an account is handed over (`provide`); the rest is decided.
        how = "provide" if r.get("class") in ("key", "account") else "decide"
        choices = [{"label": o, "command": at(f"gtt answer {number} {i}")} for i, o in enumerate(r.get("options") or [], 1)][:4] if how == "decide" else []
        needs.append({"ref": r["id"], "kind": "ask", "how": how, "title": r["title"],
                      "weight": {"stories": len(blocked), "hours": wait.get("waiting_h")}, "unblocks": [s["id"] for s in blocked][:3],
                      "choices": choices, "command": at(f"gtt answer {number} {r['recommended'] or 'ok'}")})
    # Only a promotion set that is ready to apply is an act of the human; a folder left without its spec is not.
    proposals = safe(lambda: gtt_change.drafts(), []) or []
    nxt_props = [{"ref": p["name"], "kind": p["kind"], "title": p.get("title") or p["name"], "command": at(f"gtt promote {p['name']}")}
                 for p in proposals if p["kind"] == "promotion-set" and p.get("state") == "ready to promote"]
    # A Proposed Epic needs you when work already stands on it (a Story done or in progress): the seal of what is
    # built. One without movement waits, and is listed apart; approving it moves nothing today.
    to_approve, underway = [], []
    for e in epics:
        if e["status"] != "Proposed":
            continue
        own = [s for s in stories if s["epic"] == e["id"] and s["status"] != "Cancelled"]
        opened = [s for s in own if is_open(s)]
        moving = any(s["status"] in ("Done", "In Progress") for s in own)
        row = {"ref": e["id"], "title": e.get("title"), "open_stories": len(opened), "done_stories": len(own) - len(opened), "command": at(f"gtt approve {e['id']}")}
        if moving:
            underway.append(e["id"])
            needs.append({"ref": e["id"], "kind": "epic", "title": e.get("title") or e["id"], "weight": {"stories": len(opened), "hours": e["estimate_h"]},
                          "unblocks": [s["id"] for s in opened][:3], "note": words.get("sealed"), "command": row["command"]})
        else:
            to_approve.append(row)
    if len(underway) >= 3:
        weight = sum(n["weight"]["stories"] or 0 for n in needs if n["kind"] == "epic")
        needs.append({"ref": f"{underway[0]}…{underway[-1]}", "kind": "epic-batch", "title": f"{len(underway)} " + words.get("batch", ""),
                      "weight": {"stories": weight, "hours": None}, "unblocks": [], "refs": underway,
                      "command": at("for e in " + " ".join(underway) + "; do gtt approve $e; done")})
    # A Blocked Story no question explains still waits on someone: say so, without inventing a command.
    explained = {n["unblocks"][i] for n in needs for i in range(len(n.get("unblocks") or []))}
    explained |= {r["blocks"] for r in pend.get("asks", []) if r.get("blocks")}
    for s in stories:
        if s["status"] == "Blocked" and s["id"] not in explained:
            needs.append({"ref": s["id"], "kind": "blocked", "how": "blocked", "title": s.get("title") or s["id"],
                          "weight": {"stories": 1, "hours": s["estimate_h"]}, "unblocks": [s["id"]],
                          "note": by_id[s["id"]]["blocked_by"] or words.get("nocause"), "command": None})
    inbox, inbox_counts, by_ref = None, None, {}
    try:
        inbox, inbox_counts, inbox_needs, by_ref = inbox_section(at, pend)
        needs.extend(inbox_needs)
    except (Exception, SystemExit):
        inbox = inbox_counts = None             # a Bootstrap without the inbox: no data, never an empty guess
    needs.sort(key=lambda n: (n["kind"] != "epic-batch", -(n["weight"]["stories"] or 0), -(n["weight"]["hours"] or 0), KIND_RANK.get(n["kind"], 0), n["ref"]))
    planned = [{"ref": e["id"], "title": e.get("title"), "lane": e["lane"] or "main"} for e in epics if e["status"] == "Planned"][:3]

    recent = []
    for entry in reversed((safe(dl.read_log, []) or [])[-RECENT:]):
        recent.append({"at": entry.get("t"), "actor": actor_kind(entry.get("actor")), "action": f"{entry.get('kind')} {entry.get('from') or '-'} -> {entry.get('to')}",
                       "ref": entry.get("id"), "text": f"{entry.get('id')}: {entry.get('from') or 'new'} -> {entry.get('to')}"})

    today = datetime.datetime.now(datetime.timezone.utc).date()
    if not recent:        # a Bootstrap without the delivery log: the `Closed:` lines still say what was finished, and when
        closed = sorted(((closed_day(s.get("closed")), s["id"], s) for s in stories if s["status"] == "Done" and closed_day(s.get("closed"))), reverse=True)
        recent = [{"at": d + "T00:00:00Z", "actor": None, "action": "closed", "ref": ident, "derived": True,
                   "text": f"{ident}: closed · {short(s.get('title'), 80) or ''}"} for d, ident, s in closed[:RECENT]]

    live_out = [x for x in out_stories if x["status"] != "Cancelled"]
    est = [x for x in live_out if x["estimate_h"]]
    hours_total = sum(x["estimate_h"] for x in est)
    hours_done = sum(x["estimate_h"] for x in est if x["status"] == "Done")
    hours = {"done": round(hours_done, 1), "total": round(hours_total, 1), "estimated_stories": len(est),
             "pct": round(100 * hours_done / hours_total) if hours_total else None}
    releases, order = {}, []
    for x in live_out:
        if not x["release"]:
            continue
        r = releases.setdefault(x["release"], {"name": x["release"], "done": 0, "total": 0, "hours_done": 0.0, "hours_total": 0.0, "scope": "out" if x["out_of_scope"] else "in"})
        if x["release"] not in order:
            order.append(x["release"])
        r["total"] += 1
        r["hours_total"] += x["estimate_h"] or 0
        if x["status"] == "Done":
            r["done"] += 1
            r["hours_done"] += x["estimate_h"] or 0
    release_rows = [dict(releases[n], hours_done=round(releases[n]["hours_done"], 1), hours_total=round(releases[n]["hours_total"], 1)) for n in order] or None
    in_scope = None
    if release_rows and any(r["scope"] == "out" for r in release_rows):
        inside = [x for x in live_out if not (x["release"] and releases[x["release"]]["scope"] == "out")]
        n_done = sum(1 for x in inside if x["status"] == "Done")
        in_scope = {"done": n_done, "total": len(inside), "pct": round(100 * n_done / len(inside)) if inside else None,
                    "excluded": sum(1 for x in live_out if x["release"] and releases[x["release"]]["scope"] == "out")}

    def hours_since(moment):
        try:
            return round((datetime.datetime.now(datetime.timezone.utc) - moment).total_seconds() / 3600.0, 1)
        except (TypeError, ValueError):
            return None
    working = []
    for x in out_stories:
        if x["status"] == "In Progress":
            working.append({"ref": x["ref"], "title": x["title"], "epic": x["epic"], "front": x["front"], "release": x["release"],
                            "estimate_h": x["estimate_h"], "since_h": hours_since(times.get(x["ref"], {}).get("started")) if times.get(x["ref"], {}).get("started") else None,
                            "flags": x["flags"]})
    working.sort(key=lambda w: (-(w["since_h"] or 0), w["ref"]))

    ideas = []
    try:
        import gtt_idea
        ic = gtt_idea.contract()
        ideas = [{"ref": r["ref"], "title": r["title"], "state": r["state"], "to": r["to"]} for r in gtt_idea.rows(ic) if r["state"] != "dropped"]
    except (Exception, SystemExit):
        ideas = None            # a Bootstrap without ideas: no data, never an empty guess

    return {
        "schema": SCHEMA, "generated_at": now_utc(),
        "repo": {"path": root, "key": project_key(name), "name": name},
        "suite_version": (release.get("bootstrap") or {}).get("version"), "lang": lang,
        "project": {"phase": "DEV" if frozen else "THINK", "frozen_at": safe(lambda: open(FROZEN, encoding="utf-8").readline().strip()) if frozen else None,
                    "profile": safe(dl.profile_name)},
        "summary": {"progress_pct": pct, "stories_done": len(done), "stories_total": len(live_stories), "stories_blocked": sum(1 for s in live_stories if s["status"] == "Blocked"),
                    "forecast": forecast, "deadline": deadline, "on_time": report.get("fits"),
                    "calibration": {"ratio": calibration.get("ratio"), "uncalibrated": calibration.get("uncalibrated")},
                    "hours": hours, "releases": release_rows, "in_scope": in_scope, "in_progress": len(working)},
        "columns": COLUMNS, "lanes": lanes, "epics": sorted_epics, "stories": out_stories,
        "next": {"proposals": nxt_props, "epics_to_approve": to_approve, "planned_epics": planned},
        "needs_you": needs,
        "repo_state": repo_state(root),
        "working_now": working[:15], "throughput": throughput(out_stories, today),
        "degraded": safe(lambda: dict(degraded((release.get("bootstrap") or {}).get("version")), command=at("gtt update"))),
        "refresh": "watch" if watcher_alive() else "hook",
        "signals": [{"code": s["rule"], "level": s["level"], "ref": s["artifact"], "text": s["detail"]} for s in signals],
        "health": safe(health_checks),
        "recent": recent,
        "ideas": ideas,
        "inbox": inbox, "inbox_counts": inbox_counts, "decisions": safe(lambda: decisions_list(by_ref)), "me": git_user(),
        "docs": safe(collect_docs) if docs else None,
    }


def cmd_snapshot(args):
    root = repo_root()
    if os.path.realpath(root) != os.path.realpath(os.getcwd()) and os.path.isdir(os.path.join(root, ".gtt")):
        os.chdir(root)      # a linked worktree reads the repo's one state
    try:
        data = build(os.getcwd(), docs=bool(getattr(args, "docs", False)))
    except Exception as exc:        # noqa: BLE001 - the page must get an answer or a clear refusal
        print(f"gtt-sonar: cannot build the snapshot: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(data, indent=2 if not args.json else None, sort_keys=True, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------------------------- render

SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)


def embed(data):
    """JSON safe inside a <script> element: every `<` becomes \\u003c, so `</script>` and `<!--` cannot occur."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def csp_for(template_text):
    """The page may run only the template's own script, by hash; no network, no other source."""
    found = SCRIPT.search(template_text)
    digest = base64_sha256(found.group(1)) if found else ""
    return ("default-src 'none'; script-src 'sha256-%s'; style-src 'unsafe-inline'; font-src file: 'self'; "
            "base-uri 'none'; form-action 'none'" % digest)


def base64_sha256(text):
    import base64
    return base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def page(repos, fonts_rel, root_template=None):
    """The HTML for a list of repos, each {"snapshot": {...}} or {"stale": {...}}."""
    with open(root_template or TEMPLATE, encoding="utf-8") as handle:
        template = handle.read()
    payload = {"schema": "sonar.page.v1", "generated_at": now_utc(), "repos": repos}
    # CSP first: it carries a hash of the script, which does not contain the placeholders below.
    csp = csp_for(template)
    return (template.replace("__SONAR_CSP__", csp).replace("__SONAR_FONTS__", fonts_rel)
            .replace("__SONAR_DATA__", embed(payload)))


def write_atomic(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(tmp, path)


def lock_taken():
    try:
        return time.time() - os.path.getmtime(LOCK) < LOCK_SECONDS
    except OSError:
        return False


def reconcile_quietly():
    """The inbox reconcile runs at the render (order 6.1): it files what arrived by hand. If this Bootstrap has no such
    subcommand, or it fails, the page is drawn all the same and nothing is said. The snapshot itself never calls it."""
    script = os.path.join(".gtt", "scripts", "gtt-inbox.sh")
    if not os.path.isfile(script):
        return
    try:
        subprocess.run(["bash", script, "reconcile", "--apply"], stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


def cmd_render(args):
    quiet = args.quiet
    try:
        if args.sources:
            repos = []
            for path in args.sources:
                data = read_json(path)
                if data and data.get("schema") == SCHEMA:
                    repos.append({"snapshot": data})
                elif data and isinstance(data.get("stale"), dict):
                    repos.append({"stale": data["stale"]})      # a repo whose Bootstrap has no snapshot: the CLI says so
                else:
                    repos.append({"stale": {"path": path, "name": os.path.basename(path), "reason": "unknown schema"}})
            if not args.out:
                raise ValueError("--out is required when snapshot files are given")
            fonts = args.fonts
            if not fonts:                  # a page outside the repo carries its own copy of the fonts, next to it
                fonts = "fonts"
                target = os.path.join(os.path.dirname(os.path.abspath(args.out)), "fonts")
                os.makedirs(target, exist_ok=True)
                for name in os.listdir(FONTS):
                    with open(os.path.join(FONTS, name), "rb") as src, open(os.path.join(target, name), "wb") as dst:
                        dst.write(src.read())
            write_atomic(args.out, page(repos, fonts))
            return 0
        root = repo_root()
        if os.path.realpath(root) != os.path.realpath(os.getcwd()) and os.path.isdir(os.path.join(root, ".gtt")):
            os.chdir(root)
        if quiet and lock_taken():
            return 0                                 # one render at a time: the hook never piles up
        os.makedirs(LOCAL, exist_ok=True)
        if not os.path.exists(os.path.join(LOCAL, ".gitignore")):
            write_atomic(os.path.join(LOCAL, ".gitignore"), "*\n")      # .gtt/local/ is per-user state, never versioned
        write_atomic(LOCK, str(os.getpid()))
        try:
            reconcile_quietly()
            snap = build(os.getcwd(), docs=True)
            write_atomic(os.path.join(LOCAL, "sonar.json"), json.dumps(snap, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            write_atomic(os.path.join(LOCAL, "sonar.html"), page([{"snapshot": snap}], "../sonar/fonts"))
        finally:
            try:
                os.remove(LOCK)
            except OSError:
                pass
        if not quiet:
            print(f"gtt-sonar: wrote {LOCAL}/sonar.html and sonar.json")
        return 0
    except Exception as exc:                          # noqa: BLE001
        if not quiet:
            print(f"gtt-sonar: cannot render: {exc}", file=sys.stderr)
            return 2
        return 0                                      # the hook never fails the tool


def prefs():
    return read_json(PREFS) or {}


def fingerprint():
    """What changes when the page should change: the backlog, the pending events, the health files, the proposals,
    the freeze and git's HEAD and index. Names, sizes and mtimes only; nothing is read."""
    marks = []
    for path in ("gtt-domain/backlog.md", "gtt-domain/.frozen", "gtt-domain/delivery-log.jsonl", ".git/HEAD", ".git/index"):
        try:
            st = os.stat(path)
            marks.append((path, st.st_mtime_ns, st.st_size))
        except OSError:
            pass
    for folder in ("gtt-domain/pending", "gtt-domain/proposals", "gtt-domain/adr", "docs/ideas", HEALTH_DIR):
        try:
            for entry in os.scandir(folder):
                st = entry.stat()
                marks.append((entry.path, st.st_mtime_ns, st.st_size))
        except OSError:
            pass
    return hash(tuple(sorted(marks)))


def cmd_watch(args):
    """Keeps the page fresh without tokens: one watcher per project, started by the session, gone after WATCH_HOURS."""
    root = repo_root()
    if os.path.realpath(root) != os.path.realpath(os.getcwd()) and os.path.isdir(os.path.join(root, ".gtt")):
        os.chdir(root)
    if watcher_alive():
        return 0
    os.makedirs(LOCAL, exist_ok=True)
    write_atomic(WATCH_PID, f"{os.getpid()} {now_utc()}\n")
    import signal
    stop = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, lambda *_: stop.append(1))
        except (ValueError, OSError):
            pass
    me = str(os.getpid())
    deadline = time.time() + (args.hours or WATCH_HOURS) * 3600
    seen, last = None, 0.0
    try:
        while not stop and time.time() < deadline:
            if (read_text(WATCH_PID) or "").split()[:1] != [me]:
                break                                           # another watcher took over, or the pid file was removed
            now = fingerprint()
            if now != seen or time.time() - last >= WATCH_BEAT:
                subprocess.run([sys.executable, os.path.abspath(__file__), "render", "--quiet"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=120)
                seen, last = fingerprint(), time.time()
            time.sleep(WATCH_EVERY)
    except Exception:                                           # noqa: BLE001 - a watcher never makes noise
        pass
    finally:
        if (read_text(WATCH_PID) or "").split()[:1] == [me]:
            try:
                os.remove(WATCH_PID)
            except OSError:
                pass
    return 0


def read_text(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


def spawn_watcher():
    """Starts the watcher detached unless the human turned it off (or this is CI / a test)."""
    if os.environ.get("CI") or os.environ.get("GTT_SONAR_NO_WATCH") or prefs().get("watch") is False or watcher_alive():
        return
    flags = {"creationflags": 0x00000008 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "watch"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, cwd=os.getcwd(), **flags)


def cmd_prefs(args):
    data = prefs()
    if args.open_on_start or args.watch:
        if args.open_on_start:
            data["open_on_start"] = args.open_on_start == "on"
        if args.watch:
            data["watch"] = args.watch == "on"
        os.makedirs(LOCAL, exist_ok=True)
        write_atomic(PREFS, json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"gtt-sonar: open on session start: {'on' if data.get('open_on_start') else 'off'}; keep the page fresh (watcher): {'off' if data.get('watch') is False else 'on'}")
    return 0


def can_open_here():
    """A browser can be opened only where someone is looking: not over SSH, not without a display."""
    if os.environ.get("SSH_CONNECTION") or os.environ.get("CI"):
        return False
    return sys.platform in ("darwin", "win32") or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def open_once(uri):
    """Opens the page at most once every OPEN_EVERY_HOURS: the page reloads itself, one tab is enough."""
    try:
        if time.time() - os.path.getmtime(OPENED) < OPEN_EVERY_HOURS * 3600:
            return False
    except OSError:
        pass
    if not can_open_here():
        return False
    import webbrowser
    done = webbrowser.open(uri)
    if done:
        write_atomic(OPENED, now_utc())
    return bool(done)


def cmd_start(args):
    """One line for the human, from the snapshot just written. Never fails the session and never blocks."""
    try:
        root = repo_root()
        if os.path.realpath(root) != os.path.realpath(os.getcwd()) and os.path.isdir(os.path.join(root, ".gtt")):
            os.chdir(root)
        ns = argparse.Namespace(quiet=True, sources=[], out=None, fonts=None)
        cmd_render(ns)
        snap = read_json(os.path.join(LOCAL, "sonar.json"))
        page_path = os.path.abspath(os.path.join(LOCAL, "sonar.html"))
        if not snap or not os.path.isfile(page_path):
            return 0
        import pathlib
        uri = pathlib.Path(page_path).as_uri()
        waiting = len(snap.get("needs_you") or [])
        blocked = (snap.get("summary") or {}).get("stories_blocked") or 0
        if snap.get("lang") == "es":
            head = f"{waiting} cosa(s) te esperan" if waiting else "nada te espera"
            tail = f" · {blocked} historia(s) bloqueada(s)" if blocked else ""
            line = f"Sonar: {head}{tail} · {uri} (también `gtt sonar`)"
        else:
            head = f"{waiting} thing(s) wait for you" if waiting else "nothing waits for you"
            tail = f" · {blocked} blocked Stor{'y' if blocked == 1 else 'ies'}" if blocked else ""
            line = f"Sonar: {head}{tail} · {uri} (also `gtt sonar`)"
        spawn_watcher()
        if prefs().get("open_on_start"):
            open_once(uri)
        print(line)
    except Exception:                                  # noqa: BLE001
        pass
    return 0


def main(argv):
    p = argparse.ArgumentParser(prog="gtt_sonar.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--json", action="store_true")
    s.add_argument("--docs", action="store_true")
    s.set_defaults(func=cmd_snapshot)
    r = sub.add_parser("render")
    r.add_argument("--quiet", action="store_true")
    r.add_argument("sources", nargs="*")
    r.add_argument("--out")
    r.add_argument("--fonts")
    r.set_defaults(func=cmd_render)
    st = sub.add_parser("start")
    st.set_defaults(func=cmd_start)
    wt = sub.add_parser("watch")
    wt.add_argument("--hours", type=float)
    wt.set_defaults(func=cmd_watch)
    pf = sub.add_parser("prefs")
    pf.add_argument("--open-on-start", choices=["on", "off"])
    pf.add_argument("--watch", choices=["on", "off"])
    pf.set_defaults(func=cmd_prefs)
    args = p.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
