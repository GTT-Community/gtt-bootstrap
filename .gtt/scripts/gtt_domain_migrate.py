#!/usr/bin/env python3
"""GTT - bring a project's gtt-domain up to the structure of the Bootstrap it now runs, without losing anything, and only when asked.

  gtt_domain_migrate.py status [--json]        read-only: is a migration waiting, and why (text mode lists what the validator finds)
  gtt_domain_migrate.py check  --apply [--from V]  the update calls it with the version the project WAS on: it stamps `pending` only when a
                                               release DECLARED a structural change (contract/domain.json format_changes) after V, else `clean`
  gtt_domain_migrate.py begin  [--to DIR]      zip of gtt-domain/ and docs/ideas/, the invariants before, state `in-progress`
  gtt_domain_migrate.py verify [--json]        compare the work with the invariants taken at `begin`, then check-backlog
  gtt_domain_migrate.py done                   verify; when it holds, stamp the state `done` at the current format
  gtt_domain_migrate.py dismiss                the human decided nothing is to be migrated: stamp it, it is not asked again
  gtt_domain_migrate.py restore [--apply]      put gtt-domain/backlog.md back from the zip of the last `begin`

`gtt update` replaces the Bootstrap package and never touches gtt-domain/: it is the project's, not the package's. A release that
changes the STRUCTURE of what gtt-domain must contain declares it (format_changes); one that changes nothing there asks nothing, and a
backlog with validator findings is work to do, not a migration. When a release did declare one, judging whether this project needs it
takes reading its content, so it is the agent's, and the agent ASKS the human before it changes anything: the scripts compute and
guard, the agent evaluates, the human decides, the agent writes. It reaches the agent as the next action (`gtt-project.sh next-action`)
and, for a session already open, at the person's next message; the procedure is in .gtt/docs/agents/operations.md -> *Domain migration*.

What the migration may write: gtt-domain/backlog.md, and nothing else. A Story is the agent's (rewrite, split, define
`Implements:` and `Done when:`). An Epic is the human's: its heading block (Goal, Scope, Out of Scope, `Approved`) must stay
byte for byte what it was; if the new format needs something from an Epic it is a proposal, never an edit. Everything
governed (context, ADRs, registered proposals, ideas) must be identical when the project is frozen; the hooks already
refuse those writes, `verify` proves it. A Story is never dropped and never changes status while it moves.

Exit 0 = ok, 1 = verify refused or nothing to restore, 2 = cannot run.
"""

import argparse
import hashlib
import json
import re
import os
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import gtt_backlog  # noqa: E402

CONTRACT = ".gtt/contract/domain.json"
STATE = ".gtt/domain-migration.json"
NOTICE = ".gtt/local/domain-notice.json"      # what the per-message hook last computed and to which sessions it said it
BACKLOG = gtt_backlog.DEFAULT
FROZEN = "gtt-domain/.frozen"
METHOD = ".gtt/methodology.json"
RELEASE = ".gtt/contract/release.json"

