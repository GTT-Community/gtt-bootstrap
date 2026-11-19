#!/usr/bin/env python3
"""GTT - keep the disk from filling when agents work in parallel.

  gtt_disk.py check  [--json]                     one line when all is well, the findings when not; always exit 0
  gtt_disk.py status [--json]                     the limits in force and where they come from
  gtt_disk.py prune  [PATH...] [--apply] [--idle MINUTES]
                                                  remove work copies (Git worktrees) that are merged and clean
  gtt_disk.py set    [--max-copies N] [--max-gb N] [--min-free-gb N] [--off] [--default] [--apply]
                                                  change the limits on this machine: the human's act

The rule is data (.gtt/contract/disk.json): at most 3 work copies at a time, work copies and ADE folders under 15 GB,
at least 10 GB free. It is the same for every ADE because it asks Git, not the ADE, where the work copies are
(`git worktree list`). A person may change it with `set`, which writes .gtt/local/disk.json on this machine only,
warns, and recommends keeping the default; an agent never changes it.

`check` never blocks: it is advice with numbers, for an agent to read before it creates a work copy or launches agents
in parallel. `prune` removes only a work copy that is merged into the base branch, has nothing uncommitted, is not locked,
is not the folder you stand in and, when no path is named, has been idle for 30 minutes; it never forces. Without --apply
it is a dry run.

Exit 0 = ok (a check never fails because of what it finds), 1 = refused, 2 = cannot run.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

CONTRACT = ".gtt/contract/disk.json"
ADE_DIRS = (".claude", ".cursor", ".kiro", ".agents", ".openhands")
GB = 1024 * 1024 * 1024
DU_TIMEOUT = 180
IDLE_MINUTES = 30


# --- the contract and the person's setting -------------------------------------------------------------------

def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def load_contract(root):
    for base in (root, os.getcwd(), os.path.dirname(os.path.dirname(HERE))):
        data = read_json(os.path.join(base, CONTRACT))
        if data:
            return data
    print(f"gtt-disk: {CONTRACT} is missing or unreadable; this Bootstrap does not carry the disk rule.", file=sys.stderr)
    sys.exit(2)


def language(root):
    data = read_json(os.path.join(root, ".gtt", "methodology.json")) or {}
    return data.get("language") if data.get("language") in ("en", "es") else "en"


class Say:
    def __init__(self, contract, lang):
        self.table = contract["messages"].get(lang) or contract["messages"]["en"]
        self.fallback = contract["messages"]["en"]

    def __call__(self, key, **values):
        text = self.table.get(key) or self.fallback.get(key) or key
        try:
            return text.format(**values)
        except (KeyError, IndexError):
            return text


def whole(value, bounds):
    return isinstance(value, int) and not isinstance(value, bool) and bounds[0] <= value <= bounds[1]


def policy(root, contract):
    """The limits in force: the default rule, or what a person set on this machine (never what an agent wrote)."""
    limits = dict(contract["defaults"])
    state = read_json(os.path.join(root, contract["state"]))
    out = {"enabled": True, "source": "default", **limits}
    if not state:
        return out
    if state.get("mode") == "off":
        out["enabled"] = False
        out["source"] = "custom"
        return out
    custom = False
    for name, bounds in contract["bounds"].items():
        if name in state and whole(state[name], bounds):
            out[name] = state[name]
            custom = custom or state[name] != limits[name]
    out["source"] = "custom" if custom else "default"
    return out


# --- Git -----------------------------------------------------------------------------------------------------

def git(args, cwd=None, timeout=60):
    try:
        done = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def worktrees(cwd):
    """Every worktree Git knows, the main checkout first: [{path, head, branch, locked, prunable}]."""
    out = git(["worktree", "list", "--porcelain"], cwd=cwd)
    if out is None:
        return []
    rows, row = [], None
    for line in out.splitlines() + [""]:
        if not line.strip():
            if row:
                rows.append(row)
            row = None
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            row = {"path": os.path.realpath(value), "head": "", "branch": "", "locked": False, "prunable": False}
        elif row is not None:
            if key == "HEAD":
                row["head"] = value
            elif key == "branch":
                row["branch"] = value[len("refs/heads/"):] if value.startswith("refs/heads/") else value
            elif key == "locked":
                row["locked"] = True
            elif key == "prunable":
                row["prunable"] = True
    return rows


def base_branch(main):
    """The branch the work copies are merged into: the main checkout's own branch, else main or master."""
    if main["branch"]:
        return main["branch"]
    for name in ("main", "master"):
        if git(["rev-parse", "--verify", "--quiet", f"refs/heads/{name}"], cwd=main["path"]) is not None:
            return name
    return None


