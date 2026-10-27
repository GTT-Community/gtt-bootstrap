#!/usr/bin/env python3
"""GTT - Method Governance (engine): the development method is declared, ratified and verified.

    .gtt/methods/<id>.md           Method Packs - the single source of each method's texts, template and rules
    .gtt/contract/methods.json     the two questions of the setup questionnaire and the format of the Method Lock
    .gtt/development-method.json   the setup answer (state, never authority) - written only by `select`
    gtt-domain/context/architecture.md  the Method Lock: block `gtt-method` under `## Architectural style` (governed)
    gtt-domain/context/stack.md    the row `Development method` (section 1) and the method's rules (section 5)

  gtt_method.py catalog [--json]                       the packs are well formed (part of gtt-validate.sh)
  gtt_method.py list [--question Q] [--lang L] [--json] the questionnaire: questions and options, texts from the packs
  gtt_method.py show ID [--json]                       one pack
  gtt_method.py select [--style IDS|help] [--start ID|direct|help] [--by NAME] [--apply]
                                                       record the setup answer; refused after the freeze
  gtt_method.py get [--json]                           the setup answer, the Method Lock and what is in force
  gtt_method.py lock [--json]                          the Method Lock as data
  gtt_method.py check [--pre-freeze] [--json]          the lock, the map, the backlog and the designs follow the method
  gtt_method.py rules [--json]                         the neutral rules of the ratified method and their rows in stack.md

Everything is computed from files, never judged. Nothing here corrects code or context: a violation is reported.
`select` is a dry run without --apply. There is deliberately no command that changes a ratified method.
Exit 0 = ok (warnings allowed), 1 = violation or refused, 2 = cannot run.
"""

import argparse
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

CONTRACT = ".gtt/contract/methods.json"
PACKS_DIR = ".gtt/methods"
STATE = ".gtt/development-method.json"
ARCH = "gtt-domain/context/architecture.md"
STACK = "gtt-domain/context/stack.md"
BACKLOG = "gtt-domain/backlog.md"
ADR_DIR = "gtt-domain/adr"
FROZEN = "gtt-domain/.frozen"
KINDS = ("architecture-style", "decomposition-strategy")
LEVELS = ("verified", "partial", "declared-only")           # strongest first
QUESTIONS = ("development", "start")
FRONT_KEYS = ("id", "name", "kind", "question", "recommended", "requires_adr", "compatible_with", "incompatible_with",
              "verification")
SECTIONS = ("Qué es", "Conviene si", "What it is", "Fits when", "Qué descarta", "Efecto en el diseño",
            "Plantilla de diseño por Epic", "Verificación")
TEXTS = {"es": ("Qué es", "Conviene si"), "en": ("What it is", "Fits when")}
CHECK_KEYS = ("epic-forbidden-kind", "epic-forbidden-title", "epic-required-fields", "first-epic-kind",
              "first-epic-design-fields", "design-fields", "design-unit", "design-unit-fields")
LOCK_KEYS = ("style", "start", "status", "locked_by", "verification", "gap")
APPROVED = ("Planned", "In Progress", "Completed")
OPEN = "OPEN"
DIRECT = "direct"
STACK_ROW = "Development method"
CANON = "> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md"


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read().replace("\r\n", "\n")
    except OSError:
        return None


def emit(obj):
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def die(message, code=2):
    print(f"gtt-method: {message}", file=sys.stderr)
    sys.exit(code)


def frozen():
    return os.path.isfile(FROZEN)


def now():
    return os.environ.get("GTT_NOW") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ids(value):
    """`a, b` or `[a, b]` -> ['a', 'b']."""
    return [v.strip() for v in str(value or "").strip().strip("[]").split(",") if v.strip()]


def fenced(text, name):
    """[(line, raw)] of the non-blank, non-comment lines of every ```<name> block."""
    out, inside = [], False
    for number, line in enumerate((text or "").split("\n"), 1):
        if not inside:
            inside = re.match(r"^```%s\s*$" % re.escape(name), line) is not None
        elif line.startswith("```"):
            inside = False
        elif line.strip() and not line.lstrip().startswith("#"):
            out.append((number, line.rstrip()))
    return out


def fenced_raw(text, name):
    """The full text of the first ```<name> block, or None."""
    found = re.search(r"^```%s[ \t]*\n(.*?)^```" % re.escape(name), text or "", re.M | re.S)
    return found.group(1) if found else None


# ------------------------------------------------------------------------------------------ packs

def contract():
    try:
        return json.loads(read(CONTRACT) or "")
    except ValueError:
        die(f"{CONTRACT} is missing or not valid JSON")


def h2_sections(text):
    """{heading: body} for every `## ` heading outside fenced blocks."""
    out, current, fence = {}, None, False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
        head = None if fence else re.match(r"^##\s+(.+?)\s*$", line)
        if head:
            current = head.group(1)
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def paragraph(body):
    return " ".join(line.strip() for line in (body or "").split("\n") if line.strip())


