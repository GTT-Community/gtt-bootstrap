#!/usr/bin/env python3
"""GTT - ADE-neutral write protection and session context for hook-capable ADEs.

One decision engine, thin per-ADE formats. An ADE whose hooks can stop a tool call before it runs
points its hook at this script; the script reads the ADE's event on stdin, decides, and answers in
that ADE's own shape. The rules are the same ones Claude Code's own hooks apply:

  governed paths     AGENTS.md, gtt-domain/change-request.md, SOURCE-BRIEF.* - always;
                     gtt-domain/context/ and gtt-domain/adr/ - once gtt-domain/.frozen exists;
                     gtt-domain/proposals/ is always writable
  promotion scripts  an agent never executes gtt-domain/proposals/apply-*.sh
  machinery          the hook configuration that carries this protection is not editable by the agent
  GTTGuard           a protected file or symbol (.gtt/protection/registry.yaml), span resolved live;
                     an edit whose extent is unknown fails safe to the whole file

  gtt_protect.py hook --format cursor|openhands     decide a pre-tool event, or answer a session start
  gtt_protect.py decide --file PATH | --shell CMD   the bare decision, for tests and for a human

A denial exits 2 with the ADE's deny payload. Anything this script does not understand - an unknown
event, an unreadable payload, an unexpected error - exits 0: a broken hook never blocks a session.
Shipped for Cursor and OpenHands from their documented hook contracts; NOT verified inside either
ADE. The CI gate (gtt-check-protection.sh, gtt-check-stack.sh) remains the guaranteed layer.
"""

import argparse
import json
import os
import posixpath
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FROZEN_MARKER = "gtt-domain/.frozen"
REGIME_DIRS = ("gtt-domain/context", "gtt-domain/adr")
PROPOSALS_DIR = "gtt-domain/proposals"
REGISTRY = ".gtt/protection/registry.yaml"

ROOT_FILES = re.compile(r"AGENTS\.md|change-request\.md|SOURCE-BRIEF\.", re.IGNORECASE)
MACHINERY = re.compile(r"\.claude/settings(\.local)?\.json|\.claude/hooks/|\.cursor/hooks\.json|\.openhands/hooks\.json"
                       r"|\.gtt/scripts/gtt_protect\.py", re.IGNORECASE)
MUTATING_SHELL = re.compile(
    r"\b(sed\s+-i|tee|mv|cp|rm|truncate|dd|install"
    r"|del|erase|rd|rmdir|ri|move|copy|ren"
    r"|set-content|add-content|out-file|new-item|remove-item"
    r"|move-item|copy-item|rename-item|clear-content)\b|>>?",
    re.IGNORECASE,
)
PROMOTION_SCRIPT_EXEC = re.compile(r"\b(?:bash|sh|\.)\s+\S*proposals/apply-[A-Za-z0-9._-]+\.sh\b", re.IGNORECASE)
TOKEN_SPLIT = re.compile(r"[\s\"'=(<>|;&,`]+")

GOVERNED = ("GTT governance: AGENTS.md, gtt-domain/context/, gtt-domain/adr/, gtt-domain/change-request.md, "
            "SOURCE-BRIEF.* and the hook configuration that protects them are owned by the Solution Designer. "
            "Write your draft to gtt-domain/proposals/ instead - that directory is yours - and follow the change "
            "process in AGENTS.md.")
PROMOTION = ("GTT governance: a promotion script is run by the human, never by an agent (AGENTS.md -> Human "
             "Promotion Boundary). Tell the human the command and stop.")
PROPOSE = "Draft a proposal (AGENTS.md -> Protected artifacts) instead of editing it directly."


def normalize(path):
    return path.replace("\\", "/")


def relative(token, root):
    """The token as a project-relative path, or None when it is not inside the project."""
    t = normalize(token).strip()
    if not t or t.startswith("-"):
        return None
    if os.name == "nt":
        drive = re.match(r"^/([A-Za-z])/(.*)$", t)
        if drive:
            t = f"{drive.group(1).upper()}:/{drive.group(2)}"
    absolute = t if (t.startswith("/") or re.match(r"^[A-Za-z]:/", t)) else f"{root}/{t}"
    resolved = posixpath.normpath(absolute)
    if resolved.lower() == root.lower():
        return ""
    prefix = root.lower() + "/"
    return resolved[len(prefix):] if resolved.lower().startswith(prefix) else None


def under(rel, directory):
    return rel.lower() == directory or rel.lower().startswith(directory + "/")


def governed(root, target):
    """True when a file path, or any path-like token of a shell command, is a governed path."""
    target = normalize(target)
    if MACHINERY.search(target):
        return True
    regime = proposals = False
    for token in TOKEN_SPLIT.split(target):
        rel = relative(token, root) if token else None
        if rel is None:
            continue
        regime = regime or any(under(rel, d) for d in REGIME_DIRS)
        proposals = proposals or under(rel, PROPOSALS_DIR)
    if proposals:
        return False
    if regime:
        return os.path.exists(os.path.join(root, FROZEN_MARKER))
    return bool(ROOT_FILES.search(target))


def guard_entries(root):
    try:
        import gtt_guard
        with open(os.path.join(root, REGISTRY), encoding="utf-8") as handle:
            return gtt_guard, [e for e in gtt_guard.parse_registry(handle.read()) if e.get("protection") == "HUMAN_APPROVAL"]
    except Exception:
        return None, []


