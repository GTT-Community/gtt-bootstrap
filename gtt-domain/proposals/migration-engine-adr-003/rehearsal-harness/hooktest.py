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
cases = [
    ("Write", dict(file_path=W + "\\context\\stack.md"), 2),
    ("Write", dict(file_path=W + "\\adr\\ADR-009.md"), 2),
    ("Edit", dict(file_path=FW + "/context/stack.md"), 2),
    ("Write", dict(file_path=W + "\\src\\context\\x.ts"), 0),
    ("Write", dict(file_path=W + "\\src\\adr\\x.ts"), 0),
    ("Write", dict(file_path=W + "\\proposals\\PROPOSAL-x.md"), 0),
    ("Write", dict(file_path=W + "\\proposals\\scaffold-restructure\\overlay\\x.py"), 0),
    ("Write", dict(file_path=W + "\\backlog.md"), 0),
    ("Write", dict(file_path=W + "\\change-request.md"), 2),
    ("Write", dict(file_path=W + "\\AGENTS.md"), 2),
    ("Write", dict(file_path=W + "\\.claude\\hooks\\x.py"), 2),
    ("Write", dict(file_path=W + "\\gtt\\scripts\\x.sh"), 0),
    ("NotebookEdit", dict(notebook_path=W + "\\context\\n.ipynb"), 2),
    ("Bash", dict(command="rm context/stack.md"), 2),
    ("Bash", dict(command="sed -i s/a/b/ ./context/stack.md"), 2),
    ("Bash", dict(command="rm " + FW + "/adr/ADR-001-context-governance.md"), 2),
    ("Bash", dict(command="rm -rf ../" + base + "/context"), 2),
    ("Bash", dict(command="echo x > context/stack.md"), 2),
    ("Bash", dict(command="tee adr/x.md"), 2),
    ("Bash", dict(command="cd context && rm stack.md"), 2),
    ("Bash", dict(command="cat context/stack.md"), 0),
    ("Bash", dict(command="grep -r foo context adr"), 0),
    ("Bash", dict(command="rm src/context/x.ts"), 0),
    ("Bash", dict(command="cp context/stack.md proposals/context-stack.md"), 0),
    ("Bash", dict(command="bash proposals/apply-x.sh"), 2),
    ("Bash", dict(command="bash ./proposals/apply-x.sh"), 2),
    ("Bash", dict(command="bash gtt/proposals/apply-x.sh"), 2),
    ("Bash", dict(command="echo x > change-request.md"), 2),
    ("Bash", dict(command="mv AGENTS.md x"), 2),
    ("Bash", dict(command="echo x > backlog.md"), 0),
    ("Bash", dict(command="sed -i s/a/b/ .claude/settings.json"), 2),
    ("PowerShell", dict(command="Remove-Item .\\context\\stack.md"), 2),
    ("PowerShell", dict(command="Set-Content -Path " + W + "\\adr\\x.md -Value hi"), 2),
    ("PowerShell", dict(command="Remove-Item .\\src\\context\\x.ts"), 0),
    ("PowerShell", dict(command="Get-Content .\\context\\stack.md"), 0),
]
bad = 0
for tool, ti, want in cases:
    got = run(tool, **ti)
    ok = got == want
    bad += not ok
    print(("ok  " if ok else "FAIL"), tool, str(ti)[:110], "->", got, "(want %d)" % want)

# pre-freeze: governed dirs writable, root files still protected
os.rename(".frozen", ".frozen.bak")
for tool, ti, want in [
    ("Write", dict(file_path=W + "\\context\\stack.md"), 0),
    ("Bash", dict(command="rm adr/x"), 0),
    ("Write", dict(file_path=W + "\\AGENTS.md"), 2),
]:
    got = run(tool, **ti)
    ok = got == want
    bad += not ok
    print(("ok  " if ok else "FAIL"), "PRE-FREEZE", tool, str(ti)[:80], "->", got, "(want %d)" % want)
os.rename(".frozen.bak", ".frozen")
print("failures:", bad)
