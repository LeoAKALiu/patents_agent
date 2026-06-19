import pytest
from fastapi.testclient import TestClient

from backend.app.post_draft_repair import (
    apply_section_patch,
    create_repair_patch_payload,
    infer_target_section,
    locate_issue_anchor,
    normalize_post_draft_issues,
    validate_repair_patch_text,
)
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app, _repair_patch_store
from backend.app.schemas import DraftPackage, DraftRepairPatch, DraftRepairPatchCreate


def test_infer_target_section_from_chinese_messages():
    assert infer_target_section("标题存在重复词汇方法方法") == "title"
    assert infer_target_section("权利要求6末尾残留内部审查备注") == "claims"
    assert infer_target_section("说明书有益效果使用颠覆") == "description"
    assert infer_target_section("附图说明中图1缺少说明") == "drawing_description"
    assert infer_target_section("摘要缺少关键术语定义") == "abstract"
    assert infer_target_section("一段无关文本") == "unknown"
    assert infer_target_section(None) == "unknown"
    assert infer_target_section("") == "unknown"


def test_locate_issue_anchor_matches_snippet_in_section():
    sections = {
        "title": "一种基于城市体检指标置信度的无人机主动采集方法方法",
        "abstract": "",
        "claims": "1. 一种方法。\n*(注：内部备注)**",
        "description": "本发明颠覆了固定航线模式。",
        "drawing_description": "",
    }
    anchor = locate_issue_anchor(
        sections,
        target_section="claims",
        snippet="注：内部备注",
    )
    assert anchor["type"] == "text"
    assert anchor["section"] == "claims"
    assert anchor["start"] >= 0
    assert anchor["end"] > anchor["start"]
    assert anchor["snippet"] == "注：内部备注"


def test_locate_issue_anchor_falls_back_to_contamination_terms():
    sections = {
        "title": "",
        "abstract": "",
        "claims": "",
        "description": "好的，根据交底书撰写说明书。",
        "drawing_description": "",
    }
    # Explicit targets stay within their own section instead of jumping to a
    # contamination term in a different draft section.
    anchor = locate_issue_anchor(
        sections,
        target_section="claims",
        snippet="该方法使用了",
    )
    assert anchor["type"] == "section"
    assert anchor["section"] == "claims"


def test_locate_issue_anchor_can_search_all_sections_for_unknown_target():
    sections = {
        "title": "",
        "abstract": "",
        "claims": "",
        "description": "好的，根据交底书撰写说明书。",
        "drawing_description": "",
    }
    anchor = locate_issue_anchor(
        sections,
        target_section="unknown",
        snippet="该方法使用了",
    )
    assert anchor["type"] == "text"
    assert anchor["section"] == "description"
    assert "好的，根据" in anchor["snippet"]


def test_locate_issue_anchor_falls_back_to_section_anchor():
    sections = {
        "title": "一种方法",
        "abstract": "",
        "claims": "1. 权利要求内容。",
        "description": "说明书内容。",
        "drawing_description": "",
    }
    anchor = locate_issue_anchor(
        sections,
        target_section="claims",
        snippet="这段文字不在任何section中",
    )
    assert anchor["type"] == "section"
    assert anchor["section"] == "claims"
    assert anchor["start"] is None
    assert anchor["end"] is None


def test_locate_issue_anchor_missing_for_unknown_target():
    sections = {
        "title": "",
        "abstract": "",
        "claims": "",
        "description": "",
        "drawing_description": "",
    }
    anchor = locate_issue_anchor(
        sections,
        target_section="unknown",
        snippet="某段文字",
    )
    assert anchor["type"] == "missing"
    assert anchor["section"] == "unknown"


def test_normalize_post_draft_issues_falls_back_to_section_anchor():
    review = {
        "blocking_issues": ["说明书具体实施方式缺少后验更新公式"],
        "contamination_hits": [],
        "rewrite_suggestions": [],
    }
    sections = {
        "title": "",
        "abstract": "",
        "claims": "",
        "description": "具体实施方式。",
        "drawing_description": "",
    }
    issues = normalize_post_draft_issues(review, sections)
    assert len(issues) == 1
    assert issues[0]["kind"] == "blocking"
    assert issues[0]["target_section"] == "description"
    assert issues[0]["anchor"]["type"] == "section"


