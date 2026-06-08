import hashlib

from backend.app.draft_completion import completion_run_to_markdown, run_draft_completion
from backend.app.schemas import (
    ClaimSupportMatrixRow,
    ClaimDefenseWorksheet,
    CompletionIssue,
    CompletionScoreCard,
    CompletionTask,
    DraftPackage,
    DraftCompletionRun,
    FeatureRecord,
    FilingReadinessIssue,
    FilingReadinessReport,
    PatentPointCandidate,
    ProposedPatch,
)


def test_draft_completion_models_capture_support_and_patch_state():
    issue = CompletionIssue(
        id="i1",
        category="claim_support_gap",
        severity="high",
        target="claim",
        source_refs=["claim:1"],
        message="核心权利要求特征缺少说明书支撑。",
        why_it_matters="缺少支撑会提高充分公开和支持性风险。",
        suggested_action="补充数据结构和实施例。",
        blocks_submission=True,
    )
    task = CompletionTask(
        id="t1",
        issue_id="i1",
        task_type="add_data_structure",
        priority=100,
        input_refs=["claim:1"],
        expected_output="BillTraceRecord 数据结构",
        draft_section_target="description",
    )
    patch = ProposedPatch(
        id="p1",
        task_id="t1",
        target_section="description",
        patch_kind="insert",
        before_text="",
        after_text="BillTraceRecord包括item_id、ifc_guid_list和confidence_score。",
        rationale="补充清单回链的可计算表示。",
        risk_delta="降低充分公开风险。",
        evidence_refs=["task:t1"],
        can_enter_official_draft=True,
    )
    row = ClaimSupportMatrixRow(
        claim_ref="1",
        feature_text="工程量清单回链",
        feature_classification="core_combo",
        description_refs=[],
        evidence_status="feasible_unverified",
        completion_status="missing",
    )
    run = DraftCompletionRun(
        id="r1",
        project_id="project-1",
        snapshot_hash="hash-1",
        status="completed",
        issues=[issue],
        tasks=[task],
        patches=[patch],
        support_matrix=[row],
        scorecard=CompletionScoreCard(
            authorization_stability=60,
            protection_scope=78,
            support_strength=45,
            prior_art_distinction=65,
            filing_maturity=55,
            official_hygiene=80,
            overall=64,
        ),
    )

    assert run.issues[0].category == "claim_support_gap"
    assert run.tasks[0].status == "open"
    assert run.patches[0].status == "proposed"
    assert run.support_matrix[0].completion_status == "missing"
    assert run.scorecard.overall == 64


def _completion_package() -> DraftPackage:
    return DraftPackage(
        title="一种既有建筑外立面逆建模与工程量清单生成方法",
        abstract="本发明公开一种外立面逆建模方法。",
        claims=(
            "1. 一种既有建筑外立面逆建模与工程量清单生成方法，其特征在于，"
            "生成IfcRelVoidsElement洞口扣减关系，建立工程量清单回链，并基于GUID依赖图进行增量更新。"
        ),
        description="本实施例获取点云和多视角影像，生成IFC模型，并输出工程量清单。",
        drawing_description="图1为方法流程图。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="黑白线稿 prompt",
        review_findings=[],
        citations=[],
        generation_logs=["deliberation: no completed multi-agent deliberation injected"],
    )


def test_completion_engine_finds_support_gaps_and_patch_suggestions():
    point = PatentPointCandidate(
        id="p1",
        title="IFC洞口扣减与清单回链",
        technical_problem="洞口扣减与工程量清单缺少可追溯关系。",
        innovation="建立IFC洞口扣减拓扑与清单回链。",
        technical_solution="生成IfcRelVoidsElement并建立清单回链。",
        evidence_status="feasible_unverified",
    )

    run = run_draft_completion(
        project_id="project-1",
        package=_completion_package(),
        filing_reports=[],
        worksheets=[],
        patent_points=[point],
        disclosures=[],
        materials=[],
    )

    categories = {issue.category for issue in run.issues}
    task_outputs = "\n".join(task.expected_output for task in run.tasks)
    patch_text = "\n".join(patch.after_text for patch in run.patches)
    assert "claim_support_gap" in categories
    assert "format_pollution" in categories
    assert "权利要求特征" in task_outputs
    assert "伪代码" in patch_text
    assert run.support_matrix[0].completion_status == "partial"
    assert run.scorecard.support_strength < 70


def test_completion_report_is_sidecar_and_mentions_formal_export_gates():
    run = run_draft_completion(
        project_id="project-1",
        package=_completion_package(),
        filing_reports=[],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
    )
    markdown = completion_run_to_markdown(run)

    assert "# DRAFT_COMPLETION_REPORT" in markdown
    assert "正式导出仍需通过正式稿编译和成稿后多 Agent 会审" in markdown
    assert "## Scorecard" in markdown
    assert "## Proposed Patches" in markdown


