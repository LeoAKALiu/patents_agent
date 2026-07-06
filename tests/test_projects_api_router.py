"""PR-2: Projects API router - integration tests.

Verify that project CRUD, materials, and patent-point endpoints work
through the router layer after moving from ``backend/app/main.py``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


def _make_client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=FakeLLMClient({"claims": "1. 一种方法。"}),
            load_env_file=False,
        )
    )


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------


def test_list_projects_empty_initially(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json()["projects"] == []


def test_create_and_get_project(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    payload = {
        "name": "测试专利",
        "draft_text": "一种基于深度学习的检测方法。",
        "patent_type": "invention",
    }
    create_resp = client.post("/api/projects", json=payload)
    assert create_resp.status_code == 200
    project_id = create_resp.json()["id"]
    assert create_resp.json()["name"] == "测试专利"

    get_resp = client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id


def test_get_project_not_found(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    response = client.get("/api/projects/nonexistent")
    assert response.status_code == 404


def test_update_project(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "原始名称", "draft_text": "原始文本。"},
    )
    project_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/projects/{project_id}",
        json={"name": "更新名称"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "更新名称"
    # Unchanged fields preserved
    assert update_resp.json()["draft_text"] == "原始文本。"


def test_delete_project(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "待删除", "draft_text": "将被删除。"},
    )
    project_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/projects/{project_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["ok"] is True

    # Verify gone
    get_resp = client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 404


def test_delete_project_not_found(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    response = client.delete("/api/projects/nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Project materials
# ---------------------------------------------------------------------------


def test_list_materials_empty_initially(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "项目", "draft_text": "材料测试。"},
    )
    pid = create_resp.json()["id"]
    response = client.get(f"/api/projects/{pid}/materials")
    assert response.status_code == 200
    assert response.json()["materials"] == []


def test_upload_and_list_material(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "项目", "draft_text": "材料上传测试。"},
    )
    pid = create_resp.json()["id"]

    upload_resp = client.post(
        f"/api/projects/{pid}/materials",
        files={"file": ("readme.txt", b"Hello world", "text/plain")},
    )
    assert upload_resp.status_code == 200
    material = upload_resp.json()
    assert material["file_name"] == "readme.txt"
    assert material["project_id"] == pid

    list_resp = client.get(f"/api/projects/{pid}/materials")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["materials"]) == 1


def test_upload_material_rejects_overlong_filename_without_persisting(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "项目", "draft_text": "材料上传边界测试。"},
    )
    pid = create_resp.json()["id"]
    filename = f"{'a' * 260}.md"

    upload_resp = client.post(
        f"/api/projects/{pid}/materials",
        files={"file": (filename, b"valid markdown material", "text/markdown")},
    )

    assert upload_resp.status_code == 422
    assert upload_resp.json()["detail"] == "材料文件名过长，请缩短文件名后重新上传。"
    list_resp = client.get(f"/api/projects/{pid}/materials")
    assert list_resp.status_code == 200
    assert list_resp.json()["materials"] == []
    material_dir = tmp_path / "project-materials" / pid
    assert not material_dir.exists() or list(material_dir.iterdir()) == []


def test_material_endpoints_require_project(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    response = client.get("/api/projects/nonexistent/materials")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Patent points
# ---------------------------------------------------------------------------


def test_list_patent_points_empty_initially(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "项目", "draft_text": "点测试。"},
    )
    pid = create_resp.json()["id"]
    response = client.get(f"/api/projects/{pid}/patent-points")
    assert response.status_code == 200
    assert response.json()["points"] == []


def test_create_and_get_patent_point(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "项目", "draft_text": "点测试。"},
    )
    pid = create_resp.json()["id"]

    point_payload = {
        "title": "一种检测方法",
        "technical_problem": "提高检测精度",
        "innovation": "动态阈值筛选异常样本",
        "technical_solution": "使用深度学习",
        "beneficial_effects": ["提高检测精度"],
    }
    point_resp = client.post(f"/api/projects/{pid}/patent-points", json=point_payload)
    assert point_resp.status_code == 200
    point = point_resp.json()
    assert point["title"] == "一种检测方法"
    assert point["id"]

    list_resp = client.get(f"/api/projects/{pid}/patent-points")
    assert list_resp.status_code == 200
    points = list_resp.json()["points"]
    assert len(points) == 1
    assert points[0]["id"] == point["id"]


def test_update_patent_point(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "项目", "draft_text": "点更新测试。"},
    )
    pid = create_resp.json()["id"]

    point = client.post(
        f"/api/projects/{pid}/patent-points",
        json={
            "title": "原始点",
            "technical_problem": "提高精度",
            "innovation": "多尺度融合",
            "technical_solution": "深度方案",
        },
    ).json()

    update_resp = client.patch(
        f"/api/projects/{pid}/patent-points/{point['id']}",
        json={"title": "更新点"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "更新点"


def test_delete_patent_point(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "项目", "draft_text": "点删除测试。"},
    )
    pid = create_resp.json()["id"]

    point = client.post(
        f"/api/projects/{pid}/patent-points",
        json={
            "title": "待删除",
            "technical_problem": "提高精度",
            "innovation": "局部特征增强",
            "technical_solution": "方案",
        },
    ).json()

    delete_resp = client.delete(
        f"/api/projects/{pid}/patent-points/{point['id']}"
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["ok"] is True

    list_resp = client.get(f"/api/projects/{pid}/patent-points")
    assert len(list_resp.json()["points"]) == 0


def test_patent_point_not_found(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    create_resp = client.post(
        "/api/projects",
        json={"name": "项目", "draft_text": "不存在点测试。"},
    )
    pid = create_resp.json()["id"]

    response = client.get(f"/api/projects/{pid}/patent-points/nonexistent-id")
    # The individual point endpoints don't have specific GET by ID; test PATCH
    response = client.patch(
        f"/api/projects/{pid}/patent-points/nonexistent",
        json={"title": "should fail"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# No circular imports
# ---------------------------------------------------------------------------


def test_projects_router_does_not_import_main() -> None:
    """Projects router must never import backend.app.main."""
    import ast
    from pathlib import Path

    router_path = (
        Path(__file__).resolve().parents[1]
        / "backend" / "app" / "api" / "projects.py"
    )
    tree = ast.parse(router_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "backend.app.main" in module:
                assert False, "projects.py imports backend.app.main (circular)"


def test_service_modules_do_not_import_main() -> None:
    """Service modules must never import backend.app.main."""
    import ast
    from pathlib import Path

    service_files = [
        Path(__file__).resolve().parents[1]
        / "backend" / "app" / "services" / "corpus_service.py",
        Path(__file__).resolve().parents[1]
        / "backend" / "app" / "services" / "project_service.py",
    ]
    for path in service_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "backend.app.main" in module:
                    assert False, f"{path.name} imports backend.app.main (circular)"
