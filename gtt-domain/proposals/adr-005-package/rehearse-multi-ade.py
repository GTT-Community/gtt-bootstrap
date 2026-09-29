#!/usr/bin/env python3
"""GTT ADR-005 - rehearsal of the Multi-ADE engine and the template service.

Runs entirely in a DISPOSABLE temp directory. It never touches the project it is
pointed at and it never runs a promotion script: it builds a throw-away
"catalog" (the project plus the staged post-image files) and drives the new
engine through the lifecycle - init, validate, status, inspect, resume, update,
clean, export --clean, migration - asserting the contract of each.

  python rehearse-multi-ade.py --project .        BEFORE promotion: project + the staged package
  python rehearse-multi-ade.py --catalog .        AFTER promotion: the project as it now is

Neither mode modifies the project; both work on a temporary copy.

Exit 0 = every scenario held, 1 = at least one failed.
"""

import argparse
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

FAILS = []
COUNT = 0


def check(cond, label, detail=""):
    global COUNT
    COUNT += 1
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        FAILS.append(label)


def sh(cwd, *cmd, inp=None):
    proc = subprocess.run(["bash", *cmd], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", input=inp)
    return proc.returncode, proc.stdout + proc.stderr


def ade(cwd, *args):
    return sh(cwd, ".gtt/scripts/gtt-ade.sh", *args)


def tpl(cwd, *args):
    return sh(cwd, ".gtt/scripts/gtt-template.sh", *args)


def copy_tree(src, dst, ignore=("__pycache__", ".git")):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*ignore))


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def make_host(catalog, root, foreign=True):
    """A host project that has the portable core and the Engine, no overlay yet."""
    os.makedirs(root)
    shutil.copy2(os.path.join(catalog, "AGENTS.md"), root)
    copy_tree(os.path.join(catalog, ".gtt"), os.path.join(root, ".gtt"))
    copy_tree(os.path.join(catalog, "gtt-domain"), os.path.join(root, "gtt-domain"))
    if foreign:                       # the user's own configuration for an ADE GTT does not govern
        write(os.path.join(root, ".kiro", "user-notes.md"), "the host project's own Kiro notes\n")
        write(os.path.join(root, ".claude", "keep-me.txt"), "the host project's own Claude file\n")


def scenario_registry(cat):
    print("[registry] the ADE integration registry is read from the manifest")
    rc, out = ade(cat, "list", "--json")
    data = json.loads(out)
    ids = sorted(a["id"] for a in data["ades"])
    check(rc == 0 and ids == ["claude", "codex", "copilot", "kiro"], "four ADEs registered", out[:200])
    by = {a["id"]: a for a in data["ades"]}
    check(by["codex"]["owned"] == [], "codex owns nothing beyond the core entry point")
    check(by["claude"]["enforcement"] == "realtime-hook" and by["kiro"]["enforcement"] == "ci-gate",
          "enforcement is declared per ADE (only Claude has a real-time hook)")
    check(all(a["scaffold"] == data["layout"] for a in data["ades"]), "every overlay targets the scaffold layout")


