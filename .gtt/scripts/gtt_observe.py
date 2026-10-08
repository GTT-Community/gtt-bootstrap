#!/usr/bin/env python3
"""GTT - Observation engine (the Work plane).

Governance decides what the system is supposed to be; this engine reports what is actually
happening. It never approves work and never asks for approval: it compares the project with the
frozen governed state, turns each meaningful deviation into a signal, and keeps the signals in a
durable governance backlog so that nothing is lost and nothing is reported twice.

Facts are computed, never judged: Git, the filesystem, dependency manifests, the GTTGuard registry
and the freeze baseline. No model takes part. What a fact MEANS is decided by policy the human
ratified - the `gtt-boundaries` block of gtt-domain/context/stack.md - and, for the built-in
boundaries, by the method itself.

  observe             run every observer, update the backlog, print what is NEW (silent otherwise)
  check               the same, for CI, freeze and promotion: fail on what must stop
  backlog [--all]     the governance backlog: every observation still open
  show ID             one observation in full
  accept|reject|defer ID --by NAME [--note TEXT] [--apply]
                      a human decision on an observation (a dry run without --apply)
  baseline            the freeze baseline this project is observed against
  digest              the digest of the governed state as it is now
  boundaries          the declared boundaries, as parsed

Levels (graduated enforcement). Only BLOCKING interrupts work:

  NOTICE      recorded, never announced
  WARNING     announced once, recorded; work continues
  GOVERNANCE  announced once, recorded; work continues; a decision is needed before the next
              freeze (and before promotion where the selected Method Plan says so)
  BLOCKING    announced every time; `check` fails; hook-capable ADEs deny the affected write

A boundary blocks only because the governed state says so: a rule declared BLOCKING in
`gtt-boundaries`, or an observation the human explicitly rejected. A detector that merely finds
something unusual never blocks.

Boundary rule, one per line:   ID | kind | match | LEVEL | what it guards

  path        a file matching the glob changed since the freeze baseline
  dependency  the manifest gained a dependency it did not have at the freeze baseline
  forbid      `glob :: regex` - a file matching the glob contains the pattern (current state)

Legacy `gtt-drift-signals` lines (`glob -> what it guards`) are read as path rules at WARNING.

Exit 0 = nothing that must stop, 1 = a BLOCKING condition (or a failed check), 2 = cannot run.
"""

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SCHEMA = 1
FROZEN = "gtt-domain/.frozen"
STACK = "gtt-domain/context/stack.md"
LEDGER = "gtt-domain/governance-backlog.json"
REGISTRY = ".gtt/protection/registry.yaml"
GOVERNED_DIRS = ("gtt-domain/context", "gtt-domain/adr")
OWN = (".gtt/", "gtt-domain/", ".git/")
LEVELS = ("NOTICE", "WARNING", "GOVERNANCE", "BLOCKING")
KINDS = ("path", "dependency", "forbid")
OPEN_STATES = ("open", "deferred", "rejected")
NOTICE_TEXT = ("Governance backlog: observations GTT derived from the project against the frozen governed "
               "state, and the human decisions taken on them. Written only by .gtt/scripts/gtt-observe.sh; "
               "never hand-edited. An observation is a signal, never a decision and never authority.")
MAX_SCAN = 1_000_000

BLOCK = r"```{name}\r?\n(.*?)```"
RULE = re.compile(r"^\s*([A-Za-z][\w-]*)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|\s*([A-Za-z]+)\s*\|\s*(.+?)\s*$")
LEGACY = re.compile(r"^\s*([^#\s][^\s]*)\s*->\s*(.+?)\s*$")


