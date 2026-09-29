"""The migrated protect-l0.py hook, driven exactly as Claude Code drives it (JSON on stdin), inside a
migrated disposable copy (cwd = the copy). Windows-style paths, Git-Bash paths, PowerShell and Bash commands."""
import json, subprocess, sys, os
root = os.getcwd()
W = root.replace("/", "\\")
FW = root.replace("\\", "/")
HOOK = os.path.join(".claude", "hooks", "protect-l0.py")


def run(tool, **ti):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": tool, "tool_input": ti}),
                       text=True, capture_output=True)
    return p.returncode


base = os.path.basename(root)
D = "\\gtt-domain"
cases = [
    # governed context and decisions: denied once frozen
    ("Write", dict(file_path=W + D + "\\context\\stack.md"), 2),
    ("Write", dict(file_path=W + D + "\\adr\\ADR-009.md"), 2),
    ("Edit", dict(file_path=FW + "/gtt-domain/context/stack.md"), 2),
    ("NotebookEdit", dict(notebook_path=W + D + "\\context\\n.ipynb"), 2),
    # the host project's own directories with the same names are untouched
    ("Write", dict(file_path=W + "\\src\\context\\x.ts"), 0),
    ("Write", dict(file_path=W + "\\src\\adr\\x.ts"), 0),
    ("Write", dict(file_path=W + "\\docs\\guide.md"), 0),
    ("Write", dict(file_path=W + "\\context\\x.md"), 0),
    ("Write", dict(file_path=W + "\\adr\\x.md"), 0),
    ("Write", dict(file_path=W + "\\proposals\\x.md"), 0),
    # the one directory an agent writes
    ("Write", dict(file_path=W + D + "\\proposals\\PROPOSAL-x.md"), 0),
    ("Write", dict(file_path=W + D + "\\proposals\\gtt-domain-migration\\overlay\\x.py"), 0),
    # backlog is a direct edit; change request and the entry points are protected
    ("Write", dict(file_path=W + D + "\\backlog.md"), 0),
    ("Write", dict(file_path=W + D + "\\change-request.md"), 2),
    ("Write", dict(file_path=W + "\\AGENTS.md"), 2),
    ("Write", dict(file_path=W + "\\.claude\\hooks\\x.py"), 2),
    ("Write", dict(file_path=W + "\\.claude\\settings.json"), 2),
    # the Engine is not governed context (same as gtt/ before), and its docs are outside the freeze regime
    ("Write", dict(file_path=W + "\\.gtt\\scripts\\x.sh"), 0),
    ("Write", dict(file_path=W + "\\.gtt\\docs\\usage.md"), 0),
    # shell
    ("Bash", dict(command="rm gtt-domain/context/stack.md"), 2),
    ("Bash", dict(command="sed -i s/a/b/ ./gtt-domain/context/stack.md"), 2),
    ("Bash", dict(command="rm " + FW + "/gtt-domain/adr/ADR-001-context-governance.md"), 2),
    ("Bash", dict(command="rm -rf ../" + base + "/gtt-domain/context"), 2),
    ("Bash", dict(command="echo x > gtt-domain/context/stack.md"), 2),
    ("Bash", dict(command="tee gtt-domain/adr/x.md"), 2),
    ("Bash", dict(command="cd gtt-domain/context && rm stack.md"), 2),
    ("Bash", dict(command="cat gtt-domain/context/stack.md"), 0),
    ("Bash", dict(command="grep -r foo gtt-domain/context gtt-domain/adr"), 0),
    ("Bash", dict(command="rm src/context/x.ts"), 0),
    ("Bash", dict(command="rm docs/old.md"), 0),
    ("Bash", dict(command="cp gtt-domain/context/stack.md gtt-domain/proposals/context-stack.md"), 0),
    ("Bash", dict(command="bash gtt-domain/proposals/apply-x.sh"), 2),
    ("Bash", dict(command="bash ./gtt-domain/proposals/apply-x.sh"), 2),
    ("Bash", dict(command="bash proposals/apply-x.sh"), 2),
    ("Bash", dict(command="echo x > gtt-domain/change-request.md"), 2),
    ("Bash", dict(command="mv AGENTS.md x"), 2),
    ("Bash", dict(command="echo x > gtt-domain/backlog.md"), 0),
    ("Bash", dict(command="sed -i s/a/b/ .claude/settings.json"), 2),
    ("PowerShell", dict(command="Remove-Item .\\gtt-domain\\context\\stack.md"), 2),
    ("PowerShell", dict(command="Set-Content -Path " + W + "\\gtt-domain\\adr\\x.md -Value hi"), 2),
    ("PowerShell", dict(command="Remove-Item .\\src\\context\\x.ts"), 0),
    ("PowerShell", dict(command="Get-Content .\\gtt-domain\\context\\stack.md"), 0),
]
bad = 0
for tool, ti, want in cases:
    got = run(tool, **ti)
    ok = got == want
    bad += not ok
    print(("ok  " if ok else "FAIL"), tool, str(ti)[:110], "->", got, "(want %d)" % want)

# pre-freeze: governed dirs writable, protected files still protected
M = os.path.join("gtt-domain", ".frozen")
os.rename(M, M + ".bak")
for tool, ti, want in [
    ("Write", dict(file_path=W + D + "\\context\\stack.md"), 0),
    ("Bash", dict(command="rm gtt-domain/adr/x"), 0),
    ("Write", dict(file_path=W + "\\AGENTS.md"), 2),
    ("Write", dict(file_path=W + D + "\\change-request.md"), 2),
]:
    got = run(tool, **ti)
    ok = got == want
    bad += not ok
    print(("ok  " if ok else "FAIL"), "PRE-FREEZE", tool, str(ti)[:80], "->", got, "(want %d)" % want)
os.rename(M + ".bak", M)
print("failures:", bad)
sys.exit(1 if bad else 0)