def parse_pack(path):
    text = read(path) or ""
    meta, problems = {}, []
    front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not front:
        problems.append("no YAML frontmatter (--- ... ---) at the top")
    else:
        for raw in front.group(1).split("\n"):
            line = raw.split(" #", 1)[0].rstrip()
            if not line.strip():
                continue
            found = re.match(r"^([a-z_]+):\s*(.*)$", line)
            if not found:
                problems.append(f"frontmatter line is not `key: value`: {raw.strip()}")
                continue
            key, value = found.group(1), found.group(2).strip()
            if key in meta:
                problems.append(f"frontmatter key `{key}` is given twice")
            if key in ("compatible_with", "incompatible_with"):
                meta[key] = ids(value)
            elif key in ("recommended", "requires_adr"):
                meta[key] = {"true": True, "false": False}.get(value.lower(), value)
            else:
                meta[key] = value
    sections = h2_sections(text[front.end():] if front else text)
    rules = []
    for number, raw in fenced(text, "gtt-method-rules"):
        cells = [c.strip() for c in raw.split("|")]
        rules.append({"line": number, "raw": raw, "cells": cells})
    checks = {}
    for number, raw in fenced(text, "gtt-method-checks"):
        found = re.match(r"^([a-z-]+)\s*:\s*(.*)$", raw.strip())
        if found:
            checks[found.group(1)] = [v.strip() for v in found.group(2).split(",") if v.strip()]
        else:
            problems.append(f"gtt-method-checks line {number} is not `key: value`")
    return {"path": path.replace("\\", "/"), "meta": meta, "sections": sections, "rules": rules, "checks": checks,
            "template": fenced_raw(text, "gtt-epic-template"), "has_rules_block": fenced_raw(text, "gtt-method-rules") is not None,
            "has_checks_block": fenced_raw(text, "gtt-method-checks") is not None, "problems": problems, "text": text}


def packs():
    out = {}
    for path in sorted(glob.glob(os.path.join(PACKS_DIR, "*.md"))):
        if os.path.basename(path).lower() == "readme.md":
            continue
        pack = parse_pack(path)
        out[pack["meta"].get("id") or os.path.basename(path)[:-3]] = pack
    return out


def rule_of(pack, row):
    cells = row["cells"]
    if len(cells) != 5:
        return None
    check = cells[4]
    return {"id": cells[0], "from": cells[1], "must_not_depend_on": cells[2], "may_depend_on": cells[3],
            "check": "dependency" if check == "dependency" else "audit" if check.startswith("audit") else check,
            "audit": check.split(":", 1)[1].strip() if check.startswith("audit:") else None, "pack": pack["meta"].get("id")}


def pack_rules(pack):
    return [r for r in (rule_of(pack, row) for row in pack["rules"]) if r]


def catalog_problems(all_packs=None):
    """[(level, where, message)] - the packs are well formed and agree with each other and with the contract."""
    all_packs = packs() if all_packs is None else all_packs
    found = []
    add = lambda level, where, message: found.append((level, where, message))
    spec = contract()
    if spec.get("schema") != 1 or not isinstance(spec.get("contract_version"), int):
        add("FAIL", CONTRACT, "needs schema 1 and an integer contract_version")
    if [q.get("id") for q in spec.get("questions", [])] != list(QUESTIONS):
        add("FAIL", CONTRACT, "questions must be `development` then `start`")
    if not all_packs:
        add("FAIL", PACKS_DIR, "no Method Pack found")
    rule_ids = {}
    for pid, pack in sorted(all_packs.items()):
        where, meta = pack["path"], pack["meta"]
        for problem in pack["problems"]:
            add("FAIL", where, problem)
        for key in FRONT_KEYS:
            if key not in meta or meta[key] in ("", None):
                add("FAIL", where, f"frontmatter lacks `{key}`")
        if meta.get("id") and os.path.basename(where)[:-3] != meta["id"]:
            add("FAIL", where, f"id `{meta['id']}` differs from the file name")
        if meta.get("kind") not in KINDS:
            add("FAIL", where, f"kind must be one of {', '.join(KINDS)}")
        if meta.get("question") not in QUESTIONS:
            add("FAIL", where, f"question must be one of {', '.join(QUESTIONS)}")
        if meta.get("verification") not in LEVELS:
            add("FAIL", where, f"verification must be one of {', '.join(LEVELS)}")
        for key in ("recommended", "requires_adr"):
            if not isinstance(meta.get(key), bool):
                add("FAIL", where, f"`{key}` must be true or false")
        if meta.get("kind") == "architecture-style" and meta.get("requires_adr") is not True:
            add("FAIL", where, "an architecture-style is locked by an ADR: requires_adr must be true")
        if meta.get("kind") == "decomposition-strategy" and meta.get("requires_adr") is not False:
            add("FAIL", where, "a decomposition-strategy is a light control without ADR: requires_adr must be false")
        for key in ("compatible_with", "incompatible_with"):
            for other in meta.get(key, []) if isinstance(meta.get(key), list) else []:
                if other == pid:
                    add("FAIL", where, f"{key} names the pack itself")
                elif other not in all_packs:
                    add("FAIL", where, f"{key} names `{other}`, which is not a pack")
        both = set(meta.get("compatible_with") or []) & set(meta.get("incompatible_with") or [])
        if both:
            add("FAIL", where, f"{', '.join(sorted(both))} is both compatible and incompatible")
        for other in meta.get("incompatible_with") or []:
            if other in all_packs and pid not in (all_packs[other]["meta"].get("incompatible_with") or []):
                add("FAIL", where, f"incompatible_with is not symmetric: `{other}` does not list `{pid}`")
        for title in SECTIONS:
            if not paragraph(pack["sections"].get(title)):
                add("FAIL", where, f"section `## {title}` is missing or empty")
        lines = lambda title: len([l for l in (pack["sections"].get(title) or "").split("\n") if l.strip()])
        for title in ("Qué es", "What it is"):
            if lines(title) > 4:
                add("WARN", where, f"`## {title}` has {lines(title)} lines: it is the short text of the questionnaire (2-3 lines)")
        for title in ("Conviene si", "Fits when"):
            if lines(title) > 1:
                add("WARN", where, f"`## {title}` has {lines(title)} lines: it is one line")
        if not paragraph(pack["sections"].get("Qué descarta")):
            add("FAIL", where, "a method that discards nothing has not earned its place: `## Qué descarta` is required")
        if not (pack["template"] or "").strip():
            add("FAIL", where, "`## Plantilla de diseño por Epic` has no ```gtt-epic-template block")
        if not pack["has_rules_block"]:
            add("FAIL", where, "`## Verificación` has no ```gtt-method-rules block")
        if not pack["has_checks_block"]:
            add("FAIL", where, "`## Verificación` has no ```gtt-method-checks block")
        for row in pack["rules"]:
            rule = rule_of(pack, row)
            if rule is None:
                add("FAIL", f"{where}:{row['line']}", "a rule is `ID | FROM | MUST NOT DEPEND ON | MAY DEPEND ON | CHECK`")
                continue
            if rule["check"] not in ("dependency", "audit"):
                add("FAIL", f"{where}:{row['line']}", f"{rule['id']}: CHECK must be `dependency` or `audit: <what a human judges>`")
            if rule["id"] in rule_ids:
                add("FAIL", f"{where}:{row['line']}", f"rule id {rule['id']} is also used by {rule_ids[rule['id']]}")
            rule_ids[rule["id"]] = pid
            if rule["check"] == "dependency" and (rule["must_not_depend_on"] in ("", "-")):
                add("FAIL", f"{where}:{row['line']}", f"{rule['id']}: a dependency rule names what must not be depended on")
        for key in pack["checks"]:
            if key not in CHECK_KEYS:
                add("FAIL", where, f"gtt-method-checks: unknown key `{key}` (known: {', '.join(CHECK_KEYS)})")
        if ("design-unit" in pack["checks"]) != ("design-unit-fields" in pack["checks"]):
            add("FAIL", where, "gtt-method-checks: design-unit and design-unit-fields go together")
        if CANON not in pack["text"]:
            add("FAIL", where, "the canonical reference line is missing")
    for question in QUESTIONS:
        if not any(p["meta"].get("question") == question for p in all_packs.values()):
            add("FAIL", PACKS_DIR, f"no pack answers the `{question}` question")
    return found


