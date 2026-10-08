#!/usr/bin/env python3
"""GTT - L0/L1 context protection (PreToolUse hook).

permissions.deny already blocks the Write/Edit tools for the unconditional
machinery paths. This hook covers what static config can't express: shell
commands (sed -i, tee, redirection, mv, rm, ...) reaching those same
machinery paths and the three protected governance files - AGENTS.md,
change-request.md (in gtt-domain/), and
SOURCE-BRIEF.* (stays at the project root, the one human-facing exception) -
without going through a file tool, and the two-regime condition on
gtt-domain/context/ and gtt-domain/adr/ - writable pre-freeze, denied once
gtt-domain/.frozen exists. A static permissions.deny entry can't test for a
file's existence, so those two paths are deliberately absent from
settings.json and live here instead.

ROOT_FILES matches by filename substring, not by directory prefix, so it
keeps protecting AGENTS.md, change-request.md, and SOURCE-BRIEF.*
correctly regardless of which directory each lives in. This does mean a
nested AGENTS.md some ADEs use to approximate path-scoped rules in an
installed host project (e.g. Codex's src/AGENTS.md convention, documented in
docs/docs.md) would also match here if this hook is copied into that
project - accepted as the same coarse-but-safe tradeoff already made for
change-request.md and SOURCE-BRIEF.*, and irrelevant to this repository,
which has exactly one AGENTS.md, at the root.

Machinery (.claude/settings.json, .claude/settings.local.json,
.claude/hooks/) has no regime exception and no Write/Edit fallback here
either: permissions.deny already blocks the tool path, so this hook's job
for machinery is exclusively the shell path - an agent must never be able
to disarm its own protection via sed/rm/tee/redirection just because that
happens to route through Bash instead of Edit. settings.local.json is
covered for the same reason as settings.json itself: Claude Code merges it
into the effective permissions/hooks configuration, so it is exactly as
capable of disabling this mechanism and must not be reachable by any path
settings.json itself is denied on.

Root-anchored paths: the governed directories moved from the
project root to gtt-domain/context/ and gtt-domain/adr/, and
gtt-domain/proposals/ is the one directory agents may write. A bare
substring test for "context/" would also fire on a host project's own
src/context/ (a very common directory name) and deny legitimate edits, so
paths are RESOLVED instead: every path-like token (a tool's file_path, or a
token of a shell command) is normalised, resolved against the project root,
and only a result that lands at <root>/gtt-domain/context/,
<root>/gtt-domain/adr/ or <root>/gtt-domain/proposals/ counts. This is at least as strict as the old substring
test for everything that resolves into those directories - absolute Windows
paths, Git-Bash /c/... paths, ./ prefixes, backslashes and ../ traversal
all resolve to the same place - and it stops matching unrelated directories
that merely share a name.

Path normalisation (fixed 2026-09-28): Write/Edit/NotebookEdit deliver an
ABSOLUTE WINDOWS PATH (backslashes) as file_path on this platform, and a
PowerShell command may equally use backslash paths. Every pattern below is
written with forward slashes, so without normalising first, an absolute
Windows path to a governed directory silently never matched and the
freeze-regime block never fired for the Write/Edit tools - demonstrated
live: a Write to a Windows-style absolute path under the governed context
after freeze was NOT denied, while the equivalent `rm` via Bash
(forward-slash path) WAS. normalize() is applied to every caller - file-tool
paths and shell command strings alike - without duplicating the fix.

PowerShell coverage (added 2026-09-28): this environment's primary shell is
PowerShell, not Bash, and the hook previously only inspected the Bash tool's
command string - a PowerShell Set-Content/Remove-Item/etc. against a
protected path passed through unchecked. MUTATING_SHELL now also matches
common PowerShell mutating cmdlets and their built-in aliases (case
insensitive - PowerShell itself is), and both Bash and PowerShell tool
calls are inspected the same way.

Blocking is explicit (the two planes, 2026-10-06): this hook stops a call only
where the governed state says so, and every denial names its basis - a governed
path, a promotion script, a human-only act (freezing; deciding an observation),
or a path boundary the frozen design declares BLOCKING (gtt-boundaries in
gtt-domain/context/stack.md). Ordinary work is never its business. Two false
positives that made it block work that only LOOKED unusual were removed with
that change:

  * a redirect into `.gtt/` (derived state, docs) counted as a mutation of a
    governed path because the pattern matched any `gtt/`; it now names the
    governed targets only - and gains AGENTS.md, which it was missing;
  * AGENTS.md, change-request.md and SOURCE-BRIEF.* were matched as substrings
    of the whole command, so a read-only search or a heredoc that merely
    MENTIONED one was denied whenever an unrelated mutating word appeared
    anywhere in it. They are now matched against path tokens.

One decision core, two engines (Bootstrap 1.3.1): everything this hook decides now
lives in the decision core below, which is byte-identical to the one in
.gtt/scripts/gtt_protect.py (the engine Cursor, OpenHands and Antigravity use). The
two differ only in how the event comes in and how the answer goes out. The core
closed what an audit reproduced against this hook with real PreToolUse payloads:

  * the freeze marker could be removed or written by an agent (rm, a Write to
    gtt-domain/.frozen): an unfreeze, and a freeze, that nobody decided;
  * the governance ledger could be edited directly, forging an accept or a reject;
  * a promotion script ran when it was not spelled `bash <path>` (./path, sh, source,
    an absolute path, env bash ...), and a staged patch could be applied with
    `git apply`;
  * naming any file under gtt-domain/proposals/ excused every other path of the same
    command, so `cp gtt-domain/proposals/x AGENTS.md` passed;
  * with the Git hook installed, `git commit --no-verify` and core.hooksPath skipped it;
  * a broken observation engine switched BLOCKING boundaries off without a word - it
    still never blocks a session, but now it says so.

Exit 2 plus permissionDecision:deny blocks the call deterministically.
Any unexpected input exits 0 so a broken hook never blocks a session.
"""

