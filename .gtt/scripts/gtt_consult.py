#!/usr/bin/env python3
"""GTT - the consultation thread: the questions that need thinking go to ONE conversation in Claude web.

  gtt_consult.py status [--json]            the thread, the open questions, what changed since the last answer
  gtt_consult.py seed [--json]              the first message of the thread: summaries of the design, each with its anchor
  gtt_consult.py batch [REF] [--json]       the open questions (or one) as a message for the thread, with what changed in the design
  gtt_consult.py set URL                    register the thread (https://claude.ai/chat/<id>): Sonar shows it at the top and its questions point to it
  gtt_consult.py clear                      forget it
  gtt_consult.py seen                       take the thread as up to date with today's design
  gtt_consult.py answers [--text T] [--apply]   read the «Respuesta para GTT» block the person pastes and record each answer

A business question needs more thinking than a coding agent should spend its context on, and a long conversation with the person's own
context is the right place for it. The thread is a WORKSPACE and GTT is the memory: the decisions, the ADRs and the recorded answers are the
authority, the thread is disposable and is re-seeded from those records when it fills. Nothing is sent by this script: Sonar copies the text and
opens the thread when the person clicks, and the person pastes. The answer comes back as a block the person pastes into their agent; only
then is it recorded (always the human's act and in their words), and Sonar shows the question as answered.

DATA-FREE HELPER in the sense of gtt_act: it reads the project's records and writes only .gtt/local/consult.json (per person, never committed).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse

CONTRACT = ".gtt/contract/consult.json"
METHOD = ".gtt/methodology.json"
CONTEXT = "gtt-domain/context"
ADR_DIR = "gtt-domain/adr"
PROPOSALS = "gtt-domain/proposals"
FROZEN = "gtt-domain/.frozen"

LABELS = {
    "es": {"vision": "Visión", "architecture": "Arquitectura", "constraints": "Restricciones", "principles": "Principios"},
    "en": {"vision": "Vision", "architecture": "Architecture", "constraints": "Constraints", "principles": "Principles"},
}


# --------------------------------------------------------------------------------------------------------------- basics

def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read().replace("\r\n", "\n")
    except OSError:
        return None


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def write_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


_CONTRACT = []


def contract():
    if not _CONTRACT:
        data = read_json(CONTRACT)
        if not data:
            print(f"gtt-consult: {CONTRACT} is missing: run from the project root.", file=sys.stderr)
            sys.exit(2)
        _CONTRACT.append(data)
    return _CONTRACT[0]


def lang():
    return "es" if (read_json(METHOD) or {}).get("language") == "es" else "en"


def T(key, **kw):
    table = contract()["texts"][lang()]
    return table[key].format(**kw) if kw else table[key]


def state_path():
    return contract()["state_file"]


def state():
    """The person's consultation state. The thread is registered ONCE and remembered for good: the project's own file (.gtt/local) and the person's
    register (~/.gtt/threads.json) hold it, so a new clone, a worktree, a moved folder or a cleaned .gtt/local does not ask for it again."""
    st = read_json(state_path()) or {"schema": 1}
    mine = st.get("thread") if isinstance(st.get("thread"), dict) else {}
    kept, cut = remembered(), cleared()
    if mine.get("url") and cut and str(mine.get("set_at") or "") <= cut:
        st.pop("thread", None)                                 # forgotten (`clear`) from another copy of the project after this one was set
        mine = {}
    if mine.get("url"):
        if kept is None:
            remember(mine)                                     # a thread registered before the register existed: kept from now on
        elif kept["set_at"] > str(mine.get("set_at") or ""):
            st["thread"] = kept                                # set later from another copy of the project (a new thread): the latest wins
    elif kept is not None:
        st["thread"] = kept                                    # nothing here, but the person already registered this project: adopted, in silence
    return st


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------------------- the person's register of threads

def register_path():
    """~/.gtt/threads.json (GTT_HOME when set, like the CLI): the person's own, outside every project, never committed."""
    home = os.environ.get("GTT_HOME") or os.path.join(os.path.expanduser("~"), ".gtt")
    return os.path.join(home, "threads.json")


