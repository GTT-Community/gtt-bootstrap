#!/usr/bin/env python3
"""GTT ADR-004 migration engine (.gtt/ Engine, gtt-domain/ governed domain) - staged, human-executed.

Derived from the ADR-003 engine (proposals/migration-engine-adr-003/), which was rehearsed and applied.
Status: Draft - not a decision. Prepared by an agent; run only through
proposals/apply-gtt-domain-migration.sh, by a human.

Everything mechanical the restructure does lives here so it can be reviewed in
one place and rehearsed on a throw-away clone:

  preflight   verify the repository is in exactly the expected pre-migration
              state (or report that it is already migrated); changes nothing
  plan        print every move, rewrite and overlay; changes nothing
  apply       move files (git mv), rewrite path references and relative links,
              apply exact-text patches, overlay staged files, update artifact
              identity, remove stale/generated files; aborts before writing
              anything if any precondition does not hold
  oldrefs     search for the old paths and classify every hit
              (VALID / HISTORICAL / DERIVED / STALE / ERROR)
  verify      structural check of the result against the scaffold manifest

It never touches .frozen's content (the marker is moved to gtt-domain/.frozen, and its bytes
are compared before and after), never runs gtt-freeze.sh, and never commits.
Governed context (L0) is MOVED here; its text changes only through the ADR-004 promotion script.
"""

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys

# --------------------------------------------------------------- path map

# Exact files. Everything not listed here (and not under a DIR_MAP prefix) stays where it is:
# the entry points (AGENTS.md, readme-gtt*.md, SOURCE-BRIEF.*), the ADE overlays, LICENSE, .gitignore.
FILE_MAP = {
    "backlog.md": "gtt-domain/backlog.md",
    "change-request.md": "gtt-domain/change-request.md",
    "session.md": "gtt-domain/session.md",
    ".frozen": "gtt-domain/.frozen",
    "gtt/README.md": ".gtt/README.md",
}

# Engine -> .gtt/ ; GTT documentation -> .gtt/docs/ ; Project Governance -> gtt-domain/
DIR_MAP = [
    ("gtt/index/", ".gtt/index/"),
    ("gtt/protection/", ".gtt/protection/"),
    ("gtt/scaffold/", ".gtt/scaffold/"),
    ("gtt/scripts/", ".gtt/scripts/"),
    ("gtt/session-adapters/", ".gtt/session-adapters/"),
    ("docs/", ".gtt/docs/"),
    ("context/", "gtt-domain/context/"),
    ("adr/", "gtt-domain/adr/"),
    ("proposals/", "gtt-domain/proposals/"),
]

# No file is renamed by this migration (ADR-003 already lower-cased the names).
BARE_RENAMES = {}

# Files removed by the migration, with their classification (ADR-003 already removed the versioned bytecode).
REMOVE = {}

PKG_REL = "gtt-domain/proposals/gtt-domain-migration"   # after the move
PKG_OLD = "proposals/gtt-domain-migration"              # before the move

# Files whose old-layout mentions are historical/draft records, not live references. They are neither
# rewritten nor reported as ERROR. Patterns are over FINAL paths.
HISTORICAL_FILES = [
    r"^gtt-domain/adr/ADR-\d{3}-",                     # accepted ADRs: records of their time
    r"^\.gtt/docs/gtt-completion\.md$",                 # append-only completion log
    r"^gtt-domain/proposals/PROPOSAL-",                 # drafts awaiting a decision
    r"^gtt-domain/proposals/GOVERNANCE-PACKAGE-",
    r"^gtt-domain/proposals/ADR-DRAFT-",
    r"^gtt-domain/proposals/context-",                  # staged L0 drafts (final text)
    r"^gtt-domain/proposals/apply-ADR-",
    r"^gtt-domain/proposals/apply-gtt-domain-migration\.sh$",
    r"^gtt-domain/proposals/gtt-domain-migration/",     # this package
    r"^gtt-domain/proposals/migration-engine-adr-003/",  # the persisted ADR-003 engine: history, not product
    r"^TASK-",
]
DERIVED_FILES = [r"^\.gtt/index/", r"^gtt-domain/session\.md$"]

