#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


def collect_preflight(cwd: Path | str = ".") -> dict[str, Any]:
    cwd_path = Path(cwd).resolve()
    top_level = _git(["rev-parse", "--show-toplevel"], cwd_path)
    repo_root = Path(top_level).resolve()
    status_short = _git(["status", "--short", "--branch"], repo_root)
    unmerged_files = [line for line in _git(["diff", "--name-only", "--diff-filter=U"], repo_root).splitlines() if line]
    dirty_entries = [line for line in status_short.splitlines() if line and not line.startswith("## ")]
    return {
        "worktree_path": str(cwd_path),
        "git_toplevel": str(repo_root),
        "branch": _git(["branch", "--show-current"], repo_root),
        "short_sha": _git(["rev-parse", "--short", "HEAD"], repo_root),
        "dirty": bool(dirty_entries),
        "dirty_entries": dirty_entries,
        "unmerged_files": unmerged_files,
        "versions": _read_versions(repo_root),
        "status_short": status_short,
    }


def determine_exit_code(report: dict[str, Any]) -> int:
    return 2 if report.get("unmerged_files") else 0


def format_text(report: dict[str, Any]) -> str:
    lines = [
        "QA preflight source identity",
        f"worktree_path: {report['worktree_path']}",
        f"git_toplevel: {report['git_toplevel']}",
        f"branch: {report['branch'] or '(detached)'}",
        f"short_sha: {report['short_sha']}",
        f"dirty: {'yes' if report['dirty'] else 'no'}",
    ]
    if report["dirty_entries"]:
        lines.append("dirty_entries:")
        lines.extend(f"  {entry}" for entry in report["dirty_entries"])
    if report["unmerged_files"]:
        lines.append("unmerged_files:")
        lines.extend(f"  {path}" for path in report["unmerged_files"])
    lines.append("versions:")
    for key, value in report["versions"].items():
        lines.append(f"  {key}: {value or 'unknown'}")
    mismatches = _version_mismatches(report["versions"])
    lines.append(f"version_mismatches: {', '.join(mismatches) if mismatches else 'none'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print QA source identity and release-version preflight details.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--cwd", default=".", help="Repository path to inspect.")
    args = parser.parse_args(argv)

    try:
        report = collect_preflight(args.cwd)
    except RuntimeError as exc:
        print(f"qa_preflight failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_text(report))
    return determine_exit_code(report)


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout.strip()


def _read_versions(repo_root: Path) -> dict[str, str | None]:
    return {
        "pyproject": _read_pyproject_version(repo_root / "pyproject.toml"),
        "frontend_package": _read_json_key(repo_root / "frontend" / "package.json", "version"),
        "tauri": _read_json_key(repo_root / "src-tauri" / "tauri.conf.json", "version"),
        "frontend_name": _read_json_key(repo_root / "frontend" / "package.json", "name"),
        "tauri_product": _read_json_key(repo_root / "src-tauri" / "tauri.conf.json", "productName"),
        "tauri_identifier": _read_json_key(repo_root / "src-tauri" / "tauri.conf.json", "identifier"),
    }


def _read_pyproject_version(path: Path) -> str | None:
    if not path.exists():
        return None
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    version = project.get("version")
    return str(version) if version is not None else None


def _read_json_key(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get(key)
    return str(value) if value is not None else None


def _version_mismatches(versions: dict[str, str | None]) -> list[str]:
    release_versions = {
        name: value
        for name, value in versions.items()
        if name in {"pyproject", "frontend_package", "tauri"} and value
    }
    if len(set(release_versions.values())) <= 1:
        return []
    return [f"{name}={value}" for name, value in release_versions.items()]


if __name__ == "__main__":
    raise SystemExit(main())