# --------------------------------------------------------------------------- the questionnaire

def option(pack, lang):
    meta = pack["meta"]
    texts = {code: {"what_it_is": paragraph(pack["sections"].get(a)), "fits_when": paragraph(pack["sections"].get(b))}
             for code, (a, b) in TEXTS.items()}
    out = {"id": meta.get("id"), "name": meta.get("name"), "kind": meta.get("kind"), "recommended": meta.get("recommended") is True,
           "requires_adr": meta.get("requires_adr") is True, "verification": meta.get("verification"),
           "compatible_with": meta.get("compatible_with") or [], "incompatible_with": meta.get("incompatible_with") or [],
           "source": pack["path"]}
    if lang:
        out.update(texts.get(lang, texts["en"]))
    else:
        out["texts"] = texts
    return out


def cmd_list(args):
    spec, all_packs = contract(), packs()
    pick = lambda value: value.get(args.lang, value.get("en")) if args.lang and isinstance(value, dict) else value
    questions = []
    for question in spec["questions"]:
        if args.question and question["id"] != args.question:
            continue
        options = [option(p, args.lang) for _, p in sorted(all_packs.items(), key=lambda kv: (not kv[1]["meta"].get("recommended"), kv[0]))
                   if p["meta"].get("question") == question["id"]]
        extra = [{"id": e["id"], "records": e["records"], "label": pick(e["label"]), "summary": pick(e["summary"])}
                 for e in question.get("extra_options", [])]
        questions.append({"id": question["id"], "order": question["order"], "multiple": question["multiple"],
                          "prompt": pick(question["prompt"]), "options": options, "extra_options": extra,
                          "lock_key": question["lock_key"]})
    out = {"schema": 1, "kind": "gtt-method-catalog", "contract_version": spec["contract_version"], "lang": args.lang,
           "questions": questions, "selection": spec["selection"], "frozen": frozen(),
           "rule": "texts come from the Method Packs; the recommended packs are marked, never applied in silence"}
    if args.json:
        emit(out)
        return 0
    lang = args.lang or "es"
    for q in questions:
        prompt = q["prompt"][lang] if isinstance(q["prompt"], dict) else q["prompt"]
        print(f"{q['order']}. {prompt}" + ("  (puedes combinar)" if q["multiple"] and lang == "es" else "  (several may be combined)" if q["multiple"] else ""))
        for o in q["options"]:
            texts = o.get("texts", {}).get(lang) or o
            mark = (" (recomendado)" if lang == "es" else " (recommended)") if o["recommended"] else ""
            print(f"   - {o['name']}{mark} [{o['id']}]: {texts['what_it_is']}")
            print(f"       {'Conviene si' if lang == 'es' else 'Fits when'}: {texts['fits_when']}")
        for e in q["extra_options"]:
            label = e["label"][lang] if isinstance(e["label"], dict) else e["label"]
            print(f"   - {label} [{e['id']}]")
    return 0


def cmd_show(args):
    pack = packs().get(args.id)
    if pack is None:
        die(f"`{args.id}` is not a Method Pack (bash .gtt/scripts/gtt-method.sh list)", 1)
    if args.json:
        emit({"schema": 1, "kind": "gtt-method-pack", "pack": option(pack, None),
              "sections": {k: v.strip() for k, v in pack["sections"].items()}, "epic_template": pack["template"],
              "rules": pack_rules(pack), "checks": pack["checks"]})
    else:
        print(pack["text"])
    return 0


# --------------------------------------------------------------------------- the setup answer

def selection():
    text = read(STATE)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        die(f"{STATE} is not valid JSON")
    return data


def pairs(chosen, all_packs):
    """(incompatible pairs, pairs not declared compatible)."""
    bad, undeclared = [], []
    for i, a in enumerate(chosen):
        for b in chosen[i + 1:]:
            ma, mb = all_packs[a]["meta"], all_packs[b]["meta"]
            if b in (ma.get("incompatible_with") or []) or a in (mb.get("incompatible_with") or []):
                bad.append((a, b))
            elif b not in (ma.get("compatible_with") or []) and a not in (mb.get("compatible_with") or []):
                undeclared.append((a, b))
    return bad, undeclared


