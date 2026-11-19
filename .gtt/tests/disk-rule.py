#!/usr/bin/env python3
"""GTT disk rule: agents never run the machine out of space (gtt-disk.sh, .gtt/contract/disk.json).

  D1  the contract: the default rule (3 work copies, 15 GB, 10 GB free), bounds, and the same messages in es and en
  D2  check: one line when all is well, the findings when not, and it never fails or blocks (exit 0)
  D3  prune removes only a work copy that is merged and clean, never the folder you stand in, a locked copy,
      an unmerged or dirty one, or a path that is not a work copy; without --apply nothing changes
  D4  set: dry run writes nothing, warns when it loosens, refuses values out of bounds, can turn the rule off
      and go back to the default; a linked work copy reads the main checkout's setting
  D5  the person changes the limits, an agent does not: both hook engines deny `set` and a direct write of
      .gtt/local/disk.json, and allow check, status and prune
  D6  the rule is in the contract every ADE reads: AGENTS.md, operations.md, rules.md, the usage guides

  python3 .gtt/tests/disk-rule.py [--project .] [--keep]
Exit 0 = every check held, 1 = at least one failed.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acc", os.path.join(HERE, "bootstrap-acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
check, write = acc.check, acc.write

DISK = ".gtt/scripts/gtt-disk.sh"
STATE = ".gtt/local/disk.json"


def run(cwd, *args):
    done = subprocess.run(["bash", *args], cwd=cwd, capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def git(cwd, *args):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return done.returncode, done.stdout.strip(), done.stderr.strip()


def repo(project, tmp, name, lang=None):
    """A throwaway Git repository that carries the disk rule: a main checkout on `main`, one commit."""
    root = os.path.join(tmp, name)
    for rel in (".gtt/contract/disk.json", ".gtt/scripts/gtt-disk.sh", ".gtt/scripts/gtt_disk.py", ".gtt/scripts/gtt-run-python.sh"):
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        shutil.copy2(os.path.join(project, rel), os.path.join(root, rel))
    if lang:
        write(os.path.join(root, ".gtt/methodology.json"), json.dumps({"language": lang}))
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.org")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    write(os.path.join(root, ".gitignore"), ".gtt/local/\nnode_modules/\n")
    write(os.path.join(root, "a.txt"), "a\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root


def add_copy(root, name, branch=None):
    path = os.path.join(os.path.dirname(root), name)
    git(root, "worktree", "add", "-q", path, "-b", branch or name)
    return os.path.realpath(path)


def listed(root):
    return [os.path.realpath(line.split()[0]) for line in git(root, "worktree", "list")[1].splitlines()]


def contract(project):
    d1 = os.path.join(project, ".gtt/contract/disk.json")
    data = acc.read_json(d1)
    en, es = data["messages"]["en"], data["messages"]["es"]
    check(data["defaults"] == {"max_work_copies": 3, "max_gb": 15, "min_free_gb": 10},
          "D1 the default rule is 3 work copies, 15 GB and 10 GB free", str(data["defaults"]))
    check(all(data["bounds"][k][0] <= data["defaults"][k] <= data["bounds"][k][1] for k in data["defaults"]),
          "D1 each default is inside its own bounds")
    check(set(en) == set(es), "D1 es and en carry the same messages", str(set(en) ^ set(es)))
    check(all("{" not in v.replace("{", "", 0) or v.count("{") == v.count("}") for v in list(en.values()) + list(es.values())),
          "D1 every message has balanced placeholders")
    check(data["state"] == STATE, "D1 the setting lives in .gtt/local/disk.json")
    rel = acc.read_json(os.path.join(project, ".gtt/contract/release.json"))
    check(rel["contracts"].get("disk") == 1, "D1 release.json declares the disk contract")
    manifest = open(os.path.join(project, ".gtt/scaffold/manifest.yaml"), encoding="utf-8").read()
    check(".gtt/contract/disk.json" in manifest and ".gtt/local/disk.json" in manifest, "D1 the manifest places the contract and the local state")


def checking(project, tmp):
    print("[disk] check")
    root = repo(project, tmp, "chk")
    rc, out, err = run(root, DISK, "set", "--min-free-gb", "0", "--apply")      # the machine running this may be short of space
    rc, out, err = run(root, DISK, "check")
    check(rc == 0 and out.startswith("gtt-disk: ok - 0 of 3 work copies") and out.count("\n") == 1,
          "D2 with no work copy it is one line and ok", out + err)
    copies = [add_copy(root, f"w{i}") for i in range(1, 5)]
    rc, out, err = run(root, DISK, "check")
    check(rc == 0 and "4 work copies, the limit is 3" in out, "D2 four copies over a limit of three is reported and exits 0", out + err)
    rc, out, err = run(root, DISK, "check", "--json")
    data = json.loads(out)
    check(data["copies"] == 4 and data["max_copies"] == 3 and any(f["code"] == "copies" for f in data["findings"]),
          "D2 --json carries the same facts", out[:200])
    write(os.path.join(copies[0], "playwright-report", "index.html"), "x")
    write(os.path.join(copies[1], "dump.sql.gz"), "x")
    write(os.path.join(copies[2], "node_modules", "pkg", "audio.wav"), "x")      # inside node_modules: not searched
    rc, out, err = run(root, DISK, "check", "--json")
    stray = [f for f in json.loads(out)["findings"] if f["code"] == "stray"]
    check(stray and stray[0]["count"] == 2, "D2 a report folder and a dump inside a work copy are named, node_modules is skipped", out[-300:])
    rc, out, err = run(root, DISK, "set", "--max-gb", "1", "--apply")
    big = os.path.join(copies[3], "blob.bin")
    try:
        with open(big, "wb") as handle:
            os.posix_fallocate(handle.fileno(), 0, 1100 * 1024 * 1024)      # real blocks, no time spent writing them
        allocated = True
    except (AttributeError, OSError):
        allocated = False                                                      # this file system cannot reserve space: nothing to measure
    if allocated:
        rc, out, err = run(root, DISK, "check")
        check(rc == 0 and "take 1" in out and "the limit is 1 GB" in out, "D2 work copies over the size limit are reported", out + err)
        os.remove(big)
    es = repo(project, tmp, "chk-es", lang="es")
    rc, out, err = run(es, DISK, "set", "--min-free-gb", "0", "--apply")
    rc, out, err = run(es, DISK, "check")
    check(out.startswith("gtt-disk: ok - 0 de 3 copias de trabajo"), "D2 it speaks the project's language", out + err)
    plain = os.path.join(tmp, "not-a-repo")
    os.makedirs(os.path.join(plain, ".gtt/contract"))
    shutil.copy2(os.path.join(project, ".gtt/contract/disk.json"), os.path.join(plain, ".gtt/contract/disk.json"))
    rc, out, err = run(plain, os.path.join(root, DISK), "check")
    check(rc == 0 and "not inside a Git repository" in out, "D2 outside a repository it says so and exits 0", out + err)


def pruning(project, tmp):
    print("[disk] prune")
    root = repo(project, tmp, "prn")
    merged_copy = add_copy(root, "merged")
    dirty = add_copy(root, "dirty")
    write(os.path.join(dirty, "new.txt"), "uncommitted\n")
    ahead = add_copy(root, "ahead")
    write(os.path.join(ahead, "work.txt"), "w\n")
    git(ahead, "add", "-A")
    git(ahead, "commit", "-q", "-m", "work")
    locked = add_copy(root, "locked")
    git(root, "worktree", "lock", locked)
    before = listed(root)
    rc, out, err = run(root, DISK, "prune", merged_copy)
    check(rc == 0 and "dry run" in out and listed(root) == before, "D3 without --apply nothing is removed", out + err)
    rc, out, err = run(root, DISK, "prune")
    check(rc == 0 and listed(root) == before and "nothing to remove" in out, "D3 with no path, a copy used a minute ago is left alone", out + err)
    for label, path in (("dirty", dirty), ("ahead of main", ahead), ("locked", locked)):
        rc, out, err = run(root, DISK, "prune", path, "--apply")
        check(rc == 0 and path in listed(root) and os.path.isdir(path), f"D3 a {label} work copy is never removed", out + err)
    rc, out, err = run(merged_copy, os.path.join(root, DISK), "prune", merged_copy, "--apply")
    check(merged_copy in listed(root), "D3 the folder you stand in is never removed", out + err)
    rc, out, err = run(root, DISK, "prune", tmp)
    check(rc == 1 and "is not a work copy" in err, "D3 a path that is not a work copy is refused", out + err)
    rc, out, err = run(root, DISK, "prune", merged_copy, "--apply")
    check(rc == 0 and merged_copy not in listed(root) and not os.path.exists(merged_copy), "D3 a merged, clean work copy is removed when named", out + err)
    check(git(root, "branch", "--list", "merged")[1] != "", "D3 removing the work copy keeps its branch")
    check(all(p in listed(root) for p in (dirty, ahead, locked)) and os.path.exists(os.path.join(dirty, "new.txt")),
          "D3 nothing else was touched, the uncommitted file is still there")
    old = add_copy(root, "stale")
    for rel in ("index", "HEAD", os.path.join("logs", "HEAD")):
        gitdir = git(old, "rev-parse", "--absolute-git-dir")[1]
        target = os.path.join(gitdir, rel)
        if os.path.exists(target):
            os.utime(target, (1, 1))
    rc, out, err = run(root, DISK, "prune", "--apply")
    check(old not in listed(root), "D3 with no path, a merged, clean copy idle for 30 minutes is removed", out + err)
    check(all(p in listed(root) for p in (dirty, ahead, locked)), "D3 and the others stay")


def setting(project, tmp):
    print("[disk] set")
    root = repo(project, tmp, "set")
    state = os.path.join(root, STATE)
    rc, out, err = run(root, DISK, "set", "--max-copies", "6")
    check(rc == 0 and not os.path.exists(state) and "dry run" in out and "Recommended: keep the default" in out,
          "D4 a dry run writes nothing and recommends the default when it loosens", out + err)
    rc, out, err = run(root, DISK, "set", "--max-copies", "6", "--apply")
    saved = acc.read_json(state)
    check(rc == 0 and saved == {"max_gb": 15, "max_work_copies": 6, "min_free_gb": 10, "mode": "custom"}, "D4 --apply saves it", out + err + str(saved))
    rc, out, err = run(root, DISK, "status")
    check("6 work copies, 15 GB, 10 GB free" in out and "set by a person" in out, "D4 status says where the numbers come from", out + err)
    link = add_copy(root, "link")
    rc, out, err = run(link, os.path.join(root, DISK), "status")
    check("6 work copies" in out, "D4 a linked work copy reads the main checkout's setting", out + err)
    rc, out, err = run(root, DISK, "set", "--max-gb", "5", "--apply")
    check(acc.read_json(state)["max_gb"] == 5 and acc.read_json(state)["max_work_copies"] == 6, "D4 a later set keeps what was set before", out + err)
    for bad in (("--max-copies", "0"), ("--max-copies", "51"), ("--max-gb", "0"), ("--min-free-gb", "-1")):
        rc, out, err = run(root, DISK, "set", *bad, "--apply")
        check(rc == 1 and "must be a whole number" in err, f"D4 {' '.join(bad)} is refused", out + err)
    rc, out, err = run(root, DISK, "set", "--apply")
    check(rc == 1, "D4 set with nothing to set is refused", out + err)
    rc, out, err = run(root, DISK, "set", "--off", "--max-gb", "9")
    check(rc == 1, "D4 --off stands alone", out + err)
    rc, out, err = run(root, DISK, "set", "--off", "--apply")
    check(rc == 0 and "Recommended: keep it on" in out, "D4 turning the rule off warns", out + err)
    rc, out, err = run(root, DISK, "check")
    check(rc == 0 and "rule is off" in out, "D4 with the rule off, check says so and nothing more", out + err)
    rc, out, err = run(root, DISK, "set", "--default", "--apply")
    check(rc == 0 and not os.path.exists(state), "D4 --default removes the setting", out + err)
    write(state, '{"max_gb": "lots", "mode": "custom"')
    rc, out, err = run(root, DISK, "status")
    check("15 GB" in out and "default rule" in out, "D4 an unreadable setting falls back to the default, never to nothing", out + err)
    write(state, json.dumps({"mode": "custom", "max_work_copies": 99999, "max_gb": 20}))
    rc, out, err = run(root, DISK, "status")
    check("3 work copies, 20 GB" in out, "D4 a value out of bounds is ignored, the rest is kept", out + err)


def hooks(project, tmp):
    print("[disk] who may change it")
    sys.path.insert(0, os.path.join(project, ".gtt", "scripts"))
    sys.dont_write_bytecode = True
    import gtt_protect
    root = repo(project, tmp, "hk")
    for rel in (".gtt/scripts/gtt_protect.py",):
        shutil.copy2(os.path.join(project, rel), os.path.join(root, rel))
    denied = ("bash .gtt/scripts/gtt-disk.sh set --max-copies 9 --apply", "bash .gtt/scripts/gtt-disk.sh set --off",
              "python3 .gtt/scripts/gtt_disk.py set --default --apply", "echo '{}' > .gtt/local/disk.json")
    allowed = ("bash .gtt/scripts/gtt-disk.sh check", "bash .gtt/scripts/gtt-disk.sh status", "bash .gtt/scripts/gtt-disk.sh prune --apply",
               "bash .gtt/scripts/gtt-disk.sh prune ../wt --apply", "git worktree list")
    hook = os.path.join(project, ".claude", "hooks", "protect-l0.py")
    for command in denied:
        reason = gtt_protect.decide_shell(root, command)
        check(bool(reason) and "disk rule" in str(reason), f"D5 portable engine denies: {command}", str(reason)[:120])
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "hook_event_name": "PreToolUse", "cwd": root})
        done = subprocess.run([sys.executable, hook], cwd=root, input=payload, capture_output=True, text=True)
        check("deny" in done.stdout and "disk rule" in done.stdout, f"D5 Claude Code hook denies: {command}", done.stdout[:160] + done.stderr[-120:])
    for command in allowed:
        reason = gtt_protect.decide_shell(root, command)
        check(not reason, f"D5 portable engine allows: {command}", str(reason)[:120])
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "hook_event_name": "PreToolUse", "cwd": root})
        done = subprocess.run([sys.executable, hook], cwd=root, input=payload, capture_output=True, text=True)
        check("deny" not in done.stdout, f"D5 Claude Code hook allows: {command}", done.stdout[:160] + done.stderr[-120:])


def contract_text(project):
    print("[disk] the contract every ADE reads")
    read = lambda rel: open(os.path.join(project, rel), encoding="utf-8").read()
    agents, ops, rules = read("AGENTS.md"), read(".gtt/docs/agents/operations.md"), read(".gtt/docs/agents/rules.md")
    check("## Disk and work copies" in agents and "gtt-disk.sh check" in agents and "*Disk and work copies*" in agents,
          "D6 AGENTS.md carries the rule and points to the detail")
    check("## Disk and work copies" in ops and "3 work copies" in ops and "15 GB" in ops and "10 GB free" in ops
          and "--frozen-lockfile --prefer-offline" in ops and "playwright-report" in ops and "`/tmp`" in ops,
          "D6 operations.md states the rule and its detail: limits, lean install, nothing heavy in a copy")
    check("gtt-disk.sh set" in ops and "recommended" in ops.lower(), "D6 operations.md says only the person changes it and recommends the default")
    check("work copy" in rules and "Never change the disk limits yourself" in rules, "D6 rules.md has the rule")
    for rel in (".gtt/docs/usage.md", ".gtt/docs/usage.es.md"):
        text = read(rel)
        check("gtt-disk.sh set" in text and "--off" in text and "3" in text, f"D6 {rel} tells the person how to change it")
    check("gtt-disk.sh" in read(".gtt/docs/index.md") and "disk.json" in read(".gtt/docs/index.md"), "D6 the docs index maps the script and the contract")
    rc = subprocess.run(["bash", ".gtt/scripts/gtt-check-agents.sh"], cwd=project, capture_output=True, text=True)
    check(rc.returncode == 0, "D6 AGENTS.md still fits what every ADE reads", rc.stdout + rc.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.path.join(HERE, "..", ".."))
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    tmp = tempfile.mkdtemp(prefix="gtt-disk-")
    try:
        contract(project)
        checking(project, tmp)
        pruning(project, tmp)
        setting(project, tmp)
        hooks(project, tmp)
        contract_text(project)
    finally:
        if args.keep:
            print("kept:", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{acc.COUNT - len(acc.FAILS)}/{acc.COUNT} checks held")
    if acc.FAILS:
        print("FAILED:", "; ".join(acc.FAILS))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