import json
import os
import posixpath
import re
import shlex
import sys

# >>> gtt-decision-core >>>
# The decision core. This block is IDENTICAL, byte for byte, in .claude/hooks/protect-l0.py and in
# .gtt/scripts/gtt_protect.py: the two engines differ only in how an ADE's event comes in and how
# the answer goes out, never in what is decided. .gtt/tests/bootstrap-acceptance.py fails when the
# two copies differ, and runs one table of cases against both.
#
# It stops a call only where the governed state says so, and every denial names its rule:
#
#   governed paths     AGENTS.md, change-request.md, SOURCE-BRIEF.* - always; gtt-domain/context/
#                      and gtt-domain/adr/ - once frozen; gtt-domain/proposals/ is always writable
#   machinery          the hook configuration and engine that carry this protection
#   instruction plane  only in an installed project (.gtt/ade.json exists): the GTT engine
#                      (.gtt/scripts/, .gtt/contract/), the ADE state and the instructions agents
#                      work under. In the catalog repository they are the product being built
#   freeze marker      gtt-domain/.frozen, in both regimes: the human freezes; there is no unfreeze
#   governance ledger  gtt-domain/governance-backlog.json: only the observation engine writes it
#   promotion          an agent never runs gtt-domain/proposals/apply-*.sh, in any spelling, and
#                      never applies a patch staged there (--check / --stat stay available)
#   human acts         freezing; accepting, rejecting or deferring an observation; installing or
#                      removing the Git hook; applying a staged promotion set (gtt-promote.sh)
#   Git workflow       what gtt-domain/workflow.md forbids: `commits: never` (commit, tag, push) and
#                      `branches-tags: never` (a new branch or tag). `on-request` is an instruction,
#                      not a rule here: a hook cannot see what the user asked for. In an installed
#                      project the workflow file itself is the human's
#   sources            docs/sources/: a registered source is immutable evidence - a new version is
#                      added with gtt-source.sh, never edited; after the freeze, registering one is
#                      the human's act
#   approval           an Epic and its design are approved by the human (gtt-approve.sh)
#   local state        .gtt/local/checkpoint.json and last-validation.json: written by GTT's scripts
#                      only - the review would lie if an agent could forge them
#   Git hook bypass    only where the GTT pre-commit hook is installed: --no-verify, core.hooksPath
#   boundaries         a path the frozen design declares BLOCKING (gtt-boundaries in stack.md)
#
# What it cannot see - a write made by an interpreter (python -c "open(...)") or by Git plumbing
# (git checkout <ref> -- <path>) - is not chased with more patterns: the CI gate
# (gtt-check-stack.sh, gtt-validate.sh) is the layer that holds there.

