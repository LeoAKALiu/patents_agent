from backend.app.llm import FakeLLMClient
from backend.app.official_compile import source_draft_hash
from backend.app.schemas import CompletionIssue, CompletionScoreCard, CompletionTask, DraftCompletionRun, ProposedPatch
from backend.app.storage import SQLiteStore
from fastapi.testclient import TestClient

from backend.app.main import _apply_completion_patch, create_app


def _stored_completion_run(project_id: str = "project-1") -> DraftCompletionRun:
    return DraftCompletionRun(
        id="run-1",
        project_id=project_id,
        snapshot_hash="hash-1",
        status="completed",
        issues=[
            CompletionIssue(
                id="issue-1",
                category="claim_support_gap",
                severity="high",
                target="claim",
                source_refs=["claim:1"],
                message="Claim 1 lacks support.",
                why_it_matters="Unsupported claim features reduce filing maturity.",
                suggested_action="Add concrete support for claim 1.",
                blocks_submission=True,
            ),
            CompletionIssue(
                id="issue-2",
                category="format_pollution",
                severity="medium",
                target="export",
                source_refs=["export:mermaid"],
                message="Export field contains internal format text.",
                why_it_matters="Official drafts must not include internal formatting traces.",
                suggested_action="Remove internal format text.",
                blocks_submission=True,
            ),
        ],
        tasks=[
            CompletionTask(
                id="task-1",
                issue_id="issue-1",
                task_type="revise_draft_support",
                priority=100,
                expected_output="Strengthen claim support.",
                draft_section_target="claims",
            ),
            CompletionTask(
                id="task-2",
                issue_id="issue-2",
                task_type="clean_export_trace",
                priority=90,
                expected_output="Remove internal traces.",
                draft_section_target="export",
            ),
        ],
        patches=[
            ProposedPatch(
                id="patch-1",
                task_id="task-1",
                target_section="claims",
                patch_kind="rewrite",
                before_text="old claim text",
                after_text="new claim text",
                rationale="Strengthen claim support.",
                risk_delta="lower",
                evidence_refs=["matrix:claim-1"],
            ),
            ProposedPatch(
                id="patch-2",
                task_id="task-2",
                target_section="export",
                patch_kind="sidecar_only",
                rationale="Remove internal traces.",
                risk_delta="lower",
                evidence_refs=["readiness:issue-2"],
            ),
        ],
        scorecard=CompletionScoreCard(
            authorization_stability=80,
            protection_scope=75,
            support_strength=70,
            prior_art_distinction=65,
            filing_maturity=72,
            official_hygiene=90,
            overall=75,
        ),
    )


def test_store_persists_and_updates_completion_runs(tmp_path):
    db_path = tmp_path / "patents_agent.sqlite3"
    store = SQLiteStore(db_path)
    run = store.create_draft_completion_run(_stored_completion_run())

    assert store.get_draft_completion_run("project-1", run.id) is not None
    assert store.list_draft_completion_runs("project-1")[0].id == "run-1"

    updated = store.update_completion_patch_status("project-1", "run-1", "patch-1", "accepted")
    assert updated is not None
    assert updated.patches[0].status == "accepted"
    assert updated.tasks[0].status == "accepted"

    reloaded = store.get_draft_completion_run("project-1", "run-1")
    assert reloaded is not None
    assert reloaded.patches[0].status == "accepted"
    assert reloaded.tasks[0].status == "accepted"

    reopened = SQLiteStore(db_path)
    persisted = reopened.get_draft_completion_run("project-1", "run-1")
    assert persisted is not None
    assert persisted.patches[0].status == "accepted"
    assert persisted.tasks[0].status == "accepted"

    updated = store.update_completion_patch_status("project-1", "run-1", "missing", "accepted")
    assert updated is None


def _client(tmp_path):
    return TestClient(create_app(data_dir=tmp_path, load_env_file=False))


