#!/usr/bin/env python3
"""GTT - code: what was built, and whether it respects the architecture. A map of the code against stack.md, computed from files.

  gtt_code.py map [--epic EPIC-n | --story STORY-n] [--since freeze|yesterday|<git ref>] [--json]
  gtt_code.py refresh [--quiet]          rebuild the index (what changed since the last one); the watcher calls it, a snapshot never does

What it reads, with no compiler and nothing stored in the repository:
  * the modules and what each may or must not depend on: `stack.md` 5. Dependency rules (`gtt_observe.declared_modules` reads the same table);
  * the real dependencies: the imports of each file (Python, JS and TS, Go, Java and Kotlin, C#, Ruby, PHP, Rust), by regular expressions;
  * the classes, with universal-ctags when it is installed (without it the view says so once and stays at modules and files);
  * what is new (against the last commit, or the freeze with --since freeze) and who built it (the activity journal, file by Story);
  * from the design to the code: for each Epic, each item of its design (R, F, I, E), the Stories that build it, their files and evidence.

A dependency the table does not allow is `GTT-DEPENDS` (gtt_observe.py, GOVERNANCE). Code outside every module is `GTT-MODULES`. The index is
`.gtt/local/code-index.json` (derived: delete it and it is rebuilt), keyed by each file's mtime and size; the exclusions and the extensions are data
in `.gtt/contract/findings.json` (`code`). Exit 0 always.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

INDEX = ".gtt/local/code-index.json"
MAP = ".gtt/local/code-map.json"
STACK = "gtt-domain/context/stack.md"
FROZEN = "gtt-domain/.frozen"
MAX_FILE = 400_000

LANGS = {".py": "python", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".cjs": "js", ".go": "go", ".java": "java", ".kt": "java", ".kts": "java",
         ".cs": "csharp", ".rb": "ruby", ".php": "php", ".rs": "rust"}
IMPORTS = {
    "python": [re.compile(r"^\s*from\s+([.\w]+)\s+import\b"), re.compile(r"^\s*import\s+([.\w]+)")],
    "js": [re.compile(r"""\bfrom\s+['"]([^'"]+)['"]"""), re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)"""), re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""")],
    "go": [re.compile(r"""^\s*(?:import\s+)?(?:\w+\s+)?"([\w./@-]+)"\s*$""")],
    "java": [re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)")],
    "csharp": [re.compile(r"^\s*using\s+(?:static\s+)?([\w.]+)\s*;")],
    "ruby": [re.compile(r"""^\s*require(?:_relative)?\s+['"]([^'"]+)['"]""")],
    "php": [re.compile(r"^\s*use\s+([\w\\]+)"), re.compile(r"""^\s*(?:require|include)(?:_once)?\s*\(?\s*['"]([^'"]+)['"]""")],
    "rust": [re.compile(r"^\s*(?:pub\s+)?use\s+(?:crate::)?([\w:]+)"), re.compile(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;")],
}
DEFAULT_EXCLUDE = ("vendor/", "node_modules/", ".gtt/", "gtt-domain/", ".git/", "dist/", "build/", "__pycache__/", ".venv/", "venv/", "target/", ".next/", "coverage/", ".claude/", ".kiro/", ".cursor/", ".agents/", ".openhands/", ".github/", "docs/")


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def read_json(path):
    try:
        return json.loads(read(path) or "")
    except ValueError:
        return None


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def exclusions():
    cfg = (read_json(".gtt/contract/findings.json") or {}).get("code") or {}
    return tuple(cfg.get("exclude") or DEFAULT_EXCLUDE)


# ----------------------------------------------------------------------------------------------------------- modules

def cells(line):
    return [c.strip().strip("`") for c in line.strip().strip("|").split("|")]


def paths_of(text):
    out = []
    for part in re.split(r"[,;]", text or ""):
        part = part.strip().strip("`")
        if not part or set(part) <= set("-—–: "):
            continue
        stem = re.split(r"[*?\[{<(\s]", part, maxsplit=1)[0].rstrip("/")
        if stem and "/" in (stem + "/"):
            out.append(stem + "/")
    return out


def modules():
    """[{id, path, may: [paths], must_not: [paths], has_rule}] from stack.md 5. Dependency rules (Module | May depend on | Must not depend on)."""
    text = read(STACK)
    if not text:
        return []
    out, inside = [], False
    for line in text.splitlines():
        row = cells(line) if line.lstrip().startswith("|") else None
        if row and row[0] == "Module" and len(row) > 1 and row[1].startswith("May depend"):
            inside = True
            continue
        if inside and not line.lstrip().startswith("|"):
            inside = False
        if inside and row and "/" in row[0] and not set(row[0]) <= set("-: "):
            stem = re.split(r"[*?\[{<]", row[0], maxsplit=1)[0].rstrip("/")
            if not stem:
                continue
            may = paths_of(row[1]) if len(row) > 1 else []
            must_not = paths_of(row[2]) if len(row) > 2 else []
            declared_none = len(row) > 1 and bool(row[1]) and set(row[1]) <= set("-—– ")
            out.append({"id": stem, "path": stem + "/", "may": may, "must_not": must_not, "has_rule": bool(may or must_not or declared_none), "none": declared_none})
    return out


def module_of(path, mods):
    best = None
    for m in mods:
        if path.startswith(m["path"]) and (best is None or len(m["path"]) > len(best["path"])):
            best = m
    return best


# ----------------------------------------------------------------------------------------------------------- the index

def tracked_files():
    """Every file of the project that could hold code: git's list when there is one (it honours .gitignore), else a walk."""
    skip = exclusions()
    out = []
    try:
        res = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, timeout=30)
        names = res.stdout.splitlines() if res.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        names = None
    if names is None:
        names = []
        for here, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if not d.startswith(".") and (os.path.join(here, d).lstrip("./") + "/") not in skip]
            names.extend(os.path.normpath(os.path.join(here, f)).replace(os.sep, "/") for f in files)
    for name in names:
        if os.path.splitext(name)[1].lower() in LANGS and not any(name.startswith(s) for s in skip):
            out.append(name)
    return out