def scenario_init(cat, tmp):
    print("[init] detect -> confirm -> primary -> install (dry run first)")
    host = os.path.join(tmp, "host")
    make_host(cat, host)
    rc, out = ade(host, "detect")
    check(rc == 0 and "candidate" in out and "not installation" in out, "detect reports candidates only")
    check(not os.path.exists(os.path.join(host, ".gtt", "ade.json")), "detect writes nothing")
    args = ["install", "--from", cat, "--participating", "claude,codex", "--primary", "claude"]
    write(os.path.join(host, ".claude", "CLAUDE.md"), "the host project's own file\n")
    rc, out = ade(host, *args, "--apply")
    check(rc == 1 and "CONFLICT" in out and ".claude/CLAUDE.md" in out, "install refuses to overwrite a file it did not install", out[-300:])
    check(not os.path.exists(os.path.join(host, ".gtt", "ade.json")) and not os.path.exists(os.path.join(host, ".claude", "rules")),
          "a conflict writes nothing at all")
    os.remove(os.path.join(host, ".claude", "CLAUDE.md"))
    rc, out = ade(host, *args)
    check(rc == 0 and "dry run" in out and "COPY" in out, "dry run plans a copy and writes nothing", out[-300:])
    check(not os.path.exists(os.path.join(host, ".gtt", "ade.json")), "dry run left no state")
    rc, out = ade(host, *args, "--apply")
    check(rc == 0, "install --apply succeeds", out[-400:])
    st = read_json(os.path.join(host, ".gtt", "ade.json"))
    check(st["primary"] == "claude" and st["participating"] == ["claude", "codex"], "primary + participating recorded")
    check(st["excluded"] == ["copilot", "kiro"], "the others are recorded as excluded", str(st["excluded"]))
    files = st["installed"]["claude"]["files"]
    check(".claude/CLAUDE.md" in files and ".claude/keep-me.txt" not in files, "ledger holds only what GTT copied")
    check(st["installed"]["codex"]["files"] == {}, "codex installs nothing beyond the core entry point")
    check(all(len(h) == 64 for h in files.values()), "ledger carries sha256 hashes")
    rc, out = ade(host, "validate")
    check(rc == 0 and "integration valid" in out, "validate passes for every participating ADE", out)
    check("WARN" in out and "kiro" in out and "not governed by GTT" in out, "a foreign ADE surface is a WARN, never silently governed", out)
    rc, out = sh(host, ".gtt/scripts/gtt-check-adapter.sh")
    check(rc == 0, "gtt-check-adapter.sh (state mode) passes", out)
    return host


def scenario_exclusion_and_reinclude(cat, host):
    print("[re-run] never drop, never reintroduce an excluded ADE, never change the primary")
    base = ["install", "--from", cat]
    rc, out = ade(host, *base, "--participating", "claude", "--primary", "claude")
    check(rc == 2 and "never drops" in out, "install refuses to drop an installed ADE", out)
    rc, out = ade(host, *base, "--participating", "claude,codex,kiro", "--primary", "claude")
    check(rc == 2 and "excluded" in out, "install refuses to reintroduce an excluded ADE", out)
    rc, out = ade(host, *base, "--participating", "claude,codex", "--primary", "codex")
    check(rc == 2 and "set-primary" in out, "install never changes the primary as a side effect", out)
    rc, out = ade(host, *base, "--participating", "claude,codex,kiro", "--primary", "claude", "--reinclude", "kiro", "--apply")
    check(rc == 0, "an explicit --reinclude adds the ADE", out[-300:])
    st = read_json(os.path.join(host, ".gtt", "ade.json"))
    check(st["participating"] == ["claude", "codex", "kiro"] and "kiro" not in st["excluded"], "state updated")
    check(".kiro/user-notes.md" not in st["installed"]["kiro"]["files"], "the host's own kiro file is not in the ledger")


def scenario_status_inspect_resume(host):
    print("[status / inspect / resume] multi-ADE state is visible and ADE-portable")
    rc, out = ade(host, "state")
    check(rc == 0 and "primary: claude" in out and "participating: claude, codex, kiro" in out, "state shows primary + participating", out)
    rc, out = ade(host, "state", "--json")
    data = json.loads(out)
    check(data["primary"] == "claude" and data["configured"], "state --json is machine-readable")
    rc, out = ade(host, "owned", "--json")
    data = json.loads(out)
    paths = {s["path"] for s in data["surfaces"]}
    check(".claude/CLAUDE.md" in paths and ".claude/keep-me.txt" not in paths, "owned lists only GTT-installed surfaces")
    check("AGENTS.md" in data["core_entry_points"], "core entry points are reported apart from ADE overlays")
    rc, out = sh(host, ".gtt/scripts/gtt-status.sh")
    check(rc == 0 and "## ADE integration" in out and "primary: claude" in out, "gtt-status.sh exposes the ADE section", out[-500:])
    check("holds no authority" in out, "the section states the Primary ADE holds no authority")
    with open(os.path.join(host, "gtt-domain", "session.md"), encoding="utf-8") as handle:
        session = handle.read()
    check("primary: claude" in session and "operational-only" in session, "session.md carries it, still operational-only")
    rc, out = sh(host, ".gtt/scripts/gtt-validate.sh")
    check("PASS               gtt-check-adapter.sh (participating" in out, "gtt-validate.sh runs the multi-ADE adapter check", out[:600])


