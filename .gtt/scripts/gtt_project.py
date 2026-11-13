#!/usr/bin/env python3
"""GTT - project-facing Bootstrap contracts (engine).

Structured, deterministic views and the small per-project state the CLI needs, derived from the
actual project (never from an agent's recollection, never authority):

  detect                     project detection: GTT state, layout, freeze, design-source candidates
  elicitation [--next-action] Initial Design Questionnaire state (absent|pending|in-progress|complete), read-only
  think-plan [skip <step>]   the THINK stage as ordered steps computed from the files; --gate fails when context or Epics came first
  next-action [--json] [--session-start]  what GTT is waiting on: THINK, the questionnaire, the inbox (at once or at a cut point), the design
  inbox-line                 `Bandeja: n nuevas · n en revisión · n por ratificar` for session.md
  status [--with-validation] structured status: bootstrap, ade, methodology, sources, governance, freeze, validation, session
  session                    structured session context (freeze, change request, proposals, git, operational state, artifacts)
  validation                 gtt-validate.sh as one structured result
  interaction                what the selected plan does without asking and what it asks for (derived from its policy)
  next-id                    the next free id of a kind (adr|epic|story|run); deterministic, never reuses a retired id
  profile get|set            Autonomy Profile (light|medium|hard|team) and language; meaning lives in .gtt/contract/profiles.json
  source select|list         initial sources: a SELECTED source is never a governed authority
  export-policy              clean-export policy resolved against this project (ADE overlays from the ownership ledger)
  clean-plan                 what `clean` would remove; removes nothing
  recovery snapshot|restore  preserve / re-apply GTT configuration (not the governed domain content)

Every mutating command is a dry run unless --apply is given and never overwrites existing state.
Exit 0 ok, 1 violation / refused, 2 cannot run.
"""

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

from gtt_bash import bash_executable

import gtt_manifest as gm
import gtt_provenance as gp

CONTRACT = ".gtt/contract"
METHOD = ".gtt/methodology.json"
SELECTED = ".gtt/selected-sources.json"
FROZEN = "gtt-domain/.frozen"
CONTEXT_FILES = ["stack", "architecture", "constraints", "principles", "solution-vision", "glossary"]
PLACEHOLDER = re.compile(r"TODO|PLACEHOLDER|REPLACE ME|<[a-z][^>]*>")
KIT = {"AGENTS.md", "LICENSE", "README.md", "readme-gtt.md", "readme-gtt.es.md"}
SOURCE_SUFFIX = (".md", ".txt", ".rst", ".docx", ".pdf", ".odt")


def die(message, code=2):
    print(f"gtt-project: {message}", file=sys.stderr)
    sys.exit(code)


def emit(obj):
    print(json.dumps(obj, indent=2, sort_keys=True))


def now():
    return os.environ.get("GTT_NOW") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except OSError:
        return default
    except ValueError as exc:
        die(f"{path} is not valid JSON: {exc}")


def write_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


