#!/usr/bin/env python3
"""GTT - workflow policy, the review surface, staging and promotion.

Four small services over one set of facts, all computed from the repository and never from a model
or a conversation:

  gtt_flow.py workflow get [--json] | check | detect
        the Git policy the human declared in gtt-domain/workflow.md (defaults when there is none),
        its validation, and the conventions the project's own documents mention - reported, never adopted
  gtt_flow.py review [--files] [--json] [--gate]
        the one review surface: what changed, what it touches, what is risky, what the human must
        decide, the last validation and the next step - in at most 12 lines
  gtt_flow.py state
        a hash of the working state, for the validation cache and the checkpoint
  gtt_flow.py stage NAME --reason TEXT SRC=DEST ...
        prepare a promotion set under gtt-domain/proposals/staged/NAME/ (an agent may run this)
  gtt_flow.py promote NAME | promote --undo NAME
        apply a staged set, all or nothing, after the human types `apply` (the human runs this)
  gtt_flow.py check no-commits | overlay-block | ar-rules
        the static checks gtt-validate.sh runs

Nothing here creates a commit, a branch, a tag or a stash, stages a file, or pushes: Git history is
the human's. `review` and `workflow` only read. The only things written are a staged set (by `stage`),
the files a human promotes, and local state under .gtt/local/, which is never committed.
"""

import argparse
import datetime
import difflib
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True            # a review that leaves files behind would change what it reports

WORKFLOW = "gtt-domain/workflow.md"
BACKLOG = "gtt-domain/backlog.md"
LEDGER = "gtt-domain/governance-backlog.json"
PROPOSALS = "gtt-domain/proposals"
STAGED = "gtt-domain/proposals/staged"
CHANGE_REQUEST = "gtt-domain/change-request.md"
STACK = "gtt-domain/context/stack.md"
REGISTRY = ".gtt/protection/registry.yaml"
LOCAL = ".gtt/local"
VALIDATION = ".gtt/local/last-validation.json"
BACKUPS = ".gtt/local/promote-backup"
CONTRACT = "AGENTS" + ".md"
PROFILES = ".gtt/contract/profiles.json"
DERIVED = (".gtt/index/technical-index.json", ".gtt/index/artifacts.json", "gtt-domain/session.md")
GOVERNED_DIRS = ("gtt-domain/context/", "gtt-domain/adr/")
DEFAULTS = {"commits": "on-request", "convention": "none", "branches-tags": "on-request", "review-files": 10, "review-lines": 500}
COMMITS = ("on-request", "allowed", "never")
BRANCHES = ("on-request", "never")
MAX_LINES, MAX_WIDTH = 12, 110
CONVENTIONAL = re.compile(r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([^()\s]+\))?!?: \S")
OVERLAYS = (".kiro/steering/gtt-dialogue.md", ".github/instructions/gtt.instructions.md", ".cursor/rules/gtt.mdc",
            ".agents/rules/gtt.md", ".agents/skills/gtt/SKILL.md")
AR_RULES = tuple(f"GTT-AR-{n:02d}" for n in range(1, 11))


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


def git(*args):
    """stdout of a read-only git command, or None when git cannot answer."""
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return None
    return proc.stdout if proc.returncode == 0 else None


def local_dir():
    """.gtt/local/ exists and ignores itself: what GTT keeps there is never committed."""
    os.makedirs(LOCAL, exist_ok=True)
    ignore = os.path.join(LOCAL, ".gitignore")
    if not os.path.isfile(ignore):
        with open(ignore, "w", encoding="utf-8") as handle:
            handle.write("# Local GTT state: never committed.\n*\n")


# ------------------------------------------------------------------------- workflow

def workflow():
    """(values, problems, source). A missing file, block or key uses its default."""
    values, problems = dict(DEFAULTS), []
    text = read(WORKFLOW)
    block = re.search(r"```gtt-workflow\r?\n(.*?)```", text or "", re.DOTALL)
    if not block:
        return values, problems, "defaults"
    for number, raw in enumerate(block.group(1).splitlines(), 1):
        line = re.sub(r"\s+#.*$", "", raw).strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or key not in DEFAULTS:
            problems.append(f"line {number}: unknown key `{key}` ({', '.join(DEFAULTS)})")
        elif key == "commits" and value not in COMMITS:
            problems.append(f"commits: `{value}` is not one of {' | '.join(COMMITS)}")
        elif key == "branches-tags" and value not in BRANCHES:
            problems.append(f"branches-tags: `{value}` is not one of {' | '.join(BRANCHES)}")
        elif key == "convention":
            custom = re.match(r"^custom:\s*(\S.*)$", value)
            if custom and not os.path.isfile(custom.group(1).strip()):
                problems.append(f"convention: the rule file `{custom.group(1).strip()}` does not exist")
            elif not custom and value not in ("none", "conventional"):
                problems.append(f"convention: `{value}` is not none | conventional | custom: <path>")
            else:
                values[key] = value
        elif key in ("review-files", "review-lines"):
            if not value.isdigit() or int(value) < 1:
                problems.append(f"{key}: `{value}` is not a positive number")
            else:
                values[key] = int(value)
        else:
            values[key] = value
    return values, problems, WORKFLOW