def _git(*args):
    try:
        done = subprocess.run(["git", *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


_IDENTITIES = {}


def identities():
    """How this project is recognised again, most stable first: the first commit of its repository (the same in every clone and worktree),
    its remote (the same when history was rewritten), and its folder (the same when .gtt/local was wiped). A project inside a bigger repository
    adds its folder's place in it, so two projects of one repository do not share a thread."""
    here = os.getcwd()
    if here in _IDENTITIES:
        return _IDENTITIES[here]
    keys = []
    inside = _git("rev-parse", "--show-prefix").strip("/")
    roots = sorted(_git("rev-list", "--max-parents=0", "HEAD").split())
    if roots:
        keys.append("git:" + roots[0] + ("/" + inside if inside else ""))
    remote = _git("config", "--get", "remote.origin.url").lower()
    if remote:
        remote = re.sub(r"^[a-z+]+://", "", remote)
        remote = re.sub(r"^[^@/]*@", "", remote).replace(":", "/")
        remote = re.sub(r"(\.git)?/*$", "", remote)
        keys.append("remote:" + remote + ("/" + inside if inside else ""))
    keys.append("path:" + os.path.realpath(here))
    _IDENTITIES[here] = keys
    return keys


def remembered():
    """The thread the person registered for this project (from any copy of it), or None. The register is a file the person can edit: the URL is
    checked again, as `set` does."""
    threads = (read_json(register_path()) or {}).get("threads")
    if not isinstance(threads, dict):
        return None
    best, cut = None, cleared()
    for key in identities():
        entry = threads.get(key)
        url = thread_url(entry.get("url")) if isinstance(entry, dict) else None
        if url:
            found = {"url": url, "set_at": str(entry.get("set_at") or "")}
            if cut and found["set_at"] <= cut:
                continue                                       # forgotten after it was set
            if best is None or found["set_at"] > best["set_at"]:
                best = found
    return best


def remember(thread):
    """Keeps the thread under every identity of the project. Best effort: a home that cannot be written must never stop the work."""
    try:
        data = read_json(register_path()) or {}
        threads = data.get("threads") if isinstance(data.get("threads"), dict) else {}
        for key in identities():
            threads[key] = {"url": thread["url"], "set_at": thread.get("set_at") or now_iso(), "project": project_name()}
        write_json(register_path(), {"schema": 1, "threads": threads})
    except OSError:
        pass


def cleared():
    """When the person last forgot the thread of this project (`clear`), or "". A thread set before that is a forgotten one, in any copy."""
    threads = (read_json(register_path()) or {}).get("threads")
    stamps = [str(e.get("cleared_at") or "") for k, e in (threads or {}).items() if k in identities() and isinstance(e, dict) and not e.get("url")]
    return max(stamps) if stamps else ""


def forget():
    """`clear` is the only thing that makes GTT forget this project's thread: it leaves a mark (with its time), so a copy that still holds the old
    thread does not bring it back."""
    try:
        data = read_json(register_path()) or {}
        threads = data.get("threads") if isinstance(data.get("threads"), dict) else {}
        for key in identities():
            threads[key] = {"cleared_at": now_iso(), "project": project_name()}
        write_json(register_path(), {"schema": 1, "threads": threads})
    except OSError:
        pass


def project_name():
    return os.path.basename(os.getcwd().rstrip(os.sep)) or "project"


def clean(text, limit=None):
    """One plain line: markdown marks, links and runs of spaces gone; cut at a word with an ellipsis."""
    s = re.sub(r"\[(?:FUENTE|VAC[IÍ]O|PROPUESTA|CONFLICTO)\b[^\]]*\]", "", str(text or ""))        # provenance tags are the design's bookkeeping, not its content
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`]+", "", s)
    s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if limit and len(s) > limit:
        cut = s[:limit].rsplit(" ", 1)[0]
        s = (cut if len(cut) > limit * 0.6 else s[:limit]).rstrip(" ,;:-—") + "…"
    return s


def first_sentence(text, limit):
    s = clean(text)
    match = re.match(r"(.{20,}?[.!?])(\s|$)", s)
    if match and len(match.group(1)) <= limit:
        return match.group(1)
    return clean(s, limit)


def slug(heading):
    try:
        import gtt_artifacts
        return gtt_artifacts.gh_slug(heading)
    except Exception:
        s = re.sub(r"[^\w\s-]", "", clean(heading).lower(), flags=re.UNICODE)
        return re.sub(r"\s+", "-", s.strip())


# ------------------------------------------------------------------------------------------------------- Sonar addresses

_BASE = []
LINKS = True        # off while the snapshot is made: a snapshot is a pure function of the project, and whether Sonar happens to be open is not part of it


def sonar_base():
    """(prefix, served): only the SERVED page can be opened from a link inside Claude web (a file:// page cannot), and only for a
    project Sonar was opened for. Else (None, False): the text then carries refs and paths, no address."""
    if not LINKS:
        return None, False
    if not _BASE:
        try:
            import gtt_link
            prefix, served = gtt_link.base()
            _BASE.append((prefix, served) if prefix and served else (None, False))
        except Exception:
            _BASE.append((None, False))
    return _BASE[0]


def ref_link(ref):
    prefix, served = sonar_base()
    if not prefix:
        return ""
    try:
        import gtt_link
        return gtt_link.url_for(ref, prefix, served) or ""
    except Exception:
        return ""


def doc_link(path):
    prefix, served = sonar_base()
    if not prefix:
        return ""
    return f"{prefix}#/view=design&dt=docs&doc={urllib.parse.quote(path, safe='')}&repo={urllib.parse.quote(os.path.abspath('.'), safe='')}"


# -------------------------------------------------------------------------------------------------- governed state, changes

def governed_files():
    out = []
    for base in (CONTEXT, ADR_DIR):
        for here, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d != "drafts"]
            for name in names:
                if name.endswith(".md"):
                    out.append(os.path.join(here, name).replace(os.sep, "/"))
    return sorted(out)


def governed_state():
    out = {}
    for path in governed_files():
        try:
            with open(path, "rb") as handle:
                out[path] = hashlib.sha256(handle.read()).hexdigest()
        except OSError:
            pass
    return out


def stamp(files=None):
    files = governed_state() if files is None else files
    return hashlib.sha256("\n".join(f"{k} {v}" for k, v in sorted(files.items())).encode("utf-8")).hexdigest()[:10]


def title_of(path):
    text = read_text(path) or ""
    for line in text.splitlines():
        if line.startswith("# "):
            return clean(line[2:], 90)
    return os.path.basename(path)


def changes():
    """What the governed design did since the thread was last taken as up to date: [{kind, path, title, link}]. Empty with no baseline."""
    seen = (state().get("seen") or {}).get("files")
    if not isinstance(seen, dict):
        return []
    now = governed_state()
    out = []
    for path in sorted(set(now) | set(seen)):
        if path not in seen:
            kind = "added"
        elif path not in now:
            kind = "removed"
        elif seen[path] != now[path]:
            kind = "changed"
        else:
            continue
        out.append({"kind": kind, "path": path, "title": title_of(path) if kind != "removed" else os.path.basename(path), "link": doc_link(path) if kind != "removed" else ""})
    return out


def mark_seen():
    data = state()
    data["seen"] = {"files": governed_state(), "at": now_iso()}
    write_json(state_path(), data)


# ------------------------------------------------------------------------------------------------------- the design, summarised

def md_sections(path, limit):
    """[(heading, anchor, first sentence)] of the `##`/`###` sections of a document, skipping code, tables, quotes and the canonical line."""
    text = read_text(path)
    if text is None:
        return []
    out, heading, buf, fence = [], None, [], False

    def flush():
        if heading is not None:
            para = []
            for line in buf:
                stripped = line.strip()
                if not stripped:
                    if para:
                        break
                    continue
                if stripped.startswith((">", "|", "<", "```", "---", "#")):
                    if para:
                        break
                    continue
                para.append(stripped)
            summary = first_sentence(" ".join(para), contract()["seed"]["summary_chars"])
            if summary:
                out.append((clean(heading, 70), slug(heading), summary))
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r"^(#{2,3})\s+(.+?)\s*#*\s*$", line)
        if m:
            flush()
            heading, buf = m.group(2), []
        elif heading is not None:
            buf.append(line)
    flush()
    return out[:limit]


def doc_block(key, filename, cap):
    path = f"{CONTEXT}/{filename}"
    rows = md_sections(path, contract()["seed"]["sections_per_doc"])
    if not rows:
        return ""
    base = os.path.basename(path)
    lines = [f"### {LABELS[lang()][key]} — {path}"]
    used = len(lines[0])
    for heading, anchor, summary in rows:
        line = T("doc_line", heading=heading, anchor=f"{base}#{anchor}", summary=summary)
        if used + len(line) > cap:
            link = doc_link(path)
            lines.append(T("more_in_sonar", link=link) if link else f"(… {path})")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def table_rows(path, wanted=14):
    """The first markdown table of a document as [(first cell, second cell)] without its header."""
    text = read_text(path) or ""
    rows, started = [], False
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = [clean(c) for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                started = True
                continue
            if started and len(cells) >= 2 and cells[0] and cells[1]:
                rows.append((cells[0], cells[1]))
        elif started:
            break
        if len(rows) >= wanted:
            break
    return rows


def stack_block(cap):
    rows = table_rows(f"{CONTEXT}/stack.md")
    if not rows:
        return ""
    lines = [T("stack_head")]
    used = len(lines[0])
    for a, b in rows:
        line = f"- {clean(a, 40)}: {clean(b, 90)}"
        if used + len(line) > cap:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines) if len(lines) > 1 else ""


def glossary_block(cap):
    text = read_text(f"{CONTEXT}/glossary.md") or ""
    terms = []
    for line in text.splitlines():
        m = re.match(r"^\s*(?:[-*]\s+)?\*\*(.+?)\*\*\s*[:—–-]\s*(.+)$", line)
        if m:
            terms.append((clean(m.group(1), 40), clean(m.group(2), 90)))
        elif line.strip().startswith("|"):
            cells = [clean(c) for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and cells[1] and not set("".join(cells)) <= set("-: ") and cells[0].lower() not in ("term", "término", "termino"):
                terms.append((cells[0][:40], cells[1][:90]))
        if len(terms) >= contract()["seed"]["glossary_terms"]:
            break
    if not terms:
        return ""
    lines, used = [T("glossary_head")], 0
    for a, b in terms:
        line = f"- {a}: {b}"
        if used + len(line) > cap:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines) if len(lines) > 1 else ""


def adr_block(cap):
    files = sorted((f for f in os.listdir(ADR_DIR) if re.match(r"ADR-\d+", f) and f.endswith(".md")), reverse=True) if os.path.isdir(ADR_DIR) else []
    if not files:
        return ""
    lines, used = [T("adr_head")], 0
    for name in files:
        text = read_text(f"{ADR_DIR}/{name}") or ""
        ident = re.match(r"(ADR-\d+)", name).group(1)
        title = title_of(f"{ADR_DIR}/{name}")
        title = clean(re.sub(r"^ADR-\d+\s*[—–:.-]*\s*", "", title), 80)
        m = re.search(r"(?im)^\W*(?:status|estado)\W*[:\-]\s*\W*([A-Za-zÁ-úñ]+)", text)
        line = T("adr_line", id=ident, title=title, status=(m.group(1) if m else "?"))
        if used + len(line) > cap:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines) if len(lines) > 1 else ""


