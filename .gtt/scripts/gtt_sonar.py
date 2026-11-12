#!/usr/bin/env python3
"""GTT Sonar - the snapshot: one JSON, calculated by the scripts that own each fact.

  gtt_sonar.py snapshot [--json] [--docs]   the `sonar.v1` document (read-only; writes nothing); --docs adds the
                                    governed documents, already turned into safe blocks (the project page has them)
  gtt_sonar.py render [--quiet]     writes .gtt/local/sonar.html and sonar.json (derived, disposable, outside git)
  gtt_sonar.py render --out HTML [--fonts DIR] FILE...   a page from several snapshots (the portfolio)
  gtt_sonar.py start                renders, then prints ONE line saying where the page is and what waits for the human
                                    (the session start uses it); opens the page once if the human asked for it
  gtt_sonar.py prefs [--open-on-start on|off]   the human's own preference, kept in .gtt/local/ (never versioned)

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
            "approved": short((raw_epics.get(e["id"], {}).get("fields") or {}).get("Approved"), 80)})

    out_stories = []
    for s in stories:
        t = times.get(s["id"], {})
        elapsed = None
        if t.get("started") and t.get("closed"):
            elapsed = round((t["closed"] - t["started"]).total_seconds() / 3600.0, 1)
        out_stories.append({"ref": s["id"], "epic": s["epic"], "title": s.get("title"), "status": s["status"],
                            "estimate_h": s["estimate_h"], "elapsed_h": elapsed,
                            "closed_by_evidence": bool(s["closed"].strip()) if s["status"] == "Done" else False,
                            "owner": s.get("owner") or "agent", "done_when": short(s.get("done_when"), 300), "closed": short(s.get("closed"), 200),
                            "flags": flags.get(s["id"], [])})

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
                          "weight": {"stories": 1, "hours": s["estimate_h"]}, "unblocks": [s["id"]], "note": words.get("nocause"), "command": None})
    needs.sort(key=lambda n: (n["kind"] != "epic-batch", -(n["weight"]["stories"] or 0), -(n["weight"]["hours"] or 0), n["ref"]))
    planned = [{"ref": e["id"], "title": e.get("title"), "lane": e["lane"] or "main"} for e in epics if e["status"] == "Planned"][:3]

    recent = []
    for entry in reversed((safe(dl.read_log, []) or [])[-RECENT:]):
        recent.append({"at": entry.get("t"), "actor": actor_kind(entry.get("actor")), "action": f"{entry.get('kind')} {entry.get('from') or '-'} -> {entry.get('to')}",
                       "ref": entry.get("id"), "text": f"{entry.get('id')}: {entry.get('from') or 'new'} -> {entry.get('to')}"})

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
                    "calibration": {"ratio": calibration.get("ratio"), "uncalibrated": calibration.get("uncalibrated")}},
        "columns": COLUMNS, "lanes": lanes, "epics": sorted_epics, "stories": out_stories,
        "next": {"proposals": nxt_props, "epics_to_approve": to_approve, "planned_epics": planned},
        "needs_you": needs,
        "repo_state": repo_state(root),
        "signals": [{"code": s["rule"], "level": s["level"], "ref": s["artifact"], "text": s["detail"]} for s in signals],
        "health": [],
        "recent": recent,
        "ideas": ideas,
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


def cmd_prefs(args):
    data = prefs()
    if args.open_on_start:
        data["open_on_start"] = args.open_on_start == "on"
        os.makedirs(LOCAL, exist_ok=True)
        write_atomic(PREFS, json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"gtt-sonar: open on session start: {'on' if data.get('open_on_start') else 'off'}")
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
    pf = sub.add_parser("prefs")
    pf.add_argument("--open-on-start", choices=["on", "off"])
    pf.set_defaults(func=cmd_prefs)
    args = p.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
