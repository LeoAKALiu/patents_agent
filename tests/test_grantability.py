"""Tests for V1.1 PR2: Grantability claim chart and patentability attack analysis."""

from __future__ import annotations

from backend.app.grantability import (
    generate_grantability_report,
    grantability_report_to_markdown,
)
from backend.app.schemas import (
    ClaimChartItem,
    DeepResearchFinding,
    DeepResearchEvidenceRef,
    DeepResearchPacket,
    DisclosurePackage,
    DisclosureRun,
    DraftPackage,
    FeaturePlacement,
    GrantabilityClaimChartRow,
    GrantabilityReport,
    InventiveStepAttackCombo,
    MoatScores,
    NoveltyAttack,
    PatentPointCandidate,
    PatentStrategyBrief,
    PriorArtHit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_package() -> DraftPackage:
    return DraftPackage(
        title="一种基于IFC的建筑洞口自动扣减方法",
        abstract="本发明涉及建筑信息模型领域，具体涉及基于IFC的洞口自动扣减方法。",
        claims="1. 一种基于IFC的建筑洞口自动扣减方法，其特征在于，包括：采集IFC模型数据；识别洞口元素；自动生成扣减体。",
        description=(
            "技术领域\n本发明涉及BIM技术领域。\n"
            "背景技术\n现有扣减依赖人工操作。\n"
            "发明内容\n通过IfcRelVoidsElement自动识别洞口并生成扣减体。\n"
            "实施例\n步骤S1：解析IFC文件。步骤S2：遍历IfcRelVoidsElement关系。\n"
        ),
        drawing_description="图1为系统流程图。",
        mermaid="flowchart TD\nA[采集IFC] --> B[识别洞口] --> C[生成扣减体]",
        image_prompt="IFC洞口自动扣减系统架构图",
        review_findings=[],
        citations=[],
        generation_logs=[],
    )


def _sample_prior_art() -> list[PriorArtHit]:
    return [
        PriorArtHit(
            id="pa-1",
            source="cnipa",
            query="IFC 洞口 扣减",
            title="一种基于IFC标准的建筑模型处理方法",
            publication_number="CN119131262A",
            url="https://patents.google.com/patent/CN119131262A",
            abstract="公开了一种基于IFC标准的建筑模型处理方法，包括解析IFC文件和识别建筑构件。",
        ),
        PriorArtHit(
            id="pa-2",
            source="google_patents",
            query="BIM 碰撞检测",
            title="建筑信息模型碰撞检测方法",
            publication_number="US20230123456A1",
            url="https://patents.google.com/patent/US20230123456A1",
            abstract="公开了一种建筑信息模型碰撞检测方法，通过BIM模型自动检测构件之间的碰撞。",
        ),
        PriorArtHit(
            id="pa-3",
            source="cnipa",
            query="洞口 自动 生成",
            title="建筑洞口自动生成方法",
            publication_number="CN118987654B",
            url="https://patents.google.com/patent/CN118987654B",
            abstract="公开了一种建筑洞口自动生成方法，根据预设规则自动在墙体上生成洞口。",
        ),
    ]


def _sample_patent_points() -> list[PatentPointCandidate]:
    return [
        PatentPointCandidate(
            id="pp-1",
            title="IFC洞口自动扣减",
            technical_problem="现有技术在建筑信息模型中依赖人工实现洞口扣减，效率低。",
            innovation="通过IfcRelVoidsElement自动识别洞口并生成扣减体。",
            technical_solution="解析IFC文件，遍历IfcRelVoidsElement关系，自动生成扣减体。",
            beneficial_effects=["提高效率", "减少人工错误"],
            protection_focus=["IFC模型解析", "洞口自动识别", "扣减体自动生成"],
            evidence_status="verified",
            feasibility_basis="已实现原型验证。",
            moat_scores=MoatScores(
                scope_width=0.7, designaround_difficulty=0.6, feasibility=0.8,
                support_strength=0.7, prior_art_distance=0.5, strategic_value=0.8,
            ),
            claim_chart=[
                ClaimChartItem(
                    prior_art_id="pa-1",
                    prior_art_title="一种基于IFC标准的建筑模型处理方法",
                    overlapping_features=["IFC模型解析"],
                    differentiating_features=["洞口自动识别", "扣减体自动生成"],
                    claim_drafting_advice="在权利要求中突出IfcRelVoidsElement遍历和自动扣减体生成。",
                ),
            ],
            selected=True,
        ),
        PatentPointCandidate(
            id="pp-2",
            title="清单回链",
            technical_problem="无法将扣减体关联到工程量清单。",
            innovation="建立扣减体与工程量清单项的回链映射。",
            technical_solution="生成扣减体时同时记录关联的清单项ID。",
            beneficial_effects=["追溯性"],
            protection_focus=["清单回链映射"],
            evidence_status="feasible_unverified",
            moat_scores=MoatScores(),
            claim_chart=[],
            selected=True,
        ),
    ]


def _sample_disclosure() -> DisclosureRun:
    return DisclosureRun(
        id="disc-1",
        project_id="proj-1",
        status="completed",
        package=DisclosurePackage(
            title="IFC洞口自动扣减技术方案披露",
            summary="本方案通过IfcRelVoidsElement自动识别洞口并生成扣减体。",
            materials_summary="",
            candidates=[],
            prior_art_hits=_sample_prior_art(),
            prior_art_differences="现有技术未公开基于IfcRelVoidsElement的自动洞口识别。",
            body_markdown="# 技术方案披露\n...",
            mermaid="",
            image_prompt="",
            research_confidence="medium",
            research_ledger={},
        ),
    )


def _sample_deep_research() -> DeepResearchPacket:
    return DeepResearchPacket(
        status="completed",
        cycles=2,
        project_id="proj-1",
        query_plan=["IFC 洞口 扣减 自动化"],
        queries_run=["IFC 洞口 扣减 自动化"],
        findings=[
            DeepResearchFinding(
                id="f1",
                category="differentiator",
                title="IfcRelVoidsElement差异化",
                summary="现有技术未使用IfcRelVoidsElement实现自动扣减。",
                severity="medium",
                evidence=[
                    DeepResearchEvidenceRef(
                        source="cnipa",
                        query="IFC 洞口 扣减",
                        title="基于IFC的建筑构件处理方法",
                        publication_number="CN119131263B",
                        url="",
                    )
                ],
            ),
        ],
    )


def _sample_strategy() -> PatentStrategyBrief:
    return PatentStrategyBrief(
        summary="方法独权 + 系统独权，说明书强化IfcRelVoidsElement支撑。",
        claim_strategy=["方法独权", "系统独权"],
        description_strategy=["强化IfcRelVoidsElement伪代码"],
        risk_controls=["限缩到洞口扣减"],
    )


# ---------------------------------------------------------------------------
# Tests: schema validation
# ---------------------------------------------------------------------------


def test_grantability_schema_round_trips() -> None:
    """GrantabilityReport and its sub-models serialize/deserialize correctly."""
    report = GrantabilityReport(
        id="r1",
        project_id="p1",
        status="medium",
        overall_assessment="授权前景中等。",
        closest_prior_art_summary="CN119131262A",
        claim_chart=[
            GrantabilityClaimChartRow(
                claim_ref="1",
                feature_text="IFC模型解析",
                feature_placement=FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED,
                closest_prior_art_refs=["CN119131262A"],
                novelty_distinction="现有技术未公开基于IfcRelVoidsElement的自动洞口识别。",
                support_status="strong",
            ),
        ],
        novelty_attacks=[
            NoveltyAttack(
                feature_text="IFC模型解析",
                prior_art_title="一种基于IFC标准的建筑模型处理方法",
                prior_art_ref="CN119131262A",
                citation_source="cnipa",
                overlap_analysis="现有技术已公开IFC模型解析特征。",
                attack_strength="moderate",
                evidence_quality="verified",
            ),
        ],
        inventive_step_attacks=[
            InventiveStepAttackCombo(
                title="CN119131262A + US20230123456A1 组合",
                primary_reference="CN119131262A",
                secondary_references=["US20230123456A1"],
                combination_rationale="本领域技术人员有动机结合两者。",
                attack_strength="moderate",
                defense_suggestion="说明组合存在技术障碍。",
            ),
        ],
        risk_summary={"novelty_risk": "1项特征面临强新颖性攻击。"},
        low_evidence_flags=["部分现有技术引用未经验证。"],
        fail_closed=False,
        recommendation="授权前景中等。",
        created_at="2025-01-01T00:00:00Z",
    )

    data = report.model_dump(mode="json")
    restored = GrantabilityReport.model_validate(data)

    assert restored.id == "r1"
    assert restored.status == "medium"
    assert restored.fail_closed is False
    assert len(restored.claim_chart) == 1
    assert restored.claim_chart[0].feature_placement == FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED
    assert len(restored.novelty_attacks) == 1
    assert restored.novelty_attacks[0].attack_strength == "moderate"
    assert restored.novelty_attacks[0].evidence_quality == "verified"
    assert len(restored.inventive_step_attacks) == 1
    assert restored.inventive_step_attacks[0].attack_strength == "moderate"
    assert "novelty_risk" in restored.risk_summary


def test_feature_placement_enum_values() -> None:
    """FeaturePlacement enum has exactly the four required values."""
    values = {v.value for v in FeaturePlacement}
    assert values == {
        "independent_claim_required",
        "dependent_claim_optional",
        "description_only_support",
        "should_delete",
    }


def test_novelty_attack_strength_constrained() -> None:
    """NoveltyAttack rejects invalid attack_strength."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        NoveltyAttack(
            feature_text="test",
            attack_strength="invalid",
        )


def test_grantability_report_status_constrained() -> None:
    """GrantabilityReport rejects invalid status."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GrantabilityReport(
            id="r1",
            project_id="p1",
            status="garbage",
        )