def backlog():
    try:
        import gtt_backlog
        return gtt_backlog.parse(gtt_backlog.DEFAULT)
    except Exception:
        return [], []


def counts_text(epics):
    tally = {}
    for e in epics:
        tally[e.get("status") or "?"] = tally.get(e.get("status") or "?", 0) + 1
    return ", ".join(f"{n} {s}" for s, n in sorted(tally.items(), key=lambda kv: -kv[1]))


def epics_block(epics, cap):
    if not epics:
        return ""
    interesting = [e for e in epics if e.get("status") in ("In Progress", "Proposed")]
    lines, used = [T("epics_head")], 0
    listed = 0
    for e in interesting[:contract()["seed"]["epics_listed"]]:
        goal = first_sentence((e.get("fields") or {}).get("Goal", ""), 130)
        line = T("epics_line", id=e["id"], status=e.get("status"), title=clean(re.sub(r"^E\d+\s*·\s*", "", e.get("title", "")), 70), goal=goal or "—")
        if used + len(line) > cap:
            break
        lines.append(line)
        used += len(line) + 1
        listed += 1
    rest = len(epics) - listed
    if rest > 0:
        prefix, served = sonar_base()
        link = f"{prefix}#/view=plan" if prefix else "Sonar"
        lines.append(T("epics_more", n=rest, link=link))
    return "\n".join(lines)