def scenario_validate_failures(cat, tmp, host):
    print("[validate] a participating ADE with a broken integration FAILS")
    bad = os.path.join(tmp, "bad")
    shutil.copytree(host, bad)
    os.remove(os.path.join(bad, ".kiro", "steering", "gtt-guard.md"))
    rc, out = ade(bad, "validate")
    check(rc == 1 and "FAIL" in out and "kiro" in out, "missing entry point of a participating ADE fails", out)
    rc, out = sh(bad, ".gtt/scripts/gtt-check-adapter.sh")
    check(rc == 1, "gtt-check-adapter.sh exits 1")
    rc, out = sh(bad, ".gtt/scripts/gtt-validate.sh")
    check("FAIL               gtt-check-adapter.sh (participating" in out, "gtt-validate.sh reports the FAIL", out[:500])
    ok = os.path.join(tmp, "prim")
    shutil.copytree(host, ok)
    path = os.path.join(ok, ".gtt", "ade.json")
    st = read_json(path)
    st["primary"] = "copilot"
    write(path, json.dumps(st, indent=2))
    rc, out = ade(ok, "validate")
    check(rc == 1 and "not a participating ADE" in out, "a Primary outside the participating set fails", out)
    st["primary"], st["excluded"] = "claude", ["claude"]
    write(path, json.dumps(st, indent=2))
    rc, out = ade(ok, "validate")
    check(rc == 1 and "both participating and excluded" in out, "participating and excluded at once fails", out)


def scenario_primary(host):
    print("[primary] a workflow identifier, changeable only among participating ADEs")
    rc, out = ade(host, "set-primary", "copilot")
    check(rc == 2 and "not participating" in out, "the Primary must be a participating ADE", out)
    rc, out = ade(host, "set-primary", "codex")
    check(rc == 0 and "no authority moves" in out and read_json(os.path.join(host, ".gtt", "ade.json"))["primary"] == "claude",
          "dry run changes nothing", out)
    rc, out = ade(host, "set-primary", "codex", "--apply")
    check(rc == 0 and read_json(os.path.join(host, ".gtt", "ade.json"))["primary"] == "codex", "set-primary --apply")
    rc, out = ade(host, "set-primary", "claude", "--apply")
    check(rc == 0, "primary restored")


