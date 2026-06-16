from __future__ import annotations

import os
import shutil
from pathlib import Path


COMMAND_ALIASES: dict[str, tuple[str, ...]] = {
    "kimicode": ("kimicode", "kimi"),
}


def agent_search_path() -> list[str]:
    """Return the PATH used for desktop-launched agent CLIs.

    macOS Launchpad starts GUI apps with a narrow launchd PATH, so binaries
    installed by Homebrew or per-user agent installers are invisible unless we
    add those locations explicitly.
    """
    home = Path.home()
    candidate_dirs = [
        *os.environ.get("PATENTS_AGENT_AGENT_PATH", "").split(os.pathsep),
        *os.environ.get("PATH", "").split(os.pathsep),
        str(home / ".local" / "bin"),
        str(home / ".kimi-code" / "bin"),
        str(home / ".mimocode" / "bin"),
        str(home / ".cargo" / "bin"),
        str(home / "Library" / "Python" / "3.12" / "bin"),
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]
    seen: set[str] = set()
    paths: list[str] = []
    for raw_path in candidate_dirs:
        if not raw_path:
            continue
        path = str(Path(raw_path).expanduser())
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def agent_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(agent_search_path())
    return env


def resolve_agent_command(command: str) -> str | None:
    if not command:
        return None
    command_path = Path(command).expanduser()
    if command_path.is_absolute() or os.sep in command:
        return str(command_path) if command_path.is_file() and os.access(command_path, os.X_OK) else None

    search_path = os.pathsep.join(agent_search_path())
    for candidate in COMMAND_ALIASES.get(command, (command,)):
        resolved = shutil.which(candidate, path=search_path)
        if resolved:
            return resolved
    return None