def test_normalize_post_draft_issues_from_all_kinds():
    review = {
        "blocking_issues": ["标题存在重复词汇方法方法"],
        "contamination_hits": ["好的，根据交底书撰写"],
        "rewrite_suggestions": ["建议补充实施例"],
    }
    sections = {
        "title": "一种基于城市体检指标置信度的无人机主动采集方法方法",
        "abstract": "摘要",
        "claims": "好的，根据交底书撰写权利要求。",
        "description": "说明书。",
        "drawing_description": "",
    }
    issues = normalize_post_draft_issues(review, sections)
    assert len(issues) == 3
    kinds = {issue["kind"] for issue in issues}
    assert kinds == {"blocking", "hit", "suggestion"}

    blocking = next(i for i in issues if i["kind"] == "blocking")
    assert blocking["severity"] == "critical"
    assert blocking["status"] == "open"
    assert blocking["target_section"] == "title"
    assert blocking["anchor"]["type"] == "text"
    assert blocking["anchor"]["snippet"] == "方法方法"
    assert "id" in blocking

    hit = next(i for i in issues if i["kind"] == "hit")
    assert hit["severity"] == "high"
    assert hit["message"] == "好的，根据交底书撰写"

    suggestion = next(i for i in issues if i["kind"] == "suggestion")
    assert suggestion["severity"] == "medium"
    assert suggestion["message"] == "建议补充实施例"


def test_normalize_post_draft_issues_unanchored():
    review = {
        "blocking_issues": [],
        "contamination_hits": [],
        "rewrite_suggestions": ["某段完全找不到的文本"],
    }
    sections = {
        "title": "",
        "abstract": "",
        "claims": "",
        "description": "",
        "drawing_description": "",
    }
    issues = normalize_post_draft_issues(review, sections)
    assert len(issues) == 1
    assert issues[0]["anchor"]["type"] == "missing"
    assert issues[0]["status"] == "unanchored"


def test_normalize_contamination_hits_with_dict_payload():
    """Contamination hits can be dicts with snippet/content fields."""
    review = {
        "blocking_issues": [],
        "contamination_hits": [
            {"content": "待验证的段落", "snippet": "待验证"},
        ],
        "rewrite_suggestions": [],
    }
    sections = {
        "title": "",
        "abstract": "",
        "claims": "待验证的段落出现在此处。",
        "description": "",
        "drawing_description": "",
    }
    issues = normalize_post_draft_issues(review, sections)
    assert len(issues) == 1
    assert issues[0]["kind"] == "hit"
    assert issues[0]["snippet"] == "待验证"


def test_repair_session_endpoint_returns_session(tmp_path):
    """Integration test: GET repair-session returns structured issue anchors."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="一种基于城市体检指标置信度的无人机主动采集方法方法",
            claims="好的，根据您提供的交底书，权利要求1描述了一种旧的方法。\n*(注：内部备注)**",
            description="本发明颠覆了固定航线模式。",
        ),
    )
    compile_run = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert compile_run["status"] == "completed"

    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["status"] == "completed"
    assert review["export_allowed"] is False

    response = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-session"
    )
    assert response.status_code == 200
    session = response.json()
    assert session["project_id"] == project_id
    assert session["review_run_id"] == review["id"]
    assert session["draft_package_hash"] == review["draft_package_hash"]
    assert session["current_draft_hash"] is not None
    assert session["stale"] is False
    assert len(session["issues"]) > 0
    suggestion_messages = {issue["message"] for issue in session["issues"] if issue["kind"] == "suggestion"}
    assert "替换为干净权利要求。" in suggestion_messages
    assert "删除重复词汇。" in suggestion_messages
    assert "补充量化实施例。" in suggestion_messages
    assert "修复 blocking 后重新会审。" in suggestion_messages
    assert set(session["sections"].keys()) == {
        "title", "abstract", "claims", "description", "drawing_description",
    }

    # Check issue structure
    for issue in session["issues"]:
        assert "id" in issue
        assert issue["kind"] in ("blocking", "hit", "suggestion")
        assert issue["severity"] in ("critical", "high", "medium", "low")
        assert issue["anchor"]["type"] in ("text", "section", "missing")
        assert issue["target_section"] in (
            "title", "abstract", "claims", "description", "drawing_description", "unknown",
        )


def test_repair_session_404_for_missing_review(tmp_path):
    """GET repair-session on a nonexistent review run returns 404."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(client, _package())

    response = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/nonexistent/repair-session"
    )
    assert response.status_code == 404