def imports_of(path, lang):
    text = read(path)
    if text is None or len(text) > MAX_FILE:
        return []
    found = []
    block = False
    for number, line in enumerate(text.splitlines(), 1):
        if lang == "go":
            if re.match(r"^\s*import\s*\($", line):
                block = True
                continue
            if block and line.strip() == ")":
                block = False
                continue
            if not block and not line.lstrip().startswith("import"):
                continue
        for pattern in IMPORTS[lang]:
            hit = pattern.search(line)
            if hit:
                found.append([number, hit.group(1)])
                break
    return found


def build_index(previous=None):
    """{path: {mtime, size, lang, imports}} reusing every entry whose file did not change."""
    previous = previous or {}
    index = {}
    for name in tracked_files():
        try:
            st = os.stat(name)
        except OSError:
            continue
        old = previous.get(name)
        if old and old["mtime"] == st.st_mtime_ns and old["size"] == st.st_size:
            index[name] = old
            continue
        lang = LANGS[os.path.splitext(name)[1].lower()]
        index[name] = {"mtime": st.st_mtime_ns, "size": st.st_size, "lang": lang, "imports": imports_of(name, lang)}
    return index


def load_index():
    data = read_json(INDEX)
    return data.get("files") if isinstance(data, dict) else None


def save_index(index):
    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    tmp = INDEX + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"schema": 1, "at": now_utc(), "files": index}, handle, sort_keys=True)
    os.replace(tmp, INDEX)


# ----------------------------------------------------------------------------------------------------------- resolving

