from __future__ import annotations

import os
import shutil
from pathlib import Path


COMMAND_ALIASES: dict[str, tuple[str, ...]] = {
    "kimicode": ("kimicode", "kimi"),
    "mimo": ("mimo", "mimocode"),
}


def agent_bundle_paths() -> list[str]:
    """Return well-known macOS .app bundle resource directories.

    These are directories inside installed applications that may contain
    agent CLI binaries (e.g. Codex.app bundles its ``codex`` binary).
    """
    candidates: list[str] = []
    apps_dir = Path("/Applications")
    if apps_dir.is_dir():
        for app_name in ("Codex.app",):
            bundle_bin = apps_dir / app_name / "Contents" / "Resources"
            if bundle_bin.is_dir():
                candidates.append(str(bundle_bin))
    return candidates


def agent_search_path() -> list[str]:
    """Return the PATH used for desktop-launched agent CLIs.

    macOS Launchpad starts GUI apps with a narrow launchd PATH, so binaries
    installed by Homebrew or per-user agent installers are invisible unless we
    add those locations explicitly.

    Also includes well-known .app bundle resource directories so the agent
    doctor finds bundled CLIs (e.g. Codex.app) even when the usual CLI is
    missing from PATH.
    """
    home = Path.home()
    candidate_dirs = [
        *os.environ.get("PATENTS_AGENT_AGENT_PATH", "").split(os.pathsep),
        *os.environ.get("PATH", "").split(os.pathsep),
        *agent_bundle_paths(),
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


def resolver_source_for_path(path: str) -> str:
    """Identify where a resolved agent path came from.

    Returns one of:
      - ``"bundle"`` — path is inside a known macOS .app bundle directory
      - ``"PATH"``   — path was resolved from a standard search-entry directory
      - ``"custom"`` — path does not match either category
      - ``""``       — path is empty or unresolvable
    """
    if not path:
        return ""
    bundle_dirs = [Path(b) for b in agent_bundle_paths()]
    resolved = Path(path).resolve()
    for bundle_dir in bundle_dirs:
        try:
            resolved.relative_to(bundle_dir)
            return "bundle"
        except ValueError:
            continue
    # Must already be resolve()'d and absolute — ran through agent_search_path
    return "PATH"
