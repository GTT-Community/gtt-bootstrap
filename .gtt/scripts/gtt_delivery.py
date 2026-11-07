#!/usr/bin/env python3
"""GTT - Delivery Planning (engine): how long the plan takes, with how many hands, and whether it fits.

    .gtt/contract/delivery.json     the six questions, the thresholds and the verification rules (data)
    .gtt/delivery.json              the setup answer (state, never authority) - written only by `select`
    gtt-domain/backlog.md           Epic fields Estimate, Depends on, Lane, Owner, Touches, Build, Budget;
                                    Story fields Estimate, Owner
    gtt-domain/delivery-log.jsonl   append-only record of every Story/Epic status change, written only by `log`
    .gtt/local/delivery-snapshot.json  the statuses `log` saw last (local, never versioned)

  gtt_delivery.py questions [--lang L] [--json]    the six questions, texts from the contract
  gtt_delivery.py select [--who W] [--lanes N] [--horizon H] [--pace days|flow] [--priority P] [--third-party T] [--restrictions TEXT]
                         [--epic-cap HOURS] [--team NAMES] [--by NAME] [--apply]
                                                    record the setup answer (dry run without --apply); allowed at any time
  gtt_delivery.py tell                              what the human must hear about the size, one line each (silent when nothing is open)
  gtt_delivery.py size [--lang L] [--json]         how big the backlog is, as facts; judged only against the cap and growth the human set
  gtt_delivery.py get [--json]                     the setup answer and the thresholds in force
  gtt_delivery.py plan [--lanes] [--json]          the plan per front, the longest chain, the forecast, the levers
  gtt_delivery.py report [--epic EPIC-NNN] [--json] percent, real against estimated, calibration, forecast, open DLV signals
  gtt_delivery.py check [--pre-freeze] [--json]    the freeze rules; the severity of each comes from the Autonomy Profile
  gtt_delivery.py log                              record the status changes of the backlog since the last run
  gtt_delivery.py summary                          the `## Delivery` block of gtt-domain/session.md

Everything is computed from files, never judged and never spent on tokens. Nothing here launches an agent:
GTT plans and watches the fronts; the ADE (or the people) do the work. `select` is a dry run without --apply.
Exit 0 = ok (warnings allowed), 1 = violation or refused, 2 = cannot run.
"""

import argparse
import datetime
import glob
import hashlib
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

CONTRACT = ".gtt/contract/delivery.json"
PROFILES = ".gtt/contract/profiles.json"
STATE = ".gtt/delivery.json"
LOG = "gtt-domain/delivery-log.jsonl"
SNAPSHOT = ".gtt/local/delivery-snapshot.json"
BACKLOG = "gtt-domain/backlog.md"
METHOD_STATE = ".gtt/development-method.json"
METHODOLOGY = ".gtt/methodology.json"
AGREEMENTS = "gtt-domain/working-agreements.md"
ADE_STATE = ".gtt/ade.json"
OPEN = "OPEN"
DONE = ("Done", "Cancelled")
CLOSED_EPIC = ("Completed", "Cancelled")
FIELDS = ("Estimate", "Depends on", "Lane", "Owner", "Touches", "Build", "Budget")
WHO = ("solo", "solo-multi", "team", OPEN)
HORIZONS = ("days", "weeks", "month", "none", OPEN)
PRIORITY = ("speed", "balance", "own", OPEN)
PACES = ("days", "flow")
THIRD = ("yes", "oss", "restricted", OPEN)
HOURS = re.compile(r"(\d+(?:[.,]\d+)?)\s*h\b", re.I)
DECISIONS = re.compile(r"(\d+)\s*(?:decisions?|decisiones|decisión|pd)\b", re.I)
EPIC_ID = re.compile(r"\bEPIC-\d+\b")
BUDGET_ACCEPTED = re.compile(r"^over\s*[-—–]+\s*accepted:\s*\S.*[-—–]\s*\S.*[-—–]\s*\d{4}-\d{2}-\d{2}\s*$", re.I)
BUDGET_LEVER = re.compile(r"^over\s*[-—–]+\s*(split|cut|integrate)\b", re.I)
BUILD_INTEGRATE = re.compile(r"^integrate\s*\(\s*(ADR-\d{3,})\s*\)\s*$", re.I)
CLOSING = re.compile(r"\b(?:clos(?:e[sd]?|ing)|fix(?:e[sd]|ing)?|resolv(?:e[sd]?|ing)|complet(?:e[sd]?|ing)|finish(?:e[sd]|ing)?|done|"
                     r"cierr[ae]n?|cerr[oó]|cerrad[ao]s?|termin[oó]|terminad[ao]s?|complet[oó]|completad[ao]s?)\b", re.I)
CLOSED_AFTER = re.compile(r"(STORY-\d+)\W{0,3}(?:done|closed|completed|cerrad[ao]|completad[ao]|terminad[ao])\b", re.I)
NOT_CLOSING = re.compile(r"\b(?:wip|partial(?:ly)?|parcial(?:mente)?|part of|toward[s]?|not|no|sin)\b", re.I)
STORY_ID = re.compile(r"\bSTORY-\d+\b")
SOURCE = re.compile(r"\[FUENTE:\s*([^\]]*?)\s*,?\s*(?:consultado|consulted|accessed)\s+(\d{4}-\d{2}-\d{2})\s*\]", re.I)


# ------------------------------------------------------------------------------------------ basics

def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read().replace("\r\n", "\n")
    except OSError:
        return None