def validate_choice(style, start, all_packs):
    """[problems] for style (list or OPEN) and start (id, direct or OPEN)."""
    problems = []
    if style != OPEN and not style:
        problems.append("style names no pack (`help` leaves it OPEN)")
    if style != OPEN:
        for pid in style:
            if pid not in all_packs:
                problems.append(f"style `{pid}` is not a Method Pack")
            elif all_packs[pid]["meta"].get("question") != "development":
                problems.append(f"`{pid}` answers the `{all_packs[pid]['meta'].get('question')}` question, not `development`")
        if len(set(style)) != len(style):
            problems.append("a style is named twice")
    if start not in (OPEN, DIRECT):
        if start not in all_packs:
            problems.append(f"start `{start}` is not a Method Pack (or `direct`, or `help`)")
        elif all_packs[start]["meta"].get("question") != "start":
            problems.append(f"`{start}` answers the `{all_packs[start]['meta'].get('question')}` question, not `start`")
    return problems


def cmd_select(args):
    if frozen():
        print("gtt-method: REFUSED - the project is frozen. The development method was ratified with the design; changing it "
              "is a change request with an impact analysis (gtt-domain/change-request.md -> gtt-propose-change), never a new "
              "questionnaire. Nothing was written.", file=sys.stderr)
        return 1
    if args.style is None and args.start is None:
        die("give --style and/or --start (`help` leaves it OPEN for THINK to propose)")
    all_packs, previous = packs(), selection() or {}
    style = previous.get("style", OPEN)
    start = previous.get("start", OPEN)
    helped = dict(previous.get("help") or {})
    if args.style is not None:
        style = OPEN if args.style.strip().lower() == "help" else ids(args.style)
        helped["style"] = style == OPEN
    if args.start is not None:
        start = OPEN if args.start.strip().lower() == "help" else args.start.strip()
        helped["start"] = start == OPEN
    problems = validate_choice(style, start, all_packs)
    if problems:
        for problem in problems:
            print(f"gtt-method: REFUSED - {problem}. Nothing was written.", file=sys.stderr)
        return 1
    if style != OPEN:
        bad, undeclared = pairs(style + ([start] if start not in (OPEN, DIRECT) else []), all_packs)
        if bad:
            for a, b in bad:
                print(f"gtt-method: REFUSED - `{a}` and `{b}` are incompatible (their Method Packs say so). Choose another "
                      "combination. Nothing was written.", file=sys.stderr)
            return 1
        for a, b in undeclared:
            print(f"gtt-method: NOTE - `{a}` with `{b}` is not declared compatible by either pack: confirm the combination is intended.")
    shown = lambda value: OPEN if value == OPEN else ", ".join(value) if isinstance(value, list) else value
    print(f"development method (setup answer): style {shown(style)}; start {shown(start)}")
    if OPEN in (style, start):
        print("  OPEN: nothing is chosen. During THINK the agent proposes a method as [PROPUESTA] with its reason and the "
              "human confirms; unconfirmed, it stays OPEN. No default is applied.")
    print(f"  a setup answer, never governed context: it reaches {ARCH} as the Method Lock with the human's "
          "confirmation, and the freeze ratifies it.")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    data = {"schema": 1, "style": style, "start": start, "help": helped, "answered_by": args.by or previous.get("answered_by") or "unspecified",
            "answered_at": now(), "authority": "none - a setup answer; governed only as the Method Lock, ratified by the freeze"}
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"gtt-method: written {STATE}")
    return 0


# --------------------------------------------------------------------------- the Method Lock

def section_of(text, heading):
    found = re.search(r"^##\s+%s\s*\n(.*?)(?=^##\s|\Z)" % re.escape(heading), text or "", re.M | re.S)
    return found.group(1) if found else None


def lock():
    """The Method Lock as data. `present` is False when architecture.md has no `gtt-method` block or an empty one."""
    text = read(ARCH)
    out = {"file": ARCH, "present": False, "values": {}, "lines": {}, "problems": [], "in_section": False}
    if text is None:
        return out
    rows = fenced(text, "gtt-method")
    if not rows:
        return out
    out["present"] = True
    section = section_of(text, "Architectural style") or ""
    out["in_section"] = "```gtt-method" in section
    for number, raw in rows:
        found = re.match(r"^\s*([a-z_]+)\s*:\s*(.*?)\s*$", raw)
        if not found:
            out["problems"].append((number, f"`{raw.strip()}` is not `key: value`"))
            continue
        key, value = found.group(1), found.group(2)
        if key not in LOCK_KEYS:
            out["problems"].append((number, f"unknown key `{key}` (known: {', '.join(LOCK_KEYS)})"))
            continue
        if key in out["values"]:
            out["problems"].append((number, f"`{key}` is given twice"))
        out["values"][key] = value
        out["lines"][key] = number
    return out


def lock_view(state=None):
    state = state or lock()
    values = state["values"]
    style, start = values.get("style", ""), values.get("start")
    return {"present": state["present"], "file": state["file"],
            "style": OPEN if style.strip().upper() == OPEN else ids(style),
            "start": OPEN if (start or "").strip().upper() == OPEN else start,
            "status": values.get("status"), "locked_by": values.get("locked_by"), "verification": values.get("verification"),
            "gap": values.get("gap")}


def weakest(levels):
    known = [l for l in levels if l in LEVELS]
    return max(known, key=LEVELS.index) if known else None


def chosen_packs(view):
    style = [] if view["style"] == OPEN else list(view["style"])
    return style + ([view["start"]] if view["start"] not in (None, OPEN, DIRECT) else [])


