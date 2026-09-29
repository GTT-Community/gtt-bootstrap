"""The migrated hook on a POSIX-style root under a one-letter top-level directory, plus regression checks that
the Windows/MSYS behaviour is unchanged. Pure functions: nothing here touches any repository.
Usage: python posix_hook_test.py <path to overlay/claude-hooks/protect-l0.py>"""
import importlib.util, os, sys

sys.dont_write_bytecode = True
HOOK = sys.argv[1]
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
os.name = "posix"
try:
    check("posix  /x/proj/gtt-domain/context/stack.md", h.relative_to_root("/x/proj/gtt-domain/context/stack.md", "/x/proj"), "gtt-domain/context/stack.md")
    check("posix  /x/proj/gtt-domain/adr/ADR-001.md", h.relative_to_root("/x/proj/gtt-domain/adr/ADR-001.md", "/x/proj"), "gtt-domain/adr/ADR-001.md")
    check("posix  ./gtt-domain/context/a.md", h.relative_to_root("./gtt-domain/context/a.md", "/x/proj"), "gtt-domain/context/a.md")
    check("posix  ../x/proj/gtt-domain/context/a.md (=/x/x/...)", h.relative_to_root("../x/proj/gtt-domain/context/a.md", "/x/proj"), None)
    check("posix  /y/other/gtt-domain/context/a.md (outside)", h.relative_to_root("/y/other/gtt-domain/context/a.md", "/x/proj"), None)
    h.project_root = lambda: "/x/proj"
    h.is_frozen = lambda: True
    check("posix  is_protected Write /x/proj/gtt-domain/context/stack.md", h.is_protected("/x/proj/gtt-domain/context/stack.md"), True)
    check("posix  is_protected Write /x/proj/gtt-domain/adr/ADR-9.md", h.is_protected("/x/proj/gtt-domain/adr/ADR-9.md"), True)
    check("posix  is_protected shell rm /x/proj/gtt-domain/context/stack.md", h.is_protected("rm /x/proj/gtt-domain/context/stack.md"), True)
    check("posix  is_protected /x/proj/src/context/a.ts (host's own dir)", h.is_protected("/x/proj/src/context/a.ts"), False)
    check("posix  is_protected /x/proj/context/a.md (host's own dir, no longer GTT's)", h.is_protected("/x/proj/context/a.md"), False)
    check("posix  is_protected /x/proj/gtt-domain/proposals/PROPOSAL-x.md", h.is_protected("/x/proj/gtt-domain/proposals/PROPOSAL-x.md"), False)
    check("posix  is_protected /x/proj/gtt-domain/change-request.md", h.is_protected("/x/proj/gtt-domain/change-request.md"), True)
    check("posix  is_protected /x/proj/.claude/hooks/x.py", h.is_protected("/x/proj/.claude/hooks/x.py"), True)
finally:
    os.name = REAL_NAME

os.name = "nt"
try:
    check("nt     /c/griott/p/gtt-domain/context/stack.md", h.relative_to_root("/c/griott/p/gtt-domain/context/stack.md", "C:/griott/p"), "gtt-domain/context/stack.md")
    check("nt     C:\\griott\\p\\gtt-domain\\adr\\a.md", h.relative_to_root("C:\\griott\\p\\gtt-domain\\adr\\a.md".replace("\\", "/"), "C:/griott/p"), "gtt-domain/adr/a.md")
    check("nt     /d/other/gtt-domain/context/a.md (outside)", h.relative_to_root("/d/other/gtt-domain/context/a.md", "C:/griott/p"), None)
    check("nt     case-insensitive  /C/GRIOTT/P/Gtt-Domain/a.md", h.relative_to_root("/C/GRIOTT/P/Gtt-Domain/a.md", "C:/griott/p"), "Gtt-Domain/a.md")
finally:
    os.name = REAL_NAME
print("POSIX/NT HOOK RESULT:", "ALL PASS" if not fails else f"{fails} FAIL")
sys.exit(1 if fails else 0)