MSG = {
    "en": {
        "needed": "The Bootstrap changed what the backlog must carry since your version ({frm}): {why}. Your agent will evaluate whether this project needs it and will ask you before changing anything.",
        "order": ("The Bootstrap changed what the backlog must carry since this project's version ({frm}): {why}. This is an EVALUATION, never an order to rewrite. "
                  "Run `bash .gtt/scripts/gtt-domain-migrate.sh status` (it lists what the validator finds in this backlog) and judge whether this project's Stories need it. "
                  "Then say what you found in one line and ASK the human whether they want it done; never begin on your own and never in the middle of a Story. "
                  "Only if they agree: `bash .gtt/scripts/gtt-domain-migrate.sh begin` (it makes the zip and the invariants), rewrite only Stories in gtt-domain/backlog.md "
                  "(never an Epic, never anything governed: an Epic's need is a proposal), then `gtt-domain-migrate.sh done`. "
                  "If nothing needs it, or they decline: `gtt-domain-migrate.sh dismiss` and it is not asked again. When it is done, tell the human to keep a copy of the zip somewhere else too."),
        "resume": ("A migration of the gtt-domain was begun and not finished. Do not continue it on your own: tell the human in one line and ASK whether to continue it "
                   "(rewrite only Stories, then `bash .gtt/scripts/gtt-domain-migrate.sh done`) or to undo it (`gtt-domain-migrate.sh restore --apply`, then `dismiss` if nothing is needed). "
                   "AGENTS.md -> *Domain migration*."),
        "in_progress": "a migration was begun and not finished",
        "human": "Your agent will evaluate whether your gtt-domain needs the new structure and will ask you before it changes anything.",
        "dismissed": "gtt-domain-migrate: dismissed - nothing is migrated and it is not asked again until a release declares another structural change.",
        "backup": "Backup: {zip}\n  Keep a copy of it somewhere else too (another disk or the cloud): it is the only thing that survives losing this machine.",
        "restore": "To undo: bash .gtt/scripts/gtt-domain-migrate.sh restore --apply",
    },
    "es": {
        "needed": "El Bootstrap cambió lo que el backlog debe llevar desde tu versión ({frm}): {why}. Tu agente evaluará si este proyecto lo necesita y te preguntará antes de cambiar nada.",
        "order": ("El Bootstrap cambió lo que el backlog debe llevar desde la versión de este proyecto ({frm}): {why}. Esto es una EVALUACIÓN, nunca una orden de reescribir. "
                  "Ejecuta `bash .gtt/scripts/gtt-domain-migrate.sh status` (lista lo que el validador encuentra en este backlog) y juzga si las Stories de este proyecto lo necesitan. "
                  "Luego di en una línea lo que encontraste y PREGUNTA a la persona si quiere que se haga; nunca empieces por tu cuenta ni a mitad de una Story. "
                  "Solo si acepta: `bash .gtt/scripts/gtt-domain-migrate.sh begin` (hace el zip y las invariantes), reescribe solo Stories en gtt-domain/backlog.md "
                  "(nunca un Epic ni nada gobernado: lo que pida un Epic es una propuesta) y luego `gtt-domain-migrate.sh done`. "
                  "Si nada lo necesita, o ella no quiere: `gtt-domain-migrate.sh dismiss` y no se vuelve a preguntar. Al terminar, dile que guarde también una copia del zip en otro lugar."),
        "resume": ("Una migración del gtt-domain se empezó y no se terminó. No la continúes por tu cuenta: dilo en una línea y PREGUNTA a la persona si se continúa "
                   "(reescribe solo Stories y luego `bash .gtt/scripts/gtt-domain-migrate.sh done`) o se deshace (`gtt-domain-migrate.sh restore --apply`, y luego `dismiss` si nada hace falta). "
                   "AGENTS.md -> *Domain migration*."),
        "in_progress": "se empezó una migración y no se terminó",
        "human": "Tu agente evaluará si tu gtt-domain necesita la estructura nueva y te preguntará antes de cambiar nada.",
        "dismissed": "gtt-domain-migrate: descartada - no se migra nada y no se vuelve a preguntar hasta que un release declare otro cambio de estructura.",
        "backup": "Respaldo: {zip}\n  Guarda también una copia en otro lugar (otro disco o la nube): es lo único que sobrevive si pierdes esta máquina.",
        "restore": "Para deshacer: bash .gtt/scripts/gtt-domain-migrate.sh restore --apply",
    },
}


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


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lang():
    value = (read_json(METHOD) or {}).get("language")
    return "es" if value == "es" else "en"


def contract():
    data = read_json(CONTRACT)
    if not data:
        print(f"gtt-domain-migrate: {CONTRACT} is missing or unreadable; this Bootstrap does not carry the migration.", file=sys.stderr)
        sys.exit(2)
    return data


def bootstrap_version():
    return ((read_json(RELEASE) or {}).get("bootstrap") or {}).get("version", "?")


def migrations_dir():
    return os.path.join(".gtt", "local", "migrations")


def frozen():
    return os.path.isfile(FROZEN)


# --- the backlog as data -----------------------------------------------------------------------------------------

def backlog_lines():
    with open(BACKLOG, encoding="utf-8", newline="") as handle:
        return handle.read().replace("\r\n", "\n").split("\n")


def epic_heads(lines, epics):
    """The block of an Epic above its Stories (heading, Goal, Scope, `Approved`...): the human's, so it is hashed whole."""
    heads = {}
    for epic in epics:
        block = [lines[epic["line"] - 1]]
        for line in lines[epic["line"]:]:
            if line.startswith("#") or line.startswith("---"):
                break
            block.append(line)
        heads[epic["id"]] = sha("\n".join(block).strip().encode("utf-8"))
    return heads