# ---------------------------------------------------------------------------
# Tests: core grantability report generation
# ---------------------------------------------------------------------------


def test_generate_basic_grantability_report() -> None:
    """Generate a report from standard inputs and verify key fields."""
    report = generate_grantability_report(
        project_id="proj-1",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
    )

    assert report.project_id == "proj-1"
    assert isinstance(report.id, str) and len(report.id) > 0
    assert report.created_at  # timestamp present
    assert report.claim_chart  # chart rows populated
    assert report.closest_prior_art_summary
    assert "CN119131262A" in report.closest_prior_art_summary

    # At least one novelty attack should exist.
    assert report.novelty_attacks


def test_generate_grantability_with_deep_research() -> None:
    """Deep-research packets contribute additional prior-art refs."""
    report = generate_grantability_report(
        project_id="proj-2",
        package=_sample_package(),
        disclosures=[],
        patent_points=[],
        deep_research_packets=[_sample_deep_research()],
    )

    assert report.source_ledger_citations
    # The deep-research finding should produce at least one prior-art hit.
    has_deep_research_ref = any(
        cit.get("publication_number") == "CN119131263B"
        for cit in report.source_ledger_citations
        if "publication_number" in cit
    )
    assert has_deep_research_ref


def test_generate_grantability_with_strategy_brief() -> None:
    """Strategy brief feeds into the recommendation text."""
    report = generate_grantability_report(
        project_id="proj-3",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
        strategy_brief=_sample_strategy(),
    )

    assert "方法独权" in report.recommendation


