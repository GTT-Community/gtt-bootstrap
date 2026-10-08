#!/usr/bin/env python3
"""GTT - sources, verifiable citations and the solution design of each Epic (engine).

    docs/sources/<ID>/vN/           the original source: copied, versioned, immutable     (evidence)
    gtt-domain/context/             architecture, stack, constraints                      (governed)
    gtt-domain/adr/                 architecturally significant decisions only            (governed)
    gtt-domain/context/design/      the solution design: one file per Epic                (governed)
    gtt-domain/backlog.md           Epics (approved intent) and Stories (the ADE's plan)  -> cite the design
    code

A Story is built from the Story and its Epic's design; the design cites the source; a source is
opened only to verify a citation. Everything here is computed from files, never judged:

  gtt_design.py source add FILE --id D [--version N] [--authority A] [--precedence N] [--text EXPORT.md] [--apply]
  gtt_design.py source adopt PATH --id D [--copy] [--apply]
  gtt_design.py source verify | list [--json] | impact ID
  gtt_design.py design scaffold EPIC-NNN [--apply]
  gtt_design.py design check [EPIC-NNN] [--pre-freeze] [--approval] [--json]
  gtt_design.py design coverage [--json]
  gtt_design.py approve EPIC-NNN [--by NAME]            (the human's act)

`source add` and `adopt` and `design scaffold` are dry runs without --apply. A source is never
edited after it is registered: a new version is added next to the old one. Exit 0 = ok, 1 = a
violation, 2 = cannot run.
"""

import argparse
import datetime
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
sys.dont_write_bytecode = True