def test_repair_session_404_for_missing_project(tmp_path):
    """GET repair-session on a nonexistent project returns 404."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))

    response = client.get(
        "/api/projects/nonexistent/post-draft-reviews/some-run/repair-session"
    )
    assert response.status_code == 404


def test_repair_session_stale_when_hash_mismatches(tmp_path):
    """Stale flag is true when the review hash doesn't match the current draft hash."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(client, _package())

    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()

    # Mutate the package so the current draft hash changes
    mutated = _package(title="修改后的标题")
    client.app.state.store.update_project_package(project_id, mutated)

    response = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-session"
    )
    assert response.status_code == 200
    session = response.json()
    assert session["stale"] is True
    assert session["draft_package_hash"] != session["current_draft_hash"]


def test_repair_session_404_when_no_package(tmp_path):
    """GET repair-session returns 404 when project has no draft package."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "无初稿项目", "draft_text": "测试。",
              "technical_solution": "一种方法。"},
    ).json()["id"]

    response = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/some-run/repair-session"
    )
    assert response.status_code == 404


def _create_project_with_package(client: TestClient, package: DraftPackage) -> str:
    project_id = client.post(
        "/api/projects",
        json={"name": "修复会审测试", "draft_text": "一种城市体检指标驱动无人机采集方法。",
              "technical_solution": "基于置信度生成采集任务。"},
    ).json()["id"]
    client.app.state.store.update_project_package(project_id, package)
    return project_id


def _package(**overrides) -> DraftPackage:
    data = {
        "title": "一种城市体检指标驱动无人机主动采集方法",
        "abstract": "本发明公开了一种多模态无人机主动采集方法。",
        "claims": "1. 一种方法，包括根据城市体检指标置信度增益生成无人机任务包。",
        "description": "本发明涉及无人机任务规划技术领域，说明书包括贡献矩阵和后验更新流程。",
        "drawing_description": "图1为系统流程图。",
        "mermaid": "",
        "image_prompt": "",
        "review_findings": [],
        "citations": [],
        "generation_logs": [],
    }
    data.update(overrides)
    return DraftPackage(**data)


def _repair_session_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": """
{
  "role": "claims_reviewer",
  "status": "blocked",
  "blocking_issues": ["权利要求1含内部引导语 好的，根据"],
  "contamination_hits": ["好的，根据", "注：内部备注"],
  "rewrite_suggestions": ["替换为干净权利要求。"],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_spec_cleaner": """
{
  "role": "spec_cleaner",
  "status": "blocked",
  "blocking_issues": ["标题存在重复词汇方法方法"],
  "contamination_hits": ["方法方法"],
  "rewrite_suggestions": ["删除重复词汇。"],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_technical_hardness": """
{
  "role": "technical_hardness",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": ["补充量化实施例。"],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_chair_synthesis": """
{
  "status": "blocked",
  "export_allowed": false,
  "blocking_issues": ["标题存在重复词汇方法方法", "权利要求1含内部引导语 好的，根据"],
  "contamination_hits": ["好的，根据", "方法方法", "注：内部备注"],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": [],
  "next_actions": ["修复 blocking 后重新会审。"]
}
""",
        }
    )


# --- PR3: single-issue AI patch lifecycle tests ------------------------------


def test_validate_repair_patch_text_rejects_unsafe_terms():
    """validate_repair_patch_text flags known internal/contamination markers."""
    assert validate_repair_patch_text("安全文字") == []
    assert "注：" in validate_repair_patch_text("注：内部备注")
    assert "待验证" in validate_repair_patch_text("待验证的段落")
    assert "主席" in validate_repair_patch_text("主席修订补强")
    assert "补充实施方式" in validate_repair_patch_text("补充实施方式段落")
    assert "需补充" in validate_repair_patch_text("需补充某些材料")
    assert "提交前补充" in validate_repair_patch_text("需在提交前补充")
    assert "{\"action\"" in validate_repair_patch_text('{"action": "delete"}')
    assert "\"patched\"" in validate_repair_patch_text('包含"patched"字段的 JSON')


def test_apply_section_patch_replaces_original():
    """apply_section_patch replaces the first occurrence of original text."""
    section = "原标题方法方法存在重复"
    result = apply_section_patch(section, "方法方法", "方法")
    assert result == "原标题方法存在重复"


def test_apply_section_patch_raises_when_original_not_found():
    """apply_section_patch raises ValueError when original text is absent."""
    with pytest.raises(ValueError, match="no longer present"):
        apply_section_patch("一些文字", "不存在的原文", "替换")


def test_create_repair_patch_payload_proposed():
    """A clean selected text produces a proposed patch after deterministic cleaning."""
    payload = create_repair_patch_payload(
        issue_id="blocking-abc",
        target_section="title",
        draft_package_hash="h1",
        selected_text="方法方法颠覆",
        nearby_context=None,
    )
    assert payload["id"].startswith("patch-")
    assert payload["issue_id"] == "blocking-abc"
    assert payload["status"] == "proposed"
    assert payload["original"] == "方法方法颠覆"
    assert "方法" in payload["patched"]
    assert "方法方法" not in payload["patched"]
    assert payload["risk_notes"] == []
    assert payload["draft_package_hash"] == "h1"


def test_create_repair_patch_payload_allows_cleaned_source_contamination():
    payload = create_repair_patch_payload(
        issue_id="blocking-clean-source",
        target_section="claims",
        draft_package_hash="h1",
        selected_text="好的，根据交底书撰写权利要求。",
        nearby_context=None,
    )
    assert payload["status"] == "proposed"
    assert "好的，根据" not in payload["patched"]
    assert "好的，根据" in payload["risk_notes"]


def test_create_repair_patch_payload_unsafe():
    """A selected text that can't be fully cleaned produces an unsafe patch."""
    payload = create_repair_patch_payload(
        issue_id="blocking-xyz",
        target_section="description",
        draft_package_hash="h1",
        selected_text='{"action": "delete", "patched": "内部 JSON"}',
        nearby_context=None,
    )
    assert payload["status"] == "unsafe"
    assert len(payload["risk_notes"]) > 0


def test_create_repair_patch_endpoint(tmp_path):
    """POST repair-patches creates a deterministic patch for a known issue."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="一种基于城市体检指标置信度的无人机主动采集方法方法",
            claims="好的，根据您提供的交底书，权利要求1描述了一种旧的方法。\n*(注：内部备注)**",
            description="本发明颠覆了固定航线模式。",
        ),
    )
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    session = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-session"
    ).json()

    # Find a blocking issue for the title
    title_issues = [i for i in session["issues"] if i["kind"] == "blocking" and i["target_section"] == "title"]
    assert len(title_issues) > 0
    issue_id = title_issues[0]["id"]

    payload = DraftRepairPatchCreate(
        issue_id=issue_id,
        draft_package_hash=session["current_draft_hash"],
        target_section="title",
        selected_text="方法方法",
        nearby_context=None,
    )
    response = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches",
        json=payload.model_dump(),
    )
    assert response.status_code == 200
    patch = response.json()
    assert patch["issue_id"] == issue_id
    assert patch["project_id"] == project_id
    assert patch["review_run_id"] == review["id"]
    assert patch["status"] == "proposed"
    assert patch["target_section"] == "title"
    assert patch["original"] == "方法方法"


def test_repair_patch_create_422_for_unsafe_text(tmp_path):
    """POST repair-patches returns 422 when selected_text is contaminated beyond cleaning."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="一种方法",
            claims="1. 权利要求。",
            description="注：待验证补充实施方式",
        ),
    )
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    session = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-session"
    ).json()

    blocking_issues = [i for i in session["issues"] if i["kind"] == "blocking"]
    assert blocking_issues
    issue_id = blocking_issues[0]["id"]

    payload = DraftRepairPatchCreate(
        issue_id=issue_id,
        draft_package_hash=session["current_draft_hash"],
        target_section="description",
        selected_text='{"action": "replace", "patched": "内部 JSON"}',
        nearby_context=None,
    )
    response = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches",
        json=payload.model_dump(),
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "unsafe" in detail.lower() or "不" in detail


