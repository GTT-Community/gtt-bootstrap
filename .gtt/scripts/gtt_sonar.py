#!/usr/bin/env python3
"""GTT Sonar - the snapshot: one JSON, calculated by the scripts that own each fact.

  gtt_sonar.py snapshot [--json]    the `sonar.v1` document (read-only; writes nothing)
  gtt_sonar.py render [--quiet]     writes .gtt/local/sonar.html and sonar.json (derived, disposable, outside git)
  gtt_sonar.py render --out HTML [--fonts DIR] FILE...   a page from several snapshots (the portfolio)

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


def build(root):
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
    raw = {e["id"]: e["status"] for e in (safe(lambda: gtt_backlog.parse(dl.BACKLOG)[1], []) or [])}
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
                        "planned": sum(1 for s in own if s["status"] not in ("Done", "In Progress"))},
            "flags": flags.get(e["id"], [])})

    out_stories = []
    for s in stories:
        t = times.get(s["id"], {})
        elapsed = None
        if t.get("started") and t.get("closed"):
            elapsed = round((t["closed"] - t["started"]).total_seconds() / 3600.0, 1)
        out_stories.append({"ref": s["id"], "epic": s["epic"], "title": s.get("title"), "status": s["status"],
                            "estimate_h": s["estimate_h"], "elapsed_h": elapsed,
                            "closed_by_evidence": bool(s["closed"].strip()) if s["status"] == "Done" else False,
                            "flags": flags.get(s["id"], [])})

    lanes = [{"id": k, "name": k} for k in sorted({e["lane"] for e in sorted_epics})]

    words = {"es": {"batch": "Epics con trabajo hecho o en curso, sin aprobar", "sealed": "ya construido: falta tu sello", "open": "stories abiertas"},
             "en": {"batch": "Epics with work done or under way, not approved", "sealed": "already built: needs your seal", "open": "open stories"}}.get(lang or "en", {})
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
        needs.append({"ref": r["id"], "kind": "ask", "title": r["title"],
                      "weight": {"stories": len(blocked), "hours": wait.get("waiting_h")}, "unblocks": [s["id"] for s in blocked][:3],
                      "command": at(f"gtt answer {number} {r['recommended'] or 'ok'}")})
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
        "summary": {"progress_pct": pct, "stories_done": len(done), "stories_total": len(live_stories),
                    "forecast": forecast, "deadline": deadline, "on_time": report.get("fits"),
                    "calibration": {"ratio": calibration.get("ratio"), "uncalibrated": calibration.get("uncalibrated")}},
        "columns": COLUMNS, "lanes": lanes, "epics": sorted_epics, "stories": out_stories,
        "next": {"proposals": nxt_props, "epics_to_approve": to_approve, "planned_epics": planned},
        "needs_you": needs,
        "signals": [{"code": s["rule"], "level": s["level"], "ref": s["artifact"], "text": s["detail"]} for s in signals],
        "health": [],
        "recent": recent,
        "ideas": ideas,
    }


def cmd_snapshot(args):
    root = repo_root()
    if os.path.realpath(root) != os.path.realpath(os.getcwd()) and os.path.isdir(os.path.join(root, ".gtt")):
        os.chdir(root)      # a linked worktree reads the repo's one state
    try:
        data = build(os.getcwd())
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
            snap = build(os.getcwd())
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


def main(argv):
    p = argparse.ArgumentParser(prog="gtt_sonar.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_snapshot)
    r = sub.add_parser("render")
    r.add_argument("--quiet", action="store_true")
    r.add_argument("sources", nargs="*")
    r.add_argument("--out")
    r.add_argument("--fonts")
    r.set_defaults(func=cmd_render)
    args = p.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