def read_json(path):
    text = read(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def emit(obj):
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def die(message, code=2):
    print(f"gtt-delivery: {message}", file=sys.stderr)
    sys.exit(code)


def stamp():
    return os.environ.get("GTT_NOW") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def moment():
    text = stamp()
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        die(f"GTT_NOW is not an UTC timestamp (YYYY-MM-DDTHH:MM:SSZ): {text}")


def parse_time(text):
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except (ValueError, TypeError):
        return None


def contract():
    data = read_json(CONTRACT)
    if data is None:
        die(f"{CONTRACT} is missing or not valid JSON")
    return data


def thresholds():
    base = dict(contract()["thresholds"])
    state = read_json(STATE) or {}
    if isinstance(state.get("epic_cap_h"), (int, float)) and state["epic_cap_h"] > 0:
        base["epic_cap_h"] = state["epic_cap_h"]
    if isinstance(state.get("growth_pct"), (int, float)) and state["growth_pct"] > 0:
        base["growth_pct"] = state["growth_pct"]
    base["scope_min_h"] = state["scope_min_h"] if isinstance(state.get("scope_min_h"), (int, float)) and state["scope_min_h"] > 0 else None
    base["scope_cap_h"] = state["scope_cap_h"] if isinstance(state.get("scope_cap_h"), (int, float)) and state["scope_cap_h"] > 0 else None
    return base


def profile_name():
    chosen = (read_json(METHODOLOGY) or {}).get("profile")
    spec = read_json(PROFILES) or {}
    return chosen if chosen in (spec.get("profiles") or {}) else spec.get("default", "medium")


def profile_delivery():
    spec = (read_json(PROFILES) or {}).get("profiles", {}).get(profile_name(), {})
    return spec.get("delivery") or {"signals": {}, "freeze": {}}


def hours_of(text):
    found = HOURS.search(text or "")
    return float(found.group(1).replace(",", ".")) if found else None


def decisions_of(text):
    found = DECISIONS.search(text or "")
    return int(found.group(1)) if found else 0


def split_list(text):
    return [part.strip().strip("`") for part in re.split(r"[,;]", text or "") if part.strip().strip("`")]


def blank(text):
    return (text or "").strip(" -—–.").lower() in ("", "tbd", "todo", "pending", "pendiente", "none", "n/a") \
        or bool(re.fullmatch(r"<[^<>]*>", (text or "").strip()))


def normal_path(path):
    return path.strip().strip("`").replace("\\", "/").strip("/").lower()


def overlaps(a, b):
    a, b = normal_path(a), normal_path(b)
    return bool(a) and bool(b) and (a == b or a.startswith(b + "/") or b.startswith(a + "/"))


def fmt_h(value):
    return f"{value:g}h"


# --------------------------------------------------------------------------------------- the backlog

def backlog():
    """(stories, epics) with the delivery view of each. Story: id, epic, status, estimate_h, owner. Epic: id, status,
    lane, depends, touches, build, budget, estimate_h, decisions, line. None when there is no backlog."""
    if not os.path.isfile(BACKLOG):
        return None
    import gtt_backlog
    stories, epics = gtt_backlog.parse(BACKLOG)
    out_stories, out_epics = [], []
    for story in stories:
        f = story["fields"]
        out_stories.append({"id": story["id"], "epic": story["epic"], "line": story["line"],
                            "status": gtt_backlog.normal(story["status"]), "estimate_h": hours_of(f.get("Estimate", "")),
                            "owner": (f.get("Owner", "agent").strip().lower() or "agent"), "done_when": f.get("Done when", ""),
                            "closed": f.get("Closed", "")})
    for epic in epics:
        f = epic["fields"]
        out_epics.append({"id": epic["id"], "line": epic["line"], "status": gtt_backlog.normal(epic.get("status", "")),
                          "kind": f.get("Kind", "").strip().strip("`").lower(),
                          "lane": f.get("Lane", "").strip().strip("`"), "owner": f.get("Owner", "").strip(),
                          "depends": EPIC_ID.findall(f.get("Depends on", "")), "touches": split_list(f.get("Touches", "")),
                          "build": f.get("Build", "").strip(), "budget": f.get("Budget", "").strip(),
                          "estimate_text": f.get("Estimate", ""), "estimate_h": hours_of(f.get("Estimate", "")),
                          "decisions": decisions_of(f.get("Estimate", "")),
                          "declared": [k for k in FIELDS if not blank(f.get(k, ""))]})
    return out_stories, out_epics


def live(epics):
    return [e for e in epics if e["status"] not in CLOSED_EPIC]


def epic_hours(epic, stories):
    """The Epic's estimate: its own, else the sum of its Stories', else None."""
    if epic["estimate_h"] is not None:
        return epic["estimate_h"]
    own = [s["estimate_h"] for s in stories if s["epic"] == epic["id"] and s["status"] != "Cancelled"]
    return sum(h for h in own if h is not None) if any(h is not None for h in own) else None


def progress(epic, stories):
    """(fraction done 0..1, how it was computed). By the Stories' estimates when all have one, else by count."""
    if epic["status"] == "Completed":
        return 1.0, "status"
    own = [s for s in stories if s["epic"] == epic["id"] and s["status"] != "Cancelled"]
    if not own:
        return 0.0, "no stories"
    if all(s["estimate_h"] for s in own):
        total = sum(s["estimate_h"] for s in own)
        return sum(s["estimate_h"] for s in own if s["status"] == "Done") / total, "estimate"
    return sum(1 for s in own if s["status"] == "Done") / len(own), "stories"


def remaining_h(epic, stories):
    hours = epic_hours(epic, stories)
    if hours is None:
        return 0.0
    return hours * (1.0 - progress(epic, stories)[0])


# ----------------------------------------------------------------------------------------------- the log

def read_log():
    out = []
    for line in (read(LOG) or "").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def actor():
    if os.environ.get("GTT_ACTOR"):
        return os.environ["GTT_ACTOR"]
    primary = (read_json(ADE_STATE) or {}).get("primary")
    return f"ade:{primary}" if primary else "unknown"


def cmd_log(args):
    """Compare the backlog with the statuses seen last and append one line per change. No arguments on purpose:
    what is recorded is what the backlog says, so the log cannot be told a different story."""
    loaded = backlog()
    if loaded is None:
        return 0
    stories, epics = loaded
    lane_of = {e["id"]: e["lane"] for e in epics}
    previous = (read_json(SNAPSHOT) or {})
    seen = {"story": previous.get("story") or {}, "epic": previous.get("epic") or {}}
    now, who, lines = stamp(), actor(), []
    current = {"story": {s["id"]: s["status"] for s in stories}, "epic": {e["id"]: e["status"] for e in epics}}
    parent = {s["id"]: s["epic"] for s in stories}
    for kind in ("story", "epic"):
        for ident, status in current[kind].items():
            before = seen[kind].get(ident)
            if before == status:
                continue
            owner = parent.get(ident) if kind == "story" else ident
            lines.append({"t": now, "kind": kind, "id": ident, "epic": owner, "lane": lane_of.get(owner, ""),
                          "from": before, "to": status, "actor": who})
    if lines:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8", newline="\n") as handle:
            for entry in lines:
                handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    if lines or not os.path.isfile(SNAPSHOT):
        os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
        with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(current, sort_keys=True) + "\n")
    if lines:
        print(f"gtt-delivery: logged {len(lines)} status change(s) in {LOG}")
    return 0


def timeline():
    """{story id: {first_seen, started, closed, status}} from the log. `started` is the last move to In Progress,
    `closed` the last move to Done after it."""
    out = {}
    for entry in read_log():
        if entry.get("kind") != "story":
            continue
        t, row = parse_time(entry.get("t")), out.setdefault(entry["id"], {"first_seen": None, "started": None, "closed": None, "status": None})
        if t is None:
            continue
        row["first_seen"] = row["first_seen"] or t
        row["status"] = entry.get("to")
        if entry.get("to") == "In Progress":
            row["started"], row["closed"] = t, None
        elif entry.get("to") == "Done":
            row["closed"] = t
    return out


def measured(stories, times):
    """[(story id, real hours, estimated hours)] of the Done Stories that have both a start and an estimate."""
    out = []
    for s in stories:
        row = times.get(s["id"])
        if s["status"] == "Done" and row and row["started"] and row["closed"] and s["estimate_h"]:
            real = max((row["closed"] - row["started"]).total_seconds() / 3600.0, 0.0)
            out.append((s["id"], real, s["estimate_h"]))
    return out


def calibration(stories, times):
    rows = measured(stories, times)
    need = thresholds()["calibration_min_stories"]
    ratio = statistics.median(r / e for _, r, e in rows) if rows else None
    return {"measured": len(rows), "needed": need, "uncalibrated": len(rows) < need,
            "ratio": round(ratio, 2) if ratio is not None else None}


# ------------------------------------------------------------------------------------------- the plan

def schedule(epics, stories, ratio):
    """Finish time (agent hours from now) of every live Epic: its front works one Epic at a time in backlog order,
    and an Epic starts after the Epics it depends on. Returns (finish, chain, cycles)."""
    todo = {e["id"]: e for e in live(epics)}
    finish, lane_free, cycles, visiting = {}, {}, [], set()
    order = [e["id"] for e in live(epics)]
    lane_of = lambda e: e["lane"] or "main"

    def run(ident):
        if ident in finish:
            return finish[ident]
        epic = todo[ident]
        if ident in visiting:
            cycles.append(ident)
            return 0.0
        visiting.add(ident)
        ready = max([run(d) for d in epic["depends"] if d in todo] + [0.0])
        start = max(ready, lane_free.get(lane_of(epic), 0.0))
        finish[ident] = start + remaining_h(epic, stories) * ratio
        lane_free[lane_of(epic)] = finish[ident]
        visiting.discard(ident)
        return finish[ident]

    for ident in order:
        run(ident)
    chain, tail = [], max(finish, key=finish.get) if finish else None
    while tail:
        chain.append(tail)
        epic = todo[tail]
        before = [d for d in epic["depends"] if d in finish]
        same_lane = [i for i in order[:order.index(tail)] if lane_of(todo[i]) == lane_of(epic) and i in finish]
        pool = before + same_lane[-1:]
        tail = max(pool, key=lambda i: finish[i]) if pool else None
        if tail in chain:
            break
    return finish, list(reversed(chain)), sorted(set(cycles))