def clean(path):
    out = git(["--no-optional-locks", "status", "--porcelain"], cwd=path)
    return out is not None and not out.strip()


def merged(path, head, base):
    if not base or not head:
        return False
    try:
        done = subprocess.run(["git", "merge-base", "--is-ancestor", head, base], cwd=path, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def idle_minutes(path):
    """Minutes since this work copy's Git state last moved: its index, its HEAD and its reflog."""
    gitdir = git(["rev-parse", "--absolute-git-dir"], cwd=path)
    if not gitdir:
        return 0.0
    gitdir = gitdir.strip()
    newest = 0.0
    for name in ("index", "HEAD", os.path.join("logs", "HEAD")):
        try:
            newest = max(newest, os.stat(os.path.join(gitdir, name)).st_mtime)
        except OSError:
            continue
    return (time.time() - newest) / 60.0 if newest else 0.0


# --- sizes ---------------------------------------------------------------------------------------------------

def contained(path, parent):
    return path == parent or path.startswith(parent.rstrip(os.sep) + os.sep)


def top_level(paths):
    """The paths that are not inside another of the paths: a folder is counted once."""
    unique = sorted(set(paths), key=lambda p: (len(p), p))
    keep = []
    for path in unique:
        if not any(contained(path, other) for other in keep):
            keep.append(path)
    return keep


def walk_kb(paths):
    seen, total = set(), 0
    for top in paths:
        for here, dirs, files in os.walk(top, followlinks=False):
            for name in files + dirs:
                try:
                    info = os.lstat(os.path.join(here, name))
                except OSError:
                    continue
                if info.st_nlink > 1:
                    key = (info.st_dev, info.st_ino)
                    if key in seen:
                        continue
                    seen.add(key)
                total += getattr(info, "st_blocks", 0) * 512 // 1024 or info.st_size // 1024
    return total


def size_kb(paths):
    """Kilobytes the paths really occupy (a hard link counts once). None when it cannot be measured."""
    paths = [p for p in paths if os.path.isdir(p)]
    if not paths:
        return 0
    if shutil.which("du"):
        try:
            done = subprocess.run(["du", "-sk", "--"] + paths, capture_output=True, text=True, timeout=DU_TIMEOUT)
        except (OSError, subprocess.SubprocessError):
            return None
        total = 0
        for line in done.stdout.splitlines():
            head = line.split("\t", 1)[0].strip()
            if head.isdigit():
                total += int(head)
        return total
    try:
        return walk_kb(paths)
    except OSError:
        return None


def gb(kb):
    return round((kb or 0) / (1024 * 1024), 1)


# --- what does not belong in a work copy ---------------------------------------------------------------------

def strays(path, rule):
    found = []
    dirs_named = set(rule["dirs"])
    exts = tuple(rule["extensions"])
    depth0 = path.rstrip(os.sep).count(os.sep)
    for here, dirs, files in os.walk(path):
        if here.count(os.sep) - depth0 >= rule["max_depth"]:
            dirs[:] = []
        keep = []
        for name in dirs:
            if name in ("node_modules", ".git"):
                continue
            if name in dirs_named:
                found.append(os.path.join(here, name))
                continue
            keep.append(name)
        dirs[:] = keep
        for name in files:
            if name.lower().endswith(exts):
                found.append(os.path.join(here, name))
    return found


def pnpm_store_elsewhere(root):
    if not os.path.exists(os.path.join(root, "pnpm-lock.yaml")) or not shutil.which("pnpm"):
        return None
    try:
        done = subprocess.run(["pnpm", "store", "path"], cwd=root, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    store = done.stdout.strip().splitlines()[-1].strip() if done.returncode == 0 and done.stdout.strip() else ""
    if not store:
        return None
    probe = store
    while probe and not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        probe = parent
    try:
        return store if os.stat(probe).st_dev != os.stat(root).st_dev else None
    except OSError:
        return None


# --- check ---------------------------------------------------------------------------------------------------

def analyse(root, contract, limits, trees):
    main, linked = trees[0], trees[1:]
    base = base_branch(main)
    folders = [t["path"] for t in linked] + [os.path.join(main["path"], d) for d in ADE_DIRS
                                              if os.path.isdir(os.path.join(main["path"], d))]
    used_kb = size_kb(top_level(folders))
    try:
        free = shutil.disk_usage(root).free / GB
    except OSError:
        free = None
    info = {"enabled": True, "copies": len(linked), "max_copies": limits["max_work_copies"], "gb": gb(used_kb),
            "max_gb": limits["max_gb"], "free_gb": round(free, 1) if free is not None else None,
            "min_free_gb": limits["min_free_gb"], "base": base, "findings": [], "removable": [], "source": limits["source"]}
    add = info["findings"].append
    over_copies = len(linked) > limits["max_work_copies"]
    over_size = used_kb is not None and used_kb / (1024 * 1024) > limits["max_gb"]
    low_free = free is not None and free < limits["min_free_gb"]
    if over_copies:
        add({"code": "copies"})
    if over_size:
        add({"code": "size"})
    if low_free:
        add({"code": "free"})
    for tree in linked:
        if tree["locked"] or tree["prunable"]:
            continue
        if idle_minutes(tree["path"]) >= IDLE_MINUTES and merged(tree["path"], tree["head"], base) and clean(tree["path"]):
            info["removable"].append(tree["path"])
        elif over_copies or over_size or low_free:
            node = size_kb([os.path.join(tree["path"], "node_modules")])
            if node and node / (1024 * 1024) >= 1:
                add({"code": "heavy", "path": tree["path"], "node_modules": gb(node)})
    for path in info["removable"]:
        add({"code": "merged", "path": path, "base": base})
    found = []
    for tree in linked:
        found.extend(strays(tree["path"], contract["stray"]))
    if found:
        sample = ", ".join(os.path.relpath(p, root) if contained(p, root) else p for p in sorted(found)[:3])
        add({"code": "stray", "count": len(found), "sample": sample})
    store = pnpm_store_elsewhere(root)
    if store:
        add({"code": "store", "store": store})
    return info


def render(info, say):
    values = {"copies": info["copies"], "max_copies": info["max_copies"], "gb": info["gb"], "max_gb": info["max_gb"],
              "free": info["free_gb"] if info["free_gb"] is not None else "?", "min_free": info["min_free_gb"]}
    if not info["findings"]:
        return [say("ok", **values)]
    lines = [say("head", **values)]
    for finding in info["findings"]:
        lines.append(say(finding["code"], **{**values, **finding}))
    if info["removable"]:
        lines.append(say("merged_apply"))
    return lines


def context(args):
    here = os.getcwd()
    trees = worktrees(here)
    if not trees:
        return None, None
    return trees[0]["path"], trees


def cmd_check(args):
    root, trees = context(args)
    start = root or os.getcwd()
    contract = load_contract(start)
    say = Say(contract, language(start))
    if not root:
        print(say("not_git"))
        return 0
    limits = policy(root, contract)
    if not limits["enabled"]:
        if args.json:
            print(json.dumps({"enabled": False}))
        else:
            print(say("off"))
        return 0
    info = analyse(root, contract, limits, trees)
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print("\n".join(render(info, say)))
    return 0


def cmd_status(args):
    root, _ = context(args)
    start = root or os.getcwd()
    contract = load_contract(start)
    say = Say(contract, language(start))
    limits = policy(start, contract)
    if args.json:
        print(json.dumps(limits, indent=2))
        return 0
    if not limits["enabled"]:
        print(say("off"))
        return 0
    print(say("status", max_copies=limits["max_work_copies"], max_gb=limits["max_gb"], min_free=limits["min_free_gb"],
              source=say("source_" + limits["source"])))
    return 0


# --- prune ---------------------------------------------------------------------------------------------------

def cmd_prune(args):
    root, trees = context(args)
    start = root or os.getcwd()
    contract = load_contract(start)
    say = Say(contract, language(start))
    if not root:
        print(say("not_git"))
        return 0
    main, linked = trees[0], trees[1:]
    base = base_branch(main)
    here = os.path.realpath(os.getcwd())
    named = [os.path.realpath(p) for p in args.paths]
    unknown = [p for p in named if p not in [t["path"] for t in linked]]
    if unknown:
        print(f"gtt-disk: {unknown[0]} is not a work copy of this repository (see `git worktree list`).", file=sys.stderr)
        return 1
    chosen = []
    for tree in linked:
        if named and tree["path"] not in named:
            continue
        if tree["locked"] or contained(here, tree["path"]):
            continue
        if not named and idle_minutes(tree["path"]) < args.idle:
            continue
        if merged(tree["path"], tree["head"], base) and clean(tree["path"]):
            chosen.append(tree["path"])
    if not chosen:
        print(say("prune_none"))
        return 0
    if not args.apply:
        print(say("prune_dry", count=len(chosen)))
        for path in chosen:
            print(f"  git worktree remove {path}")
        return 0
    removed = 0
    for path in chosen:
        done = subprocess.run(["git", "worktree", "remove", path], cwd=main["path"], capture_output=True, text=True)
        if done.returncode == 0:
            removed += 1
        else:
            print(say("prune_fail", path=path, why=(done.stderr.strip().splitlines() or ["?"])[-1]), file=sys.stderr)
    git(["worktree", "prune"], cwd=main["path"])
    print(say("prune_done", count=removed))
    return 0 if removed == len(chosen) else 1


# --- set -----------------------------------------------------------------------------------------------------

def write_atomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def cmd_set(args):
    root, _ = context(args)
    start = root or os.getcwd()
    contract = load_contract(start)
    say = Say(contract, language(start))
    defaults, bounds = contract["defaults"], contract["bounds"]
    path = os.path.join(start, contract["state"])
    wanted = {"max_work_copies": args.max_copies, "max_gb": args.max_gb, "min_free_gb": args.min_free_gb}
    if args.default and (args.off or any(v is not None for v in wanted.values())):
        print("gtt-disk: --default stands alone.", file=sys.stderr)
        return 1
    if args.off and any(v is not None for v in wanted.values()):
        print("gtt-disk: --off stands alone.", file=sys.stderr)
        return 1
    if not (args.default or args.off or any(v is not None for v in wanted.values())):
        print("gtt-disk: say what to set: --max-copies N, --max-gb N, --min-free-gb N, --off or --default.", file=sys.stderr)
        return 1
    for name, value in wanted.items():
        if value is not None and not whole(value, bounds[name]):
            print(say("bad_value", name={"max_work_copies": "--max-copies", "max_gb": "--max-gb",
                                         "min_free_gb": "--min-free-gb"}[name], low=bounds[name][0], high=bounds[name][1]),
                  file=sys.stderr)
            return 1
    current = policy(start, contract)
    if args.default:
        state, loosened, off = None, False, False
    elif args.off:
        state, loosened, off = {"mode": "off"}, True, True
    else:
        merged_values = {k: (wanted[k] if wanted[k] is not None else current[k]) for k in wanted}
        loosened = (merged_values["max_work_copies"] > defaults["max_work_copies"] or merged_values["max_gb"] > defaults["max_gb"]
                    or merged_values["min_free_gb"] < defaults["min_free_gb"])
        state, off = {"mode": "custom", **merged_values}, False
    if off:
        print(say("warn_off"))
    elif loosened:
        print(say("warn", d_copies=defaults["max_work_copies"], d_gb=defaults["max_gb"], d_free=defaults["min_free_gb"]))
    if not args.apply:
        print(say("set_dry"))
        return 0
    if state is None:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        print(say("set_default"))
    else:
        write_atomic(path, json.dumps(state, indent=2, sort_keys=True) + "\n")
        print(say("set_done", state=contract["state"]))
    return 0


def main():
    parser = argparse.ArgumentParser(prog="gtt-disk", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "status"):
        p = sub.add_parser(name)
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("prune")
    p.add_argument("paths", nargs="*")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--idle", type=int, default=IDLE_MINUTES, help="minutes a work copy must have been untouched when no path is named")
    p = sub.add_parser("set")
    p.add_argument("--max-copies", type=int)
    p.add_argument("--max-gb", type=int)
    p.add_argument("--min-free-gb", type=int)
    p.add_argument("--off", action="store_true")
    p.add_argument("--default", action="store_true")
    p.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    return {"check": cmd_check, "status": cmd_status, "prune": cmd_prune, "set": cmd_set}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
