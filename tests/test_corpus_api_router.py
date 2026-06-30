"""PR-2: Corpus API router - integration tests.

Verify that corpus endpoints work through the router layer after
moving from inline handlers in ``backend/app/main.py``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


SAMPLE_PATENT = """摘要
本发明公开了一种模型训练方法。
权利要求书
1. 一种模型训练方法，其特征在于，包括获取训练样本和训练神经网络模型。
说明书
技术领域
本发明涉及人工智能领域。
发明内容
本发明提高模型训练效率。
具体实施方式
系统采集样本、训练模型并输出结果。
"""


def _make_app(tmp_path: Path, **kwargs) -> TestClient:
    return TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), **kwargs))


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------


def test_list_corpus_returns_empty_initially(tmp_path: Path) -> None:
    client = _make_app(tmp_path)
    response = client.get("/api/corpus")
    assert response.status_code == 200
    assert response.json()["documents"] == []


def test_import_corpus_and_list(tmp_path: Path) -> None:
    client = _make_app(tmp_path)
    response = client.post(
        "/api/corpus/import",
        files={"file": ("patent.txt", SAMPLE_PATENT.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunks_count"] >= 3
    assert body["document"]["title"] == "本发明公开了一种模型训练方法。"

    list_response = client.get("/api/corpus")
    assert list_response.status_code == 200
    assert len(list_response.json()["documents"]) == 1


def test_get_corpus_document_found(tmp_path: Path) -> None:
    client = _make_app(tmp_path)
    import_resp = client.post(
        "/api/corpus/import",
        files={"file": ("patent.txt", SAMPLE_PATENT.encode("utf-8"), "text/plain")},
    )
    doc_id = import_resp.json()["document"]["id"]

    response = client.get(f"/api/corpus/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["id"] == doc_id


def test_get_corpus_document_not_found(tmp_path: Path) -> None:
    client = _make_app(tmp_path)
    response = client.get("/api/corpus/documents/nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_search_corpus_finds_chunks(tmp_path: Path) -> None:
    client = _make_app(tmp_path)
    client.post(
        "/api/corpus/import",
        files={"file": ("patent.txt", SAMPLE_PATENT.encode("utf-8"), "text/plain")},
    )

    response = client.get(
        "/api/corpus/search",
        params={"q": "神经网络", "section_type": "claims", "limit": 3},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) >= 1
    assert results[0]["chunk"]["section_type"] == "claims"


def test_search_corpus_empty_query_rejected(tmp_path: Path) -> None:
    client = _make_app(tmp_path)
    response = client.get("/api/corpus/search", params={"q": ""})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Versions and stats
# ---------------------------------------------------------------------------


def test_list_corpus_versions_returns_list(tmp_path: Path) -> None:
    client = _make_app(tmp_path)
    response = client.get("/api/corpus/versions")
    assert response.status_code == 200
    assert isinstance(response.json()["versions"], list)


def test_corpus_stats_after_import(tmp_path: Path) -> None:
    client = _make_app(tmp_path)
    client.post(
        "/api/corpus/import",
        files={"file": ("patent.txt", SAMPLE_PATENT.encode("utf-8"), "text/plain")},
    )

    response = client.get("/api/corpus/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["document_count"] == 1
    assert stats["chunk_count"] >= 3
    assert len(stats["document_ids"]) == 1


# ---------------------------------------------------------------------------
# No circular imports
# ---------------------------------------------------------------------------


def test_corpus_router_does_not_import_main() -> None:
    """Corpus router must never import backend.app.main."""
    import ast
    from pathlib import Path

    router_path = (
        Path(__file__).resolve().parents[1]
        / "backend" / "app" / "api" / "corpus.py"
    )
    tree = ast.parse(router_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "backend.app.main" in module:
                assert False, "corpus.py imports backend.app.main (circular)"