def in_force():
    """What applies now: the Method Lock when present, else the setup answer, else nothing (OPEN)."""
    view = lock_view()
    if view["present"]:
        return {"source": "lock", "status": view["status"], "style": view["style"], "start": view["start"],
                "packs": chosen_packs(view) if view["status"] == "ratified" else []}
    sel = selection()
    if sel:
        style, start = sel.get("style", OPEN), sel.get("start", OPEN)
        decided = OPEN not in (style, start)
        return {"source": "setup", "status": "selected" if decided else "open", "style": style, "start": start,
                "packs": ([] if style == OPEN else list(style)) + ([start] if start not in (OPEN, DIRECT) else []) if decided else []}
    return {"source": "none", "status": "not declared", "style": OPEN, "start": OPEN, "packs": []}


# --------------------------------------------------------------------------- stack.md

def table(section_text):
    """[(line offset, cells)] of a Markdown table, header included, separators out."""
    out = []
    for offset, line in enumerate((section_text or "").split("\n")):
        if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|?\s*$", line):
            out.append((offset, [c.strip() for c in line.strip().strip("|").split("|")]))
    return out


def stack_row():
    text = read(STACK) or ""
    for _, cells in table(section_of(text, "1. Stack at a glance")):
        if cells and cells[0].strip().lower() == STACK_ROW.lower():
            return {"technology": cells[1] if len(cells) > 1 else "", "locked_by": cells[3] if len(cells) > 3 else ""}
    return None


def dependency_rows():
    """Rows of stack.md section 5: [{module, may, must_not, rule}]; `rule` is '' when the table has no Rule column."""
    rows = table(section_of(read(STACK) or "", "5. Dependency rules"))
    if not rows:
        return [], False
    header = [c.lower() for c in rows[0][1]]
    index = {name: header.index(name) if name in header else None for name in ("module", "may depend on", "must not depend on", "rule")}
    out = []
    for _, cells in rows[1:]:
        get = lambda name: cells[index[name]] if index[name] is not None and index[name] < len(cells) else ""
        if any(c for c in cells):
            out.append({"module": get("module"), "may_depend_on": get("may depend on"), "must_not_depend_on": get("must not depend on"),
                        "rule": get("rule")})
    return out, index["rule"] is not None


def change_log_rows():
    return [cells for _, cells in table(section_of(read(STACK) or "", "6. Map change log"))[1:]]


def open_gaps():
    try:
        import gtt_provenance as gp
        gaps, _ = gp.load_gaps(gp.Findings())
    except Exception:
        return []
    return gaps


# --------------------------------------------------------------------------- backlog and designs

def epics():
    try:
        import gtt_backlog
        if not os.path.isfile(BACKLOG):
            return []
        _, found = gtt_backlog.parse(BACKLOG)
    except Exception:
        return []
    lines = (read(BACKLOG) or "").split("\n")
    for epic in found:
        epic["title"] = re.sub(r"^#+\s*EPIC-\d+\s*[-—–:]*\s*", "", lines[epic["line"] - 1]).strip()
        epic["number"] = int(epic["id"].split("-")[1])
    return sorted(found, key=lambda e: e["number"])


def first_epic(all_epics):
    live = [e for e in all_epics if e["status"] != "Cancelled"]
    return live[0] if live else None


def design_of(epic):
    try:
        import gtt_design
        return gtt_design.parse_design(gtt_design.epic_design(epic))
    except Exception:
        return None


def has_field(text, field, bullet=False):
    """`**Field:** content` (or `- **Field:** content`) with something after the colon."""
    pattern = (r"^\s*[-*]\s+" if bullet else r"^\s*(?:[-*]\s+)?") + r"\*\*%s:\*\*[ \t]*(\S.*)$" % re.escape(field)
    return re.search(pattern, text or "", re.M) is not None


def units(section_text, prefix):
    """{'S-1': text} of the `### S-n` subsections of a design's section 1."""
    out, current = {}, None
    for line in (section_text or "").split("\n"):
        head = re.match(r"^###\s+(%s-\d+)\b" % re.escape(prefix), line)
        if head:
            current = head.group(1)
            out[current] = ""
        elif re.match(r"^#{1,3}\s", line):
            current = None
        elif current:
            out[current] += line + "\n"
    return out


def starts_with_term(title, terms):
    plain = re.sub(r"[\"'`*_]", "", title).strip().lower()
    for term in terms:
        if re.match(r"^%s(?![\w])" % re.escape(term.lower()), plain):
            return term
    return None


