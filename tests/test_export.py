from pathlib import Path

from docx import Document

from backend.app.exporter import (
    export_docx,
    export_internal_docx,
    internal_package_to_markdown,
    package_to_markdown,
)
from backend.app.filing_readiness import official_package_to_markdown
from backend.app.schemas import DraftPackage


def test_export_docx_contains_complete_patent_sections(tmp_path: Path):
    package = DraftPackage(
        title="一种专利撰写辅助方法",
        abstract="本发明公开了一种专利撰写辅助方法。",
        claims="1. 一种专利撰写辅助方法，其特征在于，包括导入语料。",
        description="技术领域\n本发明涉及AI软件技术领域。",
        drawing_description="图1为本发明流程图。",
        mermaid="flowchart TD\nA[导入] --> B[生成]",
        image_prompt="黑白线稿，展示导入到生成的流程。",
        review_findings=[],
        citations=[],
        patent_point_summary="遮挡洞口语义补全",
    )

    output_path = export_docx(package, tmp_path / "draft.docx")

    doc = Document(output_path)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    assert "一种专利撰写辅助方法" in text
    assert "摘要" in text
    assert "权利要求书" in text
    assert "说明书" in text
    assert "附图说明" in text
    assert "绘图提示词" in text

    markdown = package_to_markdown(package)
    assert "推荐专利点" in markdown
    assert "遮挡洞口语义补全" in markdown


def test_official_markdown_export_contains_only_filing_sections():
    package = DraftPackage(
        title="一种清洁导出方法",
        abstract="本发明公开了一种清洁导出方法。",
        claims="1. 一种清洁导出方法。",
        description="技术领域\n本发明涉及专利文本处理。",
        drawing_description="图1为流程图。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="内部绘图提示词",
        generation_logs=["generation_logs: internal"],
        review_findings=[],
        citations=[],
    )

    markdown = official_package_to_markdown(package)

    assert "## 摘要" in markdown
    assert "## 权利要求书" in markdown
    assert "flowchart" not in markdown
    assert "内部绘图提示词" not in markdown
    assert "generation_logs" not in markdown


# ── PR-10: internal export labeling ───────────────────────────────────────────


def test_internal_docx_contains_disclaimer(tmp_path: Path):
    package = DraftPackage(
        title="一种专利撰写辅助方法",
        abstract="本发明公开了一种专利撰写辅助方法。",
        claims="1. 一种方法。",
        description="技术领域\n本发明涉及AI领域。",
        drawing_description="图1为流程图。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="黑白线稿",
        review_findings=[],
        citations=[],
    )
    output_path = export_internal_docx(package, tmp_path / "internal.docx")

    doc = Document(output_path)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)

    assert "内部工作稿" in text
    assert "仅供内部复核" in text
    assert "不得作为正式提交稿使用" in text
    # But patent sections are still there
    assert "一种专利撰写辅助方法" in text
    assert "摘要" in text


def test_internal_markdown_contains_disclaimer():
    package = DraftPackage(
        title="一种方法",
        abstract="本发明公开了一种方法。",
        claims="1. 一种方法。",
        description="技术领域\n本发明涉及AI领域。",
        drawing_description="图1为流程图。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="黑白线稿",
        review_findings=[],
        citations=[],
    )
    markdown = internal_package_to_markdown(package)

    assert markdown.startswith("> **内部工作稿**")
    assert "仅供内部复核" in markdown
    assert "不得作为正式提交稿使用" in markdown
    # But patent content is still there
    assert "## 摘要" in markdown
    assert "一种方法" in markdown


def test_legacy_export_endpoint_returns_internal_label(tmp_path):
    """Integration: /export.docx returns internal-labeled content."""
    from fastapi.testclient import TestClient
    from backend.app.main import create_app

    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "测试项目", "draft_text": "一种测试方法。"},
    ).json()["id"]
    client.app.state.store.update_project_package(
        project_id,
        DraftPackage(
            title="一种测试方法",
            abstract="本发明公开了一种测试方法。",
            claims="1. 一种测试方法。",
            description="技术领域\n本发明涉及测试技术领域。",
            drawing_description="图1为流程图。",
            mermaid="flowchart TD\nA-->B",
            image_prompt="黑白线稿",
            review_findings=[],
            citations=[],
        ),
    )

    # Legacy DOCX export
    from urllib.parse import unquote
    docx_resp = client.get(f"/api/projects/{project_id}/export.docx")
    assert docx_resp.status_code == 200
    content_disposition = docx_resp.headers.get("content-disposition", "")
    # FastAPI/Starlette URL-encodes non-ASCII filenames; decode before checking
    decoded = unquote(content_disposition)
    assert "内部工作稿.docx" in decoded
    assert decoded.endswith(".docx")

    # Legacy MD export
    md_resp = client.get(f"/api/projects/{project_id}/export.md")
    assert md_resp.status_code == 200
    assert "内部工作稿" in md_resp.text