def scenario_update(cat, tmp, host):
    print("[update] every participating overlay is evaluated; local edits are never overwritten")
    up = os.path.join(tmp, "up")
    shutil.copytree(host, up)
    newcat = os.path.join(tmp, "newcat")
    shutil.copytree(cat, newcat)
    rule = os.path.join(newcat, ".claude", "rules", "implementation.md")
    with open(rule, "a", encoding="utf-8", newline="\n") as handle:
        handle.write("\nnew catalog line\n")
    write(os.path.join(newcat, ".kiro", "steering", "gtt-new.md"), "# new steering\n")
    stale = os.path.join(newcat, ".kiro", "steering", "gtt-infrastructure-tf.md")
    os.remove(stale)
    rc, out = ade(up, "update", "--from", newcat)
    check(rc == 0 and "UPDATE" in out and "ADD" in out and "STALE" in out and "dry run" in out, "dry run plans UPDATE / ADD / STALE", out[-700:])
    check(not os.path.exists(os.path.join(up, ".kiro", "steering", "gtt-new.md")), "dry run wrote nothing")
    rc, out = ade(up, "update", "--from", newcat, "--apply")
    check(rc == 0 and os.path.exists(os.path.join(up, ".kiro", "steering", "gtt-new.md")), "update --apply migrates the overlays", out[-400:])
    check(not os.path.exists(os.path.join(up, ".kiro", "steering", "gtt-infrastructure-tf.md")), "an overlay file the catalog dropped is removed")
    rc, out = ade(up, "validate")
    check(rc == 0, "validate passes after the update", out)
    rc, out = ade(up, "update", "--from", newcat)
    check(rc == 0 and "UPDATE" not in out and "ADD" not in out, "a second update is a no-op (idempotent)", out[-300:])
    # local edit + catalog change -> conflict, nothing written
    local = os.path.join(up, ".claude", "rules", "infrastructure.md")
    with open(local, "a", encoding="utf-8", newline="\n") as handle:
        handle.write("local edit\n")
    with open(os.path.join(newcat, ".claude", "rules", "infrastructure.md"), "a", encoding="utf-8", newline="\n") as handle:
        handle.write("catalog edit\n")
    rc, out = ade(up, "update", "--from", newcat, "--apply")
    check(rc == 1 and "CONFLICT" in out and "nothing was written" in out, "modified locally + changed upstream = conflict, nothing written", out[-400:])
    with open(local, encoding="utf-8") as handle:
        check("local edit" in handle.read(), "the local edit survives")
    # layout mismatch
    other = os.path.join(tmp, "newlayout")
    shutil.copytree(newcat, other)
    manifest = os.path.join(other, ".gtt", "scaffold", "manifest.yaml")
    with open(manifest, encoding="utf-8") as handle:
        text = handle.read()
    write(manifest, text.replace("version: 2 ", "version: 3 ", 1))
    rc, out = ade(up, "update", "--from", other)
    check(rc == 1 and "core migration first" in out, "an overlay is never migrated across a layout change", out)


def scenario_clean(cat, tmp, host):
    print("[clean / export --clean] only GTT-installed integration is removed; the host's own config stays")
    cl = os.path.join(tmp, "clean")
    shutil.copytree(host, cl)
    rc, out = ade(cl, "remove", "kiro")
    check(rc == 0 and "REMOVE" in out and "dry run" in out and os.path.exists(os.path.join(cl, ".kiro", "steering", "gtt-guard.md")), "remove is a dry run by default", out[-300:])
    rc, out = ade(cl, "remove", "kiro", "--apply")
    check(rc == 0, "remove kiro --apply", out[-300:])
    check(not os.path.exists(os.path.join(cl, ".kiro", "steering")), "GTT's kiro files and their emptied directories are gone")
    check(os.path.exists(os.path.join(cl, ".kiro", "user-notes.md")), "the host's own kiro file is kept")
    st = read_json(os.path.join(cl, ".gtt", "ade.json"))
    check("kiro" not in st["participating"] and "kiro" in st["excluded"], "kiro leaves participation and is recorded as excluded")
    rc, out = ade(cl, "remove", "claude", "--apply")
    check(rc == 2 and "Primary" in out, "the Primary ADE cannot be removed without naming its successor", out)
    # a locally modified GTT file is kept unless the human says otherwise
    with open(os.path.join(cl, ".claude", "rules", "implementation.md"), "a", encoding="utf-8", newline="\n") as handle:
        handle.write("local edit\n")
    rc, out = ade(cl, "owned")
    check("modified" in out, "owned reports a modified surface", out)
    rc, out = ade(cl, "remove", "--all", "--apply")
    check(os.path.exists(os.path.join(cl, ".claude", "rules", "implementation.md")), "a modified GTT file is kept", out[-300:])
    check(os.path.exists(os.path.join(cl, ".claude", "keep-me.txt")), "the host's own claude file is kept")
    check(not os.path.exists(os.path.join(cl, ".claude", "CLAUDE.md")), "unmodified GTT claude files are removed")
    check(os.path.exists(os.path.join(cl, ".gtt", "ade.json")), "state stays while something is only partly removed")
    rc, out = ade(cl, "remove", "--all", "--include-modified", "--apply")
    check(rc == 0 and not os.path.exists(os.path.join(cl, ".claude", "rules")), "--include-modified removes it", out[-300:])
    check(os.path.exists(os.path.join(cl, ".claude", "keep-me.txt")), "the host's own claude file still survives")
    check(not os.path.exists(os.path.join(cl, ".gtt", "ade.json")), "state is removed once no ADE is left")
    check(os.path.exists(os.path.join(cl, "AGENTS.md")), "the core entry point is never removed with an ADE")


