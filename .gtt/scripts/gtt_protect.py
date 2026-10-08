#!/usr/bin/env python3
"""GTT - ADE-neutral write protection and session context for hook-capable ADEs.

One decision engine, thin per-ADE formats. An ADE whose hooks can stop a tool call before it runs
points its hook at this script; the script reads the ADE's event on stdin, decides, and answers in
that ADE's own shape.

What is decided lives in the decision core below, which is byte-identical to the one in Claude
Code's own hook (.claude/hooks/protect-l0.py): governed paths, machinery, the freeze marker, the
governance ledger, promotion scripts and staged patches, the acts that are the human's, bypassing
the Git hook, and the path boundaries the frozen design declares BLOCKING. On top of it this
engine adds GTTGuard (a protected file or symbol, span resolved live; an edit whose extent is
unknown fails safe to the whole file), which Claude Code gets from its own protect-guard.py.

Everything else is ordinary work and passes untouched: this engine blocks only where the governed
state says so, and every denial names the rule it comes from.

  gtt_protect.py hook --format antigravity|copilot|cursor|kiro|openhands
                                                    decide a pre-tool event
  gtt_protect.py decide --file PATH | --shell CMD   the bare decision, for tests and for a human

A denial exits 2 with the ADE's deny payload - except for GitHub Copilot, whose pre-tool hook fails
closed: there a denial is its JSON decision with exit 0, and this script never exits non-zero.
Anything this script does not understand - an unknown event, an unreadable payload, an unexpected
error - exits 0: a broken hook never blocks a session, and an unexpected error says on stderr that
the call was not checked.
The one thing it does not do quietly is lose a BLOCKING boundary: if the frozen design declares one
and the observation engine cannot be loaded, the write is allowed and a warning says so on stderr.
Shipped for Cursor, OpenHands, Antigravity, Kiro and GitHub Copilot from their documented hook
contracts; NOT verified inside any of them. The CI gate (gtt-check-protection.sh, gtt-check-stack.sh) remains the
guaranteed layer.
"""

import argparse
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

REGISTRY = ".gtt/protection/registry.yaml"
PROPOSE = "Draft a proposal (AGENTS.md -> Protected artifacts) instead of editing it directly."

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


def warn(message):
    if message:
        print(message, file=sys.stderr)


def decide_file(root, path, old_string=None):
    reason, warning = core_file(root, path)
    warn(warning)
    if reason:
        return reason
    rel = relative(path, root)
    return guard_file(root, rel, old_string) if rel else None


def decide_shell(root, command):
    reason = core_shell(root, command)
    if reason or not MUTATING_SHELL.search(normalize(command)):
        return reason
    _, entries = guard_entries(root)
    for entry in entries:
        if normalize(entry["artifact"]) in normalize(command):
            return (f"GTTGuard: {entry['artifact']} is a protected artifact. Shell commands that could mutate a "
                    f"protected file are always blocked. {PROPOSE}")
    return None


PATH_KEYS = ("file_path", "path", "target_file", "filePath", "notebook_path")


def first_path(tool_input):
    for key in PATH_KEYS:
        if isinstance(tool_input.get(key), str) and tool_input[key]:
            return tool_input[key]
    return None


def cursor(event):
    """Cursor: .cursor/hooks.json -> preToolUse / beforeShellExecution. Session start is not decided here:
    it is the session adapter's (.gtt/scripts/gtt_session_hook.py), under the Session Memory contract."""
    roots = event.get("workspace_roots") or []
    root = normalize(os.path.abspath(roots[0] if roots else event.get("cwd") or os.getcwd())).rstrip("/")
    name = event.get("hook_event_name", "")
    tool_input = event.get("tool_input") or {}
    reason = None
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
    """OpenHands: .openhands/hooks.json -> pre_tool_use. Session start is the session adapter's."""
    root = normalize(os.path.abspath(os.environ.get("OPENHANDS_PROJECT_DIR") or event.get("working_dir") or os.getcwd())).rstrip("/")
    name = event.get("event_type") or os.environ.get("OPENHANDS_EVENT_TYPE", "")
    tool_input = event.get("tool_input") or {}
    reason = None
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


ANTIGRAVITY_WRITES = ("write_to_file", "replace_file_content", "multi_replace_file_content")


def antigravity(event):
    """Antigravity: .agents/hooks.json -> PreToolUse. Its payload names no event, so a pre-tool call is
    the one that carries `toolCall`. It has no session-start event: no session context is injected here."""
    call = event.get("toolCall")
    args = call.get("args") if isinstance(call, dict) else None
    if not isinstance(args, dict):
        return 0, None
    roots = event.get("workspacePaths") or []
    root = normalize(os.path.abspath(roots[0] if roots else os.getcwd())).rstrip("/")
    tool, path = call.get("name", ""), args.get("TargetFile")
    reason = None
    if tool == "run_command":
        reason = decide_shell(root, args.get("CommandLine", ""))
    elif tool in ANTIGRAVITY_WRITES and isinstance(path, str) and path:
        extents = [None]                                    # extent unknown: GTTGuard fails safe to the whole file
        if tool == "replace_file_content":
            extents = [args.get("TargetContent")]
        elif tool == "multi_replace_file_content":
            chunks = args.get("ReplacementChunks")
            if isinstance(chunks, list) and chunks:
                extents = [c.get("TargetContent") if isinstance(c, dict) else None for c in chunks]
        for old in extents:
            reason = decide_file(root, path, old if isinstance(old, str) else None)
            if reason:
                break
    if reason:
        return 2, {"decision": "deny", "reason": reason}
    return 0, None