def test_completion_api_runs_lists_exports_and_updates_patch_status(tmp_path):
    client = _client(tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "name": "外立面逆建模",
            "draft_text": "一种生成IfcRelVoidsElement并建立工程量清单回链的方法。",
        },
    ).json()
    package_response = client.post(f"/api/projects/{project['id']}/generate")
    assert package_response.status_code == 503

    app = client.app
    store = app.state.store
    from backend.app.schemas import DraftPackage

    store.update_project_package(
        project["id"],
        DraftPackage(
            title="一种既有建筑外立面逆建模方法",
            abstract="本发明公开一种外立面逆建模方法。",
            claims="1. 一种方法，其特征在于生成IfcRelVoidsElement并建立工程量清单回链。",
            description="本实施例生成IFC模型。",
            drawing_description="图1为流程图。",
            mermaid="flowchart TD\nA-->B",
            image_prompt="prompt",
            review_findings=[],
            citations=[],
            generation_logs=["deliberation: no completed multi-agent deliberation injected"],
        ),
    )

    run_response = client.post(f"/api/projects/{project['id']}/completion-runs")
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["scorecard"]["overall"] <= 100
    assert run["issues"]

    list_response = client.get(f"/api/projects/{project['id']}/completion-runs")
    assert list_response.status_code == 200
    assert list_response.json()["runs"][0]["id"] == run["id"]

    report_response = client.get(f"/api/projects/{project['id']}/completion-runs/{run['id']}/report.md")
    assert report_response.status_code == 200
    assert "DRAFT_COMPLETION_REPORT" in report_response.text

    generate_response = client.post(f"/api/projects/{project['id']}/completion-runs/{run['id']}/patches/generate")
    assert generate_response.status_code == 200
    assert len(generate_response.json()["patches"]) >= len(run["patches"])

    patch_id = run["patches"][0]["id"]
    accept_response = client.post(f"/api/projects/{project['id']}/completion-runs/{run['id']}/patches/{patch_id}/accept")
    assert accept_response.status_code == 200
    accepted_run = accept_response.json()
    assert accepted_run["scorecard_baseline"] == run["scorecard"]
    assert accepted_run["scorecard"]["authorization_stability"] > run["scorecard"]["authorization_stability"]
    assert accepted_run["scorecard"]["protection_scope"] > run["scorecard"]["protection_scope"]
    assert accepted_run["scorecard"]["filing_maturity"] > run["scorecard"]["filing_maturity"]
    accepted_patch = next(patch for patch in accepted_run["patches"] if patch["id"] == patch_id)
    assert accepted_patch["status"] == "accepted"
    assert any(
        task["id"] == accepted_patch["task_id"] and task["status"] == "accepted"
        for task in accepted_run["tasks"]
    )

    reject_response = client.post(f"/api/projects/{project['id']}/completion-runs/{run['id']}/patches/{patch_id}/reject")
    assert reject_response.status_code == 200
    rejected_run = reject_response.json()
    rejected_patch = next(patch for patch in rejected_run["patches"] if patch["id"] == patch_id)
    assert rejected_patch["status"] == "rejected"
    assert any(
        task["id"] == rejected_patch["task_id"] and task["status"] == "rejected"
        for task in rejected_run["tasks"]
    )
    assert rejected_run["scorecard"] == run["scorecard"]


def test_accept_all_completion_patches_updates_scores_once(tmp_path):
    client = _client(tmp_path)
    project = client.post(
        "/api/projects",
        json={"name": "批量接受补强", "draft_text": "一种测试方法。"},
    ).json()
    app = client.app
    store = app.state.store
    run = store.create_draft_completion_run(_stored_completion_run(project["id"]))

    response = client.post(f"/api/projects/{run.project_id}/completion-runs/{run.id}/patches/accept-all")

    assert response.status_code == 200
    accepted = response.json()
    assert {patch["status"] for patch in accepted["patches"]} == {"accepted"}
    assert {task["status"] for task in accepted["tasks"]} == {"accepted"}
    assert accepted["scorecard_baseline"] == run.scorecard.model_dump(mode="json")
    assert accepted["scorecard"]["authorization_stability"] > run.scorecard.authorization_stability
    assert accepted["scorecard"]["protection_scope"] > run.scorecard.protection_scope
    assert accepted["scorecard"]["filing_maturity"] > run.scorecard.filing_maturity

    second_response = client.post(f"/api/projects/{run.project_id}/completion-runs/{run.id}/patches/accept-all")
    assert second_response.status_code == 200
    assert second_response.json()["scorecard"] == accepted["scorecard"]