def scenario_migration(cat, tmp):
    print("[migration] a single-ADE project keeps working and can be adopted without changing governed files")
    legacy = os.path.join(tmp, "legacy")
    make_host(cat, legacy, foreign=False)
    copy_tree(os.path.join(cat, ".claude"), os.path.join(legacy, ".claude"))
    rc, out = sh(legacy, ".gtt/scripts/gtt-check-adapter.sh", "claude")
    check(rc == 0, "the legacy single-ADE matrix still passes, unchanged", out)
    rc, out = sh(legacy, ".gtt/scripts/gtt-check-adapter.sh")
    check(rc == 2 and "no .gtt/ade.json" in out, "state mode says 'cannot determine' without state", out)
    rc, out = sh(legacy, ".gtt/scripts/gtt-validate.sh")
    check("PASS               gtt-check-adapter.sh claude" in out, "gtt-validate.sh keeps the legacy behaviour", out[:400])
    before = {p: open(os.path.join(legacy, p), "rb").read() for p in ("AGENTS.md", "gtt-domain/backlog.md")}
    rc, out = ade(legacy, "adopt")
    check(rc == 0 and "primary: claude" in out and "dry run" in out and not os.path.exists(os.path.join(legacy, ".gtt", "ade.json")), "adopt infers only the one existing ADE (dry run)", out)
    rc, out = ade(legacy, "adopt", "--apply")
    st = read_json(os.path.join(legacy, ".gtt", "ade.json"))
    check(rc == 0 and st["primary"] == "claude" and st["participating"] == ["claude"] and st["excluded"] == [], "primary = participating = the existing ADE; nothing else inferred", out)
    check(st["installed"]["claude"]["origin"] == "adopted" and st["installed"]["claude"]["files"] == {}, "an adopted ADE carries no fabricated install record")
    check(all(open(os.path.join(legacy, p), "rb").read() == b for p, b in before.items()), "no governed file was touched")
    rc, out = ade(legacy, "remove", "--all", "--apply")
    check(os.path.exists(os.path.join(legacy, ".claude", "CLAUDE.md")), "an adopted ADE's files are kept without --assume-registry-owned", out[-300:])
    rc, out = ade(legacy, "remove", "--all", "--assume-registry-owned", "--apply")
    check(rc == 0 and not os.path.exists(os.path.join(legacy, ".claude")), "with it, the registry's paths are removed", out[-300:])
    # several overlays and no state: authorization is not inferred
    multi = os.path.join(tmp, "multi")
    shutil.copytree(cat, multi)
    rc, out = ade(multi, "adopt")
    check(rc == 1 and "not inferred" in out, "several overlays present: adopt refuses to guess", out)
    rc, out = ade(multi, "adopt", "--participating", "claude,kiro", "--primary", "claude", "--apply")
    check(rc == 0, "the human can declare it explicitly", out[-300:])
    rc, out = ade(multi, "validate")
    check(rc == 0 and "detected, not participating" in out and "copilot" in out, "an ADE present but not chosen is reported, not governed", out)


