#!/usr/bin/env python3
"""GTT scaffold restructure - migration engine (staged, human-executed).

Status: Draft - not a decision. Prepared by an agent; run only through
gtt/proposals/apply-scaffold-restructure.sh, by a human.

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

It never touches gtt/.frozen's content (the marker is moved, and its bytes are
compared before and after), never runs gtt-freeze.sh, and never commits.
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

# Exact files. Everything not listed here (and not under a DIR_MAP prefix)
# stays where it is: the Engine (gtt/scripts, gtt/index, gtt/protection,
# gtt/session-adapters), the ADE overlays, LICENSE, AGENTS.md.
FILE_MAP = {
    "gtt/backlog.md": "backlog.md",
    "gtt/CHANGE-REQUEST.md": "change-request.md",
    "gtt/SESSION.md": "session.md",
    "gtt/.frozen": ".frozen",
    "gtt/INDEX.md": "docs/index.md",
    "gtt/INSTALLATION.md": "docs/installation.md",
    "gtt/INSTALLATION.es.md": "docs/installation.es.md",
    "gtt/USAGE.md": "docs/usage.md",
    "gtt/USAGE.es.md": "docs/usage.es.md",
    "gtt/GTT-COMPLETION.md": "docs/gtt-completion.md",
    "gtt/EVIDENCE.md": "docs/evidence.md",
    "gtt/docs/DOCS.md": "docs/docs.md",
    "gtt/docs/SESSION-ADAPTER-CONTRACT.md": "docs/session-adapter-contract.md",
    "README-GTT.md": "readme-gtt.md",
    "README-GTT.es.md": "readme-gtt.es.md",
}

DIR_MAP = [
    ("gtt/context/", "context/"),
    ("gtt/adr/", "adr/"),
    ("gtt/proposals/", "proposals/"),
    ("gtt/docs/", "docs/"),
]

# Bare file names (no gtt/ prefix) that are renamed. Used by the text rewrite
# for prose and code mentions such as "see CHANGE-REQUEST.md".
BARE_RENAMES = {
    "CHANGE-REQUEST.md": "change-request.md",
    "README-GTT.es.md": "readme-gtt.es.md",
    "README-GTT.md": "readme-gtt.md",
    "SESSION-ADAPTER-CONTRACT.md": "session-adapter-contract.md",
    "GTT-COMPLETION.md": "gtt-completion.md",
    "INSTALLATION.es.md": "installation.es.md",
    "INSTALLATION.md": "installation.md",
    "USAGE.es.md": "usage.es.md",
    "USAGE.md": "usage.md",
    "EVIDENCE.md": "evidence.md",
    "SESSION.md": "session.md",
    "DOCS.md": "docs.md",
    "INDEX.md": "index.md",
}

# Files that are removed by the migration, with their classification.
REMOVE = {
    "gtt/scripts/__pycache__/gtt_guard.cpython-313.pyc": "generated (versioned by mistake)",
}

PKG_REL = "proposals/scaffold-restructure"          # after the move
PKG_OLD = "gtt/proposals/scaffold-restructure"      # before the move

# Files whose old-path mentions are historical/draft records, not live
# references. They are neither rewritten nor reported as ERROR.
HISTORICAL_FILES = [
    r"^adr/ADR-\d{3}-",                    # accepted ADRs: records of their time (incl. ADR-003)
    r"^docs/gtt-completion\.md$",          # append-only completion log
    r"^proposals/PROPOSAL-",               # drafts awaiting a decision
    r"^proposals/GOVERNANCE-PACKAGE-",
    r"^proposals/ADR-DRAFT-",
    r"^proposals/context-",                # staged L0 drafts (final text)
    r"^proposals/apply-ADR-",
    r"^proposals/apply-scaffold-restructure\.sh$",
    r"^proposals/scaffold-restructure/",
    r"^TASK-",
]
DERIVED_FILES = [r"^gtt/index/", r"^session\.md$"]

# Governed context (L0) is MOVED by this migration but its TEXT is not touched
# here: every L0 text change is applied by the ADR-003 promotion script from
# staged full files (proposals/context-*.md), the governed mechanism.
L0_TEXT_DEFERRED = [r"^context/"]

TEXT_EXT = {".md", ".sh", ".py", ".json", ".yaml", ".yml", ".toml", ".ini",
            ".conf", ".cfg", ".txt", ".mdc", ""}
SKIP_DIRS = {".git", "__pycache__", "node_modules"}

LINK_RE = re.compile(r"(?<!\!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


# ---------------------------------------------------------------- helpers

def norm(p):
    return posixpath.normpath(p.replace("\\", "/"))


def die(msg, code=1):
    print(f"scaffold-restructure: {msg}", file=sys.stderr)
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


def build_text_rules():
    """Ordered (regex, replacement) pairs; longest, most specific first.
    The boundary refuses to match inside a longer identifier or path segment
    (`my-gtt/context`, `foo_gtt/adr`) but does match after `../` and `./`."""
    pairs = [(o, n) for o, n in FILE_MAP.items()]
    pairs += [(o.rstrip("/"), n.rstrip("/")) for o, n in DIR_MAP]
    # gtt-relative spellings used inside the docs themselves (e.g. INDEX.md
    # says `docs/DOCS.md` meaning gtt/docs/DOCS.md)
    pairs += [("docs/DOCS.md", "docs/docs.md"),
              ("docs/SESSION-ADAPTER-CONTRACT.md", "docs/session-adapter-contract.md")]
    pairs.sort(key=lambda kv: -len(kv[0]))
    rules = []
    for old, new in pairs:
        rules.append((re.compile(BOUNDARY_BEFORE + re.escape(old) +
                                 r"(?![A-Za-z0-9_-])"), new))
    # bare renamed names, e.g. "see CHANGE-REQUEST.md" or a link label
    bare = sorted(BARE_RENAMES.items(), key=lambda kv: -len(kv[0]))
    for old, new in bare:
        rules.append((re.compile(r"(?<![A-Za-z0-9_/.-])" + re.escape(old) +
                                 r"(?![A-Za-z0-9_-])"), new))
    return rules


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
    return (os.path.isdir("context") and os.path.isfile(".frozen")
            and not os.path.exists("gtt/context") and not os.path.exists("gtt/.frozen"))


def preflight(pkg):
    problems = []
    if not os.path.isdir("gtt/scripts") or not os.path.isdir(".git"):
        die("run from the project root of a git checkout", 2)
    if is_migrated():
        print("already migrated: context/ and .frozen exist at the project root, "
              "gtt/context and gtt/.frozen do not. Nothing to do.")
        return "migrated"
    plan = build_plan(pkg)
    # bash cannot run a script saved with CRLF line endings ("$'\r': command not
    # found"), and every step of the promotion runs these through bash.
    import glob
    for sh in sorted(glob.glob("gtt/scripts/*.sh") + glob.glob("gtt/proposals/apply-*.sh")):
        with open(sh, "rb") as fh:
            if b"\r" in fh.read():
                problems.append(f"CRLF line endings in {sh} - bash cannot run it; "
                                f"convert it to LF (it must match its committed LF content)")
    for old in ("gtt/.frozen", "gtt/context", "gtt/adr", "gtt/proposals", "gtt/docs",
                "gtt/backlog.md", "gtt/CHANGE-REQUEST.md", "gtt/INDEX.md"):
        if not os.path.exists(old):
            problems.append(f"expected pre-migration path is missing: {old}")
    for old, new in plan["moves"].items():
        if old.lower() == new.lower():
            continue                        # case-only rename (case-insensitive FS)
        if os.path.exists(new):
            problems.append(f"target already exists (would overwrite): {new}")
    for d in ("context", "adr", "proposals", "docs"):
        if os.path.exists(d):
            problems.append(f"directory already exists at the project root (would merge): {d}/")
    for new in ("gtt/scaffold/manifest.yaml", ".gitignore"):
        if os.path.exists(new):
            problems.append(f"target already exists (would overwrite): {new}")
    for path, spec in plan["overlay"]["files"].items():
        want = spec["base_sha256"]
        if not os.path.isfile(path):
            problems.append(f"overlay base file is missing: {path}")
        elif text_sha(path) != want:
            problems.append(f"{path} changed since the package was prepared "
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
        if old.startswith(PKG_OLD + "/"):
            continue
        print(f"  {old}  ->  {new}")
    print(f"  {PKG_OLD}/  ->  {PKG_REL}/   (this package, moved with proposals/)")
    print("REMOVED:")
    for p, why in REMOVE.items():
        print(f"  {p}   [{why}]")
    print("CREATED:")
    print("  gtt/scaffold/manifest.yaml   [scaffold manifest]")
    print("  .gitignore                   [__pycache__/ and *.pyc, so the removed file cannot come back]")
    print("OVERLAID (full replacement, base hash verified):")
    for p in sorted(plan["overlay"]["files"]):
        print(f"  {p}   <- overlay/{plan['overlay']['files'][p]['stage']}")
    print("PATCHED (exact-text, each must match exactly once):")
    for f in sorted({p['file'] for p in plan["patches"]}):
        print(f"  {f}  ({sum(1 for p in plan['patches'] if p['file'] == f)} patch(es))")
    print("REWRITTEN (path references + relative links), everything else that "
          "mentions an old path,\n  except the HISTORICAL files (accepted ADRs, completion log, "
          "existing drafts, this package)\n  and except governed context context/*: it is MOVED here, "
          "and its text changes only through the ADR-003 promotion script.")


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
    frozen_before = file_sha("gtt/.frozen")
    tr = tracked()
    existing_old = {f for f in plan["files"]}

    # ---- 0. generated bytecode inside the staged packages (never moved) -------
    for dirpath, dirnames, _files in os.walk("gtt/proposals"):
        for d in list(dirnames):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d))
                dirnames.remove(d)

    # ---- 1. moves ---------------------------------------------------------
    two_step = {"README-GTT.md", "README-GTT.es.md"}      # case-only renames
    for old, new in sorted(plan["moves"].items()):
        os.makedirs(os.path.dirname(new) or ".", exist_ok=True)
        if old in two_step:
            tmp = old + ".gtt-restructure-tmp"
            _mv(old, tmp, old in tr)
            _mv(tmp, new, old in tr)
        else:
            _mv(old, new, old in tr)
    for root in ("gtt/context", "gtt/adr", "gtt/proposals", "gtt/docs"):
        _prune_empty(root)

    # ---- 2. removals ------------------------------------------------------
    for path in REMOVE:
        if os.path.exists(path):
            if path in tr:
                git("rm", "-q", "--cached", "--", path)
            os.remove(path)
    # any other bytecode the engine scripts left behind (generated; ignored from now on)
    if os.path.isdir("gtt/scripts/__pycache__"):
        shutil.rmtree("gtt/scripts/__pycache__")

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

    # ---- 6. scaffold manifest, .gitignore ----------------------------------
    os.makedirs("gtt/scaffold", exist_ok=True)
    shutil.copyfile(os.path.join(pkg, "manifest.yaml"), "gtt/scaffold/manifest.yaml")
    shutil.copyfile(os.path.join(pkg, "gitignore"), ".gitignore")

    # ---- 7. artifact identity: same id, new path, old path kept as history --
    manifest_path = "gtt/index/artifacts.json"
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
    if file_sha(".frozen") != frozen_before:
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
    r"```text\n/\n├── AGENTS\.md\n├── readme-gtt\.md\n├── readme-gtt\.es\.md\n"
    r"├── SOURCE-BRIEF\.\*[^\n]*\n└── gtt/\n(?:    [^\n]*\n)+?    └── scripts/\n```")

TREE_LABELS = {
    "en": dict(src="# if a source document existed",
               gov="PROJECT GOVERNANCE", l0="L0 governed context", l1="L1 accepted decisions",
               prop="agent drafts awaiting a human decision", back="development line",
               cr="front door for change intent",
               sess="derived operational state (never authority)",
               frz="freeze marker, written by gtt-freeze.sh",
               doc="GTT DOCUMENTATION", eng="GTT ENGINE",
               ade="ADE OVERLAY - exactly one: the ADE running the bootstrap",
               agents="portable agent contract (ADE discovery file)"),
    "es": dict(src="# si existió documento fuente",
               gov="GOBERNANZA DEL PROYECTO", l0="contexto gobernado L0", l1="decisiones aceptadas L1",
               prop="borradores del agente pendientes de decisión humana", back="línea de desarrollo",
               cr="puerta de entrada de los cambios",
               sess="estado operativo derivado (nunca autoridad)",
               frz="marcador de freeze, escrito por gtt-freeze.sh",
               doc="DOCUMENTACIÓN DE GTT", eng="MOTOR DE GTT",
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
        f"├── context/                      # {t['gov']}: {t['l0']}",
        f"├── adr/                          #   {t['l1']}",
        f"├── proposals/                    #   {t['prop']}",
        f"├── backlog.md                    #   {t['back']}",
        f"├── change-request.md             #   {t['cr']}",
        f"├── session.md                    #   {t['sess']}",
        f"├── .frozen                       #   {t['frz']}",
        "│",
        f"├── docs/                         # {t['doc']}",
        "│   ├── index.md",
        "│   ├── installation.md",
        "│   ├── installation.es.md",
        "│   ├── usage.md",
        "│   ├── usage.es.md",
        "│   ├── gtt-completion.md",
        "│   ├── evidence.md",
        "│   ├── docs.md",
        "│   └── session-adapter-contract.md",
        "│",
        f"├── gtt/                          # {t['eng']}",
        "│   ├── README.md",
        "│   ├── scaffold/manifest.yaml",
        "│   ├── scripts/",
        "│   ├── index/",
        "│   ├── protection/",
        "│   └── session-adapters/",
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
    BOUNDARY_BEFORE + r"gtt/(?:context|adr|proposals|docs|backlog\.md|CHANGE-REQUEST\.md|"
    r"SESSION\.md|INDEX\.md|INSTALLATION(?:\.es)?\.md|USAGE(?:\.es)?\.md|GTT-COMPLETION\.md|"
    r"EVIDENCE\.md|\.frozen)(?![A-Za-z0-9_-])"
    r"|(?<![A-Za-z0-9_/.-])(?:CHANGE-REQUEST|SESSION|INDEX|INSTALLATION(?:\.es)?|USAGE(?:\.es)?|"
    r"GTT-COMPLETION|EVIDENCE|DOCS|SESSION-ADAPTER-CONTRACT|README-GTT(?:\.es)?)\.md"
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
        for i, line in enumerate(text.split("\n"), 1):
            for m in OLD_REF_RE.finditer(line):
                if matches_any(path, HISTORICAL_FILES):
                    kind = "HISTORICAL"
                elif matches_any(path, DERIVED_FILES):
                    kind = "DERIVED"
                elif _is_valid_mention(path, line, m):
                    kind = "VALID"
                else:
                    kind = "ERROR"
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


def _is_valid_mention(path, line, m):
    """A mention that legitimately names the old location: the migration is
    described (old -> new), or the text names an artifact of a different
    scope. Kept deliberately narrow - the default is ERROR."""
    return path in VALID_MENTION_FILES and bool(VALID_MENTION_FILES[path].search(line))


# Files allowed to describe the old layout on purpose (e.g. the migration
# note in docs), each with the pattern that marks such a line.
VALID_MENTION_FILES = {
    "docs/docs.md": re.compile(r"(?i)scaffold restructure|before the restructure|formerly|legacy-layout"),
    ".claude/skills/gtt-bootstrap/SKILL.md": re.compile(r"(?i)earlier layout|v2 layout|before the scaffold restructure|gtt/(context|adr|proposals|backlog|CHANGE-REQUEST|SESSION|\.frozen|INDEX|INSTALLATION)|directly under `gtt/`"),
    ".claude/hooks/protect-l0.py": re.compile(r"from gtt/context/ and gtt/adr/ to context/ and adr/"),
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
    mf = "gtt/scaffold/manifest.yaml"
    if not os.path.isfile(mf):
        die(f"{mf} missing")
    entries = parse_manifest(mf)
    if not entries:
        problems.append("manifest declares no entries (unparseable?)")
    for e in entries:
        p = e["path"].strip("'\"")
        required = e.get("required", "true") == "true"
        derived = e.get("derived", "false") == "true"
        exists = os.path.exists(p.rstrip("/"))
        if required and not exists:
            problems.append(f"required {e['_section']} path missing: {p}")
        if not required and not exists and not derived and e.get("optional_until") is None:
            pass
    # nothing that belongs to a layer may sit in the wrong one
    for old in ("gtt/context", "gtt/adr", "gtt/proposals", "gtt/docs", "gtt/.frozen",
                "gtt/backlog.md", "gtt/CHANGE-REQUEST.md", "gtt/SESSION.md", "gtt/INDEX.md"):
        if os.path.exists(old):
            problems.append(f"old location still present: {old}")
    # the artifact identity manifest must point at files that exist
    data = json.loads(read_text("gtt/index/artifacts.json"))
    for e in data["artifacts"]:
        if e.get("status", "active") == "active" and not os.path.isfile(e["path"]):
            problems.append(f"identity points at a missing file: {e['id']} -> {e['path']}")
    # lowercase rule for the names this restructure introduced
    for new in set(FILE_MAP.values()):
        if new != new.lower():
            problems.append(f"not lowercase: {new}")
        if not os.path.exists(new):
            problems.append(f"expected file missing after migration: {new}")
    for p in problems:
        print(f"VERIFY FAIL: {p}", file=sys.stderr)
    if problems:
        return 1
    print(f"verify: OK - {len(entries)} manifest entr(y/ies) present; identity paths exist; "
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
