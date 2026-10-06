#!/usr/bin/env python3
"""GTT Bootstrap 1.0 - acceptance tests for the CLI v1.0 contract.

Every scenario runs on a DISPOSABLE copy of this project in a temp directory; the project itself is never
modified. The tests drive the Bootstrap only through its contracts (gtt-contract.sh: release, negotiate,
show, run <declared operation>) exactly as a CLI would, and cover the acceptance list of the task:
release identity, compatibility (compatible -> PASS, incompatible -> REFUSE with the project unchanged),
profiles, ADE, questionnaire, export, recovery, evolution without CLI change, unsupported capability.

  python .gtt/tests/bootstrap-acceptance.py [--project .] [--keep]

Exit 0 = every check held, 1 = at least one failed.
"""

import argparse
import glob
import hashlib
import json
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


def bash(cwd, *cmd):
    p = subprocess.run(["bash", *cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def contract(cwd, *args):
    return bash(cwd, ".gtt/scripts/gtt-contract.sh", *args)


def op(cwd, name, **kw):
    """Run a declared operation the way a CLI would: name + typed name=value arguments, envelope out."""
    args = [f"{k}={('true' if v is True else 'false' if v is False else v)}" for k, v in kw.items()]
    rc, out, err = contract(cwd, "run", name, *args, "--envelope")
    try:
        return rc, json.loads(out), err
    except ValueError:
        return rc, {"exit_code": rc, "stdout": out, "stderr": err}, err


def data(env):
    try:
        return json.loads(env["stdout"])
    except ValueError:
        return None


def tree_hash(root):
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in ("__pycache__", ".git"))
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            digest.update(os.path.relpath(path, root).encode())
            digest.update(open(path, "rb").read())
    return digest.hexdigest()


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, obj):
    write(path, json.dumps(obj, indent=2) + "\n")