def state_block(epics, stories):
    files = governed_state()
    marker = read_text(FROZEN)
    head = []
    if marker:
        date = (marker.splitlines() or [""])[0][:10]
        head.append(T("state_frozen", date=date, stamp=stamp(files)))
    else:
        head.append(T("state_open", stamp=stamp(files)))
    if epics:
        head.append(T("state_epics", counts=counts_text(epics)))
    if stories:
        done = sum(1 for s in stories if s.get("status") == "Done")
        head.append(T("state_stories", done=done, total=len(stories)))
    return T("state_head") + "\n" + " ".join(head)


# ------------------------------------------------------------------------------------------------------- the open questions

def open_events():
    try:
        import gtt_pending
        c = gtt_pending.contract()
        return [e for e in gtt_pending.events(c) if e["kind"] in ("ASK", "REV") and not e["attended"] and not e["answered"]]
    except Exception:
        return []


def event_ref(ev):
    return f"{ev['kind']}-{int(ev['number']):03d}"


def proposal_context(entry):
    """The few `Key: value` lines of the proposal a review is about: what the person needs to judge it without the repository."""
    if not entry or not os.path.isdir(PROPOSALS):
        return []
    names = [n for n in os.listdir(PROPOSALS) if n.startswith(entry + "-") and n.endswith(".md")]
    if not names:
        return []
    text = read_text(os.path.join(PROPOSALS, sorted(names)[0])) or ""
    cfg = contract()["item"]
    out = []
    for line in text.splitlines()[:80]:
        m = re.match(r"^\s*(?:[-*]\s+)?\**([A-Za-zÁ-úñ][A-Za-zÁ-úñ ]{2,40}?)\**\s*:\s*\**\s*(\S.*)$", line)
        if m and "anonical" not in m.group(1):
            out.append(f"- {clean(m.group(1), 40)}: {clean(m.group(2), cfg['field_chars'])}")
        if len(out) >= cfg["summary_fields"]:
            break
    return out


