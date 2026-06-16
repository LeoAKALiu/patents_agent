from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from docx import Document

from backend.app.schemas import DisclosurePackage


def disclosure_to_markdown(package: DisclosurePackage) -> str:
    candidates = "\n".join(
        "\n".join(
            [
                f"- {candidate.id} {candidate.title}：{candidate.innovation}",
                f"  证据状态：{candidate.evidence_status}",
                f"  来源：{candidate.source_type}",
                f"  可行依据：{candidate.feasibility_basis or '未填写'}",
                f"  支撑缺口：{'；'.join(candidate.support_gaps) or '无显式缺口'}",
                f"  护城河评分：{candidate.moat_scores.weighted_total}",
            ]
        )
        for candidate in package.candidates
    )
    claim_charts = "\n".join(
        f"- {candidate.title}｜{chart.prior_art_title}｜差异特征：{'；'.join(chart.differentiating_features) or '暂无'}｜撰写建议：{chart.claim_drafting_advice or '暂无'}"
        for candidate in package.candidates
        for chart in candidate.claim_chart
    )
    prior_art = "\n".join(
        f"- [{hit.source}] {hit.title} {hit.publication_number or ''} {hit.url}\n  摘要：{hit.abstract or '无'}\n  差异：{'；'.join(hit.differentiators) or hit.relevance_summary or '待人工复核'}"
        for hit in package.prior_art_hits
    )
    findings = "\n".join(
        f"- [{finding.severity}] {finding.category}: {finding.message} 建议：{finding.suggestion}"
        for finding in package.self_check_findings
    )
    logs = "\n".join(f"- {log}" for log in package.generation_logs)

    # ---- V1.1: Research source ledger section ----
    ledger_section = _format_ledger_section(package)

    # ---- V1.1: Provider diagnostics section ----
    diagnostics_section = _format_diagnostics_section(package)

    # ---- V1.1: Research confidence badge ----
    confidence_badges = {"low": "🔴 低", "medium": "🟡 中", "high": "🟢 高"}
    confidence_badge = confidence_badges.get(package.research_confidence, "⚪ 未知")
    confidence_note = (
        "\n> **检索置信度**：{badge}\n>\n"
        "> 低置信度表示未检索到可引用的公开现有技术文献；交底书不隐含高专利性判断。\n"
        .format(badge=confidence_badge)
    )

    return f"""# {package.title}

## 前置材料摘要
{package.summary}

{confidence_note}
## 材料覆盖
{package.materials_summary}

## 候选专利点
{candidates or "暂无。"}

## Claim Chart
{claim_charts or "暂无。"}

## 公开现有技术
{prior_art or "暂无可用公开检索结果。"}

## 现有技术差异
{package.prior_art_differences}
{ledger_section}
{diagnostics_section}
## 技术交底书
{package.body_markdown}

## Mermaid 图
```mermaid
{package.mermaid}
```

## 绘图提示词
{package.image_prompt}

## 自检结果
{findings or "暂无。"}

## 生成日志
{logs or "暂无。"}
"""