def test_completion_maps_claims_readiness_issue_to_claim_target():
    package = _completion_package()
    report = FilingReadinessReport(
        id="fr1",
        project_id="project-1",
        draft_package_hash=hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest(),
        status="warning",
        issues=[
            FilingReadinessIssue(
                category="format_pollution",
                severity="medium",
                target="claims",
                matched_text="```",
                message="权利要求包含格式污染。",
                suggestion="删除格式标记。",
                can_auto_clean=True,
            )
        ],
    )

    run = run_draft_completion(
        project_id="project-1",
        package=package,
        filing_reports=[report],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
    )

    issue = next(issue for issue in run.issues if issue.source_refs == ["filing_readiness:claims"])
    assert issue.target == "claim"
    assert run.scorecard.official_hygiene < 100


def test_completion_support_matrix_preserves_formula_refs():
    package = _completion_package().model_copy(
        update={
            "claims": (
                "1. 一种面积计算方法，其特征在于，将多视角相机射线反投至基面平面，"
                "并使用面积公式计算扣减面积。"
            ),
            "description": (
                "本实施例将多视角相机射线反投至基面平面，"
                "并以面积公式 A = W * H 计算墙体扣减面积。"
            )
        }
    )

    run = run_draft_completion(
        project_id="project-1",
        package=package,
        filing_reports=[],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
    )

    row = next(row for row in run.support_matrix if "多视角相机射线反投" in row.feature_text)
    assert row.formula_refs
    assert row.completion_status == "supported"


def test_completion_run_ignores_stale_readiness_and_regenerates_worksheet():
    package_a = _completion_package()
    package_b = _completion_package().model_copy(
        update={
            "title": "一种构件状态标记方法",
            "claims": "1. 一种构件状态标记方法，其特征在于，包括颜色标记。\n```",
            "description": "本实施例包括颜色标记。",
        }
    )
    stale_report = FilingReadinessReport(
        id="old-readiness",
        project_id="project-1",
        draft_package_hash=hashlib.sha256(package_a.model_dump_json().encode("utf-8")).hexdigest(),
        status="warning",
        issues=[
            FilingReadinessIssue(
                category="format_pollution",
                severity="high",
                target="claims",
                matched_text="OLD",
                message="旧稿报告污染不应进入新完成度运行。",
                suggestion="忽略旧报告。",
            )
        ],
    )
    stale_worksheet = ClaimDefenseWorksheet(
        id="old-worksheet",
        project_id="project-1",
        feature_records=[
            FeatureRecord(
                feature_id="old-feature",
                text="旧工作表特征：工程量清单回链",
                classification="core_combo",
                claim_refs=["1"],
            )
        ],
    )

    run = run_draft_completion(
        project_id="project-1",
        package=package_b,
        filing_reports=[stale_report],
        worksheets=[stale_worksheet],
        patent_points=[],
        disclosures=[],
        materials=[],
    )

    assert all("旧稿报告污染" not in issue.message for issue in run.issues)
    assert any(issue.source_refs == ["filing_readiness:claims"] for issue in run.issues)
    feature_texts = [row.feature_text for row in run.support_matrix]
    assert any("颜色标记" in text for text in feature_texts)
    assert all("旧工作表特征" not in text for text in feature_texts)


def test_completion_support_matrix_does_not_apply_unrelated_formula_globally():
    package = _completion_package().model_copy(
        update={
            "claims": "1. 一种构件状态标记方法，其特征在于，包括颜色标记。",
            "description": "本实施例包括颜色标记。另有面积公式 A = W * H 用于背景统计。",
        }
    )

    run = run_draft_completion(
        project_id="project-1",
        package=package,
        filing_reports=[],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
    )

    row = next(row for row in run.support_matrix if "颜色标记" in row.feature_text)
    assert row.description_refs
    assert row.formula_refs == []
    assert row.completion_status == "partial"


def test_completion_scorecard_uses_generic_examiner_rules_instead_of_domain_keywords():
    ifc_package = _completion_package().model_copy(
        update={
            "claims": (
                "1. 一种数据处理方法，其特征在于，包括接收输入数据、"
                "生成IfcRelVoidsElement记录并输出处理结果。"
            ),
            "description": (
                "本实施例接收输入数据。针对生成IfcRelVoidsElement记录，系统执行伪代码："
                "步骤S1获取输入数据，步骤S2生成中间状态记录，步骤S3输出处理结果。"
                "所述中间状态记录为数据结构，包括input_data和output_result字段。"
            ),
        }
    )
    neutral_package = _completion_package().model_copy(
        update={
            "title": "一种数据处理与结果回链方法",
            "claims": (
                "1. 一种数据处理方法，其特征在于，包括接收输入数据、"
                "生成对象关系记录并输出处理结果。"
            ),
            "description": (
                "本实施例接收输入数据。针对生成对象关系记录，系统执行伪代码："
                "步骤S1获取输入数据，步骤S2生成中间状态记录，步骤S3输出处理结果。"
                "所述中间状态记录为数据结构，包括input_data和output_result字段。"
            ),
        }
    )

    ifc_run = run_draft_completion(
        project_id="project-ifc",
        package=ifc_package,
        filing_reports=[],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
    )
    neutral_run = run_draft_completion(
        project_id="project-neutral",
        package=neutral_package,
        filing_reports=[],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
    )

    assert ifc_run.scorecard.protection_scope == neutral_run.scorecard.protection_scope
    assert ifc_run.scorecard.prior_art_distinction == neutral_run.scorecard.prior_art_distinction
    assert ifc_run.scorecard.overall == neutral_run.scorecard.overall