def item_text(ev):
    ref = event_ref(ev)
    n = int(ev["number"])
    fields = ev.get("fields") or {}
    entry = fields.get("entry") if ev["kind"] == "REV" else None
    title = clean(ev.get("subject") or ev.get("title") or ref, 140)
    body = []
    for line in (ev.get("lines") or [])[1:]:
        if not line.strip():
            continue
        if re.match(r"^\s*(?:Respuesta|Answer)\s*:", line):
            continue
        line = re.sub(r"(sha: [0-9a-f]{12})[0-9a-f]{40,}", r"\1", line)
        body.append(line.rstrip())
    text = "\n".join(body)
    if len(text) > contract()["item"]["body_chars"]:
        text = text[: contract()["item"]["body_chars"]].rsplit("\n", 1)[0] + "\n…"
    parts = [T("item_head", ref=ref, title=title), text]
    ctx = proposal_context(entry)
    if ctx:
        parts += [T("item_context")] + ctx
    link = ref_link(entry or ref)
    if link:
        parts.append(T("item_link", link=link))
    parts.append(T("item_answer", n=n))
    return "\n".join(p for p in parts if p)


# ------------------------------------------------------------------------------------------------------------- the open gaps

class _Sink:
    """gtt_provenance.load_gaps reports problems to a collector; here there is nobody to tell (gtt-check owns that)."""
    def add(self, *args, **kw):
        pass


def open_gaps():
    try:
        import gtt_provenance
        gaps, _ = gtt_provenance.load_gaps(_Sink())
    except Exception:
        return []
    return [g for g in gaps if g["kind"] in ("OPEN", "BLOCKING")]


def design_path(epic_ref, fields):
    """The design document of an Epic: the one its `Design` field names, else the conventional gtt-domain/context/design/<EPIC>.md."""
    named = re.search(r"[\w./-]+\.md", (fields or {}).get("Design") or "")
    for cand in ([named.group(0)] if named else []) + [os.path.join(CONTEXT, "design", f"{epic_ref}.md")]:
        if os.path.isfile(cand):
            return cand
    return None


def gap_design_lines(path, gid, limit, chars):
    """The lines of a design document that cite the gap: the one that declares it open first, then the rest."""
    text = read_text(path) if path else None
    if not text:
        return []
    declared, cited = [], []
    for number, line in enumerate(text.splitlines(), 1):
        if not re.search(rf"\b{re.escape(gid)}\b", line):
            continue
        row = {"where": f"{os.path.basename(path)}:{number}", "path": path, "text": clean(line, chars)}
        if not row["text"]:
            continue
        (declared if re.search(rf"\[VAC[IÍ]O:\s*{re.escape(gid)}\]", line) else cited).append(row)
    return (declared + cited)[:limit]