def target_module(imp, lang, here, mods):
    """The module an import points to, or None (a library, a standard package, something outside every module)."""
    raw = imp
    if lang in ("js", "ruby", "php") and (raw.startswith(".") or "/" in raw) and not raw.startswith("@"):
        base = os.path.normpath(os.path.join(os.path.dirname(here), raw)).replace(os.sep, "/") if raw.startswith(".") else raw
        candidates = [base + "/"]
    elif lang == "python" and raw.startswith("."):
        dots = len(raw) - len(raw.lstrip("."))
        base = here
        for _ in range(dots):
            base = os.path.dirname(base)
        candidates = [(base + "/" + raw.lstrip(".").replace(".", "/")).strip("/") + "/"]
    else:
        candidates = [re.sub(r"[.:\\]+", "/", raw).strip("/") + "/", raw.strip("/") + "/"]
    best = None
    for cand in candidates:
        wrapped = "/" + cand
        for m in mods:
            stem = m["path"].rstrip("/")
            if ("/" + stem + "/") in wrapped or wrapped.startswith("/" + stem + "/") or (cand.startswith(m["path"])):
                if best is None or len(m["path"]) > len(best["path"]):
                    best = m
    return best


def verdict(src, dst):
    """True when `src` may depend on `dst`, False when it must not, None when no rule speaks."""
    if dst["path"] in src["must_not"]:
        return False
    if src["has_rule"] and (src["may"] or src["none"]):
        return dst["path"] in src["may"]
    return None


def layers(mods):
    """The depth of each module in the graph of what it may depend on: 0 for a module that depends on nothing."""
    by = {m["path"]: m for m in mods}
    memo, visiting = {}, set()

    def depth(m):
        if m["path"] in memo:
            return memo[m["path"]]
        if m["path"] in visiting:
            return 0
        visiting.add(m["path"])
        value = 0
        for dep in m["may"]:
            if dep in by and dep != m["path"]:
                value = max(value, 1 + depth(by[dep]))
        visiting.discard(m["path"])
        memo[m["path"]] = value
        return value
    return {m["path"]: depth(m) for m in mods}


# ----------------------------------------------------------------------------------------------------------- since, authors, classes

def git(*argv):
    try:
        res = subprocess.run(["git", *argv], capture_output=True, text=True, timeout=30)
        return res.stdout if res.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def new_files(since):
    """{path: 'new'|'changed'} against the last commit, the freeze baseline or a ref. None when git says nothing."""
    base = "HEAD"
    if since == "freeze":
        for line in (read(FROZEN) or "").splitlines():
            if line.startswith("#"):
                break
            if line.partition(":")[0].strip() == "Baseline commit" and line.partition(":")[2].strip() not in ("", "none"):
                base = line.partition(":")[2].strip()
    elif since in ("yesterday", "ayer"):
        found = git("log", "--since=yesterday", "--format=%H", "--reverse")
        first = (found or "").split()
        base = first[0] + "~1" if first else "HEAD"
    elif since and since != "head":
        base = since
    out = {}
    changed = git("diff", "--name-status", base)
    if changed is None:
        return None
    for line in changed.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            out[parts[-1]] = "new" if parts[0].startswith("A") else "changed"
    for name in (git("ls-files", "--others", "--exclude-standard") or "").splitlines():
        out[name] = "new"
    return out


def authors():
    """{path: {stories, actor, last}} from the activity journal: who touched each file, under which Story."""
    out = {}
    try:
        import gtt_activity
        for r in gtt_activity.rows():
            if r.get("path") and r.get("actor") != "human":
                row = out.setdefault(r["path"], {"stories": [], "actors": [], "last": None})
                for s in r.get("stories") or []:
                    if s not in row["stories"]:
                        row["stories"].append(s)
                label = "claude" if r.get("actor") == "agent" else "unattributed"
                if label not in row["actors"]:
                    row["actors"].append(label)
                row["last"] = r.get("t")
    except Exception:
        pass
    return out