def project_root(*candidates):
    """The project a hook was called for: the first candidate that is, or is inside, a directory with
    a GTT engine. An ADE that starts its hooks somewhere below the root is still resolved to it."""
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate:
            continue
        here = os.path.abspath(candidate)
        while True:
            if os.path.isdir(os.path.join(here, ".gtt", "scripts")):
                return normalize(here).rstrip("/")
            parent = os.path.dirname(here)
            if parent == here:
                break
            here = parent
    return normalize(os.path.abspath(os.getcwd())).rstrip("/")


def first_of(event, *keys):
    for key in keys:
        if event.get(key) not in (None, ""):
            return event[key]
    return None


KIRO_WRITES = re.compile(r"write|edit|create|replace|delete|remove|append|patch", re.IGNORECASE)


def kiro(event):
    """Kiro: .kiro/hooks/gtt-protect.json (hook schema v1) -> PreToolUse.

    Documented (https://kiro.dev/docs/ide/whats-new-v1/hooks/ and https://kiro.dev/docs/hooks/actions/,
    read 2026-10-07): a command action runs in the project root with the session context as JSON on
    stdin; exit 2 blocks the tool call and stderr goes to the agent; on exit 0 stdout is added to the
    agent's context, so an allow prints nothing. A file tool carries `path`, a shell tool `command`.
    NOT documented there: the field names of the JSON around them, and the tool names. So this reads
    the names the other ADEs use, takes a tool for a file write only when its name says so, and lets
    through whatever it does not recognise - a read of a governed file is never denied by a guess."""
    root = project_root(os.getcwd(), event.get("cwd"))
    tool = first_of(event, "tool_name", "toolName", "tool")
    tool_input = first_of(event, "tool_input", "toolInput", "input", "arguments", "args")
    if not isinstance(tool_input, dict):
        return 0, None
    path, command = first_path(tool_input), tool_input.get("command")
    reason = None
    if path:
        if isinstance(tool, str) and KIRO_WRITES.search(tool):
            reason = decide_file(root, path, tool_input.get("old_str") or tool_input.get("old_string"))
    elif isinstance(command, str) and command:
        reason = decide_shell(root, command)
    return (2, reason) if reason else (0, None)             # a string goes to stderr: Kiro hands it to the agent


COPILOT_SHELLS = ("bash", "powershell")
COPILOT_WRITES = ("create", "edit")


def copilot(event):
    """GitHub Copilot: .github/hooks/gtt-protect.json -> preToolUse (cloud agent and CLI).

    Documented (https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-hooks-reference,
    read 2026-10-07): stdin carries sessionId, timestamp, cwd, toolName and toolArgs; the tools are
    bash, powershell, create, edit and view; a denial is {"permissionDecision": "deny",
    "permissionDecisionReason": ...} on stdout. preToolUse fails CLOSED: a crash, or an exit other than
    0, denies the call. So this format never exits non-zero - a denial is that JSON with exit 0, and
    only a decision of the core is ever a denial. NOT documented there: the fields inside toolArgs.
    This reads `command` and the path names the other ADEs use; a tool that carries neither
    (apply_patch) is not seen here and stays with the CI gate."""
    root = project_root(event.get("cwd"), os.getcwd())
    tool, tool_args = event.get("toolName"), event.get("toolArgs")
    if isinstance(tool_args, str):
        try:
            tool_args = json.loads(tool_args)
        except ValueError:
            return 0, None
    if not isinstance(tool, str) or not isinstance(tool_args, dict):
        return 0, None
    reason = None
    if tool in COPILOT_SHELLS:
        command = tool_args.get("command")
        reason = decide_shell(root, command) if isinstance(command, str) and command else None
    elif tool in COPILOT_WRITES:
        path = first_path(tool_args)
        reason = decide_file(root, path, tool_args.get("old_str") or tool_args.get("old_string")) if path else None
    if reason:
        return 0, {"permissionDecision": "deny", "permissionDecisionReason": reason}
    return 0, None


FORMATS = {"antigravity": antigravity, "copilot": copilot, "cursor": cursor, "kiro": kiro, "openhands": openhands}


def cmd_hook(args):
    try:
        event = json.load(sys.stdin)
        code, payload = FORMATS[args.format](event if isinstance(event, dict) else {})
    except ValueError:
        return 0                                            # not an event this script can read
    except Exception as error:
        # A broken hook never blocks a session - and never says nothing about it either.
        print(f"GTT WARNING: the {args.format} hook could not evaluate this call ({type(error).__name__}: {error}). "
              "It was NOT checked; the CI gate is the layer that holds.", file=sys.stderr)
        return 0
    if isinstance(payload, str):
        print(payload, file=sys.stderr)
    elif payload is not None:
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