def test_score_improvement_applies_safe_patches_and_re_scores_project(tmp_path):
    client = _client(tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "name": "通用处理流程",
            "draft_text": "一种输入数据处理方法，解决处理结果不可追溯的问题。",
        },
    ).json()
    app = client.app
    store = app.state.store
    from backend.app.schemas import DraftPackage, ProjectMaterial

    store.update_project_package(
        project["id"],
        DraftPackage(
            title="一种输入数据处理方法",
            abstract="本发明公开一种输入数据处理方法。",
            claims="1. 一种输入数据处理方法，其特征在于，包括接收输入数据、生成处理结果并输出控制指令。",
            description="本实施例接收输入数据。",
            drawing_description="图1为流程图。",
            mermaid="flowchart TD\nA-->B",
            image_prompt="prompt",
            review_findings=[],
            citations=[],
            generation_logs=[],
        ),
    )
    store.add_project_material(
        ProjectMaterial(
            id="material-1",
            project_id=project["id"],
            file_name="实验记录.md",
            path="/tmp/material.md",
            file_type="markdown",
            text="接收输入数据、生成处理结果并输出控制指令。",
            status="processed",
        )
    )

    response = client.post(f"/api/projects/{project['id']}/score-improvement", json={"max_rounds": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["before_score"] < payload["after_score"]
    assert payload["accepted_patch_ids"]
    assert any("重新评分" in line for line in payload["logs"])
    # Regression: at most one patch is accepted per round (the round stops after
    # the first applied patch), and applied-patch logs match the accepted ids so
    # stale follow-up patches no longer emit a misleading "未通过安全检查" line.
    assert len(payload["accepted_patch_ids"]) == 1
    applied_logs = [line for line in payload["logs"] if "已应用补丁" in line]
    assert len(applied_logs) == len(payload["accepted_patch_ids"])

    updated_project = client.get(f"/api/projects/{project['id']}").json()
    assert "生成处理结果" in updated_project["package"]["description"]
    assert "伪代码" in updated_project["package"]["description"]


def test_apply_completion_patch_rejects_stale_run_hash():
    from backend.app.schemas import DraftPackage

    package = DraftPackage(
        title="一种输入数据处理方法",
        abstract="本发明公开一种输入数据处理方法。",
        claims="1. 一种方法。",
        description="本实施例接收输入数据。",
        drawing_description="图1为流程图。",
        mermaid="",
        image_prompt="",
    )
    patch = ProposedPatch(
        id="patch-1",
        task_id="task-1",
        target_section="description",
        patch_kind="insert",
        before_text="本实施例接收输入数据。",
        after_text="补充实施例文本。",
        rationale="补强。",
        risk_delta="降低风险。",
        evidence_refs=["E100"],
        can_enter_official_draft=True,
    )

    updated = _apply_completion_patch(package, patch, run_draft_package_hash="stale-hash")

    assert updated == package


def test_apply_completion_patch_rejects_official_safe_patch_without_real_evidence_refs():
    from backend.app.schemas import DraftPackage

    package = DraftPackage(
        title="一种输入数据处理方法",
        abstract="本发明公开一种输入数据处理方法。",
        claims="1. 一种方法。",
        description="本实施例接收输入数据。",
        drawing_description="图1为流程图。",
        mermaid="",
        image_prompt="",
    )
    patch = ProposedPatch(
        id="patch-1",
        task_id="task-1",
        target_section="description",
        patch_kind="insert",
        before_text="本实施例接收输入数据。",
        after_text="补充实施例文本。",
        rationale="补强。",
        risk_delta="降低风险。",
        evidence_refs=["task:task-1", "claim:1"],
        can_enter_official_draft=True,
    )

    updated = _apply_completion_patch(package, patch, run_draft_package_hash=source_draft_hash(package))

    assert updated == package


def test_apply_completion_patch_accepts_verified_patent_point_ref():
    from backend.app.schemas import DraftPackage

    package = DraftPackage(
        title="一种输入数据处理方法",
        abstract="本发明公开一种输入数据处理方法。",
        claims="1. 一种方法。",
        description="本实施例接收输入数据。",
        drawing_description="图1为流程图。",
        mermaid="",
        image_prompt="",
    )
    patch = ProposedPatch(
        id="patch-1",
        task_id="task-1",
        target_section="description",
        patch_kind="insert",
        before_text="本实施例接收输入数据。",
        after_text="补充实施例文本。",
        rationale="补强。",
        risk_delta="降低风险。",
        evidence_refs=["patent_points", "patent_point:verified"],
        can_enter_official_draft=True,
    )

    updated = _apply_completion_patch(package, patch, run_draft_package_hash=source_draft_hash(package))

    assert "补充实施例文本。" in updated.description


def test_score_improvement_invalidates_previous_official_export_gate(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project = client.post(
        "/api/projects",
        json={
            "name": "通用处理流程",
            "draft_text": "一种输入数据处理方法，解决处理结果不可追溯的问题。",
        },
    ).json()
    app = client.app
    store = app.state.store
    from backend.app.schemas import DraftPackage, ProjectMaterial

    store.update_project_package(
        project["id"],
        DraftPackage(
            title="一种输入数据处理方法",
            abstract="本发明公开一种输入数据处理方法。",
            claims="1. 一种输入数据处理方法，其特征在于，包括接收输入数据、生成处理结果并输出控制指令。",
            description="本实施例接收输入数据。",
            drawing_description="图1为流程图。",
            mermaid="",
            image_prompt="",
            review_findings=[],
            citations=[],
            generation_logs=[],
        ),
    )
    store.add_project_material(
        ProjectMaterial(
            id="material-1",
            project_id=project["id"],
            file_name="实验记录.md",
            path="/tmp/material.md",
            file_type="markdown",
            text="接收输入数据、生成处理结果并输出控制指令。",
            status="processed",
        )
    )
    assert client.post(f"/api/projects/{project['id']}/filing-readiness").status_code == 200
    assert client.post(f"/api/projects/{project['id']}/claim-defense-worksheets").status_code == 200
    assert client.post(f"/api/projects/{project['id']}/completion-runs").status_code == 200
    assert client.post(f"/api/projects/{project['id']}/official-compile-runs", json={}).json()["status"] == "completed"
    assert client.post(f"/api/projects/{project['id']}/post-draft-reviews", json={}).json()["export_allowed"] is True
    assert client.get(f"/api/projects/{project['id']}/official-export.md").status_code == 200

    response = client.post(f"/api/projects/{project['id']}/score-improvement", json={"max_rounds": 1})
    assert response.status_code == 200
    assert response.json()["accepted_patch_ids"]

    blocked_export = client.get(f"/api/projects/{project['id']}/official-export.md")
    assert blocked_export.status_code == 409
    assert "current draft" in blocked_export.json()["detail"]


def _review_llm(*, export_allowed: bool) -> FakeLLMClient:
    status = "passed" if export_allowed else "blocked"
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": f"""
{{
  "role": "claims_reviewer",
  "status": "{status}",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}}
""",
            "post_draft_spec_cleaner": f"""
{{
  "role": "spec_cleaner",
  "status": "{status}",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}}
""",
            "post_draft_technical_hardness": f"""
{{
  "role": "technical_hardness",
  "status": "{status}",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}}
""",
            "post_draft_chair_synthesis": f"""
{{
  "status": "{status}",
  "export_allowed": {str(export_allowed).lower()},
  "blocking_issues": [],
  "contamination_hits": [],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": [],
  "next_actions": []
}}
""",
        }
    )