def governed_files():
    """Every file the migration must never change once the design is frozen."""
    found = {}
    for top, keep in (("gtt-domain/context", lambda p: True),
                      ("gtt-domain/adr", lambda p: "/drafts/" not in p.replace(os.sep, "/") + "/"),
                      ("gtt-domain/proposals", lambda p: os.path.basename(p).startswith("PROP-")),
                      ("docs/ideas", lambda p: os.path.basename(p).startswith("IDEA-"))):
        for base, _dirs, names in os.walk(top):
            for name in names:
                path = os.path.join(base, name)
                if keep(path):
                    found[path.replace(os.sep, "/")] = sha_file(path)
    return found


def invariants():
    stories, epics = gtt_backlog.parse(BACKLOG)
    lines = backlog_lines()
    return {
        "schema": 1, "at": now(), "frozen": frozen(),
        "epics": {e["id"]: {"status": gtt_backlog.normal(e["status"]), "head": h} for e, h in
                  ((e, epic_heads(lines, [e])[e["id"]]) for e in epics)},
        "stories": {s["id"]: {"status": gtt_backlog.normal(s["status"]), "epic": s["epic"]} for s in stories},
        "governed": governed_files(),
    }


# --- does it need a migration ---------------------------------------------------------------------------------------

def run_check_backlog():
    proc = subprocess.run(["bash", os.path.join(HERE, "gtt-check-backlog.sh"), BACKLOG], capture_output=True, text=True)
    text = (proc.stdout + proc.stderr).strip()
    marker = "gtt-check-backlog: FAILED - "          # the findings; the closing `FAILED` and the explanation are not
    return proc.returncode, [line.strip()[len(marker):] for line in text.splitlines() if line.strip().startswith(marker)]


def split_findings(lines):
    """(the agent's, the human's). A finding that names an Epic and no Story - a status, a design file, a goal - is about what the
    human owns: the agent cannot fix it and a migration must not wait for it. Anything else blocks, as before."""
    epic_only = re.compile(r"^(Epic\b|.*\bEPIC-\d+\b)")
    mine, theirs = [], []
    for line in lines:
        (theirs if epic_only.match(line) and "STORY-" not in line else mine).append(line)
    return mine, theirs


def vtuple(version):
    try:
        return tuple(int(x) for x in str(version).split("-")[0].split(".")[:3])
    except (ValueError, TypeError):
        return None


def changes_between(spec, frm, to):
    """The structural changes a release declared (format_changes) in (frm, to]. Empty when a version is unknown: nothing is guessed."""
    a, b = vtuple(frm), vtuple(to)
    if a is None or b is None:
        return []
    return [c for c in spec.get("format_changes", []) if vtuple(c.get("since")) is not None and a < vtuple(c["since"]) <= b]


def change_texts(changes):
    return [c.get(lang()) or c.get("en") or "" for c in changes]


def evaluate():
    """{needed, state, why, from, changes, epics, format, current}. Read-only and cheap: it reads the state file and counts Epics.
    It never runs the validator: a backlog with findings is work, not a migration. A migration is asked of the agent only when a
    release DECLARED a change of structure between the version the project was on and the one it runs now (`check --from`)."""
    spec = contract()
    current = int(spec.get("format", 1))
    state = read_json(STATE) or {}
    out = {"schema": 1, "kind": "gtt-domain-status", "format": state.get("format"), "current": current,
           "state": state.get("status"), "needed": False, "why": [], "epics": 0, "bootstrap": bootstrap_version(),
           "from": state.get("from"), "changes": state.get("changes") or []}
    if not os.path.isfile(BACKLOG):
        return out
    try:
        _stories, epics = gtt_backlog.parse(BACKLOG)
    except OSError:
        return out
    out["epics"] = len(epics)
    if state.get("status") == "in-progress":
        out.update(needed=True, why=[MSG[lang()]["in_progress"]])
    elif state.get("status") == "pending" and epics:
        out.update(needed=True, why=change_texts(state.get("changes") or []))
    return out


def order_text(result):
    m = MSG[lang()]
    if result.get("state") == "in-progress":
        return m["resume"]
    return m["order"].format(frm=result.get("from") or "?", why="; ".join(result.get("why") or []))