FROZEN_MARKER = "gtt-domain/.frozen"
LEDGER = "gtt-domain/governance-backlog.json"
STACK_MAP = "gtt-domain/context/stack.md"
DOMAIN_DIR = "gtt-domain"
REGIME_DIRS = ("gtt-domain/context", "gtt-domain/adr")
PROPOSALS_DIR = "gtt-domain/proposals"
GIT_HOOK = ".git/hooks/pre-commit"
WORKFLOW_FILE = "gtt-domain/workflow.md"
LOCAL_STATE = (".gtt/local/checkpoint.json", ".gtt/local/last-validation.json")
SOURCES_DIR = "docs/sources"
BRANCH_LISTING = {"-l", "--list", "--show-current", "-a", "--all", "-r", "--remotes", "-v", "-vv", "--contains", "--merged",
                  "--no-merged", "--points-at"}
GIT_HOOK_MARK = "# gtt-git-hook: installed by .gtt/scripts/gtt-git-hook.sh"

# Matched against the project-relative path of a write target: the contract and the source brief at
# the project root, and the change-request front door. A nested AGENTS.md - scoped rules for Codex or
# Copilot - is the project's own file.
ROOT_FILES = re.compile(r"^(?:AGENTS\.md|(?:gtt-domain/)?change-request\.md|SOURCE-BRIEF\.[^/]*)[*?]*$", re.IGNORECASE)
MACHINERY = re.compile(
    r"\.claude/settings(\.local)?\.json|\.claude/hooks/|\.cursor/hooks\.json|\.openhands/hooks\.json"
    r"|\.agents/hooks\.json|\.kiro/hooks/|\.github/hooks/gtt-protect\.json|\.gtt/scripts/gtt_protect\.py",
    re.IGNORECASE,
)
# The instruction plane. A project is installed when .gtt/ade.json exists: the manifest requires it
# there and the catalog repository never has it.
INSTALLED_MARK = ".gtt/ade.json"
PLANE_DIRS = (".gtt/scripts", ".gtt/contract", ".gtt/docs/agents", ".claude/skills", ".claude/rules", ".kiro/steering",
              ".agents/skills/gtt")
PLANE_FILES = re.compile(
    r"^(?:\.gtt/ade\.json|\.claude/claude\.md|\.cursor/rules/gtt[^/]*\.mdc|\.agents/rules/gtt[^/]*\.md"
    r"|\.github/instructions/gtt[^/]*\.md)$",
    re.IGNORECASE,
)
# A shell command is judged by what it writes: the operands of a command that mutates and the target
# of a redirect. A path it only reads, and the words of a here-document nobody executes, are not writes.
COPIES = {"cp", "copy", "copy-item", "install", "ln", "rsync", "scp"}       # only the last operand is written
MUTATORS = {"rm", "mv", "tee", "truncate", "unlink", "shred", "touch", "del", "erase", "rd", "rmdir", "ri", "move", "ren",
            "set-content", "add-content", "out-file", "new-item", "remove-item", "move-item", "rename-item", "clear-content"}