def deadline():
    state = read_json(STATE) or {}
    text = state.get("deadline")
    try:
        return datetime.date.fromisoformat(text) if text else None
    except ValueError:
        return None


def build_plan():
    loaded = backlog()
    if loaded is None:
        return None
    stories, epics = loaded
    times = timeline()
    cal = calibration(stories, times)
    ratio = cal["ratio"] if not cal["uncalibrated"] and cal["ratio"] else 1.0
    finish, chain, cycles = schedule(epics, stories, ratio)
    th = thresholds()
    total_h = max(finish.values()) if finish else 0.0
    days = math.ceil(total_h / th["hours_per_day"]) if total_h else 0
    today = moment().date()
    eta = today + datetime.timedelta(days=days)
    limit = deadline()
    lanes = {}
    for epic in live(epics):
        lanes.setdefault(epic["lane"] or "main", []).append(epic["id"])
    unestimated = [e["id"] for e in live(epics) if e["status"] in ("Planned", "In Progress") and epic_hours(e, stories) is None]
    over = [e["id"] for e in live(epics) if (epic_hours(e, stories) or 0) > th["epic_cap_h"]]
    fits = None if limit is None or not finish else eta <= limit
    levers = []
    if fits is False:
        late_h = (eta - limit).days * th["hours_per_day"]
        for epic in sorted(live(epics), key=lambda e: -(remaining_h(e, stories))):
            if remaining_h(epic, stories) > 0 and len(levers) < 3:
                levers.append({"epic": epic["id"], "saves_h": round(remaining_h(epic, stories) * ratio, 1),
                               "lever": "integrate (buy) | cut | split into parallel fronts", "on_critical_chain": epic["id"] in chain})
        late = {"late_days": (eta - limit).days, "late_h_about": late_h}
    else:
        late = None
    return {"schema": 1, "kind": "gtt-delivery-plan", "profile": profile_name(), "calibration": cal,
            "lanes": lanes, "chain": chain, "chain_hours": round(total_h, 1), "days": days, "eta": eta.isoformat() if finish else None,
            "deadline": limit.isoformat() if limit else None, "fits": fits, "late": late, "levers": levers,
            "unestimated": unestimated, "over_cap": over, "cycles": cycles,
            "waiting_on_you": human_waits(stories, times)}


def human_waits(stories, times):
    out, now = [], moment()
    for s in stories:
        if s["owner"] == "human" and s["status"] not in DONE:
            seen = (times.get(s["id"]) or {}).get("first_seen")
            hours = (now - seen).total_seconds() / 3600.0 if seen else 0.0
            out.append({"story": s["id"], "epic": s["epic"], "waiting_h": round(hours, 1)})
    out += pending_waits({w["story"] for w in out}, stories, now)
    return out


def pending_waits(known, stories, now):
    """A question for the human (gtt-domain/pending/) that blocks a Story is a wait on the human too."""
    try:
        import gtt_pending
        asks = gtt_pending.summary()["blocking"]
    except Exception:
        return []
    epic_of = {s["id"]: s["epic"] for s in stories}
    out = []
    for ask in asks:
        if ask["blocks"] in known:
            continue
        try:
            since = datetime.datetime.fromisoformat(ask["created"]).replace(tzinfo=datetime.timezone.utc)
            hours = max((now - since).total_seconds() / 3600.0, 0.0)
        except (TypeError, ValueError):
            hours = 0.0
        out.append({"story": ask["blocks"], "epic": epic_of.get(ask["blocks"], ""), "waiting_h": round(hours, 1), "ask": ask["id"]})
    return out


def cmd_plan(args):
    plan = build_plan()
    if plan is None:
        print("gtt-delivery: no gtt-domain/backlog.md yet - nothing to plan", file=sys.stderr)
        return 1
    if args.lanes:
        return print_lanes(plan, args.json)
    if args.json:
        emit(plan)
        return 0
    cal = plan["calibration"]
    print(f"Delivery plan - profile {plan['profile']}, " + ("UNCALIBRATED (fewer than %d Stories measured; estimates taken as given)" % cal["needed"]
          if cal["uncalibrated"] else f"calibrated on {cal['measured']} Stories (real/estimated x{cal['ratio']})"))
    for lane, ids in plan["lanes"].items():
        print(f"  front {lane}: " + " -> ".join(ids))
    if plan["chain"]:
        print(f"  longest chain: {' -> '.join(plan['chain'])} = {plan['chain_hours']:g} agent h (~{plan['days']} working day(s), "
              f"estimated finish {plan['eta']})")
    if plan["deadline"]:
        print(f"  deadline {plan['deadline']}: " + ("fits" if plan["fits"] else f"DOES NOT FIT - {plan['late']['late_days']} day(s) late"))
        for lever in plan["levers"]:
            print(f"    lever: {lever['epic']} ({lever['saves_h']:g} h)" + (" [critical chain]" if lever["on_critical_chain"] else "")
                  + f" - {lever['lever']}")
    else:
        print("  no deadline declared (gtt delivery set --horizon ...)")
    if plan["unestimated"]:
        print(f"  without Estimate: {', '.join(plan['unestimated'])}")
    if plan["over_cap"]:
        print(f"  over the {thresholds()['epic_cap_h']:g} h cap: {', '.join(plan['over_cap'])}")
    if plan["cycles"]:
        print(f"  dependency cycle through: {', '.join(plan['cycles'])}")
    for wait in plan["waiting_on_you"]:
        print(f"  waiting on you: {wait['story']} ({wait['waiting_h']:g} h)")
    print("  every lever is a [PROPUESTA]: you decide (Budget, Build, Lane); GTT never does.")
    return 0


def lane_data():
    loaded = backlog()
    if loaded is None:
        return None
    stories, epics = loaded
    lanes = {}
    for epic in live(epics):
        row = lanes.setdefault(epic["lane"] or "main", {"owners": set(), "epics": [], "touches": [], "depends_on": set(), "done_when": []})
        row["epics"].append(epic["id"])
        if epic["owner"]:
            row["owners"].add(epic["owner"])
        row["touches"] += [t for t in epic["touches"] if t not in row["touches"]]
        row["depends_on"] |= {d for d in epic["depends"]}
        for s in stories:
            if s["epic"] == epic["id"] and s["status"] not in DONE and not blank(s["done_when"]):
                row["done_when"].append(f"{s['id']}: {s['done_when'][:120]}")
    for row in lanes.values():
        row["owners"] = sorted(row["owners"])
        row["depends_on"] = sorted(row["depends_on"] - set(row["epics"]))
    return lanes