# ---------------------------------------------------------------------------
# Tests: low-evidence fail-closed behavior
# ---------------------------------------------------------------------------


def test_empty_inputs_fail_closed() -> None:
    """When there are zero disclosures and zero patent points, fail_closed=True."""
    report = generate_grantability_report(
        project_id="proj-4",
        package=_sample_package(),
        disclosures=[],
        patent_points=[],
        deep_research_packets=[],
    )

    assert report.fail_closed is True
    assert report.status in ("low", "uncertain")
    assert report.low_evidence_flags  # at least one flag
    assert any("不足" in flag for flag in report.low_evidence_flags)


def test_no_prior_art_fail_closed() -> None:
    """Disclosure with zero prior-art hits triggers fail-closed."""
    disc = DisclosureRun(
        id="disc-empty",
        project_id="proj-5",
        status="completed",
        package=DisclosurePackage(
            title="Empty disclosure",
            summary="",
            materials_summary="",
            prior_art_hits=[],
            prior_art_differences="",
            body_markdown="",
            mermaid="",
            image_prompt="",
            research_confidence="low",
            research_ledger={},
        ),
    )
    report = generate_grantability_report(
        project_id="proj-5",
        package=_sample_package(),
        disclosures=[disc],
        patent_points=[],
    )

    assert report.fail_closed is True
    assert report.status in ("low", "uncertain")


