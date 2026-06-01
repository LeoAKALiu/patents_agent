from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


def _test_app_without_env(tmp_path):
    return TestClient(create_app(data_dir=tmp_path, load_env_file=False))


def test_api_corpus_project_generation_review_and_export(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种图像缺陷识别方法，其特征在于，包括采集图像并训练模型。\n2. 根据权利要求1所述的方法，其特征在于，输出缺陷位置。",
            "description": "技术领域\n本发明涉及AI检测技术领域。\n发明内容\n本发明通过模型训练实现缺陷识别。",
            "abstract": "本发明公开了一种图像缺陷识别方法，能够提高检测准确性。",
            "drawings": "图1为图像缺陷识别方法流程图。\n图2为系统结构图。",
            "diagram": "flowchart TD\nA[采集图像] --> B[训练模型] --> C[输出结果]",
            "image_prompt": "黑白线稿，展示图像采集、模型训练和结果输出流程。",
            "review": '[{"category":"支持性","severity":"medium","message":"从属权利要求支撑略少。","suggestion":"在具体实施方式中补充缺陷位置输出细节。","evidence":"权利要求2"}]',
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    sample = """摘要
本发明公开了一种图像缺陷识别方法。
权利要求书
1. 一种图像缺陷识别方法，其特征在于，包括训练神经网络模型并输出检测结果。
说明书
技术领域
本发明涉及人工智能检测技术领域。
具体实施方式
系统采集图像、训练模型并输出结果。
"""

    import_response = client.post(
        "/api/corpus/import",
        files={"file": ("sample.txt", sample.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 200
    assert import_response.json()["chunks_count"] >= 3

    search_response = client.get("/api/corpus/search", params={"q": "图像 神经网络 缺陷", "section_type": "claims"})
    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["chunk"]["section_type"] == "claims"

    project_response = client.post(
        "/api/projects",
        json={
            "name": "图像缺陷识别",
            "draft_text": "一种基于神经网络的图像缺陷识别方法，解决人工检测效率低的问题。",
        },
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]

    generate_response = client.post(f"/api/projects/{project_id}/generate")
    assert generate_response.status_code == 200
    assert "权利要求1" in generate_response.json()["claims"]

    review_response = client.post(f"/api/projects/{project_id}/review")
    assert review_response.status_code == 200
    assert review_response.json()["review_findings"][0]["category"] == "支持性"

    export_response = client.get(f"/api/projects/{project_id}/export.docx")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_generate_fails_closed_without_llm_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = _test_app_without_env(tmp_path)
    project_response = client.post(
        "/api/projects",
        json={"name": "未配置模型", "draft_text": "一种AI方法，用于生成专利文本。"},
    )
    project_id = project_response.json()["id"]

    generate_response = client.post(f"/api/projects/{project_id}/generate")

    assert generate_response.status_code == 503
    assert "DEEPSEEK_API_KEY" in generate_response.json()["detail"]