def print_lanes(plan, as_json):
    lanes = lane_data() or {}
    project = os.path.basename(os.getcwd())
    out = []
    for name, row in lanes.items():
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "main"
        out.append(dict(row, lane=name, worktree=f"git worktree add ../{project}-{slug} -b gtt/{slug}"))
    if as_json:
        emit({"schema": 1, "kind": "gtt-delivery-lanes", "lanes": out})
        return 0
    if not out:
        print("gtt-delivery: no live Epic - nothing to split into fronts")
        return 0
    for row in out:
        print(f"front {row['lane']}" + (f" - owner {', '.join(row['owners'])}" if row["owners"] else ""))
        print(f"  Epics:   {', '.join(row['epics'])}")
        print(f"  may touch: {', '.join(row['touches']) or '(no Touches declared)'}")
        print(f"  depends on (through an interface): {', '.join(row['depends_on']) or 'nothing outside the front'}")
        for item in row["done_when"][:5]:
            print(f"  done when: {item}")
        print(f"  {row['worktree']}")
    print("GTT creates no agent, no session and no worktree: copy the commands you want. Work inside your front's Touches; "
          "if you need another front's paths, report it.")
    return 0


# ---------------------------------------------------------------------------------------------- report

def cmd_report(args):
    loaded = backlog()
    if loaded is None:
        print("gtt-delivery: no gtt-domain/backlog.md yet - nothing to report", file=sys.stderr)
        return 1
    stories, epics = loaded
    times, now = timeline(), moment()
    rows = []
    for epic in epics:
        if args.epic and epic["id"] != args.epic:
            continue
        own = [s for s in stories if s["epic"] == epic["id"]]
        fraction, how = progress(epic, stories)
        real = 0.0
        for s in own:
            row = times.get(s["id"])
            if row and row["started"]:
                end = row["closed"] if s["status"] == "Done" and row["closed"] else (now if s["status"] == "In Progress" else None)
                if end:
                    real += max((end - row["started"]).total_seconds() / 3600.0, 0.0)
        rows.append({"epic": epic["id"], "status": epic["status"], "lane": epic["lane"] or "main", "estimate_h": epic_hours(epic, stories),
                     "percent": round(fraction * 100), "percent_by": how, "stories": len(own),
                     "stories_done": sum(1 for s in own if s["status"] == "Done"), "real_h": round(real, 1)})
    if args.epic and not rows:
        print(f"gtt-delivery: {args.epic} is not in the backlog", file=sys.stderr)
        return 1
    plan = build_plan()
    cal = plan["calibration"]
    open_signals = [s for s in signals()]
    data = {"schema": 1, "kind": "gtt-delivery-report", "uncalibrated": cal["uncalibrated"], "calibration": cal,
            "epics": rows, "forecast": {"chain": plan["chain"], "hours": plan["chain_hours"], "eta": plan["eta"], "deadline": plan["deadline"],
                                        "fits": plan["fits"]},
            "planned_h": round(sum(r["estimate_h"] or 0 for r in rows), 1), "real_h": round(sum(r["real_h"] for r in rows), 1),
            "signals": [{"rule": s["rule"], "artifact": s["artifact"], "detail": s["detail"]} for s in open_signals]}
    if args.json:
        emit(data)
        return 0
    print("Delivery report - " + ("UNCALIBRATED (%d of %d Stories measured)" % (cal["measured"], cal["needed"]) if cal["uncalibrated"]
                                  else f"calibrated, real/estimated x{cal['ratio']} over {cal['measured']} Stories"))
    for r in rows:
        est = fmt_h(r["estimate_h"]) if r["estimate_h"] is not None else "no estimate"
        print(f"  {r['epic']:10} {r['status']:12} {r['percent']:3}% (by {r['percent_by']})  {r['stories_done']}/{r['stories']} Stories  "
              f"est {est}, real {fmt_h(r['real_h'])}  front {r['lane']}")
    f = data["forecast"]
    if f["eta"]:
        print(f"  forecast: {f['hours']:g} agent h on the longest chain, finish {f['eta']}" + (f" (deadline {f['deadline']}: {'fits' if f['fits'] else 'DOES NOT FIT'})" if f["deadline"] else ""))
    for s in open_signals:
        print(f"  {s['rule']} {s['artifact']}: {s['detail']}")
    return 0


# --------------------------------------------------------------------------------------------- signals

def lane_cross_level(level):
    if profile_name() == "team" and level == "GOVERNANCE":
        if re.search(r"(?mi)^\s*lane-cross:\s*blocking\b", read(AGREEMENTS) or ""):
            return "BLOCKING"
    return level


def conflicts(epics):
    """[(epic a, epic b, path)]: Epics of different fronts whose Touches overlap, unless one depends on the other."""
    out, items = [], live(epics)
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if (a["lane"] or "main") == (b["lane"] or "main") or b["id"] in a["depends"] or a["id"] in b["depends"]:
                continue
            for pa in a["touches"]:
                hit = next((pb for pb in b["touches"] if overlaps(pa, pb)), None)
                if hit:
                    out.append((a["id"], b["id"], pa if len(normal_path(pa)) >= len(normal_path(hit)) else hit))
                    break
    return out


def budget_decided(epic):
    text = epic["budget"].strip().strip("`")
    return bool(BUDGET_ACCEPTED.match(text) or BUDGET_LEVER.match(text))


def has_method():
    state = read_json(METHOD_STATE) or {}
    return bool(state) and state.get("style") not in (None, OPEN, [OPEN], [])


def open_stories(stories, epics):
    """The Stories still to do under a live Epic."""
    alive = {e["id"] for e in live(epics)}
    return [s for s in stories if s["status"] not in DONE and s["epic"] in alive]


def noplan_finding(stories, epics):
    """(open Stories, with a duration, Epics) when the backlog holds a lot of work that nothing sizes, else None.
    Independent of whether delivery planning was declared: this is exactly the project that never did."""
    th, items = thresholds(), open_stories(stories, epics)
    if len(items) < th["noplan_min_stories"]:
        return None
    sized_epics = {e["id"] for e in epics if epic_hours(e, stories) is not None}
    sized = [s for s in items if s["estimate_h"] or s["epic"] in sized_epics]
    if len(sized) / len(items) >= th["noplan_min_coverage"]:
        return None
    return len(items), len(sized), len({s["epic"] for s in items})


def noplan_text(found):
    total, sized, epics = found
    return (f"{total} open Stories in {epics} Epics, {sized} with a duration: GTT cannot say how long this takes or when it ends. "
            "Add `Estimate: <n>h` to the Epics (or their Stories) and run `gtt delivery set --horizon ... --pace days|flow`")