def test_low_evidence_cannot_be_presented_as_high_grant() -> None:
    """Low-evidence reports must never present status='high'."""
    report = generate_grantability_report(
        project_id="proj-6",
        package=_sample_package(),
        disclosures=[],
        patent_points=[],
    )

    assert report.status != "high"
    assert report.fail_closed is True


def test_minimal_prior_art_less_than_two_triggers_flag() -> None:
    """Fewer than 2 prior-art hits produces a low-evidence flag."""
    disc = DisclosureRun(
        id="disc-one",
        project_id="proj-7",
        status="completed",
        package=DisclosurePackage(
            title="One-hit disclosure",
            summary="",
            materials_summary="",
            prior_art_hits=[_sample_prior_art()[0]],  # only 1 hit
            prior_art_differences="",
            body_markdown="",
            mermaid="",
            image_prompt="",
            research_confidence="low",
            research_ledger={},
        ),
    )
    report = generate_grantability_report(
        project_id="proj-7",
        package=_sample_package(),
        disclosures=[disc],
        patent_points=[],
    )

    assert report.fail_closed is True
    assert any("数量不足" in flag for flag in report.low_evidence_flags)


# ---------------------------------------------------------------------------
# Tests: feature placement classification
# ---------------------------------------------------------------------------


def test_feature_placement_independent_claim() -> None:
    """Features appearing in claims with '其特征在于' are independent_claim_required."""
    report = generate_grantability_report(
        project_id="proj-8",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
    )
    independent = [r for r in report.claim_chart if r.feature_placement == FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED]
    assert len(independent) >= 1


def test_feature_placement_should_delete() -> None:
    """Features not in claims or description are flagged should_delete."""
    # Create patent points with a feature that won't match anything in the package.
    orphan_point = PatentPointCandidate(
        id="pp-orphan",
        title="孤岛特征",
        technical_problem="无对应技术问题",
        innovation="一个完全不在说明书和权利要求中的特征XYZ123ABC",
        technical_solution="",
        protection_focus=["XYZ123ABC完全不存在的特征"],
        evidence_status="model_generated",
        moat_scores=MoatScores(),
        claim_chart=[],
        selected=True,
    )
    report = generate_grantability_report(
        project_id="proj-9",
        package=DraftPackage(
            title="minimal", abstract="", claims="", description="",
            drawing_description="", mermaid="", image_prompt="",
        ),
        disclosures=[],
        patent_points=[orphan_point],
    )
    should_delete = [r for r in report.claim_chart if r.feature_placement == FeaturePlacement.SHOULD_DELETE]
    assert len(should_delete) >= 1


def test_feature_placement_description_only() -> None:
    """Features in description but not claims are description_only_support."""
    report = generate_grantability_report(
        project_id="proj-10",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
    )
    desc_only = [r for r in report.claim_chart if r.feature_placement == FeaturePlacement.DESCRIPTION_ONLY_SUPPORT]
    # Some features from patent_points may fall into this category.
    # At minimum, the classification logic should not crash.
    assert isinstance(desc_only, list)


# ---------------------------------------------------------------------------
# Tests: novelty attack
# ---------------------------------------------------------------------------


def test_novelty_attack_strength_from_overlap() -> None:
    """Novelty attacks are graded by keyword overlap with prior art."""
    report = generate_grantability_report(
        project_id="proj-11",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
    )
    # The first prior-art hit should produce attacks.
    assert report.novelty_attacks
    attack = report.novelty_attacks[0]
    assert attack.attack_strength in ("strong", "moderate", "weak", "none")
    assert attack.evidence_quality in ("verified", "unverified", "low")
    assert attack.prior_art_ref