def die(message, code=2):
    print(f"gtt-observe: {message}", file=sys.stderr)
    sys.exit(code)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def digest(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def git(*args):
    """stdout of a git command, or None when git cannot answer."""
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return None
    return proc.stdout if proc.returncode == 0 else None


def match(path, glob):
    return fnmatch.fnmatch(path, glob) or (glob.startswith("**/") and fnmatch.fnmatch(path, glob[3:]))


# ----------------------------------------------------------------- governed state

def governed_digest():
    """One hash of everything under the governed directories: the reference the baseline records."""
    acc = hashlib.sha256()
    for base in GOVERNED_DIRS:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                acc.update(full.replace("\\", "/").encode())
                with open(full, "rb") as handle:
                    acc.update(handle.read().replace(b"\r\n", b"\n"))
    return acc.hexdigest()


def baseline():
    """The freeze baseline: {frozen, at, commit, digest}. A freeze that predates baselines has neither
    commit nor digest; the observers that need them then report nothing rather than guess."""
    if not os.path.isfile(FROZEN):
        return {"frozen": False}
    lines = read(FROZEN).splitlines()
    out = {"frozen": True, "at": lines[0].strip() if lines else "", "commit": None, "digest": None}
    for line in lines:
        if line.startswith("#"):
            break                                           # earlier freezes follow; the first block is current
        key, _, value = line.partition(":")
        if key.strip() == "Baseline commit" and value.strip() not in ("", "none"):
            out["commit"] = value.strip()
        elif key.strip() == "Governed digest" and value.strip():
            out["digest"] = value.strip()
    return out


def boundaries():
    """Declared boundary rules, plus the problems found while parsing them."""
    rules, problems = [], []
    if not os.path.isfile(STACK):
        return rules, problems
    text = read(STACK)
    block = re.search(BLOCK.format(name="gtt-boundaries"), text, re.DOTALL)
    for number, line in enumerate((block.group(1) if block else "").splitlines(), 1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        hit = RULE.match(line)
        if not hit:
            problems.append(f"gtt-boundaries line {number}: expected `ID | kind | match | LEVEL | what it guards`")
            continue
        rid, kind, target, level, guards = hit.groups()
        if kind not in KINDS:
            problems.append(f"{rid}: unknown kind `{kind}` (one of {', '.join(KINDS)})")
        elif level.upper() not in LEVELS:
            problems.append(f"{rid}: unknown level `{level}` (one of {', '.join(LEVELS)})")
        elif any(r["id"] == rid for r in rules):
            problems.append(f"{rid}: declared twice")
        elif kind == "forbid" and "::" not in target:
            problems.append(f"{rid}: a forbid rule is `glob :: regex`")
        else:
            rules.append({"id": rid, "kind": kind, "match": target, "level": level.upper(), "guards": guards})
    legacy = re.search(BLOCK.format(name="gtt-drift-signals"), text, re.DOTALL)
    for line in (legacy.group(1) if legacy else "").splitlines():
        hit = LEGACY.match(line) if line.strip() and not line.strip().startswith("#") else None
        if hit:
            rules.append({"id": "DS-" + digest(hit.group(1))[:6], "kind": "path", "match": hit.group(1),
                          "level": "WARNING", "guards": hit.group(2)})
    return rules, problems


# ---------------------------------------------------------------------- observers

def changed_since(commit):
    """Project-relative paths that differ from the baseline commit (committed, staged, unstaged,
    untracked), or None when Git cannot tell."""
    if not commit or git("cat-file", "-e", commit + "^{commit}") is None:
        return None
    diff, extra = git("diff", "--name-only", commit), git("ls-files", "--others", "--exclude-standard")
    if diff is None:
        return None
    return sorted({p for p in (diff + (extra or "")).splitlines() if p.strip()})


def tracked():
    out = git("ls-files", "--cached", "--others", "--exclude-standard")
    if out is not None:
        return [p for p in out.splitlines() if p.strip()]
    found = []
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
        found += [os.path.relpath(os.path.join(dirpath, n), ".").replace("\\", "/") for n in filenames]
    return found


def own(path):
    return path.startswith(OWN)


def file_state(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()[:16]
    except OSError:
        return "absent"


def dependencies(name, text):
    """Dependency names a manifest declares, or None when its format is not one this engine parses."""
    base = os.path.basename(name).lower()
    try:
        if base == "package.json":
            doc = json.loads(text)
            keys = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
            return {dep for key in keys for dep in (doc.get(key) or {})}
        if base.startswith("requirements") and base.endswith(".txt"):
            return {re.split(r"[\s<>=!~;\[@]", line.strip(), 1)[0].lower() for line in text.splitlines()
                    if line.strip() and not line.strip().startswith(("#", "-"))}
        if base == "go.mod":
            return set(re.findall(r"^\s*(?:require\s+)?([\w.-]+\.[\w.-]+/[^\s]+)\s+v[\w.+-]+", text, re.M))
        if base in ("pyproject.toml", "cargo.toml"):
            import tomllib
            doc = tomllib.loads(text)
            if base == "cargo.toml":
                return {dep for key in ("dependencies", "dev-dependencies", "build-dependencies") for dep in (doc.get(key) or {})}
            listed = list((doc.get("project") or {}).get("dependencies") or [])
            for group in ((doc.get("project") or {}).get("optional-dependencies") or {}).values():
                listed += list(group)
            return {re.split(r"[\s<>=!~;\[@]", dep.strip(), 1)[0].lower() for dep in listed}
    except Exception:
        return None
    return None


def observe_rules(rules, base):
    signals, notes = [], []
    changed = changed_since(base.get("commit"))
    if changed is None and any(r["kind"] in ("path", "dependency") for r in rules):
        notes.append("the freeze baseline has no commit this repository can resolve: path and dependency "
                     "boundaries cannot be compared (re-freeze to record one)")
    files = None
    for rule in rules:
        if rule["kind"] == "path" and changed is not None:
            for path in changed:
                if not own(path) and match(path, rule["match"]):
                    signals.append(signal(rule, path, "changed since the freeze baseline", file_state(path)))
        elif rule["kind"] == "dependency" and changed is not None:
            for path in changed:
                if own(path) or not match(path, rule["match"]) or not os.path.isfile(path):
                    continue
                now = dependencies(path, read(path))
                before_text = git("show", f"{base['commit']}:{path}")
                before = dependencies(path, before_text) if before_text is not None else None
                if now is None or before_text is None or before is None:
                    reason = "is new since the freeze baseline" if before_text is None else "changed (format not parsed)"
                    signals.append(signal(rule, path, f"dependency manifest {reason}", file_state(path)))
                    continue
                for dep in sorted(now - before):
                    signals.append(signal(rule, f"{path}#{dep}", f"new dependency `{dep}`", "present"))
        elif rule["kind"] == "forbid":
            glob, _, pattern = (part.strip() for part in rule["match"].partition("::"))
            try:
                regex = re.compile(pattern)
            except re.error as exc:
                notes.append(f"{rule['id']}: invalid pattern ({exc})")
                continue
            files = tracked() if files is None else files
            for path in files:
                if own(path) or not match(path, glob) or not os.path.isfile(path) or os.path.getsize(path) > MAX_SCAN:
                    continue
                for number, line in enumerate(read(path).splitlines(), 1):
                    if regex.search(line):
                        signals.append(signal(rule, path, f"line {number}: {line.strip()[:120]}", file_state(path)))
                        break
    return signals, notes


def observe_governed(base):
    """The governed state itself moved since the freeze: it needs a new freeze, never an unfreeze."""
    if not base.get("digest") or governed_digest() == base["digest"]:
        return []
    changed = changed_since(base.get("commit")) or []
    which = [p for p in changed if p.startswith(tuple(d + "/" for d in GOVERNED_DIRS))]
    rule = {"id": "GTT-GOVERNED", "kind": "governed", "level": "GOVERNANCE",
            "guards": "the frozen governed state (gtt-domain/.frozen); a governed change is completed by a new freeze"}
    return [signal(rule, "gtt-domain/context+adr", "governed context or ADRs differ from the freeze baseline"
                   + (": " + ", ".join(which[:6]) if which else ""), governed_digest()[:16])]


def observe_protected(base):
    """A GTTGuard-protected artifact changed since the freeze baseline."""
    changed = changed_since(base.get("commit"))
    if changed is None or not os.path.isfile(REGISTRY):
        return []
    try:
        import gtt_guard
        entries = [e for e in gtt_guard.parse_registry(read(REGISTRY)) if e.get("protection") == "HUMAN_APPROVAL"]
    except Exception:
        return []
    rule = {"id": "GTT-PROTECTED", "kind": "protected", "level": "GOVERNANCE",
            "guards": "a @GTTGuard marker (.gtt/protection/registry.yaml): changed only with the Solution Designer's approval"}
    out = []
    for entry in entries:
        artifact = entry["artifact"].replace("\\", "/")
        if artifact not in changed:
            continue
        symbol = entry.get("symbol") or ""
        if symbol and unchanged_symbol(gtt_guard, artifact, symbol, base["commit"]):
            continue
        target = f"{artifact}#{symbol}" if symbol else artifact
        out.append(signal(rule, target, "protected artifact changed since the freeze baseline", file_state(artifact)))
    return out


def observe_commits():
    """With `convention: conventional` in gtt-domain/workflow.md: one NOTICE for each commit subject since
    the merge base with the default branch that is not a Conventional Commit. It informs and never blocks."""
    try:
        import gtt_flow
        values = gtt_flow.workflow()[0]
        start = gtt_flow.base_ref() if values["convention"] == "conventional" else None
    except Exception:
        return []
    log = git("log", "--no-merges", "--format=%h%x09%s", f"{start}..HEAD") if start else None
    rule = {"id": "GTT-COMMITS", "kind": "convention", "level": "NOTICE", "guards": "gtt-domain/workflow.md - convention: conventional"}
    out = []
    for entry in (log or "").splitlines():
        sha, _, subject = entry.partition("\t")
        if subject and not gtt_flow.CONVENTIONAL.match(subject):
            out.append(signal(rule, sha, f"commit subject is not a Conventional Commit: {subject[:80]}", subject))
    return out


def unchanged_symbol(guard, artifact, symbol, commit):
    """True only when the protected symbol's own text is provably the same as at the baseline."""
    import tempfile
    before = git("show", f"{commit}:{artifact}")
    if before is None or not os.path.isfile(artifact):
        return False
    with tempfile.TemporaryDirectory(prefix="gtt-observe-") as tmp:
        target = os.path.join(tmp, artifact)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="") as handle:
            handle.write(before)
        try:
            old, new = guard.resolve_symbol_span(tmp, artifact, symbol), guard.resolve_symbol_span(".", artifact, symbol)
        except Exception:
            return False
    if old is None or new is None:
        return False
    return before.splitlines()[old[0]:old[1] + 1] == read(artifact).splitlines()[new[0]:new[1] + 1]


def signal(rule, artifact, detail, state):
    return {"fingerprint": digest(rule["id"] + "\0" + artifact)[:16], "rule": rule["id"], "kind": rule["kind"],
            "level": rule["level"], "artifact": artifact, "guards": rule["guards"], "detail": detail, "state": state}


def collect():
    """(signals, notes, base). Before the first freeze nothing is ratified, so nothing is observed."""
    base = baseline()
    if not base["frozen"]:
        return [], ["not frozen yet: there is no governed state to observe against"], base
    rules, problems = boundaries()
    signals, notes = observe_rules(rules, base)
    signals += observe_governed(base) + observe_protected(base) + observe_commits()
    seen, unique = set(), []
    for sig in signals:
        if sig["fingerprint"] not in seen:
            seen.add(sig["fingerprint"])
            unique.append(sig)
    return unique, problems + notes, base


# ------------------------------------------------------------------------- ledger

def load_ledger():
    if not os.path.isfile(LEDGER):
        return {"schema": SCHEMA, "notice": NOTICE_TEXT, "next": 1, "items": []}
    try:
        ledger = json.loads(read(LEDGER))
    except ValueError as exc:
        die(f"{LEDGER} is not valid JSON: {exc}")
    if ledger.get("schema") != SCHEMA:
        die(f"{LEDGER}: unsupported schema {ledger.get('schema')!r}")
    return ledger


def save_ledger(ledger, before):
    """Write only when something changed: observing the same state twice leaves no trace."""
    text = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    if text == before or (not ledger["items"] and not os.path.isfile(LEDGER)):
        return
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def correlate(ledger, signals):
    """Fold the current signals into the backlog. Returns the items that are NEW to the human: first
    seen, seen again after it had gone, or changed since the human decided on it."""
    today = datetime.date.today().isoformat()
    by_print = {item["fingerprint"]: item for item in ledger["items"]}
    fresh, present = [], set()
    for sig in signals:
        present.add(sig["fingerprint"])
        item = by_print.get(sig["fingerprint"])
        if item is None:
            item = dict(sig, id=f"OBS-{ledger['next']:04d}", status="open", first_seen=today)
            ledger["next"] += 1
            ledger["items"].append(item)
            fresh.append(item)
            continue
        decided = (item.get("decision") or {}).get("state")
        if item["status"] == "resolved" or (item["status"] == "accepted" and decided != sig["state"]):
            item.update(status="open", reopened=today)
            item.pop("resolution", None)
            fresh.append(item)
        item.update({k: sig[k] for k in ("level", "guards", "detail", "state", "rule", "kind", "artifact")})
    for item in ledger["items"]:
        if item["fingerprint"] not in present and item["status"] in OPEN_STATES:
            item.update(status="resolved", resolution="no longer observed", resolved=today)
    return fresh


def stops(item):
    """A reason this observation must stop the affected operation, or None. Both reasons are explicit
    governance: a boundary the human ratified as BLOCKING, or a deviation the human rejected."""
    if item["status"] == "rejected":
        return "rejected by " + (item.get("decision") or {}).get("by", "the human") + " and still present"
    if item["status"] == "open" and item["level"] == "BLOCKING":
        return "boundary declared BLOCKING in the governed state"
    return None


def plan_gate():
    """True when the selected Method Plan makes an undecided GOVERNANCE observation fail `check`."""
    try:
        spec = json.loads(read(".gtt/contract/profiles.json"))
        chosen = json.loads(read(".gtt/methodology.json")).get("profile") if os.path.isfile(".gtt/methodology.json") else None
        gates = spec["profiles"][chosen or spec["default"]]["gates"]
        return bool(gates.get("governance_observation_fails_check"))
    except Exception:
        return False


# ----------------------------------------------------------------------- commands

MARK = {"NOTICE": "·", "WARNING": "⚠", "GOVERNANCE": "◆", "BLOCKING": "✗"}


def line(item):
    stop = stops(item)
    tail = f"STOP: {stop}" if stop else {"NOTICE": "recorded", "WARNING": "work continues",
                                         "GOVERNANCE": "work continues; decide before the next freeze"}.get(item["level"], "")
    status = "" if item["status"] == "open" else f" [{item['status']}]"
    return (f"{MARK[item['level']]} {item['id']} {item['level']:10} {item['rule']}  {item['artifact']}{status}\n"
            f"    {item['detail']}\n    guards: {item['guards']}\n    {tail}")


def run(args, checking):
    signals, notes, base = collect()
    ledger = load_ledger()
    before = json.dumps(ledger, indent=2, sort_keys=True) + "\n" if os.path.isfile(LEDGER) else None
    fresh = correlate(ledger, signals) if base["frozen"] else []
    if not args.dry_run:
        save_ledger(ledger, before)
    stopping = [i for i in ledger["items"] if stops(i)]
    pending = [i for i in ledger["items"] if i["status"] == "open" and i["level"] == "GOVERNANCE"]
    failing = list(stopping)
    if checking and (args.strict or plan_gate()):
        failing += [i for i in pending if i not in failing and not (args.for_freeze and i["rule"] == "GTT-GOVERNED")]
    announce = [i for i in fresh if i["level"] != "NOTICE" and i not in stopping] + stopping
    if checking:
        announce = failing + [i for i in announce if i not in failing]
    if args.json:
        print(json.dumps({"schema": SCHEMA, "frozen": base["frozen"], "baseline": base, "notes": notes,
                          "new": [i["id"] for i in fresh], "stopping": [i["id"] for i in stopping],
                          "pending_governance": [i["id"] for i in pending],
                          "result": "fail" if (failing if checking else stopping) else "pass",
                          "items": [i for i in ledger["items"] if i["status"] in OPEN_STATES]}, indent=2, sort_keys=True))
    else:
        if announce:
            print("@gtt · Observation")
            print("\n".join(line(i) for i in announce))
            print("  detail: bash .gtt/scripts/gtt-observe.sh backlog")
        elif args.verbose or checking:
            count = sum(1 for i in ledger["items"] if i["status"] in OPEN_STATES)
            print(f"gtt-observe: nothing to stop ({count} open observation(s) in the governance backlog).")
        if args.verbose:
            for note in notes:
                print(f"  note: {note}")
    if any(n.startswith("gtt-boundaries") or ": unknown" in n or "declared twice" in n or "forbid rule" in n
           or "invalid pattern" in n for n in notes):
        for note in notes:
            print(f"gtt-observe: {note}", file=sys.stderr)
        return 1 if checking else 0
    return 1 if (failing if checking else stopping) else 0


def debounced(seconds):
    """True when an observation ran for this project less than `seconds` ago. A hook that fires after
    every write asks for this, so a burst of edits costs one observation and not one per edit. Nothing
    is lost: what a skipped run would have seen is seen by the next one, at commit, in validation and at
    session start. The stamp lives in the system's temp directory, never in the project."""
    stamp = os.path.join(tempfile.gettempdir(), "gtt-observe-" + hashlib.sha1(os.getcwd().encode("utf-8")).hexdigest()[:16])
    try:
        if time.time() - os.path.getmtime(stamp) < seconds:
            return True
    except OSError:
        pass
    try:
        with open(stamp, "w", encoding="utf-8"):
            pass
    except OSError:
        pass
    return False


def cmd_observe(args):
    if getattr(args, "debounce", 0) and debounced(args.debounce):
        return 0
    return run(args, False)


def cmd_check(args):
    return run(args, True)


def cmd_backlog(args):
    ledger = load_ledger()
    items = [i for i in ledger["items"] if args.all or i["status"] in OPEN_STATES]
    if args.json:
        print(json.dumps({"schema": SCHEMA, "items": items}, indent=2, sort_keys=True))
        return 0
    if not items:
        print("Governance backlog: empty.")
        return 0
    print(f"Governance backlog - {len(items)} observation(s)" + ("" if args.all else " open"))
    print("\n".join(line(i) for i in sorted(items, key=lambda i: (-LEVELS.index(i["level"]), i["id"]))))
    return 0


def cmd_summary(args):
    ledger = load_ledger()
    open_items = [i for i in ledger["items"] if i["status"] in OPEN_STATES]
    counts = {level: sum(1 for i in open_items if i["level"] == level and i["status"] == "open") for level in LEVELS}
    deferred = sum(1 for i in open_items if i["status"] == "deferred")
    rejected = sum(1 for i in open_items if i["status"] == "rejected")
    print(f"open: BLOCKING {counts['BLOCKING']}, GOVERNANCE {counts['GOVERNANCE']}, WARNING {counts['WARNING']}, "
          f"NOTICE {counts['NOTICE']}; deferred {deferred}; rejected and still present {rejected}")
    return 0


def find(ledger, ident):
    for item in ledger["items"]:
        if item["id"].lower() == ident.lower():
            return item
    die(f"no observation `{ident}` in {LEDGER}", 1)


def cmd_show(args):
    print(json.dumps(find(load_ledger(), args.id), indent=2, sort_keys=True))
    return 0


def cmd_decide(args):
    ledger = load_ledger()
    before = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    item = find(ledger, args.id)
    status = {"accept": "accepted", "reject": "rejected", "defer": "deferred"}[args.command]
    if item["status"] == "resolved":
        die(f"{item['id']} is resolved (no longer observed); there is nothing to decide.", 1)
    print(f"{item['id']} {item['level']} {item['rule']} {item['artifact']}: {item['status']} -> {status} (by {args.by})")
    if status == "accepted":
        print("  accepted: this deviation stands. If it means the governed design itself changes, that still goes\n"
              "  through gtt-domain/change-request.md and a new freeze - accepting an observation ratifies nothing.")
    elif status == "rejected":
        print("  rejected: `check` fails for as long as this is still observed.")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    item.update(status=status, decision={"by": args.by, "date": datetime.date.today().isoformat(),
                                         "note": args.note or "", "state": item["state"]})
    save_ledger(ledger, before)
    print(f"gtt-observe: recorded in {LEDGER}.")
    return 0


def cmd_baseline(args):
    base = baseline()
    base["governed_digest_now"] = governed_digest()
    base["head"] = (git("rev-parse", "HEAD") or "").strip() or None
    if args.json:
        print(json.dumps(base, indent=2, sort_keys=True))
    elif not base["frozen"]:
        print("not frozen: no baseline yet.")
    else:
        moved = base["digest"] is not None and base["digest"] != base["governed_digest_now"]
        print(f"frozen: {base['at']}\nbaseline commit: {base['commit'] or 'not recorded'}\n"
              f"governed digest: {base['digest'] or 'not recorded'}"
              + ("\ngoverned state has moved since the freeze: a new freeze is needed" if moved else ""))
    return 0


def cmd_boundaries(args):
    rules, problems = boundaries()
    if args.json:
        print(json.dumps({"schema": SCHEMA, "rules": rules, "problems": problems}, indent=2, sort_keys=True))
    else:
        for rule in rules:
            print(f"{rule['id']:12} {rule['kind']:10} {rule['level']:10} {rule['match']}   -> {rule['guards']}")
        for problem in problems:
            print(f"problem: {problem}", file=sys.stderr)
        if not rules:
            print("no boundaries declared (gtt-boundaries block of gtt-domain/context/stack.md).")
    return 1 if problems else 0


def blocking_path(path):
    """For a pre-write hook: (rule id, what it guards) of a BLOCKING path boundary this project-relative
    path falls under, once frozen - or None. Nothing else is ever blocked before it happens."""
    if not os.path.isfile(FROZEN) or own(path):
        return None
    for rule in boundaries()[0]:
        if rule["kind"] == "path" and rule["level"] == "BLOCKING" and match(path, rule["match"]):
            return rule["id"], rule["guards"]
    return None


def main(argv):
    if not os.path.isdir(".gtt"):
        die("run from the project root (no .gtt/ directory here)")
    parser = argparse.ArgumentParser(prog="gtt-observe.sh", description="GTT observation engine")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("observe", cmd_observe), ("check", cmd_check)):
        p = sub.add_parser(name)
        p.add_argument("--json", action="store_true")
        p.add_argument("--verbose", action="store_true")
        p.add_argument("--dry-run", action="store_true", help="do not update the governance backlog")
        p.add_argument("--strict", action="store_true", help="check: an undecided GOVERNANCE observation fails too")
        p.add_argument("--for-freeze", action="store_true", help="check: the governed state having moved is expected")
        p.add_argument("--debounce", type=int, default=0, metavar="SECONDS",
                       help="observe: do nothing if an observation ran less than SECONDS ago (for a hook that fires on every write)")
        p.set_defaults(func=func)
    p = sub.add_parser("backlog"); p.add_argument("--all", action="store_true"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_backlog)
    p = sub.add_parser("summary"); p.set_defaults(func=cmd_summary)
    p = sub.add_parser("show"); p.add_argument("id"); p.set_defaults(func=cmd_show)
    for name in ("accept", "reject", "defer"):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--by", required=True, help="the person deciding")
        p.add_argument("--note")
        p.add_argument("--apply", action="store_true", help="write (default is a dry run)")
        p.set_defaults(func=cmd_decide)
    p = sub.add_parser("digest"); p.set_defaults(func=lambda a: print(governed_digest()) or 0)
    p = sub.add_parser("baseline"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_baseline)
    p = sub.add_parser("boundaries"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_boundaries)
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