def stamp_new(session_start=False):
    """A project that begins with no Epic is stamped `clean` at the current format, so that an ordinary failure later is never
    mistaken for a legacy one. Called first by next-action: a new project is in THINK or the questionnaire, which return earlier."""
    try:
        spec = contract()
    except SystemExit:
        return None
    state = read_json(STATE)
    if state is None and session_start and os.path.isfile(BACKLOG):
        try:
            _s, epics = gtt_backlog.parse(BACKLOG)
        except OSError:
            return None
        if not epics:
            write_json(STATE, {"schema": 1, "format": int(spec.get("format", 1)), "status": "clean", "at": now(),
                               "bootstrap": bootstrap_version()})
            return True
    return None


def action(session_start=False):
    """The next action for the agent, or None. Writes the `clean` stamp of a project with no Epic (see stamp_new)."""
    if stamp_new(session_start):
        return None
    result = evaluate()
    if not result["needed"]:
        return None
    return {"kind": "domain-migration", "text": order_text(result), "human": MSG[lang()]["human"]}


def prompt_notice(session):
    """The same evaluation for a session that is already open: the next action reaches only a session that STARTS, and the one open
    while `gtt update` ran is the one that needs it. Said once per session (again only if the text changes), at the person's next
    message. Reading the state file is all it costs. Silent when no release declared a change for this project."""
    try:
        result = evaluate()
    except SystemExit:
        return ""
    if not result["needed"]:
        return ""
    text = order_text(result)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    cache = read_json(NOTICE) or {}
    shown = cache.setdefault("shown", {})
    if shown.get(session) == digest:
        return ""
    shown[session] = digest
    for old in list(shown)[:-5]:
        shown.pop(old)
    write_json(NOTICE, {"shown": shown})
    return text


# --- commands ----------------------------------------------------------------------------------------------------

def cmd_status(args):
    result = evaluate()
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if result["needed"]:
        print(MSG[lang()]["needed"].format(frm=result.get("from") or "?", version=result["bootstrap"], why="; ".join(result["why"])))
        code, lines = run_check_backlog()          # what the validator finds now: the evidence for the agent's judgment, only when asked
        mine, theirs = split_findings(lines) if code else ([], [])
        for line in mine[:8]:
            print(f"  finds   {line}")
        if len(mine) > 8:
            print(f"  finds   (+{len(mine) - 8} more Story findings)")
        for line in theirs[:3]:
            print(f"  epic    {line}   (an Epic is the human's: a proposal, never an edit)")
        if not mine and not theirs:
            print("  the validator finds nothing in this backlog: likely nothing to rewrite")
    else:
        print("gtt-domain-migrate: nothing to migrate" + (f" (format {result['format']})" if result["format"] else ""))
    return 0


def cmd_check(args):
    """The update calls this with the version the project WAS on (--from): the changes a release declared since then decide whether
    anything is asked. Without --from it compares with the version stamped last time; with neither, nothing is guessed."""
    spec = contract()
    state = read_json(STATE) or {}
    if args.apply and state.get("status") != "in-progress":
        to = bootstrap_version()
        frm = args.frm or state.get("bootstrap")
        epics = 0
        try:
            epics = len(gtt_backlog.parse(BACKLOG)[1]) if os.path.isfile(BACKLOG) else 0
        except OSError:
            pass
        changes = changes_between(spec, frm, to) if epics else []
        if changes:
            write_json(STATE, {"schema": 1, "format": state.get("format", 0), "status": "pending", "at": now(), "from": frm, "to": to,
                               "bootstrap": to, "changes": changes})
        else:
            write_json(STATE, {"schema": 1, "format": int(spec.get("format", 1)), "status": "clean", "at": now(), "bootstrap": to})
    return cmd_status(args)


def cmd_dismiss(args):
    state = read_json(STATE) or {}
    if state.get("status") == "in-progress":
        print("gtt-domain-migrate: a migration is in progress: finish it (`done`) or undo it (`restore --apply`).", file=sys.stderr)
        return 1
    spec = contract()
    write_json(STATE, {"schema": 1, "format": int(spec.get("format", 1)), "status": "done", "dismissed": True, "at": now(),
                       "bootstrap": bootstrap_version()})
    print(MSG[lang()]["dismissed"])
    return 0


