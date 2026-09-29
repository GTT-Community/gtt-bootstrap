"""D3: the staged hook on a POSIX-style root under a one-letter top-level directory,
plus regression checks that the Windows/MSYS behaviour is unchanged. Pure functions:
nothing here touches any repository."""
import importlib.util, os, sys

sys.dont_write_bytecode = True
HOOK = r"C:\griott\GTT\gtt-bootstrap\gtt\proposals\scaffold-restructure\overlay\claude-hooks\protect-l0.py"
spec = importlib.util.spec_from_file_location("hook", HOOK)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)

fails = 0


def check(label, got, want):
    global fails
    ok = got == want
    fails += not ok
    print(("PASS  " if ok else "FAIL  ") + label + f" -> {got!r}" + ("" if ok else f" (want {want!r})"))


REAL_NAME = os.name

# ---- POSIX: os.name == 'posix'
os.name = "posix"
try:
    check("posix  root=/x/proj   /x/proj/context/stack.md", h.relative_to_root("/x/proj/context/stack.md", "/x/proj"), "context/stack.md")
    check("posix  root=/x/proj   /x/proj/adr/ADR-001.md", h.relative_to_root("/x/proj/adr/ADR-001.md", "/x/proj"), "adr/ADR-001.md")
    check("posix  root=/x/proj   ./context/a.md", h.relative_to_root("./context/a.md", "/x/proj"), "context/a.md")
    check("posix  root=/x/proj   ../x/proj/context/a.md", h.relative_to_root("../x/proj/context/a.md", "/x/proj"), None)  # from /x/proj, ../x = /x/x
    check("posix  root=/x/proj   /y/other/context/a.md (outside)", h.relative_to_root("/y/other/context/a.md", "/x/proj"), None)
    check("posix  root=/home/u/proj  /home/u/proj/context/a.md", h.relative_to_root("/home/u/proj/context/a.md", "/home/u/proj"), "context/a.md")

    # end to end through is_protected with a POSIX root and a frozen project
    h.project_root = lambda: "/x/proj"
    h.is_frozen = lambda: True
    check("posix  is_protected Write /x/proj/context/stack.md", h.is_protected("/x/proj/context/stack.md"), True)
    check("posix  is_protected Write /x/proj/adr/ADR-9.md", h.is_protected("/x/proj/adr/ADR-9.md"), True)
    check("posix  is_protected shell rm /x/proj/context/stack.md", h.is_protected("rm /x/proj/context/stack.md"), True)
    check("posix  is_protected /x/proj/src/context/a.ts (host's own dir)", h.is_protected("/x/proj/src/context/a.ts"), False)
    check("posix  is_protected /x/proj/proposals/PROPOSAL-x.md", h.is_protected("/x/proj/proposals/PROPOSAL-x.md"), False)
    check("posix  is_protected /x/proj/change-request.md", h.is_protected("/x/proj/change-request.md"), True)
    check("posix  is_protected /x/proj/.claude/hooks/x.py", h.is_protected("/x/proj/.claude/hooks/x.py"), True)
finally:
    os.name = REAL_NAME

# ---- what the OLD conversion did (documents the defect, run on the same input)
import re
def old_conversion(t, root):
    m = re.match(r"^/([A-Za-z])/(.*)$", t)
    if m:
        t = f"{m.group(1).upper()}:/{m.group(2)}"
    return t
print("INFO  old code on /x/proj/context/stack.md ->", old_conversion("/x/proj/context/stack.md", "/x/proj"), "(resolves outside /x/proj: unprotected)")

# ---- Windows/MSYS behaviour must be unchanged
os.name = "nt"
try:
    check("nt     root=C:/griott/p  /c/griott/p/context/stack.md", h.relative_to_root("/c/griott/p/context/stack.md", "C:/griott/p"), "context/stack.md")
    check("nt     root=C:/griott/p  C:\\griott\\p\\adr\\a.md", h.relative_to_root("C:\\griott\\p\\adr\\a.md".replace("\\", "/"), "C:/griott/p"), "adr/a.md")
    check("nt     root=C:/griott/p  /d/other/context/a.md (outside)", h.relative_to_root("/d/other/context/a.md", "C:/griott/p"), None)
    check("nt     case-insensitive  /C/GRIOTT/P/Context/a.md", h.relative_to_root("/C/GRIOTT/P/Context/a.md", "C:/griott/p"), "Context/a.md")
finally:
    os.name = REAL_NAME
print("POSIX/NT HOOK RESULT:", "ALL PASS" if not fails else f"{fails} FAIL")
sys.exit(1 if fails else 0)
