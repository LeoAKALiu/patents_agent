from __future__ import annotations

from pathlib import Path

from backend.app.evidence_binding import (
    bindings_by_label,
    build_evidence_bindings,
    evidence_refs_for_text,
)
from backend.app.schemas import (
    DisclosurePackage,
    DisclosureRun,
    EvidenceBinding,
    EvidenceBindingSourceType,
    EvidenceVerificationStatus,
    PatentPointCandidate,
    PriorArtHit,
    ProjectMaterial,
    ProjectRecord,
)


def _project() -> ProjectRecord:
    return ProjectRecord(id="project-1", name="巡检机器人", draft_text="")


def _disclosure_run() -> DisclosureRun:
    prior_art_hit = PriorArtHit(
        id="prior-art-1",
        source="Google Patents",
        query="声学 视觉 巡检",
        title="一种设备异常检测方法",
        publication_number="CN111111A",
        url="https://patents.google.com/patent/CN111111A",
        abstract="公开了通过声学信号识别设备异常。",
        relevance_summary="覆盖声学检测，但未公开视觉复检窗口。",
        differentiators=["未公开声学异常窗口触发视觉局部复检"],
    )
    package = DisclosurePackage(
        title="声学视觉融合巡检",
        summary="通过声学异常窗口触发视觉局部复检。",
        materials_summary="用户材料描述了声学异常窗口。",
        prior_art_hits=[prior_art_hit],
        body_markdown="# 交底书\n声学异常窗口触发视觉局部复检。",
        mermaid="",
        image_prompt="",
        research_ledger={
            "entries": [
                {
                    "evidence_id": "E777",
                    "provider": "patent",
                    "source": "Google Patents",
                    "query": "声学 视觉 巡检",
                    "matched_query": "声学 视觉 巡检",
                    "title": "一种复合传感巡检方法",
                    "publication_number": "CN222222A",
                    "url": "https://patents.google.com/patent/CN222222A",
                    "snippet": "公开了复合传感巡检流程。",
                    "confidence": 0.73,
                    "citable": True,
                }
            ]
        },
    )
    return DisclosureRun(
        id="disclosure-run-1",
        project_id="project-1",
        status="completed",
        package=package,
    )


def _material() -> ProjectMaterial:
    return ProjectMaterial(
        id="material-1",
        project_id="project-1",
        file_name="实验记录.md",
        path="/tmp/material.md",
        file_type="markdown",
        text="实验记录显示，声学异常窗口触发视觉局部复检能够减少无效拍摄。",
        status="processed",
    )


def _patent_point() -> PatentPointCandidate:
    return PatentPointCandidate(
        id="point-1",
        title="声学窗口触发视觉复检",
        technical_problem="持续视觉采集成本高。",
        innovation="通过声学异常窗口触发视觉局部复检。",
        technical_solution="先用声学模型定位异常时间窗，再触发视觉复检。",
        beneficial_effects=["减少无效拍摄"],
        evidence_status="feasible_unverified",
        source_type="user",
        selected=True,
    )