def zip_domain(destination):
    count = 0
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as bundle:
        for top in ("gtt-domain", "docs/ideas"):
            for base, _dirs, names in os.walk(top):
                for name in sorted(names):
                    path = os.path.join(base, name)
                    if os.path.islink(path):
                        continue
                    bundle.write(path, path.replace(os.sep, "/"))
                    count += 1
    return count


def cmd_begin(args):
    if not os.path.isfile(BACKLOG):
        print(f"gtt-domain-migrate: {BACKLOG} is missing; nothing to migrate.", file=sys.stderr)
        return 2
    folder = os.path.join(migrations_dir(), stamp())
    os.makedirs(folder, exist_ok=True)
    archive = os.path.join(folder, "gtt-domain.zip")
    files = zip_domain(archive)
    write_json(os.path.join(folder, "invariants.json"), invariants())
    copies = [archive]
    if args.to:
        target = os.path.abspath(args.to)
        if not os.path.isdir(target):
            print(f"gtt-domain-migrate: --to {args.to} is not a directory.", file=sys.stderr)
            return 2
        extra = os.path.join(target, f"gtt-domain-{os.path.basename(os.getcwd())}-{os.path.basename(folder)}.zip")
        with open(archive, "rb") as src, open(extra, "wb") as dst:
            dst.write(src.read())
        copies.append(extra)
    spec = contract()
    state = read_json(STATE) or {}
    write_json(STATE, {"schema": 1, "format": state.get("format", 0), "status": "in-progress", "at": now(),
                       "bootstrap": bootstrap_version(), "backup": archive.replace(os.sep, "/"),
                       "why": state.get("why", [])})
    text = MSG[lang()]
    print(f"gtt-domain-migrate: {files} file(s) backed up, invariants taken (format {spec.get('format', 1)}).")
    print(text["backup"].format(zip=", ".join(copies)))
    print(text["restore"])
    return 0


def latest_folder():
    base = migrations_dir()
    if not os.path.isdir(base):
        return None
    names = sorted(n for n in os.listdir(base) if os.path.isfile(os.path.join(base, n, "invariants.json")))
    return os.path.join(base, names[-1]) if names else None


def compare(before, after):
    problems, notes = [], []
    for ident, old in before["epics"].items():
        new = after["epics"].get(ident)
        if new is None:
            problems.append(f"{ident}: the Epic is gone (an Epic is the human's: propose it, never remove it)")
        elif new["head"] != old["head"]:
            problems.append(f"{ident}: the Epic's Goal, Scope or `Approved` changed (the migration copies an Epic, it never edits it)")
        elif new["status"] != old["status"]:
            problems.append(f"{ident}: the Epic's status changed {old['status']} -> {new['status']}")
    for ident in after["epics"]:
        if ident not in before["epics"]:
            problems.append(f"{ident}: a new Epic appeared (adding an Epic is the human's decision: propose it)")
    for ident, old in before["stories"].items():
        new = after["stories"].get(ident)
        if new is None:
            problems.append(f"{ident}: the Story is gone (a Story is never dropped by a migration; mark it Cancelled with the reason if it must end)")
        elif new["status"] != old["status"]:
            problems.append(f"{ident}: the Story's status changed {old['status']} -> {new['status']} (a migration moves content, not progress)")
        elif new["epic"] != old["epic"]:
            notes.append(f"{ident}: moved from {old['epic']} to {new['epic']}")
    added = [i for i in after["stories"] if i not in before["stories"]]
    if added:
        notes.append(f"{len(added)} new Story(ies): {', '.join(added[:8])}{' ...' if len(added) > 8 else ''}")
    changed = sorted(p for p, h in before["governed"].items() if after["governed"].get(p) != h)
    created = sorted(p for p in after["governed"] if p not in before["governed"])
    for path in changed + created:
        message = f"{path}: governed content {'changed' if path in before['governed'] else 'appeared'}"
        if before["frozen"] or frozen():
            problems.append(message + " (the design is frozen: only the change flow writes it)")
        else:
            notes.append(message + " (allowed before the freeze)")
    return problems, notes