IN_PLACE = re.compile(r"^(?:-[A-Za-z]*i|--in-place)")
HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")
SHELL_READS = re.compile(r"(?:^|[|;&(]\s*)(?:(?:sudo|env|exec)\s+)*(?:bash|sh|zsh|dash|ksh)\b")
MUTATING_SHELL = re.compile(
    r"\b(sed\s+-i|tee|mv|cp|rm|truncate|dd|install"
    r"|del|erase|rd|rmdir|ri|move|copy|ren"
    r"|set-content|add-content|out-file|new-item|remove-item"
    r"|move-item|copy-item|rename-item|clear-content)\b"
    # A redirect counts only when it lands on a governed target: `> /tmp/out.txt` is not a mutation
    # of anything GTT governs, whatever the command reads.
    r"|>>?\s*\S*(gtt-domain/|AGENTS\.md|change-request\.md|SOURCE-BRIEF\."
    r"|\.claude/settings(\.local)?\.json|\.claude/hooks/|\.cursor/hooks\.json|\.openhands/hooks\.json"
    r"|\.agents/hooks\.json|gtt_protect\.py|\.git/hooks/|\.kiro/|\.github/hooks/|\.github/instructions/"
    r"|\.gtt/scripts/|\.gtt/contract/|\.gtt/ade\.json|\.claude/skills/|\.claude/rules/|CLAUDE\.md"
    r"|\.cursor/rules/|\.agents/skills/|\.agents/rules/)",
    re.IGNORECASE,
)
TOKEN_SPLIT = re.compile(r"[\s\"'=(<>|;&,`]+")
APPLY_SCRIPT = re.compile(r"(?:^|/)proposals/apply-[^/]+\.sh$", re.IGNORECASE)
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "source", "."}
WRAPPERS = {"env", "sudo", "exec", "time", "nohup", "command", "builtin"}
READ_ONLY_APPLY = {"--check", "--stat", "--numstat", "--summary"}
OBSERVE_DECISIONS = {"accept", "reject", "defer"}

GOVERNED = ("GTT governance (governed paths): AGENTS.md, gtt-domain/context/, gtt-domain/adr/, "
            "gtt-domain/change-request.md, SOURCE-BRIEF.* and the hook configuration that protects them are owned "
            "by the Solution Designer. Write your draft to gtt-domain/proposals/ instead - that directory is yours - "
            "and follow the change process in AGENTS.md.")
FREEZE = ("GTT governance (freeze-semantics): gtt-domain/.frozen is the freeze marker and its history. The human "
          "freezes, by running gtt-freeze.sh, and there is no unfreeze: a governed change is completed by a new "
          "freeze (AGENTS.md -> The two planes).")
LEDGER_OWNED = ("GTT governance (human-decision-authority): gtt-domain/governance-backlog.json is written only by the "
                "observation engine, and the decisions recorded in it are the human's. Refresh it with "
                "`bash .gtt/scripts/gtt-observe.sh observe`; never edit it.")
PROMOTION = ("GTT governance (Human Promotion Boundary): a promotion is run by the human, never by an agent. "
             "Tell the human the command and stop.")
PATCH = ("GTT governance (Human Promotion Boundary): applying a patch staged under gtt-domain/proposals/ is the "
         "human's act. `git apply --check` and `--stat` stay available. Tell the human the command.")
HUMAN_ACT = ("GTT governance (human-decision-authority): freezing, accepting, rejecting or deferring an observation, "
             "and installing or removing the Git hook are the human's decisions (AGENTS.md -> The two planes). Tell "
             "the human the command and continue with the work.")
PLANE = ("GTT governance (instruction-plane): in an installed project the GTT engine (.gtt/scripts/, .gtt/contract/), "
         ".gtt/ade.json and the instructions agents work under are the Solution Designer's - an agent does not rewrite "
         "its own governance. Run the scripts freely; to change one, write a draft under gtt-domain/proposals/ and "
         "tell the human. `gtt-ade.sh update` is how a new Bootstrap version lands.")
BYPASS = ("GTT governance (explicit-blocking): the GTT pre-commit hook is installed in this repository. Skipping it "
          "(--no-verify), redirecting core.hooksPath or removing it is not an agent's call: if the check stops the "
          "commit, fix what it reports or tell the human.")
NO_COMMITS = ("GTT governance (workflow.md: commits: never): this project's gtt-domain/workflow.md says an ADE never "
              "commits, tags or pushes. Git history is the human's: leave the work in the tree and say that it is "
              "uncommitted.")
NO_BRANCHES = ("GTT governance (workflow.md: branches-tags: never): this project's gtt-domain/workflow.md says an ADE "
               "never creates a branch or a tag. Work on the branch the human gave you.")
WORKFLOW_OWNED = ("GTT governance (workflow.md): gtt-domain/workflow.md is the human's - an ADE reads it and never edits "
                  "it. Report the convention you found in one line and say which line the human would add.")
