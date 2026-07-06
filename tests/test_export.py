from pathlib import Path

from docx import Document

from backend.app.exporter import export_docx, package_to_markdown
from backend.app.filing_readiness import official_package_to_markdown
from backend.app.schemas import DraftPackage, PatentStrategyBrief


def test_export_docx_contains_only_draft_sections(tmp_path: Path):
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
        generation_logs=["deliberation: injected strategy brief from run abc"],
        strategy_brief=PatentStrategyBrief(
            summary="多智能体主席汇总。",
            claim_strategy=["方法独权"],
            description_strategy=["补充实施例"],
            risk_controls=["避免过宽"],
            agent_consensus="codex 与 deepseek 交叉质询后形成共识。",
        ),
    )

    output_path = export_docx(package, tmp_path / "draft.docx")

    doc = Document(output_path)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    assert "一种专利撰写辅助方法" in text
    assert "摘要" in text
    assert "权利要求书" in text
    assert "说明书" in text
    assert "附图说明" in text
    assert "Mermaid流程图" not in text
    assert "绘图提示词" not in text
    assert "多Agent会审策略" not in text
    assert "生成日志" not in text
    assert "codex" not in text
    assert "deepseek" not in text

    markdown = package_to_markdown(package)
    assert "## 摘要" in markdown
    assert "## 权利要求书" in markdown
    assert "## 说明书" in markdown
    assert "## 附图说明" in markdown
    assert "推荐专利点" not in markdown
    assert "遮挡洞口语义补全" not in markdown
    assert "Mermaid流程图" not in markdown
    assert "绘图提示词" not in markdown
    assert "多Agent会审策略" not in markdown
    assert "生成日志" not in markdown
    assert "codex" not in markdown
    assert "deepseek" not in markdown


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
