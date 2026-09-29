#!/usr/bin/env python3
"""GTT ADR-006 - rehearsal of provenance, gaps (OPEN/BLOCKING), sources and working agreements.

Runs entirely in a DISPOSABLE temp directory; never touches the project it is pointed at and never
runs a promotion script. It builds a throw-away catalog (the project plus the staged package) and
drives the new gate through valid and invalid cases, freeze, status/query, compatibility with
projects that adopted none of it, and the non-regression of the Multi-ADE / questionnaire work.

  python rehearse-provenance.py --project .        BEFORE promotion: project + the staged package
  python rehearse-provenance.py --catalog .        AFTER promotion: the project as it now is

Exit 0 = every scenario held, 1 = at least one failed.
"""

import argparse
import datetime
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

FAILS, COUNT = [], 0


def check(cond, label, detail=""):
    global COUNT
    COUNT += 1
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        FAILS.append(label)


def sh(cwd, *cmd):
    proc = subprocess.run(["bash", *cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def gate(cwd, *args):
    return sh(cwd, ".gtt/scripts/gtt-check-provenance.sh", *args)


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def append(path, text):
    write(path, read(path) + text)


def fresh(cat, tmp, name):
    dst = os.path.join(tmp, name)
    shutil.copytree(cat, dst)
    return dst


def stack(proj):
    return os.path.join(proj, "gtt-domain", "context", "stack.md")


def set_gaps(proj, lines):
    text = read(stack(proj))
    write(stack(proj), text.replace("```gtt-gaps\n```", "```gtt-gaps\n" + "\n".join(lines) + "\n```", 1))


def set_sources(proj, lines):
    write(os.path.join(proj, "gtt-domain", "context", "sources.md"),
          "# Sources\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md\n\n"
          "```gtt-sources\n" + "\n".join(lines) + "\n```\n")


def ctx_append(proj, text):
    append(os.path.join(proj, "gtt-domain", "context", "architecture.md"), "\n" + text + "\n")


def base_sources(proj):
    write(os.path.join(proj, "docs", "spec.md"), "# spec\nline 2\nline 3\nline 4\n")
    write(os.path.join(proj, "docs", "req.md"), "# req\n")
    set_sources(proj, ["policy: provenance=advisory",
                       "spec | docs/spec.md | 2.1 | primary | 1 | active",
                       "req | docs/req.md | 1.7 | primary | 2 | active"])


# ---------------------------------------------------------------- scenarios

def scenario_valid(cat, tmp):
    print("[provenance] valid tags, sources and gaps pass")
    p = fresh(cat, tmp, "valid")
    base_sources(p)
    set_gaps(p, ["OPEN | GAP-001 | cache | scope: the choice of a cache technology only | affects: stack.md section 1, Datastore (cache)"])
    ctx_append(p, "Persistence follows the spec [FUENTE: spec:section-3] and the requirements [FUENTE: docs/req.md:1]. "
                  "The cache is not decided [VACÍO: GAP-001].")
    rc, out = gate(p)
    check(rc == 0 and "0 FAIL" in out, "valid provenance, sources and an OPEN gap: gate passes", out[-500:])
    rc, out = gate(p, "--pre-freeze")
    check(rc == 0, "a valid OPEN gap does not block freeze", out[-400:])
    rc, out = sh(p, ".gtt/scripts/gtt-query.sh", "--governance", "sources")
    check(rc == 0 and out.index("spec") < out.index("req") and "provenance=advisory" in out, "sources are listed in precedence order", out)
    ctx_append(p, "Code spans are ignored: `[PROPUESTA]` and `[FUENTE: nosuch]` and `[VACÍO]`.")
    rc, out = gate(p)
    check(rc == 0, "tags inside code spans are not scanned", out[-300:])


def scenario_invalid_tags(cat, tmp):
    print("[provenance] invalid tags fail; ambiguity is visible")
    def case(name, text, expect, level="FAIL", args=(), setup=None):
        p = fresh(cat, tmp, name)
        base_sources(p)
        if setup:
            setup(p)
        ctx_append(p, text)
        rc, out = gate(p, *args)
        want_rc = 1 if level == "FAIL" else 0
        check(rc == want_rc and expect in out, f"{name}: {expect}", out[-350:])
        return p
    case("bad-fuente", "Claim [FUENTE: nosuch]", "does not resolve")
    case("empty-fuente", "Claim [FUENTE]", "without a reference")
    case("bare-vacio", "Unknown [VACÍO]", "is not classified", level="WARN")
    def required(p):
        set_sources(p, ["policy: provenance=required", "spec | docs/spec.md | 2.1 | primary | 1 | active"])
    case("bare-vacio-required", "Unknown [VACÍO]", "is not classified", args=(), setup=required)
    case("unknown-gap", "Unknown [VACÍO: GAP-999]", "not OPEN or BLOCKING")
    case("conflict-unnamed", "Auth differs [CONFLICTO]", "must name the participating sources")
    case("conflict-undeclared", "Auth differs [CONFLICTO: spec vs ghost]", "not a declared source")
    case("proposal-in-context", "We could use Redis [PROPUESTA]", "not a decision")
    def unfrozen(p):
        os.remove(os.path.join(p, "gtt-domain", ".frozen"))
    p = case("conflict-named", "Auth differs [CONFLICTO: spec vs req]", "unresolved [CONFLICTO]", level="WARN", setup=unfrozen)
    q = case("conflict-in-frozen", "Auth differs [CONFLICTO: spec vs req]", "unresolved [CONFLICTO]")
    rc, out = gate(p, "--pre-freeze")
    check(rc == 1 and "unresolved [CONFLICTO]" in out, "an unresolved conflict refuses freeze", out[-300:])
    rc, out = sh(p, ".gtt/scripts/gtt-query.sh", "--governance", "conflicts")
    check("spec(1) > req(2)" in out and "does not resolve the conflict" in out,
          "precedence orders the sources but does not resolve the conflict", out)
    def required2(p):
        set_sources(p, ["policy: provenance=required", "spec | docs/spec.md | 2.1 | primary | 1 | active"])
    p = fresh(cat, tmp, "required-rows")
    required2(p) if os.makedirs(os.path.join(p, "docs"), exist_ok=True) is None else None
    write(os.path.join(p, "docs", "spec.md"), "# spec\n")
    rc, out = gate(p)
    check(rc == 1 and "policy provenance=required" in out, "policy=required demands a source or ADR for each technology row", out[-300:])


def scenario_gaps(cat, tmp):
    print("[gaps] OPEN vs BLOCKING")
    def gapcase(name, lines, expect, rc_want, args=(), frozen_marker=None):
        p = fresh(cat, tmp, name)
        if frozen_marker is False:
            os.remove(os.path.join(p, "gtt-domain", ".frozen"))
        set_gaps(p, lines)
        rc, out = gate(p, *args)
        check(rc == rc_want and (expect in out if expect else True), f"{name}", out[-300:])
        return p
    gapcase("open-noscope", ["OPEN | GAP-001 | cache | scope:  | affects: x"], "needs an explicit `scope:`", 1)
    gapcase("open-as-authorisation", ["OPEN | GAP-001 | cache | scope: anything about caching is authorised | affects: x"],
            "never an authorisation", 1)
    gapcase("blocking-pre-freeze-state", ["BLOCKING | GAP-002 | auth | scope: the identity provider | affects: stack.md"],
            "freeze is refused", 0, frozen_marker=False)
    gapcase("blocking-refuses-freeze", ["BLOCKING | GAP-002 | auth | scope: the identity provider | affects: stack.md"],
            "BLOCKING pending", 1, args=("--pre-freeze",), frozen_marker=False)
    gapcase("blocking-in-frozen-design", ["BLOCKING | GAP-002 | auth | scope: the identity provider | affects: stack.md"],
            "frozen design cannot carry", 1)
    gapcase("resolved-traceable", ["RESOLVED | GAP-003 | cache | was: OPEN | by: ADR-001"], "", 0)
    gapcase("resolved-missing-adr", ["RESOLVED | GAP-003 | cache | was: OPEN | by: ADR-777"], "existing ADR", 1)
    gapcase("resolved-and-open", ["OPEN | GAP-003 | cache | scope: cache choice only | affects: x",
                                  "RESOLVED | GAP-003 | cache | was: OPEN | by: ADR-001"], "both RESOLVED and still", 1)
    gapcase("dup-id", ["OPEN | GAP-004 | a | scope: a only | affects: x", "OPEN | GAP-004 | b | scope: b only | affects: y"],
            "duplicate id", 1)
    gapcase("bad-kind", ["MAYBE | GAP-005 | a | scope: a | affects: x"], "unknown kind", 1)
    p = fresh(cat, tmp, "empty-cell")
    write(stack(p), read(stack(p)).replace("| Datastore (cache) | none |", "| Datastore (cache) | |", 1))
    rc, out = gate(p)
    check(rc == 0 and "not classified as an OPEN or BLOCKING gap" in out, "an empty decision that is not classified is flagged", out[-300:])
    set_gaps(p, ["OPEN | GAP-006 | Datastore (cache) | scope: cache technology only | affects: stack.md section 1"])
    rc, out = gate(p)
    check("not classified" not in out, "classifying it as OPEN clears the flag", out[-300:])
    # OPEN is visible everywhere it should be
    rc, out = sh(p, ".gtt/scripts/gtt-query.sh", "--governance", "open")
    check("GAP-006" in out and "scope:" in out, "query --governance open lists it with its scope", out)
    rc, out = sh(p, ".gtt/scripts/gtt-status.sh")
    check("OPEN 1, BLOCKING 0" in out, "status counts it", out[-500:])


def scenario_sources(cat, tmp):
    print("[sources] manifest, authority, precedence")
    def case(name, lines, expect, rc_want=1, brief=False):
        p = fresh(cat, tmp, name)
        write(os.path.join(p, "docs", "a.md"), "# a\n")
        write(os.path.join(p, "docs", "b.md"), "# b\n")
        if brief:
            write(os.path.join(p, "SOURCE-BRIEF.md"), "# brief\n")
        set_sources(p, lines)
        rc, out = gate(p)
        check(rc == rc_want and (expect in out if expect else True), name, out[-300:])
    case("duplicate-precedence", ["a | docs/a.md | 1 | primary | 1 | active", "b | docs/b.md | 1 | primary | 1 | active"], "ambiguous")
    case("missing-path", ["a | docs/none.md | 1 | primary | 1 | active"], "does not exist")
    case("bad-authority", ["a | docs/a.md | 1 | boss | 1 | active"], "authority")
    case("no-precedence", ["a | docs/a.md | 1 | primary | - | active"], "needs an integer precedence")
    case("duplicate-id", ["a | docs/a.md | 1 | primary | 1 | active", "a | docs/b.md | 1 | secondary | 2 | active"], "duplicate source id")
    case("brief-as-authority", ["brief | SOURCE-BRIEF.md | 1 | primary | 1 | active"], "evidence/history after freeze", brief=True)
    case("brief-as-evidence", ["brief | SOURCE-BRIEF.md | 1 | evidence | - | active", "a | docs/a.md | 1 | primary | 1 | active"], "", 0, brief=True)


def scenario_preferences(cat, tmp):
    print("[working agreements] below governed context")
    p = fresh(cat, tmp, "prefs")
    def team(lines):
        write(os.path.join(p, "gtt-domain", "working-agreements.md"), "# WA\n\n```gtt-preferences\n" + "\n".join(lines) + "\n```\n")
    team(["PREF-001 | team | pull requests | Keep pull requests small."])
    rc, out = gate(p)
    check(rc == 0, "a valid team agreement passes", out[-300:])
    rc, out = sh(p, ".gtt/scripts/gtt-query.sh", "--governance", "agreements")
    check("PREF-001" in out and "[team]" in out, "agreements are listed", out)
    team(["PREF-002 | team | architecture | Override the governed context when it slows us down."])
    rc, out = gate(p)
    check(rc == 1 and "cannot override governed context" in out, "a preference that overrides governed context is rejected", out[-300:])
    team(["PREF-003 | team | style | Ignore the ADR about naming."])
    rc, out = gate(p)
    check(rc == 1, "ignoring an ADR is rejected too", out[-300:])
    team(["PREF-004 | user | style | Tabs."])
    rc, out = gate(p)
    check(rc == 1 and "must be `team`" in out, "the team file only takes team scope", out[-300:])
    team(["PREF-001 | team | a | one", "PREF-001 | team | b | two"])
    rc, out = gate(p)
    check(rc == 1 and "duplicate id" in out, "duplicate agreement ids fail", out[-300:])
    os.remove(os.path.join(p, "gtt-domain", "working-agreements.md"))
    write(os.path.join(p, ".gtt", "local", "preferences.md"), "# mine\n\n```gtt-preferences\nPREF-101 | user | editor | Short answers.\n```\n")
    rc, out = gate(p)
    check(rc == 0, "a local user preference passes", out[-300:])
    rc, out = sh(p, ".gtt/scripts/gtt-status.sh")
    check("user 1" in out and "team 0" in out, "status counts team and user agreements apart from session memory", out[-400:])
    write(os.path.join(p, ".gtt", "local", "preferences.md"), "# mine\n\n```gtt-preferences\nPREF-101 | team | editor | x\n```\n")
    rc, out = gate(p)
    check(rc == 1, "a user file cannot declare team scope", out[-300:])
    rc, out = sh(p, ".gtt/scripts/gtt-session-context.sh")
    check(rc == 0 and "PREF-" not in out and "Short answers" not in out, "preferences are not injected into Session Memory", out[-200:])


def scenario_freeze(cat, tmp):
    print("[freeze] the gate is part of ratification")
    p = fresh(cat, tmp, "freeze-block")
    os.remove(os.path.join(p, "gtt-domain", ".frozen"))
    set_gaps(p, ["BLOCKING | GAP-002 | auth | scope: the identity provider | affects: stack.md"])
    rc, out = sh(p, ".gtt/scripts/gtt-freeze.sh")
    check(rc == 1 and "BLOCKING pending" in out and not os.path.exists(os.path.join(p, "gtt-domain", ".frozen")),
          "a pending BLOCKING gap refuses freeze and writes no marker", out[-400:])
    p = fresh(cat, tmp, "freeze-conflict")
    os.remove(os.path.join(p, "gtt-domain", ".frozen"))
    base_sources(p)
    ctx_append(p, "Auth differs [CONFLICTO: spec vs req]")
    rc, out = sh(p, ".gtt/scripts/gtt-freeze.sh")
    check(rc == 1 and not os.path.exists(os.path.join(p, "gtt-domain", ".frozen")), "an unresolved conflict refuses freeze", out[-300:])
    p = fresh(cat, tmp, "freeze-open")
    os.remove(os.path.join(p, "gtt-domain", ".frozen"))
    set_gaps(p, ["OPEN | GAP-001 | cache | scope: the choice of a cache technology only | affects: stack.md"])
    rc, out = sh(p, ".gtt/scripts/gtt-freeze.sh")
    check(rc == 0 and os.path.exists(os.path.join(p, "gtt-domain", ".frozen")), "a valid OPEN gap crosses freeze", out[-300:])
    rc, out = sh(p, ".gtt/scripts/gtt-query.sh", "--governance", "open")
    check("GAP-001" in out, "and stays visible after freeze", out)
    # an OPEN never authorises a change to the frozen design: only an ADR-backed RESOLVED line closes it
    set_gaps(p, ["RESOLVED | GAP-001 | cache | was: OPEN | by: ADR-001"])
    rc, out = gate(p)
    check(rc == 0, "resolution is traceable: the gap becomes RESOLVED citing an ADR", out[-200:])


def scenario_compat(cat, tmp):
    print("[compatibility] projects that adopted none of it are unchanged")
    p = fresh(cat, tmp, "legacy")
    write(stack(p), read(stack(p)).replace("```gtt-gaps\n```", "", 1))
    rc, out = gate(p)
    check(rc == 0 and "no gap register in stack.md" in out, "no gap register, no manifest, no agreements: gate passes", out[-300:])
    q = fresh(cat, tmp, "no-gate")
    os.remove(os.path.join(q, ".gtt", "scripts", "gtt-check-provenance.sh"))
    os.remove(os.path.join(q, "gtt-domain", ".frozen"))
    rc, out = sh(q, ".gtt/scripts/gtt-freeze.sh")
    check(rc == 0, "an install without the gate still freezes (the gate is skipped, not required)", out[-300:])
    rc, out = sh(p, ".gtt/scripts/gtt-status.sh")
    check("## Evidence / Governance" in out and "sources: 0 declared" in out, "status prints the governance section", out[-500:])


def scenario_templates(cat, tmp):
    print("[templates] the Bootstrap exposes the two new templates")
    p = fresh(cat, tmp, "templates")
    rc, out = sh(p, ".gtt/scripts/gtt-template.sh", "list")
    check(rc == 0 and all(t in out for t in ("initial-design-questionnaire", "source-manifest", "working-agreements")),
          "list shows the questionnaire and both new templates", out)
    rc, out = sh(p, ".gtt/scripts/gtt-template.sh", "materialize", "working-agreements", "--apply")
    target = os.path.join(p, "gtt-domain", "working-agreements.md")
    check(rc == 0 and os.path.isfile(target), "working-agreements materialises where declared", out)
    rc, out = gate(p)
    check(rc == 0, "the untouched template passes the gate (its example lines are comments)", out[-300:])
    rc, out = sh(p, ".gtt/scripts/gtt-template.sh", "materialize", "source-manifest", "--apply")
    check(rc == 0 and os.path.isfile(os.path.join(p, "gtt-domain", "proposals", "bootstrap", "sources.md")),
          "source-manifest materialises to the bootstrap drafts area", out)
    rc, out = sh(p, ".gtt/scripts/gtt-template.sh", "materialize", "working-agreements", "--apply")
    check(rc == 1 and "CONFLICT" in out, "never overwritten", out)
    rc, out = sh(p, ".gtt/scripts/gtt-check-integrity.sh")
    check(rc == 0, "the new artifacts are registered; integrity holds", out[-300:])


def scenario_regression(cat, tmp):
    print("[regression] the whole gate, Multi-ADE and the questionnaire")
    p = fresh(cat, tmp, "gate")
    rc, out = sh(p, ".gtt/scripts/gtt-index.sh")
    check(rc == 0, "gtt-index.sh registers the new artifacts", out[-300:])
    rc, out = sh(p, ".gtt/scripts/gtt-validate.sh")
    fails = [l for l in out.splitlines() if l.startswith("FAIL")]
    check(not fails and "PASS               gtt-check-provenance.sh" in out, "gtt-validate.sh: no FAIL, provenance gate runs", " | ".join(fails) + out[-400:])
    info = [l for l in out.splitlines() if l.startswith("CANNOT-DETERMINE")]
    if info:
        print("  note  " + "; ".join(info) + " (needs git/origin, outside a checkout)")
    for name in ("gtt_provenance.py", "gtt-check-provenance.sh"):
        text = read(os.path.join(p, ".gtt", "scripts", name)).lower()
        hit = [w for w in ("claude", "codex", "kiro", "copilot") if w in text]
        check(not hit, f"{name} names no ADE (Core stays ADE-agnostic)", str(hit))
    rc, out = sh(p, ".gtt/scripts/gtt-ade.sh", "list")
    check(rc == 0 and "claude" in out, "the ADE registry still reads from the extended manifest", out[-200:])
    rc, out = sh(p, ".gtt/scripts/gtt-query.sh", "Human Promotion Boundary")
    check(rc == 0, "ordinary gtt-query.sh retrieval is unchanged", out[-200:])
    harness = os.path.join(p, "gtt-domain", "proposals", "adr-005-package", "rehearse-multi-ade.py")
    if os.path.isfile(harness):
        proc = subprocess.run([sys.executable, harness, "--catalog", p], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        tail = [l for l in proc.stdout.splitlines() if "checks held" in l]
        check(proc.returncode == 0, "ADR-005 rehearsal (Multi-ADE + questionnaire) still holds: " + (tail[0].strip() if tail else ""),
              proc.stdout[-600:])
    else:
        print("  note  ADR-005 rehearsal harness not found; regression against Multi-ADE not exercised")


def overlay_package(project, proposals, cat):
    pkg = os.path.join(proposals, "adr-006-package", "tree")
    for dirpath, _, filenames in os.walk(pkg):
        for name in filenames:
            if not name.endswith(".staged"):
                continue
            src = os.path.join(dirpath, name)
            dst = os.path.join(cat, os.path.relpath(src, pkg)[: -len(".staged")])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
    today = datetime.date.today().isoformat()
    for draft in glob.glob(os.path.join(proposals, "context-*-adr-006.md")):
        name = os.path.basename(draft)[len("context-"):-len("-adr-006.md")]
        write(os.path.join(cat, "gtt-domain", "context", name + ".md"), read(draft).replace("{{RATIFIED_ON}}", today))
    for draft in glob.glob(os.path.join(proposals, "ADR-DRAFT-provenance-*.md")):
        text = read(draft).replace("{{RATIFIED_ON}}", today).replace("{{RATIFIED_BY}}", "rehearsal")
        text = text.replace("- Status: Proposed", "- Status: Accepted")
        write(os.path.join(cat, "gtt-domain", "adr", "ADR-006-provenance-gaps-sources-agreements.md"), text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project")
    parser.add_argument("--proposals")
    parser.add_argument("--catalog")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    tmp = tempfile.mkdtemp(prefix="gtt-adr006-")
    try:
        cat = os.path.join(tmp, "catalog")
        ignore = shutil.ignore_patterns("__pycache__", ".git")
        if args.catalog:
            shutil.copytree(args.catalog, cat, ignore=ignore)
        else:
            if not args.project:
                parser.error("give --project (before promotion) or --catalog (after)")
            shutil.copytree(args.project, cat, ignore=ignore)
            overlay_package(args.project, args.proposals or os.path.join(args.project, "gtt-domain", "proposals"), cat)
        scenario_valid(cat, tmp)
        scenario_invalid_tags(cat, tmp)
        scenario_gaps(cat, tmp)
        scenario_sources(cat, tmp)
        scenario_preferences(cat, tmp)
        scenario_freeze(cat, tmp)
        scenario_compat(cat, tmp)
        scenario_templates(cat, tmp)
        scenario_regression(cat, tmp)
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
