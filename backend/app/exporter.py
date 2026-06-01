from __future__ import annotations

from pathlib import Path

from docx import Document

from backend.app.schemas import DraftPackage


def export_docx(package: DraftPackage, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_heading(package.title, level=0)
    _add_section(doc, "摘要", package.abstract)
    _add_section(doc, "权利要求书", package.claims)
    _add_section(doc, "说明书", package.description)
    _add_section(doc, "附图说明", package.drawing_description)
    _add_section(doc, "Mermaid流程图", package.mermaid)
    _add_section(doc, "绘图提示词", package.image_prompt)
    if package.strategy_brief:
        doc.add_heading("多Agent会审策略", level=1)
        doc.add_paragraph(package.strategy_brief.summary)
        for item in package.strategy_brief.claim_strategy:
            doc.add_paragraph(item, style=None)
    if package.citations:
        doc.add_heading("引用语料片段", level=1)
        for citation in package.citations:
            doc.add_paragraph(f"{citation.chunk_id} ({citation.section_type.value})")
            doc.add_paragraph(citation.text)
    if package.generation_logs:
        doc.add_heading("生成日志", level=1)
        for log in package.generation_logs:
            doc.add_paragraph(log)
    doc.save(output_path)
    return output_path


def package_to_markdown(package: DraftPackage) -> str:
    citations = "\n".join(
        f"- `{citation.chunk_id}` {citation.section_type.value}: {citation.text[:120]}"
        for citation in package.citations
    )
    findings = "\n".join(
        f"- [{finding.severity}] {finding.category}: {finding.message} 建议：{finding.suggestion}"
        for finding in package.review_findings
    )
    logs = "\n".join(f"- {log}" for log in package.generation_logs)
    strategy = package.strategy_brief.model_dump_json(ensure_ascii=False, indent=2) if package.strategy_brief else "暂无。"
    return f"""# {package.title}

## 摘要
{package.abstract}

## 权利要求书
{package.claims}

## 说明书
{package.description}

## 附图说明
{package.drawing_description}

## Mermaid流程图
```mermaid
{package.mermaid}
```

## 绘图提示词
{package.image_prompt}

## 推荐专利点
{package.patent_point_summary or "未注入前置专利点。"}

## 前置交底摘要
{package.disclosure_summary or "未注入前置交底书。"}

## 审查意见
{findings or "暂无。"}

## 多Agent会审策略
{strategy}

## 引用语料片段
{citations or "暂无。"}

## 生成日志
{logs or "暂无。"}
"""


def _add_section(doc: Document, heading: str, text: str) -> None:
    doc.add_heading(heading, level=1)
    for line in text.splitlines() or [""]:
        doc.add_paragraph(line)