def gap_context(gap, stories, epics):
    """What the person needs to decide a gap without opening the repository, kept small because a project can have hundreds: the scope the
    register gives it, the lines of the design that cite it and the Stories that cite it. The Epic and the Stories are named, not copied:
    the page already holds them. Deterministic, read only, no tokens."""
    cfg = contract()["gap"]
    gid = gap["id"]
    by_id = {e["id"]: e for e in epics}
    design = []
    for ref in re.findall(r"EPIC-\d+", gap.get("affects") or ""):
        e = by_id.get(ref)
        if e:
            design += gap_design_lines(design_path(ref, e.get("fields")), gid, cfg["design_lines"], cfg["line_chars"])
    cited = [s["id"] for s in stories if re.search(rf"\b{re.escape(gid)}\b", json.dumps(s.get("fields") or {}, ensure_ascii=False))]
    return {"kind": gap["kind"], "topic": clean(gap.get("topic"), 140), "scope": clean(gap.get("scope"), 240) or None, "design": design[: cfg["design_lines"]], "stories": cited[: cfg["stories"]]}


def gap_texts():
    """The words Sonar needs to write the message of a gap for the thread, from the contract (one copy, in the person's language)."""
    table = contract()["texts"][lang()]
    return {k: v for k, v in table.items() if k.startswith("gap_") or k in ("item_head", "item_link")}


def answer_contract(events):
    header = contract()["answers"]["header"]
    example = f"{int(events[0]['number'])}: 1" if events else "13: 1"
    return T("contract_head") + "\n" + T("contract_body", header=header, example=example)


def changes_text():
    rows = changes()
    if not rows:
        return ""
    lines = [T("changes_head")]
    for row in rows[:12]:
        lines.append(T("change_" + row["kind"], title=row["title"], path=row["path"], link=row["link"]).rstrip())
    if len(rows) > 12:
        lines.append(f"- … +{len(rows) - 12}")
    return "\n".join(lines)


def batch(ref=None):
    """(text or None, [refs]) for the open questions, or one of them."""
    events = open_events()
    if ref:
        events = [e for e in events if event_ref(e).lower() == ref.lower() or str(int(e["number"])) == str(ref).lstrip("0")]
    if not events:
        return None, []
    header = contract()["answers"]["header"]
    parts = [T("batch_title", project=project_name(), date=datetime.date.today().isoformat()), T("batch_intro", header=header)]
    ch = changes_text()
    if ch:
        parts.append(ch)
    parts += [item_text(e) for e in events]
    parts.append(answer_contract(events))
    return "\n\n".join(parts), [event_ref(e) for e in events]


# ------------------------------------------------------------------------------------------------------------- the first message

def seed():
    """{text, chars, omitted, desktop_ok}: the first message of the thread. Mandatory: who Claude is here, the state, the open questions and
    how to answer; the summaries come in order of value while they fit the size the link of Claude Desktop can carry."""
    cfg = contract()["seed"]
    stories, epics = backlog()
    events = open_events()
    intro = T("seed_title", project=project_name()) + "\n\n" + T("seed_intro", project=project_name())
    if events:
        questions = T("questions_head") + "\n" + T("questions_count", n=len(events), refs=", ".join(event_ref(e) for e in events))
    else:
        questions = T("questions_head") + "\n" + T("questions_none")
    mandatory = [intro, state_block(epics, stories), questions, answer_contract(events), T("seed_close")]
    budget = cfg["max_chars"] - sum(len(p) + 2 for p in mandatory) - 140
    builders = {}
    for entry in cfg["context_files"]:
        builders[entry["key"]] = (lambda e=entry: doc_block(e["key"], e["file"], cfg["caps"][e["key"]]))
    builders["stack"] = lambda: stack_block(cfg["caps"]["stack"])
    builders["glossary"] = lambda: glossary_block(cfg["caps"]["glossary"])
    builders["adr"] = lambda: adr_block(cfg["caps"]["adr"])
    builders["epics"] = lambda: epics_block(epics, cfg["caps"]["epics"])
    chosen, omitted = {}, []
    for key in cfg["priority"]:
        block = builders[key]() if key in builders else ""
        if not block:
            continue
        if len(block) + 2 <= budget:
            chosen[key] = block
            budget -= len(block) + 2
        else:
            omitted.append(key)
    docs = [chosen[k] for k in ("vision", "architecture", "constraints", "stack", "principles", "glossary") if k in chosen]
    order = [intro, mandatory[1]]
    if docs:
        order.append(T("docs_head") + "\n\n" + "\n\n".join(docs))
    for k in ("adr", "epics"):
        if k in chosen:
            order.append(chosen[k])
    order += [questions, mandatory[3]]
    if omitted:
        names = {"vision": LABELS[lang()]["vision"], "architecture": LABELS[lang()]["architecture"], "constraints": LABELS[lang()]["constraints"],
                 "principles": LABELS[lang()]["principles"], "stack": "stack", "glossary": T("glossary_head").lstrip("# ").strip(), "adr": "ADR", "epics": "Epics"}
        order.append(T("omitted", names=", ".join(names[k] for k in omitted)))
    order.append(T("seed_close"))
    text = "\n\n".join(order)
    return {"text": text, "chars": len(text), "omitted": omitted, "desktop_ok": len(text) <= cfg["desktop_prefill_max_chars"]}