def guard_file(root, rel, old_string):
    """Why a write to `rel` touches a GTTGuard-protected artifact, or None."""
    engine, entries = guard_entries(root)
    hits = [e for e in entries if rel == normalize(e["artifact"]) or rel.endswith("/" + normalize(e["artifact"]))]
    if not hits:
        return None
    if any(not h["symbol"] for h in hits):
        return f"GTTGuard: {rel} is protected (HUMAN_APPROVAL) - the whole file is protected. {PROPOSE}"
    if not old_string:
        return (f"GTTGuard: {rel} contains a protected symbol and the extent of this write is unknown. Failing safe: "
                f"the whole file is treated as protected. {PROPOSE}")
    try:
        with open(os.path.join(root, hits[0]["artifact"]), encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return None
    at = text.find(old_string)
    for hit in hits:
        span = engine.resolve_symbol_span(root, hit["artifact"], hit["symbol"])
        if span is None:
            return (f"GTTGuard: {rel} declares protected symbol '{hit['symbol']}' that could not be resolved. Failing "
                    f"safe: the whole file is treated as protected. Run .gtt/scripts/gtt-check-protection.sh.")
        if at == -1:
            continue
        first = text.count("\n", 0, at)
        if first <= span[1] and first + old_string.count("\n") >= span[0]:
            return f"GTTGuard: {hit['symbol']} in {rel} is protected (HUMAN_APPROVAL). {PROPOSE}"
    return None


def decide_file(root, path, old_string=None):
    rel = relative(path, root)
    if rel is None:
        return None
    if governed(root, rel):
        return GOVERNED
    return guard_file(root, rel, old_string)


def decide_shell(root, command):
    if PROMOTION_SCRIPT_EXEC.search(normalize(command)):
        return PROMOTION
    if not MUTATING_SHELL.search(command):
        return None                                         # reads stay allowed
    if governed(root, command):
        return GOVERNED
    _, entries = guard_entries(root)
    for entry in entries:
        if normalize(entry["artifact"]) in normalize(command):
            return (f"GTTGuard: {entry['artifact']} is a protected artifact. Shell commands that could mutate a "
                    f"protected file are always blocked. {PROPOSE}")
    return None


def session_context(root):
    proc = subprocess.run(["bash", os.path.join(".gtt", "scripts", "gtt-session-context.sh")], cwd=root,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout if proc.returncode == 0 and proc.stdout.strip() else None


PATH_KEYS = ("file_path", "path", "target_file", "filePath", "notebook_path")


def first_path(tool_input):
    for key in PATH_KEYS:
        if isinstance(tool_input.get(key), str) and tool_input[key]:
            return tool_input[key]
    return None


def cursor(event):
    """Cursor: .cursor/hooks.json -> preToolUse / beforeShellExecution / sessionStart."""
    roots = event.get("workspace_roots") or []
    root = normalize(os.path.abspath(roots[0] if roots else event.get("cwd") or os.getcwd())).rstrip("/")
    name = event.get("hook_event_name", "")
    tool_input = event.get("tool_input") or {}
    reason = None
    if name == "sessionStart":
        text = session_context(root)
        return (0, {"additional_context": text}) if text else (0, None)
    if name == "beforeShellExecution":
        reason = decide_shell(root, event.get("command", ""))
    elif name == "preToolUse":
        tool = event.get("tool_name", "")
        if tool == "Shell":
            reason = decide_shell(root, tool_input.get("command", ""))
        elif tool in ("Write", "Delete", "Edit"):
            path = first_path(tool_input)
            reason = decide_file(root, path, tool_input.get("old_string")) if path else None
    if reason:
        return 2, {"permission": "deny", "user_message": reason, "agent_message": reason}
    return 0, None


def openhands(event):
    """OpenHands: .openhands/hooks.json -> pre_tool_use / session_start."""
    root = normalize(os.path.abspath(os.environ.get("OPENHANDS_PROJECT_DIR") or event.get("working_dir") or os.getcwd())).rstrip("/")
    name = event.get("event_type") or os.environ.get("OPENHANDS_EVENT_TYPE", "")
    tool_input = event.get("tool_input") or {}
    reason = None
    if name == "SessionStart":
        text = session_context(root)
        return (0, {"additionalContext": text}) if text else (0, None)
    if name == "PreToolUse":
        path = first_path(tool_input)
        command = tool_input.get("command", "")
        if path:                                            # a file tool: `command` is its sub-command
            if command != "view":
                reason = decide_file(root, path, tool_input.get("old_str") or tool_input.get("old_string"))
        elif isinstance(command, str) and command:
            reason = decide_shell(root, command)
    if reason:
        return 2, {"decision": "deny", "reason": reason}
    return 0, None


FORMATS = {"cursor": cursor, "openhands": openhands}


def cmd_hook(args):
    try:
        event = json.load(sys.stdin)
        code, payload = FORMATS[args.format](event if isinstance(event, dict) else {})
    except Exception:
        return 0
    if payload is not None:
        print(json.dumps(payload))
    return code


def cmd_decide(args):
    root = normalize(os.path.abspath(os.getcwd())).rstrip("/")
    reason = decide_file(root, args.file) if args.file else decide_shell(root, args.shell or "")
    print(reason or "allow")
    return 2 if reason else 0


def main(argv):
    parser = argparse.ArgumentParser(prog="gtt_protect.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("hook"); p.add_argument("--format", required=True, choices=sorted(FORMATS)); p.set_defaults(func=cmd_hook)
    p = sub.add_parser("decide"); p.add_argument("--file"); p.add_argument("--shell"); p.set_defaults(func=cmd_decide)
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