def stale_statuses(stories):
    """[(story id, commit)]: Stories not Done whose recent commits already close them. The backlog must say what happened."""
    import subprocess
    known = {s["id"]: s for s in stories if s["status"] not in DONE}
    if not known or not os.path.isdir(".git"):
        return []
    try:
        proc = subprocess.run(["git", "log", "-n", str(thresholds()["stale_commits_scanned"]), "--no-merges", "--format=%h%x1f%s%n%b%x1e"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    found = {}
    for entry in proc.stdout.split("\x1e"):
        sha, _, message = entry.strip().partition("\x1f")
        for line in message.splitlines():
            if NOT_CLOSING.search(line):
                continue
            closed = set(m.group(1) for m in CLOSED_AFTER.finditer(line))
            verb = CLOSING.search(line)
            if verb:
                closed |= set(STORY_ID.findall(line[verb.end():]))
            for ident in closed:
                if ident in known and ident not in found:
                    found[ident] = sha
    return sorted(found.items())


def drift_paths():
    skip = ("gtt-domain/session.md", "gtt-domain/change-request.md", "gtt-domain/delivery-log.jsonl")
    paths = glob.glob("gtt-domain/*.md") + glob.glob("docs/**/*.md", recursive=True) + glob.glob("*.md")
    return sorted(p.replace(os.sep, "/") for p in set(paths) if p.replace(os.sep, "/") not in skip)


def unintegrated(stories):
    """(Stories Done without a commit or PR in `Closed:`, uncommitted paths): finished work that Git history does not hold yet."""
    import subprocess
    th = thresholds()
    done = [s["id"] for s in stories if s["status"] == "Done" and not re.search(r"\b[0-9a-f]{7,40}\b|#\d+|\bPR\b|pull request", s["closed"], re.I)]
    if len(done) < th["unintegrated_min_stories"] or not os.path.exists(".git"):
        return [], 0
    try:
        proc = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude)gtt-domain/session.md"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return [], 0
    if proc.returncode != 0:
        return [], 0
    dirty = len([l for l in proc.stdout.splitlines() if "__pycache__/" not in l and not l.endswith(".pyc")])
    return (done, dirty) if dirty >= th["unintegrated_min_paths"] else ([], dirty)


def pace_drift():
    """[(path, line, text)]: documents that speak in the other rhythm than the one declared in `pace`."""
    state = read_json(STATE) or {}
    pace = state.get("pace")
    spec = contract().get("pace", {}).get("drift", {})
    if pace not in PACES or not spec.get(pace):
        return []
    pattern = re.compile("|".join(f"(?:{p})" for p in spec[pace]), re.I)
    out = []
    for path in drift_paths():
        fenced = False
        for number, line in enumerate((read(path) or "").splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
            if not fenced and pattern.search(line):
                out.append((path, number, line.strip()[:80]))
    return out


def workflow_commits():
    """The `commits:` value of gtt-domain/workflow.md; the default when the file or the block is missing."""
    found = re.search(r"^commits:\s*([a-z-]+)", read("gtt-domain/workflow.md") or "", re.MULTILINE)
    return found.group(1) if found else "on-request"


def signals():
    """Every open DLV condition as {rule, level, artifact, detail, state}; levels come from the Autonomy Profile."""
    loaded = backlog()
    if loaded is None:
        return []
    stories, epics = loaded
    th, levels, times, now = thresholds(), profile_delivery()["signals"], timeline(), moment()
    out = []

    def add(rule, artifact, detail, state="open"):
        level = levels.get(rule)
        if level:
            out.append({"rule": rule, "level": lane_cross_level(level) if rule == "DLV-LANE-CROSS" else level,
                        "artifact": artifact, "detail": detail, "state": state})

    # The signals that do not depend on a declaration: they exist for the project that never declared anything.
    found = noplan_finding(stories, epics)
    if found:
        add("DLV-NO-PLAN", "backlog", noplan_text(found), state=f"{found[0]}/{found[1]}")
    for ident, sha in stale_statuses(stories):
        add("DLV-STALE-STATUS", ident, f"{ident} is still not Done but commit {sha} already closes it: set `Status: Done` and `Closed:` (date and commit)", state=sha)
    pending, dirty = unintegrated(stories)
    if pending and (workflow_commits() != "never"):
        add("DLV-UNINTEGRATED", "git", f"{len(pending)} Stories are Done with no commit or PR in `Closed:` and {dirty} paths are uncommitted: "
            "when you decide to integrate, commit them and put the commit in `Closed:` (Git history is yours; GTT never commits for you)", state=f"{len(pending)}/{dirty}")
    drifted = {}
    for path, number, text in pace_drift():
        drifted.setdefault(path, []).append((number, text))
    for path, rows in drifted.items():
        pace = (read_json(STATE) or {}).get("pace")
        add("DLV-PACE-DRIFT", path, f"the declared pace is `{pace}` but {path} speaks otherwise ({len(rows)} line(s), first {path}:{rows[0][0]}: \"{rows[0][1]}\"): "
            "bring it to the declared pace or change it with `gtt delivery set --pace`", state=str(len(rows)))
    if not active(epics):
        return out
    size = size_report(loaded)
    if size["target"]["state"] == "over":
        add("DLV-OVER-TARGET", "backlog", f"{size['remaining_h']:g} agent h remain, {size['target']['over_pct']}% over the {size['target']['cap_h']:g} h you set as too much: "
            "keep, slim down or change the cap with `gtt delivery review`", state=f"{size['remaining_h']:g}/{size['target']['cap_h']:g}")
    if size["floor"]["state"] == "under":
        add("DLV-UNDER-TARGET", "backlog", f"the plan totals {size['total_h']:g} agent h, under the {size['floor']['min_h']:g} h you set as too little: "
            "keep it, make it fuller or change the minimum with `gtt delivery review`", state=f"{size['total_h']:g}/{size['floor']['min_h']:g}")
    g, base = size["growth"], size["baseline"]
    if g and base and g["stories_added"] >= th["growth_min_stories"] and \
            ((g["stories_pct"] or 0) >= th["growth_pct"] or (g["hours_pct"] or 0) >= th["growth_pct"]):
        add("DLV-GROWTH", "backlog", f"the project grew since {base['at']}: {g['stories_added']:+d} open Stories ({g['stories_pct']:+d}%)"
            + (f", estimated hours {g['hours_pct']:+d}%" if g["hours_pct"] is not None else "")
            + f" (you set the warning at +{th['growth_pct']:g}%): keep it, slim it down or change the answers with `gtt delivery review`",
            state=f"{size['open_stories']}")

    for s in stories:
        row = times.get(s["id"])
        if s["status"] == "In Progress" and s["estimate_h"] and row and row["started"]:
            spent = (now - row["started"]).total_seconds() / 3600.0
            if spent > th["story_over_ratio"] * s["estimate_h"]:
                add("DLV-STORY-OVER", s["id"], f"In Progress for {spent:.1f} h against an estimate of {fmt_h(s['estimate_h'])} "
                    f"(more than {th['story_over_ratio']:g}x): is it bigger than thought, or stuck?")
    for epic in live(epics):
        hours = epic_hours(epic, stories)
        if hours is not None and hours > th["epic_cap_h"] and not budget_decided(epic):
            add("DLV-EPIC-BUDGET", epic["id"], f"{fmt_h(hours)} against a cap of {fmt_h(th['epic_cap_h'])} and no decision in Budget "
                "(accept it, split it, cut it or integrate)")
    plan = build_plan()
    if plan["fits"] is False:
        add("DLV-FORECAST", "delivery-plan", f"forecast finish {plan['eta']} is {plan['late']['late_days']} day(s) after the deadline "
            f"{plan['deadline']}" + (" (uncalibrated)" if plan["calibration"]["uncalibrated"] else ""), state=plan["deadline"])
    for wait in plan["waiting_on_you"]:
        if wait["waiting_h"] > th["human_wait_h"]:
            add("DLV-HUMAN-WAIT", wait["story"], f"an action for you has waited {wait['waiting_h']:.0f} h (more than {th['human_wait_h']:g} h)")
    for a, b, path in conflicts(epics):
        add("DLV-LANE-CROSS", f"{a}+{b}", f"{a} and {b} are on different fronts and both touch `{path}`: declare an interface between them (Depends on) or move one")
    if has_method() and live(epics) and not any(e["kind"] in ("slice", "skeleton") for e in live(epics)):
        add("DLV-NO-VALUE", "backlog", "a development method is declared but no live Epic is `Kind: slice` or `skeleton`: no end-to-end flow delivers value")
    cal = calibration(stories, times)
    if cal["uncalibrated"] and stories:
        add("DLV-UNCALIBRATED", "delivery-plan", f"{cal['measured']} of {cal['needed']} Stories measured: forecasts are estimates taken as given")
    return out


# ------------------------------------------------------------------------------------------------ check

def active(epics=None):
    """True when delivery planning was declared. A project that never did is never obstructed."""
    if os.path.isfile(STATE):
        return True
    if epics is None:
        loaded = backlog()
        epics = loaded[1] if loaded else []
    return any(e["declared"] for e in epics)


def source_findings(limit_days):
    found, today = [], moment().date()
    for path in sorted(glob.glob("gtt-domain/**/*.md", recursive=True)):
        for number, line in enumerate((read(path) or "").splitlines(), 1):
            for url, when in SOURCE.findall(line):
                try:
                    age = (today - datetime.date.fromisoformat(when)).days
                except ValueError:
                    continue
                if age > limit_days:
                    found.append((f"{path}:{number}", f"external source `{url[:60]}` was consulted {when} ({age} days ago, limit {limit_days}): verify it again before the freeze"))
    return found


# ------------------------------------------------------------------------------------------- the size

def take_baseline(loaded=None):
    """The size the plan had when the human declared it: the reference for growth. None while the backlog is too small to measure."""
    loaded = loaded or backlog()
    if loaded is None:
        return None
    stories, epics = loaded
    items = open_stories(stories, epics)
    if len(items) < thresholds()["growth_min_stories"]:
        return None
    report = size_report(loaded, with_baseline=False)
    return {"at": moment().date().isoformat(), "open_stories": len(items), "live_epics": len(live(epics)),
            "remaining_h": report["remaining_h"]}


def pct_change(now, before):
    return None if not before or now is None else round(100.0 * (now - before) / before)


def size_report(loaded=None, with_baseline=True):
    """How big the backlog is, as facts. It judges nothing except against what the human declared (scope_cap_h, growth_pct)."""
    loaded = loaded or backlog()
    if loaded is None:
        return None
    stories, epics = loaded
    th, state = thresholds(), read_json(STATE) or {}
    items, alive = open_stories(stories, epics), live(epics)
    sized_epics = {e["id"] for e in epics if epic_hours(e, stories) is not None}
    sized = [s for s in items if s["estimate_h"] or s["epic"] in sized_epics]
    coverage = len(sized) / len(items) if items else 1.0
    measurable = bool(items) and coverage >= th["noplan_min_coverage"]
    remaining = round(sum(remaining_h(e, stories) for e in alive), 1) if measurable else None
    lanes = state.get("lanes") if isinstance(state.get("lanes"), int) else len({e["lane"] or "main" for e in alive}) or 1
    limit = deadline()
    left = max((limit - moment().date()).days, 0) if limit else None
    capacity = round(left * th["hours_per_day"] * lanes, 1) if left is not None else None
    target, floor = th["scope_cap_h"], th["scope_min_h"]
    total = round(sum(epic_hours(e, stories) or 0 for e in alive), 1) if measurable else None
    out = {"schema": 1, "kind": "gtt-delivery-size", "declared": bool(state), "pace": state.get("pace"), "horizon": state.get("horizon"),
           "deadline": limit.isoformat() if limit else None, "open_stories": len(items), "done_stories": sum(1 for s in stories if s["status"] == "Done"),
           "live_epics": len(alive), "open_epics": len({i["epic"] for i in items}), "coverage_pct": round(100 * coverage), "measurable": measurable, "remaining_h": remaining,
           "days_of_work": math.ceil(remaining / th["hours_per_day"]) if remaining else (0 if remaining == 0 else None),
           "fronts": lanes, "capacity_h": capacity, "of_capacity_pct": round(100 * remaining / capacity) if remaining is not None and capacity else None,
           "target": {"declared": target is not None, "cap_h": target,
                      "state": "none" if target is None else "unknown" if remaining is None else "over" if remaining > target else "within",
                      "over_pct": pct_change(remaining, target) if target and remaining is not None and remaining > target else None},
           "total_h": total,
           "floor": {"declared": floor is not None, "min_h": floor,
                     "state": "none" if floor is None else "unknown" if total is None else "under" if total < floor else "ok"},
           "growth_pct_limit": th["growth_pct"], "baseline": None, "growth": None}
    base = state.get("baseline") if with_baseline else None
    if base:
        out["baseline"] = base
        out["growth"] = {"stories_pct": pct_change(len(items), base.get("open_stories")),
                         "stories_added": len(items) - base.get("open_stories", 0),
                         "hours_pct": pct_change(remaining, base.get("remaining_h"))}
    return out


def cmd_tell(args):
    """What the human must hear about the size, one line each, for the agent to say once at the start of a session. Silent when nothing is open."""
    if backlog() is None:
        return 0
    for s in signals():
        if s["rule"] in TELL:
            print(f"{s['rule']}: {s['detail']}")
    return 0


def cmd_size(args):
    report = size_report()
    if report is None:
        die("there is no backlog yet (gtt-domain/backlog.md)")
    lang = args.lang or "en"
    spec = contract()["review"]
    report["choices"] = [{"id": c["id"], "label": c["label"][lang]} for c in spec["choices"]]
    report["slim_note"] = spec["slim_note"][lang]
    report["expand_note"] = spec["expand_note"][lang]
    report["pace_values"] = contract()["pace"]["values"]
    report["prompts"] = {k: v[lang] for k, v in spec["prompts"].items()}
    if args.json:
        emit(report)
        return 0
    r = report
    print(f"size: {r['open_stories']} open Stories in {r['open_epics']} of {r['live_epics']} live Epics, {r['done_stories']} Done")
    if r["measurable"]:
        print(f"  remaining: {r['remaining_h']:g} agent h (~{r['days_of_work']} day(s) of work on one front); {r['coverage_pct']}% of the open Stories have a duration")
    else:
        print(f"  remaining: NOT MEASURABLE - only {r['coverage_pct']}% of the open Stories have a duration; add `Estimate:` to the Epics")
    if r["capacity_h"] is not None:
        print(f"  until the deadline {r['deadline']}: {r['capacity_h']:g} agent h of capacity on {r['fronts']} front(s)"
              + (f"; the remaining work is {r['of_capacity_pct']}% of it" if r["of_capacity_pct"] is not None else ""))
    t = r["target"]
    print("  your cap: " + (f"{t['cap_h']:g} h - " + {"within": "within", "over": f"OVER by {t['over_pct']}%", "unknown": "cannot be compared (not measurable)"}[t["state"]]
                            if t["declared"] else "none declared (you decide what is too much: gtt delivery set --scope-cap <hours>)"))
    f = r["floor"]
    if f["declared"]:
        print(f"  your minimum: {f['min_h']:g} h - " + {"ok": "reached", "under": f"UNDER it (the plan totals {r['total_h']:g} h)", "unknown": "cannot be compared (not measurable)"}[f["state"]])
    if r["growth"]:
        g = r["growth"]
        print(f"  since {r['baseline']['at']}: {g['stories_added']:+d} open Stories ({g['stories_pct']:+d}%)"
              + (f", hours {g['hours_pct']:+d}%" if g["hours_pct"] is not None else "") + f"; GTT warns at +{r['growth_pct_limit']:g}%")
    elif r["declared"]:
        print("  reference size: not taken yet (needs "
              f"{thresholds()['growth_min_stories']} open Stories when you declare; take it now with `gtt delivery set --rebase`)")
    return 0


VISIBILITY = ("DLV-NO-PLAN", "DLV-STALE-STATUS", "DLV-PACE-DRIFT", "DLV-UNINTEGRATED", "DLV-GROWTH", "DLV-OVER-TARGET", "DLV-UNDER-TARGET")
TELL = ("DLV-NO-PLAN", "DLV-UNINTEGRATED", "DLV-GROWTH", "DLV-OVER-TARGET", "DLV-UNDER-TARGET")


def visibility_warnings():
    """The signals that need no declaration, as check findings. They warn and never fail: the project may not have chosen planning."""
    return [("WARN", s["artifact"], f"{s['rule']}: {s['detail']}") for s in signals() if s["rule"] in VISIBILITY]


def check_all():
    """[(level, where, message)] - level is FAIL or WARN according to the Autonomy Profile."""
    loaded = backlog()
    if loaded is None:
        return [], False
    if not active(loaded[1]):
        return visibility_warnings(), False
    stories, epics = loaded
    th, freeze, found = thresholds(), profile_delivery()["freeze"], []

    def add(kind, where, message):
        found.append(("FAIL" if freeze.get(kind, "warn") == "fail" else "WARN", where, message))

    items = live(epics)
    multi = len({e["lane"] or "main" for e in items}) > 1
    for epic in items:
        where = f"{BACKLOG}:{epic['line']}"
        hours = epic_hours(epic, stories)
        if epic["status"] in ("Planned", "In Progress") and hours is None:
            add("estimate", where, f"{epic['id']} is {epic['status']} without an `Estimate:` (agent hours, e.g. `6h + 2 decisions`)")
        if hours is not None and hours > th["epic_cap_h"] and not budget_decided(epic):
            add("budget", where, f"{epic['id']} is {fmt_h(hours)}, over the {fmt_h(th['epic_cap_h'])} cap, and `Budget:` holds no decision "
                f"(`over - accepted: <reason> - <who> - <YYYY-MM-DD>`, or `over - split | cut | integrate`)")
        if multi and (not epic["lane"] or not epic["touches"]):
            add("lanes", where, f"{epic['id']} needs `Lane:` and `Touches:` because the plan has more than one front")
        build = BUILD_INTEGRATE.match(epic["build"].strip().strip("`"))
        if epic["build"].lower().startswith("integrate"):
            if not build:
                add("build", where, f"{epic['id']} `Build:` must read `integrate (ADR-NNN)`")
            elif not glob.glob(f"gtt-domain/adr/{build.group(1)}*.md") and not glob.glob(f"gtt-domain/proposals/*{build.group(1)}*"):
                add("build", where, f"{epic['id']} integrates a service under {build.group(1)}, which does not exist: buying is an architecture decision (needs an ADR)")
    if multi:
        for a, b, path in conflicts(epics):
            add("lanes", BACKLOG, f"{a} and {b} are on different fronts and both touch `{path}`: declare the interface (Depends on) or move one")
    for where, message in source_findings(th["source_max_age_days"]):
        add("source", where, message)
    return found + visibility_warnings(), True


def cmd_check(args):
    found, declared = check_all()
    failed = any(level == "FAIL" for level, _, _ in found)
    if args.json:
        emit({"schema": 1, "kind": "gtt-delivery-check", "result": "fail" if failed else "pass", "pre_freeze": args.pre_freeze,
              "declared": declared, "profile": profile_name(), "findings": [{"level": l, "where": w, "message": m} for l, w, m in found]})
        return 1 if failed else 0
    for level, where, message in found:
        print(f"{level}  {where}: {message}", file=sys.stderr if level == "FAIL" else sys.stdout)
    if not failed:
        print("gtt-delivery: OK - " + ("delivery plan checked." if declared else "no delivery planning declared."))
    return 1 if failed else 0


# ------------------------------------------------------------------------------- questions and answers

def cmd_questions(args):
    spec, lang = contract(), args.lang or "en"
    rows = []
    for q in spec["questions"]:
        rows.append({"id": q["id"], "key": q["key"], "asked_by": q["asked_by"], "only_if": q.get("only_if"),
                     "prompt": q["prompt"][lang], "note": (q.get("note") or {}).get(lang),
                     "options": [{"id": o["id"], "label": o["label"][lang], "recommended": bool(o.get("recommended")), "days": o.get("days")}
                                 for o in q["options"]]})
    if args.json:
        emit({"schema": 1, "kind": "gtt-delivery-questions", "questions": rows, "thresholds": spec["thresholds"]})
        return 0
    for q in rows:
        print(f"{q['id']} {q['prompt']}")
        for number, o in enumerate(q["options"], 1):
            print(f"  {number}. {o['label']}" + (" (recommended)" if o["recommended"] else ""))
    return 0


def current_state():
    return read_json(STATE)


def cmd_select(args):
    spec, previous = contract(), current_state() or {}
    data = dict(previous)
    checks = (("who", args.who, WHO), ("horizon", args.horizon, HORIZONS), ("priority", args.priority, PRIORITY),
              ("third_party", args.third_party, THIRD))
    if all(v is None for _, v, _ in checks) and args.lanes is None and args.epic_cap is None and args.team is None \
            and args.restrictions is None and args.pace is None \
            and args.preset is None and args.scope_cap is None and args.scope_min is None and args.growth_pct is None and not args.rebase:
        die("give at least one of --who, --lanes, --horizon, --pace, --preset, --priority, --third-party, --restrictions, --epic-cap, --team, --scope-cap, --scope-min, --growth-pct, --rebase")
    for key, value, allowed in checks:
        if value is not None:
            if value not in allowed:
                print(f"gtt-delivery: REFUSED - --{key.replace('_', '-')} must be one of {', '.join(allowed)}. Nothing was written.", file=sys.stderr)
                return 1
            data[key] = value
    if args.preset is not None:
        preset = contract().get("presets", {}).get(args.preset)
        if not preset:
            print(f"gtt-delivery: REFUSED - --preset must be one of {', '.join(contract().get('presets', {}))}. Nothing was written.", file=sys.stderr)
            return 1
        args.horizon, args.pace = args.horizon or preset["horizon"], args.pace or preset["pace"]
        data["horizon"], data["preset"] = args.horizon, args.preset
    if args.scope_cap is not None:
        if args.scope_cap == "none":
            data.pop("scope_cap_h", None)
        else:
            try:
                value = float(args.scope_cap)
            except ValueError:
                value = 0
            if value <= 0:
                print("gtt-delivery: REFUSED - --scope-cap must be a positive number of agent hours, or `none`. Nothing was written.", file=sys.stderr)
                return 1
            data["scope_cap_h"] = value
    if args.scope_min is not None:
        if args.scope_min == "none":
            data.pop("scope_min_h", None)
        else:
            try:
                value = float(args.scope_min)
            except ValueError:
                value = 0
            if value <= 0:
                print("gtt-delivery: REFUSED - --scope-min must be a positive number of agent hours, or `none`. Nothing was written.", file=sys.stderr)
                return 1
            data["scope_min_h"] = value
    if args.growth_pct is not None:
        try:
            value = float(args.growth_pct)
        except ValueError:
            value = 0
        if value <= 0:
            print("gtt-delivery: REFUSED - --growth-pct must be a positive percentage. Nothing was written.", file=sys.stderr)
            return 1
        data["growth_pct"] = value
    if args.pace is not None:
        if args.pace not in PACES:
            print(f"gtt-delivery: REFUSED - --pace must be one of {', '.join(PACES)}. Nothing was written.", file=sys.stderr)
            return 1
        data["pace"] = args.pace
    if args.lanes is not None:
        if args.lanes != "propose" and not (args.lanes.isdigit() and 1 <= int(args.lanes) <= 12):
            print("gtt-delivery: REFUSED - --lanes must be a number from 1 to 12 or `propose`. Nothing was written.", file=sys.stderr)
            return 1
        data["lanes"] = args.lanes if args.lanes == "propose" else int(args.lanes)
    if args.epic_cap is not None:
        if args.epic_cap <= 0:
            print("gtt-delivery: REFUSED - --epic-cap must be a positive number of hours. Nothing was written.", file=sys.stderr)
            return 1
        data["epic_cap_h"] = args.epic_cap
    if args.team is not None:
        data["team"] = [n.strip() for n in args.team.split(",") if n.strip()]
    if args.restrictions is not None:
        data["restrictions"] = args.restrictions.strip()
    if args.horizon is not None:
        days = next((o.get("days") for q in spec["questions"] if q["key"] == "horizon" for o in q["options"] if o["id"] == args.horizon), None)
        data["deadline"] = (moment().date() + datetime.timedelta(days=days)).isoformat() if days else None
        data["horizon_set_at"] = moment().date().isoformat()
    for key, default in (("who", OPEN), ("horizon", OPEN), ("priority", OPEN), ("third_party", OPEN), ("lanes", OPEN)):
        data.setdefault(key, default)
    if data.get("who") == "solo":
        data["lanes"] = 1
    if data.get("who") == "team" and not data.get("team"):
        print("gtt-delivery: NOTE - a team needs the names of its members (--team ana,luis): they own the fronts.")
    shown = ", ".join(f"{k} {data[k]}" for k in ("who", "lanes", "horizon", "pace", "priority", "third_party") if k in data)
    print(f"delivery (setup answer): {shown}" + (f"; deadline {data['deadline']}" if data.get("deadline") else "")
          + (f"; Epic cap {data['epic_cap_h']:g} h" if data.get("epic_cap_h") else "")
          + (f"; scope cap {data['scope_cap_h']:g} h" if data.get("scope_cap_h") else "")
          + (f"; scope minimum {data['scope_min_h']:g} h" if data.get("scope_min_h") else ""))
    if OPEN in (data.get("who"), data.get("horizon")):
        print("  OPEN: nothing is invented. The plan shows it as OPEN and the agent asks again at the next natural moment.")
    print("  an operating answer, never architecture: it can change at any time with `gtt delivery set`.")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    if args.rebase or not data.get("baseline"):
        taken = take_baseline()
        if taken:
            data["baseline"] = taken
        elif args.rebase:
            print("gtt-delivery: NOTE - the backlog holds fewer than "
                  f"{thresholds()['growth_min_stories']} open Stories: no reference size taken yet.")
    data.update({"schema": 1, "answered_by": args.by or previous.get("answered_by") or "unspecified", "answered_at": stamp(),
                 "authority": "none - an operating answer, never architecture"})
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"gtt-delivery: written {STATE}")
    return 0


def cmd_get(args):
    state, th = current_state(), thresholds()
    out = {"schema": 1, "kind": "gtt-delivery-state", "declared": state is not None, "state": state, "thresholds": th,
           "profile": profile_name(), "levels": profile_delivery()}
    if args.json:
        emit(out)
        return 0
    if state is None:
        print("delivery: not declared yet (gtt delivery set ...)")
        return 0
    print(f"delivery: who {state.get('who', OPEN)}, fronts {state.get('lanes', OPEN)}, horizon {state.get('horizon', OPEN)}"
          + (f" (deadline {state['deadline']})" if state.get("deadline") else "") + f", pace {state.get('pace', 'undeclared')}" + f", Epic cap {th['epic_cap_h']:g} h")
    return 0


def cmd_summary(args):
    """The `## Delivery` block of session.md. Stable between runs: no clock readings finer than a day."""
    state, loaded = current_state(), backlog()
    if state is None and not (loaded and active(loaded[1])):
        print("not declared (no .gtt/delivery.json; gtt delivery set ...)")
        for s in (signals() if loaded else []):
            print(f"signal: {s['rule']} {s['artifact']} - {s['detail']}")
        return 0
    if loaded is None:
        print("declared; no backlog yet")
        return 0
    stories, epics = loaded
    plan = build_plan()
    state = state or {}
    print(f"who {state.get('who', OPEN)}; fronts {state.get('lanes', OPEN)}; "
          + (f"deadline {plan['deadline']}" if plan["deadline"] else f"horizon {state.get('horizon', OPEN)}")
          + f"; pace {state.get('pace', 'UNDECLARED (gtt delivery set --pace days|flow)')}"
          + ("; UNCALIBRATED" if plan["calibration"]["uncalibrated"] else f"; calibrated x{plan['calibration']['ratio']}"))
    if plan["eta"] and plan["chain"]:
        print(f"forecast: {plan['chain_hours']:g} agent h on the longest chain ({' -> '.join(plan['chain'])}), finish {plan['eta']}"
              + ("" if plan["fits"] is None else ", fits the deadline" if plan["fits"] else f", DOES NOT FIT ({plan['late']['late_days']} day(s) late)"))
    for epic in live(epics):
        fraction, _ = progress(epic, stories)
        print(f"- {epic['id']} [{epic['lane'] or 'main'}] {round(fraction * 100)}%" + (f" est {fmt_h(epic_hours(epic, stories))}" if epic_hours(epic, stories) is not None else " no estimate"))
    for wait in plan["waiting_on_you"]:
        print(f"waiting on you: {wait['story']}")
    size = size_report(loaded)
    print(f"size: {size['open_stories']} open Stories, " + (f"{size['remaining_h']:g} h remain (~{size['days_of_work']} day(s) of work)" if size["measurable"] else "hours not measurable (no Estimate)")
          + (f"; cap {size['target']['cap_h']:g} h {size['target']['state']}" if size["target"]["declared"] else "; no cap declared")
          + (f"; minimum {size['floor']['min_h']:g} h {size['floor']['state']}" if size["floor"]["declared"] else "")
          + (f"; {size['growth']['stories_added']:+d} Stories since {size['baseline']['at']}" if size["growth"] else ""))
    open_signals = signals()
    if open_signals:
        print("signals: " + "; ".join(f"{s['rule']} {s['artifact']}" for s in open_signals if s["rule"] != "DLV-UNCALIBRATED") or "none")
    return 0


def main(argv):
    if not os.path.isdir(".gtt"):
        die("run from the project root (no .gtt/ directory here)")
    parser = argparse.ArgumentParser(prog="gtt_delivery.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("questions"); p.add_argument("--lang", choices=("es", "en")); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_questions)
    p = sub.add_parser("select"); p.add_argument("--who"); p.add_argument("--lanes"); p.add_argument("--horizon"); p.add_argument("--priority")
    p.add_argument("--third-party", dest="third_party"); p.add_argument("--restrictions"); p.add_argument("--epic-cap", dest="epic_cap", type=float)
    p.add_argument("--team"); p.add_argument("--pace"); p.add_argument("--preset"); p.add_argument("--scope-cap", dest="scope_cap"); p.add_argument("--scope-min", dest="scope_min")
    p.add_argument("--growth-pct", dest="growth_pct"); p.add_argument("--rebase", action="store_true"); p.add_argument("--by"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_select)
    p = sub.add_parser("get"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_get)
    p = sub.add_parser("plan"); p.add_argument("--lanes", action="store_true"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_plan)
    p = sub.add_parser("tell"); p.set_defaults(func=cmd_tell)
    p = sub.add_parser("size"); p.add_argument("--lang", choices=("es", "en")); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_size)
    p = sub.add_parser("report"); p.add_argument("--epic"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_report)
    p = sub.add_parser("check"); p.add_argument("--pre-freeze", action="store_true"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_check)
    p = sub.add_parser("log"); p.set_defaults(func=cmd_log)
    p = sub.add_parser("summary"); p.set_defaults(func=cmd_summary)
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