def ctags_classes(files):
    """{path: [class names]} with universal-ctags; None when it is not installed."""
    exe = shutil.which("ctags")
    if not exe:
        return None
    try:
        res = subprocess.run([exe, "--output-format=json", "--fields=+K", "-L", "-", "-o", "-", "--kinds-all=*"], input="\n".join(files), capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if "Universal" not in (subprocess.run([exe, "--version"], capture_output=True, text=True).stdout or "") or res.returncode != 0:
        return None
    out = {}
    for line in res.stdout.splitlines():
        try:
            tag = json.loads(line)
        except ValueError:
            continue
        if tag.get("kind") in ("class", "struct", "interface", "enum", "trait", "type"):
            out.setdefault(tag.get("path"), []).append(tag.get("name"))
    return out


# ----------------------------------------------------------------------------------------------------------- design to code

def design_to_code(epic_filter=None, story_filter=None):
    """Per Epic: each item of its design with the Stories that build it, their files (from the journal), the evidence of their `Done when` and whether they closed."""
    try:
        import gtt_design
        stories, epics = gtt_design.backlog()
    except (Exception, SystemExit):
        return None
    files_by_story = {}
    for path, row in authors().items():
        for s in row["stories"]:
            files_by_story.setdefault(s, []).append(path)
    out = {}
    for epic in epics:
        if epic_filter and epic["id"] != epic_filter:
            continue
        design = gtt_design.parse_design(gtt_design.epic_design(epic))
        if design is None:
            continue
        own = [s for s in stories if s["epic"] == epic["id"] and s["status"] != "Cancelled"]
        rows = []
        for key in sorted((k for k in design["items"] if k[0] in "RFIE" or k.startswith("AC-")), key=lambda k: (k[0], int(re.sub(r"\D", "", k) or 0))):
            builders = [s for s in own if (epic["id"], key) in gtt_design.implements_of(s)[0]]
            if story_filter and not any(s["id"] == story_filter for s in builders):
                continue
            rows.append({"item": key, "text": (design["items"][key] or "")[:140] if isinstance(design["items"], dict) else "",
                         "stories": [s["id"] for s in builders], "files": sorted({f for s in builders for f in files_by_story.get(s["id"], [])})[:12],
                         "evidence": [s["fields"].get("Done when", "")[:140] for s in builders if s["fields"].get("Done when")][:3],
                         "closed": bool(builders) and all(s["status"] == "Done" for s in builders), "built": bool(builders)})
        if rows:
            out[epic["id"]] = rows
    return out


# ----------------------------------------------------------------------------------------------------------- the map

def epic_files():
    """{EPIC: {title, stories, files}}: which Stories belong to each Epic and which files the journal says they touched."""
    out = {}
    try:
        import gtt_backlog
        stories, epics = gtt_backlog.parse(gtt_backlog.DEFAULT)
    except (Exception, SystemExit):
        return out
    by_file = authors()
    for e in epics:
        mine = [s["id"] for s in stories if s["epic"] == e["id"]]
        files = sorted(p for p, row in by_file.items() if any(s in mine for s in row["stories"]))
        out[e["id"]] = {"title": e.get("title"), "stories": mine, "files": files}
    return out


def build_map(since=None, epic=None, story=None, refresh=True):
    mods = modules()
    index = load_index()
    if index is None or refresh:
        index = build_index(index)
        save_index(index)
    layer = layers(mods)
    mod_files = {m["path"]: [] for m in mods}
    outside = []
    edges = {}
    for name in sorted(index):
        mine = module_of(name, mods)
        if mine is None:
            if mods and any(name.startswith(m["path"].split("/", 1)[0] + "/") for m in mods):
                outside.append(name)
            continue
        mod_files[mine["path"]].append(name)
        for line, imp in index[name]["imports"]:
            dst = target_module(imp, index[name]["lang"], name, mods)
            if dst is None or dst["path"] == mine["path"]:
                continue
            key = (mine["path"], dst["path"])
            row = edges.setdefault(key, {"from": mine["path"], "to": dst["path"], "count": 0, "example": f"{name}:{line}", "allowed": verdict(mine, dst)})
            row["count"] += 1
    tree = new_files(since)
    tree_freeze, tree_yday = new_files("freeze"), new_files("yesterday")
    who = authors()
    classes = ctags_classes([f for fs in mod_files.values() for f in fs]) if mods else None
    focus = None
    d2c = design_to_code(epic, story)
    if epic or story:
        eps = epic_files()
        focus = sorted({f for e, row in eps.items() if (not epic or e == epic) for f, s in [(f, None) for f in row["files"]]
                        if not story or any(story in (who.get(f) or {"stories": []})["stories"] for _ in [0])})
    out_mods = []
    for m in mods:
        files = mod_files[m["path"]]
        out_mods.append({"id": m["id"], "path": m["path"], "layer": layer[m["path"]], "files": len(files), "empty": not files,
                         "classes": sum(len(classes.get(f, [])) for f in files) if classes is not None else None,
                         "new": sum(1 for f in files if (tree or {}).get(f) == "new") if tree is not None else None,
                         "changed": sum(1 for f in files if (tree or {}).get(f)) if tree is not None else None,
                         "stories": sorted({s for f in files for s in (who.get(f) or {"stories": []})["stories"]}),
                         "touched": bool(focus and any(f.startswith(m["path"]) for f in focus)),
                         "detail": [{"file": f, "status": (tree or {}).get(f), "freeze": (tree_freeze or {}).get(f), "yesterday": (tree_yday or {}).get(f), "classes": (classes or {}).get(f) if classes is not None else None,
                                     "stories": (who.get(f) or {}).get("stories"), "who": (who.get(f) or {}).get("actors"), "last": (who.get(f) or {}).get("last")} for f in files[:80]],
                         "may": m["may"], "must_not": m["must_not"]})
    epics_out = epic_files()
    return {"schema": 1, "kind": "gtt-code-map", "at": now_utc(), "since": since or "head", "epics": epics_out, "modules": out_mods, "edges": sorted(edges.values(), key=lambda e: (e["from"], e["to"])),
            "outside": outside[:40], "ctags": classes is not None, "files": len(index), "design_to_code": d2c, "journal": bool(who)}


def cmd_map(args):
    data = build_map(args.since, args.epic, args.story, refresh=not args.cached)
    print(json.dumps(data, indent=2, ensure_ascii=False) if args.json else summary(data))
    return 0


def summary(data):
    lines = [f"{len(data['modules'])} module(s), {data['files']} file(s) read" + ("" if data["ctags"] else "; no universal-ctags: modules and files only")]
    for m in data["modules"]:
        lines.append(f"  {m['path']:24} layer {m['layer']}  {m['files']} file(s)" + ("  (declared, empty)" if m["empty"] else ""))
    for e in data["edges"]:
        flag = {True: "allowed", False: "NOT ALLOWED", None: "no rule"}[e["allowed"]]
        lines.append(f"  {e['from']} -> {e['to']}  {e['count']}x  {flag}  e.g. {e['example']}")
    return "\n".join(lines)


def cmd_refresh(args):
    try:
        data = build_map(None, None, None, refresh=True)
        os.makedirs(os.path.dirname(MAP), exist_ok=True)
        tmp = MAP + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, sort_keys=True, ensure_ascii=False)
        os.replace(tmp, MAP)
    except Exception as exc:       # a refresh never makes noise
        if not args.quiet:
            print(f"gtt-code: {exc}", file=sys.stderr)
    return 0


