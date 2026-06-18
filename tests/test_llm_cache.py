from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.llm_cache import clear_project_llm_cache, complete_stage_cached, stage_cache_key
from backend.app.main import create_app
from backend.app.schemas import DraftPackage
from backend.app.storage import SQLiteStore


def _store(tmp_path: Path) -> SQLiteStore:
    return SQLiteStore(tmp_path / "patents_agent.sqlite3")


def test_stage_cache_key_changes_for_stage_prompt_model_source_hash_and_prompt_pack() -> None:
    base = stage_cache_key(
        project_id="project-1",
        stage="claims",
        model="deepseek-chat",
        system_prompt="system",
        user_prompt="user",
        source_hash="source-a",
        prompt_pack_version="v1",
    )

    assert base != stage_cache_key(
        project_id="project-1",
        stage="description",
        model="deepseek-chat",
        system_prompt="system",
        user_prompt="user",
        source_hash="source-a",
        prompt_pack_version="v1",
    )
    assert base != stage_cache_key(
        project_id="project-1",
        stage="claims",
        model="deepseek-chat",
        system_prompt="system changed",
        user_prompt="user",
        source_hash="source-a",
        prompt_pack_version="v1",
    )
    assert base != stage_cache_key(
        project_id="project-1",
        stage="claims",
        model="other-model",
        system_prompt="system",
        user_prompt="user",
        source_hash="source-a",
        prompt_pack_version="v1",
    )
    assert base != stage_cache_key(
        project_id="project-1",
        stage="claims",
        model="deepseek-chat",
        system_prompt="system",
        user_prompt="user",
        source_hash="source-b",
        prompt_pack_version="v1",
    )
    assert base != stage_cache_key(
        project_id="project-1",
        stage="claims",
        model="deepseek-chat",
        system_prompt="system",
        user_prompt="user",
        source_hash="source-a",
        prompt_pack_version="v2",
    )


def test_complete_stage_cached_miss_calls_underlying_once_and_hit_skips_it(tmp_path) -> None:
    store = _store(tmp_path)
    calls: list[str] = []

    def fallback() -> str:
        calls.append("called")
        return "cached response"

    first = complete_stage_cached(
        store=store,
        project_id="project-1",
        stage="claims",
        model="deepseek-chat",
        system_prompt="system",
        user_prompt="user",
        source_hash="source-a",
        prompt_pack_version="v1",
        fallback=fallback,
    )
    second = complete_stage_cached(
        store=store,
        project_id="project-1",
        stage="claims",
        model="deepseek-chat",
        system_prompt="system",
        user_prompt="user",
        source_hash="source-a",
        prompt_pack_version="v1",
        fallback=fallback,
    )

    assert first == "cached response"
    assert second == "cached response"
    assert calls == ["called"]


def test_clear_project_llm_cache_deletes_only_one_project(tmp_path) -> None:
    store = _store(tmp_path)

    complete_stage_cached(
        store=store,
        project_id="project-1",
        stage="claims",
        model="model",
        system_prompt="system",
        user_prompt="user",
        source_hash="hash",
        fallback=lambda: "project 1",
    )
    complete_stage_cached(
        store=store,
        project_id="project-2",
        stage="claims",
        model="model",
        system_prompt="system",
        user_prompt="user",
        source_hash="hash",
        fallback=lambda: "project 2",
    )

    deleted = clear_project_llm_cache(store, "project-1")

    assert deleted == 1
    assert store.get_llm_stage_cache(stage_cache_key(
        project_id="project-1",
        stage="claims",
        model="model",
        system_prompt="system",
        user_prompt="user",
        source_hash="hash",
    )) is None
    assert store.get_llm_stage_cache(stage_cache_key(
        project_id="project-2",
        stage="claims",
        model="model",
        system_prompt="system",
        user_prompt="user",
        source_hash="hash",
    )) is not None


def test_clear_project_llm_cache_endpoint(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project = client.post("/api/projects", json={"name": "cache", "draft_text": "一种方法。"}).json()
    store = client.app.state.store
    complete_stage_cached(
        store=store,
        project_id=project["id"],
        stage="claims",
        model="model",
        system_prompt="system",
        user_prompt="user",
        source_hash="hash",
        fallback=lambda: "response",
    )

    response = client.post(f"/api/projects/{project['id']}/llm-cache/clear")

    assert response.status_code == 200
    assert response.json()["deleted"] == 1


def test_post_draft_review_uses_stage_cache_for_same_official_package(tmp_path) -> None:
    llm = _review_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False))
    project = client.post("/api/projects", json={"name": "cache review", "draft_text": "一种方法。"}).json()
    client.app.state.store.update_project_package(project["id"], _package())

    assert client.post(f"/api/projects/{project['id']}/official-compile-runs", json={}).json()["status"] == "completed"
    first = client.post(f"/api/projects/{project['id']}/post-draft-reviews", json={})
    assert first.status_code == 200
    assert len(llm.calls) == 4
    second = client.post(f"/api/projects/{project['id']}/post-draft-reviews", json={})

    assert second.status_code == 200
    assert len(llm.calls) == 4


def _package() -> DraftPackage:
    return DraftPackage(
        title="一种输入数据处理方法",
        abstract="本发明公开一种输入数据处理方法。",
        claims="1. 一种输入数据处理方法，其特征在于，包括接收输入数据并输出处理结果。",
        description="本实施例接收输入数据并输出处理结果。",
        drawing_description="图1为流程图。",
        mermaid="",
        image_prompt="",
    )


def _review_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": """
{
  "role": "claims_reviewer",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_spec_cleaner": """
{
  "role": "spec_cleaner",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
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
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_chair_synthesis": """
{
  "status": "passed",
  "export_allowed": true,
  "blocking_issues": [],
  "contamination_hits": [],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": [],
  "next_actions": []
}
""",
        }
    )