def test_repair_patch_create_409_when_review_run_is_stale_even_with_current_hash(tmp_path):
    """A stale review run cannot mint a patch by sending the latest draft hash."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="一种基于城市体检指标置信度的无人机主动采集方法方法",
            claims="好的，根据交底书撰写权利要求。",
        ),
    )
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()

    mutated = _package(
        title="一种基于城市体检指标置信度的无人机主动采集方法方法",
        abstract="本发明公开了一种已经人工修改过的摘要。",
        claims="好的，根据交底书撰写权利要求。",
    )
    client.app.state.store.update_project_package(project_id, mutated)

    session = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-session"
    ).json()
    assert session["stale"] is True
    current_hash = session["current_draft_hash"]
    title_issues = [i for i in session["issues"] if i["kind"] == "blocking" and i["target_section"] == "title"]
    assert title_issues

    payload = DraftRepairPatchCreate(
        issue_id=title_issues[0]["id"],
        draft_package_hash=current_hash,
        target_section="title",
        selected_text="方法方法",
    )
    response = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches",
        json=payload.model_dump(),
    )

    assert response.status_code == 409
    assert "stale" in response.json()["detail"].lower()


def test_repair_patch_apply_409_when_stale(tmp_path):
    """POST apply returns 409 when the draft hash has changed since patch creation."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="一种基于城市体检指标置信度的无人机主动采集方法方法",
            claims="好的，根据交底书撰写权利要求。",
        ),
    )
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    session = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-session"
    ).json()

    title_issues = [i for i in session["issues"] if i["kind"] == "blocking" and i["target_section"] == "title"]
    assert title_issues
    issue_id = title_issues[0]["id"]

    # Create patch against current draft
    create_payload = DraftRepairPatchCreate(
        issue_id=issue_id,
        draft_package_hash=session["current_draft_hash"],
        target_section="title",
        selected_text="方法方法",
    )
    patch_resp = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches",
        json=create_payload.model_dump(),
    )
    assert patch_resp.status_code == 200
    patch = patch_resp.json()
    patch_id = patch["id"]

    # Mutate the package to change the draft hash
    mutated = _package(title="完全不同的新标题")
    client.app.state.store.update_project_package(project_id, mutated)

    # Apply should fail with 409 because the patch is stale
    apply_resp = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches/{patch_id}/apply",
    )
    assert apply_resp.status_code == 409