def method_findings(chosen, all_packs, prefreeze, is_frozen):
    """Backlog and design findings of the chosen packs."""
    found = []
    all_epics = epics()
    first = first_epic(all_epics)
    for pid in chosen:
        pack = all_packs[pid]
        checks = pack["checks"]
        name = pack["meta"].get("name", pid)
        for epic in all_epics:
            if epic["status"] == "Cancelled":
                continue
            approved = epic["status"] in APPROVED
            level = "FAIL" if prefreeze or (is_frozen and approved) else "WARN"
            kind = epic["fields"].get("Kind", "").strip().lower()
            for forbidden in checks.get("epic-forbidden-kind", []):
                if kind == forbidden.lower():
                    found.append((level, BACKLOG, f"{epic['id']} is marked `Kind: {forbidden}`: with {name} an Epic is never a "
                                                  "technical layer - cut it into end-to-end results"))
            term = starts_with_term(epic["title"], checks.get("epic-forbidden-title", []))
            if term:
                found.append((level, BACKLOG, f"{epic['id']} — \"{epic['title']}\" is titled as a technical layer (`{term}`): with "
                                              f"{name} the backlog has no horizontal Epics"))
            if approved:
                for field in checks.get("epic-required-fields", []):
                    if not epic["fields"].get(field, "").strip():
                        found.append(("FAIL" if prefreeze or is_frozen else "WARN", BACKLOG,
                                      f"{epic['id']} is approved and has no `**{field}:**` ({name})"))
        wanted = checks.get("first-epic-kind", [])
        if wanted:
            if first is None:
                found.append(("NOTE", BACKLOG, f"no Epic yet: {name} makes the first Epic `Kind: {wanted[0]}`"))
            elif first["fields"].get("Kind", "").strip().lower() != wanted[0].lower():
                found.append(("FAIL" if prefreeze or is_frozen else "WARN", BACKLOG,
                              f"the first Epic, {first['id']}, is not marked `**Kind:** {wanted[0]}`: with {name} the first Epic is the "
                              "skeleton that crosses the whole stack"))
        for epic in all_epics:
            if epic["status"] == "Cancelled":
                continue
            design = design_of(epic)
            if design is None:
                continue
            approved = design["status"] == "Approved"
            level = "FAIL" if approved and (prefreeze or is_frozen) else "WARN"
            suffix = "" if approved else " (draft)"
            section = design["sections"].get(1, "")
            fields = list(checks.get("design-fields", []))
            if first is not None and epic["id"] == first["id"]:
                fields += checks.get("first-epic-design-fields", [])
            for field in fields:
                if not has_field(section, field):
                    found.append((level, design["path"], f"section 1 lacks `**{field}:**` with content ({name}){suffix}"))
            prefix = (checks.get("design-unit") or [None])[0]
            if prefix:
                parts = units(section, prefix)
                if not parts:
                    found.append((level, design["path"], f"section 1 has no `### {prefix}-n` subsection: with {name} the design is "
                                                         f"cut into units ({prefix}-1, {prefix}-2, ...){suffix}"))
                for unit, body in sorted(parts.items(), key=lambda kv: int(kv[0].split("-")[1])):
                    for field in checks.get("design-unit-fields", []):
                        if not has_field(body, field, bullet=True):
                            found.append((level, design["path"], f"{unit} lacks `- **{field}:**` with content ({name}){suffix}"))
    return found


# --------------------------------------------------------------------------- check