def scenario_record(cat, tmp):
    print("[record] session-adapter files installed later can be attributed to GTT")
    host = os.path.join(tmp, "rec")
    make_host(cat, host, foreign=False)
    rc, out = ade(host, "install", "--from", cat, "--participating", "codex", "--primary", "codex", "--apply")
    check(rc == 0, "codex-only project installs", out[-200:])
    write(os.path.join(host, ".codex", "gtt-session-start.sh"), "#!/bin/sh\n")
    rc, out = ade(host, "record", "codex", ".codex/gtt-session-start.sh")
    check(rc == 2, "a path outside registry and declarations cannot be recorded", out)
    # what apply-session-adapters.sh does after flipping the declaration to installed
    decl = os.path.join(host, ".gtt", "session-adapters", "codex.json")
    with open(decl, encoding="utf-8") as handle:
        text = handle.read()
    write(decl, text.replace('"adapter_status": "staged"', '"adapter_status": "installed"'))
    write(os.path.join(host, ".codex", "hooks.json"), "{}" + chr(10))
    rc, out = sh(host, "-c", r"""RECORD=(); while IFS= read -r p; do [ -n "$p" ] && RECORD+=("$p"); done < <(grep -oE '"install_path": *"[^"]+"' .gtt/session-adapters/codex.json | sed -E 's/.*: *"([^"]+)"/\1/'); bash .gtt/scripts/gtt-ade.sh record codex "${RECORD[@]}" --apply""")
    check(rc == 0, "the session-adapter installer's record step attributes its files to the ADE", out)
    rc, out = ade(host, "owned")
    check(".codex/hooks.json" in out and "unmodified" in out, "clean/export now see those files as GTT-installed", out)


def scenario_templates(cat, tmp):
    print("[questionnaire] the Bootstrap exposes it; the CLI never carries a copy")
    host = os.path.join(tmp, "qhost")
    shutil.copytree(cat, host)
    rc, out = tpl(host, "list", "--json")
    data = json.loads(out)
    row = data["templates"][0]
    check(rc == 0 and row["id"] == "initial-design-questionnaire" and row["exists"] and row["compatible"], "the questionnaire is discoverable", out[:300])
    check(row["path"] == ".gtt/scaffold/templates/gtt-initial-design-questionnaire.md", "the canonical path is unchanged")
    check(row["becomes"] == "source-material", "it is declared as source material, not governed architecture")
    rc, out = tpl(host, "show", "initial-design-questionnaire")
    check(rc == 0 and "materialize_to: gtt-domain/proposals/bootstrap/" in out, "show states where a working copy goes", out)
    rc, out = tpl(host, "show", "nope")
    check(rc == 2, "an unknown template is an error", out)
    target = os.path.join(host, "gtt-domain", "proposals", "bootstrap", "initial-design-questionnaire.md")
    rc, out = tpl(host, "materialize", "initial-design-questionnaire")
    check(rc == 0 and "dry run" in out and not os.path.exists(target), "materialize is a dry run by default")
    rc, out = tpl(host, "materialize", "initial-design-questionnaire", "--apply")
    check(rc == 0 and os.path.exists(target), "materialize --apply creates the working copy", out)
    with open(target, encoding="utf-8") as a, open(os.path.join(host, row["path"]), encoding="utf-8") as b:
        check(a.read() == b.read(), "the working copy is the Bootstrap template, verbatim")
    rc, out = tpl(host, "materialize", "initial-design-questionnaire", "--apply")
    check(rc == 1 and "CONFLICT" in out, "a filled questionnaire is never overwritten", out)
    rc, out = sh(host, ".gtt/scripts/gtt-check-integrity.sh")
    check(rc == 0, "the new working copy is registered; integrity holds", out[-400:])
    with open(os.path.join(host, ".gtt", "scaffold", "templates", "gtt-initial-design-questionnaire.md"), encoding="utf-8") as handle:
        check(handle.read().count("# GTT Initial Design Questionnaire") == 1, "there is exactly one questionnaire template (no second copy)")


def scenario_core_neutral(cat):
    print("[core] the Core stays ADE-agnostic")
    for name in ("gtt-status.sh", "gtt-session-context.sh", "gtt-run-python.sh", "gtt_manifest.py", "gtt_template.py", "gtt-template.sh"):
        with open(os.path.join(cat, ".gtt", "scripts", name), encoding="utf-8") as handle:
            text = handle.read().lower()
        hit = [w for w in ("claude", "codex", "kiro", "copilot") if w in text]
        check(not hit, f"{name} names no ADE", str(hit))
    rc, out = sh(cat, ".gtt/scripts/gtt-check-session-adapter.sh", "claude")
    check(rc == 0, "the Session Memory adapter conformance check still passes", out[-300:])