def test_build_evidence_bindings_collects_research_prior_art_materials_and_patent_points() -> None:
    bindings = build_evidence_bindings(
        _project(),
        materials=[_material()],
        disclosures=[_disclosure_run()],
        patent_points=[_patent_point()],
    )

    by_id = {binding.evidence_id: binding for binding in bindings}
    assert "E777" in by_id
    ledger_binding = by_id["E777"]
    assert ledger_binding.source_type == EvidenceBindingSourceType.PRIOR_ART
    assert ledger_binding.source_id == "CN222222A"
    assert ledger_binding.metadata["publication_number"] == "CN222222A"
    assert ledger_binding.metadata["url"] == "https://patents.google.com/patent/CN222222A"
    assert ledger_binding.metadata["source"] == "Google Patents"
    assert ledger_binding.quote == "公开了复合传感巡检流程。"
    assert ledger_binding.confidence == 0.73
    assert ledger_binding.verification_status == EvidenceVerificationStatus.RETRIEVED
    assert ledger_binding.internal_only is True
    assert ledger_binding.citable is True

    prior_art_bindings = [item for item in bindings if item.source_type == EvidenceBindingSourceType.PRIOR_ART]
    assert {item.source_id for item in prior_art_bindings} == {"CN111111A", "CN222222A"}
    assert all(item.internal_only for item in prior_art_bindings)

    material_binding = next(item for item in bindings if item.source_type == EvidenceBindingSourceType.PROJECT_MATERIAL)
    assert material_binding.source_id == "material-1"
    assert material_binding.source_label == "实验记录.md"
    assert material_binding.verification_status == EvidenceVerificationStatus.USER_PROVIDED

    point_binding = next(item for item in bindings if item.source_type == EvidenceBindingSourceType.PATENT_POINT)
    assert point_binding.source_id == "point-1"
    assert point_binding.verification_status == EvidenceVerificationStatus.FEASIBLE_UNVERIFIED
    assert point_binding.confidence < 0.6
    assert point_binding.internal_only is True


def test_duplicate_publication_numbers_are_deduplicated_and_ledger_id_wins() -> None:
    run = _disclosure_run()
    assert run.package is not None
    run.package.research_ledger["entries"][0]["publication_number"] = "CN111111A"
    run.package.research_ledger["entries"][0]["evidence_id"] = "E123"

    bindings = build_evidence_bindings(
        _project(),
        materials=[],
        disclosures=[run],
        patent_points=[],
    )

    prior_art_bindings = [item for item in bindings if item.source_type == EvidenceBindingSourceType.PRIOR_ART]
    assert len(prior_art_bindings) == 1
    assert prior_art_bindings[0].evidence_id == "E123"
    assert prior_art_bindings[0].metadata["publication_number"] == "CN111111A"


def test_bindings_by_label_indexes_ids_titles_publication_numbers_and_urls() -> None:
    binding = EvidenceBinding(
        evidence_id="E050",
        source_type=EvidenceBindingSourceType.PRIOR_ART,
        source_id="CN555555A",
        source_label="一种声学视觉巡检方法",
        metadata={"publication_number": "CN555555A", "url": "https://example.test/CN555555A"},
    )

    index = bindings_by_label([binding])

    assert index["E050"] == [binding]
    assert index["CN555555A"] == [binding]
    assert index["一种声学视觉巡检方法"] == [binding]
    assert index["HTTPS://EXAMPLE.TEST/CN555555A"] == [binding]


def test_evidence_refs_for_text_uses_labels_quotes_and_confidence_threshold() -> None:
    high_confidence = EvidenceBinding(
        evidence_id="E900",
        source_type=EvidenceBindingSourceType.PROJECT_MATERIAL,
        source_id="material-9",
        source_label="实验记录.md",
        quote="声学异常窗口触发视觉局部复检",
        confidence=0.82,
        verification_status=EvidenceVerificationStatus.USER_PROVIDED,
    )
    low_confidence = EvidenceBinding(
        evidence_id="E901",
        source_type=EvidenceBindingSourceType.PATENT_POINT,
        source_id="point-9",
        source_label="低置信模型建议",
        quote="声学异常窗口触发视觉局部复检",
        confidence=0.42,
        verification_status=EvidenceVerificationStatus.MODEL_GENERATED,
    )

    refs = evidence_refs_for_text(
        "权利要求限定声学异常窗口触发视觉局部复检，并引用实验记录.md。",
        [high_confidence, low_confidence],
        min_confidence=0.6,
    )

    assert refs == ["E900"]


def test_official_export_modules_do_not_import_evidence_bindings() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    official_modules = [
        repo_root / "backend/app/official_compile.py",
        repo_root / "backend/app/filing_readiness.py",
    ]

    for module_path in official_modules:
        content = module_path.read_text(encoding="utf-8")
        assert "backend.app.evidence_binding" not in content
        assert "EvidenceBinding" not in content