def check_all(prefreeze=False):
    """([(level, where, message)], summary)."""
    found = []
    add = lambda level, where, message: found.append((level, where, message))
    all_packs = packs()
    for level, where, message in catalog_problems(all_packs):
        if level == "FAIL":
            add("FAIL", where, f"Method Pack catalog: {message}")
    is_frozen = frozen()
    strict = "FAIL" if prefreeze or is_frozen else "WARN"
    state, sel = lock(), selection()
    view = lock_view(state)
    summary = {"declared": state["present"] or bool(sel), "lock": view, "selection": sel, "frozen": is_frozen}
    if sel is not None:
        problems = validate_choice(sel.get("style", OPEN), sel.get("start", OPEN), all_packs)
        for problem in problems:
            add(strict, STATE, f"setup answer: {problem}")
    if not state["present"]:
        if sel is not None:
            add(strict, ARCH, "a development method was answered at setup (" + STATE + ") and architecture.md has no Method Lock: "
                "write the `gtt-method` block under `## Architectural style` (OPEN is a valid value; nothing is applied in silence)")
            # While the bootstrap is still writing the context, the setup answer already shapes the backlog and the designs.
            force = in_force()
            known = [pid for pid in force["packs"] if pid in all_packs]
            found.extend(method_findings(known, all_packs, prefreeze, is_frozen))
            summary["checked_packs"] = known
            summary["source"] = "setup"
        else:
            add("NOTE", ARCH, "no development method declared (no `gtt-method` block, no setup answer): nothing to check")
        return found, summary
    for number, problem in state["problems"]:
        add(strict, f"{ARCH}:{number}", f"Method Lock: {problem}")
    if not state["in_section"]:
        add("WARN", ARCH, "the `gtt-method` block is not under `## Architectural style`")
    for key in ("style", "start", "status", "locked_by", "verification"):
        if not state["values"].get(key, "").strip():
            add(strict, ARCH, f"Method Lock: `{key}` is missing")
    style, start, status = view["style"], (view["start"] or "").strip(), (view["status"] or "").strip()
    for problem in validate_choice(style, start or OPEN, all_packs):
        add(strict, ARCH, f"Method Lock: {problem}")
    is_open = style == OPEN or start == OPEN
    if status not in ("ratified", "open"):
        add(strict, ARCH, f"Method Lock: status `{status}` must be `ratified` or `open`")
    elif is_open and status != "open":
        add(strict, ARCH, "Method Lock: style or start is OPEN, so status must be `open`")
    elif not is_open and status == "open":
        add(strict, ARCH, "Method Lock: status is `open` but style and start are decided - write `ratified`, or OPEN where undecided")
    row = stack_row()
    locked_by = (view["locked_by"] or "").strip()
    if is_open:
        if locked_by.upper() != OPEN:
            add(strict, ARCH, "Method Lock: an open method is `locked_by: OPEN` - nothing locks it yet")
        gap = (view["gap"] or "").strip()
        gaps = {g["id"]: g for g in open_gaps()}
        if not re.fullmatch(r"GAP-\d{3,}", gap):
            add(strict, ARCH, "Method Lock: an open method names its gap (`gap: GAP-NNN`): an OPEN is typed, never just empty")
        elif gap not in gaps or gaps[gap]["kind"] != "OPEN":
            add(strict, STACK, f"{gap} is not an OPEN gap of the gtt-gaps register: add `OPEN | {gap} | {STACK_ROW} | scope: ... | affects: ...`")
        elif gaps[gap]["topic"].strip().lower() != STACK_ROW.lower():
            add(strict, STACK, f"{gap} has topic `{gaps[gap]['topic']}`: the gap of an open method has the topic `{STACK_ROW}`")
        if row is None:
            add(strict, STACK, f"section 1 has no `{STACK_ROW}` row: an open method is visible in the map")
        elif OPEN not in row["locked_by"].upper():
            add(strict, STACK, f"the `{STACK_ROW}` row shows `{row['locked_by'] or 'nothing'}` under Locked by: an open method shows OPEN, never an empty cell")
        add("NOTE", ARCH, "the development method is OPEN: it does not block the freeze, and no pack's template or rule applies "
            "until the human decides")
        summary["checked_packs"] = []
        return found, summary
    chosen = chosen_packs(view)
    known = [pid for pid in chosen if pid in all_packs]
    if view["gap"]:
        add("WARN", ARCH, "Method Lock: `gap` is only for an open method")
    bad, undeclared = pairs(known, all_packs)
    for a, b in bad:
        add(strict, ARCH, f"Method Lock: `{a}` and `{b}` are incompatible (their Method Packs say so)")
    for a, b in undeclared:
        add("WARN", ARCH, f"Method Lock: `{a}` with `{b}` is not declared compatible by either pack")
    need_adr = [pid for pid in known if all_packs[pid]["meta"].get("requires_adr") is True]
    adr_ok = re.fullmatch(r"ADR-\d{3,}", locked_by) is not None
    if need_adr and not adr_ok:
        add(strict, ARCH, f"Method Lock: {', '.join(need_adr)} require an ADR, and locked_by is `{locked_by or 'empty'}`: "
            "draft it with the ADR template (gtt-domain/adr/ADR-TEMPLATE.md) and name it here")
    if not need_adr and locked_by.lower() != "none" and not adr_ok:
        add(strict, ARCH, f"Method Lock: no chosen pack requires an ADR, so locked_by is `none` (or an ADR) - got `{locked_by}`")
    if adr_ok:
        files = glob.glob(os.path.join(ADR_DIR, f"{locked_by}*.md"))
        if not files:
            add(strict, ARCH, f"Method Lock: locked_by {locked_by} does not exist under {ADR_DIR}/")
        else:
            adr_status = re.search(r"^-\s*Status:\s*(\S+)", read(files[0]) or "", re.M)
            adr_status = adr_status.group(1) if adr_status else ""
            if adr_status.lower().startswith("superseded"):
                add(strict, files[0], f"{locked_by} is Superseded: the method is locked by the ADR that superseded it")
            elif not adr_status.lower().startswith("accepted"):
                add("WARN", files[0], f"{locked_by} is `{adr_status or 'without status'}`: the freeze ratifies it as accepted")
            if not any(locked_by in " ".join(cells) for cells in change_log_rows()):
                add("WARN", STACK, f"the map change log has no row for {locked_by}: add the row of the method's ADR")
    expected = weakest([all_packs[pid]["meta"].get("verification") for pid in known])
    if expected and (view["verification"] or "").strip() != expected:
        add(strict, ARCH, f"Method Lock: verification is `{view['verification']}`; the weakest of the chosen packs is `{expected}` - "
            "a combination is never more verified than its weakest pack")
    if row is None:
        add(strict, STACK, f"section 1 has no `{STACK_ROW}` row: the ratified method is visible in the map")
    else:
        for pid in chosen:
            if pid not in row["technology"]:
                add(strict, STACK, f"the `{STACK_ROW}` row does not name `{pid}` under Technology")
        expected_lock = locked_by if adr_ok else "none"
        if expected_lock.lower() not in row["locked_by"].lower():
            add(strict, STACK, f"the `{STACK_ROW}` row shows `{row['locked_by'] or 'nothing'}` under Locked by; the Method Lock says `{expected_lock}`")
    rows, has_rule_column = dependency_rows()
    wanted = [r for pid in known for r in pack_rules(all_packs[pid]) if r["check"] == "dependency"]
    if wanted and not has_rule_column:
        add(strict, STACK, "section 5 (Dependency rules) has no `Rule` column: the method's rules are written there with their id")
    for rule in wanted:
        matching = [r for r in rows if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(rule["id"]), r["rule"])]
        if not matching:
            add(strict, STACK, f"{rule['id']} ({rule['pack']}: {rule['from']} must not depend on {rule['must_not_depend_on']}) is not in "
                "section 5 (Dependency rules): write it with the project's real paths and its id in the Rule column")
        for r in matching:
            if not r["module"] or not r["must_not_depend_on"]:
                add(strict, STACK, f"{rule['id']} in section 5 has no Module or no Must not depend on: the real paths are required")
    owned = {r["id"] for pid in known for r in pack_rules(all_packs[pid])}
    every = {r["id"] for p in all_packs.values() for r in pack_rules(p)}
    for r in rows:
        for rid in re.findall(r"[A-Z]{1,4}-\d+", r["rule"]):
            if rid in every and rid not in owned:
                add("WARN", STACK, f"section 5 cites {rid}, a rule of a method this project did not choose")
    found.extend(method_findings(known, all_packs, prefreeze, is_frozen))
    if sel and sel.get("style") not in (None, OPEN) and OPEN not in (sel.get("style"), sel.get("start")):
        if sorted(sel.get("style") or []) != sorted(style) or sel.get("start") != start:
            add("NOTE", ARCH, "the Method Lock differs from the setup answer: the Lock is what the human confirmed and what applies")
    summary["checked_packs"] = known
    return found, summary


def cmd_check(args):
    found, summary = check_all(args.pre_freeze)
    failed = any(level == "FAIL" for level, _, _ in found)
    if args.json:
        emit({"schema": 1, "kind": "gtt-method-check", "result": "fail" if failed else "pass", "pre_freeze": args.pre_freeze,
              "findings": [{"level": l, "where": w, "message": m} for l, w, m in found], "summary": summary})
        return 1 if failed else 0
    for level, where, message in found:
        print(f"{level}  {where}: {message}", file=sys.stderr if level == "FAIL" else sys.stdout)
    if not failed:
        packs_checked = summary.get("checked_packs")
        if packs_checked:
            what = f"method {', '.join(packs_checked)} checked" + (" (setup answer; no Method Lock yet)" if summary.get("source") == "setup" else "")
        elif summary["lock"]["present"]:
            what = "development method OPEN, typed and visible"
        elif summary["selection"] is not None:
            what = "development method OPEN at setup; no Method Lock yet"
        else:
            what = "no development method declared"
        print(f"gtt-method: OK - {what}.")
    return 1 if failed else 0


