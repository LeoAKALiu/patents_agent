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

SHIFTED_DEEP_RESEARCH_MD = """
# DeepResearch: 图像缺陷识别

## 背景补充
- 无关的前置说明，不应影响后续发现的稳定 ID。

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

DISTINCT_EVIDENCE_MD = """
# DeepResearch: 图像缺陷识别

## 现有技术
- CN123456789A 一种图像缺陷检测方法 https://patents.google.com/patent/CN123456789A
  摘要：公开了基于神经网络的图像缺陷检测，但未涉及实时闭环反馈。
- CN123456789A 一种图像缺陷检测方法 https://patents.google.com/patent/CN123456789A
  摘要：另一段不同的摘录，强调不同的实施环境与误检抑制策略。
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
    assert packet.evidence_ledger[0]["source_label"] == "deepresearch.md"
    assert packet.findings[0].evidence[0].source == "DeepResearch Markdown"
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


def test_parse_deep_research_markdown_is_stable_across_repeated_runs() -> None:
    packet_one = parse_deep_research_markdown("project-1", DEEP_RESEARCH_MD, source_label="deepresearch.md")
    packet_two = parse_deep_research_markdown("project-1", DEEP_RESEARCH_MD, source_label="deepresearch.md")

    assert [finding.id for finding in packet_one.findings] == [finding.id for finding in packet_two.findings]
    assert packet_one.evidence_ledger == packet_two.evidence_ledger
    assert [hit.id for hit in packet_prior_art_hits(packet_one)] == [hit.id for hit in packet_prior_art_hits(packet_two)]


def test_parse_deep_research_markdown_keeps_finding_id_when_earlier_content_is_inserted() -> None:
    target_summary = "本方案将检测结果实时回写至采集策略，形成闭环反馈。"
    packet_one = parse_deep_research_markdown("project-1", DEEP_RESEARCH_MD, source_label="deepresearch.md")
    packet_two = parse_deep_research_markdown("project-1", SHIFTED_DEEP_RESEARCH_MD, source_label="shifted.md")

    base_id = next(finding.id for finding in packet_one.findings if finding.summary == target_summary)
    shifted_id = next(finding.id for finding in packet_two.findings if finding.summary == target_summary)

    assert base_id == shifted_id


def test_parse_deep_research_markdown_keeps_ids_stable_across_project_and_file_changes() -> None:
    packet_one = parse_deep_research_markdown("project-a", DEEP_RESEARCH_MD, source_label="alpha.md")
    packet_two = parse_deep_research_markdown("project-b", DEEP_RESEARCH_MD, source_label="beta.md")

    assert [finding.id for finding in packet_one.findings] == [finding.id for finding in packet_two.findings]
    assert [entry["evidence_id"] for entry in packet_one.evidence_ledger] == [
        entry["evidence_id"] for entry in packet_two.evidence_ledger
    ]
    assert [hit.id for hit in packet_prior_art_hits(packet_one)] == [hit.id for hit in packet_prior_art_hits(packet_two)]
    assert packet_one.evidence_ledger[0]["source_label"] == "alpha.md"
    assert packet_two.evidence_ledger[0]["source_label"] == "beta.md"


def test_parse_deep_research_markdown_does_not_collide_on_distinct_evidence() -> None:
    packet_one = parse_deep_research_markdown(
        "project-1",
        DEEP_RESEARCH_MD,
        source_label="deepresearch-a.md",
    )
    packet_two = parse_deep_research_markdown(
        "project-1",
        """
        # DeepResearch: 图像缺陷识别

        ## 现有技术
        - CN987654321A 另一种图像缺陷检测方法 https://patents.google.com/patent/CN987654321A
          摘要：公开了不同的图像缺陷检测方案。
        """,
        source_label="deepresearch-b.md",
    )

    ids_one = {entry["evidence_id"] for entry in packet_one.evidence_ledger}
    ids_two = {entry["evidence_id"] for entry in packet_two.evidence_ledger}
    hit_ids_one = {hit.id for hit in packet_prior_art_hits(packet_one)}
    hit_ids_two = {hit.id for hit in packet_prior_art_hits(packet_two)}

    assert ids_one.isdisjoint(ids_two)
    assert hit_ids_one.isdisjoint(hit_ids_two)


def test_parse_deep_research_markdown_keeps_distinct_snippets_separate() -> None:
    packet = parse_deep_research_markdown("project-1", DISTINCT_EVIDENCE_MD, source_label="deepresearch.md")

    assert len(packet.evidence_ledger) == 2
    assert packet.evidence_ledger[0]["evidence_id"] != packet.evidence_ledger[1]["evidence_id"]

    hits = packet_prior_art_hits(packet)
    assert len(hits) == 2
    assert hits[0].id != hits[1].id
    assert hits[0].abstract != hits[1].abstract


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