def export_disclosure_docx(package: DisclosurePackage, output_path: Path, run_dir: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    warnings = list(package.export_warnings)
    image_path = _render_mermaid(package.mermaid, run_dir)
    if not image_path:
        warnings.append("Mermaid renderer unavailable or failed; DOCX keeps Mermaid code as text.")

    doc = Document()
    doc.add_heading(package.title, level=0)

    # ---- V1.1: Research confidence badge ----
    confidence_badges = {"low": "🔴 低（0 references）", "medium": "🟡 中", "high": "🟢 高"}
    confidence_label = confidence_badges.get(package.research_confidence, "⚪ 未知")
    _add_section(doc, "检索置信度", f"{confidence_label}\n\n低置信度表示未检索到可引用的公开现有技术文献；交底书不隐含高专利性判断。")

    _add_section(doc, "前置材料摘要", package.summary)
    _add_section(doc, "材料覆盖", package.materials_summary)
    _add_section(
        doc,
        "候选专利点",
        "\n".join(f"{item.id}. {item.title}：{item.innovation}" for item in package.candidates) or "暂无。",
    )
    _add_section(
        doc,
        "护城河与证据状态",
        "\n".join(
            f"{item.id}. {item.title}\n证据状态：{item.evidence_status}\n来源：{item.source_type}\n支撑缺口：{'；'.join(item.support_gaps) or '无显式缺口'}"
            for item in package.candidates
        )
        or "暂无。",
    )
    _add_section(
        doc,
        "Claim Chart",
        "\n".join(
            f"{candidate.title}｜{chart.prior_art_title}｜差异特征：{'；'.join(chart.differentiating_features) or '暂无'}｜撰写建议：{chart.claim_drafting_advice or '暂无'}"
            for candidate in package.candidates
            for chart in candidate.claim_chart
        )
        or "暂无。",
    )
    _add_section(
        doc,
        "公开现有技术",
        "\n".join(
            f"{hit.source}｜{hit.title}｜{hit.publication_number or ''}\n{hit.url}\n摘要：{hit.abstract or '无'}\n差异：{'；'.join(hit.differentiators) or hit.relevance_summary or '待人工复核'}"
            for hit in package.prior_art_hits
        )
        or "暂无可用公开检索结果。",
    )
    _add_section(doc, "现有技术差异", package.prior_art_differences)
    _add_section(doc, "检索来源台账", _format_ledger_section(package).replace("# ", "").replace("## ", ""))
    _add_section(doc, "检索链路诊断", _format_diagnostics_section(package).replace("# ", "").replace("## ", ""))
    _add_section(doc, "技术交底书", package.body_markdown)
    doc.add_heading("Mermaid 图", level=1)
    if image_path:
        doc.add_picture(str(image_path))
    else:
        for line in package.mermaid.splitlines() or [""]:
            doc.add_paragraph(line)
    _add_section(doc, "绘图提示词", package.image_prompt)
    _add_section(
        doc,
        "自检结果",
        "\n".join(
            f"[{finding.severity}] {finding.category}: {finding.message} 建议：{finding.suggestion}"
            for finding in package.self_check_findings
        )
        or "暂无。",
    )
    _add_section(doc, "生成日志", "\n".join(package.generation_logs + warnings))
    doc.save(output_path)
    return output_path


def write_disclosure_artifacts(package: DisclosurePackage, run_dir: Path) -> dict[str, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    md_path = run_dir / "disclosure.md"
    mmd_path = run_dir / "diagram.mmd"
    prompt_path = run_dir / "image-prompt.md"
    docx_path = run_dir / "disclosure.docx"
    md_path.write_text(disclosure_to_markdown(package), encoding="utf-8")
    mmd_path.write_text(package.mermaid, encoding="utf-8")
    prompt_path.write_text(package.image_prompt, encoding="utf-8")
    export_disclosure_docx(package, docx_path, run_dir)
    return {"md": md_path, "mmd": mmd_path, "prompt": prompt_path, "docx": docx_path}


def _render_mermaid(mermaid: str, run_dir: Path) -> Path | None:
    mmdc = shutil.which("mmdc")
    command: list[str] | None = None
    if mmdc:
        command = [mmdc]
    elif os.environ.get("PATENTS_AGENT_ENABLE_NPX_MERMAID") == "1" and shutil.which("npx"):
        command = ["npx", "-y", "@mermaid-js/mermaid-cli", "mmdc"]
    if not command:
        return None
    source = run_dir / "diagram-source.mmd"
    output = run_dir / "diagram.png"
    source.write_text(mermaid, encoding="utf-8")
    try:
        subprocess.run(
            [*command, "-i", str(source), "-o", str(output), "-b", "white"],
            check=True,
            capture_output=True,
            timeout=12,
        )
    except Exception:
        return None
    return output if output.exists() else None


def _add_section(doc: Document, heading: str, text: str) -> None:
    doc.add_heading(heading, level=1)
    for line in text.splitlines() or [""]:
        doc.add_paragraph(line)


def _format_ledger_section(package: "DisclosurePackage") -> str:
    """Format the research source ledger as a markdown section."""
    ledger = package.research_ledger
    if not ledger:
        return ""

    lines = [
        "## 检索来源台账",
        "",
    ]
    entries = ledger.get("entries", [])
    if not entries:
        lines.append("暂无检索记录。")
        lines.append("")
        return "\n".join(lines)

    lines.extend([
        f"- 总命中数：{ledger.get('total_hits', 0)}",
        f"- 总引用数：{ledger.get('total_citations', 0)}",
        "",
        "| 来源 | 类型 | 检索词 | 状态 | 命中 | 保留 | 失败原因 |",
        "|------|------|--------|------|------|------|----------|",
    ])
    for entry in entries:
        provider = entry.get("provider", "")
        kind = entry.get("kind", "")
        query = (entry.get("query", "") or "")[:50]
        status = entry.get("status", "running")
        hit_count = entry.get("hit_count", 0)
        retained = entry.get("retained_count", 0)
        failure = (entry.get("failure_reason", "") or "")[:60]

        status_icon = {"ok": "✅", "failed": "❌", "timeout": "⏰", "skipped": "⏭️", "running": "🔄"}.get(status, "❓")
        lines.append(
            f"| {provider} | {kind} | {query} | {status_icon} {status} | {hit_count} | {retained} | {failure} |"
        )

    # Citation snapshots
    all_citations: list[dict] = []
    for entry in entries:
        citations = entry.get("citations", [])
        if isinstance(citations, list):
            all_citations.extend(citations)

    if all_citations:
        lines.append("")
        lines.append("### 引用快照")
        lines.append("")
        for i, cit in enumerate(all_citations[:20], start=1):
            pub = cit.get("publication_number", "") or ""
            title = cit.get("title", "")[:80] or ""
            source = cit.get("source", "") or ""
            abstract = cit.get("abstract_snippet", "")[:60] or ""
            lines.append(f"{i}. [{source}] {pub} {title}")
            if abstract:
                lines.append(f"   {abstract}")

    lines.append("")
    return "\n".join(lines)


def _format_diagnostics_section(package: "DisclosurePackage") -> str:
    """Format provider diagnostics as a markdown section."""
    diagnostics = package.provider_diagnostics
    if not diagnostics:
        return ""

    lines = [
        "## 检索链路诊断",
        "",
    ]
    for diag in diagnostics:
        phase = diag.get("phase", "unknown")
        phase_label = "🔍 检索前" if phase == "pre_flight" else "📊 检索后"
        lines.append(f"### {phase_label}")
        lines.append("")

        available = diag.get("available_providers", [])
        if available:
            lines.append(f"- 可用来源：{'、'.join(available)}")
        else:
            lines.append("- 可用来源：无")

        skipped = diag.get("skipped_providers", [])
        if skipped:
            lines.append("- 跳过来源：")
            for skip in skipped:
                provider = skip.get("provider", "") if isinstance(skip, dict) else str(skip)
                reason = skip.get("reason", "") if isinstance(skip, dict) else ""
                lines.append(f"  - {provider}：{reason}")

        warnings_list = diag.get("warnings", [])
        if warnings_list:
            lines.append("- 警告：")
            for w in warnings_list:
                lines.append(f"  - {w}")

        lines.append("")
    return "\n".join(lines)