SOURCES_OWNED = ("GTT governance (sources-immutable): docs/sources/ holds the registered design sources, and a source "
                 "is never edited. Register a new version next to the old one: bash .gtt/scripts/gtt-source.sh add "
                 "<file> --id <ID> --apply.")
SOURCE_FROZEN = ("GTT governance (human-decision-authority): after the freeze, registering a source is the human's act. "
                 "Tell the human the command: bash .gtt/scripts/gtt-source.sh add <file> --id <ID> --apply.")
APPROVAL = ("GTT governance (human-decision-authority): approving an Epic and its design is the human's decision. "
            "Tell the human the command - bash .gtt/scripts/gtt-approve.sh EPIC-NNN - and continue with the work.")
LOCAL_OWNED = ("GTT governance (deterministic-first): .gtt/local/checkpoint.json and .gtt/local/last-validation.json are "
               "written only by GTT's own scripts. Run gtt-checkpoint.sh or gtt-validate.sh; never edit their result.")


def normalize(path):
    """Every pattern here is written with forward slashes; every raw input is normalised first."""
    return path.replace("\\", "/")


def relative(token, root):
    """The token as a project-relative path, or None when it is not inside the project."""
    t = normalize(token).strip()
    if not t or t.startswith("-"):
        return None
    # Git-Bash / MSYS drive spelling (/c/foo -> C:/foo), Windows only: on POSIX /x/proj is an
    # ordinary path and rewriting it would resolve it OUTSIDE the project root.
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


def frozen(root):
    return os.path.exists(os.path.join(root, FROZEN_MARKER))


def installed(root):
    return os.path.isfile(os.path.join(root, INSTALLED_MARK))


def in_plane(low, shell):
    """True when the project-relative path is the engine, the ADE state or an instruction file - or,
    for a shell command, a directory that holds one of them."""
    if PLANE_FILES.match(low) or any(under(low, directory) for directory in PLANE_DIRS):
        return True
    return bool(shell and low) and any(directory.startswith(low.rstrip("/") + "/") for directory in PLANE_DIRS)


def git_hook_installed(root):
    """True when the pre-commit hook GTT installs is in place. Nothing about Git is restricted
    otherwise: a bypass can only be denied where there is something to bypass."""
    try:
        with open(os.path.join(root, GIT_HOOK), encoding="utf-8", errors="replace") as handle:
            return GIT_HOOK_MARK in handle.read()
    except OSError:
        return False


def workflow_policy(root):
    """(commits, branches-tags) as the human declared them in gtt-domain/workflow.md. A missing file, block
    or value - or one this engine does not know - is the default, which restricts nothing here."""
    commits, branches = "on-request", "on-request"
    try:
        with open(os.path.join(root, WORKFLOW_FILE), encoding="utf-8", errors="replace") as handle:
            block = re.search(r"```gtt-workflow\r?\n(.*?)```", handle.read(), re.DOTALL)
    except OSError:
        return commits, branches
    for line in (block.group(1).splitlines() if block else []):
        key, _, value = re.sub(r"\s+#.*$", "", line).partition(":")
        if key.strip() == "commits" and value.strip() in ("on-request", "allowed", "never"):
            commits = value.strip()
        elif key.strip() == "branches-tags" and value.strip() in ("on-request", "never"):
            branches = value.strip()
    return commits, branches


def protected_token(root, token, shell=False):
    """Why one path token must not be mutated by an agent, or None. Each token is judged on its
    own: naming a file under gtt-domain/proposals/ never excuses another token of the command."""
    rel = relative(token, root)
    if rel is None:
        return None
    low = rel.lower()
    if low == FROZEN_MARKER:
        return FREEZE
    if low == LEDGER:
        return LEDGER_OWNED
    if low in LOCAL_STATE:
        return LOCAL_OWNED
    if under(low, SOURCES_DIR) or (shell and low == "docs"):
        return SOURCES_OWNED
    if low == WORKFLOW_FILE and installed(root):
        return WORKFLOW_OWNED
    if low == GIT_HOOK:
        return BYPASS if git_hook_installed(root) else None
    if under(rel, PROPOSALS_DIR):
        return None
    if in_plane(low, shell) and installed(root):
        return PLANE
    if any(under(rel, directory) for directory in REGIME_DIRS):
        return GOVERNED if frozen(root) else None
    if shell and low == DOMAIN_DIR:                         # the whole governed domain, in one move
        return FREEZE if frozen(root) else GOVERNED
    if ROOT_FILES.match(rel.rstrip("/")):
        return GOVERNED
    return None


