"""Tests for Content-Disposition header behavior on export endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import _ascii_download_filename, _content_disposition_header, create_app
from backend.app.schemas import (
    DeliberationRun,
    DeliberationStageResult,
    PatentStrategyBrief,
)


# ---------------------------------------------------------------------------
# Unit tests on the helper functions
# ---------------------------------------------------------------------------

def test_content_disposition_header_ascii_english():
    """Plain ASCII filename — both filename and filename*= should match."""
    header = _content_disposition_header("MyProject.docx")
    cd = header["Content-Disposition"]
    assert 'filename="MyProject.docx"' in cd
    assert "filename*=UTF-8''MyProject.docx" in cd
    assert cd.startswith("attachment; ")


def test_content_disposition_header_chinese_name():
    """Chinese project name — filename*= should be percent-encoded, ASCII filename fallback is stripped."""
    header = _content_disposition_header("图像缺陷识别.md")
    cd = header["Content-Disposition"]
    # ASCII fallback: only alphanumeric/punctuation remains — the dot and extension stay
    assert 'filename="download.md"' in cd
    # UTF-8 part: Chinese chars are percent-encoded
    assert "filename*=UTF-8''" in cd
    assert "%" in cd  # percent-encoding present
    assert cd.startswith("attachment; ")


def test_content_disposition_header_empty_after_strip():
    """Fully non-ASCII or empty filename — ASCII fallback becomes 'download'."""
    header = _content_disposition_header("   ")
    cd = header["Content-Disposition"]
    assert 'filename="download"' in cd
    assert "filename*=UTF-8''" in cd


def test_content_disposition_header_path_separators_stripped():
    """Slashes and backslashes replaced with underscores."""
    header = _content_disposition_header("a/b\\c.docx")
    cd = header["Content-Disposition"]
    assert 'filename="a_b_c.docx"' in cd
    assert "filename*=UTF-8''a_b_c.docx" in cd


def test_ascii_download_filename_keeps_alnum_dot_hyphen():
    assert _ascii_download_filename("hello-world_v2.txt") == "hello-world_v2.txt"
    assert _ascii_download_filename("   spaced name .docx  ") == "spaced name .docx"


def test_ascii_download_filename_strips_unicode():
    assert _ascii_download_filename("图像缺陷识别.md") == "download.md"


def test_ascii_download_filename_all_unicode_falls_back():
    assert _ascii_download_filename("识别") == "download"


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

STRICT_PROVIDERS = ["codex", "deepseek", "claude"]


def _minimal_app_with_llm(tmp_path: Path, responses: dict | None = None) -> TestClient:
    llm = FakeLLMClient(responses or {})
    return TestClient(create_app(data_dir=tmp_path, llm_client=llm))


def _create_completed_deliberation(client: TestClient, project_id: str) -> None:
    """Create a fully-completed deliberation run that passes all gates."""
    stages = [
        *[
            DeliberationStageResult(
                phase="opening",
                provider_id=provider,
                label=f"opening {provider}",
                payload={"stance": "ok"},
                status="completed",
            )
            for provider in STRICT_PROVIDERS
        ],
        *[
            DeliberationStageResult(
                phase="pair",
                provider_id="codex",
                label=label,
                payload={"resolved_recommendation": "ok"},
                status="completed",
            )
            for label in [
                "pair codex-vs-deepseek",
                "pair codex-vs-claude",
                "pair deepseek-vs-claude",
            ]
        ],
        DeliberationStageResult(
            phase="chair",
            provider_id="codex",
            label="chair synthesis",
            payload={"summary": "ok"},
            status="completed",
        ),
    ]
    client.app.state.store.create_deliberation_run(
        DeliberationRun(
            id=f"delib-{project_id}",
            project_id=project_id,
            status="completed",
            providers=STRICT_PROVIDERS,
            run_mode="full",
            stage_results=stages,
            strategy_brief=PatentStrategyBrief(
                summary="测试会审策略",
                claim_strategy=["方法独权"],
                description_strategy=["补充实施例"],
                risk_controls=["避免功能性概括"],
                agent_consensus="测试会审通过。",
            ),
            events=["test deliberation completed"],
        )
    )


def _create_project_with_package(client: TestClient) -> str:
    """Create a project, run deliberation + generation, return project_id."""
    project_resp = client.post(
        "/api/projects",
        json={"name": "测试项目", "draft_text": "一种基于AI的专利撰写方法。"},
    )
    assert project_resp.status_code == 200
    project_id = project_resp.json()["id"]

    _create_completed_deliberation(client, project_id)

    gen_resp = client.post(f"/api/projects/{project_id}/generate")
    assert gen_resp.status_code == 200, gen_resp.text
    return project_id


# ---------------------------------------------------------------------------
# Integration tests via the API
# ---------------------------------------------------------------------------

def test_export_docx_has_content_disposition_header(tmp_path: Path):
    client = _minimal_app_with_llm(
        tmp_path,
        {
            "claims": "1. 一种专利撰写方法，其特征在于，包括AI辅助生成。",
            "description": "技术领域\n本发明涉及AI辅助专利撰写技术领域。",
            "abstract": "本发明公开了一种AI辅助专利撰写方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[输入] --> B[生成]",
            "image_prompt": "黑白线稿，展示AI辅助专利撰写流程。",
        },
    )
    project_id = _create_project_with_package(client)

    resp = client.get(f"/api/projects/{project_id}/export.docx")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd.lower() or "filename" in cd.lower()
    assert "filename*=UTF-8''" in cd
    assert ".docx" in cd
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_export_md_has_utf8_filename(tmp_path: Path):
    client = _minimal_app_with_llm(
        tmp_path,
        {
            "claims": "1. 一种专利撰写方法，其特征在于，包括AI辅助生成。",
            "description": "技术领域\n本发明涉及AI辅助专利撰写技术领域。",
            "abstract": "本发明公开了一种AI辅助专利撰写方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[输入] --> B[生成]",
            "image_prompt": "黑白线稿，展示AI辅助专利撰写流程。",
        },
    )
    project_id = _create_project_with_package(client)

    resp = client.get(f"/api/projects/{project_id}/export.md")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "filename*=UTF-8''" in cd
    assert ".md" in cd
    assert resp.headers["content-type"] == "text/markdown; charset=utf-8"


def test_export_mermaid_has_mmd_extension(tmp_path: Path):
    client = _minimal_app_with_llm(
        tmp_path,
        {
            "claims": "1. 一种专利撰写方法，其特征在于，包括AI辅助生成。",
            "description": "技术领域\n本发明涉及AI辅助专利撰写技术领域。",
            "abstract": "本发明公开了一种AI辅助专利撰写方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[输入] --> B[生成]",
            "image_prompt": "黑白线稿，展示AI辅助专利撰写流程。",
        },
    )
    project_id = _create_project_with_package(client)

    resp = client.get(f"/api/projects/{project_id}/diagram.mmd")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert ".mmd" in cd
    assert "filename*=UTF-8''" in cd


def test_export_image_prompt_has_md_extension(tmp_path: Path):
    client = _minimal_app_with_llm(
        tmp_path,
        {
            "claims": "1. 一种专利撰写方法，其特征在于，包括AI辅助生成。",
            "description": "技术领域\n本发明涉及AI辅助专利撰写技术领域。",
            "abstract": "本发明公开了一种AI辅助专利撰写方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[输入] --> B[生成]",
            "image_prompt": "黑白线稿，展示AI辅助专利撰写流程。",
        },
    )
    project_id = _create_project_with_package(client)

    resp = client.get(f"/api/projects/{project_id}/image-prompt.md")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert ".md" in cd
    assert "filename*=UTF-8''" in cd


def test_official_export_blocked_without_compile_and_review(tmp_path: Path):
    """Official export endpoints return 409 when gates are not satisfied."""
    client = _minimal_app_with_llm(
        tmp_path,
        {
            "claims": "1. 一种专利撰写方法，其特征在于，包括AI辅助生成。",
            "description": "技术领域\n本发明涉及AI辅助专利撰写技术领域。",
            "abstract": "本发明公开了一种AI辅助专利撰写方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[输入] --> B[生成]",
            "image_prompt": "黑白线稿，展示AI辅助专利撰写流程。",
        },
    )
    project_id = _create_project_with_package(client)

    # Without compile: blocked
    resp_md = client.get(f"/api/projects/{project_id}/official-export.md")
    assert resp_md.status_code == 409
    assert "compile" in resp_md.json()["detail"].lower()

    resp_docx = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert resp_docx.status_code == 409

    # With compile but without post-draft review: still blocked
    compile_resp = client.post(
        f"/api/projects/{project_id}/official-compile-runs", json={}
    )
    assert compile_resp.status_code == 200

    resp_md = client.get(f"/api/projects/{project_id}/official-export.md")
    assert resp_md.status_code == 409
    assert "review" in resp_md.json()["detail"].lower()


def test_official_export_content_disposition_after_gates(tmp_path: Path):
    """Official export markdown returns proper Content-Disposition after gates pass."""
    responses = {
        "claims": "1. 一种专利撰写方法，其特征在于，包括AI辅助生成。",
        "description": "技术领域\n本发明涉及AI辅助专利撰写技术领域。",
        "abstract": "本发明公开了一种AI辅助专利撰写方法。",
        "drawings": "图1为流程图。",
        "diagram": "flowchart TD\nA[输入] --> B[生成]",
        "image_prompt": "黑白线稿，展示AI辅助专利撰写流程。",
        "post_draft_claims_reviewer": '{"role":"claims_reviewer","status":"passed","blocking_issues":[],"contamination_hits":[],"rewrite_suggestions":[],"official_safe_patches":[],"attorney_memo":[]}',
        "post_draft_spec_cleaner": '{"role":"spec_cleaner","status":"passed","blocking_issues":[],"contamination_hits":[],"rewrite_suggestions":[],"official_safe_patches":[],"attorney_memo":[]}',
        "post_draft_technical_hardness": '{"role":"technical_hardness","status":"passed","blocking_issues":[],"contamination_hits":[],"rewrite_suggestions":[],"official_safe_patches":[],"attorney_memo":[]}',
        "post_draft_chair_synthesis": '{"status":"passed","export_allowed":true,"blocking_issues":[],"contamination_hits":[],"claim_1_rewrite":"","system_claim_rewrite":"","abstract_rewrite":"","description_rewrite_tasks":[],"official_safe_patches":[],"attorney_memo":[],"next_actions":[]}',
    }
    client = _minimal_app_with_llm(tmp_path, responses)
    project_id = _create_project_with_package(client)

    # Compile
    compile_resp = client.post(
        f"/api/projects/{project_id}/official-compile-runs", json={}
    )
    assert compile_resp.status_code == 200

    # Post-draft review
    review_resp = client.post(
        f"/api/projects/{project_id}/post-draft-reviews", json={}
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["export_allowed"] is True

    # Now official-export.md should work with Content-Disposition
    resp = client.get(f"/api/projects/{project_id}/official-export.md")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "filename*=UTF-8''" in cd
    assert ".md" in cd
    assert "filename=" in cd  # ASCII fallback present

    # Official DOCX too
    docx_resp = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert docx_resp.status_code == 200
    assert docx_resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_text_export_endpoints_preserve_content_types(tmp_path: Path):
    """All text-based export routes preserve the correct content-type."""
    client = _minimal_app_with_llm(
        tmp_path,
        {
            "claims": "1. 一种方法。",
            "description": "技术领域\n本发明涉及AI技术。",
            "abstract": "本发明公开了一种方法。",
            "drawings": "图1。",
            "diagram": "flowchart TD\nA-->B",
            "image_prompt": "prompt",
        },
    )
    project_id = _create_project_with_package(client)

    # Markdown export
    md = client.get(f"/api/projects/{project_id}/export.md")
    assert md.status_code == 200
    assert md.headers["content-type"] == "text/markdown; charset=utf-8"

    # Mermaid export
    mmd = client.get(f"/api/projects/{project_id}/diagram.mmd")
    assert mmd.status_code == 200
    assert mmd.headers["content-type"] == "text/plain; charset=utf-8"

    # Image prompt export
    img = client.get(f"/api/projects/{project_id}/image-prompt.md")
    assert img.status_code == 200
    assert img.headers["content-type"] == "text/markdown; charset=utf-8"

    # DOCX export
    docx = client.get(f"/api/projects/{project_id}/export.docx")
    assert docx.status_code == 200
    assert docx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