# Governed context (L0) is MOVED by this migration but its TEXT is not touched here: every L0 text change is
# applied by the ADR-004 promotion script from staged full files (context-*-adr-004.md), the governed mechanism.
L0_TEXT_DEFERRED = [r"^gtt-domain/context/"]

TEXT_EXT = {".md", ".sh", ".py", ".json", ".yaml", ".yml", ".toml", ".ini",
            ".conf", ".cfg", ".txt", ".mdc", ""}
SKIP_DIRS = {".git", "__pycache__", "node_modules"}

LINK_RE = re.compile(r"(?<!\!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


# ---------------------------------------------------------------- helpers

def norm(p):
    return posixpath.normpath(p.replace("\\", "/"))


def die(msg, code=1):
    print(f"gtt-domain-migration: {msg}", file=sys.stderr)
    sys.exit(code)


def sha(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def text_sha(path):
    """Line-ending-insensitive hash (autocrlf-safe) for overlay base checks."""
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="strict", newline="") as fh:
        return fh.read()


def write_text(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def git(*args, check=False):
    r = subprocess.run(["git", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        die(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r


def tracked():
    out = git("ls-files", "-z").stdout
    return {p for p in out.split("\0") if p}


def map_path(p):
    """New path for an old repository path, or None when it does not move."""
    p = norm(p)
    if p in FILE_MAP:
        return FILE_MAP[p]
    for old, new in DIR_MAP:
        if p.startswith(old):
            return new + p[len(old):]
    return None


def map_link_target(p):
    """Like map_path but also accepts a directory written without its
    trailing slash (a link to `gtt/context`)."""
    m = map_path(p)
    if m is not None:
        return m
    for old, new in DIR_MAP:
        if p == old.rstrip("/"):
            return new.rstrip("/")
    return None


def all_files():
    """Every file in the working tree (tracked or not), minus .git."""
    found = []
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for name in sorted(filenames):
            found.append(norm(os.path.join(dirpath, name)))
    return sorted(found)


def is_text(path):
    if "__pycache__" in path.split("/"):
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext not in TEXT_EXT:
        return False
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(4096)
        if b"\0" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except (OSError, UnicodeDecodeError):
        return False


def matches_any(path, patterns):
    return any(re.search(p, path) for p in patterns)


# ------------------------------------------------------- text rewriting

# Not inside a longer identifier (`my-gtt/context`, `foo_gtt/adr`), but fine
# after `:-`, `=`, `../`, quotes and the like (`${1:-gtt/backlog.md}`).
BOUNDARY_BEFORE = r"(?<![A-Za-z0-9_])(?<![A-Za-z0-9_]-)"


# Engine paths are written `gtt/<sub>` today: rewrite unless already `.gtt/` (a dot before) or inside a longer name.
_ENGINE = re.compile(r"(?<![A-Za-z0-9_.])gtt/(scripts|index|protection|scaffold|session-adapters|README\.md)(?![A-Za-z0-9_-])")

# Domain / documentation names are written UNQUALIFIED today (ADR-003 put them at the project root). A name is
# rewritten only when it starts a path: never after a letter, digit, `_`, `/`, `.` or `-` (so `src/context/`,
# `gtt-domain/adr/`, `.gtt/docs/`, `my-docs/` and `gtt-adr/` are left alone), optionally after `./` or `../`.
# `context/ADR` (prose, "context/ADRs") is not a path.
_DOMAIN = re.compile(
    r"(?<![A-Za-z0-9_/.-])(?P<rel>(?:\.{1,2}/)*)"
    r"(?:(?P<d>context/(?!ADRs?\b)|adr/|proposals/)|(?P<docs>docs/)"
    r"|(?P<f>backlog\.md|change-request\.md|session\.md)(?![A-Za-z0-9_-])"
    r"|(?P<fz>\.frozen)(?![A-Za-z0-9_-]))")


def _domain_sub(m):
    rel = m.group("rel") or ""
    if m.group("docs"):
        return rel + ".gtt/docs/"
    if m.group("d"):
        return rel + "gtt-domain/" + m.group("d")
    if m.group("fz"):
        return rel + "gtt-domain/.frozen"
    return rel + "gtt-domain/" + m.group("f")


def build_text_rules():
    """Two rules, applied in a single pass each (no rule sees another rule's output)."""
    return [(_ENGINE, lambda m: ".gtt/" + m.group(1)), (_DOMAIN, _domain_sub)]


TEXT_RULES = build_text_rules()


def mask_code(text):
    out, fence = [], None
    for line in text.split("\n"):
        stripped = line.lstrip()
        if fence:
            out.append(" " * len(line))
            if stripped.startswith(fence):
                fence = None
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = stripped[:3]
            out.append(" " * len(line))
            continue
        out.append(re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), line))
    return "\n".join(out)


def rewrite_links(text, old_src, new_src, existing):
    """Rewrite relative markdown links so they keep pointing at the same
    artifact, accounting for both a moved target and a moved source file.
    `existing` is the set of old paths (files) that existed before the move."""
    masked = mask_code(text)
    edits = []
    for m in LINK_RE.finditer(masked):
        raw = m.group(1)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) or raw.startswith("#"):
            continue
        path, _, frag = raw.partition("#")
        if not path:
            continue
        trailing = path.endswith("/")
        # A root-anchored link (README style: `gtt/USAGE.md`) and a relative
        # link (INDEX style: `../AGENTS.md`) both resolve from the source dir.
        old_target = norm(posixpath.join(posixpath.dirname(old_src), path))
        exists = (old_target in existing
                  or any(e.startswith(old_target.rstrip("/") + "/") for e in existing))
        if not exists:
            continue                        # already broken: not ours to guess
        new_target = map_link_target(old_target) or map_link_target(old_target + "/") \
            or old_target
        rel = posixpath.relpath(new_target, posixpath.dirname(new_src) or ".")
        if trailing and not rel.endswith("/"):
            rel += "/"
        new_raw = rel + (("#" + frag) if frag else "")
        if new_raw != raw:
            edits.append((m.start(1), m.end(1), new_raw))
    for start, end, repl in sorted(edits, reverse=True):
        text = text[:start] + repl + text[end:]
    return text


def rewrite_text(text):
    # A line that a patch or a promotion draft wrote for the NEW layout is never re-scanned: only text
    # that existed before the migration is rewritten (patches run after the rewrite).
    for rx, repl in TEXT_RULES:
        text = rx.sub(repl, text)
    return text


# ------------------------------------------------------------- the plan

def load_pkg(pkg):
    with open(os.path.join(pkg, "overlay.json"), encoding="utf-8") as fh:
        overlay = json.load(fh)
    with open(os.path.join(pkg, "patches.json"), encoding="utf-8") as fh:
        patches = json.load(fh)
    return overlay, patches


def build_plan(pkg):
    overlay, patches = load_pkg(pkg)
    files = all_files()
    moves = {}
    for f in files:
        if "__pycache__" in f.split("/"):
            continue
        n = map_path(f)
        if n is not None:
            moves[f] = n
    return {"files": files, "moves": moves, "overlay": overlay, "patches": patches}


def is_migrated():
    return (os.path.isdir("gtt-domain/context") and os.path.isfile("gtt-domain/.frozen")
            and os.path.isdir(".gtt/scripts")
            and not os.path.exists("context") and not os.path.exists(".frozen")
            and not os.path.exists("gtt/scripts"))


def preflight(pkg):
    problems = []
    if not (os.path.isdir("gtt/scripts") or os.path.isdir(".gtt/scripts")) or not os.path.isdir(".git"):
        die("run from the project root of a git checkout", 2)
    if is_migrated():
        print("already migrated: gtt-domain/ and .gtt/ exist, the root context/, .frozen and gtt/scripts "
              "do not. Nothing to do.")
        return "migrated"
    plan = build_plan(pkg)
    # bash cannot run a script saved with CRLF line endings ("$'\r': command not
    # found"), and every step of the promotion runs these through bash.
    import glob
    for sh in sorted(glob.glob("gtt/scripts/*.sh") + glob.glob("proposals/apply-*.sh")):
        with open(sh, "rb") as fh:
            if b"\r" in fh.read():
                problems.append(f"CRLF line endings in {sh} - bash cannot run it; "
                                f"convert it to LF (it must match its committed LF content)")
    for old in (".frozen", "context", "adr", "proposals", "docs", "backlog.md", "change-request.md",
                "gtt/scripts", "gtt/index", "gtt/protection", "gtt/session-adapters", "gtt/scaffold/manifest.yaml"):
        if not os.path.exists(old):
            problems.append(f"expected pre-migration path is missing: {old}")
    # every file still under gtt/ must have a home, or it would be stranded (bytecode is removed, never moved)
    for f in plan["files"]:
        if f.startswith("gtt/") and "__pycache__" not in f.split("/") and f not in plan["moves"]:
            problems.append(f"file under gtt/ with no destination in the map: {f}")
    for old, new in plan["moves"].items():
        if old.lower() == new.lower():
            continue                        # case-only rename (case-insensitive FS)
        if os.path.exists(new):
            problems.append(f"target already exists (would overwrite): {new}")
    for d in (".gtt", "gtt-domain"):
        if os.path.exists(d):
            problems.append(f"directory already exists at the project root (would merge): {d}/")
    for path, spec in plan["overlay"]["files"].items():
        want = spec["base_sha256"]
        base = spec.get("base_path", path)      # the file as it exists BEFORE the moves
        if not os.path.isfile(base):
            problems.append(f"overlay base file is missing: {base}")
        elif text_sha(base) != want:
            problems.append(f"{base} changed since the package was prepared "
                            "(overlay would discard those changes)")
    new_to_old = {n: o for o, n in plan["moves"].items()}
    missing = sorted({p["file"] for p in plan["patches"]
                      if not os.path.isfile(new_to_old.get(p["file"], p["file"]))})
    for target in missing:
        problems.append(f"patch target is missing: {new_to_old.get(target, target)}")
    return problems if problems else "ok"


def describe(pkg):
    plan = build_plan(pkg)
    print("MOVES (git mv):")
    for old, new in sorted(plan["moves"].items()):
        if old.startswith(PKG_OLD + "/") or old.startswith("proposals/migration-engine-adr-003/"):
            continue
        print(f"  {old}  ->  {new}")
    print(f"  {PKG_OLD}/  ->  {PKG_REL}/   (this package, moved with proposals/)")
    print("  proposals/migration-engine-adr-003/  ->  gtt-domain/proposals/migration-engine-adr-003/   (history, not rewritten)")
    print("OVERLAID (full replacement, base hash verified):")
    for p in sorted(plan["overlay"]["files"]):
        s = plan["overlay"]["files"][p]
        print(f"  {p}   <- overlay/{s['stage']}" + (f"   (base: {s['base_path']})" if s.get("base_path") else ""))
    print("PATCHED (exact-text / block / regex / tree, each must match where it says):")
    for f in sorted({p['file'] for p in plan["patches"]}):
        print(f"  {f}  ({sum(1 for p in plan['patches'] if p['file'] == f)} patch(es))")
    print("REWRITTEN (path references + relative links): everything that mentions a moved path, except the\n"
          "  HISTORICAL files (accepted ADRs, completion log, drafts, staged promotion files, this package, the persisted\n"
          "  ADR-003 engine) and except governed context gtt-domain/context/*: it is MOVED here, and its text changes only\n"
          "  through the ADR-004 promotion script.")


def rewrite_file_set(plan_moves, final_paths):
    """Final-path list of files whose text is rewritten."""
    out = []
    for path in final_paths:
        if not is_text(path):
            continue
        if (matches_any(path, HISTORICAL_FILES) or matches_any(path, DERIVED_FILES)
                or matches_any(path, L0_TEXT_DEFERRED)):
            continue
        out.append(path)
    return out


def apply(pkg):
    state = preflight(pkg)
    if state == "migrated":
        return 0
    if state != "ok":
        for p in state:
            print(f"PRECONDITION FAILED: {p}", file=sys.stderr)
        die("the repository is not in the expected pre-migration state; nothing was changed.")

    plan = build_plan(pkg)
    overlay = plan["overlay"]
    frozen_before = file_sha(".frozen")
    tr = tracked()
    existing_old = {f for f in plan["files"]}

    # ---- 0. generated bytecode inside the staged packages (never moved) -------
    for dirpath, dirnames, _files in os.walk("proposals"):
        for d in list(dirnames):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d))
                dirnames.remove(d)

    # ---- 1. moves ---------------------------------------------------------
    for old, new in sorted(plan["moves"].items()):
        os.makedirs(os.path.dirname(new) or ".", exist_ok=True)
        _mv(old, new, old in tr)
    for root in ("gtt", "docs", "context", "adr", "proposals"):
        _prune_empty(root)

    # ---- 2. removals ------------------------------------------------------
    for path in REMOVE:
        if os.path.exists(path):
            if path in tr:
                git("rm", "-q", "--cached", "--", path)
            os.remove(path)
    # bytecode the engine scripts left behind (generated; ignored) is never moved
    if os.path.isdir("gtt/scripts/__pycache__"):
        shutil.rmtree("gtt/scripts/__pycache__")
    _prune_empty("gtt")

    # ---- 3. rewrite path references + relative links -----------------------
    new_to_old = {n: o for o, n in plan["moves"].items()}
    final_files = [f for f in all_files()]
    targets = rewrite_file_set(plan["moves"], final_files)
    changed = []
    for path in targets:
        old_src = new_to_old.get(path, path)
        text = read_text(path)
        new_text = text
        if path.endswith(".md"):
            new_text = rewrite_links(new_text, old_src, path, existing_old)
        new_text = rewrite_text(new_text)
        if new_text != text:
            write_text(path, new_text)
            changed.append(path)

    # ---- 4. patches (prose and small logic edits that need a human-written
    #         rewrite); each must match exactly where it says, or we stop ------
    for p in plan["patches"]:
        apply_patch(p)

    # ---- 5. overlay: full replacement of files whose logic changes ---------
    for path in sorted(overlay["files"]):
        src = os.path.join(pkg, "overlay", overlay["files"][path]["stage"])
        if not os.path.isfile(src):
            die(f"overlay file missing from the package: {src}")
        shutil.copyfile(src, path)

    # ---- 6. (the scaffold manifest is an overlay of .gtt/scaffold/manifest.yaml: layout version 2)

    # ---- 7. artifact identity: same id, new path, old path kept as history --
    manifest_path = ".gtt/index/artifacts.json"
    data = json.loads(read_text(manifest_path))
    remapped = []
    for e in data["artifacts"]:
        if e.get("status", "active") != "active":
            continue
        new = plan["moves"].get(e["path"])
        if new:
            e["history"] = sorted(set(e.get("history", [])) | {e["path"]})
            e["path"] = new
            remapped.append((e["id"], new))
    data["artifacts"].sort(key=lambda a: a["id"])
    write_text(manifest_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    # ---- 8. the freeze marker must be byte-identical -----------------------
    if file_sha("gtt-domain/.frozen") != frozen_before:
        die(".frozen changed during the migration - refusing to continue.")

    print(f"moved {len(plan['moves'])} file(s); rewrote {len(changed)}; "
          f"patched {len({p['file'] for p in plan['patches']})}; "
          f"overlaid {len(overlay['files'])}; re-registered {len(remapped)} artifact path(s).")
    print(f".frozen preserved byte-for-byte ({frozen_before[:12]}...).")
    return 0


# ---------------------------------------------------------------- patches

# The host-project layout tree appears in a dozen documents. It is replaced
# everywhere by the same block (one definition, per language), so the docs
# cannot drift apart from each other.
OLD_TREE_RE = re.compile(
    r"```text\n/\n├── AGENTS\.md[^\n]*\n[\s\S]*?└── \.claude/ \| \.kiro/ \| \.copilot/[^\n]*\n```")

TREE_LABELS = {
    "en": dict(src="# if a source document existed",
               eng="GTT-METHOD ENGINE (machinery, derived state, GTT's own documentation)",
               docs="GTT's own documentation",
               dom="THE DOMAIN GOVERNED BY GTT-METHOD",
               l0="L0 governed context", l1="L1 accepted decisions",
               prop="governed drafts awaiting a human decision",
               sess="derived operational state (never authority)",
               frz="freeze marker, written by gtt-freeze.sh",
               ade="ADE OVERLAY - exactly one: the ADE running the bootstrap",
               agents="portable agent contract (ADE discovery file)"),
    "es": dict(src="# si existió documento fuente",
               eng="MOTOR DE GTT-METHOD (maquinaria, estado derivado, documentación propia de GTT)",
               docs="documentación propia de GTT",
               dom="EL DOMINIO GOBERNADO POR GTT-METHOD",
               l0="contexto gobernado L0", l1="decisiones aceptadas L1",
               prop="borradores gobernados pendientes de decisión humana",
               sess="estado operativo derivado (nunca autoridad)",
               frz="marcador de freeze, escrito por gtt-freeze.sh",
               ade="OVERLAY DEL ADE - exactamente uno: el ADE que ejecuta el bootstrap",
               agents="contrato portable del agente (archivo de descubrimiento del ADE)"),
}


def new_tree(lang):
    t = TREE_LABELS[lang]
    rows = [
        "```text",
        "/",
        f"├── AGENTS.md                     # {t['agents']}",
        "├── readme-gtt.md",
        "├── readme-gtt.es.md",
        f"├── SOURCE-BRIEF.*                {t['src']}",
        "│",
        f"├── .gtt/                         # {t['eng']}",
        "│   ├── README.md",
        "│   ├── index/",
        "│   ├── protection/",
        "│   ├── scaffold/manifest.yaml",
        "│   ├── scripts/",
        "│   ├── session-adapters/",
        f"│   └── docs/                     #   {t['docs']}: index, installation, usage, docs, evidence,",
        "│                                 #   gtt-completion, session-adapter-contract",
        "│",
        f"├── gtt-domain/                   # {t['dom']}",
        f"│   ├── context/                  #   {t['l0']}",
        f"│   ├── adr/                      #   {t['l1']}",
        f"│   ├── proposals/                #   {t['prop']}",
        "│   ├── backlog.md",
        "│   ├── change-request.md",
        f"│   ├── session.md                #   {t['sess']}",
        f"│   └── .frozen                   #   {t['frz']}",
        "│",
        f"└── .claude/ | .kiro/ | .copilot/ # {t['ade']}",
        "```",
    ]
    return "\n".join(rows)


def apply_patch(p):
    """Three kinds: exact (old -> new, must match once), block (replace the
    lines from the one starting with `start` up to, not including, the first
    later line starting with `end`; end=None means end of file), and tree."""
    path = p["file"]
    text = read_text(path)
    crlf = "\r\n" in text
    if crlf:
        text = text.replace("\r\n", "\n")
    kind = p.get("type", "exact")
    if kind == "exact":
        n = text.count(p["old"])
        if n != 1:
            die(f"patch for {path} matched {n} times (expected exactly 1): {p['old'][:70]!r}")
        text = text.replace(p["old"], p["new"])
    elif kind == "block":
        lines = text.split("\n")
        starts = [i for i, l in enumerate(lines) if l.startswith(p["start"])]
        if len(starts) != 1:
            die(f"block start in {path} matched {len(starts)} lines (expected 1): {p['start'][:70]!r}")
        s = starts[0]
        if p.get("end") is None:
            e = len(lines)
        else:
            ends = [i for i in range(s + 1, len(lines)) if lines[i].startswith(p["end"])]
            if not ends:
                die(f"block end in {path} not found after start: {p['end'][:70]!r}")
            e = ends[0]
        lines[s:e] = p["new"].split("\n")
        text = "\n".join(lines)
    elif kind == "regex":
        text, n = re.subn(p["pattern"], p["repl"], text, flags=re.M)
        if n < p.get("min_count", 1):
            die(f"regex patch in {path} matched {n} time(s) (expected at least "
                f"{p.get('min_count', 1)}): {p['pattern'][:70]!r}")
    elif kind == "tree":
        text, n = OLD_TREE_RE.subn(lambda m: new_tree(p["lang"]), text)
        if n != p.get("count", 1):
            die(f"tree patch in {path} replaced {n} block(s) (expected {p.get('count', 1)})")
    else:
        die(f"unknown patch type {kind!r}")
    if crlf:
        text = text.replace("\n", "\r\n")
    write_text(path, text)


def _mv(old, new, is_tracked):
    if is_tracked:
        r = git("mv", "--", old, new)
        if r.returncode != 0:
            die(f"git mv {old} {new} failed: {r.stderr.strip()}")
    else:
        os.makedirs(os.path.dirname(new) or ".", exist_ok=True)
        os.replace(old, new)


def _prune_empty(root):
    if not os.path.isdir(root):
        return
    for dirpath, _dirnames, _filenames in os.walk(root, topdown=False):
        try:
            os.rmdir(dirpath)
        except OSError:
            pass


# ------------------------------------------------------- old-ref search

OLD_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_.])gtt/(?:scripts|index|protection|scaffold|session-adapters|README\.md)(?![A-Za-z0-9_-])"
    r"|(?<![A-Za-z0-9_/.-])(?:\.{1,2}/)*(?:(?:context/(?!ADRs?\b)|adr/|proposals/|docs/)"
    r"|(?:backlog\.md|change-request\.md|session\.md)(?![A-Za-z0-9_-])|\.frozen(?![A-Za-z0-9_-]))"
)