def scenario_repo(cat):
    print("[repo] the whole gate is green on the catalog once the new artifacts are registered")
    rc, out = sh(cat, ".gtt/scripts/gtt-index.sh")
    check(rc == 0, "gtt-index.sh registers the new artifacts", out[-300:])
    rc, out = sh(cat, ".gtt/scripts/gtt-validate.sh")
    fails = [line for line in out.splitlines() if line.startswith("FAIL")]
    check(not fails, "gtt-validate.sh reports no FAIL", " | ".join(fails) + out[-600:])
    check("SKIPPED            gtt-check-adapter.sh" in out, "the catalog (no .gtt/ade.json) still skips the adapter check, as before")
    info = [line for line in out.splitlines() if line.startswith("CANNOT-DETERMINE")]
    if info:
        print("  note  " + "; ".join(info) + " (needs git/origin, outside a checkout)")


def overlay_package(project, proposals, cat):
    """project + the staged package -> what the project would be after promotion."""
    pkg = os.path.join(proposals, "adr-005-package", "tree")
    for dirpath, _, filenames in os.walk(pkg):
        for name in filenames:
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, pkg)
            if not rel.endswith(".staged"):
                continue
            dst = os.path.join(cat, rel[: -len(".staged")])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
    today = datetime.date.today().isoformat()
    for draft in glob.glob(os.path.join(proposals, "context-*-adr-005.md")):
        name = os.path.basename(draft)[len("context-"):-len("-adr-005.md")]
        with open(draft, encoding="utf-8", newline="") as handle:
            text = handle.read().replace("{{RATIFIED_ON}}", today)
        write(os.path.join(cat, "gtt-domain", "context", name + ".md"), text)
    adr = glob.glob(os.path.join(proposals, "ADR-DRAFT-*.md"))
    for draft in adr:
        if "bootstrap-integration-contracts" not in draft:
            continue
        with open(draft, encoding="utf-8", newline="") as handle:
            text = handle.read()
        text = text.replace("{{RATIFIED_ON}}", today).replace("{{RATIFIED_BY}}", "rehearsal")
        text = text.replace("- Status: Proposed", "- Status: Accepted")
        write(os.path.join(cat, "gtt-domain", "adr", "ADR-005-bootstrap-integration-contracts.md"), text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", help="project root; the staged package is overlaid on a temporary copy")
    parser.add_argument("--proposals", help="default: <project>/gtt-domain/proposals")
    parser.add_argument("--catalog", help="a ready project/catalog root (already promoted)")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    tmp = tempfile.mkdtemp(prefix="gtt-adr005-")
    try:
        if args.catalog:
            cat = os.path.join(tmp, "catalog")
            copy_tree(args.catalog, cat)
        else:
            if not args.project:
                parser.error("give --project (before promotion) or --catalog (after)")
            cat = os.path.join(tmp, "catalog")
            copy_tree(args.project, cat, ignore=("__pycache__", ".git"))
            overlay_package(args.project, args.proposals or os.path.join(args.project, "gtt-domain", "proposals"), cat)
        scenario_registry(cat)
        host = scenario_init(cat, tmp)
        scenario_exclusion_and_reinclude(cat, host)
        scenario_status_inspect_resume(host)
        scenario_validate_failures(cat, tmp, host)
        scenario_primary(host)
        scenario_update(cat, tmp, host)
        scenario_clean(cat, tmp, host)
        scenario_migration(cat, tmp)
        scenario_record(cat, tmp)
        scenario_templates(cat, tmp)
        scenario_core_neutral(cat)
        scenario_repo(cat)
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print("kept:", tmp)
    print(f"\n{COUNT - len(FAILS)}/{COUNT} checks held")
    if FAILS:
        print("FAILED:", "; ".join(FAILS))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