# ----------------------------------------------------------------------------------------------------------- the thread

def thread_url(raw):
    """The clean URL of a Claude web conversation or project, or None. Query and fragment are dropped; the host is claude.ai, only."""
    try:
        parsed = urllib.parse.urlparse(str(raw).strip())
    except ValueError:
        return None
    url = f"https://{parsed.netloc}{parsed.path}" if parsed.scheme == "https" else ""
    return url.rstrip("/") if re.match(contract()["thread_url"]["pattern"], url) else None


def refresh_sonar():
    """The static page is derived: bring it up to date so the top bar shows the thread (best effort, never a failure)."""
    if os.path.isfile(os.path.join(".gtt", "local", "sonar.html")):
        try:
            subprocess.run(["bash", os.path.join(".gtt", "scripts", "gtt-sonar.sh"), "render", "--quiet"], capture_output=True, timeout=90)
        except (OSError, subprocess.SubprocessError):
            pass


def data():
    """What Sonar draws: the thread, the first message, the questions and what changed. Read-only and deterministic: the texts carry no address
    (the person is in Sonar already; the terminal's `seed` and `batch` do carry them when Sonar is open)."""
    global LINKS
    LINKS = False
    try:
        return _data()
    finally:
        LINKS = True


def _data():
    st = state()
    events = open_events()
    items = {}
    for e in events:
        text = item_text(e)
        items[event_ref(e)] = text
        entry = (e.get("fields") or {}).get("entry") if e["kind"] == "REV" else None
        if entry:
            items.setdefault(entry, text)            # the card of the proposal in the Inbox finds its review
    gaps = {}
    stories, epics = backlog()
    for g in open_gaps():
        gaps[g["id"]] = gap_context(g, stories, epics)
    text, refs = batch()
    sd = seed()
    return {"schema": 1, "thread": st.get("thread") or None, "seed": sd["text"], "seed_chars": sd["chars"], "seed_omitted": sd["omitted"], "desktop_ok": sd["desktop_ok"],
            "batch": text, "refs": refs, "items": items, "gaps": gaps, "gap_texts": gap_texts(), "count": len(events), "changes": [{k: v for k, v in c.items() if k != "link"} for c in changes()],
            "new_url": contract()["thread_url"]["new"], "desktop_new": contract()["thread_url"]["desktop_new"],
            "set_command": "bash .gtt/scripts/gtt-consult.sh set <URL>",
            "answer_line": contract()["answers"]["line"], "answer_header": contract()["answers"]["header"]}


# ------------------------------------------------------------------------------------------------------------- the answers

def parse_answers(text):
    cfg = contract()["answers"]
    match = re.search(re.escape(cfg["header"]) + r"\s*:?", text, re.I)
    body = text[match.end():] if match else text
    rows = []
    for raw in body.splitlines():
        m = re.match(cfg["line"], raw)
        if m:
            answer = re.sub(r"\s+", " ", m.group(2)).strip().strip("*_`«»\"")
            if answer:
                rows.append((int(m.group(1)), answer, raw.strip()))
    return rows


def record(ref, answer, raw, apply):
    cmd = ["bash", os.path.join(".gtt", "scripts", "gtt-pending.sh"), "record", ref, answer, "--quote", raw]
    if apply:
        cmd.append("--apply")
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (done.stdout + done.stderr).strip().splitlines()
    return done.returncode == 0, (out[0] if out else "")


# -------------------------------------------------------------------------------------------------------------- commands

