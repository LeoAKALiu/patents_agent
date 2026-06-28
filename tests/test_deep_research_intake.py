from backend.app.research.deep_research_intake import (
    is_deep_research_markdown_material,
    packet_prior_art_hits,
    parse_deep_research_markdown,
    parse_deep_research_materials,
)
from backend.app.schemas import ProjectMaterial


DEEP_RESEARCH_MD = """
# DeepResearch: 图像缺陷识别

## 现有技术
- CN123456789A 一种图像缺陷检测方法 https://patents.google.com/patent/CN123456789A
  摘要：公开了基于神经网络的图像缺陷检测，但未涉及实时闭环反馈。

## 差异点
- 本方案将检测结果实时回写至采集策略，形成闭环反馈。

## 权利要求约束
- 独立权利要求需要限定闭环反馈的数据流，避免纯功能性概括。

## 证据缺口
- 需要补充闭环反馈降低误检率的工程样例。

## 风险
- 现有技术可能组合通用神经网络检测和反馈控制。
"""


def test_is_deep_research_markdown_material_detects_markdown_report() -> None:
    assert is_deep_research_markdown_material("deepresearch.md", DEEP_RESEARCH_MD)
    assert is_deep_research_markdown_material("research.markdown", DEEP_RESEARCH_MD)
    assert not is_deep_research_markdown_material("notes.txt", DEEP_RESEARCH_MD)
    assert not is_deep_research_markdown_material("notes.md", "普通会议纪要")


def test_parse_deep_research_markdown_builds_internal_packet() -> None:
    packet = parse_deep_research_markdown("project-1", DEEP_RESEARCH_MD, source_label="deepresearch.md")

    assert packet.status == "completed"
    assert packet.project_id == "project-1"
    assert packet.internal_only is True
    assert packet.evidence_ledger
    assert packet.evidence_ledger[0]["publication_number"] == "CN123456789A"
    assert packet.evidence_ledger[0]["url"] == "https://patents.google.com/patent/CN123456789A"
    assert "实时回写" in packet.differentiators[0]
    assert "闭环反馈的数据流" in packet.claim_drafting_constraints[0]
    assert "工程样例" in packet.suggested_completion_tasks[0]
    assert packet.findings
    assert {finding.category for finding in packet.findings} >= {
        "prior_art_cluster",
        "differentiator",
        "claim_constraint",
        "evidence_gap",
        "warning",
    }


def test_packet_prior_art_hits_converts_ledger_entries() -> None:
    packet = parse_deep_research_markdown("project-1", DEEP_RESEARCH_MD, source_label="deepresearch.md")

    hits = packet_prior_art_hits(packet)

    assert len(hits) == 1
    assert hits[0].source == "DeepResearch Markdown"
    assert hits[0].publication_number == "CN123456789A"
    assert hits[0].abstract and "实时闭环反馈" in hits[0].abstract


def test_parse_deep_research_markdown_handles_unrecognized_markdown() -> None:
    packet = parse_deep_research_markdown("project-1", "# 普通文档\n\n没有研究结构。", source_label="plain.md")

    assert packet.status == "partial"
    assert packet.warnings
    assert packet.evidence_ledger == []
    assert packet.findings == []


def test_parse_deep_research_materials_filters_markdown_materials() -> None:
    materials = [
        ProjectMaterial(
            id="m1",
            project_id="project-1",
            file_name="deepresearch.md",
            path="data/deepresearch.md",
            file_type="md",
            text=DEEP_RESEARCH_MD,
            status="processed",
        ),
        ProjectMaterial(
            id="m2",
            project_id="project-1",
            file_name="plain.md",
            path="data/plain.md",
            file_type="md",
            text="普通材料",
            status="processed",
        ),
    ]

    packets = parse_deep_research_materials(materials)

    assert len(packets) == 1
    assert packets[0].project_id == "project-1"