STALE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])gtt/(?![A-Za-z0-9_/.-])"                       # the Engine used to be `gtt/`
    r"|Project Governance|PROJECT GOVERNANCE|GTT Documentation|GTT DOCUMENTATION|four layers"
    r"|Gobernanza del Proyecto|GOBERNANZA DEL PROYECTO|Documentaci[oó]n de GTT|DOCUMENTACI[OÓ]N DE GTT"
    r"|cuatro capas"
)


def oldrefs():
    """Classify every remaining mention of an old path or name."""
    counts = {"VALID": 0, "HISTORICAL": 0, "DERIVED": 0, "STALE": 0, "ERROR": 0}
    lines = []
    for path in all_files():
        if not is_text(path):
            continue
        try:
            text = read_text(path)
        except UnicodeDecodeError:
            continue
        all_lines = text.split("\n")
        for i, line in enumerate(all_lines, 1):
            prev = "\n".join(all_lines[max(0, i - 3):i - 1])
            for m in OLD_REF_RE.finditer(line):
                if matches_any(path, HISTORICAL_FILES):
                    kind = "HISTORICAL"
                elif matches_any(path, DERIVED_FILES):
                    kind = "DERIVED"
                elif _is_valid_mention(path, line, m, prev):
                    kind = "VALID"
                else:
                    kind = "ERROR"
                counts[kind] += 1
                lines.append((kind, path, i, m.group(0)))
            # Wording of the ADR-003 layout that no path rewrite can see (a bare `gtt/` directory, the
            # "Project Governance" / "GTT Documentation" layers, "four layers"): STALE unless it is a record
            # of the past (historical file, change-log row, or a line that names the new directories).
            for m in STALE_RE.finditer(line):
                if matches_any(path, HISTORICAL_FILES) or matches_any(path, DERIVED_FILES):
                    kind = "HISTORICAL"
                elif _is_valid_mention(path, line, m, prev, stale=True):
                    kind = "VALID"
                else:
                    kind = "STALE"
                counts[kind] += 1
                lines.append((kind, path, i, m.group(0)))
    for kind, path, i, hit in lines:
        if kind in ("ERROR", "STALE"):
            print(f"{kind:<10} {path}:{i}: {hit}")
    print("old-reference search: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    if os.environ.get("GTT_OLDREFS_LIST"):
        for kind, path, i, hit in lines:
            print(f"  {kind:<10} {path}:{i}: {hit}")
    return 1 if counts["ERROR"] or counts["STALE"] else 0


def _is_valid_mention(path, line, m, prev="", stale=False):
    """A mention that legitimately uses the old spelling: (a) a member list written relative to the new
    directories - on a line that names `gtt-domain` / `.gtt`, or continuing such a line (one of the two
    lines before it names them), or a nested tree line (`├── context/` under `gtt-domain/`), (b) a line
    that speaks of a host project's own directories, or (c) a file that describes the old layout on
    purpose. The default is ERROR; the rewrite itself is what guarantees the paths, this only classifies
    what is left."""
    if not stale:      # the wording of the old layout ("Project Governance", bare `gtt/`) is never excused this way
        if re.search(r"gtt-domain|\.gtt\b", line) or re.search(r"gtt-domain|\.gtt\b", prev):
            return True
        if re.match(r"^\s*[│├└]", line) or re.search(r"(?i)host project|proyecto anfitri", line):
            return True
    # a change-log row of the stack map records a past decision in the words of its time
    if re.match(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*ADR-\d+\s*\|", line):
        return True
    return path in VALID_MENTION_FILES and bool(VALID_MENTION_FILES[path].search(line))


# Files allowed to describe the old layout on purpose (e.g. the migration note in docs), each with the pattern
# that marks such a line (final paths).
VALID_MENTION_FILES = {
    ".gtt/docs/docs.md": re.compile(r"(?i)restructure|formerly|legacy-layout|before the migration"),
    # generic mentions inside the hook's own documentation and patterns (filename-substring rule, "proposals/apply-")
    ".claude/hooks/protect-l0.py": re.compile(r"change-request\.md|docs/docs\.md|\"context/\"|proposals/|\(gtt/\|gtt-domain/"),
    ".claude/skills/gtt-bootstrap/SKILL.md": re.compile(r"(?i)earlier layout|v2 layout|layout of ADR-003|v2\.1 layout|directly under `gtt/`"),
}


# ----------------------------------------------------------------- verify

def parse_manifest(path):
    """Tiny reader for the flow-style entries of manifest.yaml (data only)."""
    entries = []
    section = None
    for raw in read_text(path).split("\n"):
        line = raw.rstrip()
        if re.match(r"^[a-z_]+:\s*$", line):
            section = line.split(":")[0]
            continue
        m = re.match(r"^\s*-\s*\{(.*)\}\s*$", line)
        if m and section:
            fields = dict(
                (k.strip(), v.strip())
                for k, v in (kv.split(":", 1) for kv in re.split(r",\s*(?=\w+:)", m.group(1)))
            )
            fields["_section"] = section
            entries.append(fields)
    return entries


def verify():
    problems = []
    mf = ".gtt/scaffold/manifest.yaml"
    if not os.path.isfile(mf):
        die(f"{mf} missing")
    entries = parse_manifest(mf)
    if not entries:
        problems.append("manifest declares no entries (unparseable?)")
    for e in entries:
        p = e["path"].strip("'\"")
        required = e.get("required", "true") == "true"
        exists = os.path.exists(p.rstrip("/"))
        if required and not exists:
            problems.append(f"required {e['_section']} path missing: {p}")
    if not any(re.match(r"^\s*version:\s*2\b", l) for l in read_text(mf).split("\n")):
        problems.append("manifest is not layout version 2")
    # nothing may remain at an old location
    for old in ("gtt", "context", "adr", "proposals", "docs", ".frozen", "backlog.md", "change-request.md",
                "session.md"):
        if os.path.exists(old):
            problems.append(f"old location still present: {old}")
    # the artifact identity manifest must point at files that exist
    data = json.loads(read_text(".gtt/index/artifacts.json"))
    for e in data["artifacts"]:
        if e.get("status", "active") == "active" and not os.path.isfile(e["path"]):
            problems.append(f"identity points at a missing file: {e['id']} -> {e['path']}")
    # lowercase rule for the names this restructure introduced
    for new in set(FILE_MAP.values()):
        if new != new.lower() and new != ".gtt/README.md":      # README.md: established convention
            problems.append(f"not lowercase: {new}")
        if new != ".gtt/README.md" and not os.path.exists(new):
            problems.append(f"expected file missing after migration: {new}")
    for p in problems:
        print(f"VERIFY FAIL: {p}", file=sys.stderr)
    if problems:
        return 1
    print(f"verify: OK - {len(entries)} manifest entr(y/ies) present; layout version 2; identity paths exist; "
          "no old location remains.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["preflight", "plan", "apply", "oldrefs", "verify"])
    ap.add_argument("--pkg", default=PKG_OLD)
    args = ap.parse_args()
    if args.command == "preflight":
        r = preflight(args.pkg)
        if r in ("ok", "migrated"):
            print(f"preflight: {r}")
            return 0 if r == "ok" else 3
        for p in r:
            print(f"PRECONDITION FAILED: {p}", file=sys.stderr)
        return 1
    if args.command == "plan":
        describe(args.pkg)
        return 0
    if args.command == "apply":
        return apply(args.pkg)
    if args.command == "oldrefs":
        return oldrefs()
    return verify()


if __name__ == "__main__":
    sys.exit(main())