def base(word):
    return normalize(word).rstrip("/").rsplit("/", 1)[-1].lower()


def strip_heredocs(command):
    """The command without the bodies of here-documents that are only data. `python - <<EOF` writes
    nothing this engine can see, whatever its text says; `bash <<EOF` runs every line, so that body
    stays and is read as commands."""
    out, end, keep = [], None, True
    for line in command.replace("\r", "").split("\n"):
        if end is not None:
            if line.strip() == end:
                end = None
            elif keep:
                out.append(line)
            continue
        out.append(line)
        found = HEREDOC.search(line)
        if found:
            end = found.group(1)
            keep = bool(SHELL_READS.search(line))
    return "\n".join(out)


def shell_units(command, depth=0):
    """The simple commands of a shell line, quotes respected: [(words, piped, redirects)], where
    `piped` says the unit reads the previous one through a pipe and `redirects` are the targets of
    its `>` / `>>`. The inner command of `bash -c "..."` / `eval` is unfolded. Leading wrappers
    (env, sudo, VAR=value ...) are dropped."""
    text = strip_heredocs(command).replace("\n", " ; ").replace("`", " ; ").replace("$(", " ( ")
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:                                      # unbalanced quotes: a coarser split still decides
        tokens = [t for t in re.split(r"\s+|([;&|()<>]+)", text.replace('"', " ").replace("'", " ")) if t]
    units, words, redirects, piped, writes = [], [], [], False, False
    for token in tokens + [";"]:
        if token and not token.strip(";&|()<>"):            # an operator
            if ("<" in token or ">" in token) and not set(token) & set(";|()"):
                writes = ">" in token                       # a redirect: its target stays in the unit
                continue
            if words:
                units.append((words, piped, redirects))
            words, redirects, piped, writes = [], [], token in ("|", "|&"), False
            continue
        if writes:
            redirects.append(token)
            writes = False
        words.append(token)
    out = []
    for words, piped, redirects in units:
        while words and (base(words[0]) in WRAPPERS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0])):
            words = words[1:]
            while words and words[0].startswith("-"):       # the wrapper's own options (env -i ...)
                words = words[1:]
        if not words:
            continue
        out.append((words, piped, redirects))
        head = base(words[0])
        if depth < 3 and head in SHELLS | {"eval"}:
            if head == "eval":
                out += shell_units(" ".join(words[1:]), depth + 1)
            for index, word in enumerate(words[1:-1], 1):
                if re.fullmatch(r"-[A-Za-z]*c", word):
                    out += shell_units(words[index + 1], depth + 1)
    return out


def operands(words):
    """The paths one simple command writes, removes or replaces, as far as its own words say."""
    head, rest = base(words[0]), words[1:]
    plain = [w for w in rest if not w.startswith("-")]
    named = [rest[i + 1] for i, w in enumerate(rest[:-1]) if w in ("-o", "--output")]
    named += [w.split("=", 1)[1] for w in rest if w.startswith("--output=")]
    if head == "git":
        sub, args, _ = git_subcommand(words)
        return [a for a in args if not a.startswith("-")] if sub in ("rm", "mv") else []
    if head == "xargs":
        return operands(plain) if plain and base(plain[0]) != "xargs" else []
    if head == "find":
        if "-delete" in rest:
            return plain
        for flag in ("-exec", "-execdir", "-ok"):
            if flag in rest:
                inner = rest[rest.index(flag) + 1:]
                return (plain + operands(inner)) if inner and operands(inner + ["x"]) else []
        return []
    if head == "dd":
        return [w[3:] for w in rest if w.lower().startswith("of=")]
    if head in ("sed", "perl"):
        return plain if any(IN_PLACE.match(w) for w in rest) else named
    if head in COPIES:
        to = [rest[i + 1] for i, w in enumerate(rest[:-1]) if w.lower() in ("-destination", "-t", "--target-directory")]
        return to or plain[-1:]
    if head in MUTATORS:
        return plain
    return named


