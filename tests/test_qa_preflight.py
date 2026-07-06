from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


def _load_qa_preflight():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "qa_preflight.py"
    spec = importlib.util.spec_from_file_location("qa_preflight", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qa_preflight = _load_qa_preflight()


def test_collect_preflight_reports_source_identity_and_release_versions(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "frontend").mkdir()
    (repo / "src-tauri").mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname = "patents-agent"\nversion = "1.2.3"\n', encoding="utf-8")
    (repo / "frontend" / "package.json").write_text(
        '{"name":"grantatlas-frontend","version":"1.2.3"}',
        encoding="utf-8",
    )
    (repo / "src-tauri" / "tauri.conf.json").write_text(
        '{"productName":"GrantAtlas","version":"1.2.3","identifier":"xin.liubo.patentagent"}',
        encoding="utf-8",
    )
    _git(repo, "init")
    _git(repo, "add", ".")
    _git(repo, "-c", "user.name=QA", "-c", "user.email=qa@example.test", "commit", "-m", "init")

    report = qa_preflight.collect_preflight(repo)

    assert report["git_toplevel"] == str(repo.resolve())
    assert report["branch"]
    assert report["short_sha"]
    assert report["dirty"] is False
    assert report["unmerged_files"] == []
    assert report["versions"]["pyproject"] == "1.2.3"
    assert report["versions"]["frontend_package"] == "1.2.3"
    assert report["versions"]["tauri"] == "1.2.3"
    assert "version_mismatches: none" in qa_preflight.format_text(report)


def test_preflight_exit_code_blocks_unmerged_files():
    clean_report = {"unmerged_files": []}
    conflicted_report = {"unmerged_files": ["frontend/src/App.tsx"]}

    assert qa_preflight.determine_exit_code(clean_report) == 0
    assert qa_preflight.determine_exit_code(conflicted_report) == 2


def test_preflight_text_surfaces_version_mismatches():
    report = {
        "worktree_path": "/repo",
        "git_toplevel": "/repo",
        "branch": "main",
        "short_sha": "abc1234",
        "dirty": True,
        "dirty_entries": [" M frontend/package.json"],
        "unmerged_files": [],
        "versions": {
            "pyproject": "1.1.0",
            "frontend_package": "1.1.1",
            "tauri": "1.1.0",
            "frontend_name": "grantatlas-frontend",
            "tauri_product": "GrantAtlas",
            "tauri_identifier": "xin.liubo.patentagent",
        },
    }

    text = qa_preflight.format_text(report)

    assert "dirty: yes" in text
    assert "frontend_package=1.1.1" in text


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