def cmd_status(args):
    st = state()
    thread = st.get("thread") or {}
    events = open_events()
    rows = changes()
    sd = seed()
    if args.json:
        print(json.dumps({"schema": 1, "thread": thread or None, "open": [event_ref(e) for e in events], "changes": len(rows), "seed_chars": sd["chars"]}, indent=2, ensure_ascii=False))
        return 0
    print(T("status_thread", url=thread["url"], at=thread.get("set_at", "?")) if thread.get("url") else T("status_no_thread"))
    print(T("status_questions", n=len(events)))
    if rows:
        print(T("status_changes", n=len(rows)))
    print(T("status_seed", chars=sd["chars"]))
    if sonar_base()[0] is None:
        print(T("sonar_note"))
    return 0


def cmd_seed(args):
    sd = seed()
    if args.json:
        print(json.dumps(sd, indent=2, ensure_ascii=False))
    else:
        print(sd["text"])
    return 0


def cmd_batch(args):
    text, refs = batch(args.ref)
    if args.json:
        print(json.dumps({"schema": 1, "text": text, "refs": refs}, indent=2, ensure_ascii=False))
    else:
        print(text if text else T("questions_none"))
    return 0


def cmd_set(args):
    url = thread_url(args.url)
    if not url:
        print(T("set_bad"), file=sys.stderr)
        return 1
    st = state()
    st["thread"] = {"url": url, "set_at": now_iso()}
    write_json(state_path(), st)
    remember(st["thread"])                       # once and for good: the person's register keeps it for every copy of this project
    mark_seen()                                  # the thread was just seeded with today's design
    refresh_sonar()
    print(T("set_ok"))
    return 0


def cmd_clear(args):
    st = state()
    st.pop("thread", None)
    write_json(state_path(), st)
    forget()                                     # the one act that makes GTT forget the thread, here and in the person's register
    refresh_sonar()
    print(T("clear_ok"))
    return 0


def cmd_seen(args):
    mark_seen()
    refresh_sonar()
    print(T("seen_ok"))
    return 0


def cmd_answers(args):
    text = args.text if args.text is not None else sys.stdin.read()
    if "\n" not in text:
        text = text.replace("\\n", "\n")          # an operation argument cannot carry a line break (the contract refuses control characters): the CLI sends them as `\n`
    rows = parse_answers(text)
    if not rows:
        print(T("answers_none", header=contract()["answers"]["header"]), file=sys.stderr)
        return 1
    by_number = {int(e["number"]): e for e in open_events()}
    failed, recorded = 0, 0
    import gtt_pending
    pending_contract = gtt_pending.contract()
    for number, answer, raw in rows:
        ev = by_number.get(number)
        if not ev:
            print(T("answers_line_bad", n=number, answer=answer, why="no open question with that number"))
            failed += 1
            continue
        if not args.apply:
            # A dry run needs no quote: it says whether the answer is valid for that question and gives the person their own command.
            cleaned, error = gtt_pending.clean_answer(answer, ev, pending_contract)
            if error:
                print(T("answers_line_bad", n=number, answer=answer, why=error))
                failed += 1
            else:
                print(T("answers_would", n=number, answer=cleaned))
            continue
        ok, result = record(event_ref(ev), answer, raw, args.apply)
        print(T("answers_line_ok" if ok else "answers_line_bad", n=number, answer=answer, result=result, why=result))
        failed += 0 if ok else 1
        recorded += 1 if ok else 0
    if not args.apply:
        print(T("answers_dry"))
    elif recorded:
        mark_seen()
        refresh_sonar()
    return 1 if failed else 0


def main(argv):
    parser = argparse.ArgumentParser(prog="gtt-consult.sh", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_status)
    p = sub.add_parser("seed"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_seed)
    p = sub.add_parser("batch"); p.add_argument("ref", nargs="?"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_batch)
    p = sub.add_parser("set"); p.add_argument("url"); p.add_argument("--apply", action="store_true", help="accepted for the operations contract; set always writes"); p.set_defaults(func=cmd_set)
    p = sub.add_parser("clear"); p.add_argument("--apply", action="store_true", help="accepted for the operations contract"); p.set_defaults(func=cmd_clear)
    p = sub.add_parser("seen"); p.add_argument("--apply", action="store_true", help="accepted for the operations contract"); p.set_defaults(func=cmd_seen)
    p = sub.add_parser("answers"); p.add_argument("--text"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_answers)
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