def write_targets(command):
    targets = []
    for words, _, redirects in shell_units(command):
        targets += redirects + operands(words)
    return targets


def git_subcommand(words):
    """(subcommand, its arguments, the `-c key=value` settings given before it) of a git call."""
    settings, index = [], 1
    while index < len(words):
        word = words[index]
        if word == "-c" and index + 1 < len(words):
            settings.append(words[index + 1])
            index += 2
        elif word in ("-C", "--git-dir", "--work-tree", "--namespace") and index + 1 < len(words):
            index += 2
        elif word.startswith("-"):
            index += 1
        else:
            return word.lower(), words[index + 1:], settings
    return "", [], settings


def decide_units(root, command):
    """Why the shell command is an act an agent does not perform, or None. Reading is never one."""
    chain_reads_apply = False
    hook = policy = None
    for words, piped, _ in shell_units(command):
        head, rest = base(words[0]), words[1:]
        if not piped:
            chain_reads_apply = False
        # --- promotion scripts, in any spelling
        if APPLY_SCRIPT.search(normalize(words[0])):
            return PROMOTION
        syntax_only = head in SHELLS and "-n" in rest and "-c" not in rest      # `bash -n script` reads, never runs
        if head in SHELLS and not syntax_only and (any(APPLY_SCRIPT.search(normalize(w)) for w in rest) or (piped and chain_reads_apply)):
            return PROMOTION
        chain_reads_apply = chain_reads_apply or any(APPLY_SCRIPT.search(normalize(w)) for w in words)
        # --- patches staged under proposals/
        staged = [w for w in rest if (relative(w, root) or "").lower().startswith(PROPOSALS_DIR + "/")]
        if head == "git":
            sub, args, settings = git_subcommand(words)
            if sub in ("apply", "am") and staged and not READ_ONLY_APPLY & set(args):
                return PATCH
            # --- what the human's workflow file forbids
            if sub in ("commit", "push", "tag", "branch", "switch", "checkout"):
                if policy is None:
                    policy = workflow_policy(root)
                plain = [a for a in args if not a.startswith("-")]
                listing = BRANCH_LISTING & set(args)
                makes_tag = sub == "tag" and not listing and bool(plain or {"-d", "--delete"} & set(args))
                makes_branch = ((sub == "branch" and bool(plain) and not listing)
                                or (sub == "switch" and bool({"-c", "-C", "--create", "--force-create"} & set(args)))
                                or (sub == "checkout" and bool({"-b", "-B", "--orphan"} & set(args))))
                if policy[0] == "never" and (sub in ("commit", "push") or makes_tag):
                    return NO_COMMITS
                if policy[1] == "never" and (makes_tag or makes_branch):
                    return NO_BRANCHES
            # --- bypassing the Git hook, only where it is installed
            if hook is None:
                hook = git_hook_installed(root)
            if hook:
                if any(s.lower().startswith("core.hookspath") for s in settings):
                    return BYPASS
                if sub == "commit" and ("--no-verify" in args or any(re.fullmatch(r"-[aesvqpoiz]*n[aesvqpoiz]*", a) for a in args)):
                    return BYPASS
                if sub == "config":
                    keys = [i for i, a in enumerate(args) if a.lower() == "core.hookspath"]
                    reading = {"--get", "--get-all", "--list", "-l"} & set(args)
                    if keys and not reading and (keys[0] < len(args) - 1 or "--unset" in args):
                        return BYPASS
        if head == "patch" and staged and "--dry-run" not in rest:
            return PATCH
        # --- acts that are the human's
        if base(words[0]) == "gtt-freeze.sh" or (head in SHELLS and any(base(w) == "gtt-freeze.sh" for w in rest)):
            return HUMAN_ACT
        if not syntax_only and (base(words[0]) == "gtt-promote.sh" or (head in SHELLS and any(base(w) == "gtt-promote.sh" for w in rest))):
            return PROMOTION
        if not syntax_only and (base(words[0]) == "gtt-approve.sh" or (head in SHELLS and any(base(w) == "gtt-approve.sh" for w in rest))):
            return APPROVAL
        for index, word in enumerate(words):
            follow = words[index + 1:]
            if base(word) == "gtt_flow.py" and follow and follow[0] == "promote":
                return PROMOTION
            if base(word) == "gtt_design.py" and follow and follow[0] == "approve":
                return APPROVAL
            registers = (base(word) == "gtt-source.sh" and follow[:1] and follow[0] in ("add", "adopt")) or \
                        (base(word) == "gtt_design.py" and follow[:2] in (["source", "add"], ["source", "adopt"]))
            if registers and "--apply" in follow and frozen(root):
                return SOURCE_FROZEN
            if base(word) in ("gtt-observe.sh", "gtt_observe.py") and follow and follow[0] in OBSERVE_DECISIONS:
                return HUMAN_ACT
            if base(word) == "gtt-git-hook.sh" and follow and follow[0] in ("install", "remove") and "--apply" in follow:
                return HUMAN_ACT
    return None