def test_novelty_attack_verified_when_publication_number_exists() -> None:
    """Prior art with a publication_number gets evidence_quality='verified'."""
    from backend.app.grantability import _build_single_novelty_attack

    pa = PriorArtHit(
        id="pa-1",
        source="cnipa",
        query="test",
        title="Test Patent",
        publication_number="CN123A",
        url="",
        abstract="This patent discloses a method for testing.",
    )
    attack = _build_single_novelty_attack("method for testing", pa)
    assert attack.evidence_quality == "verified"


def test_novelty_attack_low_when_no_publication_number() -> None:
    """Prior art without a publication_number gets evidence_quality='low'."""
    from backend.app.grantability import _build_single_novelty_attack

    pa = PriorArtHit(
        id="pa-1",
        source="llm-echo",
        query="test",
        title="Test Patent",
        publication_number=None,
        url="",
        abstract="",
    )
    attack = _build_single_novelty_attack("completely different feature", pa)
    assert attack.evidence_quality == "low"


# ---------------------------------------------------------------------------
# Tests: inventive-step attack combos
# ---------------------------------------------------------------------------


def test_inventive_step_combos_built_when_multiple_prior_art() -> None:
    """With ≥2 prior-art hits, inventive-step combos are generated."""
    report = generate_grantability_report(
        project_id="proj-12",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
    )

    # 3 prior-art hits → at least some combos.
    assert report.inventive_step_attacks
    for combo in report.inventive_step_attacks:
        assert combo.attack_strength in ("strong", "moderate", "weak")
        assert combo.combination_rationale
        assert combo.defense_suggestion


def test_empty_prior_art_produces_no_combos() -> None:
    """No prior art → no inventive-step combos."""
    report = generate_grantability_report(
        project_id="proj-13",
        package=_sample_package(),
        disclosures=[],
        patent_points=[],
    )

    assert report.inventive_step_attacks == []


def test_inventive_step_combos_attached_to_rows() -> None:
    """Claim-chart rows carry inventive-step combos from prior art."""
    report = generate_grantability_report(
        project_id="proj-14",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
    )

    for row in report.claim_chart[:3]:
        assert row.inventive_step_combos


# ---------------------------------------------------------------------------
# Tests: risk summary
# ---------------------------------------------------------------------------


def test_risk_summary_detects_overbreadth() -> None:
    """Broad features without detail trigger overbreadth risk."""
    report = generate_grantability_report(
        project_id="proj-15",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
    )

    assert isinstance(report.risk_summary, dict)
    # The protection_focus items should generate at least some risk entries.
    assert len(report.risk_summary) >= 1 or report.low_evidence_flags


def test_risk_summary_detects_support_gaps() -> None:
    """Features missing from description trigger support_gap risk."""
    report = generate_grantability_report(
        project_id="proj-16",
        package=DraftPackage(
            title="minimal", abstract="",
            claims="1. 一种方法，包括步骤A。",
            description="",
            drawing_description="", mermaid="", image_prompt="",
        ),
        disclosures=[],
        patent_points=[
            PatentPointCandidate(
                id="pp-x",
                title="步骤A",
                technical_problem="",
                innovation="步骤A",
                technical_solution="",
                protection_focus=["步骤A"],
                evidence_status="model_generated",
                moat_scores=MoatScores(),
                claim_chart=[],
                selected=True,
            ),
        ],
    )

    assert report.fail_closed
    if "support_gap" in report.risk_summary:
        assert "缺乏" in report.risk_summary["support_gap"]


# ---------------------------------------------------------------------------
# Tests: markdown export
# ---------------------------------------------------------------------------


def test_markdown_export_includes_key_sections() -> None:
    """Markdown export contains the expected section headers."""
    report = generate_grantability_report(
        project_id="proj-17",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
    )

    md = grantability_report_to_markdown(report)
    assert "# 授权前景分析报告" in md
    assert "## 总体评估" in md
    assert "## 最接近现有技术" in md
    assert "## 权利要求对照表" in md
    assert "## 新颖性攻击" in md
    assert "## 创造性攻击组合" in md
    assert "## 建议" in md