def cmd_verify(args):
    folder = latest_folder()
    if folder is None:
        print("gtt-domain-migrate: no `begin` found: run `bash .gtt/scripts/gtt-domain-migrate.sh begin` first.", file=sys.stderr)
        return 2
    before = read_json(os.path.join(folder, "invariants.json"))
    try:
        after = invariants()
    except OSError as error:
        print(f"gtt-domain-migrate: cannot read the backlog: {error}", file=sys.stderr)
        return 2
    problems, notes = compare(before, after)
    code, lines = run_check_backlog()
    if code != 0:
        mine, theirs = split_findings(lines)
        problems += [f"check-backlog: {l}" for l in mine[:8]] or ([] if theirs else ["check-backlog failed"])
        if len(mine) > 8:
            problems.append(f"check-backlog: (+{len(mine) - 8} more)")
        for l in theirs[:6]:
            notes.append(f"for the human, not blocking (an Epic is theirs; if it matters, a proposal): {l}")
        if len(theirs) > 6:
            notes.append(f"for the human, not blocking: (+{len(theirs) - 6} more Epic-level findings in `gtt-check-backlog.sh`)")
    if args.json:
        print(json.dumps({"schema": 1, "kind": "gtt-domain-verify", "ok": not problems, "problems": problems, "notes": notes,
                          "backup": os.path.join(folder, "gtt-domain.zip").replace(os.sep, "/")}, indent=2, ensure_ascii=False))
    else:
        for note in notes:
            print(f"  note   {note}")
        for problem in problems:
            print(f"  REFUSED {problem}")
        if not problems:
            print("gtt-domain-migrate: verify OK - no Epic, Story or governed file was lost or altered; check-backlog passes.")
        else:
            print(f"gtt-domain-migrate: {len(problems)} problem(s). Fix them, or undo it.\n  {MSG[lang()]['restore']}")
    return 1 if problems else 0


def cmd_done(args):
    args.json = False
    if cmd_verify(args) != 0:
        return 1
    spec = contract()
    state = read_json(STATE) or {}
    write_json(STATE, {"schema": 1, "format": int(spec.get("format", 1)), "status": "done", "at": now(),
                       "bootstrap": bootstrap_version(), "backup": state.get("backup")})
    print(f"gtt-domain-migrate: done - gtt-domain is at format {spec.get('format', 1)}. The zip stays at {state.get('backup')}.")
    return 0


def cmd_restore(args):
    folder = latest_folder()
    archive = os.path.join(folder, "gtt-domain.zip") if folder else None
    if not archive or not os.path.isfile(archive):
        print("gtt-domain-migrate: there is no backup to restore from.", file=sys.stderr)
        return 1
    with zipfile.ZipFile(archive) as bundle:
        if BACKLOG not in bundle.namelist():
            print(f"gtt-domain-migrate: the backup holds no {BACKLOG}.", file=sys.stderr)
            return 1
        data = bundle.read(BACKLOG)
    if os.path.isfile(BACKLOG) and sha_file(BACKLOG) == sha(data):
        print("gtt-domain-migrate: the backlog is already what the backup holds.")
        return 0
    if not args.apply:
        print(f"gtt-domain-migrate: would put {BACKLOG} back from {archive} (dry run; re-run with --apply).")
        print("  Anything else in the zip is yours to restore by hand: the migration only ever writes the backlog.")
        return 0
    with open(BACKLOG, "wb") as handle:
        handle.write(data)
    state = read_json(STATE) or {}
    write_json(STATE, {"schema": 1, "format": state.get("format", 0), "status": "pending", "at": now(),
                       "bootstrap": bootstrap_version(), "why": ["the migration was undone"], "backup": state.get("backup")})
    print(f"gtt-domain-migrate: {BACKLOG} restored from {archive}. The migration is pending again.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="gtt-domain-migrate", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("status"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_status)
    p = sub.add_parser("check"); p.add_argument("--apply", action="store_true"); p.add_argument("--json", action="store_true")
    p.add_argument("--from", dest="frm", help="the Bootstrap version the project was on before this update"); p.set_defaults(func=cmd_check)
    p = sub.add_parser("dismiss"); p.set_defaults(func=cmd_dismiss)
    p = sub.add_parser("begin"); p.add_argument("--to"); p.set_defaults(func=cmd_begin)
    p = sub.add_parser("verify"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_verify)
    p = sub.add_parser("done"); p.set_defaults(func=cmd_done)
    p = sub.add_parser("restore"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_restore)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