def fresh(project, tmp, name):
    dst = os.path.join(tmp, name)
    shutil.copytree(project, dst, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    return dst


def make_host(project, tmp, name):
    """A host project: portable core + Engine + domain, no overlay installed."""
    host = os.path.join(tmp, name)
    os.makedirs(host)
    for item in ("AGENTS.md",):
        shutil.copy2(os.path.join(project, item), host)
    for item in (".gtt", "gtt-domain"):
        shutil.copytree(os.path.join(project, item), os.path.join(host, item), ignore=shutil.ignore_patterns("__pycache__"))
    return host


# ------------------------------------------------------------------ scenarios

def release_identity(project, tmp):
    print("[release identity] the CLI can identify the exact Bootstrap release")
    p = fresh(project, tmp, "rel")
    rc, out, _ = contract(p, "release", "--json")
    rel = json.loads(out)
    b = rel["bootstrap"]
    check(rc == 0 and b["id"] == "gtt-bootstrap" and b["version"] == "1.3.1" and b["schema_version"] == 1 and b["channel"] == "stable",
          "id, version, schema_version and channel are machine-readable", out[:200])
    check(rel["scaffold"]["version"] == 2 and rel["scaffold"]["version"] != b["version"], "scaffold version is distinct from the release version")
    check(all(isinstance(v, int) for v in rel["contracts"].values()) and "export_policy" in rel["contracts"], "every contract has a version")
    rc, out, _ = contract(p, "capabilities", "--json")
    ids = {c["id"] for c in json.loads(out)["capabilities"]}
    need = {"project.detect", "ade.detect", "ade.install", "template.materialize", "methodology.profile", "validation",
            "freeze", "session-context", "export-policy", "recovery", "developer-experience"}
    check(need <= ids, "the capability registry lists the required capabilities", str(need - ids))
    rc, out, _ = contract(p, "operations", "--json")
    ops = json.loads(out)["operations"]
    check(all(isinstance(o["version"], int) for o in ops.values()), "the operation registry is versioned")
    rc, out, err = contract(p, "check")
    check(rc == 0, "the contract check passes", out + err)


def compatibility(project, tmp):
    print("[compatibility] compatible CLI -> PASS; incompatible -> REFUSE with the project unchanged")
    p = fresh(project, tmp, "compat")
    before = tree_hash(p)
    good = ("--cli-version", "1.0.0", "--cli-capabilities", "contract.negotiate.v1,operation.execute.v1", "--cli-schemas", "1")
    rc, out, _ = contract(p, "negotiate", *good, "--json")
    check(rc == 0 and json.loads(out)["compatible"], "a compatible CLI passes")
    cases = [("older CLI", ("--cli-version", "0.9.9", "--cli-capabilities", "contract.negotiate.v1,operation.execute.v1", "--cli-schemas", "1")),
             ("unsupported schema", ("--cli-version", "1.0.0", "--cli-capabilities", "contract.negotiate.v1,operation.execute.v1", "--cli-schemas", "2")),
             ("missing capability", ("--cli-version", "1.0.0", "--cli-capabilities", "contract.negotiate.v1", "--cli-schemas", "1")),
             ("no version declared", ("--cli-capabilities", "contract.negotiate.v1,operation.execute.v1", "--cli-schemas", "1")),
             ("no schemas declared", ("--cli-version", "1.0.0", "--cli-capabilities", "contract.negotiate.v1,operation.execute.v1")),
             ("garbage version", ("--cli-version", "one", "--cli-capabilities", "contract.negotiate.v1,operation.execute.v1", "--cli-schemas", "1"))]
    for label, args in cases:
        rc, out, _ = contract(p, "negotiate", *args, "--json")
        check(rc == 3 and not json.loads(out)["compatible"] and json.loads(out)["reasons"], f"{label}: REFUSE with reasons")
    rel = read_json(os.path.join(p, ".gtt/contract/release.json"))
    rel["compatibility"]["cli"]["max_version"] = "1.4.0"
    save_json(os.path.join(p, ".gtt/contract/release.json"), rel)
    rc, out, _ = contract(p, "negotiate", "--cli-version", "2.0.0", "--cli-capabilities", "contract.negotiate.v1,operation.execute.v1", "--cli-schemas", "1")
    check(rc == 3, "a CLI newer than max_version is refused")
    rel["compatibility"]["cli"]["max_version"] = None
    save_json(os.path.join(p, ".gtt/contract/release.json"), rel)
    check(tree_hash(p) != before, "(sanity) the copy was edited only by this test")
    q = fresh(project, tmp, "compat2")
    h = tree_hash(q)
    contract(q, "negotiate", "--cli-version", "0.1.0", "--cli-schemas", "9")
    check(tree_hash(q) == h, "a refusal never modifies the project")


def profiles(project, tmp):
    print("[profiles] Light, Medium, Hard and Team are Bootstrap-defined; the human selects, the CLI records")
    p = fresh(project, tmp, "prof")
    rc, out, _ = contract(p, "show", "profiles")
    spec = json.loads(out)
    check([x["id"] for x in spec["supported"]] == ["light", "medium", "hard", "team"] and spec["strictness_order"] == ["light", "medium", "hard", "team"],
          "four supported plans, ordered light < medium < hard < team")
    check(spec["selection"]["policy"] == "ask" and spec["selection"]["unselected"]["gates_from"] == spec["default"] == "medium",
          "the plan is asked for, never inferred; medium is only the gate fallback of an unselected project")
    check(all(spec["profiles"][x]["plan"]["policy"]["human"]["confirmation"][k] == "required"
              for x in spec["strictness_order"] for k in ("governed_decision", "destructive")),
          "no plan delegates a governed decision or a destructive operation")
    check(spec["profiles"]["team"]["gates"] == spec["profiles"]["hard"]["gates"] and spec["profiles"]["team"]["plan"]["policy"]["collaboration"]["ci"] == "required",
          "Team is the Hard gates plus collaboration requirements (CI required)")
    check(all(not i["relaxable"] for i in spec["invariants"]) and {"human-decision-authority", "provenance-tags", "freeze-semantics"} <= {i["id"] for i in spec["invariants"]},
          "the mandatory invariants are defined and none is relaxable")
    check(all(spec["profiles"][x]["relaxes"] == [] for x in ("medium", "hard", "team")) and spec["profiles"]["light"]["relaxes"],
          "only Light relaxes anything, and says exactly how")
    rc, env, _ = op(p, "methodology.profile.get")
    got = data(env)
    check(got["profile"] == "medium" and got["source"] == "default" and got["selected"] is False,
          "no selection -> reported as not selected; medium gates apply as a fallback")
    rc, text, _ = bash(p, ".gtt/scripts/gtt-project.sh", "profile", "get")
    check("plan: not selected" in text, "the unselected state is stated in plain words", text)
    for choice in ("light", "medium", "team", "hard"):
        rc, env, _ = op(p, "methodology.profile.set", profile=choice, language="es", apply=True)
        state = read_json(os.path.join(p, ".gtt/methodology.json"))
        check(rc == 0 and state["profile"] == choice and state["language"] == "es", f"{choice} is valid and recorded")
    rc, env, _ = op(p, "methodology.profile.set", profile="extreme", apply=True)
    check(rc == 5, "an unsupported profile is refused by the argument schema")
    rc, env, _ = op(p, "methodology.profile.set", profile="light")
    check(rc == 0 and read_json(os.path.join(p, ".gtt/methodology.json"))["profile"] == "hard", "without apply it is a dry run")
    # the Bootstrap applies the semantics: gates differ by profile
    results = {}
    for choice in ("light", "medium", "team", "hard"):
        op(p, "methodology.profile.set", profile=choice, apply=True)
        results[choice] = bash(p, ".gtt/scripts/gtt-check-provenance.sh", "--pre-freeze")[0]
    check(results["light"] == 0 and results["medium"] == 0 and results["hard"] == 1 and results["team"] == 1,
          "Hard and Team refuse freeze where Light and Medium accept (warnings block, manifest required)", str(results))
    got = data(op(p, "methodology.profile.get")[1])
    check(got["selected"] is True and got["plan"]["label"] == "Hard Method", "a selected plan is reported with its label and policy")
    op(p, "methodology.profile.set", profile="hard", apply=True)
    hard = bash(p, ".gtt/scripts/gtt-check-provenance.sh", "--pre-freeze")
    out = hard[1] + hard[2]
    check("requires a source manifest" in out and "blocks freeze" in out, "the Hard failures cite the profile", out[-300:])
    # frozen: relaxing is a governed change
    write(os.path.join(p, "gtt-domain/.frozen"), "2026-01-01T00:00:00Z\n")
    rc, env, err = op(p, "methodology.profile.set", profile="light", apply=True)
    check(env["exit_code"] == 1 and "governed change" in env["stderr"] and read_json(os.path.join(p, ".gtt/methodology.json"))["profile"] == "hard",
          "a frozen project refuses a less strict profile", env["stderr"][:200])
    op(p, "methodology.profile.set", profile="team", apply=True)
    rc, env, err = op(p, "methodology.profile.set", profile="hard", apply=True)
    check(env["exit_code"] == 1 and read_json(os.path.join(p, ".gtt/methodology.json"))["profile"] == "team",
          "a frozen project accepts a stricter plan (team) and then refuses to step back to hard")
    # the contracts themselves refuse to weaken an invariant
    bad = fresh(project, tmp, "prof-bad")
    spec = read_json(os.path.join(bad, ".gtt/contract/profiles.json"))
    spec["profiles"]["light"]["relaxes"].append({"control": "freeze-semantics", "how": "skip it"})
    save_json(os.path.join(bad, ".gtt/contract/profiles.json"), spec)
    rc, out, _ = contract(bad, "check")
    check(rc == 1 and "relaxes the invariant" in out, "a profile that relaxes an invariant fails the contract check", out)
    spec = read_json(os.path.join(bad, ".gtt/contract/profiles.json"))
    spec["profiles"]["light"]["relaxes"].pop()
    spec["invariants"][0]["relaxable"] = True
    save_json(os.path.join(bad, ".gtt/contract/profiles.json"), spec)
    rc, out, _ = contract(bad, "check")
    check(rc == 1 and "must not be relaxable" in out, "an invariant marked relaxable fails the check", out)
    spec = read_json(os.path.join(bad, ".gtt/contract/profiles.json"))
    spec["invariants"][0]["relaxable"] = False
    spec["profiles"]["light"]["plan"]["policy"]["human"]["confirmation"]["destructive"] = "not_required"
    spec["selection"]["policy"] = "infer"
    save_json(os.path.join(bad, ".gtt/contract/profiles.json"), spec)
    rc, out, _ = contract(bad, "check")
    check(rc == 1 and "no plan delegates it" in out and "never inferred" in out,
          "a plan that delegates a destructive operation, or a selection that is inferred, fails the check", out)


def ade(project, tmp):
    print("[ADE] detect, participate, primary, secondary, validate, change primary")
    host = make_host(project, tmp, "ade-host")
    write(os.path.join(host, ".kiro", "user-notes.md"), "the host's own\n")
    rc, out, _ = contract(host, "show", "ade-registry")
    reg = json.loads(out)
    row = {a["id"]: a for a in reg["ades"]}
    need = {"id", "name", "detect", "install", "validate", "owned_paths", "handoff", "invoke", "version"}
    check(sorted(row) == ["antigravity", "claude", "codex", "copilot", "cursor", "kiro", "openhands"] and all(need <= set(a) for a in reg["ades"]),
          "the ADE registry is machine-readable with the required fields")
    check(reg["participation_states"] == ["detected", "participating", "primary", "excluded"], "participation states are defined")
    rc, env, _ = op(host, "ade.detect")
    cand = {c["id"]: c for c in data(env)["candidates"]}
    check(rc == 0 and cand["kiro"]["status"] == "candidate", "detect yields candidates, never participation")
    rc, env, _ = op(host, "ade.install", **{"from": project, "participating": "claude,codex", "primary": "claude"})
    check(rc == 0 and not os.path.exists(os.path.join(host, ".gtt/ade.json")), "install is a dry run by default")
    rc, env, _ = op(host, "ade.install", **{"from": project, "participating": "claude,codex", "primary": "claude", "apply": True})
    check(rc == 0 and os.path.isfile(os.path.join(host, ".claude/CLAUDE.md")), "participating ADEs are installed", env["stderr"])
    rc, env, _ = op(host, "ade.state")
    st = data(env)
    check(st["primary"] == "claude" and st["participating"] == ["claude", "codex"] and st["excluded"] == ["antigravity", "copilot", "cursor", "kiro", "openhands"], "primary + secondary + excluded recorded")
    rc, env, _ = op(host, "ade.validate")
    check(rc == 0, "the resulting state validates")
    before_claude = tree_hash(os.path.join(host, ".claude"))
    rc, env, _ = op(host, "ade.set-primary", ade="copilot", apply=True)
    check(rc != 0, "the Primary must be a participating ADE")
    rc, env, _ = op(host, "ade.set-primary", ade="codex", apply=True)
    st = data(op(host, "ade.state")[1])
    check(rc == 0 and st["primary"] == "codex" and st["participating"] == ["claude", "codex"], "changing the Primary preserves the secondary ADEs")
    check(tree_hash(os.path.join(host, ".claude")) == before_claude and os.path.exists(os.path.join(host, ".kiro/user-notes.md")),
          "changing the Primary reinstalls and removes nothing")
    rc, env, _ = op(host, "ade.validate")
    check(rc == 0, "the state validates after the change")
    state = read_json(os.path.join(host, ".gtt/ade.json"))
    state["primary"] = "kiro"
    save_json(os.path.join(host, ".gtt/ade.json"), state)
    rc, env, _ = op(host, "ade.validate")
    check(rc == 1, "exactly one Primary, and it participates: a violating state fails validation")


def cursor_and_openhands(project, tmp):
    print("[ADE] Cursor and OpenHands: registry-driven overlays, only GTT's own files owned")
    reg = {a["id"]: a for a in json.loads(contract(project, "show", "ade-registry")[1])["ades"]}
    check(reg["cursor"]["owned_paths"] == [".cursor/rules/gtt.mdc", ".cursor/rules/gtt-implementation.mdc", ".cursor/hooks.json"]
          and reg["cursor"]["handoff"]["instruction_entry"] == ".cursor/rules/gtt.mdc",
          "Cursor integrates through two project rules and a hooks file, and GTT owns exactly those")
    check(reg["openhands"]["owned_paths"] == [".agents/skills/gtt/SKILL.md", ".openhands/hooks.json"] and reg["openhands"]["handoff"]["instruction_entry"].endswith("GENTS.md"),
          "OpenHands reads the portable contract as its entry point, plus one repository skill and a hooks file")
    with open(os.path.join(project, ".cursor/rules/gtt.mdc"), encoding="utf-8") as handle:
        rule = handle.read()
    check(rule.startswith("---\n") and "alwaysApply: true" in rule.split("---")[1] and "@gtt" in rule,
          "the Cursor rule is always applied and tells Cursor how to speak for GTT")
    with open(os.path.join(project, ".agents/skills/gtt/SKILL.md"), encoding="utf-8") as handle:
        front = handle.read().split("---")[1]
    check("name: gtt\n" in front and "description:" in front, "the OpenHands skill carries the name and description its loader requires")
    host = make_host(project, tmp, "co-host")
    write(os.path.join(host, ".cursor", "rules", "team.mdc"), "---\nalwaysApply: true\n---\nthe host's own\n")
    write(os.path.join(host, ".openhands", "setup.sh"), "echo the host's own\n")
    cand = {c["id"]: c for c in data(op(host, "ade.detect")[1])["candidates"]}
    check(cand["cursor"]["status"] == "candidate" and cand["openhands"]["status"] == "candidate", "both are detected as candidates, never as participating")
    rc, env, _ = op(host, "ade.install", **{"from": project, "participating": "cursor,openhands", "primary": "cursor", "apply": True})
    st = data(op(host, "ade.state")[1])
    check(rc == 0 and st["primary"] == "cursor" and st["participating"] == ["cursor", "openhands"] and st["excluded"] == ["antigravity", "claude", "codex", "copilot", "kiro"],
          "a project may run on Cursor and OpenHands alone", env["stderr"][-300:])
    check(all(os.path.isfile(os.path.join(host, f)) for f in (".cursor/rules/gtt.mdc", ".cursor/rules/gtt-implementation.mdc", ".agents/skills/gtt/SKILL.md"))
          and not os.path.exists(os.path.join(host, ".claude")) and not os.path.exists(os.path.join(host, ".kiro")),
          "only the chosen overlays are installed")
    check(os.path.isfile(os.path.join(host, ".cursor/rules/team.mdc")) and os.path.isfile(os.path.join(host, ".openhands/setup.sh")),
          "the host's own Cursor rule and OpenHands setup are untouched")
    rc, env, _ = op(host, "ade.validate")
    check(rc == 0, "the Cursor + OpenHands state validates", env["stderr"][-300:])
    pol = data(op(host, "export-policy")[1])["clean_export"]
    check(".cursor/rules/gtt.mdc" in pol["exclude"] and ".cursor/rules/team.mdc" not in pol["exclude"]
          and ".cursor/" not in pol["exclude"] and ".agents/" not in pol["exclude"],
          "export excludes GTT's own rule files, never the host's or the ADE directories by name", str(pol["exclude"])[-300:])


def antigravity(project, tmp):
    print("[ADE] Antigravity: its own id, three owned files inside a shared .agents/, never a merge")
    owned = [".agents/rules/gtt.md", ".agents/rules/gtt-implementation.md", ".agents/hooks.json"]
    reg = {a["id"]: a for a in json.loads(contract(project, "show", "ade-registry")[1])["ades"]}
    check(reg["antigravity"]["owned_paths"] == owned and reg["antigravity"]["handoff"]["instruction_entry"].endswith("GENTS.md")
          and reg["antigravity"]["enforcement"] == "realtime-hook-unverified",
          "Antigravity is an ADE of its own: the portable contract as entry point, two rules and a hooks file, hook unverified")
    with open(os.path.join(project, ".agents/rules/gtt.md"), encoding="utf-8") as handle:
        rule = handle.read()
    check(rule.startswith("---\n") and "trigger: always_on" in rule.split("---")[1] and "@gtt" in rule and "gtt-session-context.sh" in rule,
          "the Antigravity rule is always on, says how to speak for GTT and tells the agent to run the session service")
    check(len(rule) < 12000 and "## Non-negotiable rules" not in rule and "## Human Promotion Boundary" not in rule,
          "the rule is short and refers to the agent contract instead of copying it")
    hooks = read_json(os.path.join(project, ".agents/hooks.json"))
    entry = hooks["gtt-protect"]["PreToolUse"][0]
    check("gtt_protect.py hook --format antigravity" in entry["hooks"][0]["command"]
          and set(entry["matcher"].split("|")) == {"run_command", "write_to_file", "replace_file_content", "multi_replace_file_content"},
          ".agents/hooks.json points Antigravity's pre-tool hook at the shared engine, for its shell and write tools")

    host = make_host(project, tmp, "ag-host")
    write(os.path.join(host, ".agents", "skills", "other", "SKILL.md"), "---\nname: other\ndescription: the host's own\n---\n")
    cand = {c["id"]: c for c in data(op(host, "ade.detect")[1])["candidates"]}
    check(not cand["antigravity"]["signals"], "a shared .agents/skills/ does not make Antigravity a candidate")
    write(os.path.join(host, ".agents", "rules", "team.md"), "---\ntrigger: always_on\n---\nthe host's own\n")
    cand = {c["id"]: c for c in data(op(host, "ade.detect")[1])["candidates"]}
    check(cand["antigravity"]["status"] == "candidate" and cand["antigravity"]["signals"], "its own rules directory makes it a candidate, never a participant")
    rc, env, _ = op(host, "ade.install", **{"from": project, "participating": "antigravty", "primary": "antigravty", "apply": True})
    check(rc != 0 and not os.path.exists(os.path.join(host, ".gtt/ade.json")), "an unknown ADE id is refused and nothing is written")
    rc, env, _ = op(host, "ade.install", **{"from": project, "participating": "antigravity", "primary": "antigravity"})
    check(rc == 0 and not os.path.exists(os.path.join(host, ".gtt/ade.json")) and not os.path.exists(os.path.join(host, ".agents/hooks.json")),
          "install is a dry run by default")
    rc, env, _ = op(host, "ade.install", **{"from": project, "participating": "antigravity,openhands", "primary": "antigravity", "apply": True})
    st = data(op(host, "ade.state")[1])
    check(rc == 0 and st["primary"] == "antigravity" and st["participating"] == ["antigravity", "openhands"],
          "Antigravity can be the Primary ADE, and shares .agents/ with OpenHands without a conflict", env["stderr"][-300:])
    check(all(os.path.isfile(os.path.join(host, f)) for f in owned + [".agents/skills/gtt/SKILL.md"]) and not os.path.exists(os.path.join(host, ".claude")),
          "exactly the chosen overlays are installed")
    rc, env, _ = op(host, "ade.validate")
    check(rc == 0, "the Antigravity + OpenHands state validates", env["stderr"][-300:])
    pol = data(op(host, "export-policy")[1])["clean_export"]
    check(all(f in pol["exclude"] for f in owned) and ".agents/rules/team.md" not in pol["exclude"] and ".agents/" not in pol["exclude"],
          "export excludes GTT's three files, never the host's rule or .agents/ by name", str(pol["exclude"])[-300:])
    rc, env, _ = op(host, "ade.remove", ades="openhands", apply=True)
    check(rc == 0 and not os.path.exists(os.path.join(host, ".agents/skills/gtt/SKILL.md")) and all(os.path.isfile(os.path.join(host, f)) for f in owned),
          "removing OpenHands leaves Antigravity's files in the shared directory", env["stderr"][-300:])
    check(os.path.isfile(os.path.join(host, ".agents/rules/team.md")) and os.path.isfile(os.path.join(host, ".agents/skills/other/SKILL.md")),
          "the host's own files under .agents/ are untouched by install and remove")

    for name, own in (("ag-hooks", ".agents/hooks.json"), ("ag-rule", ".agents/rules/gtt.md")):
        host = make_host(project, tmp, name)
        write(os.path.join(host, own), "the host's own\n")
        rc, env, _ = op(host, "ade.install", **{"from": project, "participating": "antigravity", "primary": "antigravity", "apply": True})
        with open(os.path.join(host, own), encoding="utf-8") as handle:
            kept = handle.read() == "the host's own\n"
        written = [f for f in owned if f != own and os.path.exists(os.path.join(host, f))]
        check(rc != 0 and kept and not written and not os.path.exists(os.path.join(host, ".gtt/ade.json")),
              f"a host that already has {own} is a reported conflict: nothing written, nothing merged", env["stderr"][-200:])

    host = make_host(project, tmp, "ag-alone")
    op(host, "ade.install", **{"from": project, "participating": "openhands", "primary": "openhands", "apply": True})
    cand = {c["id"]: c for c in data(op(host, "ade.detect")[1])["candidates"]}
    rc, env, _ = op(host, "ade.validate")
    check(cand["antigravity"]["status"] == "excluded" and not cand["antigravity"]["signals"] and "antigravity" not in env["stdout"],
          "a project that runs OpenHands alone shows no trace of Antigravity")


def questionnaire(project, tmp):
    print("[questionnaire] no design -> contract -> materialize -> ADE handoff")
    rc, out, _ = contract(project, "show", "initial-design")
    q = json.loads(out)["scaffold"]["initial_design"]["questionnaire"]
    check(q["template"] == ".gtt/scaffold/templates/gtt-initial-design-questionnaire.md" and q["output"] and q["version"] and q["contract_version"],
          "the CLI discovers template, output, version and contract_version from the Bootstrap")
    check(q["handoff"]["reader"] == "the Primary ADE", "the handoff names the Primary ADE")
    rc, out, _ = contract(project, "show", "elicitation")
    eli = json.loads(out)
    ids = {d["id"] for d in eli["directives"]}
    need = {"inspect-existing-evidence", "ask-progressively", "avoid-redundant-questions", "identify-missing-information", "identify-conflicts",
            "mark-proposals", "preserve-provenance", "ask-human-for-decisions", "do-not-invent-architecture"}
    check(need <= ids, "the guided-elicitation contract has every required directive", str(need - ids))
    host = make_host(project, tmp, "q-host")
    rc, env, _ = op(host, "project.detect")
    det = data(env)
    check(det["questionnaire"]["offer"] and det["design_sources"]["candidates_at_root"] == [], "no design document -> the questionnaire is offered")
    write(os.path.join(host, "design-notes.md"), "# notes\n")
    det = data(op(host, "project.detect")[1])
    check(not det["questionnaire"]["offer"] and det["design_sources"]["candidates_at_root"] == ["design-notes.md"],
          "a candidate document is reported, not assumed, and the questionnaire is not offered")
    check(det["assessment"]["offer"] and det["assessment"]["template"] == "design-assessment" and det["assessment"]["verdicts"] == ["STRONG", "ADEQUATE", "POOR"]
          and not det["design_sources"]["multiple"] and not det["design_sources"]["resolution"]["required"],
          "a design document -> its assessment is offered")
    write(os.path.join(host, "requirements.md"), "# reqs\n")
    det = data(op(host, "project.detect")[1])
    check(det["design_sources"]["multiple"] and det["design_sources"]["resolution"]["required"]
          and det["design_sources"]["resolution"]["options"] == ["CONSOLIDATE", "KEEP_AS_SOURCES"] and "never inferred" in det["design_sources"]["resolution"]["decided_by"],
          "several documents -> consolidate or keep as sources, decided by the human")
    rc, env, _ = op(host, "template.materialize", id="design-assessment", apply=True)
    with open(os.path.join(host, "gtt-domain/proposals/bootstrap/design-assessment.md"), encoding="utf-8") as handle:
        text = handle.read()
    check(rc == 0 and all(x in text for x in ("## 4. Minimum floor", "The technology stack is decided", "`POOR`", "CONSOLIDATE", "KEEP_AS_SOURCES", "[PROPUESTA]")),
          "the assessment carries the floor (stack decided), the verdict and the stack options", env["stderr"])
    check(data(op(host, "project.detect")[1])["assessment"]["working_copy_exists"], "the assessment working copy is detected")
    os.remove(os.path.join(host, "gtt-domain/proposals/bootstrap/design-assessment.md"))
    os.remove(os.path.join(host, "requirements.md"))
    os.remove(os.path.join(host, "design-notes.md"))
    rc, env, _ = op(host, "template.materialize", id="initial-design-questionnaire", apply=True)
    target = os.path.join(host, q["output"])
    same = os.path.isfile(target) and open(target, "rb").read() == open(os.path.join(host, q["template"]), "rb").read()
    check(rc == 0 and same, "materialize creates the working copy verbatim (the CLI holds no copy)", env["stderr"])
    rc, env, _ = op(host, "template.materialize", id="initial-design-questionnaire", apply=True)
    check(rc == 1 and "CONFLICT" in env["stderr"], "a filled working copy is never overwritten")
    bad = fresh(project, tmp, "q-bad")
    tpl = os.path.join(bad, q["template"])
    text = open(tpl, encoding="utf-8").read().replace("Operating Contract for the ADE", "Renamed")
    write(tpl, text)
    rc, out, _ = contract(bad, "check")
    check(rc == 1 and "elicitation directive" in out, "the elicitation contract stays tied to the questionnaire's own structure", out[-200:])


def sources(project, tmp):
    print("[initial sources] selected source != governed authority")
    p = fresh(project, tmp, "src")
    write(os.path.join(p, "docs/spec.md"), "# spec\n")
    rc, env, _ = op(p, "source.select", path="docs/spec.md", type="design-document", version="2.1", by="cli")
    check(rc == 0 and not os.path.exists(os.path.join(p, ".gtt/selected-sources.json")), "select is a dry run by default")
    rc, env, _ = op(p, "source.select", path="docs/spec.md", type="design-document", version="2.1", by="cli", apply=True)
    rows = data(op(p, "source.list")[1])["selected"]
    r = rows[0]
    check(rc == 0 and r["path"] == "docs/spec.md" and r["type"] == "design-document" and r["version"] == "2.1" and r["selected_by"] == "cli"
          and r["authority_status"] == "unassigned" and r["precedence_status"] == "unassigned",
          "path, type, selection metadata and version are kept; authority and precedence are unassigned")
    rc, env, _ = op(p, "source.select", path="docs/spec.md", type="design-document", apply=True)
    check(rc == 1, "a source is selected once")
    rc, env, _ = op(p, "source.select", path="docs/none.md", type="other", apply=True)
    check(rc == 1, "a source that does not exist is refused")
    rc, env, _ = op(p, "source.select", path="../outside.md", type="other", apply=True)
    check(rc != 0, "a path outside the project is refused")
    write(os.path.join(p, "gtt-domain/context/sources.md"),
          "# Sources\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md\n\n"
          "```gtt-sources\nspec | docs/spec.md | 2.1 | primary | 1 | active\n```\n")
    r = data(op(p, "source.list")[1])["selected"][0]
    check(r["governed"] and r["authority_status"] == "primary" and r["precedence_status"] == 1,
          "authority and precedence appear only once a human declares them in the governed manifest")
    check("never inferred" in data(op(p, "source.list")[1])["rule"], "the Bootstrap states that authority is never inferred")


def export_and_clean(project, tmp):
    print("[export policy] Bootstrap policy -> CLI export -> correct GTT exclusions")
    host = make_host(project, tmp, "exp-host")
    write(os.path.join(host, ".claude", "keep-me.txt"), "the host's own claude file\n")
    op(host, "ade.install", **{"from": project, "participating": "claude,codex", "primary": "claude", "apply": True})
    pol = data(op(host, "export-policy")[1])["clean_export"]
    check(all(x in pol["exclude"] for x in (".gtt/", "gtt-domain/", "AGENTS.md", "readme-gtt.md", "SOURCE-BRIEF.*")), "GTT-owned content is excluded")
    check(".claude/CLAUDE.md" in pol["exclude"] and ".claude/keep-me.txt" not in pol["exclude"],
          "ADE overlays come from the ownership ledger; the host's own ADE files are not excluded")
    check(".claude" not in pol["exclude"] and ".claude/" not in pol["exclude"], "an ADE directory is never excluded by name")
    with open(os.path.join(host, ".claude/CLAUDE.md"), "a", encoding="utf-8") as handle:
        handle.write("local edit\n")
    pol = data(op(host, "export-policy")[1])["clean_export"]
    check(any(".claude/CLAUDE.md" in c for c in pol["requires_confirmation"]) and ".claude/CLAUDE.md" not in pol["exclude"],
          "a modified GTT file needs confirmation instead of being dropped silently")
    before = tree_hash(host)
    rc, env, _ = op(host, "clean.plan")
    plan = data(env)
    check(rc == 0 and plan["removes_nothing"] and ".gtt/" in plan["would_remove"] and "export --clean" in plan["distinct_from"], "clean.plan is distinct from export --clean")
    check(tree_hash(host) == before, "neither policy nor plan modified the project")


def recovery(project, tmp):
    print("[recovery] snapshot -> clean -> detect -> restore -> validate")
    host = make_host(project, tmp, "rec-host")
    op(host, "ade.install", **{"from": project, "participating": "claude,codex", "primary": "codex", "apply": True})
    op(host, "methodology.profile.set", profile="hard", language="es", apply=True)
    write(os.path.join(host, "docs/spec.md"), "# spec\n")
    op(host, "source.select", path="docs/spec.md", type="design-document", by="cli", apply=True)
    snap_path = os.path.join(tmp, "snapshot.json")
    rc, env, _ = op(host, "recovery.snapshot", output=snap_path)
    snap = read_json(snap_path)
    for key in ("bootstrap", "compatibility", "ade", "methodology", "sources", "operational", "recovery"):
        check(key in snap, f"snapshot carries `{key}`")
    check(snap["bootstrap"]["version"] == "1.3.1" and snap["ade"]["primary"] == "codex" and snap["methodology"] == {"profile": "hard", "language": "es"}
          and snap["sources"]["selected"][0]["path"] == "docs/spec.md", "identity, Primary, profile, language and selected sources are preserved")
    rc, env, _ = op(host, "recovery.snapshot", output=snap_path)
    check(env["exit_code"] == 1, "a snapshot is never overwritten")
    # clean the GTT configuration
    op(host, "ade.remove", all=True, apply=True)
    for f in (".gtt/methodology.json", ".gtt/selected-sources.json"):
        if os.path.exists(os.path.join(host, f)):
            os.remove(os.path.join(host, f))
    det = data(op(host, "project.detect")[1])
    check(not det["ade_configured"] and det["methodology"]["source"] == "default", "detect sees the cleaned project")
    rc, env, _ = op(host, "recovery.restore", snapshot=snap_path)
    check(rc == 0 and not os.path.exists(os.path.join(host, ".gtt/methodology.json")), "restore is a dry run by default")
    rc, env, _ = op(host, "recovery.restore", snapshot=snap_path, **{"from": project, "apply": True})
    st = data(op(host, "ade.state")[1])
    check(rc == 0 and st["primary"] == "codex" and st["participating"] == ["claude", "codex"], "the ADE state is restored (overlays reinstalled from the catalog)", env["stderr"])
    check(data(op(host, "methodology.profile.get")[1])["profile"] == "hard" and data(op(host, "methodology.profile.get")[1])["language"] == "es",
          "profile and language are restored")
    check(data(op(host, "source.list")[1])["selected"][0]["path"] == "docs/spec.md", "selected sources are restored")
    rc, env, _ = op(host, "ade.validate")
    check(rc == 0, "the restored ADE state validates")
    rc, env, _ = op(host, "recovery.restore", snapshot=snap_path, apply=True)
    check(not os.path.exists(os.path.join(host, "gtt-domain/.frozen")), "restore never writes a freeze marker")
    # refusals
    for label, mutate in (("newer schema", lambda s: s.update(schema=2)),
                          ("another bootstrap", lambda s: s["bootstrap"].update(id="someone-else")),
                          ("missing field", lambda s: s.pop("ade")),
                          ("unknown profile", lambda s: s["methodology"].update(profile="extreme"))):
        bad = json.loads(json.dumps(snap))
        mutate(bad)
        path = os.path.join(tmp, f"bad-{label.replace(' ', '-')}.json")
        save_json(path, bad)
        rc, env, _ = op(host, "recovery.restore", snapshot=path, apply=True)
        check(env["exit_code"] == 1 and "REFUSED" in env["stderr"], f"restore refuses: {label}")
    write(os.path.join(host, "gtt-domain/.frozen"), "2026-01-01T00:00:00Z\n")
    relax = json.loads(json.dumps(snap))
    relax["methodology"]["profile"] = "light"
    path = os.path.join(tmp, "relax.json")
    save_json(path, relax)
    rc, env, _ = op(host, "recovery.restore", snapshot=path, apply=True)
    check(env["exit_code"] == 1 and "relax" in env["stderr"], "a frozen project refuses a snapshot that would relax the profile")


def session_status_validation(project, tmp):
    print("[session / status / validation] deterministic, structured, derived from the project")
    p = fresh(project, tmp, "ssv")
    subprocess.run(["git", "init", "-q"], cwd=p)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"], cwd=p)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "test commit"], cwd=p)
    write(os.path.join(p, "untracked.txt"), "x\n")
    rc, env, _ = op(p, "session-context")
    s = data(env)
    need = {"freeze", "change_request", "proposals", "validation", "git", "operational", "artifacts"}
    check(rc == 0 and need <= set(s), "the session contract identifies freeze, change request, proposals, validation, git, operational state and artifacts", str(need - set(s)))
    check(s["authority"] == "none" and s["operational_only"] and "NOT authority" in s["markers"], "it declares itself non-authoritative")
    check(s["git"]["available"] and s["git"]["uncommitted_paths"] >= 1 and s["git"]["recent_commits"][0].endswith("test commit"), "git state comes from the repository")
    check(s["change_request"] == "empty" and s["freeze"]["frozen"] is False, "freeze and change request come from the actual files")
    rc, env, _ = op(p, "status")
    st = data(env)
    need = {"bootstrap", "ade", "methodology", "sources", "governance", "freeze", "validation", "session"}
    check(rc == 0 and need <= set(st) and st["bootstrap"]["version"] == "1.3.1", "the status contract has every section", str(need - set(st)))
    rc, env, _ = op(p, "validation.run")
    v = data(env)
    check(rc == 0 and v["result"] == "pass" and any(c["check"].startswith("gtt-check-contract.sh") and c["result"] == "pass" for c in v["checks"]),
          "validation.run is one structured entry point that includes the contract gate", str(v)[:300])
    write(os.path.join(p, "gtt-domain/context/architecture.md"), "# Architecture\n\n[PROPUESTA] something\n")
    rc, env, _ = op(p, "validation.run")
    v = data(env)
    check(rc == 1 and v["result"] == "fail" and "gtt-check-provenance.sh" in v["failing"], "a violation surfaces as a failing check", str(v)[:200])
    check(any("[PROPUESTA]" in m for m in v["messages"]) and not any(c["check"].startswith(("FAIL", "WARN")) for c in v["checks"]),
          "detail lines are reported as messages, never mistaken for checks", str(v)[:200])
    rc, env, _ = op(p, "session-context.text")
    check(rc == 0 and "GTT-SESSION-CONTEXT" in env["stdout"], "the text session context remains available")


def developer_experience(project, tmp):
    print("[developer experience] deterministic work is done, not asked; reports are brief; protected operations still need the human")
    p = fresh(project, tmp, "dx")
    spec = json.loads(contract(p, "show", "profiles")[1])
    dx = spec["developer_experience"]
    check(all(dx[k] is True for k in ("minimize_interruption", "automatic_deterministic_operations", "concise_reports", "details_on_demand")),
          "the policy is declared for every plan")
    check(dx["protected_operations"]["agent_executes"] is False and len(dx["stop_conditions"]) == 6,
          "protected operations stay with the human; STOP has a closed list of reasons")
    planes = spec["two_planes"]
    check([level["id"] for level in planes["levels"]] == ["NOTICE", "WARNING", "GOVERNANCE", "BLOCKING"]
          and [level["work"] for level in planes["levels"]][:3] == ["continues"] * 3,
          "the two planes are data: four named levels, and work continues at every one but BLOCKING")
    check("Stories and the working plan" in planes["work"]["holds"] and "Epics (goal and scope)" in planes["governance"]["holds"]
          and "no approval" in planes["work"]["authority"],
          "Epics belong to Governance; Stories and the implementation belong to Work, which asks for no approval")
    ids = {inv["id"] for inv in spec["invariants"]}
    check({"autonomous-work", "non-blocking-continuity", "explicit-blocking", "deterministic-first", "session-state-is-derived"} <= ids
          and not any(inv["relaxable"] for inv in spec["invariants"]),
          "autonomous work, non-blocking continuity and explicit blocking are invariants no plan relaxes")
    check(data(op(p, "methodology.profile.get")[1])["developer_experience"]["report"]["default"] == "brief",
          "the CLI receives the policy with the plan")
    talk = data(op(p, "methodology.profile.get")[1])["developer_experience"]["dialogue"]
    check(talk["marker"] == "@gtt" and all(e.startswith("@gtt") for e in talk["examples"]) and talk["authority"].startswith("none"),
          "GTT's dialogue is identified by its marker, which carries no authority")
    with open(os.path.join(p, ".gtt/scaffold/templates/gtt-initial-design-questionnaire.md"), encoding="utf-8") as handle:
        check("`@gtt · Initial Design Questionnaire`" in handle.read(), "the questionnaire tells the ADE to open every turn with the marker")
    q = fresh(project, tmp, "dx-marker")
    broken = read_json(os.path.join(q, ".gtt/contract/profiles.json"))
    broken["developer_experience"]["dialogue"]["authority"] = "the marker approves"
    save_json(os.path.join(q, ".gtt/contract/profiles.json"), broken)
    rc, out, err = bash(q, ".gtt/scripts/gtt-check-contract.sh")
    check(rc == 1 and "dialogue.authority must be none" in out + err, "a marker that claims authority fails the contract check", (out + err)[-200:])
    # the next free id is determined, never asked for
    h = tree_hash(p)
    rc, env, _ = op(p, "artifact.next-id", kind="adr")
    first = data(env)
    check(rc == 0 and first["id"] not in first["occupied"] and "ADR-001" in first["occupied"], "the next free ADR id is determined from the project", str(first))
    check(data(op(p, "artifact.next-id", kind="epic")[1])["id"] == "EPIC-001", "a template example Epic does not occupy an id")
    got = data(op(p, "artifact.next-id", kind="adr", requested="ADR-001")[1])
    check(got["requested"]["free"] is False and got["id"] == first["id"], "an occupied id resolves to the next free one, with no question")
    check(tree_hash(p) == h, "resolving an id reserves and writes nothing")
    write(os.path.join(p, "gtt-domain/adr", first["id"] + "-example.md"), "# " + first["id"] + " - example\n")
    after = data(op(p, "artifact.next-id", kind="adr")[1])
    check(int(after["id"].split("-")[1]) == int(first["id"].split("-")[1]) + 1, "a newly taken id moves the answer on")
    os.remove(os.path.join(p, "gtt-domain/adr", first["id"] + "-example.md"))
    rc, env, _ = op(p, "artifact.next-id", kind="widget")
    check(rc == 5, "an unknown kind is refused by the argument schema")
    # post-operation maintenance: one run, brief by default, detail on demand
    rc, out, err = bash(p, ".gtt/scripts/gtt-maintain.sh")
    lines = [l for l in out.splitlines() if l.strip()]
    check(rc == 0 and len(lines) <= 4 and not any(l.startswith("PASS") for l in lines) and "Validation:" in out,
          "maintain reports in a few lines", out + err)
    rc, out, _ = bash(p, ".gtt/scripts/gtt-maintain.sh", "--verbose")
    check(rc == 0 and "PASS" in out and "gtt-validate: OK" in out, "the full detail is available on demand")
    rc, env, _ = op(p, "maintain")
    check(rc == 0 and env["exit_code"] == 0, "maintain runs through the operation registry")
    for cmd in (["init", "-q", "."], ["add", "-A"], ["-c", "user.name=gtt", "-c", "user.email=gtt@example.invalid", "commit", "-qm", "base"],
                ["mv", ".gtt/docs/usage.md", ".gtt/docs/usage-moved.md"]):       # a real rename, as a developer would do it
        subprocess.run(["git", *cmd], cwd=p, capture_output=True, check=True)
    rc, out, _ = bash(p, ".gtt/scripts/gtt-maintain.sh")
    check(rc == 1 and "need reconciling" in out and "gtt-reconcile.sh" in out and os.path.isfile(os.path.join(p, ".gtt/docs/usage-moved.md")),
          "maintain does not rewrite references on its own: it stops with the exact command", out)
    # the same rule, a different effect per plan
    expect = {"light": (True, "use", []), "medium": (False, "use", ["agent_context_sync", "reference_updates", "relevant_change"]),
              "hard": (False, "propose", ["agent_context_sync", "identity_resolution", "reference_updates", "relevant_change"]),
              "team": (False, "propose", ["agent_context_sync", "identity_resolution", "reference_updates", "relevant_change"])}
    for choice, (reconciles, resolution, extra) in expect.items():
        op(p, "methodology.profile.set", profile=choice, apply=True)
        got = data(op(p, "methodology.profile.get")[1])["interaction"]
        check(got["maintain_reconciles_moves"] is reconciles and got["id_resolution"] == resolution
              and sorted(set(got["asks_for"]) - {"governed_decision", "destructive"}) == extra
              and {"governed_decision", "destructive"} <= set(got["asks_for"]),
              f"{choice}: asks for governed decisions, destructive operations and {extra or 'nothing else'}", str(got))
        check(data(op(p, "artifact.next-id", kind="adr")[1])["resolution"] == resolution, f"{choice}: an id is to {resolution}")
        if not reconciles:
            rc, out, _ = bash(p, ".gtt/scripts/gtt-maintain.sh")
            check(rc == 1 and "need reconciling" in out and choice in out, f"{choice}: maintain stops before rewriting references", out)
    op(p, "methodology.profile.set", profile="light", apply=True)
    rc, out, err = bash(p, ".gtt/scripts/gtt-maintain.sh")
    check(rc == 0 and "Reconciled 1 moved artifact(s)" in out and "usage-moved.md" in out,
          "light: maintain reconciles the unambiguous move, says so, and validates", out + err)
    os.remove(os.path.join(p, ".gtt/docs/usage-moved.md"))
    rc, out, _ = bash(p, ".gtt/scripts/gtt-maintain.sh")
    check(rc == 1 and "need your decision" in out, "light: a missing artifact is still a decision, never resolved automatically", out)
    check(all(os.access(f, os.X_OK) for f in glob.glob(os.path.join(p, ".gtt/scripts/*.sh")) + glob.glob(os.path.join(p, "gtt-domain/proposals/*.sh"))),
          "every shipped script is directly executable")
    # lower friction can never hand a protected operation to the agent
    bad = fresh(project, tmp, "dx-bad")
    spec = read_json(os.path.join(bad, ".gtt/contract/profiles.json"))
    spec["developer_experience"]["protected_operations"]["agent_executes"] = True
    spec["developer_experience"]["automatic_operations"].append({"what": "freeze", "operation": "freeze"})
    save_json(os.path.join(bad, ".gtt/contract/profiles.json"), spec)
    rc, out, _ = contract(bad, "check")
    check(rc == 1 and "agent_executes must be false" in out and "needs human authority" in out,
          "a policy that automates a human-authority operation fails the contract check", out)


def fresh_host(project, tmp):
    print("[fresh host] install -> reconcile the catalog identity -> index -> validation.run")
    host = make_host(project, tmp, "fresh-host")
    for kit in ("readme-gtt.md", "readme-gtt.es.md"):
        shutil.copy2(os.path.join(project, kit), host)
    rc, env, _ = op(host, "ade.install", **{"from": project, "participating": "claude", "primary": "claude", "apply": True})
    rc, env, _ = op(host, "validation.run")
    check(env["exit_code"] == 1 and "gtt-check-integrity.sh" in data(env)["failing"],
          "a fresh host still carries the catalog's identity manifest: integrity fails until it is reconciled")
    before = tree_hash(host)
    rc, env, _ = op(host, "reconcile", retire_missing=True)
    check(rc == 0 and "dry run" in env["stdout"] and tree_hash(host) == before, "reconcile retire_missing is a dry run by default")
    rc, env, _ = op(host, "reconcile", retire_missing=True, apply=True)
    check(rc == 0, "reconcile retire_missing apply=true retires only registered paths that are gone", env["stderr"][:200])
    rc, env, _ = op(host, "index")
    rc, env, _ = op(host, "validation.run")
    check(env["exit_code"] == 0 and data(env)["result"] == "pass", "after reconcile and index the fresh host validates", str(data(env))[:200])


def any_ade_alone(project, tmp):
    print("[ADE matrix] every ADE works alone: install -> reconcile -> index -> validation.run")
    for ade in ("antigravity", "claude", "codex", "copilot", "cursor", "kiro", "openhands"):
        host = make_host(project, tmp, f"alone-{ade}")
        for kit in ("readme-gtt.md", "readme-gtt.es.md"):
            shutil.copy2(os.path.join(project, kit), host)
        rc, env, _ = op(host, "ade.install", **{"from": project, "participating": ade, "primary": ade, "apply": True})
        op(host, "reconcile", retire_missing=True, apply=True)
        op(host, "index")
        rc, env, _ = op(host, "validation.run")
        v = data(env)
        check(env["exit_code"] == 0 and v["result"] == "pass", f"a project whose only ADE is {ade} validates", str(v.get("failing"))[:200] + str(v.get("messages"))[:200])
        if ade != "claude":
            check(any(c["result"] == "skipped" and c["check"].startswith("gtt-check-session-adapter.sh claude") for c in v["checks"]),
                  f"{ade}: the session adapter of an ADE that does not participate is skipped, never failed")
    host = make_host(project, tmp, "alone-claude-broken")
    for kit in ("readme-gtt.md", "readme-gtt.es.md"):
        shutil.copy2(os.path.join(project, kit), host)
    op(host, "ade.install", **{"from": project, "participating": "claude", "primary": "claude", "apply": True})
    op(host, "reconcile", retire_missing=True, apply=True)
    op(host, "index")
    os.remove(os.path.join(host, ".claude/hooks/session-start.py"))
    rc, env, _ = op(host, "validation.run")
    check(env["exit_code"] == 1 and any(f.startswith("gtt-check-session-adapter.sh claude") for f in data(env)["failing"]),
          "a participating ADE's session adapter is still checked against its native paths", str(data(env)["failing"])[:200])


def protection_hooks(project, tmp):
    print("[protection hooks] Cursor and OpenHands: one engine, each ADE's documented payload in, its deny shape out")
    p = fresh(project, tmp, "hooks")
    root = p.replace("\\", "/")
    engine = os.path.join(".gtt", "scripts", "gtt_protect.py")
    governed_file = "AGENTS" + ".md"
    script = "gtt-domain/proposals/apply-ADR-009-x.sh"

    def hook(fmt, event):
        proc = subprocess.run([sys.executable, engine, "hook", "--format", fmt], cwd=p, input=json.dumps(event) if isinstance(event, dict) else event,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            return proc.returncode, json.loads(proc.stdout)
        except ValueError:
            return proc.returncode, None

    def cursor(tool, **tool_input):
        return hook("cursor", {"hook_event_name": "preToolUse", "tool_name": tool, "tool_input": tool_input, "workspace_roots": [root]})

    def openhands(tool, **tool_input):
        return hook("openhands", {"event_type": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "working_dir": root})

    def ag(tool, **args):
        return hook("antigravity", {"toolCall": {"name": tool, "args": args}, "stepIdx": 1, "workspacePaths": [root]})

    rc, out = ag("write_to_file", TargetFile=f"{root}/{governed_file}", CodeContent="x")
    check(rc == 2 and out["decision"] == "deny" and out["reason"], "Antigravity: a write to the agent contract is denied, in Antigravity's shape")
    check(ag("write_to_file", TargetFile=f"{root}/src/app.py")[0] == 0 and ag("write_to_file", TargetFile=f"{root}/gtt-domain/proposals/PROPOSAL-x.md")[0] == 0,
          "Antigravity: implementation code and the proposals directory stay writable")
    rc, out = ag("run_command", CommandLine=f"bash {script}", Cwd=root)
    check(rc == 2 and "run by the human" in out["reason"], "Antigravity: an agent never executes a promotion script")
    check(ag("run_command", CommandLine=f"cat {governed_file}")[0] == 0 and ag("run_command", CommandLine=f"sed -i s/a/b/ {governed_file}")[0] == 2,
          "Antigravity: reading a governed file stays allowed, mutating it through the shell is denied")
    check(ag("run_command", CommandLine="rm .agents/hooks.json")[0] == 2 and ag("write_to_file", TargetFile=f"{root}/.agents/hooks.json")[0] == 2,
          "Antigravity: the agent cannot disarm its own protection")
    check(ag("read_file", TargetFile=f"{root}/{governed_file}") == (0, None) and hook("antigravity", {"invocationNum": 1, "workspacePaths": [root]}) == (0, None),
          "Antigravity: an unknown tool and an event that is not a tool call pass untouched")
    check(hook("antigravity", "not json") == (0, None) and hook("antigravity", {"toolCall": {"name": "write_to_file"}}) == (0, None)
          and hook("antigravity", {"toolCall": "x"}) == (0, None),
          "Antigravity: a malformed event never blocks a session")

    for name, cfg in ((".cursor/hooks.json", lambda d: d["hooks"]["preToolUse"][0]["command"]),
                      (".openhands/hooks.json", lambda d: d["pre_tool_use"][0]["hooks"][0]["command"])):
        check("gtt_protect.py hook --format" in cfg(read_json(os.path.join(p, name))), f"{name} points its pre-tool hook at the shared engine")

    rc, out = cursor("Write", file_path=f"{root}/{governed_file}")
    check(rc == 2 and out["permission"] == "deny" and out["agent_message"], "Cursor: a write to the agent contract is denied, in Cursor's shape")
    rc, out = cursor("Write", file_path=f"{root}/src/app.py")
    check(rc == 0 and out is None, "Cursor: ordinary implementation code is not touched")
    rc, out = cursor("Shell", command=f"bash {script}")
    check(rc == 2 and "run by the human" in out["agent_message"], "Cursor: an agent never executes a promotion script")
    rc, out = cursor("Shell", command=f"cat {governed_file}")
    check(rc == 0, "Cursor: reading a governed file stays allowed")
    rc, out = cursor("Shell", command="rm .cursor/hooks.json")
    check(rc == 2, "Cursor: the agent cannot disarm its own protection through the shell")
    rc, out = cursor("Write", file_path="gtt-domain/proposals/PROPOSAL-x.md")
    check(rc == 0, "Cursor: the proposals directory is always writable")
    rc, out = hook("cursor", {"hook_event_name": "beforeShellExecution", "command": f"sed -i s/a/b/ {governed_file}", "workspace_roots": [root]})
    check(rc == 2 and out["permission"] == "deny", "Cursor: beforeShellExecution is decided by the same rules")

    rc, out = openhands("terminal", command="rm .openhands/hooks.json")
    check(rc == 2 and out["decision"] == "deny" and out["reason"], "OpenHands: a denial uses OpenHands' shape")
    rc, out = openhands("file_editor", command="view", path=f"{root}/{governed_file}")
    check(rc == 0, "OpenHands: viewing a governed file stays allowed")
    rc, out = openhands("file_editor", command="str_replace", path=f"{root}/{governed_file}", old_str="x")
    check(rc == 2, "OpenHands: editing the agent contract is denied")
    rc, out = openhands("terminal", command=f"bash {script}")
    check(rc == 2, "OpenHands: an unattended run never executes a promotion script")
    rc, out = openhands("file_editor", command="create", path=f"{root}/src/app.py")
    check(rc == 0, "OpenHands: ordinary implementation code is not touched")

    context = "gtt-domain/context/stack.md"
    check(cursor("Write", file_path=context)[0] == 0 and openhands("file_editor", command="create", path=f"{root}/{context}")[0] == 0,
          "before freeze the governed context is writable (bootstrap populates it)")
    check(ag("write_to_file", TargetFile=f"{root}/{context}")[0] == 0, "Antigravity: before freeze the governed context is writable")
    write(os.path.join(p, "gtt-domain/.frozen"), "2026-01-01T00:00:00Z\n")
    check(cursor("Write", file_path=context)[0] == 2 and openhands("file_editor", command="create", path=f"{root}/{context}")[0] == 2
          and cursor("Shell", command=f"rm {context}")[0] == 2,
          "after freeze it is denied on both ADEs: the two-regime condition a static config cannot express")
    check(ag("write_to_file", TargetFile=f"{root}/{context}")[0] == 2 and ag("run_command", CommandLine=f"rm {context}")[0] == 2,
          "Antigravity: after freeze it is denied, by file tool and by shell")

    write(os.path.join(p, "src/billing.py"), "# @GTTGuard reason=audited\ndef charge():\n    return 1\n\n\ndef helper():\n    return 2\n")
    bash(p, ".gtt/scripts/gtt-guard-sync.sh")
    rc, out = cursor("Write", file_path=f"{root}/src/billing.py")
    check(rc == 2 and "GTTGuard" in out["agent_message"], "a GTTGuard-protected artifact is denied when the extent of the write is unknown (fail safe)", str(out)[:200])
    rc, out = openhands("file_editor", command="str_replace", path=f"{root}/src/billing.py", old_str="def helper():\n    return 2")
    check(rc == 0, "an edit to an unprotected symbol next to a protected one stays allowed", str(out)[:200])
    rc, out = openhands("file_editor", command="str_replace", path=f"{root}/src/billing.py", old_str="def charge():\n    return 1")
    check(rc == 2, "an edit to the protected symbol itself is denied", str(out)[:200])
    check(openhands("terminal", command="rm src/billing.py")[0] == 2, "a mutating shell command on a protected artifact is denied")
    guarded, free = "def charge():\n    return 1", "def helper():\n    return 2"
    check(ag("replace_file_content", TargetFile=f"{root}/src/billing.py", TargetContent=guarded)[0] == 2
          and ag("replace_file_content", TargetFile=f"{root}/src/billing.py", TargetContent=free)[0] == 0,
          "Antigravity: an edit inside the protected symbol is denied, one next to it is allowed")
    check(ag("multi_replace_file_content", TargetFile=f"{root}/src/billing.py", ReplacementChunks=[{"TargetContent": free}, {"TargetContent": guarded}])[0] == 2
          and ag("multi_replace_file_content", TargetFile=f"{root}/src/billing.py", ReplacementChunks=[{"TargetContent": free}])[0] == 0,
          "Antigravity: a multi-chunk edit is denied when any chunk reaches the protected symbol")
    check(ag("multi_replace_file_content", TargetFile=f"{root}/src/billing.py", ReplacementChunks="unexpected")[0] == 2
          and ag("write_to_file", TargetFile=f"{root}/src/billing.py")[0] == 2,
          "Antigravity: an edit of unknown extent on a file with a protected symbol fails safe")

    check(hook("cursor", "not json") == (0, None) and hook("openhands", {"event_type": "SomethingNew"}) == (0, None),
          "an unreadable or unknown event never blocks a session")
    rc, out = hook("cursor", {"hook_event_name": "sessionStart", "workspace_roots": [root]})
    check(rc == 0 and "GTT-SESSION-CONTEXT" in out["additional_context"] and "NOT authority" in out["additional_context"],
          "Cursor: session start injects the session context, marked as non-authoritative")
    rc, out = hook("openhands", {"event_type": "SessionStart", "working_dir": root})
    check(rc == 0 and "GTT-SESSION-CONTEXT" in out["additionalContext"], "OpenHands: session start injects the same context in its own field")
    reg = {a["id"]: a for a in json.loads(contract(project, "show", "ade-registry")[1])["ades"]}
    listing = bash(project, ".gtt/scripts/gtt-ade.sh", "list")[1]
    check(".cursor/hooks.json" in reg["cursor"]["owned_paths"] and ".openhands/hooks.json" in reg["openhands"]["owned_paths"]
          and ".agents/hooks.json" in reg["antigravity"]["owned_paths"] and listing.count("realtime-hook-unverified") == 3,
          "the registry states every such hook as shipped but unverified - no ADE is credited with a guarantee it has not proven")


def registry_safety(project, tmp):
    print("[operations] declared only, no arbitrary shell, no unfreeze, fail closed")
    p = fresh(project, tmp, "safe")
    canary = os.path.join(p, "canary")
    rc, env, _ = op(p, "query", term=f"$(touch {canary})")
    check(not os.path.exists(canary), "shell metacharacters in an argument are data, never executed")
    rc, env, _ = op(p, "query", term=f"x; touch {canary}")
    check(not os.path.exists(canary), "a command separator in an argument is not executed")
    rc, out, err = contract(p, "run", "nosuch", "--envelope")
    check(rc == 5, "an undeclared operation is refused")
    rc, env, _ = op(p, "ade.set-primary", ade="--apply")
    check(rc == 5, "an argument that looks like a flag is refused")
    rc, env, _ = op(p, "ade.set-primary", ade="claude", surprise="1")
    check(rc == 5, "an undeclared argument is refused")
    rc, env, _ = op(p, "ade.install", **{"from": project})
    check(rc == 5, "a missing required argument is refused")
    rc, env, _ = op(p, "freeze")
    check(rc == 4, "freeze needs a human decision from the CLI")
    ops = read_json(os.path.join(p, ".gtt/contract/operations.json"))
    check(not any("unfreeze" in k.lower() for k in ops["operations"]), "there is no unfreeze operation")
    def mutated(name, fn, expect):
        q = fresh(project, tmp, name)
        doc = read_json(os.path.join(q, ".gtt/contract/operations.json"))
        fn(doc)
        save_json(os.path.join(q, ".gtt/contract/operations.json"), doc)
        rc, out, _ = contract(q, "check")
        check(rc == 1 and expect in out, f"the contract check rejects: {expect}", out[-200:])
        return q
    mutated("m1", lambda d: d["operations"].update({"unfreeze": dict(d["operations"]["freeze"])}), "no unfreeze operation")
    mutated("m2", lambda d: d["operations"]["index"].update(implementation="/bin/echo"), "existing file under .gtt/scripts/")
    mutated("m3", lambda d: d["operations"]["index"].update(argv=["-c", "rm -rf /; echo"]), "shell syntax")
    mutated("m4", lambda d: d["operations"]["freeze"].update(human_authority=False), "human_authority")
    q = mutated("m5", lambda d: d["operations"]["index"].update(implementation=".gtt/scripts/../../etc/passwd"), "existing file under .gtt/scripts/")
    rc, env, _ = op(q, "index")
    check(rc == 5, "the runner also refuses an untrusted implementation")
    mutated("m6", lambda d: d["operations"]["template.materialize"]["args"].pop(2), "must offer `apply`")


def evolution(project, tmp):
    print("[evolution] Bootstrap content changes work with the CLI source unchanged")
    p = fresh(project, tmp, "evo")
    # new template
    write(os.path.join(p, ".gtt/scaffold/templates/gtt-new-template.md"), "# New template\n\n> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md\n")
    manifest = os.path.join(p, ".gtt/scaffold/manifest.yaml")
    text = open(manifest, encoding="utf-8", newline="").read()
    line = "  - { id: new-template, path: .gtt/scaffold/templates/gtt-new-template.md, kind: file, required: false, use: test, when: test, materialize_to: gtt-domain/proposals/new-template.md, becomes: draft, scaffold: 2, version: 1, contract_version: 1, role: new template }\n"
    anchor = "\nnaming:"
    text = text.replace(anchor, "\n" + line.rstrip("\n") + "\n" + anchor, 1) if "\nnaming:" in text else text
    write(manifest, text)
    rc, env, _ = op(p, "template.list")
    check(any(t["id"] == "new-template" for t in data(env)["templates"]), "a new template is offered with no code change")
    rc, env, _ = op(p, "template.materialize", id="new-template", apply=True)
    check(rc == 0 and os.path.isfile(os.path.join(p, "gtt-domain/proposals/new-template.md")), "and can be materialized through the same operation")
    # new profile semantics
    spec = read_json(os.path.join(p, ".gtt/contract/profiles.json"))
    spec["profiles"]["medium"]["semantics"]["audit_requirements"] = "gtt-audit every sprint (new semantics)"
    save_json(os.path.join(p, ".gtt/contract/profiles.json"), spec)
    check("every sprint" in data(op(p, "methodology.profile.get")[1])["semantics"]["audit_requirements"], "new profile semantics are read from the contract")
    # new ADE using existing primitives
    text = open(manifest, encoding="utf-8", newline="").read()
    ade_line = "  - { id: newade, name: New ADE, path: .newade/, entry: .newade/rules.md, owned: [.newade/], detect: [.newade/], enforcement: ci-gate, scaffold: 2, version: 1, kind: dir, required: false, role: test overlay }\n"
    text = text.replace("\ntemplates:", "\n" + ade_line.rstrip("\n") + "\n\ntemplates:", 1)
    write(manifest, text)
    write(os.path.join(p, ".newade/rules.md"), "# rules\n")
    reg = {a["id"] for a in json.loads(contract(p, "show", "ade-registry")[1])["ades"]}
    check("newade" in reg, "a new ADE appears in the registry with no CLI change")
    host = make_host(p, tmp, "evo-host")
    rc, env, _ = op(host, "ade.install", **{"from": p, "participating": "newade", "primary": "newade", "apply": True})
    check(rc == 0 and os.path.isfile(os.path.join(host, ".newade/rules.md")), "and installs through the existing ADE primitives", env["stderr"])
    # new operation on an existing implementation
    doc = read_json(os.path.join(p, ".gtt/contract/operations.json"))
    doc["operations"]["guard.check"] = dict(doc["operations"]["guard.validate"])
    save_json(os.path.join(p, ".gtt/contract/operations.json"), doc)
    rc, env, _ = op(p, "guard.check")
    check(rc == 0, "a new operation declared over an existing implementation runs through the same runner", env["stderr"])
    rc, out, _ = contract(p, "check")
    check(rc == 0, "the evolved contracts still pass the contract check", out)


def unsupported(project, tmp):
    print("[unsupported capability] Bootstrap requires X, CLI lacks X -> REFUSE -> project unchanged")
    p = fresh(project, tmp, "unsup")
    rel = read_json(os.path.join(p, ".gtt/contract/release.json"))
    rel["requires_cli_capabilities"].append("future.capability.v2")
    save_json(os.path.join(p, ".gtt/contract/release.json"), rel)
    before = tree_hash(p)
    rc, out, _ = contract(p, "negotiate", "--cli-version", "1.0.0", "--cli-capabilities", "contract.negotiate.v1,operation.execute.v1", "--cli-schemas", "1", "--json")
    r = json.loads(out)
    check(rc == 3 and not r["compatible"] and any("future.capability.v2" in x for x in r["reasons"]), "the CLI is told exactly which capability it lacks")
    check(tree_hash(p) == before, "the project is unchanged")
    rc, out, _ = contract(p, "negotiate", "--cli-version", "1.0.0", "--cli-capabilities", "contract.negotiate.v1,operation.execute.v1,future.capability.v2", "--cli-schemas", "1")
    check(rc == 0, "a CLI that has the capability is compatible")


def guard_and_retrieval(project, tmp):
    print("[guard / index / reconcile / query] stable operations")
    p = fresh(project, tmp, "gr")
    for name, kw in (("guard.validate", {}), ("guard.sync", {}), ("index", {}), ("reconcile", {}), ("query", {"term": "Human Promotion Boundary"}),
                     ("query.governance", {"kind": "open"})):
        rc, env, _ = op(p, name, **kw)
        check(rc == 0, f"{name} runs through the operation registry", env["stderr"][:200])
    rc, env, _ = op(p, "query.governance", kind="everything")
    check(rc == 5, "an enum outside its values is refused")


def backlog_model(project, tmp):
    print("[backlog] Epics are approved intent; Stories are the ADE's working plan and need no approval")
    p = fresh(project, tmp, "bl")
    path = os.path.join(p, "gtt-domain", "backlog.md")
    with open(path, encoding="utf-8") as handle:
        base = handle.read()
    check(bash(p, ".gtt/scripts/gtt-check-backlog.sh")[0] == 0, "the shipped template passes (its examples are not real entries)")

    def run(stories, epic="**Status:** Planned\n**Goal:** invoices go out\n**Approved:** MG - 2026-01-15\n"):
        block = "\n### EPIC-900 - Billing\n\n" + epic + "\n#### Stories\n\n" + stories + "\n---\n\n## General Development Work"
        write(path, base.replace("## General Development Work", block, 1))
        rc, out, err = bash(p, ".gtt/scripts/gtt-check-backlog.sh")
        return rc, out + err

    title = "##### STORY-901 - Issue invoices\n\n- **Status:** {}\n"
    for status in ("Planned", "In Progress", "Blocked", "Cancelled"):
        rc, out = run(title.format(status))
        check(rc == 0, f"a Story the ADE wrote on its own may be {status}: nobody approves a Story", out[-300:])
    rc, out = run(title.format("Done"))
    check(rc == 0 and "STORY-901 is `Done` without `Closed`" in out, "a Done Story without its closure is reported, never a failure", out[-300:])
    rc, out = run(title.format("Done") + "- **Closed:** 2026-02-01 - a1b2c3d - 14 tests passed\n")
    check(rc == 0 and "without `Closed`" not in out and "mark it Completed" in out, "a closed Story is clean; an Epic whose Stories are all closed is pointed out", out[-300:])
    for legacy in ("Undesigned", "Ready", "Proposed"):
        check(run(title.format(legacy))[0] == 0, f"a backlog written before this model still reads: `{legacy}` is a planned Story")
    rc, out = run(title.format("Designed"))
    check(rc == 1 and "status outside" in out, "the status vocabulary is closed", out[-300:])

    rc, out = run(title.format("Planned"), epic="**Status:** Proposed\n**Goal:** <goal>\n")
    check(rc == 0, "a Proposed Epic needs no approval yet", out[-300:])
    rc, out = run(title.format("In Progress"), epic="**Status:** Proposed\n**Goal:** g\n")
    check(rc == 0 and "still `Proposed`" in out and "STORY-901" in out, "work under an Epic nobody approved is reported, never stopped", out[-300:])
    for status in ("Planned", "In Progress", "Completed"):
        rc, out = run(title.format("Cancelled"), epic=f"**Status:** {status}\n**Goal:** g\n")
        check(rc == 1 and "EPIC-900" in out and "`Approved`" in out, f"an Epic is intent: it cannot be {status} without the human's approval", out[-300:])
    rc, out = run(title.format("Planned"), epic="**Status:** Planned\n**Goal:** g\n**Approved:** <who> - <YYYY-MM-DD>\n")
    check(rc == 1 and "`Approved`" in out, "a placeholder is not an approval", out[-300:])
    rc, out = run(title.format("Planned"), epic="**Status:** Planned\n**Goal:** <goal>\n**Approved:** MG - 2026-01-15\n")
    check(rc == 1 and "`Goal`" in out, "an approved Epic states its goal", out[-300:])
    rc, out = run(title.format("In Progress"), epic="**Status:** Completed\n**Goal:** g\n**Approved:** MG - 2026-01-15\n")
    check(rc == 1 and "EPIC-900 is `Completed`" in out and "STORY-901" in out, "an Epic is not Completed while one of its Stories is open", out[-300:])

    run(title.format("Planned"))
    rc, env, _ = op(p, "session-context")
    check(rc == 0 and any("STORY-901" in x for x in data(env)["operational"]["stories_planned"]), "the session contract lists the planned Stories")
    bash(p, ".gtt/scripts/gtt-status.sh")
    with open(os.path.join(p, "gtt-domain", "session.md"), encoding="utf-8") as handle:
        check("1 Story(ies): 1 Planned; 1 Epic(s)" in handle.read(), "status reports the working plan as it stands")


def frozen_project(project, tmp, name, boundaries="", before_freeze=None):
    """A disposable project with a real governed context, a Git history and a first freeze."""
    p = fresh(project, tmp, name)
    for doc in ("stack", "architecture", "solution-vision", "principles", "constraints", "glossary"):
        write(os.path.join(p, "gtt-domain", "context", doc + ".md"), f"# {doc}\n\n" + "".join(f"decided {i}\n" for i in range(8)))
    with open(os.path.join(p, "gtt-domain", "context", "stack.md"), "a", encoding="utf-8") as handle:
        handle.write("\n```gtt-boundaries\n" + boundaries + "```\n")
    write(os.path.join(p, "package.json"), json.dumps({"dependencies": {"express": "1"}}))
    write(os.path.join(p, "src", "domain", "order.py"), "def total():\n    return 1\n")
    if before_freeze:
        before_freeze(p)
    git(p, "init", "-q")
    git(p, "config", "user.email", "t@example.org")
    git(p, "config", "user.name", "t")
    commit(p, "base")
    rc, out, err = bash(p, ".gtt/scripts/gtt-freeze.sh")
    commit(p, "freeze")
    return p, rc, out + err


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def commit(cwd, message):
    git(cwd, "add", "-A")
    git(cwd, "commit", "-qm", message)


RULES = ("B-001 | path | infra/** | WARNING | Deployment topology\n"
         "B-002 | path | **/openapi.yaml | GOVERNANCE | Public API contract\n"
         "B-003 | dependency | package.json | WARNING | Stack at a glance\n"
         "B-004 | forbid | src/domain/** :: import .*infrastructure | BLOCKING | Dependency rules\n"
         "B-005 | path | secrets/** | BLOCKING | Security boundary\n")


def observation(project, tmp):
    print("[observation] the ADE works on its own; GTT observes against the freeze; only BLOCKING stops anything")
    ledger = "gtt-domain/governance-backlog.json"

    def obs(p, *args):
        rc, out, err = bash(p, ".gtt/scripts/gtt-observe.sh", *args)
        return rc, out + err

    rc, out = obs(fresh(project, tmp, "ob-pre"), "observe")
    check(rc == 0 and out.strip() == "", "before the first freeze nothing is ratified, so nothing is observed")

    p, rc, out = frozen_project(project, tmp, "ob", RULES)
    with open(os.path.join(p, "gtt-domain/.frozen"), encoding="utf-8") as handle:
        marker = handle.read()
    check(rc == 0 and "Baseline commit: " in marker and "Governed digest: " in marker and "implementation stays free" in out,
          "freeze records a governance baseline - commit and digest of the governed state - and leaves the code free", out[-300:])
    rc, out = obs(p, "observe")
    check(rc == 0 and out.strip() == "" and not os.path.exists(os.path.join(p, ledger)), "compliant work is silent and leaves no trace")

    write(os.path.join(p, "src", "domain", "order.py"), "def total():\n    return 2\n\n\ndef tax():\n    return 3\n")
    write(os.path.join(p, "tests", "test_order.py"), "def test_total():\n    assert True\n")
    rc, out = obs(p, "observe")
    check(rc == 0 and out.strip() == "", "ordinary implementation - a refactor, new tests - raises nothing and asks nothing")

    write(os.path.join(p, "infra", "main.tf"), "resource {}\n")
    write(os.path.join(p, "api", "openapi.yaml"), "openapi: 3\n")
    write(os.path.join(p, "package.json"), json.dumps({"dependencies": {"express": "1", "kafkajs": "2"}}))
    rc, out = obs(p, "observe")
    check(rc == 0 and out.startswith("@gtt · Observation") and all(x in out for x in ("B-001", "B-002", "B-003", "kafkajs")) and "work continues" in out,
          "drift becomes a signal that names the boundary it crossed - and the work continues", out[-400:])
    check("STOP" not in out, "a non-blocking observation never becomes a stop")
    items = {i["rule"]: i for i in read_json(os.path.join(p, ledger))["items"]}
    check(items["B-003"]["artifact"] == "package.json#kafkajs" and items["B-002"]["level"] == "GOVERNANCE" and all(i["status"] == "open" for i in items.values()),
          "every observation enters the governance backlog with its rule, artifact and level")
    before = open(os.path.join(p, ledger), "rb").read()
    rc, out = obs(p, "observe")
    check(rc == 0 and out.strip() == "" and open(os.path.join(p, ledger), "rb").read() == before,
          "observation is idempotent: the same state observed again reports nothing and writes nothing")
    rc, env, _ = op(p, "observe")
    check(rc == 0 and data(env)["result"] == "pass" and len(data(env)["items"]) == 3 and data(env)["new"] == [], "the same is a declared operation a CLI can run")
    rc, env, _ = op(p, "validation.run")
    check(any(c["check"] == "gtt-observe.sh check" and c["result"] == "pass" for c in data(env)["checks"]),
          "validation does not fail on drift that is not blocking", str(data(env).get("failing"))[:200])

    check(obs(p, "check")[0] == 0 and obs(p, "check", "--strict")[0] == 1,
          "an undecided GOVERNANCE observation fails a check only where that is asked for")
    h, rc, out = frozen_project(project, tmp, "ob-hard", RULES)
    write(os.path.join(h, "api", "openapi.yaml"), "openapi: 3\n")
    check(obs(h, "check")[0] == 0, "(sanity) the same observation passes the check under the default gates")
    op(h, "methodology.profile.set", profile="hard", apply=True)
    rc, out = obs(h, "check")
    check(rc == 1 and "OBS-0001" in out, "under a plan that says so, an undecided GOVERNANCE observation fails the check", out[-300:])
    rc, out = obs(p, "defer", "OBS-0002", "--by", "MG")
    check(rc == 0 and "dry run" in out and obs(p, "check", "--strict")[0] == 1, "a decision on an observation is a dry run by default")
    obs(p, "defer", "OBS-0002", "--by", "MG", "--apply")
    check(obs(p, "check", "--strict")[0] == 0, "once the human has deferred it, it no longer fails anything")
    obs(p, "accept", "OBS-0003", "--by", "MG", "--note", "event bus approved in principle", "--apply")
    rc, out = obs(p, "reject", "OBS-0001", "--by", "MG", "--apply")
    rc, out = obs(p, "observe")
    check(rc == 1 and "OBS-0001" in out and "rejected by MG and still present" in out and "OBS-0003" not in out,
          "what the human rejected stops the check until it is gone; what the human accepted is not raised again", out[-300:])
    shutil.rmtree(os.path.join(p, "infra"))
    rc, out = obs(p, "observe")
    done = {i["id"]: i for i in read_json(os.path.join(p, ledger))["items"]}
    check(rc == 0 and done["OBS-0001"]["status"] == "resolved" and done["OBS-0003"]["status"] == "accepted",
          "an observation that is no longer true resolves itself", out[-300:])

    write(os.path.join(p, "src", "domain", "order.py"), "from app import infrastructure\n")
    rc, out = obs(p, "observe")
    check(rc == 1 and "B-004" in out and "BLOCKING" in out and "declared BLOCKING in the governed state" in out and "Dependency rules" in out,
          "a boundary ratified as BLOCKING stops, and says which rule and what it guards", out[-300:])
    rc, env, _ = op(p, "validation.run")
    check(env["exit_code"] == 1 and any(f.startswith("gtt-observe.sh check") for f in data(env)["failing"]), "validation fails on a BLOCKING observation")
    write(os.path.join(p, "src", "domain", "order.py"), "def total():\n    return 2\n")
    check(obs(p, "observe")[0] == 0, "fixing it is all it takes: there is nothing to approve")

    engine = os.path.join(".gtt", "scripts", "gtt_protect.py")

    def decide(*args):
        proc = subprocess.run([sys.executable, engine, "decide", *args], cwd=p, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout
    rc, out = decide("--file", "secrets/prod.env")
    check(rc == 2 and "B-005" in out and "Security boundary" in out, "a hook-capable ADE is denied a write under a BLOCKING path boundary, with the rule named", out[:200])
    check(decide("--file", "infra/new.tf")[0] == 0 and decide("--file", "src/domain/order.py")[0] == 0,
          "a write under any other boundary is never blocked: it is observed afterwards")
    check(decide("--shell", "bash .gtt/scripts/gtt-observe.sh accept OBS-0002 --by me --apply")[0] == 2
          and decide("--shell", "bash .gtt/scripts/gtt-freeze.sh")[0] == 2 and decide("--shell", "bash .gtt/scripts/gtt-observe.sh observe")[0] == 0,
          "an agent observes freely but never decides an observation and never freezes")
    rc, env, _ = op(p, "governance.accept", id="OBS-0002", by="MG", apply=True)
    check(rc == 4, "deciding an observation needs a human decision from the CLI too")

    with open(os.path.join(p, "gtt-domain", "context", "architecture.md"), "a", encoding="utf-8") as handle:
        handle.write("the event bus is now part of the design\n")
    rc, out = obs(p, "observe")
    check(rc == 0 and "GTT-GOVERNED" in out and "new freeze" in out, "a change to the governed state itself is seen and calls for a new freeze, not an unfreeze", out[-300:])
    write(os.path.join(p, "api", "v2", "openapi.yaml"), "openapi: 3\n")
    rc, out, err = bash(p, ".gtt/scripts/gtt-freeze.sh")
    check(rc == 1 and "undecided observations" in err, "a new baseline is not drawn over a governance observation nobody decided", (out + err)[-300:])
    obs(p, "observe")
    pending = [i["id"] for i in read_json(os.path.join(p, ledger))["items"] if i["status"] == "open" and i["rule"] == "B-002"]
    for ident in pending:
        obs(p, "accept", ident, "--by", "MG", "--apply")
    commit(p, "work")
    rc, out, err = bash(p, ".gtt/scripts/gtt-freeze.sh")
    with open(os.path.join(p, "gtt-domain/.frozen"), encoding="utf-8") as handle:
        again = handle.read()
    check(rc == 0 and "new governance baseline" in out and "# earlier freezes" in again and marker.splitlines()[0] in again and again.splitlines()[0] != "",
          "a promoted change is completed by a new freeze, and the earlier one is kept as history", (out + err)[-300:])
    commit(p, "refreeze")
    rc, out = obs(p, "observe")
    still = [i for i in read_json(os.path.join(p, ledger))["items"] if i["status"] in ("open", "deferred", "rejected")]
    check(rc == 0 and not still, "from the new baseline the backlog starts clean: what was decided is behind it")
    check(bash(p, ".gtt/scripts/gtt-freeze.sh")[0] == 2, "freezing an unchanged governed state does nothing")
    bash(p, ".gtt/scripts/gtt-status.sh")
    with open(os.path.join(p, "gtt-domain", "session.md"), encoding="utf-8") as handle:
        text = handle.read()
    check("## Observation" in text and "baseline commit:" in text and "open: BLOCKING 0" in text, "the session state carries what was observed, derived from the project")
    rc, env, _ = op(p, "session-context")
    check(rc == 0 and data(env)["operational"]["observation"]["authority"] == "none", "and the session contract carries it as a signal with no authority")

    def guarded(q):
        write(os.path.join(q, "src", "billing.py"), "# @GTTGuard reason=audited\ndef charge():\n    return 1\n\n\ndef helper():\n    return 2\n")
        bash(q, ".gtt/scripts/gtt-guard-sync.sh")
    q, rc, out = frozen_project(project, tmp, "ob-guard", "", guarded)
    write(os.path.join(q, "src", "billing.py"), "# @GTTGuard reason=audited\ndef charge():\n    return 1\n\n\ndef helper():\n    return 99\n")
    check(obs(q, "observe") == (0, ""), "an edit next to a protected symbol is ordinary work")
    write(os.path.join(q, "src", "billing.py"), "# @GTTGuard reason=audited\ndef charge():\n    return 100\n\n\ndef helper():\n    return 99\n")
    rc, out = obs(q, "observe")
    check(rc == 0 and "GTT-PROTECTED" in out and "billing.py" in out, "a change to the protected symbol itself is observed, whoever made it", out[-300:])

    q, rc, out = frozen_project(project, tmp, "ob-bad", "B-001 | teleport | x | WARNING | nothing\n")
    check(rc == 1 and "gtt-boundaries" in out, "a malformed boundary is refused at freeze: what is ratified must be readable", out[-300:])
    q, rc, out = frozen_project(project, tmp, "ob-legacy")
    with open(os.path.join(q, "gtt-domain", "context", "stack.md"), "a", encoding="utf-8") as handle:
        handle.write("\n```gtt-drift-signals\ninfra/** -> Deployment topology\n```\n")
    rc, env, _ = op(q, "governance.boundaries")
    check(rc == 0 and [(r["kind"], r["level"], r["match"]) for r in data(env)["rules"]] == [("path", "WARNING", "infra/**")],
          "an earlier `gtt-drift-signals` block still works, read as path boundaries at WARNING")


def claude_hook_under_test(project):
    """The Claude Code hook the suite exercises: the installed one, or - to prove a staged hook before
    the human installs it - the file named by GTT_TEST_CLAUDE_HOOK."""
    return os.path.abspath(os.environ.get("GTT_TEST_CLAUDE_HOOK") or os.path.join(project, ".claude", "hooks", "protect-l0.py"))


def place_claude_hook(project, copy):
    """The harness puts the hook under test at its native path inside the disposable copy."""
    shutil.copy2(claude_hook_under_test(project), os.path.join(copy, ".claude", "hooks", "protect-l0.py"))


def claude_decides(copy, kind, target):
    """(denied, text, warning) from Claude Code's own PreToolUse hooks for one call, fed the payload
    Claude Code sends on stdin: protect-l0.py, then protect-guard.py - a call runs only if both allow it."""
    tool_input = {"file_path": target} if kind == "file" else {"command": target}
    payload = json.dumps({"tool_name": "Write" if kind == "file" else "Bash", "tool_input": tool_input})
    env = dict(os.environ, CLAUDE_PROJECT_DIR=copy)
    warning = ""
    for hook in ("protect-l0.py", "protect-guard.py"):
        proc = subprocess.run([sys.executable, os.path.join(copy, ".claude", "hooks", hook)], cwd=copy, env=env, input=payload,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode == 2:
            return True, proc.stdout, ""
        if hook == "protect-l0.py" and "systemMessage" in proc.stdout:
            warning = proc.stdout
    return False, "", warning


def portable_decides(copy, kind, target):
    """(denied, text, warning) from the engine Cursor, OpenHands and Antigravity share."""
    proc = subprocess.run([sys.executable, os.path.join(".gtt", "scripts", "gtt_protect.py"), "decide", "--file" if kind == "file" else "--shell", target],
                          cwd=copy, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode == 2, proc.stdout, proc.stderr


APPLY = "gtt-domain/proposals/apply-ADR-900-x.sh"
STAGED_PATCH = "gtt-domain/proposals/x.patch"
CONTRACT = "AGENTS" + ".md"
# (fix or rule, regime, kind, target, decision, what a denial must name)
ENFORCEMENT_CASES = [
    ("work", "pre", "file", "src/app.py", "allow", None),
    ("work", "pre", "file", "gtt-domain/proposals/PROPOSAL-x.md", "allow", None),
    ("work", "pre", "file", "gtt-domain/context/stack.md", "allow", None),
    ("work", "pre", "shell", f"cat {CONTRACT}", "allow", None),
    ("work", "pre", "shell", "bash .gtt/scripts/gtt-observe.sh observe", "allow", None),
    ("work", "pre", "shell", f"cat {APPLY}", "allow", None),
    ("work", "pre", "shell", f"git apply --check {STAGED_PATCH}", "allow", None),
    ("work", "pre", "shell", f"git apply --stat {STAGED_PATCH}", "allow", None),
    ("work", "pre", "shell", "bash .gtt/scripts/gtt-git-hook.sh status", "allow", None),
    ("work", "pre", "shell", "bash .gtt/scripts/gtt-git-hook.sh install", "allow", None),
    ("F5", "pre", "shell", "git commit --no-verify -m x", "allow", None),
    ("F7", "pre", "shell", f"grep -n Story {CONTRACT} > /tmp/gtt-out.txt", "allow", None),
    ("F7", "pre", "shell", f"cat >> .gtt/docs/evidence.md <<'EOF'\nloads {CONTRACT} in full\nEOF", "allow", None),
    ("governed", "pre", "file", CONTRACT, "deny", "governed paths"),
    ("governed", "pre", "shell", f"sed -i s/a/b/ ./{CONTRACT}", "deny", "governed paths"),
    ("governed", "pre", "shell", f"echo x > {CONTRACT}", "deny", "governed paths"),
    ("governed", "pre", "shell", "rm .claude/hooks/protect-l0.py", "deny", "governed paths"),
    ("F7", "pre", "shell", "rm .gtt/scripts/gtt_protect.py", "deny", "governed paths"),
    ("F1", "pre", "file", "gtt-domain/.frozen", "deny", "freeze-semantics"),
    ("F1", "pre", "shell", "echo 2026-01-01 > gtt-domain/.frozen", "deny", "freeze-semantics"),
    ("F1", "pre", "shell", "cp /tmp/marker gtt-domain/.frozen", "deny", "freeze-semantics"),
    ("F2", "pre", "file", "gtt-domain/governance-backlog.json", "deny", "human-decision-authority"),
    ("F2", "pre", "shell", "echo {} > gtt-domain/governance-backlog.json", "deny", "human-decision-authority"),
    ("F2", "pre", "shell", "sed -i s/open/accepted/ gtt-domain/governance-backlog.json", "deny", "human-decision-authority"),
    ("F3", "pre", "shell", f"bash {APPLY}", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f"./{APPLY}", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f"sh {APPLY}", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f"source {APPLY}", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f". {APPLY}", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f"env bash -x {APPLY}", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f"cat {APPLY} | bash", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f'bash -c "bash {APPLY}"', "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", "{root}/" + APPLY, "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f"git apply {STAGED_PATCH}", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f"patch -p1 < {STAGED_PATCH}", "deny", "Human Promotion Boundary"),
    ("F3", "pre", "shell", f"cp gtt-domain/proposals/contract.md {CONTRACT}", "deny", "governed paths"),
    ("human act", "pre", "shell", "bash .gtt/scripts/gtt-freeze.sh", "deny", "human-decision-authority"),
    ("human act", "pre", "shell", "bash .gtt/scripts/gtt-observe.sh accept OBS-0001 --by me --apply", "deny", "human-decision-authority"),
    ("F5", "pre", "shell", "bash .gtt/scripts/gtt-git-hook.sh install --apply", "deny", "human-decision-authority"),
    ("F5", "pre", "shell", "bash .gtt/scripts/gtt-git-hook.sh remove --apply", "deny", "human-decision-authority"),
    ("work", "frozen", "file", "src/domain/order.py", "allow", None),
    ("work", "frozen", "file", "infra/main.tf", "allow", None),
    ("work", "frozen", "shell", "bash .gtt/scripts/gtt-observe.sh check", "allow", None),
    ("work", "frozen", "shell", "cat gtt-domain/context/stack.md", "allow", None),
    ("governed", "frozen", "file", "gtt-domain/context/stack.md", "deny", "governed paths"),
    ("boundary", "frozen", "file", "secrets/prod.env", "deny", "B-005"),
    ("F1", "frozen", "shell", "rm gtt-domain/.frozen", "deny", "freeze-semantics"),
    ("F1", "frozen", "shell", "git rm -q gtt-domain/.frozen", "deny", "freeze-semantics"),
    ("F1", "frozen", "shell", "mv gtt-domain/.frozen /tmp/x", "deny", "freeze-semantics"),
    ("F1", "frozen", "shell", "rm -rf gtt-domain", "deny", "freeze-semantics"),
    ("F3", "frozen", "shell", "mv gtt-domain/proposals/context-stack.md gtt-domain/context/stack.md", "deny", "governed paths"),
    ("F5", "hooked", "shell", "git commit --no-verify -m x", "deny", "explicit-blocking"),
    ("F5", "hooked", "shell", "git commit -n -m x", "deny", "explicit-blocking"),
    ("F5", "hooked", "shell", "git -c core.hooksPath=/dev/null commit -m x", "deny", "explicit-blocking"),
    ("F5", "hooked", "shell", "git config core.hooksPath /tmp/hooks", "deny", "explicit-blocking"),
    ("F5", "hooked", "shell", "rm .git/hooks/pre-commit", "deny", "explicit-blocking"),
    ("F5", "hooked", "shell", 'git commit -m "fix -n handling"', "allow", None),
    ("F5", "hooked", "shell", "git commit -uno -m x", "allow", None),
    ("F5", "hooked", "shell", "git config --get core.hooksPath", "allow", None),
]


def enforcement(project, tmp):
    print("[enforcement] one decision core, two engines: Claude Code's hook and the portable engine decide alike")
    hook = claude_hook_under_test(project)
    print(f"  (Claude hook under test: {os.path.relpath(hook, project)})")
    mark = re.compile(r"# >>> gtt-decision-core >>>.*?# <<< gtt-decision-core <<<", re.DOTALL)
    with open(hook, encoding="utf-8") as handle:
        in_hook = mark.search(handle.read())
    with open(os.path.join(project, ".gtt", "scripts", "gtt_protect.py"), encoding="utf-8") as handle:
        in_engine = mark.search(handle.read())
    check(bool(in_hook and in_engine) and in_hook.group(0) == in_engine.group(0),
          "F7: the decision core is byte-identical in the Claude hook and in the portable engine")

    pre = fresh(project, tmp, "enf-pre")
    frozen, rc, out = frozen_project(project, tmp, "enf-frozen", RULES)
    hooked, rc, out = frozen_project(project, tmp, "enf-hooked", RULES)
    rc, out, err = bash(hooked, ".gtt/scripts/gtt-git-hook.sh", "install", "--apply")
    check(rc == 0 and "installed" in out, "(setup) the Git hook installs in a disposable frozen copy", out + err)
    copies = {"pre": pre, "frozen": frozen, "hooked": hooked}
    for copy in copies.values():
        place_claude_hook(project, copy)
    for fix, regime, kind, target, expect, names in ENFORCEMENT_CASES:
        copy = copies[regime]
        target = target.replace("{root}", copy.replace("\\", "/"))
        c_denied, c_text, _ = claude_decides(copy, kind, target)
        p_denied, p_text, _ = portable_decides(copy, kind, target)
        ok = c_denied == p_denied == (expect == "deny") and (not names or (names in c_text and names in p_text))
        shown = target if len(target) < 70 else target[:67] + "..."
        check(ok, f"{fix}: {regime:6} {kind:5} {expect:5} {shown!r}" + (f" - names `{names}`" if names else ""),
              f"claude={'deny' if c_denied else 'allow'} portable={'deny' if p_denied else 'allow'} {c_text[:120]!r}")

    broken, rc, out = frozen_project(project, tmp, "enf-broken", RULES)
    place_claude_hook(project, broken)
    write(os.path.join(broken, ".gtt", "scripts", "gtt_observe.py"), "this is not python (\n")
    c_denied, _, c_warn = claude_decides(broken, "file", "secrets/prod.env")
    p_denied, _, p_warn = portable_decides(broken, "file", "secrets/prod.env")
    check(not c_denied and not p_denied, "F6: a broken observation engine never blocks a session")
    check("explicit-blocking" in c_warn and "BLOCKING" in c_warn and "explicit-blocking" in p_warn and "NOT checked" in p_warn,
          "F6: but BLOCKING is not switched off in silence - both engines say the write was not checked", (c_warn + p_warn)[:200])
    c_denied, _, c_warn = claude_decides(broken, "file", "gtt-domain/context/stack.md")
    check(c_denied, "F6: and what does not depend on that engine is still denied")
    quiet, rc, out = frozen_project(project, tmp, "enf-quiet", "B-001 | path | infra/** | WARNING | Deployment topology\n")
    place_claude_hook(project, quiet)
    write(os.path.join(quiet, ".gtt", "scripts", "gtt_observe.py"), "this is not python (\n")
    check(claude_decides(quiet, "file", "infra/main.tf") == (False, "", "") and portable_decides(quiet, "file", "infra/main.tf")[2] == "",
          "F6: with no BLOCKING boundary declared there is nothing to warn about")

    print("[enforcement] CI sees a removed or rewritten freeze marker (F4)")
    q, rc, out = frozen_project(project, tmp, "enf-ci", RULES)
    git(q, "branch", "base")
    marker = os.path.join(q, "gtt-domain", ".frozen")
    with open(marker, encoding="utf-8") as handle:
        original = handle.read()
    rc, out, err = bash(q, ".gtt/scripts/gtt-check-stack.sh", "base")
    check(rc == 0, "F4: an untouched freeze passes the stack gate", (out + err)[-200:])
    os.remove(marker)
    rc, out, err = bash(q, ".gtt/scripts/gtt-check-stack.sh", "base")
    check(rc == 1 and "freeze marker removed" in err and "there is no unfreeze" in err,
          "F4: a tree whose base was frozen and whose marker is gone fails - it is not `not frozen yet`", (out + err)[-200:])
    write(marker, "2031-01-01T00:00:00Z\nFrozen by: someone\nBaseline commit: none\nGoverned digest: 0000\n")
    rc, out, err = bash(q, ".gtt/scripts/gtt-check-stack.sh", "base")
    check(rc == 1 and "freeze history rewritten" in err, "F4: a marker that drops the baseline the base recorded fails", (out + err)[-200:])
    write(marker, original)
    with open(os.path.join(q, "gtt-domain", "context", "architecture.md"), "a", encoding="utf-8") as handle:
        handle.write("a promoted decision\n")
    commit(q, "promoted")
    rc, out, err = bash(q, ".gtt/scripts/gtt-freeze.sh")
    commit(q, "new freeze")
    rc2, out2, err2 = bash(q, ".gtt/scripts/gtt-check-stack.sh", "base")
    check(rc == 0 and rc2 == 0, "F4: a new freeze, which keeps the earlier baseline as history, passes", (out + err + out2 + err2)[-300:])
    spec = json.loads(contract(project, "show", "profiles")[1])
    freeze_inv = next(inv for inv in spec["invariants"] if inv["id"] == "freeze-semantics")
    check("gate:gtt-check-stack.sh" in freeze_inv["enforcement"], "the contract declares the gate this suite just demonstrated for freeze-semantics")

    print("[enforcement] the Git pre-commit hook, for real, in a disposable frozen copy")
    g = hooked
    write(os.path.join(g, "infra", "main.tf"), "resource {}\n")
    git(g, "add", "-A")
    proc = git(g, "commit", "-m", "non-blocking drift")
    check(proc.returncode == 0 and "non-blocking drift" in git(g, "log", "-1", "--format=%s").stdout,
          "a change that crosses a non-blocking boundary is committed: the hook is not an approval step", (proc.stdout + proc.stderr)[-300:])
    head = git(g, "rev-parse", "HEAD").stdout
    write(os.path.join(g, "src", "domain", "order.py"), "from app import infrastructure\n")
    git(g, "add", "-A")
    proc = git(g, "commit", "-m", "blocking")
    check(proc.returncode != 0 and "B-004" in proc.stdout + proc.stderr and git(g, "rev-parse", "HEAD").stdout == head,
          "a BLOCKING boundary stops the commit and names its rule", (proc.stdout + proc.stderr)[-300:])
    write(os.path.join(g, "src", "domain", "order.py"), "def total():\n    return 3\n")
    git(g, "add", "-A")
    proc = git(g, "commit", "-m", "fixed")
    check(proc.returncode == 0, "fixing it is all it takes for the commit to go through", (proc.stdout + proc.stderr)[-300:])
    os.rename(os.path.join(g, ".gtt", "scripts", "gtt-observe.sh"), os.path.join(g, ".gtt", "scripts", "gtt-observe.sh.off"))
    write(os.path.join(g, "notes.txt"), "x\n")
    git(g, "add", "-A")
    proc = git(g, "commit", "-m", "unchecked")
    check(proc.returncode == 0 and "NOT checked" in proc.stderr, "F5: with the engine missing the hook still lets the commit through - and says it was not checked", (proc.stdout + proc.stderr)[-300:])


def think_depth(project, tmp):
    print("[THINK Depth] QUICK / STANDARD / DEEP: how deep THINK goes, never which rules it may skip")
    spec = json.loads(contract(project, "show", "elicitation")[1])["think_depth"]
    check(spec["levels"] == ["QUICK", "STANDARD", "DEEP"] and sorted(spec["depths"]) == ["DEEP", "QUICK", "STANDARD"]
          and all(spec["depths"][x][k] for x in spec["levels"] for k in ("for", "assessment", "focus", "stack", "questionnaire")),
          "the three depths are declared, each with its assessment, focus, stack and questionnaire behaviour")
    check(spec["floor_varies_with_depth"] is False and any("minimum floor" in x for x in spec["invariant_at_every_depth"])
          and any("human decision" in x for x in spec["invariant_at_every_depth"]),
          "the floor and human authority are invariant at every depth")
    check(spec["selection"]["decided_by"] == "the human" and spec["selection"]["unselected"] == {**spec["selection"]["unselected"], "applies": "STANDARD", "state": "not selected"},
          "the human selects the depth; unselected is a state and STANDARD (the previous behaviour) applies")
    check(spec["escalation"]["automatic"] is False and spec["escalation"]["decided_by"] == "the human" and spec["escalation"]["signals"],
          "escalation is proposed with evidence and decided by the human, never automatic")
    check("Method Plan" in spec["not_a_method_plan"], "THINK Depth is declared independent of the Method Plan")

    host = make_host(project, tmp, "think-host")
    write(os.path.join(host, "design.md"), "# design\n")
    op(host, "template.materialize", id="design-assessment", apply=True)
    path = os.path.join(host, "gtt-domain/proposals/bootstrap/design-assessment.md")
    with open(path, encoding="utf-8") as handle:
        blank = handle.read()
    check(all(x in blank for x in ("## THINK Depth", "`QUICK`", "`STANDARD`", "`DEEP`", "not assessed (QUICK)", "### Escalation log", "### 6.3 Architecture alternatives")),
          "the assessment working copy carries the depth, what each level does, and the escalation log")

    def state(depth="", verdict="", floor="MET", unmet=0, unassessed=0, escalation=None):
        text = blank.replace("THINK Depth:\n", f"THINK Depth: {depth}\n", 1).replace("Verdict:\n", f"Verdict: {verdict}\n", 1)
        head, rest = text.split("## 4. Minimum floor", 1)
        body, tail = rest.split("## 5. Verdict", 1)
        lines, seen = [], 0
        for line in body.split("\n"):
            if line.startswith("| ") and line.endswith("|  |"):
                seen += 1
                value = "NOT MET" if seen <= unmet else "" if seen <= unmet + unassessed else floor
                line = line[:-4] + f"| {value} |"
            lines.append(line)
        text = head + "## 4. Minimum floor" + "\n".join(lines) + "## 5. Verdict" + tail
        if escalation:
            before, after = text.split("### Escalation log", 1)
            text = before + "### Escalation log" + after.replace("|---|---|---|---|\n", "|---|---|---|---|\n| " + " | ".join(escalation) + " |\n", 1)
        write(path, text)
        rc, out, err = bash(host, ".gtt/scripts/gtt-project.sh", "think", "--json")
        return rc, json.loads(out)

    rc, s = state()
    check(rc == 0 and s["selected"] is None and s["applies"] == "STANDARD" and s["state"] == "not selected",
          "no depth selected: STANDARD applies as a fallback and is reported as not selected")
    for depth in ("QUICK", "STANDARD", "DEEP"):
        rc, s = state(depth, "ADEQUATE")
        check(rc == 0 and s["selected"] == depth and s["applies"] == depth and s["floor"] == {"met": 5, "not_met": 0, "unassessed": 0},
              f"{depth}: a selected depth is recorded; a design that meets the floor may be ADEQUATE", str(s)[:200])
        rc, s = state(depth, "ADEQUATE", unmet=1)
        check(rc == 1 and any("below the floor" in f for f in s["findings"]), f"{depth}: below the floor the verdict is POOR - the depth never lifts it", str(s)[:300])
        rc, s = state(depth, "STRONG", unassessed=1)
        check(rc == 1 and any("line by line" in f for f in s["findings"]), f"{depth}: the floor is assessed line by line, never skipped", str(s)[:300])
        rc, s = state(depth, "POOR", unmet=1)
        check(rc == 0, f"{depth}: a design below the floor is reported as POOR", str(s)[:200])
    rc, s = state("EXTREME")
    check(rc == 1 and any("not one of" in f for f in s["findings"]), "a depth outside QUICK / STANDARD / DEEP is refused")
    rc, s = state("QUICK", escalation=["QUICK", "STANDARD", "regulated data [FUENTE: design.md:1]", ""])
    check(rc == 0 and s["selected"] == "QUICK" and s["escalations"] == [{"from": "QUICK", "to": "STANDARD", "decision": "pending", "accepted": False}],
          "an escalation is a proposal: it is recorded as pending and the depth stays where the human put it", str(s)[:300])
    rc, s = state("STANDARD", escalation=["QUICK", "STANDARD", "regulated data [FUENTE: design.md:1]", ""])
    check(rc == 1 and any("has not accepted" in f for f in s["findings"]), "a depth raised without the human's decision fails", str(s)[:300])
    rc, s = state("STANDARD", escalation=["QUICK", "STANDARD", "regulated data [FUENTE: design.md:1]", "declined - MG - 2026-03-01"])
    check(rc == 1, "a declined escalation does not raise the depth either", str(s)[:300])
    rc, s = state("STANDARD", escalation=["QUICK", "STANDARD", "regulated data [FUENTE: design.md:1]", "accepted - MG - 2026-03-01"])
    check(rc == 0 and s["escalations"][0]["accepted"], "an escalation the human accepted is traceable: from, to, evidence, who and when", str(s)[:300])
    det = data(op(host, "project.detect")[1])["assessment"]["think_depth"]
    check(det["selected"] == "STANDARD" and det["levels"] == ["QUICK", "STANDARD", "DEEP"], "project detection reports the recorded depth")
    state("QUICK", "STRONG", unmet=1)
    rc, out, err = bash(host, ".gtt/scripts/gtt-validate.sh")
    check(rc == 1 and "FAIL               gtt-project.sh think (THINK Depth)" in out, "validation fails while the working copy claims more than the floor allows", out[-400:])
    state("QUICK", "POOR", unmet=1)
    rc, out, err = bash(host, ".gtt/scripts/gtt-validate.sh")
    check("PASS               gtt-project.sh think (THINK Depth)" in out, "and passes once the verdict says what the floor says", out[-400:])

    solo = make_host(project, tmp, "think-solo")
    op(solo, "template.materialize", id="initial-design-questionnaire", apply=True)
    qpath = os.path.join(solo, "gtt-domain/proposals/bootstrap/initial-design-questionnaire.md")
    with open(qpath, encoding="utf-8") as handle:
        qtext = handle.read()
    check("## THINK Depth" in qtext and "### Escalation log" in qtext, "the questionnaire carries the depth for a project with no design document")
    rc, out, _ = bash(solo, ".gtt/scripts/gtt-project.sh", "think", "--json")
    check(rc == 0 and json.loads(out)["state"] == "not selected" and json.loads(out)["applies"] == "STANDARD", "with no document and no choice, STANDARD applies as not selected")
    for depth in ("QUICK", "STANDARD", "DEEP"):
        write(qpath, qtext.replace("THINK Depth:\n", f"THINK Depth: {depth}\n", 1))
        rc, out, _ = bash(solo, ".gtt/scripts/gtt-project.sh", "think", "--json")
        check(rc == 0 and json.loads(out)["selected"] == depth, f"{depth}: selectable with no design document, recorded in the questionnaire")
    before, after = qtext.replace("THINK Depth:\n", "THINK Depth: DEEP\n", 1).split("### Escalation log", 1)
    write(qpath, before + "### Escalation log" + after.replace("|---|---|---|---|\n", "|---|---|---|---|\n| STANDARD | DEEP | several integrations |  |\n", 1))
    rc, out, _ = bash(solo, ".gtt/scripts/gtt-project.sh", "think", "--json")
    check(rc == 1, "in the questionnaire too, a depth raised without the human's decision fails")

    for number, (label, mutate, needle) in enumerate((
            ("a contract in which depth lowers the floor", lambda d: d.update(floor_varies_with_depth=True), "floor must not vary with depth"),
            ("a contract with automatic escalation", lambda d: d["escalation"].update(automatic=True), "must not be automatic"),
            ("a contract missing a depth", lambda d: d["depths"].pop("DEEP"), "exactly QUICK, STANDARD and DEEP"),
            ("a contract in which the ADE selects the depth", lambda d: d["selection"].update(decided_by="the ADE"), "the human selects the depth"))):
        q = fresh(project, tmp, f"think-{number}")
        broken = read_json(os.path.join(q, ".gtt/contract/elicitation.json"))
        mutate(broken["think_depth"])
        save_json(os.path.join(q, ".gtt/contract/elicitation.json"), broken)
        rc, out, err = bash(q, ".gtt/scripts/gtt-check-contract.sh")
        check(rc == 1 and needle in out + err, f"{label} fails the contract check", (out + err)[-200:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-bootstrap-acceptance-")
    try:
        for scenario in (release_identity, compatibility, profiles, developer_experience, ade, cursor_and_openhands, antigravity, questionnaire, sources, export_and_clean, recovery,
                         session_status_validation, fresh_host, any_ade_alone, protection_hooks, registry_safety, evolution, unsupported, guard_and_retrieval, backlog_model, observation, enforcement, think_depth):
            scenario(project, tmp)
    finally:
        if args.keep:
            print("kept:", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{COUNT - len(FAILS)}/{COUNT} checks held")
    if FAILS:
        print("FAILED:", "; ".join(FAILS))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