SIGNS = (("Conventional Commits", re.compile(r"conventional\s*commits|conventionalcommits\.org", re.IGNORECASE)),
         ("commitlint", re.compile(r"commitlint", re.IGNORECASE)), ("commitizen", re.compile(r"commitizen|\bcz-", re.IGNORECASE)))


def detect():
    """Conventions the project's own documents and files mention. Each is a finding: nothing is adopted."""
    selected = [s.get("path") for s in (read_json(".gtt/selected-sources.json") or {}).get("sources", []) if s.get("path")]
    documents = [p for p in sorted(set(selected + glob.glob("*.md") + glob.glob("SOURCE-BRIEF.*") + glob.glob("docs/*.md")))
                 if os.path.isfile(p) and p != CONTRACT and not p.lower().startswith("readme-gtt")]
    found, seen = [], set()
    for path in documents:
        for number, line in enumerate((read(path) or "").splitlines(), 1):
            for name, pattern in SIGNS:
                if name not in seen and pattern.search(line):
                    seen.add(name)
                    found.append(f"{name} mentioned in {path}:{number}")
    for path in sorted(glob.glob(".czrc") + glob.glob(".gitmessage") + glob.glob("commitlint*") + glob.glob(".commitlintrc*")):
        found.append(f"{path} found")
    package = read("package.json") or ""
    if re.search(r'"(commitizen|@commitlint/[^"]+)"', package):
        found.append("commitizen or commitlint declared in package.json")
    return found


def cmd_workflow(args):
    values, problems, source = workflow()
    if args.action == "detect":
        if values["convention"] == "none":
            for finding in detect():
                print(f'@gtt · Finding  {finding}. To adopt it, set "convention: conventional" in {WORKFLOW}.')
        return 0
    if args.action == "check":
        for problem in problems:
            print(f"gtt-workflow: FAILED - {WORKFLOW}: {problem}", file=sys.stderr)
        if not problems:
            print(f"gtt-workflow: OK - commits: {values['commits']}; convention: {values['convention']}; "
                  f"branches-tags: {values['branches-tags']} ({source}).")
        return 1 if problems else 0
    if args.json:
        print(json.dumps({"schema": 1, "kind": "gtt-workflow", "source": source, "valid": not problems, "problems": problems,
                          "values": values, "defaults": DEFAULTS, "owner": "the human - an ADE never edits it"},
                         indent=2, sort_keys=True))
    else:
        for key in DEFAULTS:
            print(f"{key}: {values[key]}")
        print(f"source: {source}")
    return 0


# ------------------------------------------------------------------------- repository facts

