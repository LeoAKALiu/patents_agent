from __future__ import annotations

import zipfile

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


def test_corpus_job_api_runs_batch_import_and_exposes_stats(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({})))
    archive_path = tmp_path / "official-export.zip"
    metadata = (
        "申请号,授权公告号,专利名称,申请人,发明人,IPC分类号,专利类型,申请日,法律状态,文件名\n"
        "202310000010.0,CN116000010B,一种模型训练方法,某AI公司,张三,G06N 20/00,发明授权,2023-01-01,授权,cn116000010b.txt\n"
    )
    text = """一种模型训练方法
摘要
本发明公开了一种机器学习模型训练方法。
权利要求书
1. 一种模型训练方法，其特征在于，包括获取训练样本、训练神经网络模型并输出模型参数。
说明书
技术领域
本发明涉及人工智能模型训练技术领域。
发明内容
本发明提高模型训练稳定性。
附图说明
图1为模型训练流程图。
具体实施方式
服务器执行样本清洗、模型训练和参数输出。
"""
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("metadata.csv", metadata)
        archive.writestr("cn116000010b.txt", text)

    create_response = client.post(
        "/api/corpus/jobs",
        json={
            "source_type": "cnipa_export",
            "source_name": "CNIPA",
            "query": "G06N 机器学习 模型训练",
            "domain": "ai_software",
            "version_name": "ai-software-v1",
        },
    )
    assert create_response.status_code == 200
    job_id = create_response.json()["id"]

    with archive_path.open("rb") as handle:
        upload_response = client.post(
            f"/api/corpus/jobs/{job_id}/files",
            files={"file": ("official-export.zip", handle, "application/zip")},
        )
    assert upload_response.status_code == 200
    assert upload_response.json()["file_count"] == 1

    run_response = client.post(f"/api/corpus/jobs/{job_id}/run")
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["status"] == "completed"
    assert run_payload["quality_report"]["imported_documents"] == 1

    job_response = client.get(f"/api/corpus/jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["quality_report"]["section_coverage"]["claims"] == 1.0

    versions_response = client.get("/api/corpus/versions")
    assert versions_response.status_code == 200
    assert versions_response.json()["versions"][0]["name"] == "ai-software-v1"

    stats_response = client.get("/api/corpus/stats", params={"version": "ai-software-v1"})
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["document_count"] == 1
    assert stats["section_coverage"]["claims"] == 1.0
    assert stats["ipc_distribution"]["G06N"] == 1

    document_id = stats["document_ids"][0]
    document_response = client.get(f"/api/corpus/documents/{document_id}")
    assert document_response.status_code == 200
    assert document_response.json()["metadata"]["claims"][0]["category"] == "method"

    search_response = client.get(
        "/api/corpus/search",
        params={"q": "模型训练 神经网络 方法", "section_type": "claims", "version": "ai-software-v1"},
    )
    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["chunk"]["document_id"] == document_id


def test_corpus_upload_keeps_same_named_files_distinct(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({})))
    create_response = client.post(
        "/api/corpus/jobs",
        json={
            "source_type": "cnipa_export",
            "source_name": "CNIPA",
            "query": "G06N",
            "domain": "ai_software",
            "version_name": "ai-software-v1",
        },
    )
    assert create_response.status_code == 200
    job_id = create_response.json()["id"]

    last_payload = None
    for body in (b"first file body", b"second file body"):
        upload_response = client.post(
            f"/api/corpus/jobs/{job_id}/files",
            files={"file": ("duplicate.txt", body, "text/plain")},
        )
        assert upload_response.status_code == 200
        last_payload = upload_response.json()

    # Both uploads share a filename, but must be stored without overwriting.
    assert last_payload["file_count"] == 2
    input_paths = last_payload["job"]["input_paths"]
    assert len(input_paths) == 2
    assert len(set(input_paths)) == 2

    uploaded_dir = tmp_path / "corpus-jobs" / job_id / "uploaded"
    stored = sorted(path.name for path in uploaded_dir.iterdir())
    assert len(stored) == 2
    assert all(name.endswith("-duplicate.txt") for name in stored)