def test_repair_patch_apply_409_when_review_run_is_stale_even_with_current_hash_patch(tmp_path):
    """Apply re-checks the review-run hash, not only the stored patch hash."""
    _repair_patch_store().clear()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="一种基于城市体检指标置信度的无人机主动采集方法方法",
            claims="好的，根据交底书撰写权利要求。",
        ),
    )
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()

    mutated = _package(
        title="一种基于城市体检指标置信度的无人机主动采集方法方法",
        abstract="本发明公开了一种已经人工修改过的摘要。",
        claims="好的，根据交底书撰写权利要求。",
    )
    client.app.state.store.update_project_package(project_id, mutated)
    current_hash = client.get(f"/api/projects/{project_id}/post-draft-reviews").json()["current_draft_hash"]

    patch = DraftRepairPatch(
        id="patch-stale-review-current-hash",
        issue_id="blocking-manual",
        project_id=project_id,
        review_run_id=review["id"],
        status="proposed",
        target_section="title",
        original="方法方法",
        patched="方法",
        diff_summary="test patch",
        risk_notes=[],
        draft_package_hash=current_hash,
    )
    _repair_patch_store()[patch.id] = patch

    response = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches/{patch.id}/apply",
    )

    assert response.status_code == 409
    assert "stale" in response.json()["detail"].lower()


def test_repair_patch_apply_writes_through_package(tmp_path):
    """POST apply writes safe patch into the draft package, changing its hash."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_repair_session_llm(), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="一种基于城市体检指标置信度的无人机主动采集方法方法",
            claims="好的，根据交底书撰写权利要求。",
        ),
    )
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    session = client.get(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-session"
    ).json()

    title_issues = [i for i in session["issues"] if i["kind"] == "blocking" and i["target_section"] == "title"]
    assert title_issues
    issue_id = title_issues[0]["id"]

    create_payload = DraftRepairPatchCreate(
        issue_id=issue_id,
        draft_package_hash=session["current_draft_hash"],
        target_section="title",
        selected_text="方法方法",
    )
    patch_resp = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches",
        json=create_payload.model_dump(),
    )
    assert patch_resp.status_code == 200
    patch = patch_resp.json()
    patch_id = patch["id"]

    apply_resp = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches/{patch_id}/apply",
    )
    assert apply_resp.status_code == 200
    result = apply_resp.json()
    assert "package" in result
    assert result["package"]["title"] != "一种基于城市体检指标置信度的无人机主动采集方法方法"
    assert "方法方法" not in result["package"]["title"]
    assert result["current_draft_hash"] is not None

    second_apply = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-patches/{patch_id}/apply",
    )
    assert second_apply.status_code == 409
