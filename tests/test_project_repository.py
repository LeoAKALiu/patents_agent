"""PR-5: Project repository - unit tests.

Verify that ``ProjectRepository`` delegates correctly to ``SQLiteStore`` and
that the service layer can operate through the repository interface.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.repositories.projects import ProjectRepository
from backend.app.schemas import (
    PatentPointCreate,
    PatentType,
    ProjectCreate,
    ProjectRecord,
    ProjectUpdate,
)
from backend.app.services.project_service import (
    apply_project_update,
    build_patent_point_candidate,
    build_project_record,
    import_project_material,
)
from backend.app.storage import SQLiteStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path) -> ProjectRepository:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    return ProjectRepository(store)


def _make_project_record(name: str = "测试项目") -> ProjectRecord:
    return build_project_record(
        ProjectCreate(
            name=name,
            draft_text="一种测试方法。",
            patent_type=PatentType.INVENTION,
        )
    )


# ---------------------------------------------------------------------------
# Repository CRUD
# ---------------------------------------------------------------------------


def test_list_projects_empty_initially(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert repo.list_all() == []


def test_create_and_get_by_id(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    project = _make_project_record()
    created = repo.create(project)
    assert created.id == project.id
    assert created.name == project.name

    fetched = repo.get_by_id(project.id)
    assert fetched is not None
    assert fetched.id == project.id
    assert fetched.name == project.name


def test_get_by_id_not_found_returns_none(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert repo.get_by_id("nonexistent") is None


def test_update_project(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    project = _make_project_record("原始名称")
    repo.create(project)

    repo.update(project.id, {"name": "更新名称"})
    fetched = repo.get_by_id(project.id)
    assert fetched is not None
    assert fetched.name == "更新名称"


def test_delete_project(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    project = _make_project_record()
    repo.create(project)

    assert repo.get_by_id(project.id) is not None
    deleted = repo.delete(project.id)
    assert deleted is True
    assert repo.get_by_id(project.id) is None


def test_delete_project_not_found(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert repo.delete("nonexistent") is False


# ---------------------------------------------------------------------------
# Materials through repository
# ---------------------------------------------------------------------------


def test_add_and_list_materials(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    project = _make_project_record()
    repo.create(project)

    material_text = "Hello world"
    stored_path = tmp_path / "materials" / "test.txt"
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    stored_path.write_text(material_text, encoding="utf-8")

    material = import_project_material(
        project_id=project.id,
        file_name="test.txt",
        stored_path=stored_path,
        repo=repo,
    )
    assert material.project_id == project.id
    assert material.file_name == "test.txt"

    materials = repo.list_materials(project.id)
    assert len(materials) == 1
    assert materials[0].file_name == "test.txt"


# ---------------------------------------------------------------------------
# Patent points through repository
# ---------------------------------------------------------------------------


def test_add_and_list_patent_points(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    project = _make_project_record()
    repo.create(project)

    point = build_patent_point_candidate(
        PatentPointCreate(
            title="一种检测方法",
            technical_problem="提高检测精度",
            innovation="动态阈值",
            technical_solution="深度学习",
        )
    )
    stored = repo.add_patent_point(project.id, point)
    assert stored.title == "一种检测方法"

    points = repo.list_patent_points(project.id)
    assert len(points) == 1
    assert points[0].id == stored.id


def test_get_and_delete_patent_point(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    project = _make_project_record()
    repo.create(project)

    point = build_patent_point_candidate(
        PatentPointCreate(
            title="待删除点",
            technical_problem="问题",
            innovation="创新",
            technical_solution="方案",
        )
    )
    stored = repo.add_patent_point(project.id, point)

    fetched = repo.get_patent_point(project.id, stored.id)
    assert fetched is not None
    assert fetched.id == stored.id

    deleted = repo.delete_patent_point(project.id, stored.id)
    assert deleted is True
    assert repo.get_patent_point(project.id, stored.id) is None


def test_patent_point_not_found(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    project = _make_project_record()
    repo.create(project)

    assert repo.get_patent_point(project.id, "nonexistent") is None
    assert repo.delete_patent_point(project.id, "nonexistent") is False


# ---------------------------------------------------------------------------
# Service layer with repository
# ---------------------------------------------------------------------------


def test_apply_project_update_with_repo(tmp_path: Path) -> None:
    """Verify apply_project_update works when given a ProjectRepository."""
    repo = _make_repo(tmp_path)
    project = _make_project_record("原始名称")
    repo.create(project)

    updated = apply_project_update(
        project.id,
        ProjectUpdate(name="更新名称"),
        repo,
    )
    assert updated is not None
    assert updated.name == "更新名称"


def test_apply_project_update_empty_payload(tmp_path: Path) -> None:
    """An empty update payload returns the existing project unchanged."""
    repo = _make_repo(tmp_path)
    project = _make_project_record()
    repo.create(project)

    updated = apply_project_update(project.id, ProjectUpdate(), repo)
    assert updated is not None
    assert updated.id == project.id


# ---------------------------------------------------------------------------
# Circular import safety
# ---------------------------------------------------------------------------


def test_repository_does_not_import_main() -> None:
    """ProjectRepository must never import backend.app.main."""
    import ast

    repo_path = (
        Path(__file__).resolve().parents[1]
        / "backend" / "app" / "repositories" / "projects.py"
    )
    tree = ast.parse(repo_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "backend.app.main" in module:
                assert False, "projects.py (repository) imports backend.app.main (circular)"


def test_service_imports_repo_not_store() -> None:
    """project_service.py now uses ProjectRepository, not SQLiteStore directly."""
    import ast

    svc_path = (
        Path(__file__).resolve().parents[1]
        / "backend" / "app" / "services" / "project_service.py"
    )
    tree = ast.parse(svc_path.read_text(encoding="utf-8"))
    repo_imported = False
    store_imported = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "backend.app.repositories" in module:
                repo_imported = True
            if "backend.app.storage" in module:
                store_imported = True
    # project_service should NOT import storage directly
    assert not store_imported, "project_service.py directly imports storage (use repository instead)"
    # Note: project_service.py doesn't need to import ProjectRepository itself
    # because it receives it as a parameter. But it should not import storage.