def core_shell(root, command):
    """Why a shell command is denied, or None. Reading is never a reason: only what the command
    writes is looked at, so naming a governed file next to a mutation of something else is allowed."""
    reason = decide_units(root, command)
    if reason:
        return reason
    for target in write_targets(command):
        if MACHINERY.search(normalize(target)):
            return GOVERNED
        reason = protected_token(root, target, shell=True)
        if reason:
            return reason
    return None


def blocking_undetermined(root, error):
    """The warning owed when the frozen design declares a BLOCKING boundary and the engine that
    evaluates boundaries cannot run. A broken hook never blocks a session - but it never goes quiet
    about the blocking it can no longer do."""
    try:
        with open(os.path.join(root, STACK_MAP), encoding="utf-8", errors="replace") as handle:
            block = re.search(r"```gtt-boundaries\r?\n(.*?)```", handle.read(), re.DOTALL)
    except OSError:
        return None
    declared = block and any(re.search(r"\|\s*BLOCKING\s*\|", line, re.IGNORECASE)
                             for line in block.group(1).splitlines() if not line.strip().startswith("#"))
    if not declared:
        return None
    return ("GTT WARNING (explicit-blocking): gtt-domain/context/stack.md declares BLOCKING boundaries, but the "
            f"observation engine could not evaluate them ({type(error).__name__}: {error}). This write was NOT checked "
            "against them. Run `bash .gtt/scripts/gtt-observe.sh boundaries` and tell the human.")


def core_boundary(root, rel):
    """(reason, warning) for a write to `rel` against the BLOCKING path boundaries of a frozen
    design. Every other boundary is observed after the fact and never blocks a write."""
    if not rel or not frozen(root):
        return None, None
    here = os.getcwd()
    try:
        scripts = os.path.join(root, ".gtt", "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import gtt_observe
        os.chdir(root)
        hit = gtt_observe.blocking_path(rel)
    except Exception as error:
        return None, blocking_undetermined(root, error)
    finally:
        os.chdir(here)
    if not hit:
        return None, None
    return (f"GTT boundary {hit[0]} (BLOCKING): {rel} is under a boundary the frozen design declares blocking - it "
            f"guards {hit[1]}. This needs a decision: write a proposal under gtt-domain/proposals/ and tell the "
            "human."), None


def core_file(root, path):
    """(reason, warning) for a file-tool write to `path`."""
    target = normalize(path)
    if MACHINERY.search(target):
        return GOVERNED, None
    reason = protected_token(root, target)
    if reason:
        return reason, None
    rel = relative(target, root)
    return core_boundary(root, rel) if rel else (None, None)
# <<< gtt-decision-core <<<


def project_root():
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return normalize(os.path.abspath(root)).rstrip("/")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    return 2


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    root = project_root()
    reason = warning = None

    if tool in ("Write", "Edit", "NotebookEdit"):
        target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if target:
            reason, warning = core_file(root, target)
    elif tool in ("Bash", "PowerShell"):
        reason = core_shell(root, tool_input.get("command", ""))

    if reason:
        return deny(reason)
    if warning:                                             # allowed, and said out loud
        print(warning, file=sys.stderr)
        print(json.dumps({"systemMessage": warning}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                       # a broken hook never blocks a session
        sys.exit(0)
