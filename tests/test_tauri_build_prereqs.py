from __future__ import annotations

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_tauri_build_command_runs_frontend_and_backend_packaging_steps() -> None:
    config = json.loads(read(ROOT / "src-tauri" / "tauri.conf.json"))

    build = config["build"]
    before_build = build["beforeBuildCommand"]
    assert build["frontendDist"] == "../frontend/dist"
    assert "find backend -type d -name __pycache__ -prune -exec rm -rf {} +" in before_build
    assert "npm --prefix frontend run build" in before_build
    assert "python3 -m PyInstaller scripts/backend.spec" in before_build
    assert "--distpath build/backend" in before_build
    assert "--workpath build/pyinstaller-work" in before_build


def test_pyinstaller_backend_spec_uses_backend_server_entrypoint() -> None:
    spec = read(ROOT / "scripts" / "backend.spec")

    assert 'ROOT / "scripts" / "backend_server.py"' in spec
    assert 'name="patentagent-backend"' in spec
    assert 'collect_submodules("backend")' in spec
    assert 'collect_submodules("uvicorn")' in spec
    for package in ["fastapi", "pydantic", "pydantic_settings", "multipart"]:
        assert f'"{package}"' in spec


def test_packaging_extra_contains_pyinstaller() -> None:
    project = tomllib.loads(read(ROOT / "pyproject.toml"))

    packaging = project["project"]["optional-dependencies"]["packaging"]
    assert any(dependency.lower().startswith("pyinstaller") for dependency in packaging)


def test_sqlalchemy_migration_scaffold_is_not_a_runtime_dependency() -> None:
    project = tomllib.loads(read(ROOT / "pyproject.toml"))

    runtime = project["project"]["dependencies"]
    assert not any(dependency.lower().startswith("sqlalchemy") for dependency in runtime)
    assert not any(dependency.lower().startswith("alembic") for dependency in runtime)

    optional = project["project"]["optional-dependencies"]
    for extra in ["dev", "migration"]:
        dependencies = optional[extra]
        assert any(dependency.lower().startswith("sqlalchemy") for dependency in dependencies)
        assert any(dependency.lower().startswith("alembic") for dependency in dependencies)


def test_pyinstaller_excludes_unwired_migration_scaffold() -> None:
    spec = read(ROOT / "scripts" / "backend.spec")

    assert 'if not module.startswith("backend.app.db")' in spec
    assert '"sqlalchemy"' in spec
    assert '"alembic"' in spec


def test_tauri_bundle_inputs_exist_before_packaging() -> None:
    config = json.loads(read(ROOT / "src-tauri" / "tauri.conf.json"))

    for icon in config["bundle"]["icon"]:
        assert (ROOT / "src-tauri" / icon).is_file()
    assert (ROOT / "backend" / "app" / "main.py").is_file()
    assert (ROOT / "scripts" / "backend_server.py").is_file()
    assert (ROOT / "scripts" / "backend.spec").is_file()