def cmd_catalog(args):
    found = catalog_problems()
    failed = any(level == "FAIL" for level, _, _ in found)
    if args.json:
        emit({"schema": 1, "kind": "gtt-method-catalog-check", "result": "fail" if failed else "pass",
              "packs": sorted(packs()), "findings": [{"level": l, "where": w, "message": m} for l, w, m in found]})
        return 1 if failed else 0
    for level, where, message in found:
        print(f"{level}  {where}: {message}", file=sys.stderr if level == "FAIL" else sys.stdout)
    if not failed:
        print(f"gtt-method: catalog OK - {len(packs())} Method Pack(s) in {PACKS_DIR}/.")
    return 1 if failed else 0


def cmd_get(args):
    sel, view, force = selection(), lock_view(), in_force()
    out = {"schema": 1, "kind": "gtt-method-state", "selection": sel, "lock": view, "in_force": force, "frozen": frozen(),
           "change": "after the freeze the method changes only through a change request (gtt-propose-change), never here"}
    if args.json:
        emit(out)
        return 0
    shown = lambda value: OPEN if value == OPEN else ", ".join(value) if isinstance(value, list) else (value or OPEN)
    print(f"development method: {force['status']} (from {force['source']}); style {shown(force['style'])}; start {shown(force['start'])}"
          + (f"; locked by {view['locked_by']}; verification {view['verification']}" if view["present"] else "")
          + f"; frozen: {'yes' if out['frozen'] else 'no'}")
    return 0


def cmd_lock(args):
    state = lock()
    view = lock_view(state)
    out = dict(view, schema=1, kind="gtt-method-lock", problems=[{"line": n, "message": m} for n, m in state["problems"]],
               packs=chosen_packs(view) if view["present"] else [], frozen=frozen())
    if args.json:
        emit(out)
    elif not view["present"]:
        print(f"no Method Lock in {ARCH}")
    else:
        print(" ".join(f"{k}: {v}" for k, v in state["values"].items()))
    return 0


def cmd_rules(args):
    all_packs, view = packs(), lock_view()
    ratified = view["present"] and view["status"] == "ratified"
    chosen = [pid for pid in chosen_packs(view) if pid in all_packs] if ratified else []
    rows, _ = dependency_rows()
    rules = []
    for pid in chosen:
        for rule in pack_rules(all_packs[pid]):
            rule["materialized"] = [r for r in rows if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(rule["id"]), r["rule"])]
            rules.append(rule)
    out = {"schema": 1, "kind": "gtt-method-rules", "status": view["status"] if view["present"] else "not declared",
           "packs": chosen, "verification": view["verification"] if ratified else None, "rules": rules,
           "adapters": "the CLI turns each `dependency` rule's materialized rows into its language tool's configuration; "
                       "without an adapter for the language the method is declared-only for that project",
           "violation": "a conflict to report (rule, source file, forbidden dependency) - never a silent correction"}
    if args.json:
        emit(out)
    else:
        if not rules:
            print("no ratified development method: no rules apply")
        for rule in rules:
            where = "; ".join(f"{r['module']} must not depend on {r['must_not_depend_on']}" for r in rule["materialized"]) or "not in stack.md section 5"
            print(f"{rule['id']:6} {rule['check']:10} {rule['from']} must not depend on {rule['must_not_depend_on']}  ->  {where}")
    return 0


# --------------------------------------------------------------------------- the design template (gtt_design)

def epic_templates(epic_id):
    """([(pack id, template)], note) for the design of one Epic, from the method in force. Used by gtt-design.sh scaffold."""
    force, all_packs = in_force(), packs()
    if force["source"] == "none":
        return [], None
    if not force["packs"]:
        return [], ("the development method is OPEN: the design gets no method template. THINK proposes a method as [PROPUESTA] "
                    "with its reason, citing the sources, and waits for the human to confirm before cutting Epics.")
    all_epics = epics()
    first = first_epic(all_epics)
    epic = next((e for e in all_epics if e["id"] == epic_id), None)
    skeleton = epic is not None and (epic["fields"].get("Kind", "").strip().lower() == "skeleton"
                                     or (first is not None and first["id"] == epic_id))
    out = []
    for pid in force["packs"]:
        pack = all_packs.get(pid)
        if not pack or not pack["template"]:
            continue
        if pack["checks"].get("first-epic-kind") and not skeleton:
            continue                                  # a start strategy shapes only its own Epic
        out.append((pid, pack["template"].rstrip("\n")))
    return out, None


def main(argv):
    if not os.path.isdir(".gtt"):
        die("run from the project root (no .gtt/ directory here)")
    parser = argparse.ArgumentParser(prog="gtt_method.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("catalog"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_catalog)
    p = sub.add_parser("list"); p.add_argument("--question", choices=QUESTIONS); p.add_argument("--lang", choices=("es", "en"))
    p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_list)
    p = sub.add_parser("show"); p.add_argument("id"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_show)
    p = sub.add_parser("select"); p.add_argument("--style"); p.add_argument("--start"); p.add_argument("--by")
    p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_select)
    p = sub.add_parser("get"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_get)
    p = sub.add_parser("lock"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_lock)
    p = sub.add_parser("check"); p.add_argument("--pre-freeze", action="store_true"); p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check)
    p = sub.add_parser("rules"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_rules)
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