def base_ref():
    """The commit a review compares against: the merge base with the default branch."""
    if git("rev-parse", "--git-dir") is None:
        return None
    default = (git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD") or "").strip()
    for candidate in [default, "origin/main", "origin/master", "main", "master"]:
        if candidate and git("rev-parse", "--verify", "--quiet", candidate + "^{commit}"):
            merged = git("merge-base", "HEAD", candidate)
            if merged:
                return merged.strip()
    head = git("rev-parse", "--verify", "--quiet", "HEAD")
    return head.strip() if head else None


def noise(path):
    """Interpreter caches are not work: they are never counted as a change."""
    return "__pycache__/" in path or path.endswith(".pyc")


def changes():
    """What differs from the base, derived files left out: {files: {path: status}, added, removed, uncommitted}."""
    out = {"git": False, "base": None, "files": {}, "added": 0, "removed": 0, "uncommitted": 0}
    base = base_ref()
    if git("rev-parse", "--git-dir") is None:
        return out
    out.update(git=True, base=base)
    exclude = ["--", "."] + [":(exclude)" + path for path in DERIVED]
    if base:
        for line in (git("diff", "--name-status", "--no-renames", base, *exclude) or "").splitlines():
            status, _, path = line.partition("\t")
            if noise(path):
                continue
            out["files"][path] = {"A": "new", "D": "deleted"}.get(status[:1], "modified")
        for line in (git("diff", "--numstat", "--no-renames", base, *exclude) or "").splitlines():
            added, removed, _ = (line.split("\t") + ["", ""])[:3]
            out["added"] += int(added) if added.isdigit() else 0
            out["removed"] += int(removed) if removed.isdigit() else 0
    for path in (git("ls-files", "--others", "--exclude-standard", *exclude) or "").splitlines():
        if noise(path):
            continue
        out["files"][path] = "new"
        try:
            if os.path.getsize(path) < 1_000_000:
                out["added"] += (read(path) or "").count("\n")
        except OSError:
            pass
    out["uncommitted"] = len([l for l in (git("status", "--porcelain", "--untracked-files=all", *exclude) or "").splitlines() if not noise(l[3:])])
    return out


def state_hash():
    """One hash of the working state (derived files left out): HEAD, what is modified and its content."""
    if git("rev-parse", "--git-dir") is None:
        return "no-git"
    exclude = ["--", "."] + [":(exclude)" + path for path in DERIVED]
    status = [l for l in (git("status", "--porcelain", "--untracked-files=all", *exclude) or "").splitlines() if not noise(l[3:])]
    parts = [git("rev-parse", "--verify", "--quiet", "HEAD") or "no-head", "\n".join(status), git("diff", "HEAD", *exclude) or ""]
    for path in (git("ls-files", "--others", "--exclude-standard", *exclude) or "").splitlines():
        if noise(path):
            continue
        try:
            stat = os.stat(path)
            parts.append(f"{path}:{stat.st_size}:{stat.st_mtime_ns}")
        except OSError:
            pass
    return hashlib.sha1("\0".join(parts).encode("utf-8", "replace")).hexdigest()


def open_observations():
    ledger = read_json(LEDGER) or {}
    return [item for item in ledger.get("items", []) if item.get("status") in ("open", "deferred", "rejected")]


def stories():
    try:
        import gtt_backlog
        return gtt_backlog.parse(BACKLOG) if os.path.isfile(BACKLOG) else ([], [])
    except Exception:
        return [], []


def story_title(story):
    lines = (read(BACKLOG) or "").splitlines()
    head = lines[story["line"] - 1] if 0 < story["line"] <= len(lines) else ""
    return re.sub(r"^#+\s*STORY-\d+\s*[-—–:]*\s*", "", head).strip()


def untraced(story):
    """Why a Done Story's closure cannot be trusted, or None: said is not the same as observed."""
    closed = story["fields"].get("Closed", "")
    if not closed.strip() or re.search(r"<[^<>]*>", closed):
        return "Done without a closure trace"
    for sha in re.findall(r"\b[0-9a-f]{7,40}\b", closed):
        if git("rev-parse", "--git-dir") is not None and git("cat-file", "-e", sha + "^{commit}") is None:
            return f"Done, but its closure names a commit that does not exist ({sha[:10]})"
    return None


def blocking_gaps():
    block = re.search(r"```gtt-gaps\r?\n(.*?)```", read(STACK) or "", re.DOTALL)
    return [parts[1].strip() for parts in (line.split("|") for line in (block.group(1).splitlines() if block else []))
            if len(parts) > 1 and parts[0].strip() == "BLOCKING"]


def protected_artifacts():
    return set(re.findall(r"^\s*-\s*artifact:\s*(\S+)", read(REGISTRY) or "", re.MULTILINE))


def last_validation():
    cache = read_json(VALIDATION)
    return cache if isinstance(cache, dict) and "result" in cache else None


# ------------------------------------------------------------------------- review

def review_facts():
    values, problems, _ = workflow()
    change = changes()
    files = change["files"]
    observations = open_observations()
    all_stories, epics = stories()
    in_progress = [s for s in all_stories if s["status"] == "In Progress"]
    blocked = [s for s in all_stories if s["status"] == "Blocked"]
    over = []
    if len(files) > values["review-files"]:
        over.append(f"{len(files)} files > {values['review-files']}")
    if change["added"] + change["removed"] > values["review-lines"]:
        over.append(f"{change['added'] + change['removed']} lines > {values['review-lines']}")
    governed = sorted(p for p in files if p.startswith(GOVERNED_DIRS))
    guarded = sorted(p for p in files if p in protected_artifacts())
    cache = last_validation()
    stale = bool(cache) and cache.get("state") != state_hash()
    try:
        import gtt_design
        unplanned = [c for c in gtt_design.coverage() if c["missing"] and c["working"] and not c["closed"]]
    except Exception:
        unplanned = []

    risks = []
    warnings = [o for o in observations if o.get("level") == "WARNING" and o.get("status") == "open"]
    if warnings:
        risks.append(f"{len(warnings)} WARNING")
    for story in all_stories:
        if story["status"] == "Done" and untraced(story):
            risks.append(f"{story['id']} {untraced(story)}")
    if files and (cache is None or stale):
        risks.append("validation not run since the last change")
    if problems:
        risks.append(f"{WORKFLOW} is not valid")

    decide = []
    for item in observations:
        if item.get("level") in ("BLOCKING", "GOVERNANCE") or item.get("status") == "rejected" or item.get("kind") == "dependency":
            note = ", authority: not found" if item.get("kind") == "dependency" else ""
            decide.append({"id": item["id"], "level": item.get("level"), "what": f"{item['id']} {item.get('detail') or item.get('artifact')}{note}",
                           "command": f"bash .gtt/scripts/gtt-observe.sh accept|reject|defer {item['id']} --by <you> --apply"})
    for name in sorted(os.listdir(STAGED)) if os.path.isdir(STAGED) else []:
        if os.path.isfile(os.path.join(STAGED, name, "promote.json")):
            decide.append({"id": name, "level": "PROMOTION", "what": f"promotion {name}", "command": f"bash .gtt/scripts/gtt-promote.sh {name}"})
    for path in sorted(glob.glob(os.path.join(PROPOSALS, "PROPOSAL-*.md"))):
        decide.append({"id": os.path.basename(path)[:-3], "level": "PROPOSAL", "what": f"proposal {os.path.basename(path)[:-3]}", "command": f"read {path}"})
    request = read(CHANGE_REQUEST)
    if request and not re.search(r"^Change: <", request, re.MULTILINE):
        decide.append({"id": "change-request", "level": "REQUEST", "what": "a change request is waiting", "command": f"read {CHANGE_REQUEST}"})
    for epic in epics:
        if epic["status"] == "Proposed":
            decide.append({"id": epic["id"], "level": "EPIC", "what": f"{epic['id']} awaits approval", "command": f"bash .gtt/scripts/gtt-approve.sh {epic['id']}"})
    for gap in blocking_gaps():
        decide.append({"id": gap, "level": "GAP", "what": f"{gap} is a BLOCKING gap", "command": f"decide it in {STACK}"})

    blocking = [d for d in decide if d["level"] == "BLOCKING"]
    if blocking:
        nxt = f"fix or decide {blocking[0]['id']}: {blocking[0]['command']}"
    elif decide:
        nxt = f"decide {decide[0]['id']} ({decide[0]['command']})"
    elif files and (cache is None or stale):
        nxt = "bash .gtt/scripts/gtt-validate.sh"
    else:
        nxt = "nothing pending"
    return {"schema": 1, "kind": "gtt-review", "workflow": values,
            "work": {"in_progress": [{"id": s["id"], "title": story_title(s), "epic": s["epic"]} for s in in_progress],
                     "blocked": [s["id"] for s in blocked]},
            "changed": {"git": change["git"], "base": change["base"], "files": files, "count": len(files),
                        "new": sum(1 for v in files.values() if v == "new"), "deleted": sum(1 for v in files.values() if v == "deleted"),
                        "added": change["added"], "removed": change["removed"], "uncommitted": change["uncommitted"], "over": over},
            "impact": {"governed": governed, "protected": guarded}, "risks": risks, "decide": decide,
            "design": [{"epic": c["epic"], "not_planned": c["missing"]} for c in unplanned],
            "validation": dict(cache, stale=stale) if cache else None, "next": nxt,
            "authority": "none - computed from the repository; it reports whether the governance conditions hold, never whether the design is right"}


def fit(line):
    return line if len(line) <= MAX_WIDTH else line[:MAX_WIDTH - 1].rstrip() + "…"


def review_lines(facts):
    out = ["@gtt · Review"]
    work, changed = facts["work"], facts["changed"]
    if work["in_progress"] or work["blocked"]:
        first = work["in_progress"][0] if work["in_progress"] else None
        lead = f"{first['id']} {first['title']}".strip() + (f" ({first['epic']})" if first and first["epic"] else "") if first else "nothing in progress"
        out.append(f"WORK     {lead} · {len(work['in_progress'])} In Progress · {len(work['blocked'])} Blocked")
    if changed["count"]:
        high = f"   ▲ HIGH: {changed['over'][0]}" if changed["over"] else ""
        out.append(f"CHANGED  {changed['count']} files (+{changed['new']} new, −{changed['deleted']}) · +{changed['added']} −{changed['removed']}"
                   f" · uncommitted: {changed['uncommitted']}{high}")
        governed = ", ".join(os.path.basename(p) for p in facts["impact"]["governed"][:3]) or "none"
        protected = ", ".join(facts["impact"]["protected"][:2]) or "none"
        out.append(f"IMPACT   governed: {governed} · protected: {protected}")
    elif not changed["git"]:
        out.append("CHANGED  not a Git repository: nothing to compare against")
    if facts.get("design"):
        first = facts["design"][0]
        out.append(f"DESIGN   {first['epic']} design items not planned: {', '.join(first['not_planned'][:8])}"
                   + (f" · +{len(facts['design']) - 1} Epic(s)" if len(facts["design"]) > 1 else ""))
    if facts["risks"]:
        out.append("RISKS    " + " · ".join(facts["risks"][:3]) + (f" · +{len(facts['risks']) - 3} more" if len(facts["risks"]) > 3 else ""))
    if facts["decide"]:
        shown = "   ".join(f"{n}) {d['what']}" for n, d in enumerate(facts["decide"][:3], 1))
        out.append("DECIDE   " + shown + (f"   +{len(facts['decide']) - 3} more" if len(facts["decide"]) > 3 else ""))
    cache = facts["validation"]
    if cache:
        out.append(f"VALID    {cache.get('at', '')[11:16]} · {'OK' if cache['result'] == 'pass' else 'FAILED'} {cache.get('pass', 0)} PASS "
                   f"{cache.get('skipped', 0)} SKIPPED" + (f" {cache['fail']} FAIL" if cache.get("fail") else "") + (" · stale" if cache["stale"] else ""))
    else:
        out.append("VALID    not run")
    out.append(f"NEXT     {facts['next']}")
    out.append("more: gtt-review.sh --files · git diff --stat · gtt-status.sh")
    return [fit(line) for line in out][:MAX_LINES]


def gate_lines(facts):
    blocking = [d for d in facts["decide"] if d["level"] == "BLOCKING"]
    pending = [d for d in facts["decide"] if d["level"] == "GOVERNANCE"]
    changed = facts["changed"]
    out = ["@gtt · Review gate",
           "BLOCKING    " + (", ".join(d["what"] for d in blocking[:3]) if blocking else "none"),
           f"GOVERNANCE  {len(pending)} pending" + (": " + ", ".join(d["id"] for d in pending[:4]) if pending else ""),
           f"SIZE        {changed['count']} files · +{changed['added']} −{changed['removed']} "
           f"(thresholds: {facts['workflow']['review-files']} files, {facts['workflow']['review-lines']} lines)",
           "Human review: " + ("RECOMMENDED - " + "; ".join(changed["over"]) if changed["over"] else "not called for by size"),
           "Governance conditions: " + ("NOT met - a BLOCKING condition is open" if blocking else "met"),
           "This says whether the governance conditions hold. It does not say the design is right."]
    return [fit(line) for line in out], bool(blocking)


def cmd_review(args):
    facts = review_facts()
    if args.gate:
        lines, blocked = gate_lines(facts)
        if args.json:
            print(json.dumps(dict(facts, gate={"blocking": blocked, "human_review": "recommended" if facts["changed"]["over"] else "not-called-for"}),
                             indent=2, sort_keys=True))
        else:
            print("\n".join(lines))
        return 1 if blocked else 0
    if args.json:
        print(json.dumps(facts, indent=2, sort_keys=True))
    elif args.files:
        print("@gtt · Review - files")
        for path, status in sorted(facts["changed"]["files"].items()):
            print(f"  {status:9} {path}")
        if not facts["changed"]["files"]:
            print("  nothing changed against the base")
    else:
        print("\n".join(review_lines(facts)))
    return 0


def cmd_state(args):
    print(state_hash())
    return 0


# ------------------------------------------------------------------------- staging and promotion

def sha256(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def inside(path):
    """The path, normalised, when it is a relative path inside the project; else None."""
    norm = os.path.normpath(path).replace("\\", "/")
    return None if os.path.isabs(path) or norm.startswith("../") or norm in ("..", ".") else norm


def cmd_stage(args):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.name):
        print("gtt-stage: the set name may hold letters, digits, dot, dash and underscore.", file=sys.stderr)
        return 2
    folder = os.path.join(STAGED, args.name)
    files = []
    for pair in args.pairs:
        source, sep, dest = pair.partition("=")
        dest = inside(dest) if sep else None
        if not dest or not os.path.isfile(source):
            print(f"gtt-stage: `{pair}` must be SRC=DEST, with SRC an existing file and DEST a path inside the project.", file=sys.stderr)
            return 2
        staged = dest.replace("/", "__") + ".staged"
        os.makedirs(folder, exist_ok=True)
        if os.path.abspath(source) != os.path.abspath(os.path.join(folder, staged)):
            shutil.copyfile(source, os.path.join(folder, staged))
        files.append({"from": staged, "to": dest, "sha_before": sha256(dest)})
    with open(os.path.join(folder, "promote.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"schema": 1, "name": args.name, "reason": args.reason.strip().splitlines()[0], "files": files}, handle, indent=2)
        handle.write("\n")
    print(f"gtt-stage: {len(files)} file(s) staged in {folder}/. Nothing was applied.")
    print(f"The human applies it with: bash .gtt/scripts/gtt-promote.sh {args.name}")
    return 0


def load_set(name):
    folder = os.path.join(STAGED, name)
    spec = read_json(os.path.join(folder, "promote.json"))
    if not isinstance(spec, dict) or not isinstance(spec.get("files"), list) or not spec["files"]:
        return folder, None, f"no promotion set `{name}` ({folder}/promote.json is missing or empty)"
    for entry in spec["files"]:
        source = os.path.join(folder, str(entry.get("from", "")))
        if not inside(str(entry.get("to", ""))) or os.path.dirname(os.path.normpath(str(entry.get("from", "")))) or not os.path.isfile(source):
            return folder, None, f"`{entry.get('from')}` -> `{entry.get('to')}` is not a file of this set going to a path inside the project"
    return folder, spec, None


def diff_of(source, dest):
    old = (read(dest) or "").splitlines(True) if os.path.isfile(dest) else []
    new = (read(source) or "").splitlines(True)
    lines = list(difflib.unified_diff(old, new, "a/" + dest, "b/" + dest))
    added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    return lines, added, removed


def restore(name, quiet=False):
    """Put back what a promotion replaced, and remove what it created."""
    folder = os.path.join(BACKUPS, name)
    record = read_json(os.path.join(folder, "backup.json"))
    if not record:
        print(f"gtt-promote: nothing to undo for `{name}` ({folder}/backup.json not found).", file=sys.stderr)
        return 1
    for entry in record["files"]:
        if entry["existed"]:
            os.makedirs(os.path.dirname(entry["to"]) or ".", exist_ok=True)
            shutil.copyfile(os.path.join(folder, entry["backup"]), entry["to"])
        elif os.path.isfile(entry["to"]):
            os.remove(entry["to"])
    shutil.rmtree(folder, ignore_errors=True)
    if not quiet:
        print(f"gtt-promote: `{name}` undone - {len(record['files'])} file(s) back to what they were. Nothing was staged or committed.")
    return 0


FROZEN = "gtt-domain/.frozen"
ARCHITECTURE_FILES = ("gtt-domain/context/architecture.md", "gtt-domain/context/constraints.md")
BOUNDARY_SECTIONS = ("1", "2", "3", "4", "5", "7")


def map_sections(text):
    """{number: text} of the numbered sections of the stack map."""
    out, current = {}, None
    for line in (text or "").split("\n"):
        head = re.match(r"^## (\d+)\.", line)
        if head:
            current = head.group(1)
            out[current] = ""
        elif current:
            out[current] += line + "\n"
    return out


def blocking_lines(text):
    block = re.search(r"```gtt-gaps\r?\n(.*?)```", text or "", re.DOTALL)
    return sorted(l.strip() for l in (block.group(1).splitlines() if block else []) if l.strip().startswith("BLOCKING"))


def architectural_reasons(folder, spec):
    """Why a set is an architectural change, deterministically: it touches architecture.md or constraints.md,
    sections 1 to 5 or 7 of the stack map, or a BLOCKING gap. Anything else in governed context - a design,
    the glossary, the vision - is a specification change."""
    reasons = []
    for entry in spec["files"]:
        if entry["to"] in ARCHITECTURE_FILES:
            reasons.append(os.path.basename(entry["to"]))
        elif entry["to"] == STACK and entry.get("from"):
            old, new = read(STACK), read(os.path.join(folder, entry["from"]))
            before, after = map_sections(old), map_sections(new)
            moved = [n for n in BOUNDARY_SECTIONS if before.get(n) != after.get(n)]
            if moved:
                reasons.append("stack.md section " + ", ".join(moved))
            if blocking_lines(old) != blocking_lines(new):
                reasons.append("a BLOCKING gap")
    return reasons


def log_change(change_id, reason):
    """Add the row of a promoted specification change to section 6 of the stack map."""
    lines = (read(STACK) or "").split("\n")
    start = next((i for i, l in enumerate(lines) if re.match(r"^## 6\.", l)), None)
    if start is None:
        return False
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^(## |---\s*$)", lines[i])), len(lines))
    rows = [i for i in range(start, end) if lines[i].startswith("|")]
    if len(rows) < 2:
        return False
    row = f"| {datetime.date.today().isoformat()} | {change_id} | {reason.replace('|', '/')} |"
    blank = next((i for i in rows[2:] if not lines[i].replace("|", "").strip()), None)
    if blank is not None:
        lines[blank] = row
    else:
        lines.insert(rows[-1] + 1, row)
    with open(STACK, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    return True


def cmd_promote(args):
    if args.undo:
        return restore(args.name)
    folder, spec, problem = load_set(args.name)
    if problem:
        print(f"gtt-promote: {problem}.", file=sys.stderr)
        return 2
    print("@gtt · Promotion")
    print(f"Set: {args.name} - {spec.get('reason', '(no reason given)')}")
    diffs = {}
    for entry in spec["files"]:
        diffs[entry["to"]], added, removed = diff_of(os.path.join(folder, entry["from"]), entry["to"])
        print(f"  {'new     ' if entry.get('sha_before') is None else 'replaces'} {entry['to']}  +{added} −{removed}")
    while True:
        print("Type `apply` to apply, `d` to see the full diff, anything else to cancel: ", end="", flush=True)
        answer = sys.stdin.readline().strip()
        if answer != "d":
            break
        for lines in diffs.values():
            sys.stdout.writelines(lines)
    if answer != "apply":
        print("gtt-promote: not confirmed; nothing was written.", file=sys.stderr)
        return 1
    for entry in spec["files"]:
        if sha256(entry["to"]) != entry.get("sha_before"):
            print(f"gtt-promote: {entry['to']} changed since this set was prepared; nothing was written. Restage the set.", file=sys.stderr)
            return 1
    # A frozen design changes through one of two routes: architecture needs an ADR; a specification change
    # is promoted as it is and recorded as CHANGE-... in the map change log. Both end in a new freeze.
    frozen_change = os.path.isfile(FROZEN) and any(e["to"].startswith(GOVERNED_DIRS) for e in spec["files"])
    change_id = None
    if frozen_change:
        architectural = architectural_reasons(folder, spec)
        has_adr = any(re.match(r"^gtt-domain/adr/ADR-\d+.*\.md$", e["to"]) for e in spec["files"])
        if architectural and not has_adr:
            print("gtt-promote: this set changes the architecture (" + "; ".join(architectural) + ") and carries no ADR. "
                  "Nothing was written: an architectural change needs its ADR in the same set.", file=sys.stderr)
            return 1
        if not has_adr:
            change_id = f"CHANGE-{datetime.date.today().strftime('%Y%m%d')}-{args.name}"
            if not any(e["to"] == STACK for e in spec["files"]):
                spec["files"].append({"from": None, "to": STACK, "sha_before": sha256(STACK)})
    local_dir()
    backup = os.path.join(BACKUPS, args.name)
    shutil.rmtree(backup, ignore_errors=True)
    os.makedirs(backup)
    record = {"schema": 1, "name": args.name, "files": []}
    for number, entry in enumerate(spec["files"]):
        existed = os.path.isfile(entry["to"])
        if existed:
            shutil.copyfile(entry["to"], os.path.join(backup, f"{number}.orig"))
        record["files"].append({"to": entry["to"], "existed": existed, "backup": f"{number}.orig"})
    with open(os.path.join(backup, "backup.json"), "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    try:
        for entry in spec["files"]:
            if entry["from"] is None:
                continue
            os.makedirs(os.path.dirname(entry["to"]) or ".", exist_ok=True)
            mode = os.stat(entry["to"]).st_mode if os.path.isfile(entry["to"]) else None
            shutil.copyfile(os.path.join(folder, entry["from"]), entry["to"])
            if mode is not None:
                os.chmod(entry["to"], mode)
        if change_id and not log_change(change_id, spec.get("reason", "")):
            raise OSError(f"{STACK} has no map change log (section 6) to record {change_id} in")
    except OSError as error:
        restore(args.name, quiet=True)
        print(f"gtt-promote: failed ({error}); every file was put back. Nothing was changed.", file=sys.stderr)
        return 1
    if frozen_change:
        freeze = subprocess.run(["bash", os.path.join(".gtt", "scripts", "gtt-freeze.sh")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if freeze.returncode != 0:
            restore(args.name, quiet=True)
            print((freeze.stdout + freeze.stderr).rstrip(), file=sys.stderr)
            print("gtt-promote: the new freeze failed, so nothing was promoted: every file was put back.", file=sys.stderr)
            return 1
        print(("Specification change recorded as " + change_id + " in the map change log. " if change_id else "Architectural change, with its ADR. ")
              + "A new freeze was recorded with this confirmation.")
    shutil.rmtree(folder, ignore_errors=True)
    if os.path.isdir(STAGED) and not os.listdir(STAGED):
        os.rmdir(STAGED)
    print(f"Applied {len(spec['files'])} file(s). Nothing was staged or committed.")
    print(f"Undo: bash .gtt/scripts/gtt-promote.sh --undo {args.name}")
    maintain = os.path.join(".gtt", "scripts", "gtt-maintain.sh")
    if os.path.isfile(maintain):
        done = subprocess.run(["bash", maintain], capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(done.stdout.rstrip())
        return 0 if done.returncode == 0 else 1
    return 0


# ------------------------------------------------------------------------- static checks

MUTATING_GIT = r"(?:commit|tag|push|rebase|reset|merge|stash|cherry-pick|revert)"
PY_GIT = re.compile(r"""\[\s*["']git["']\s*,\s*["'](?:%s)["']|\bgit\(\s*["'](?:%s)["']|["']git["']\s*,\s*["'](?:switch|checkout|branch)["']\s*,\s*["']-[cCbB]["']"""
                    % (MUTATING_GIT, MUTATING_GIT))
SH_GIT = re.compile(r"""(?:^|[;&|(]\s*|\bthen\s+|\bdo\s+|\$\(\s*)git\s+(?:-[A-Za-z-]+\s+(?:[^-\s]\S*\s+)?)*(?:(?:%s)\b(?!\s+(?:-l|--list)\b)|switch\s+-[cC]\b|checkout\s+-[bB]\b|branch\s+[^-\s])"""
                    % MUTATING_GIT)


def hook_commands(path):
    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                yield from walk(value)
        elif isinstance(node, list):
            for value in node:
                yield from walk(value)
        elif isinstance(node, str):
            yield node
    return list(walk(read_json(path) or {}))


def check_no_commits():
    """GTT never writes Git history: no script of the engine and no hook runs a command that does."""
    hits = []
    for path in sorted(glob.glob(".gtt/scripts/*.py") + glob.glob(".claude/hooks/*.py")):
        for number, line in enumerate((read(path) or "").splitlines(), 1):
            if PY_GIT.search(line) and not line.lstrip().startswith("#"):
                hits.append(f"{path}:{number}: {line.strip()[:90]}")
    for path in sorted(glob.glob(".gtt/scripts/*.sh")):
        for number, line in enumerate((read(path) or "").splitlines(), 1):
            code = line.strip()
            if code.startswith(("#", "echo ", "printf ")):
                continue
            if SH_GIT.search(code):
                hits.append(f"{path}:{number}: {code[:90]}")
    for path in sorted([".claude/settings.json", ".cursor/hooks.json", ".openhands/hooks.json", ".agents/hooks.json"]
                       + glob.glob(".kiro/hooks/*.json") + glob.glob(".github/hooks/gtt*.json")):
        for command in hook_commands(path):
            if SH_GIT.search(command):
                hits.append(f"{path}: {command[:90]}")
    return hits


def contract_block():
    """The `## Git and workflow` section of the agent contract, heading included."""
    found = re.search(r"(?ms)^## Git and workflow\n.*?(?=^## |\Z)", read(CONTRACT) or "")
    return found.group(0).rstrip("\n") + "\n" if found else None


def check_overlay_block():
    block = contract_block()
    if block is None:
        return [f"{CONTRACT} has no `## Git and workflow` section"]
    return [f"{path} does not carry the `## Git and workflow` section of {CONTRACT} byte for byte"
            for path in OVERLAYS if os.path.isfile(path) and block not in (read(path) or "")]


def check_ar_rules():
    invariants = {i.get("id"): i for i in (read_json(PROFILES) or {}).get("invariants", [])}
    problems = []
    for rule in AR_RULES:
        entry = invariants.get(rule)
        if entry is None:
            problems.append(f"{rule} is not in {PROFILES} -> invariants")
        elif entry.get("relaxable") is not False or not entry.get("enforcement"):
            problems.append(f"{rule} must be relaxable: false and state its enforcement")
        elif not entry.get("statement") and entry.get("same_as") not in invariants:
            problems.append(f"{rule} needs its statement, or `same_as` naming an existing invariant")
    return problems


CHECKS = {"no-commits": (check_no_commits, "no GTT script or hook writes Git history"),
          "overlay-block": (check_overlay_block, "the Git and workflow section is identical in every overlay"),
          "ar-rules": (check_ar_rules, "GTT-AR-01 to GTT-AR-10 are in the contract")}


def cmd_check(args):
    run, label = CHECKS[args.which]
    problems = run()
    for problem in problems:
        print(f"gtt-flow: FAILED - {problem}", file=sys.stderr)
    if not problems:
        print(f"gtt-flow: OK - {label}.")
    return 1 if problems else 0


def cmd_record_validation(args):
    """Called by gtt-validate.sh only: remember the result against the state it was computed for."""
    local_dir()
    with open(VALIDATION, "w", encoding="utf-8") as handle:
        json.dump({"schema": 1, "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "state": state_hash(),
                   "result": "pass" if args.exit == 0 else "fail", "pass": args.passed, "skipped": args.skipped, "fail": args.failed}, handle, indent=2)
    return 0


def main(argv):
    if not os.path.isdir(".gtt"):
        print("gtt-flow: run from the project root (no .gtt/ directory here)", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog="gtt_flow.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("workflow"); p.add_argument("action", choices=("get", "check", "detect")); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_workflow)
    p = sub.add_parser("review"); p.add_argument("--files", action="store_true"); p.add_argument("--json", action="store_true")
    p.add_argument("--gate", action="store_true"); p.set_defaults(func=cmd_review)
    p = sub.add_parser("state"); p.set_defaults(func=cmd_state)
    p = sub.add_parser("stage"); p.add_argument("name"); p.add_argument("--reason", required=True); p.add_argument("pairs", nargs="+"); p.set_defaults(func=cmd_stage)
    p = sub.add_parser("promote"); p.add_argument("--undo", action="store_true"); p.add_argument("name"); p.set_defaults(func=cmd_promote)
    p = sub.add_parser("check"); p.add_argument("which", choices=sorted(CHECKS)); p.set_defaults(func=cmd_check)
    p = sub.add_parser("record-validation"); p.add_argument("--exit", type=int, required=True); p.add_argument("--passed", type=int, default=0)
    p.add_argument("--skipped", type=int, default=0); p.add_argument("--failed", type=int, default=0); p.set_defaults(func=cmd_record_validation)
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
