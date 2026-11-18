#!/usr/bin/env python3
"""GTT - activity: what the agent does, as a fixed-size journal in `.gtt/local/activity.jsonl`.

  gtt_activity.py log [--ade ADE]        a PostToolUse hook: reads the tool event on stdin, writes one line, prints nothing
  gtt_activity.py sample                 one sample of the working tree (`git status --porcelain`): what changed, unattributed
  gtt_activity.py now [--json]           what is going on: the Story in progress, its active hours, the last files, how long ago
  gtt_activity.py hours STORY [--json]   the active hours of a Story

One line per action: {t, actor, ade, source, tool, path, stories}. It never keeps content or arguments: a shell command keeps its first
word only, because the rest can carry keys. The journal lives outside git, keeps the last 1000 lines and is written only here (the agent
cannot edit it: it is protected like `delivery-log.jsonl`). Human acts of the CLI and of Sonar add {t, actor: "human", via, op, ref}.

Where the data comes from is always said: `hook` (the agent, attributed), `sample` (the working tree, unattributed) or `inferred`
(a change inside the `Touches` of one Epic: marked as inferred, never as fact). Exit 0 always: a broken hook must never stop a tool call.
"""
import datetime
import json
import os
import re
import subprocess
import sys

JOURNAL = ".gtt/local/activity.jsonl"
STATE = ".gtt/local/activity-state.json"
MAX_LINES = 1000
PAUSE_S = 15 * 60            # a gap longer than this is a pause: it does not count as active time
EDIT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "write", "edit", "create", "replace", "patch", "fs_write", "str_replace")
CODE_SKIP = ("gtt-domain/", ".gtt/", ".claude/", ".kiro/", ".cursor/", ".openhands/", ".agents/", ".github/hooks", "docs/", ".git/")


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(moment=None):
    return (moment or now_utc()).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(value):
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def in_progress():
    """The Stories In Progress right now: what the journal sticks to every action."""
    try:
        import gtt_backlog
        stories, _ = gtt_backlog.parse(gtt_backlog.DEFAULT)
        return [s["id"] for s in stories if gtt_backlog.normal(s["status"]) == "In Progress"]
    except (Exception, SystemExit):
        return []


def rows():
    out = []
    try:
        with open(JOURNAL, encoding="utf-8") as handle:
            for line in handle:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def write(entry):
    """Appends one line and keeps the last MAX_LINES. Never raises."""
    try:
        os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
        with open(JOURNAL, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        if os.path.getsize(JOURNAL) > MAX_LINES * 90:
            lines = open(JOURNAL, encoding="utf-8").read().splitlines()
            if len(lines) > MAX_LINES:
                tmp = JOURNAL + ".tmp"
                with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("\n".join(lines[-MAX_LINES:]) + "\n")
                os.replace(tmp, JOURNAL)
    except OSError:
        pass


def human(via, op, ref=None):
    """A human act (the CLI or Sonar): who did what, never its content."""
    write({"t": stamp(), "actor": "human", "via": via, "op": op, "ref": ref})


def relative(path):
    path = str(path or "").replace("\\", "/")
    root = os.getcwd().replace("\\", "/").rstrip("/") + "/"
    return path[len(root):] if path.startswith(root) else path.lstrip("./") if path.startswith("./") else path


def first_word(command):
    word = str(command or "").strip().split(None, 1)
    return os.path.basename(word[0]) if word else None


def is_code(path):
    return bool(path) and not any(path.startswith(p) for p in CODE_SKIP)


# -------------------------------------------------------------------------------------------------------- the hook

def cmd_log(args):
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        event = {}
    tool = str(event.get("tool_name") or event.get("toolName") or event.get("tool") or "")
    data = event.get("tool_input") or event.get("toolInput") or {}
    path = relative(data.get("file_path") or data.get("path") or data.get("filePath") or "") or None
    if tool in ("Bash", "PowerShell", "shell", "execute_bash", "runCommand"):
        path, tool = None, first_word(data.get("command")) or tool
    stories = in_progress()
    write({"t": stamp(), "actor": "agent", "ade": args.ade, "source": "hook", "tool": tool or None, "path": path, "stories": stories})
    notice(event, stories, path)
    return 0


def notice(event, stories, path):
    """DEF-WORK-NO-STORY, heard once per session in one line: code changing for 15 minutes with no Story In Progress."""
    try:
        if stories or not is_code(path or ""):
            return
        started = work_without_story()
        if started is None:
            return
        session = str(event.get("session_id") or event.get("sessionId") or "-")
        state = read_json(STATE) or {}
        if state.get("warned") == session:
            return
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, "w", encoding="utf-8") as handle:
            json.dump({"warned": session}, handle)
        language = (read_json(".gtt/methodology.json") or {}).get("language")
        line = ("@gtt · Hay código cambiando hace más de 15 min sin ninguna historia En curso: marca la historia que construyes como `In Progress` antes de seguir."
                if language == "es" else
                "@gtt · Code has been changing for over 15 min with no Story In Progress: mark the Story you are building `In Progress` before going on.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": line}}))
    except Exception:
        pass