def last_map():
    """The map the watcher left (what a snapshot reads); None when there is none."""
    return read_json(MAP)


def findings():
    """The `code` plane of the findings: a dependency the table does not allow (GTT-DEPENDS) and a declared module with no code (informative).
    Code outside every module is `GTT-MODULES`, which gtt_observe already raises. Read from the last map; nothing is computed here."""
    import gtt_findings as gf
    data = last_map()
    if not data or not data.get("modules"):
        return []
    out = []
    for e in data["edges"]:
        if e["allowed"] is False:
            out.append(gf.make("GTT-DEPENDS", f"{e['from']}>{e['to']}", e["example"], "gtt_code", frm=e["from"], to=e["to"], count=e["count"], example=e["example"]))
    for m in data["modules"]:
        if m["empty"]:
            out.append(gf.make("CODE-EMPTY", m["path"], m["path"], "gtt_code", path=m["path"]))
    return out


def main(argv):
    parser = argparse.ArgumentParser(prog="gtt_code.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("map")
    m.add_argument("--epic")
    m.add_argument("--story")
    m.add_argument("--since")
    m.add_argument("--json", action="store_true")
    m.add_argument("--cached", action="store_true")
    r = sub.add_parser("refresh")
    r.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    return {"map": cmd_map, "refresh": cmd_refresh}[args.cmd](args)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv[1:]))
