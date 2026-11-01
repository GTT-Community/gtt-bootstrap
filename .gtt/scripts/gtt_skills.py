#!/usr/bin/env python3
"""GTT - skill mirrors: one procedural skill, delivered to every ADE that reads skills.

The source is .gtt/scaffold/skills/<name>/SKILL.md, part of the core every project receives. Each ADE gets a
generated copy in the place it reads, so the procedure never has two authors and a project with any one ADE can
verify its copy:

    Claude    .claude/skills/<name>/SKILL.md     Agent Skills format, a verbatim copy
    Codex     .agents/skills/<name>/SKILL.md     Agent Skills format, a verbatim copy
    Copilot   .github/skills/<name>/SKILL.md     Agent Skills format, a verbatim copy
    Kiro      .kiro/steering/<name>.md           steering file, `inclusion: auto` with the skill's name and description

  gtt_skills.py sync [--apply]   rewrite the mirrors from the source (dry run without --apply)
  gtt_skills.py check            the mirror of every participating ADE exists and says what the source says
                                 (part of gtt-validate.sh); the mirror of an ADE that is not there is not required

A mirror is a derived file, like the index: never hand-edited. `check` fails when one has drifted from its source.
Exit 0 = ok, 1 = drift or missing mirror, 2 = cannot run.
"""

import os
import re
import sys

sys.dont_write_bytecode = True

SKILLS = ("gtt-delivery",)
SOURCE = ".gtt/scaffold/skills/{name}/SKILL.md"
TARGETS = {
    "claude": ".claude/skills/{name}/SKILL.md",
    "codex": ".agents/skills/{name}/SKILL.md",
    "copilot": ".github/skills/{name}/SKILL.md",
    "kiro": ".kiro/steering/{name}.md",
}


def read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().replace("\r\n", "\n")
    except OSError:
        return None


def split(text):
    """(front matter dict, body) of an Agent Skills file."""
    found = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not found:
        return {}, text
    meta = {}
    for line in found.group(1).split("\n"):
        key, _, value = line.partition(":")
        if value:
            meta[key.strip()] = value.strip()
    return meta, found.group(2)


def render(ade, name, text):
    """The mirror of one source for one ADE."""
    meta, body = split(text)
    if ade == "kiro":
        return f"---\ninclusion: auto\nname: {meta.get('name', name)}\ndescription: {meta.get('description', '')}\n---\n{body}"
    return text


def participating():
    """The ADEs whose mirror is required: those of .gtt/ade.json, or every ADE where the project has none (the catalog)."""
    import json
    try:
        with open(".gtt/ade.json", encoding="utf-8") as handle:
            return set(json.load(handle).get("participating") or [])
    except (OSError, ValueError):
        return set(TARGETS)


def check():
    problems = []
    required = participating()
    for name in SKILLS:
        source = read(SOURCE.format(name=name))
        if source is None:
            problems.append(f"{SOURCE.format(name=name)} is missing")
            continue
        meta, _ = split(source)
        if meta.get("name") != name or not meta.get("description"):
            problems.append(f"{SOURCE.format(name=name)}: front matter needs `name: {name}` and a `description`")
        if re.search(r": | #", meta.get("description", "")) and not meta.get("description", "")[:1] in "\"'":
            problems.append(f"{SOURCE.format(name=name)}: the description has `: ` or ` #`, which breaks the YAML front matter every ADE parses; reword it")
        for ade, pattern in TARGETS.items():
            path = pattern.format(name=name)
            have = read(path)
            if have is None and ade not in required:
                continue
            if have is None:
                problems.append(f"{ade}: {path} is missing (run: bash .gtt/scripts/gtt-skills.sh sync --apply)")
            elif have != render(ade, name, source):
                problems.append(f"{ade}: {path} differs from {SOURCE.format(name=name)} (run: bash .gtt/scripts/gtt-skills.sh sync --apply)")
    return problems


def sync(apply):
    changed = 0
    for name in SKILLS:
        source = read(SOURCE.format(name=name))
        if source is None:
            print(f"gtt-skills: {SOURCE.format(name=name)} is missing", file=sys.stderr)
            return 2
        for ade, pattern in TARGETS.items():
            path, want = pattern.format(name=name), render(ade, name, source)
            if read(path) == want:
                continue
            if read(path) is None and ade not in participating():
                continue
            changed += 1
            print(f"  {'WRITE' if apply else 'WOULD WRITE'}  {ade:8} {path}")
            if apply:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(want)
    print(f"gtt-skills: {changed} mirror(s) " + ("written." if apply else "out of date (dry run - re-run with --apply)."))
    return 0


def main(argv):
    if not os.path.isdir(".gtt"):
        print("gtt-skills: run from the project root (no .gtt/ directory here)", file=sys.stderr)
        return 2
    if len(argv) >= 2 and argv[1] == "sync":
        return sync("--apply" in argv)
    if len(argv) >= 2 and argv[1] == "check":
        problems = check()
        for problem in problems:
            print(f"FAIL  {problem}", file=sys.stderr)
        if not problems:
            print(f"gtt-skills: OK - {len(SKILLS)} skill(s) mirrored for {', '.join(TARGETS)}.")
        return 1 if problems else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