SOURCES_MD = "gtt-domain/context/sources.md"
SOURCES_DIR = "docs/sources"
DESIGN_DIR = "gtt-domain/context/design"
BACKLOG = "gtt-domain/backlog.md"
STACK = "gtt-domain/context/stack.md"
FROZEN = "gtt-domain/.frozen"
PROPOSALS = "gtt-domain/proposals"
TEMPLATE = ".gtt/scaffold/templates/gtt-design-epic.md"
SIDECAR = ".gtt-source.json"
AUTHORITIES = ("primary", "secondary", "reference", "evidence")
SECTIONS = ("Purpose and scope", "Data", "Rules", "Flows", "Interfaces", "Examples", "Open points", "Decisions taken with the human")
ITEM = re.compile(r"^\s*[-*]\s+\*\*([RFIED])-(\d+)\*\*(.*)$")
CITE = re.compile(r"\[FUENTE:\s*([^\]]+)\]")
VACIO = re.compile(r"\[VAC[ÍI]O(?::\s*([^\]]*))?\]")
PLACEHOLDER = re.compile(r"<[^<>\n]{2,}>")
CANON = "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md"


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def sha256(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def frozen():
    return os.path.isfile(FROZEN)


def today():
    return datetime.date.today().isoformat()


def die(message, code=2):
    print(message, file=sys.stderr)
    sys.exit(code)


# ------------------------------------------------------------------------- the source manifest

def source_rows():
    """[{id, path, version, authority, precedence, status, sha, line}] from the `gtt-sources` block."""
    rows, inside = [], False
    for number, line in enumerate((read(SOURCES_MD) or "").split("\n"), 1):
        if not inside:
            inside = re.match(r"^```gtt-sources\s*$", line) is not None
        elif line.startswith("```"):
            break
        elif line.strip() and not line.lstrip().startswith("#") and not re.match(r"(?i)^\s*policy\s*:", line):
            cells = [c.strip() for c in line.split("|")]
            if len(cells) in (6, 7):
                rows.append({"id": cells[0], "path": cells[1], "version": cells[2], "authority": cells[3], "precedence": cells[4],
                             "status": cells[5], "sha": cells[6] if len(cells) == 7 else "", "line": number})
    return rows


def sidecars():
    """What `source add` recorded next to each copied file: the evidence of what was registered."""
    out = []
    for path in sorted(glob.glob(os.path.join(SOURCES_DIR, "*", "v*", SIDECAR))):
        try:
            record = json.loads(read(path) or "")
        except ValueError:
            continue
        record["dir"] = os.path.dirname(path).replace("\\", "/")
        out.append(record)
    return out


def version_number(text):
    found = re.fullmatch(r"v?(\d+)", str(text).strip())
    return int(found.group(1)) if found else None


def known_versions(source_id):
    """{N: {path, text, sha}} of a source: what the manifest declares and what was copied."""
    out = {}
    for row in source_rows():
        number = version_number(row["version"])
        if row["id"] == source_id and number is not None:
            out[number] = {"path": row["path"], "text": None, "sha": row["sha"], "status": row["status"]}
    for record in sidecars():
        if record.get("id") == source_id and isinstance(record.get("version"), int):
            entry = out.setdefault(record["version"], {"status": "registered"})
            entry["path"] = record["dir"] + "/" + record["name"]
            entry["text"] = record["dir"] + "/" + record["text"] if record.get("text") else None
            entry["sha"] = record.get("sha256", "")
    return out


def active_version(source_id):
    rows = [r for r in source_rows() if r["id"] == source_id and r["status"] == "active" and version_number(r["version"]) is not None]
    if rows:
        return version_number(rows[-1]["version"])
    versions = known_versions(source_id)
    return max(versions) if versions else None


def write_row(source_id, path, version, authority, precedence, digest):
    """Add the row of a new version to the manifest; the version that was active becomes `superseded`."""
    text = read(SOURCES_MD)
    if text is None:
        text = ("# Source Manifest\n\n" + CANON + "\n\nThe design sources this project treats as authorised. One line per version of a source:\n"
                "`id | path | version | authority | precedence | status | sha256`. Written by `.gtt/scripts/gtt-source.sh`;\n"
                "a source is immutable once registered - a new version is added next to the old one.\n\n"
                "## Sources\n\n```gtt-sources\n# policy: provenance=advisory\n```\n\n---\nGovernance: L0. Read-only for AI agents after freeze.\n")
    lines, out, inside, done = text.split("\n"), [], False, False
    row = f"{source_id} | {path} | v{version} | {authority} | {precedence} | active | {digest[:12]}"
    for line in lines:
        if not inside and re.match(r"^```gtt-sources\s*$", line):
            inside = True
        elif inside and line.startswith("```"):
            out.append(row)
            inside, done = False, True
        elif inside and line.strip() and not line.lstrip().startswith("#"):
            cells = [c.strip() for c in line.split("|")]
            if len(cells) in (6, 7) and cells[0] == source_id and cells[5] == "active":
                cells[5] = "superseded"
                line = " | ".join(cells)
        out.append(line)
    if not done:
        die(f"gtt-source: {SOURCES_MD} has no `gtt-sources` block to write to.")
    write(SOURCES_MD, "\n".join(out))


# ------------------------------------------------------------------------- sections and citations

def slug(title):
    text = re.sub(r"[^\w\s-]", "", title.strip().lower(), flags=re.UNICODE)
    return re.sub(r"[\s]+", "-", text).strip("-")


def sections_of(path):
    """{key: text} for every heading of a Markdown file, by its number (`3.4`) and by its slug."""
    text = read(path)
    if text is None:
        return None
    lines = text.split("\n")
    heads = []
    fence = False
    for index, line in enumerate(lines):
        if line.startswith("```"):
            fence = not fence
        found = None if fence else re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if found:
            heads.append((index, len(found.group(1)), found.group(2)))
    out = {}
    for position, (index, level, title) in enumerate(heads):
        end = next((i for i, lvl, _ in heads[position + 1:] if lvl <= level), len(lines))
        body = "\n".join(lines[index:end]).strip()
        number = re.match(r"^§?\s*(\d+(?:\.\d+)*)\.?(?:\s|$)", title)
        keys = {slug(title)}
        if number:
            keys.add(number.group(1))
            keys.add(slug(title[number.end():]))
        for key in keys:
            if key:
                out.setdefault(key, body)
    return out


def parse_ref(ref):
    """`D`, `D:§3.4`, `D@v1:§18`, `D:§16–22` -> (id, version or None, [section keys] or None, raw section)."""
    token = ref.strip().split()[0] if ref.strip() else ""
    found = re.fullmatch(r"([A-Za-z][\w.-]*?)(?:@v?(\d+))?(?::(.*))?", token)
    if not found:
        return None
    source_id, version, where = found.group(1), found.group(2), found.group(3)
    if where is None or not where.startswith("§"):
        return source_id, int(version) if version else None, None, where
    section = where[1:]
    span = re.fullmatch(r"(\d+(?:\.\d+)*)\s*[–—-]\s*(\d+(?:\.\d+)*)", section)
    if span and "." not in span.group(1) and "." not in span.group(2) and int(span.group(1)) <= int(span.group(2)):
        keys = [str(n) for n in range(int(span.group(1)), int(span.group(2)) + 1)]
        return source_id, int(version) if version else None, keys, section
    return source_id, int(version) if version else None, [section.strip().lower() if not re.match(r"^\d", section) else section.strip()], section


def text_of(source_id, version):
    """The Markdown text a citation is checked against, or None when the source has none."""
    entry = known_versions(source_id).get(version)
    if not entry:
        return None
    for candidate in (entry.get("text"), entry.get("path")):
        if candidate and candidate.lower().endswith((".md", ".markdown")) and os.path.isfile(candidate):
            return candidate
    return None


def check_citation(ref):
    """(level, message) for one [FUENTE: ref] to a declared source, or None when it holds."""
    parsed = parse_ref(ref)
    if not parsed:
        return None
    source_id, version, keys, raw = parsed
    versions = known_versions(source_id)
    if not versions:
        return None
    use = version if version is not None else active_version(source_id)
    if version is not None and version not in versions:
        return "FAIL", f"[FUENTE: {ref}] names version v{version} of `{source_id}`, which is not registered"
    if keys is None:
        return None
    document = text_of(source_id, use)
    if document is None:
        return "NOTE", f"[FUENTE: {ref}]: `{source_id}` has no Markdown text, so the section is checked by id only (register one with --text)"
    present = sections_of(document) or {}
    span = len(keys) > 1
    missing = [k for k in ((keys[0], keys[-1]) if span else keys) if k not in present]
    if missing:
        return "FAIL", f"[FUENTE: {ref}]: section §{', §'.join(missing)} does not exist in `{source_id}` v{use} ({document})"
    return None


def governed_files():
    files = sorted(glob.glob("gtt-domain/context/*.md")) + sorted(glob.glob(os.path.join(DESIGN_DIR, "*.md")))
    files += [f for f in sorted(glob.glob("gtt-domain/adr/ADR-*.md")) if "ADR-TEMPLATE" not in f]
    return [f.replace("\\", "/") for f in files]


def masked(text):
    blank = lambda match: re.sub(r"[^\n]", " ", match.group(0))
    text = re.sub(r"^```.*?^```", blank, text, flags=re.S | re.M)
    return re.sub(r"`[^`\n]*`", blank, text)


def citations(source_id=None):
    """[(file, line, ref)] of every [FUENTE] in governed files that names a declared source."""
    ids = {r["id"] for r in source_rows()} | {s.get("id") for s in sidecars()}
    out = []
    for path in governed_files():
        text = masked(read(path) or "")
        for found in CITE.finditer(text):
            parsed = parse_ref(found.group(1))
            if parsed and parsed[0] in ids and (source_id is None or parsed[0] == source_id):
                out.append((path, text.count("\n", 0, found.start()) + 1, found.group(1).strip()))
    return out


def impact(source_id, old, new):
    """What a new version does to the citations that do not pin a version: [(level, file, line, ref, why)]."""
    before, after = text_of(source_id, old), text_of(source_id, new)
    if not before or not after:
        return []
    old_sections, new_sections = sections_of(before) or {}, sections_of(after) or {}
    out = []
    for path, line, ref in citations(source_id):
        _, version, keys, _ = parse_ref(ref)
        if version is not None or not keys:
            continue
        gone = [k for k in keys if k in old_sections and k not in new_sections]
        changed = [k for k in keys if k in old_sections and k in new_sections and old_sections[k] != new_sections[k]]
        if gone:
            out.append(("FAIL", path, line, ref, f"section §{', §'.join(gone)} no longer exists in v{new}"))
        elif changed:
            out.append(("WARNING", path, line, ref, f"section §{', §'.join(changed)} changed between v{old} and v{new}: re-check"))
    return out


# ------------------------------------------------------------------------- gtt-source.sh

def cmd_source_add(args, adopt=False):
    source_id = args.id
    if not re.fullmatch(r"[A-Za-z][\w.-]*", source_id):
        die("gtt-source: --id must start with a letter and hold letters, digits, dot, dash or underscore.")
    origin = args.file
    if not os.path.isfile(origin):
        die(f"gtt-source: {origin} is not a file.")
    existing = known_versions(source_id)
    version = args.version or (max(existing) + 1 if existing else 1)
    if version in existing:
        die(f"gtt-source: `{source_id}` v{version} is already registered. A source is immutable: add the next version.", 1)
    copy = not adopt or args.copy
    name = os.path.basename(origin)
    target_dir = f"{SOURCES_DIR}/{source_id}/v{version}"
    path = f"{target_dir}/{name}" if copy else origin.replace("\\", "/")
    digest = sha256(origin)
    rows = [r for r in source_rows() if r["id"] == source_id]
    authority = args.authority or (rows[-1]["authority"] if rows else "primary")
    taken = {r["precedence"] for r in source_rows() if r["status"] == "active" and r["id"] != source_id}
    precedence = str(args.precedence) if args.precedence else (rows[-1]["precedence"] if rows else
                                                               str(next(n for n in range(1, 1000) if str(n) not in taken)))
    if authority in ("reference", "evidence") and not args.precedence and not rows:
        precedence = ""
    print(f"gtt-source: {'adopt' if adopt and not copy else 'add'} `{source_id}` v{version} <- {origin}")
    print(f"  {'in place' if not copy else 'copy to'} {path}  sha256 {digest[:12]}  authority {authority}  precedence {precedence or '-'}")
    previous = active_version(source_id)
    if frozen():
        print(f"  the project is frozen: {SOURCES_MD} is not touched; a change request lists the citations to re-check")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    text_name = None
    if copy:
        os.makedirs(target_dir, exist_ok=True)
        shutil.copyfile(origin, path)
        if args.text:
            if not os.path.isfile(args.text):
                die(f"gtt-source: --text {args.text} is not a file.")
            text_name = os.path.splitext(name)[0] + ".text.md"
            shutil.copyfile(args.text, f"{target_dir}/{text_name}")
        write(f"{target_dir}/{SIDECAR}", json.dumps({"schema": 1, "id": source_id, "version": version, "name": name, "sha256": digest,
                                                      "text": text_name, "added": today(), "origin": origin.replace("\\", "/")}, indent=2) + "\n")
    affected = impact(source_id, previous, version) if previous and copy else []
    if frozen():
        note = f"{PROPOSALS}/CHANGE-REQUEST-source-{source_id}-v{version}.md"
        body = [f"# Change request - new version of source `{source_id}` (v{version})", "", CANON, "",
                f"`{path}` was registered on {today()}. The governed context was not changed. Copy the block below into",
                "`gtt-domain/change-request.md` to start the change: THINK, then a specification change or an ADR, then a new freeze.", "",
                "```text", f"Change: adopt version v{version} of source {source_id} ({path}); declare it in {SOURCES_MD} and re-check the citations below.",
                f"Reason: the source changed; {len(affected)} citation(s) that do not pin a version point at sections that changed or are gone.",
                "Trigger: a new version of a design source.", "Scope: the citations listed here, and the parts of the governed context they support.",
                "Impact: every design and context file listed below.", "Risk: a citation that silently means something else.", "Priority: medium", "```", "",
                "## Citations to re-check", ""]
        body += [f"- {level}: `{file}:{line}` [FUENTE: {ref}] - {why}" for level, file, line, ref, why in affected] or ["- none: no citation is affected"]
        write(note, "\n".join(body) + "\n")
        print(f"gtt-source: registered. Change request drafted at {note}")
    else:
        write_row(source_id, path, version, authority, precedence, digest)
        print(f"gtt-source: registered in {SOURCES_MD}." + (f" v{previous} is now superseded." if previous else ""))
    for level, file, line, ref, why in affected:
        print(f"  {level}: {file}:{line} [FUENTE: {ref}] - {why}")
    return 0


def cmd_source_verify(args):
    problems, checked = [], 0
    for row in source_rows():
        if row["sha"] and os.path.isfile(row["path"]):
            checked += 1
            if not (sha256(row["path"]) or "").startswith(row["sha"]):
                problems.append(f"{row['path']} (`{row['id']}` {row['version']}) no longer matches its registered sha256 {row['sha']}")
        elif row["sha"]:
            problems.append(f"{row['path']} (`{row['id']}` {row['version']}) is registered and missing")
    for record in sidecars():
        path = f"{record['dir']}/{record.get('name')}"
        checked += 1
        if sha256(path) != record.get("sha256"):
            problems.append(f"{path} (`{record.get('id')}` v{record.get('version')}) was edited or removed after it was registered")
    for problem in problems:
        print(f"gtt-source: FAILED - {problem}. Sources are immutable: restore it, or add a new version.", file=sys.stderr)
    if not problems:
        print(f"gtt-source: OK - {checked} registered source file(s) match their hash.")
    return 1 if problems else 0


def cmd_source_list(args):
    cited = {}
    for _, _, ref in citations():
        cited[parse_ref(ref)[0]] = cited.get(parse_ref(ref)[0], 0) + 1
    rows = [dict(r, citations=cited.get(r["id"], 0)) for r in source_rows()]
    declared = {(r["id"], version_number(r["version"])) for r in rows}
    for record in sidecars():
        if (record.get("id"), record.get("version")) not in declared:
            rows.append({"id": record["id"], "path": f"{record['dir']}/{record['name']}", "version": f"v{record['version']}", "authority": "-",
                         "precedence": "-", "status": "registered, not declared", "sha": record.get("sha256", "")[:12], "citations": cited.get(record["id"], 0)})
    if args.json:
        print(json.dumps({"schema": 1, "kind": "gtt-sources", "sources": rows}, indent=2, sort_keys=True))
    else:
        for row in rows:
            print(f"{row['id']:14} {row['version']:5} {row['status']:24} {row['authority']:10} {row['citations']:3} citation(s)  {row['path']}")
        if not rows:
            print("no sources registered (bash .gtt/scripts/gtt-source.sh add <file> --id <ID> --apply)")
    return 0


def cmd_source_impact(args):
    versions = sorted(known_versions(args.id))
    if len(versions) < 2:
        print(f"gtt-source: `{args.id}` has fewer than two versions: nothing to compare.")
        return 0
    found = impact(args.id, versions[-2], versions[-1])
    for level, file, line, ref, why in found:
        print(f"{level}: {file}:{line} [FUENTE: {ref}] - {why}")
    if not found:
        print(f"gtt-source: no citation of `{args.id}` is affected between v{versions[-2]} and v{versions[-1]}.")
    return 1 if any(level == "FAIL" for level, *_ in found) else 0


# ------------------------------------------------------------------------- the design of an Epic

def backlog():
    try:
        import gtt_backlog
        return gtt_backlog.parse(BACKLOG) if os.path.isfile(BACKLOG) else ([], [])
    except Exception:
        return [], []


def design_path(epic_id):
    return f"{DESIGN_DIR}/{epic_id}.md"


def parse_design(path):
    """{status, sections: {n: text}, items: {'R-1': line}, listed: [refs], cites: {n: [refs]}, examples: {'E-1': [ids]}}"""
    text = read(path)
    if text is None:
        return None
    status = re.search(r"\*\*Status:\*\*\s*([A-Za-z]+)", text)
    sections, current = {}, None
    for line in text.split("\n"):
        head = re.match(r"^##\s+(\d)\.\s+(.*)$", line)
        if head:
            current = int(head.group(1))
            sections[current] = ""
        elif current is not None:
            sections[current] += line + "\n"
    listed = re.search(r"\*\*Source sections:\*\*\s*(.*)", sections.get(1, ""))
    items, duplicates, examples, unsupported = {}, [], {}, []
    for number in (2, 3, 4, 5, 6, 8):
        for line in sections.get(number, "").split("\n"):
            found = ITEM.match(line)
            if not found:
                continue
            key = f"{found.group(1)}-{found.group(2)}"
            if key in items:
                duplicates.append(key)
            items[key] = line
            if found.group(1) == "E":
                examples[key] = re.findall(r"\b([RFI]-\d+)\b", found.group(3))
            if found.group(1) != "D" and not CITE.search(line) and not re.search(r"\bD-\d+\b", found.group(3)):
                unsupported.append(key)
    cites = [found.group(1).strip() for number in range(2, 7) for found in CITE.finditer(masked(sections.get(number, "")))]
    return {"path": path, "text": text, "status": status.group(1) if status else "", "sections": sections, "items": items,
            "duplicates": duplicates, "examples": examples, "unsupported": unsupported, "cites": cites,
            "listed": [r.strip() for r in re.split(r"\s*[·,;]\s*", listed.group(1)) if r.strip()]
            if listed and not PLACEHOLDER.search(listed.group(1)) else [],
            "open": [found.group(1) or "" for found in VACIO.finditer(masked(text))]}


def covered(listed_ref, cites):
    """True when a listed source section is cited at least once in sections 2 to 6 (a citation of a
    subsection, or a range that contains it, covers it)."""
    parsed = parse_ref(listed_ref)
    if not parsed or not parsed[2]:
        return True
    source_id, _, wanted, _ = parsed
    have = set()
    for cite in cites:
        other = parse_ref(cite)
        if other and other[0] == source_id and other[2]:
            have.update(other[2])
    return all(any(key == want or key.startswith(want + ".") for key in have) for want in wanted)


def blocking_gaps():
    block = re.search(r"```gtt-gaps\r?\n(.*?)```", read(STACK) or "", re.DOTALL)
    return {parts[1].strip() for parts in (line.split("|") for line in (block.group(1).splitlines() if block else []))
            if len(parts) > 1 and parts[0].strip() == "BLOCKING"}


def design_problems(design, approval=False):
    """([FAIL messages], [notes]) for one design. Completeness is the same in every plan and at every depth."""
    fails, notes = [], []
    for number, title in enumerate(SECTIONS, 1):
        body = design["sections"].get(number)
        if body is None:
            fails.append(f"section `## {number}. {title}` is missing: the eight sections always exist")
        elif not body.strip():
            fails.append(f"section {number} ({title}) is empty: write its content, or `N/A — <reason>`")
    for key in sorted(set(design["duplicates"])):
        fails.append(f"{key} is defined twice: ids are stable and never reused")
    if not design["listed"]:
        fails.append("`**Source sections:**` lists no section of the sources: nothing shows what was carried over")
    for ref in design["listed"]:
        if not covered(ref, design["cites"]):
            fails.append(f"source section {ref} is listed and never cited in sections 2 to 6: part of the source did not reach the design")
    for key in design["unsupported"]:
        fails.append(f"{key} carries neither a [FUENTE] nor a D-n: nothing supports it")
    used = {ref for refs in design["examples"].values() for ref in refs}
    lonely = sorted(k for k in design["items"] if k[0] in "RF" and k not in used)
    for key in lonely:
        fails.append(f"{key} appears in no example: every rule and flow is shown by at least one E-n")
    blocking = sorted(blocking_gaps() & set(design["open"]))
    if approval or design["status"] == "Approved":
        if PLACEHOLDER.search(masked(design["text"])):
            fails.append("template text (`<...>`) is still there: an approved design has none")
        for gap in blocking:
            fails.append(f"[VACÍO: {gap}] is a BLOCKING gap: it is decided before the design is approved")
    opened = [g for g in design["open"] if g not in blocking]
    if opened:
        notes.append(f"{len(opened)} open point(s) cross as explicit pending items: {', '.join(sorted(set(g or 'unclassified' for g in opened)))}")
    return fails, notes


def epic_design(epic):
    declared = epic["fields"].get("Design", "").strip().strip("`")
    return declared or design_path(epic["id"])


def implements_of(story):
    """The design items a Story says it builds: {(epic design file, 'R-2'), ...} and the ADRs it names."""
    field = story["fields"].get("Implements", "")
    items, last = set(), None
    for token in re.findall(r"(?:design/(EPIC-\d+))?#([RFIED]-\d+)", field):
        last = token[0] or last
        if last:
            items.add((last, token[1]))
    return items, re.findall(r"\bADR-\d{3,}\b", field)


def coverage():
    """Per Epic with a design: the R, F and I items no Story implements yet, and whether the Epic is closed."""
    stories, epics = backlog()
    out = []
    for epic in epics:
        design = parse_design(epic_design(epic))
        if design is None:
            continue
        own = [s for s in stories if s["epic"] == epic["id"] and s["status"] != "Cancelled"]
        built = {item for s in own for file, item in implements_of(s)[0] if file == epic["id"]}
        missing = sorted((k for k in design["items"] if k[0] in "RFI" and k not in built), key=lambda k: ("RFI".index(k[0]), int(k[2:])))
        closed = bool(own) and all(s["status"] == "Done" for s in own)
        working = any(s["status"] in ("In Progress", "Done") for s in own)
        out.append({"epic": epic["id"], "missing": missing, "closed": closed, "working": working})
    return out


def check_all(only=None, prefreeze=False, approval=False):
    """([(level, where, message)], summary) over every design, the Epics that need one, and the coverage."""
    findings = []
    stories, epics = backlog()
    by_id = {e["id"]: e for e in epics}
    paths = sorted(glob.glob(os.path.join(DESIGN_DIR, "EPIC-*.md")))
    for path in paths:
        epic_id = os.path.basename(path)[:-3]
        if only and epic_id != only:
            continue
        design = parse_design(path.replace("\\", "/"))
        fails, notes = design_problems(design, approval)
        # A draft that is still being written warns; an approved design, or one about to be approved, fails.
        level = "FAIL" if (approval or design["status"] == "Approved") else "WARN"
        for message in fails:
            findings.append((level, path, message + ("" if level == "FAIL" else " (draft)")))
        for message in notes:
            findings.append(("NOTE", path, message))
        if epic_id not in by_id:
            findings.append(("WARN", path, f"no {epic_id} in {BACKLOG}: a design belongs to an Epic"))
    for epic in epics:
        if only and epic["id"] != only:
            continue
        path = epic_design(epic)
        design = parse_design(path)
        if epic["status"] in ("Planned", "In Progress", "Completed"):
            if design is None:
                findings.append(("FAIL" if prefreeze else "WARN", BACKLOG, f"{epic['id']} is approved and has no design ({path}): "
                                 "an approved Epic needs its complete, approved design" + ("" if prefreeze else " before the next freeze")))
            elif design["status"] != "Approved":
                findings.append(("FAIL" if prefreeze else "WARN", path, f"{epic['id']} is approved and its design is `{design['status'] or 'not stated'}`: "
                                 "approve both together (bash .gtt/scripts/gtt-approve.sh " + epic["id"] + ")"))
    for entry in coverage():
        if only and entry["epic"] != only:
            continue
        if entry["missing"] and entry["closed"]:
            findings.append(("FAIL", BACKLOG, f"{entry['epic']}: every Story is Done and {', '.join(entry['missing'])} of its design was never implemented"))
    return findings


def cmd_design_check(args):
    findings = check_all(args.epic, args.pre_freeze, args.approval)
    if args.json:
        print(json.dumps({"schema": 1, "kind": "gtt-design-check", "result": "fail" if any(f[0] == "FAIL" for f in findings) else "pass",
                          "findings": [{"level": l, "where": w, "message": m} for l, w, m in findings], "coverage": coverage()}, indent=2, sort_keys=True))
    else:
        for level, where, message in findings:
            print(f"{level}  {where}: {message}", file=sys.stderr if level == "FAIL" else sys.stdout)
        if not any(f[0] == "FAIL" for f in findings):
            count = len(glob.glob(os.path.join(DESIGN_DIR, "EPIC-*.md")))
            drafts = len({w for l, w, m in findings if l == "WARN" and m.endswith("(draft)")})
            print(f"gtt-check-design: OK - {count} design(s) checked; no approved design is incomplete"
                  + (f"; {drafts} draft(s) still to complete (warnings above)." if drafts else "."))
    return 1 if any(f[0] == "FAIL" for f in findings) else 0


def cmd_design_coverage(args):
    data = coverage()
    if args.json:
        print(json.dumps({"schema": 1, "kind": "gtt-design-coverage", "epics": data}, indent=2, sort_keys=True))
    else:
        for entry in data:
            print(f"{entry['epic']}: " + ("design items not planned: " + ", ".join(entry["missing"]) if entry["missing"] else "every design item is in a Story"))
    return 0


def cmd_design_scaffold(args):
    _, epics = backlog()
    epic = next((e for e in epics if e["id"] == args.epic), None)
    if epic is None:
        die(f"gtt-design: {args.epic} is not in {BACKLOG}.")
    template = read(TEMPLATE)
    if template is None:
        die(f"gtt-design: {TEMPLATE} not found.")
    lines = (read(BACKLOG) or "").split("\n")
    title = re.sub(r"^#+\s*EPIC-\d+\s*[-—–:]*\s*", "", lines[epic["line"] - 1]).strip() or "<title>"
    target = design_path(args.epic) if not frozen() else f"{PROPOSALS}/design-{args.epic}.md"
    if os.path.exists(design_path(args.epic)) or os.path.exists(target):
        print(f"gtt-design: CONFLICT - a design for {args.epic} already exists; it is never overwritten.", file=sys.stderr)
        return 1
    print(f"gtt-design: scaffold {args.epic} -> {target}")
    if frozen():
        print(f"  the project is frozen: the draft goes to {PROPOSALS}/ and reaches {design_path(args.epic)} through a promotion set")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    body = template[template.index("# EPIC-NNN"):] if "# EPIC-NNN" in template else template
    write(target, body.replace("EPIC-NNN", args.epic).replace("<title>", title, 1))
    print(f"created {target}. List every source section of this Epic under `Source sections`, carry its content over in full")
    print("with a [FUENTE] on each line, write what the sources do not define as [VACÍO], and ask the human for those.")
    return 0


# ------------------------------------------------------------------------- approval (the human's act)

def replace_line(path, pattern, new, after=None):
    """Replace the first line matching `pattern`, or insert `new` after the first line matching `after`."""
    lines = (read(path) or "").split("\n")
    for index, line in enumerate(lines):
        if re.match(pattern, line):
            lines[index] = new
            break
    else:
        for index, line in enumerate(lines):
            if after and re.match(after, line):
                lines.insert(index + 1, new)
                break
        else:
            return False
    write(path, "\n".join(lines))
    return True


def cmd_approve(args):
    stories, epics = backlog()
    epic = next((e for e in epics if e["id"] == args.epic), None)
    if epic is None:
        die(f"gtt-approve: {args.epic} is not in {BACKLOG}.")
    path = epic_design(epic)
    design = parse_design(path)
    print("@gtt · Approval")
    print(f"{args.epic}  Goal: {epic['fields'].get('Goal', '(none stated)')}")
    print(f"          Scope: {epic['fields'].get('Scope', '(none stated)')}")
    if design is None:
        print(f"gtt-approve: {args.epic} has no design ({path}). Nothing was approved: bash .gtt/scripts/gtt-design.sh scaffold {args.epic} --apply", file=sys.stderr)
        return 1
    count = lambda letter: sum(1 for k in design["items"] if k[0] == letter)
    cited = sum(1 for ref in design["listed"] if covered(ref, design["cites"]))
    used = {ref for refs in design["examples"].values() for ref in refs}
    lonely = sorted(k for k in design["items"] if k[0] in "RF" and k not in used)
    print(f"Design    {path}: {count('R')} rules, {count('F')} flows, {count('I')} interfaces, {count('E')} examples")
    print(f"          source sections covered: {cited}/{len(design['listed'])} · rules or flows without an example: {', '.join(lonely) or 'none'}"
          f" · open points: {len(design['open'])}")
    fails = [m for level, where, m in check_all(args.epic, approval=True) if level == "FAIL"]
    if fails:
        for message in fails:
            print(f"  missing: {message}", file=sys.stderr)
        print("gtt-approve: the design is not complete. Nothing was approved.", file=sys.stderr)
        return 1
    print("Type `approve` to approve this Epic and its design together, anything else to cancel: ", end="", flush=True)
    if sys.stdin.readline().strip() != "approve":
        print("gtt-approve: not confirmed; nothing was written.", file=sys.stderr)
        return 1
    who = args.by or (subprocess.run(["git", "config", "user.name"], capture_output=True, text=True).stdout.strip() or os.environ.get("USER") or "unknown")
    stamp = f"{who} — {today()}"
    originals = {BACKLOG: read(BACKLOG), path: design["text"]}
    lines = originals[BACKLOG].split("\n")
    end = next((i for i in range(epic["line"], len(lines)) if re.match(r"^(### |## |---)", lines[i])), len(lines))
    block = lines[epic["line"]:end]
    for index, line in enumerate(block):
        if re.match(r"^\*\*Status:\*\*\s*Proposed\s*$", line):
            block[index] = "**Status:** Planned"
    block = [l for l in block if not re.match(r"^\*\*(Approved|Design):\*\*", l)]
    anchor = next((i for i, l in enumerate(block) if re.match(r"^\*\*", l)), 0)
    last = max((i for i, l in enumerate(block) if re.match(r"^\*\*[^*]+:\*\*", l)), default=anchor)
    block[last + 1:last + 1] = [f"**Design:** {path}", f"**Approved:** {stamp}"]
    write(BACKLOG, "\n".join(lines[:epic["line"]] + block + lines[end:]))
    replace_line(path, r"^\*\*Epic:\*\*.*\*\*Status:\*\*", re.sub(r"\*\*Status:\*\*.*$", f"**Status:** Approved — {stamp}",
                                                                 next(l for l in design["text"].split("\n") if "**Status:**" in l)))
    if frozen():
        done = subprocess.run(["bash", os.path.join(".gtt", "scripts", "gtt-freeze.sh")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if done.returncode != 0:
            for target, text in originals.items():
                write(target, text)
            print(done.stdout + done.stderr, file=sys.stderr)
            print("gtt-approve: the new freeze failed, so nothing was approved: both files are as they were.", file=sys.stderr)
            return 1
        print("A new freeze was recorded with this approval.")
    print(f"Approved {args.epic} and its design - {stamp}. Nothing was staged or committed.")
    return 0


def main(argv):
    if not os.path.isdir(".gtt"):
        die("gtt-design: run from the project root (no .gtt/ directory here)")
    parser = argparse.ArgumentParser(prog="gtt_design.py")
    sub = parser.add_subparsers(dest="area", required=True)
    source = sub.add_parser("source").add_subparsers(dest="action", required=True)
    for name in ("add", "adopt"):
        p = source.add_parser(name)
        p.add_argument("file"); p.add_argument("--id", required=True); p.add_argument("--version", type=int)
        p.add_argument("--authority", choices=AUTHORITIES); p.add_argument("--precedence", type=int); p.add_argument("--text")
        p.add_argument("--copy", action="store_true"); p.add_argument("--apply", action="store_true")
        p.set_defaults(func=lambda a, adopt=(name == "adopt"): cmd_source_add(a, adopt))
    source.add_parser("verify").set_defaults(func=cmd_source_verify)
    p = source.add_parser("list"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_source_list)
    p = source.add_parser("impact"); p.add_argument("id"); p.set_defaults(func=cmd_source_impact)
    design = sub.add_parser("design").add_subparsers(dest="action", required=True)
    p = design.add_parser("scaffold"); p.add_argument("epic"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_design_scaffold)
    p = design.add_parser("check"); p.add_argument("epic", nargs="?"); p.add_argument("--pre-freeze", action="store_true")
    p.add_argument("--approval", action="store_true"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_design_check)
    p = design.add_parser("coverage"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_design_coverage)
    p = sub.add_parser("approve"); p.add_argument("epic"); p.add_argument("--by"); p.set_defaults(func=cmd_approve)
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