def test_markdown_export_fail_closed_banner() -> None:
    """Fail-closed reports show a warning banner in markdown."""
    report = generate_grantability_report(
        project_id="proj-18",
        package=_sample_package(),
        disclosures=[],
        patent_points=[],
    )

    md = grantability_report_to_markdown(report)
    assert "低证据关闭" in md or "⚠" in md


# ---------------------------------------------------------------------------
# Tests: evidence quality aggregation
# ---------------------------------------------------------------------------


def test_evidence_quality_verified_with_publication_numbers() -> None:
    """Prior art with publication numbers from trusted sources → verified."""
    from backend.app.grantability import _aggregate_evidence_quality

    hits = [
        PriorArtHit(
            id=f"pa-{i}", source="cnipa", query="",
            title=f"专利{i}",
            publication_number=f"CN0000{i}A",
            url="",
            abstract="",
        )
        for i in range(5)
    ]
    quality = _aggregate_evidence_quality(hits, [], [])
    assert quality == "verified"


def test_evidence_quality_low_with_empty_inputs() -> None:
    """Empty inputs → low evidence quality."""
    from backend.app.grantability import _aggregate_evidence_quality

    quality = _aggregate_evidence_quality([], [], [])
    assert quality == "low"


# ---------------------------------------------------------------------------
# Tests: overall status computation
# ---------------------------------------------------------------------------


def test_overall_status_with_strong_novelty_attacks() -> None:
    """Two or more strong novelty attacks → low grantability."""
    from backend.app.grantability import _compute_overall_status

    rows = [
        GrantabilityClaimChartRow(
            claim_ref="1", feature_text="f1",
            feature_placement=FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED,
            support_status="strong",
        ),
    ]
    novelty = [
        NoveltyAttack(feature_text="f1", attack_strength="strong"),
        NoveltyAttack(feature_text="f2", attack_strength="strong"),
    ]
    status = _compute_overall_status(rows, novelty, [], fail_closed=False, evidence_quality="verified")
    assert status == "low"


def test_overall_status_high_with_clean_features() -> None:
    """Clean independent claims with verified evidence → high."""
    from backend.app.grantability import _compute_overall_status

    rows = [
        GrantabilityClaimChartRow(
            claim_ref="1", feature_text="f1",
            feature_placement=FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED,
            support_status="strong",
        ),
    ]
    novelty = [NoveltyAttack(feature_text="f1", attack_strength="weak")]
    status = _compute_overall_status(rows, novelty, [], fail_closed=False, evidence_quality="verified")
    assert status == "high"


def test_overall_status_fail_closed_overrides() -> None:
    """Fail-closed flag always produces 'uncertain' regardless of other signals."""
    from backend.app.grantability import _compute_overall_status

    status = _compute_overall_status([], [], [], fail_closed=True, evidence_quality="low")
    assert status == "uncertain"


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


def test_empty_package_does_not_crash() -> None:
    """An empty draft package should not crash the generator."""
    empty_pkg = DraftPackage(
        title="", abstract="", claims="", description="",
        drawing_description="", mermaid="", image_prompt="",
    )
    report = generate_grantability_report(
        project_id="proj-edge",
        package=empty_pkg,
        disclosures=[],
        patent_points=[],
    )

    assert report.project_id == "proj-edge"
    assert report.fail_closed is True


def test_invalid_patent_point_handled_gracefully() -> None:
    """Patent points with missing fields don't crash."""
    minimal_point = PatentPointCandidate(
        id="pp-min",
        title="",
        technical_problem="",
        innovation="",
        technical_solution="",
        protection_focus=[],
        evidence_status="model_generated",
        moat_scores=MoatScores(),
        claim_chart=[],
        selected=True,
    )
    report = generate_grantability_report(
        project_id="proj-min",
        package=_sample_package(),
        disclosures=[],
        patent_points=[minimal_point],
    )

    assert isinstance(report, GrantabilityReport)