def sh(*cmd):
    proc = subprocess.run([bash_executable(), *cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout, proc.stderr


def release():
    data = read_json(os.path.join(CONTRACT, "release.json"))
    if data is None:
        die(f"{CONTRACT}/release.json missing")
    return data


def profiles():
    data = read_json(os.path.join(CONTRACT, "profiles.json"))
    if data is None:
        die(f"{CONTRACT}/profiles.json missing")
    return data


def frozen_since():
    if not os.path.isfile(FROZEN):
        return None
    with open(FROZEN, encoding="utf-8") as handle:
        return handle.readline().strip() or "unknown"


def ade_json(op, *extra):
    if not os.path.isfile(".gtt/ade.json") and op in ("state", "owned", "validate"):
        return {"configured": False}
    rc, out, err = sh(".gtt/scripts/gtt-ade.sh", op, "--json", *extra)
    try:
        return json.loads(out)
    except ValueError:
        return {"error": (err or out).strip()[:200], "exit_code": rc}


# --------------------------------------------------------------- methodology

def current_profile():
    state = read_json(METHOD) or {}
    spec = profiles()
    profile = state.get("profile")
    # No selection: the gates of spec["default"] apply, but that is a fallback, never a selection - the plan is
    # reported as not selected and the Bootstrap still has to ask the human (profiles.json -> selection).
    return {"profile": profile or spec["default"], "source": "project" if profile else "default",
            "selected": bool(profile), "language": state.get("language"), "state": state}


ASKS = ("confirm", "propose_confirm", "team_policy", "required")


def interaction(profile_id, spec=None):
    """What the selected plan makes GTT do without asking and what it asks for - derived from the plan's own
    policy, never a second definition. This is how the developer-experience rule differs from plan to plan."""
    spec = spec or profiles()
    policy = spec["profiles"][profile_id]["plan"]["policy"]
    values = dict(policy["automation"], relevant_change=policy["human"]["confirmation"]["relevant_change"],
                  governed_decision=policy["human"]["confirmation"]["governed_decision"],
                  destructive=policy["human"]["confirmation"]["destructive"])
    values.pop("level", None)
    return {"plan": profile_id, "automation_level": policy["automation"]["level"],
            "without_asking": sorted(k for k, v in values.items() if v not in ASKS),
            "asks_for": {k: v for k, v in sorted(values.items()) if v in ASKS},
            "maintain_reconciles_moves": policy["automation"]["reference_updates"] in ("automatic", "automatic_safe"),
            "id_resolution": {"automatic": "use", "automatic_safe": "use"}.get(policy["automation"]["identity_resolution"], "propose")}


def cmd_interaction(args):
    cur = current_profile()
    out = dict(interaction(cur["profile"]), schema=1, selected=cur["selected"])
    if args.key:
        if args.key not in out:
            die(f"unknown key `{args.key}`")
        value = out[args.key]
        print(str(value).lower() if isinstance(value, bool) else value)
    else:
        emit(out)
    return 0


ADR_PLAN_LINE = re.compile(r"^\s*[-*]?\s*Autonomy Profile:\s*(\w+)\s*(?:->|\u2192)\s*(\w+)\s*$", re.MULTILINE)


def adr_authorises(adr_id, before, after):
    """True when a human-promoted, Accepted ADR records exactly this plan change. gtt-domain/adr/ is write-protected to
    agents, so such an ADR is the evidence that the governed change (proposal -> human decision) happened."""
    for path in glob.glob(f"gtt-domain/adr/{adr_id}-*.md"):
        text = open(path, encoding="utf-8").read()
        if re.search(r"^\s*[-*]?\s*Status:\s*Accepted\b", text, re.MULTILINE | re.IGNORECASE):
            if any((m.group(1), m.group(2)) == (before, after) for m in ADR_PLAN_LINE.finditer(text)):
                return True
    return False


def cmd_profile(args):
    spec = profiles()
    order = spec["strictness_order"]
    cur = current_profile()
    if args.action == "get":
        prof = spec["profiles"][cur["profile"]]
        out = {"schema": 1, "contract_version": spec["contract_version"], "profile": cur["profile"], "source": cur["source"],
               "language": cur["language"], "supported": [p["id"] for p in spec["supported"]], "default": spec["default"],
               "selected": cur["selected"], "selection": spec["selection"], "plan": prof["plan"],
               "developer_experience": spec["developer_experience"], "interaction": interaction(cur["profile"], spec),
               "gates": prof["gates"], "relaxes": prof["relaxes"], "semantics": prof["semantics"],
               "invariants": [i["id"] for i in spec["invariants"]], "frozen": os.path.isfile(FROZEN)}
        if args.json:
            emit(out)
        elif cur["selected"]:
            print(f"plan: {prof['plan']['label']} ({out['profile']}); language: {out['language'] or 'unset'}; frozen: {out['frozen']}")
        else:
            print(f"plan: not selected - the human must choose one of {', '.join(out['supported'])} "
                  f"({out['profile']} gates apply meanwhile); language: {out['language'] or 'unset'}; frozen: {out['frozen']}")
        return 0
    if not args.profile and not args.language:
        die("give --profile and/or --language")
    new = dict(cur["state"])
    if args.profile:
        if args.profile not in order:
            die(f"unknown profile `{args.profile}` (supported: {', '.join(order)})")
        relaxes = order.index(args.profile) < order.index(cur["profile"])
        if os.path.isfile(FROZEN) and relaxes and not (args.adr and adr_authorises(args.adr, cur["profile"], args.profile)):
            why = (f"`{args.adr}` is not an Accepted ADR in gtt-domain/adr/ recording `Autonomy Profile: {cur['profile']} -> {args.profile}`. "
                   if args.adr else "")
            print(f"REFUSED: the project is frozen; moving from `{cur['profile']}` to the less strict `{args.profile}` is a "
                  "governed change (change request -> proposal -> human decision). " + why +
                  "Ask the agent for an Autonomy Profile change proposal (gtt-propose-change, form 7); once the ADR is promoted, run: "
                  f"gtt-project.sh profile set --profile {args.profile} --adr ADR-NNN --apply. Nothing was written.", file=sys.stderr)
            return 1
        new["profile"] = args.profile
    if args.language:
        if args.language not in release()["supported_languages"]:
            die(f"unsupported language `{args.language}` (supported: {', '.join(release()['supported_languages'])})")
        new["language"] = args.language
    new.update({"schema": 1, "set_at": now()})
    before = cur["profile"] if cur["selected"] else "not selected"
    print(f"methodology: plan {before} -> {new.get('profile', before)}; "
          f"language {cur['language'] or 'unset'} -> {new.get('language') or 'unset'}")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    write_json(METHOD, new)
    print(f"gtt-project: written {METHOD}")
    return 0


# -------------------------------------------------------------------- next id

ID_KINDS = {"adr": "ADR", "epic": "EPIC", "story": "STORY", "run": "RUN"}


def occupied_ids(prefix):
    """Every number already taken for `prefix`: ids in the identity manifest (active AND retired - a retired id is
    never reused), file names under gtt-domain/, and ids written in gtt-domain/backlog.md. Template placeholder
    lines do not count. Deterministic: the same repository always gives the same answer."""
    token = re.compile(rf"(?<![A-Za-z0-9]){prefix}-(\d+)(?![0-9])")
    taken = {}

    def note(text, where):
        for match in token.finditer(text):
            taken.setdefault(int(match.group(1)), where)

    manifest = read_json(".gtt/index/artifacts.json") or {}
    for entry in manifest.get("artifacts", []):
        note(str(entry.get("id", "")), f"identity ({entry.get('status', 'active')})")
    for root, _dirs, files in os.walk("gtt-domain"):
        for name in files:
            note(name, os.path.join(root, name).replace(os.sep, "/"))
    try:
        with open("gtt-domain/backlog.md", encoding="utf-8") as handle:
            for line in handle:
                if not re.search(r"<[A-Za-z][^>]*>", line):      # a template example is not a real Epic/Story
                    note(line, "gtt-domain/backlog.md")
    except OSError:
        pass
    return taken


def cmd_next_id(args):
    prefix = ID_KINDS[args.kind]
    taken = occupied_ids(prefix)
    number = max(taken, default=0) + 1
    cur = current_profile()
    out = {"schema": 1, "kind": args.kind, "id": f"{prefix}-{number:03d}",
           "plan": cur["profile"], "plan_selected": cur["selected"],
           "resolution": interaction(cur["profile"])["id_resolution"],
           "occupied": [f"{prefix}-{n:03d}" for n in sorted(taken)],
           "rule": "highest occupied number + 1; retired ids are never reused"}
    if args.requested:
        match = re.fullmatch(rf"{prefix}-(\d+)", args.requested)
        if not match:
            die(f"`{args.requested}` is not a {prefix} id ({prefix}-NNN)")
        free = int(match.group(1)) not in taken
        out["requested"] = {"id": args.requested, "free": free,
                            "occupied_by": None if free else taken[int(match.group(1))]}
        if free:
            out["id"] = f"{prefix}-{int(match.group(1)):03d}"
    if args.json:
        emit(out)
    else:
        print(out["id"])
    return 0


# ------------------------------------------------------------------- sources

def cmd_source(args):
    data = read_json(SELECTED) or {"schema": 1, "sources": []}
    if args.action == "select":
        path = os.path.normpath(args.path).replace("\\", "/")
        root = os.path.realpath(".")
        if not os.path.exists(path) or not os.path.realpath(path).startswith(root):
            die(f"`{args.path}` does not exist inside the project; nothing recorded.", 1)
        if any(s["path"] == path for s in data["sources"]):
            die(f"`{path}` is already selected; nothing recorded.", 1)
        entry = {"path": path, "type": args.type, "version": args.version or None, "selected_by": args.by or "unspecified",
                 "selected_at": now(), "authority_status": "unassigned", "precedence_status": "unassigned"}
        print(f"select {path} ({args.type}): authority and precedence stay UNASSIGNED - a selected source is not a governed authority")
        if not args.apply:
            print("(dry run - nothing written; re-run with --apply)")
            return 0
        data["sources"].append(entry)
        write_json(SELECTED, data)
        return 0
    findings = gp.Findings()
    manifest = gp.load_sources(findings)
    declared = {s["path"]: s for s in (manifest["sources"] if manifest else [])}
    rows = []
    for s in data["sources"]:
        d = declared.get(s["path"])
        rows.append(dict(s, governed=bool(d), authority_status=d["authority"] if d else "unassigned",
                         precedence_status=(d["precedence"] if d and d["precedence"] is not None else "unassigned"),
                         declared_id=d["id"] if d else None, version=s["version"] or (d["version"] if d else None)))
    selected_paths = {s["path"] for s in data["sources"]}
    out = {"schema": 1, "rule": "selected != governed authority: authority and precedence are declared in "
           "gtt-domain/context/sources.md by a human, never inferred by the CLI or the Bootstrap",
           "grounding": "only declared sources with authority primary or secondary enter grounding as authority; "
                        "selected-only sources are candidates for Confirmation A",
           "selected": rows,
           "declared_not_selected": [d for p, d in declared.items() if p not in selected_paths],
           "policy": manifest["policy"] if manifest else "none"}
    if args.json:
        emit(out)
    else:
        for r in rows:
            print(f"{r['path']}  [{r['type']}]  authority: {r['authority_status']}  precedence: {r['precedence_status']}")
        if not rows:
            print("no sources selected")
    return 0


# -------------------------------------------------------------------- detect

def context_state():
    states = {}
    for name in CONTEXT_FILES:
        path = f"gtt-domain/context/{name}.md"
        if not os.path.isfile(path):
            states[name] = "missing"
            continue
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        states[name] = "placeholders" if (PLACEHOLDER.search(text) or len([l for l in text.split("\n") if l.strip()]) <= 5) else "no-placeholders"
    return states


def design_candidates():
    out = []
    for name in sorted(os.listdir(".")):
        if not os.path.isfile(name) or name in KIT or name.startswith(".") or name.startswith("SOURCE-BRIEF"):
            continue
        if name.lower().endswith(SOURCE_SUFFIX) and not re.match(r"(?i)^(license|changelog|contributing|code_of_conduct)", name):
            out.append(name)
    return out


THINK_LEVELS = ("QUICK", "STANDARD", "DEEP")
THINK_FALLBACK = "STANDARD"


def think_state(path):
    """The THINK Depth recorded in a Design Assessment working copy, and what the copy may not say whatever the
    depth: a verdict above POOR with a floor line not met or not assessed, or a depth nobody decided.
    Deterministic; it judges no rating."""
    out = {"levels": list(THINK_LEVELS), "selected": None, "applies": THINK_FALLBACK, "state": "not selected",
           "escalations": [], "verdict": None, "floor": {"met": 0, "not_met": 0, "unassessed": 0}, "findings": []}
    if not path or not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as handle:
        text = handle.read().replace("\r\n", "\n")
    value = re.search(r"^THINK Depth:[ \t]*(\S*)", text, re.M)
    depth = value.group(1) if value else ""
    if depth in THINK_LEVELS:
        out.update(selected=depth, applies=depth, state="selected")
    elif depth:
        out["findings"].append(f"THINK Depth `{depth}` is not one of {', '.join(THINK_LEVELS)}")
    verdict = re.search(r"^Verdict:[ \t]*(\S*)", text, re.M)
    out["verdict"] = verdict.group(1) if verdict and verdict.group(1) else None
    if out["verdict"] and out["verdict"] not in ("STRONG", "ADEQUATE", "POOR"):
        out["findings"].append(f"verdict `{out['verdict']}` is not one of STRONG, ADEQUATE, POOR")

    def rows(heading):
        section = re.search(r"^#+ " + re.escape(heading) + r"[^\n]*\n(.*?)(?=^#+ |\Z)", text, re.M | re.S)
        cells = [[c.strip() for c in line.strip().strip("|").split("|")] for line in (section.group(1) if section else "").split("\n")
                 if line.startswith("|")]
        return [r for r in cells[2:] if any(r)]                # header and separator out

    for row in rows("4. Minimum floor"):
        state = row[-1].upper()
        key = "met" if state == "MET" else "not_met" if state == "NOT MET" else "unassessed"
        out["floor"][key] += 1
    if out["verdict"] in ("STRONG", "ADEQUATE"):
        if out["floor"]["not_met"]:
            out["findings"].append(f"verdict {out['verdict']} with {out['floor']['not_met']} floor line(s) NOT MET: below the floor "
                                   f"the verdict is POOR at every THINK Depth")
        if out["floor"]["unassessed"]:
            out["findings"].append(f"verdict {out['verdict']} with {out['floor']['unassessed']} floor line(s) not assessed: the floor "
                                   f"is assessed line by line at every THINK Depth")
    for row in rows("Escalation log"):
        if len(row) < 4 or not (row[0] or row[1]):
            continue
        decision = row[-1]
        accepted = bool(re.match(r"(?i)accept", decision))
        out["escalations"].append({"from": row[0], "to": row[1], "decision": decision or "pending", "accepted": accepted})
        if row[1] not in THINK_LEVELS or row[0] not in THINK_LEVELS:
            out["findings"].append(f"escalation `{row[0]}` -> `{row[1]}` names a depth that does not exist")
        elif row[1] == out["selected"] and not accepted:
            out["findings"].append(f"THINK Depth is {row[1]} through an escalation the human has not accepted: the ADE proposes, "
                                   f"the human decides")
    return out


def think_copy():
    """Where the THINK Depth of this project is recorded: the Design Assessment working copy when there is a
    design document, otherwise the questionnaire working copy. None while neither exists."""
    templates = gm.templates(gm.load())
    for tid in ("design-assessment", "initial-design-questionnaire"):
        path = (templates.get(tid) or {}).get("materialize_to")
        if path and os.path.isfile(path):
            return path
    return None


def cmd_think(args):
    state = think_state(think_copy())
    if args.json:
        emit(state)
    else:
        print(f"THINK Depth: {state['selected'] or 'not selected (' + state['applies'] + ' applies)'}; verdict: {state['verdict'] or 'none'}; "
              f"floor: {state['floor']['met']} met, {state['floor']['not_met']} not met, {state['floor']['unassessed']} not assessed; "
              f"escalations: {len(state['escalations'])}")
        for finding in state["findings"]:
            print(f"FAIL  design assessment: {finding}", file=sys.stderr)
    return 1 if state["findings"] else 0


# ------------------------------------------------------------------ THINK plan

THINK_SKIPS = "gtt-domain/proposals/bootstrap/think-skips.json"
THINK_ORDER = ("depth", "assessment", "guidelines", "questionnaire", "mapping", "designs", "stories")
THINK_BEFORE_MAPPING = ("depth", "assessment", "guidelines", "questionnaire")
THINK_LABEL = {
    "depth": "THINK Depth chosen by the human",
    "assessment": "Design Assessment written (gtt-template.sh materialize design-assessment)",
    "guidelines": "the human's guidelines asked and recorded (`Human guidelines:` line of the THINK Depth block)",
    "questionnaire": "Initial Design Questionnaire completed for what is THIN or MISSING",
    "mapping": "the six context files written from the confirmed design",
    "designs": "one design per Epic (gtt-domain/context/design/EPIC-NNN.md)",
    "stories": "Stories of the first Epic drafted (Implements + Done when) and their open questions asked",
}


def think_skips():
    data = read_json(THINK_SKIPS) or {}
    return {s.get("step"): s for s in data.get("skips", []) if s.get("step") in THINK_ORDER}


def backlog_epics():
    """(epic ids, Stories per epic) read from the backlog by shape only."""
    try:
        with open("gtt-domain/backlog.md", encoding="utf-8") as handle:
            text = handle.read().replace("\r\n", "\n")
    except OSError:
        return [], {}
    ids, stories, current = [], {}, None
    for line in text.split("\n"):
        epic = re.match(r"^#{2,4}\s+(EPIC-\d+)\b", line)
        if epic and "(example)" not in line:
            current = epic.group(1)
            ids.append(current)
            stories[current] = 0
        elif current and re.match(r"^#{3,6}\s+STORY-\d+", line) and "(example)" not in line:
            stories[current] += 1
    return ids, stories


def guidelines_recorded(path):
    if not path or not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as handle:
        found = re.search(r"^Human guidelines:[ \t]*(\S.*)$", handle.read(), re.M)
    return bool(found)


def think_plan():
    """The THINK stage as an ordered list of steps, each done, pending or skipped, computed from the files.
    A step before the mapping that is pending while the context is already written, or the Epics already cut,
    is a violation: THINK was skipped, not done. Only the human skips a step (think-plan skip). Never a decision."""
    installed = os.path.isfile(".gtt/ade.json")
    frozen = os.path.isfile(FROZEN)
    report = ""
    try:
        with open(".gtt/docs/gtt-completion.md", encoding="utf-8") as handle:
            report = handle.read()
    except OSError:
        pass
    recorded = bool(report) and "No bootstrap has been recorded yet" not in report
    out = {"schema": 1, "kind": "gtt-think-plan", "authority": "none", "active": installed and not frozen and not recorded,
           "steps": [], "violations": [], "current": None}
    if not out["active"]:
        return out
    skips = think_skips()
    has_doc = bool(design_candidates() or glob.glob("SOURCE-BRIEF.*"))
    copy = think_copy()
    think = think_state(copy)
    quest = elicitation_state()
    ids, stories = backlog_epics()
    mapped = all(v == "no-placeholders" for v in context_state().values())
    templates = gm.templates(gm.load())
    assess_path = (templates.get("design-assessment") or {}).get("materialize_to")
    assessed = bool(assess_path and os.path.isfile(assess_path) and think_state(assess_path)["verdict"])
    needs_quest = (not has_doc) or (think["verdict"] != "STRONG")
    done = {
        "depth": think["selected"] is not None,
        "assessment": assessed,
        "guidelines": guidelines_recorded(copy),
        "questionnaire": quest["state"] == "complete",
        "mapping": mapped,
        "designs": bool(ids) and all(os.path.isfile(f"gtt-domain/context/design/{i}.md") for i in ids),
        "stories": bool(ids) and stories.get(sorted(ids)[0], 0) > 0,
    }
    required = {"depth": True, "assessment": has_doc, "guidelines": True, "questionnaire": needs_quest,
                "mapping": True, "designs": True, "stories": True}
    for step in THINK_ORDER:
        if not required[step]:
            state = "not-needed"
        elif done[step]:
            state = "done"
        elif step in skips:
            state = "skipped"
        else:
            state = "pending"
        out["steps"].append({"id": step, "label": THINK_LABEL[step], "state": state,
                             "skipped_by": skips[step].get("by") if state == "skipped" else None})
    state_of = {s["id"]: s["state"] for s in out["steps"]}
    out["current"] = next((s["id"] for s in out["steps"] if s["state"] == "pending"), None)
    written = [name for name, flag in (("the six context files", mapped), ("the Epics in the backlog", bool(ids))) if flag]
    open_before = [s for s in THINK_BEFORE_MAPPING if state_of[s] == "pending"]
    if written and open_before:
        out["violations"].append(f"{' and '.join(written)} written before THINK finished: "
                                 f"{', '.join(open_before)} not done and not skipped by the human")
    return out


def think_plan_text(plan):
    """The one block the ADE reads: where THINK stands and what to do now. Short on purpose."""
    mark = {"done": "x", "skipped": "-", "not-needed": " ", "pending": " "}
    lines = [f"[{mark[s['state']]}] {s['id']}: {s['label']}" + (" (skipped by the human)" if s["state"] == "skipped" else "")
             for s in plan["steps"] if s["state"] != "not-needed"]
    if plan["violations"]:
        lines.insert(0, "OUT OF ORDER - " + "; ".join(plan["violations"]) + ". Go back to the first pending step; "
                        "do not continue from here. Nothing already written is deleted.")
    if plan["current"]:
        lines.append(f"NEXT: {plan['current']} - {THINK_LABEL[plan['current']]}. Never skip a step on your own; "
                     f"only if the human asks: gtt-project.sh think-plan skip {plan['current']} --by <who> --reason <why> --apply")
    return "\n".join(lines)


def cmd_think_plan(args):
    if args.action == "skip":
        if args.step not in THINK_ORDER or not args.by or not args.reason:
            die("skip needs a step (" + ", ".join(THINK_ORDER) + "), --by and --reason: only the human skips a THINK step.", 2)
        print(f"skip {args.step}: by {args.by} - {args.reason}")
        if not args.apply:
            print("(dry run - nothing written; re-run with --apply)")
            return 0
        data = read_json(THINK_SKIPS) or {"schema": 1, "skips": []}
        data["skips"] = [s for s in data["skips"] if s.get("step") != args.step] + [
            {"step": args.step, "by": args.by, "reason": args.reason, "at": now()}]
        os.makedirs(os.path.dirname(THINK_SKIPS), exist_ok=True)
        write_json(THINK_SKIPS, data)
        return 0
    plan = think_plan()
    if args.json:
        emit(plan)
    elif plan["active"]:
        print(think_plan_text(plan))
    if args.gate and plan["violations"]:
        for v in plan["violations"]:
            print(f"FAIL  THINK: {v}", file=sys.stderr)
        return 1
    return 0


QUESTIONNAIRE_SLOT = re.compile(r"<!-- ADE (?:inspects project and )?populates this section -->")
PROVENANCE_TAG = re.compile(r"\[(FUENTE|VAC[IÍ]O|CONFLICTO|PROPUESTA)\b")
READINESS = ("READY", "READY_WITH_OPEN_ITEMS", "NOT_READY")
ELICITATION_OPEN = ("pending", "in-progress")


def elicitation_state():
    """Where the Initial Design Questionnaire stands: absent, pending, in-progress or complete. Computed from the
    working copy against the template it was materialized from - slots still holding the template's placeholder,
    provenance tags beyond the template's own, the THINK Depth, the readiness of section 23 and the human review of
    section 24, and the minimum floor of section 23 (a readiness above NOT_READY below the floor is not complete).
    Read-only: it never writes the copy, never turns a [PROPUESTA] into an answer, never judges one.
    The next action is shown only while the questionnaire is open and the project is not frozen."""
    templates = gm.templates(gm.load())
    tpl = templates.get("initial-design-questionnaire") or {}
    path = tpl.get("materialize_to")
    out = {"schema": 1, "kind": "gtt-elicitation-state", "authority": "none", "template": "initial-design-questionnaire",
           "working_copy": path, "state": "absent", "slots": {"total": 0, "answered": 0},
           "provenance_tags_added": 0, "think_depth": None, "readiness": None, "floor": {"lines": 0, "met": 0}, "human_review": None,
           "frozen": os.path.isfile(FROZEN), "next_action": None, "findings": []}
    if not path or not os.path.isfile(path):
        return out
    try:
        with open(tpl["path"], encoding="utf-8") as handle:
            template = handle.read()
    except (KeyError, OSError):
        template = ""
    with open(path, encoding="utf-8") as handle:
        text = handle.read().replace("\r\n", "\n")
    total = len(QUESTIONNAIRE_SLOT.findall(template))
    out["slots"] = {"total": total, "answered": max(0, total - len(QUESTIONNAIRE_SLOT.findall(text)))}
    out["provenance_tags_added"] = max(0, len(PROVENANCE_TAG.findall(text)) - len(PROVENANCE_TAG.findall(template)))
    out["think_depth"] = think_state(path)["selected"]

    def section(heading):
        found = re.search(r"^#+ " + re.escape(heading) + r"[^\n]*\n(.*?)(?=^#+ |\Z)", text, re.M | re.S)
        return found.group(1) if found else ""

    status = re.search(r"^Status:[ \t]*(\S*)", section("Readiness"), re.M)
    if status and status.group(1):
        if status.group(1) in READINESS:
            out["readiness"] = status.group(1)
        else:
            out["findings"].append(f"readiness `{status.group(1)}` is not one of {', '.join(READINESS)}")
    floor = [[c.strip() for c in line.strip().strip("|").split("|")]
             for line in section("Minimum floor").split("\n") if line.startswith("|")][2:]   # header and separator out
    out["floor"] = {"lines": len(floor), "met": sum(1 for r in floor if r[1:2] and r[1].upper() == "MET")}
    if out["readiness"] in ("READY", "READY_WITH_OPEN_ITEMS") and out["floor"]["met"] < out["floor"]["lines"]:
        out["findings"].append(f"readiness {out['readiness']} with {out['floor']['lines'] - out['floor']['met']} floor line(s) "
                               f"not MET (section 23): below the floor the readiness is NOT_READY")
    review = re.search(r"^Reviewed by:[ \t]*(.*)$", section("24. Human Review"), re.M)
    # A copy materialized before section 24 carried a review record has no line to fill: readiness decides alone.
    out["human_review"] = "not recorded in this copy" if review is None else ("recorded" if review.group(1).strip() else "pending")
    touched = (out["slots"]["answered"] or out["provenance_tags_added"] or out["think_depth"] or out["readiness"]
               or out["human_review"] == "recorded")
    below_floor = out["floor"]["met"] < out["floor"]["lines"]
    if out["readiness"] in ("READY", "READY_WITH_OPEN_ITEMS") and out["human_review"] != "pending" and not below_floor:
        out["state"] = "complete"
    else:
        out["state"] = "in-progress" if touched else "pending"
    if out["state"] in ELICITATION_OPEN and not out["frozen"]:
        detail = (f"{out['slots']['answered']}/{total} sections answered" if out["state"] == "in-progress" else "not started")
        if out["readiness"] in ("READY", "READY_WITH_OPEN_ITEMS") and below_floor:
            detail += f"; readiness {out['readiness']} but the floor is not met (section 23): architecture and stack still to decide"
        elif out["readiness"] in ("READY", "READY_WITH_OPEN_ITEMS"):
            detail += f"; readiness {out['readiness']}, awaiting the human's review (section 24)"
        out["next_action"] = (f"Initial Design Questionnaire {out['state']} ({detail}) -> {path}. "
                              f"Start or resume it on the user's first message, whatever it says, "
                              f"or when they run /gtt: AGENTS.md -> Bootstrap behavior.")
    return out


def cmd_elicitation(args):
    state = elicitation_state()
    if args.json:
        emit(state)
    elif args.next_action:
        if state["next_action"]:
            print(state["next_action"])
    else:
        print(f"Initial Design Questionnaire: {state['state']}; sections answered: {state['slots']['answered']}/{state['slots']['total']}; "
              f"readiness: {state['readiness'] or 'not set'}; human review: {state['human_review'] or 'n/a'}")
    for finding in state["findings"]:
        print(f"WARN  questionnaire: {finding}", file=sys.stderr)
    return 0


def inbox_state():
    """The inbox as the session sees it: counts for the status line and the refs that wait on the agent. None when this
    Bootstrap carries no inbox. Computed from the files (gtt_inbox), never stored."""
    try:
        import gtt_inbox
        import gtt_pending
        c = gtt_inbox.contract()
        items = gtt_inbox.entries(c)
        asks_open = {r["id"] for r in gtt_pending.summary()["asks"]}
    except (Exception, SystemExit):
        return None
    out = {"new": [], "now": [], "accepted": [], "urgent": [], "review": 0, "ratify": 0}
    for e in items:
        last_state = next((l for l in reversed(e["trail"]) if l["key"] not in ("priority",)), None)
        mirrored = bool(last_state and gtt_inbox.MIRROR.search(last_state["value"]))
        if e["stage"] == "new":
            waiting = next((l for l in reversed(e["trail"]) if l["key"] == "triage"), None)
            if waiting and last_state is waiting and gtt_inbox.triage_info(waiting["value"], c)["result"] == "ask":
                ref = (gtt_inbox.triage_info(waiting["value"], c)["to"] or "")
                if ref in asks_open:
                    continue                                # the agent asked; the human has not answered yet
            out["new"].append(e["ref"])
            if e["now"]:
                out["now"].append(e["ref"])
        elif e["stage"] == "accepted" and e["kind"] == "PROP":
            out["accepted"].append(e["ref"])
            if e["priority"] == "urgent":
                out["urgent"].append(e["ref"])
        elif e["stage"] in ("review", "ratify") and not (e["kind"] == "IDEA" and mirrored):
            out[e["stage"]] += 1
    return out


def inbox_line(triage_only=False):
    """`Bandeja: n nuevas · n en revisión · n por ratificar` (the session's one line), or "" when the inbox is empty.
    With triage_only, `Bandeja: n sin triage` (the notice when a Story closes), or "" when none waits."""
    state = inbox_state()
    if triage_only:
        if not state or not state["new"]:
            return ""
        return (f"Bandeja: {len(state['new'])} sin triage" if (read_json(METHOD) or {}).get("language") == "es"
                else f"Inbox: {len(state['new'])} without triage")
    if not state or not (state["new"] or state["review"] or state["ratify"]):
        return ""
    if (read_json(METHOD) or {}).get("language") == "es":
        return f"Bandeja: {len(state['new'])} nuevas · {state['review']} en revisión · {state['ratify']} por ratificar"
    return f"Inbox: {len(state['new'])} new · {state['review']} in review · {state['ratify']} to ratify"


def at_cut_point(session_start):
    """The inbox is triaged at a cut point: when a session starts, or when no Story is In Progress, so a triage never
    interrupts one."""
    return bool(session_start) or os.environ.get("GTT_SESSION_START") == "1" or not stories("In Progress")


def inbox_work(session_start=False):
    """The next action the inbox asks for, or None. An entry written with --now, or an accepted urgent one, is the first
    answer; the rest waits for a cut point."""
    state = inbox_state()
    if not state:
        return None
    spanish = ((read_json(METHOD) or {}).get("language") == "es")
    urgent = state["now"] + [r for r in state["urgent"] if r not in state["now"]]
    if urgent:
        refs = urgent
    elif at_cut_point(session_start):
        refs = state["new"] + state["accepted"]
    else:
        return None
    if not refs:
        return None
    waiting_new = [r for r in refs if r in state["new"]]
    waiting_pkg = [r for r in refs if r in state["accepted"]]
    parts = []
    if waiting_new:
        parts.append(f"triage {', '.join(waiting_new[:6])}" + (" and more" if len(waiting_new) > 6 else "") +
                     " (skill gtt-propose-change, section Triage; `bash .gtt/scripts/gtt-inbox.sh list`)")
    if waiting_pkg:
        parts.append(f"prepare the package of {', '.join(waiting_pkg[:6])} (accepted: skill gtt-propose-change)")
    text = (f"Inbox waits on you: {'; '.join(parts)}. Do it on the user's first message, whatever it says"
            f"{' - the entry is urgent or was written with --now' if urgent else ''}; it decides nothing, the human ratifies.")
    human = (f"Abre el proyecto en el ADE principal y escribe cualquier cosa: su primera respuesta atiende la bandeja ({', '.join(refs[:4])}). "
             "Síguela con: gtt status" if spanish else
             f"Open the project in the Primary ADE and write anything: its first answer works the inbox ({', '.join(refs[:4])}). "
             "Follow it with: gtt status")
    return {"kind": "inbox", "text": text, "human": human, "refs": refs}


def next_action(session_start=False):
    """What GTT is waiting on, or None: THINK, an open Initial Design Questionnaire, then the inbox (an entry with
    --now or an urgent accepted one at once; the rest at a cut point), then - in an installed project with no design
    yet - the design itself.
    `text` is the agent's instruction; `human` is what the person does next.
    Computed, never a decision."""
    plan = think_plan()
    if plan["active"] and plan["current"] and (plan["violations"] or design_candidates() or glob.glob("SOURCE-BRIEF.*")):
        candidates = design_candidates()
        named = (f"No governed design yet. Design document candidates: {', '.join(candidates)}. Ask the human which one(s) are the design "
                 "before anything else.\n") if candidates else ""
        step = plan["current"] or "review"
        spanish = ((read_json(METHOD) or {}).get("language") == "es")
        human = (f"Abre el proyecto en el ADE principal y escribe cualquier cosa: su primera respuesta continúa THINK en el paso donde quedó ({step})."
                 if spanish else
                 f"Open the project in the Primary ADE and write anything: its first answer continues THINK at the step it stopped ({step}).")
        return {"kind": "think", "text": named + "THINK is in progress; follow it in order (AGENTS.md -> Bootstrap behavior). Run "
                "`bash .gtt/scripts/gtt-project.sh think-plan` and show the human where it stands.\n" + think_plan_text(plan),
                "human": human}
    line = elicitation_state()["next_action"]
    if line:
        handoff = (read_json(os.path.join(CONTRACT, "elicitation.json")) or {}).get("handoff", {}).get("next_action")
        return {"kind": "questionnaire", "text": line, "human": handoff or line}
    urgent = inbox_work(session_start)
    if urgent:
        return urgent
    # An installed project with no design yet and no questionnaire: the design is what GTT waits on. Every
    # state has a next action, so an ADE that only reads it at session start still knows where to begin.
    if os.path.isfile(".gtt/ade.json") and not os.path.isfile(FROZEN) and not glob.glob("SOURCE-BRIEF.*") \
            and any(v != "no-placeholders" for v in context_state().values()):
        candidates = design_candidates()
        if candidates:
            text = (f"No governed design yet. Design document candidates: {', '.join(candidates)}. Ask the human which one(s) "
                    "are the design, then assess and map them (AGENTS.md -> Bootstrap behavior; skill gtt-bootstrap).")
        else:
            text = ("No governed design yet and no design document. Ask the human for the design document(s) to use; if there "
                    "is none, start the Initial Design Questionnaire: bash .gtt/scripts/gtt-template.sh materialize "
                    "initial-design-questionnaire --apply (AGENTS.md -> Bootstrap behavior; skill gtt-bootstrap).")
        return {"kind": "design", "text": text,
                "human": "Open the project in the Primary ADE and write anything: its first answer starts the design - "
                         "from your document, or through the guided questionnaire."}
    return None


def cmd_next_action(args):
    found = next_action(getattr(args, "session_start", False))
    if args.json:
        emit({"schema": 1, "kind": "gtt-next-action", "next_action": found, "authority": "none - what GTT is waiting on"})
    elif found:
        print(found["text"])
    return 0


def cmd_detect(args):
    engine, domain = os.path.isdir(".gtt"), os.path.isdir("gtt-domain")
    layout = None
    overlays = {}
    if os.path.isfile(gm.MANIFEST):
        m = gm.load()
        layout = gm.layout_version(m)
        overlays = gm.overlays(m)
    ctx = context_state()
    if not engine:
        state = "no-gtt"
    elif os.path.isfile(FROZEN):
        state = "frozen"
    elif all(v == "no-placeholders" for v in ctx.values()):
        state = "populated"
    else:
        state = "virgin"
    candidates = design_candidates()
    has_brief = bool(glob.glob("SOURCE-BRIEF.*"))
    tpl = gm.templates(gm.load()).get("initial-design-questionnaire") if engine and layout else None
    offer = bool(tpl) and state == "virgin" and not candidates and not has_brief
    review = gm.templates(gm.load()).get("design-assessment") if engine and layout else None
    assess = bool(review) and state == "virgin" and bool(candidates) and not has_brief
    out = {"schema": 1, "kind": "gtt-project-detection", "state": state,
           "gtt": {"engine": engine, "domain": domain, "scaffold_layout": layout,
                   "bootstrap": release()["bootstrap"] if engine else None},
           "catalog": bool(overlays) and all(os.path.exists(o["path"]) for o in overlays.values()) and not os.path.isfile(".gtt/ade.json"),
           "frozen": frozen_since(), "context": ctx,
           "design_sources": {"candidates_at_root": candidates, "source_brief": has_brief,
                              "multiple": len(candidates) > 1,
                              "resolution": {"required": len(candidates) > 1, "options": ["CONSOLIDATE", "KEEP_AS_SOURCES"],
                                             "decided_by": "the human; never inferred from file order, name or size"},
                              "note": "candidates only; which one is authoritative is a human decision (Confirmation A)"},
           "assessment": {"offer": assess, "operation": "template.materialize", "template": "design-assessment",
                          "working_copy": review["materialize_to"] if review else None,
                          "working_copy_exists": bool(review) and os.path.isfile(review["materialize_to"]),
                          "verdicts": ["STRONG", "ADEQUATE", "POOR"],
                          "think_depth": think_state(think_copy() if engine and layout else None),
                          "note": "the Primary ADE writes it; a POOR design is strengthened before it is used as a source"},
           "questionnaire": {"offer": offer, "operation": "template.materialize", "template": "initial-design-questionnaire",
                             "working_copy": tpl["materialize_to"] if tpl else None,
                             "working_copy_exists": bool(tpl) and os.path.isfile(tpl["materialize_to"]),
                             "think_depth": "recorded in the questionnaire working copy when there is no Design Assessment",
                             "state": elicitation_state()["state"] if engine and layout else "absent"},
           "ade_configured": os.path.isfile(".gtt/ade.json"),
           "methodology": {k: current_profile()[k] for k in ("profile", "source", "language")}}
    if args.json:
        emit(out)
    else:
        print(f"state: {state}; frozen: {out['frozen'] or 'no'}; design candidates: {', '.join(candidates) or 'none'}; "
              f"questionnaire offered: {offer}; design assessment offered: {assess}"
              + ("; several documents: the human chooses CONSOLIDATE or KEEP_AS_SOURCES" if len(candidates) > 1 else ""))
    return 0


# ----------------------------------------------------------- status / session

def change_request_state():
    path = "gtt-domain/change-request.md"
    if not os.path.isfile(path):
        return "missing"
    with open(path, encoding="utf-8") as handle:
        return "empty" if re.search(r"(?m)^Change: <", handle.read()) else "legacy"   # a 1.22 desk not migrated: gtt-inbox.sh migrate


def proposals():
    try:
        return sorted(f for f in os.listdir("gtt-domain/proposals") if f != "README.md")
    except OSError:
        return []


def observations():
    """Open observations, by level - what the work did against the frozen design. Status observes now, in
    memory (the backlog is written only by `observe`): a dependency an agent added through the shell, with
    no file-tool hook to notice it, is counted the moment anyone asks."""
    ledger = None
    try:
        import gtt_observe
        if gtt_observe.baseline().get("frozen"):
            signals, _, _ = gtt_observe.collect()
            ledger = gtt_observe.load_ledger()
            gtt_observe.correlate(ledger, signals)
    except (Exception, SystemExit):
        ledger = None
    if ledger is None:
        ledger = read_json("gtt-domain/governance-backlog.json") or {}
    live = [i for i in ledger.get("items", []) if i.get("status") in ("open", "deferred", "rejected")]
    out = {level.lower(): sum(1 for i in live if i.get("level") == level) for level in ("NOTICE", "WARNING", "GOVERNANCE", "BLOCKING")}
    out["stopping"] = sum(1 for i in live if (i.get("level") == "BLOCKING" and i.get("status") == "open") or i.get("status") == "rejected")
    return out


def governance():
    findings, state = gp.run_checks()
    gaps = state["gaps"]
    count = lambda kind: sum(1 for g in gaps if g["kind"] == kind)
    return {"gaps": {"open": count("OPEN"), "blocking": count("BLOCKING"), "resolved": count("RESOLVED")},
            "unresolved_conflicts": sum(1 for t in state["tags"] if t[2] == "CONFLICTO"),
            "proposals_in_governed_context": sum(1 for t in state["tags"] if t[2] == "PROPUESTA"),
            "provenance_policy": state["policy"], "provenance_findings": {"fail": len(findings.fails()),
                                                                             "warn": len(findings.items) - len(findings.fails())},
            "pending_proposals": proposals(), "change_request": change_request_state(), "observations": observations(),
            "working_agreements": {"team": sum(1 for a in state["agreements"] if a["scope"] == "team"),
                                   "user": sum(1 for a in state["agreements"] if a["scope"] == "user")}}


def run_validation():
    rc, out, err = sh(".gtt/scripts/gtt-validate.sh")
    checks, messages = [], []
    for line in out.splitlines():
        # the summary lines gtt-validate.sh prints per check are fixed-width ("PASS" + 15 spaces, ...); the detail
        # lines a failing check adds start with the level and TWO spaces and must not be mistaken for checks
        m = re.match(r"^(PASS {15}|FAIL {15}|SKIPPED {12}|CANNOT-DETERMINE {3})(\S.*)$", line)
        if m:
            checks.append({"result": m.group(1).strip().lower(), "check": m.group(2).strip()})
        elif re.match(r"^(FAIL|WARN) {2,}\S", line):
            messages.append(line.strip())
    result = "pass" if rc == 0 else "fail"
    return {"schema": 1, "kind": "gtt-validation", "result": result, "exit_code": rc, "checks": checks,
            "failing": [c["check"] for c in checks if c["result"] == "fail"], "messages": messages}, rc


def cmd_validation(args):
    out, rc = run_validation()
    if args.json:
        emit(out)
    else:
        for c in out["checks"]:
            print(f"{c['result'].upper():18} {c['check']}")
    return rc


def selected_summary():
    data = read_json(SELECTED) or {"sources": []}
    findings = gp.Findings()
    manifest = gp.load_sources(findings)
    return {"selected": len(data["sources"]), "declared": len(manifest["sources"]) if manifest else 0,
            "policy": manifest["policy"] if manifest else "none"}


def development_method():
    """The development method in force (Method Governance): the Method Lock, else the setup answer, else OPEN."""
    try:
        import gtt_method
        force = gtt_method.in_force()
        lock = gtt_method.lock_view()
        return dict(force, locked_by=lock["locked_by"], verification=lock["verification"],
                    authority="the Method Lock in gtt-domain/context/architecture.md; the setup answer is never authority")
    except Exception as exc:                          # status never fails because of one view
        return {"error": str(exc)[:200]}


def cmd_status(args):
    cur = current_profile()
    val = None
    if args.with_validation:
        val, _ = run_validation()
    out = {"schema": 1, "kind": "gtt-status",
           "bootstrap": dict(release()["bootstrap"], scaffold_layout=gm.layout_version(gm.load())),
           "ade": ade_json("state"),
           "methodology": {"profile": cur["profile"], "source": cur["source"], "language": cur["language"]},
           "development_method": development_method(),
           "sources": selected_summary(),
           "governance": governance(),
           "freeze": {"frozen": os.path.isfile(FROZEN), "since": frozen_since()},
           "validation": val or {"run": False, "operation": "validation.run", "note": "pass --with-validation to run it"},
           "session": {"file": "gtt-domain/session.md", "exists": os.path.isfile("gtt-domain/session.md"),
                       "authority": "none - derived operational state"}}
    if args.json:
        emit(out)
    else:
        b = out["bootstrap"]
        print(f"{b['id']} {b['version']}; profile {cur['profile']}; frozen: {out['freeze']['frozen']}; "
              f"gaps open/blocking: {out['governance']['gaps']['open']}/{out['governance']['gaps']['blocking']}")
    return 0


def git(*args):
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def stories(status):
    path = "gtt-domain/backlog.md"
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().replace("\r\n", "\n").split("\n")
    out = []
    for i, line in enumerate(lines):
        if line.startswith("##### STORY-") and any(re.match(r"^\s*- \*\*Status:\*\* " + status + r"\s*$", l) for l in lines[i + 1:i + 4]):
            out.append(line[6:].strip())
    return out


def observation():
    """What the work has done against the frozen governed state, read from the governance backlog as it
    stands (session-context computes nothing: `observe` is the operation that observes). Signals only."""
    try:
        import gtt_observe
        ledger = gtt_observe.load_ledger()
        items = [i for i in ledger["items"] if i["status"] in gtt_observe.OPEN_STATES]
        return {"authority": "none", "note": "signals derived from the project; never decisions",
                "baseline": gtt_observe.baseline(), "operation": "observe",
                "open": [{k: i[k] for k in ("id", "level", "rule", "artifact", "status", "guards")} for i in items],
                "stopping": [i["id"] for i in items if gtt_observe.stops(i)]}
    except (Exception, SystemExit) as exc:
        return {"authority": "none", "error": str(exc)}


def cmd_session(args):
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    dirty = git("status", "--porcelain")
    recent = git("log", "-5", "--format=%h %s")
    cur = current_profile()
    ctx_files = sorted(glob.glob("gtt-domain/context/*.md"))
    out = {"schema": 1, "kind": "gtt-session-context", "authority": "none", "operational_only": True,
           "markers": ["operational-only", "NOT authority", "NOT evidence", "NOT a decision record", "NOT a grounding source"],
           "precedence": "gtt-domain/context/ (L0) > gtt-domain/adr/ (L1) > gtt-domain/backlog.md > this",
           "derived_from": "repository state at generation time; never from an agent's recollection",
           "freeze": {"frozen": os.path.isfile(FROZEN), "since": frozen_since()},
           "change_request": change_request_state(),
           "proposals": proposals(),
           "validation": {"operation": "validation.run", "result": None,
                          "note": "session-context does not execute validation; run validation.run"},
           "git": {"available": branch is not None, "branch": branch,
                   "uncommitted_paths": len(dirty.splitlines()) if dirty else 0,
                   "recent_commits": recent.splitlines() if recent else []},
           "operational": {"ade": ade_json("state"), "methodology": {"profile": cur["profile"], "language": cur["language"]},
                           "stories_in_progress": stories("In Progress"), "stories_blocked": stories("Blocked"),
                           "stories_planned": stories("Planned") + stories("Ready") + stories("Undesigned") + stories("Proposed"),
                           "observation": observation(),
                           "elicitation": elicitation_state(),
                           "governance": governance()},
           "artifacts": {"governed_context": ctx_files,
                         "adrs": sorted(glob.glob("gtt-domain/adr/ADR-[0-9]*.md")),
                         "backlog": "gtt-domain/backlog.md", "proposals_dir": "gtt-domain/proposals/",
                         "identity_index": ".gtt/index/artifacts.json"}}
    emit(out) if args.json else print("\n".join(f"{k}: {v}" for k, v in out.items() if k in ("freeze", "change_request", "proposals")))
    return 0


# ------------------------------------------------------------- export / clean

def ownership():
    policy = read_json(os.path.join(CONTRACT, "export-policy.json"))
    if policy is None:
        die(f"{CONTRACT}/export-policy.json missing")
    static = [e["pattern"] for e in policy["ownership"]["static"]]
    owned = ade_json("owned")
    surfaces = owned.get("surfaces", []) if isinstance(owned, dict) else []
    clean = sorted({s["path"] for s in surfaces if s["status"] == "unmodified"})
    confirm = sorted({s["path"] + f"  ({s['status']}, {s['basis']})" for s in surfaces if s["status"] in ("modified", "unrecorded")})
    return policy, static, clean, confirm, owned


def cmd_export_policy(args):
    policy, static, clean, confirm, owned = ownership()
    out = {"schema": 1, "contract_version": policy["contract_version"], "kind": "gtt-export-policy",
           "clean_export": {"creates": policy["export"]["clean"]["creates"], "include": ["**"],
                            "exclude": static + clean, "exclude_static": static, "exclude_from_ledger": clean,
                            "requires_confirmation": confirm},
           "ownership": policy["ownership"], "ade_state_configured": bool(owned.get("configured", True)) if isinstance(owned, dict) else False,
           "note": "everything not matched belongs to the host project; ADE directories are never matched by name"}
    emit(out) if args.json else print("\n".join(out["clean_export"]["exclude"]))
    return 0


def cmd_clean_plan(args):
    policy, static, clean, confirm, _ = ownership()
    out = {"schema": 1, "kind": "gtt-clean-plan", "removes_nothing": True,
           "would_remove": static + clean, "plus": policy["clean"]["plus"],
           "requires_confirmation": confirm, "confirmation": policy["clean"]["confirmation"],
           "keeps": policy["clean"]["keeps"],
           "distinct_from": "export --clean, which creates a separate delivery artifact and leaves this project untouched",
           "ade_operations": ["ade.remove"]}
    emit(out) if args.json else print("\n".join(out["would_remove"]))
    return 0


# ------------------------------------------------------------------ recovery

def snapshot():
    rel = release()
    cur = current_profile()
    ade = read_json(".gtt/ade.json") or {}
    sel = read_json(SELECTED) or {"sources": []}
    return {"schema": 1, "contract_version": read_json(os.path.join(CONTRACT, "recovery.json"))["contract_version"],
            "kind": "gtt-recovery-snapshot",
            "bootstrap": rel["bootstrap"], "compatibility": rel["compatibility"],
            "ade": {"primary": ade.get("primary"), "participating": ade.get("participating", []), "excluded": ade.get("excluded", []),
                    "configured": bool(ade)},
            "methodology": {"profile": cur["profile"], "language": cur["language"]},
            "sources": {"selected": sel["sources"]},
            "operational": {"frozen": os.path.isfile(FROZEN), "frozen_marker_time": frozen_since()},
            "recovery": {"created_at": now(), "note": "GTT configuration only; the governed domain content lives in version control",
                         "restore_rules": "recovery.json"}}


def cmd_recovery(args):
    if args.action == "snapshot":
        snap = snapshot()
        if args.output:
            if os.path.exists(args.output):
                die(f"{args.output} exists; snapshots are never overwritten.", 1)
            write_json(args.output, snap)
            print(f"snapshot written: {args.output}")
        else:
            emit(snap)
        return 0
    spec = read_json(os.path.join(CONTRACT, "recovery.json"))
    snap = read_json(args.snapshot)
    if snap is None:
        die(f"snapshot not readable: {args.snapshot}", 1)
    rel = release()["bootstrap"]
    refusals = []
    for key in spec["snapshot"]["required"]:
        if key not in snap:
            refusals.append(f"snapshot lacks required field `{key}`")
    if not refusals:
        if snap["kind"] != spec["snapshot"]["kind"]:
            refusals.append("not a gtt-recovery-snapshot")
        if snap["schema"] > 1:
            refusals.append(f"snapshot schema {snap['schema']} is newer than this Bootstrap understands")
        if snap["bootstrap"]["id"] != rel["id"]:
            refusals.append(f"snapshot was produced by `{snap['bootstrap']['id']}`, not `{rel['id']}`")
        order = profiles()["strictness_order"]
        prof = snap["methodology"]["profile"]
        if prof not in order:
            refusals.append(f"snapshot names an unknown profile `{prof}`")
        elif os.path.isfile(FROZEN) and order.index(prof) < order.index(current_profile()["profile"]):
            refusals.append("the project is frozen and the snapshot would relax the methodology profile")
    if refusals:
        for r in refusals:
            print("REFUSED: " + r, file=sys.stderr)
        print("Nothing was written.", file=sys.stderr)
        return 1
    plan = []
    if not os.path.exists(METHOD):
        plan.append(("write", METHOD, {"schema": 1, "profile": snap["methodology"]["profile"],
                                       "language": snap["methodology"]["language"], "set_at": now(), "restored": True}))
    else:
        plan.append(("keep", METHOD, "already exists - never overwritten"))
    if not os.path.exists(SELECTED) and snap["sources"]["selected"]:
        plan.append(("write", SELECTED, {"schema": 1, "sources": snap["sources"]["selected"]}))
    elif os.path.exists(SELECTED):
        plan.append(("keep", SELECTED, "already exists - never overwritten"))
    ade = snap["ade"]
    if ade.get("configured") and not os.path.exists(".gtt/ade.json"):
        plan.append(("ade", ".gtt/ade.json", ade))
    for kind, target, detail in plan:
        print(f"  {kind.upper():6} {target}" + (f"   ({detail})" if isinstance(detail, str) else ""))
    print("  NOTE   the freeze marker is never restored: freeze is a human act")
    if not args.apply:
        print("(dry run - nothing written; re-run with --apply)")
        return 0
    for kind, target, detail in plan:
        if kind == "write":
            write_json(target, detail)
        elif kind == "ade":
            if not args.frm:
                print("  ADE state needs --from <catalog> to re-install the recorded ADEs; skipped (run ade.install yourself)")
                continue
            rc, out, err = sh(".gtt/scripts/gtt-ade.sh", "install", "--from", args.frm, "--participating",
                              ",".join(detail["participating"]), "--primary", detail["primary"], "--apply")
            sys.stdout.write(out); sys.stderr.write(err)
            if rc != 0:
                return rc
    print("restored. Next: validation.run")
    return 0


# ---------------------------------------------------------------------- main

def build_parser():
    parser = argparse.ArgumentParser(prog="gtt-project.sh", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("detect"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_detect)
    p = sub.add_parser("think"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_think)
    p = sub.add_parser("think-plan"); p.add_argument("action", nargs="?", choices=["show", "skip"], default="show")
    p.add_argument("step", nargs="?"); p.add_argument("--by"); p.add_argument("--reason"); p.add_argument("--json", action="store_true")
    p.add_argument("--gate", action="store_true"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_think_plan)
    p = sub.add_parser("next-action"); p.add_argument("--json", action="store_true"); p.add_argument("--session-start", action="store_true"); p.set_defaults(func=cmd_next_action)
    p = sub.add_parser("inbox-line"); p.add_argument("--triage", action="store_true")
    p.set_defaults(func=lambda a: (print(inbox_line(a.triage)), 0)[1])
    p = sub.add_parser("elicitation"); p.add_argument("--json", action="store_true"); p.add_argument("--next-action", action="store_true")
    p.set_defaults(func=cmd_elicitation)
    p = sub.add_parser("status"); p.add_argument("--json", action="store_true"); p.add_argument("--with-validation", action="store_true"); p.set_defaults(func=cmd_status)
    p = sub.add_parser("session"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_session)
    p = sub.add_parser("validation"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_validation)
    p = sub.add_parser("interaction"); p.add_argument("--key"); p.set_defaults(func=cmd_interaction)
    p = sub.add_parser("next-id"); p.add_argument("--kind", required=True, choices=sorted(ID_KINDS)); p.add_argument("--requested")
    p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_next_id)
    p = sub.add_parser("profile"); p.add_argument("action", choices=["get", "set"]); p.add_argument("--json", action="store_true")
    p.add_argument("--profile"); p.add_argument("--language"); p.add_argument("--adr"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_profile)
    p = sub.add_parser("source"); p.add_argument("action", choices=["select", "list"]); p.add_argument("--json", action="store_true")
    p.add_argument("--path"); p.add_argument("--type"); p.add_argument("--version"); p.add_argument("--by"); p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_source)
    p = sub.add_parser("export-policy"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_export_policy)
    p = sub.add_parser("clean-plan"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_clean_plan)
    p = sub.add_parser("recovery"); p.add_argument("action", choices=["snapshot", "restore"]); p.add_argument("--output")
    p.add_argument("--snapshot"); p.add_argument("--from", dest="frm"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_recovery)
    return parser


def main(argv):
    if not os.path.isdir(".gtt"):
        die("run from the project root (no .gtt/ directory here)")
    args = build_parser().parse_args(argv)
    if args.command == "source" and args.action == "select" and not (args.path and args.type):
        die("source select needs --path and --type")
    if args.command == "recovery" and args.action == "restore" and not args.snapshot:
        die("recovery restore needs --snapshot")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
