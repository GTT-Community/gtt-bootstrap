#!/usr/bin/env python3
"""The bash that runs GTT Bootstrap scripts.

On Windows a process started by name is looked up in the system directory
before the PATH, and that directory holds the WSL launcher (bash.exe): it
starts a Linux distribution, which cannot run a script by its Windows path.
Every Bootstrap script that starts bash asks here which one to start.

DATA-FREE HELPER. It decides nothing about GTT; it only names an executable.
"""
import os
import shutil
import sys


def _is_wsl_launcher(path):
    p = path.lower().replace("\\", "/")
    return p.endswith("/windows/system32/bash.exe") or p.endswith("/windows/sysnative/bash.exe") \
        or "/microsoft/windowsapps/" in p


def bash_executable():
    """Return the bash to run; never the WSL launcher on Windows.

    GTT_BASH wins when it names a file: a CLI that already resolved bash
    passes it, so both sides run the same one.
    """
    explicit = os.environ.get("GTT_BASH")
    if explicit and os.path.isfile(explicit):
        return explicit
    if sys.platform != "win32":
        return "bash"
    found = shutil.which("bash")  # follows the PATH order, unlike process creation
    if found and not _is_wsl_launcher(found):
        return found
    bases = [os.environ.get(name) for name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")]
    candidates = [os.path.join(base, "Git", "bin", "bash.exe") for base in bases if base]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(os.path.join(local, "Programs", "Git", "bin", "bash.exe"))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return "bash"