# ------------------------------------------------------------------------------------------------------- sampling

def porcelain():
    try:
        out = subprocess.run(["git", "status", "--porcelain", "-uall"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    result = {}
    for line in out.stdout.splitlines():
        if len(line) > 3:
            name = line[3:].split(" -> ")[-1].strip().strip('"')
            try:
                result[name] = os.stat(name).st_mtime_ns
            except OSError:
                result[name] = 0
    return result


def sample(previous=None):
    """The files that changed since the last sample and that the hook did not just record. Returns the new picture of the tree."""
    tree = porcelain()
    if tree is None or previous is None:
        return tree
    seen = {r.get("path") for r in rows()[-50:] if r.get("source") == "hook" and r.get("t") and (now_utc() - (parse(r["t"]) or now_utc())).total_seconds() < 30}
    stories = None
    for name, mtime in tree.items():
        if previous.get(name) != mtime and name not in seen and not name.startswith(".gtt/local/"):
            stories = in_progress() if stories is None else stories
            write({"t": stamp(), "actor": None, "ade": None, "source": "sample", "tool": None, "path": name, "stories": stories})
    return tree


def cmd_sample(_args):
    sample(previous=porcelain())
    return 0


# ------------------------------------------------------------------------------------------------------- reading

def span_hours(entries, start=None, end=None):
    """Active hours of a list of entries in time order: the sum of the gaps between consecutive ones that are not pauses."""
    times = sorted(t for t in (parse(e.get("t")) for e in entries) if t and (start is None or t >= start) and (end is None or t <= end))
    total = 0.0
    for before, after in zip(times, times[1:]):
        gap = (after - before).total_seconds()
        if gap <= PAUSE_S:
            total += gap
    return round(total / 3600.0, 2)


def active_hours(story, start=None, end=None):
    """Hours of real work on a Story: the sum of the intervals between actions that name it, without the pauses. None without a journal of it."""
    mine = [r for r in rows() if story in (r.get("stories") or []) and r.get("actor") != "human"]
    if not mine:
        return None
    return span_hours(mine, start, end)


def work_without_story():
    """When the code started changing with no Story In Progress, if it has gone on for 15 minutes without a pause; else None."""
    chain = []
    for r in reversed(rows()):
        if r.get("actor") == "human" or not is_code(r.get("path") or ""):
            continue
        if r.get("stories"):
            break
        t = parse(r.get("t"))
        if t is None:
            continue
        if chain and (chain[-1] - t).total_seconds() > PAUSE_S:
            break
        chain.append(t)
    if len(chain) >= 2 and (chain[0] - chain[-1]).total_seconds() >= 15 * 60:
        return chain[-1]
    return None


def probable_story(paths):
    """The Epic whose `Touches` hold every path: the changes belong 'probably' to it. None when none or more than one does. Inferred, never fact."""
    try:
        import gtt_backlog
        _stories, epics = gtt_backlog.parse(gtt_backlog.DEFAULT)
    except (Exception, SystemExit):
        return None
    owners = set()
    for path in paths:
        hit = {e["id"] for e in epics if e.get("status") in ("In Progress", "Planned") and any(
            path.startswith(t.strip().strip("`").rstrip("*").rstrip("/")) for t in re.split(r"[,;]", e["fields"].get("Touches", "")) if t.strip())}
        owners |= hit
    return next(iter(owners)) if len(owners) == 1 else None


def now_state():
    """What goes on now, for the page: the Story in progress, since when, active hours against the estimate, the last 5 files, how long ago and from where."""
    entries = [r for r in rows() if r.get("actor") != "human"]
    last = entries[-1] if entries else None
    running = in_progress()
    out = {"story": running[0] if running else None, "stories": running, "since": None, "active_h": None, "estimate_h": None, "files": [], "last_t": None,
           "last_source": None, "source": None, "probable": None, "attributed": None}
    try:
        import gtt_delivery as dl
        stories, _ = dl.backlog()
        times = dl.timeline()
        if running:
            row = times.get(running[0]) or {}
            out["since"] = stamp(row["started"]) if row.get("started") else None
            out["estimate_h"] = next((s["estimate_h"] for s in stories if s["id"] == running[0]), None)
            out["active_h"] = active_hours(running[0], row.get("started"))
    except (Exception, SystemExit):
        pass
    since = parse(out["since"]) if out["since"] else None
    paths = []
    for r in reversed(entries):
        if r.get("path") and r["path"] not in paths and (since is None or (parse(r.get("t")) or since) >= since):
            paths.append(r["path"])
        if len(paths) >= 5:
            break
    out["files"] = paths
    if last:
        out["last_t"], out["last_source"] = last.get("t"), last.get("source")
        out["attributed"] = last.get("actor") == "agent"
        out["source"] = "claude" if last.get("actor") == "agent" and (last.get("ade") or "claude") == "claude" else (last.get("ade") if last.get("actor") == "agent" else "unattributed")
    if not running and paths:
        out["probable"] = probable_story([p for p in paths if is_code(p)])
    return out


def cmd_now(args):
    data = now_state()
    print(json.dumps(data, indent=2, ensure_ascii=False) if args.json else json.dumps(data, ensure_ascii=False))
    return 0


def cmd_hours(args):
    value = active_hours(args.story)
    print(json.dumps({"story": args.story, "active_h": value}) if args.json else (value if value is not None else "no journal"))
    return 0


def findings():
    """DEF-WORK-NO-STORY: code has been changing for more than 15 minutes (WARNING at 30) with no Story In Progress."""
    import gtt_findings as gf
    started = work_without_story()
    if started is None or in_progress():
        return []
    minutes = int((now_utc() - started).total_seconds() / 60)
    last = next((r for r in reversed(rows()) if r.get("actor") != "human" and is_code(r.get("path") or "")), {})
    likely = probable_story([r["path"] for r in rows()[-20:] if r.get("path") and is_code(r["path"])])
    hint = (f" (probably {likely}, inferred)" if gf.language() == "en" else f" (probablemente {likely}, inferido)") if likely else ""
    return [gf.make("DEF-WORK-NO-STORY", "work", JOURNAL, "gtt_activity", level="WARNING" if minutes >= 30 else "NOTICE", minutes=minutes, probable=hint)]


def main(argv):
    import argparse
    parser = argparse.ArgumentParser(prog="gtt_activity.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    one = sub.add_parser("log")
    one.add_argument("--ade", default="claude")
    sub.add_parser("sample")
    two = sub.add_parser("now")
    two.add_argument("--json", action="store_true")
    three = sub.add_parser("hours")
    three.add_argument("story")
    three.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        return {"log": cmd_log, "sample": cmd_sample, "now": cmd_now, "hours": cmd_hours}[args.cmd](args)
    except Exception:
        return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv[1:]))
