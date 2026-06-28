from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.llm_cassette import LLMCassetteError, cassette_key, maybe_wrap_with_cassette
from backend.app.main import create_app
from backend.app.patent_mode import UTILITY_MODEL_MODE_PREFIX
from backend.app.services.llm_factory import build_llm
from backend.app.settings import build_settings


def test_record_mode_writes_response_and_replay_mode_returns_without_delegate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATENTAGENT_LLM_MODE", "record")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_DIR", str(tmp_path))
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_SUITE", "pipeline")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_CASE", "happy-path")
    record_delegate = FakeLLMClient({"claims": "recorded response"})

    recorder = maybe_wrap_with_cassette(record_delegate, provider="fake", model="unit-test")
    assert recorder.complete_stage("claims", "system", "user") == "recorded response"

    cassette_path = tmp_path / "pipeline" / "happy-path.json"
    payload = json.loads(cassette_path.read_text(encoding="utf-8"))
    assert list(payload["entries"].values())[0]["response"] == "recorded response"

    monkeypatch.setenv("PATENTAGENT_LLM_MODE", "replay")
    replay_delegate = FakeLLMClient({})
    replayer = maybe_wrap_with_cassette(replay_delegate, provider="fake", model="unit-test")

    assert replayer.complete_stage("claims", "system", "user") == "recorded response"
    assert replay_delegate.calls == []


def test_record_mode_handles_concurrent_stage_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATENTAGENT_LLM_MODE", "record")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_DIR", str(tmp_path))
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_SUITE", "pipeline")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_CASE", "concurrent")
    responses = {f"stage-{index}": f"response-{index}" for index in range(20)}
    recorder = maybe_wrap_with_cassette(
        FakeLLMClient(responses),
        provider="fake",
        model="unit-test",
    )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda stage: recorder.complete_stage(stage, f"system {stage}", f"user {stage}"),
                responses,
            )
        )

    cassette_path = tmp_path / "pipeline" / "concurrent.json"
    payload = json.loads(cassette_path.read_text(encoding="utf-8"))
    assert sorted(results) == sorted(responses.values())
    assert len(payload["entries"]) == len(responses)


def test_replay_mode_fails_closed_when_cassette_entry_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATENTAGENT_LLM_MODE", "replay")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_DIR", str(tmp_path))
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_SUITE", "pipeline")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_CASE", "missing")
    delegate = FakeLLMClient({"claims": "must not be called"})

    client = maybe_wrap_with_cassette(delegate, provider="fake", model="unit-test")

    with pytest.raises(LLMCassetteError, match="missing cassette entry"):
        client.complete_stage("claims", "system", "user")
    assert delegate.calls == []


def test_live_mode_does_not_touch_cassette_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATENTAGENT_LLM_MODE", "live")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_DIR", str(tmp_path))
    delegate = FakeLLMClient({"claims": "live response"})

    client = maybe_wrap_with_cassette(delegate, provider="fake", model="unit-test")

    assert client.complete_stage("claims", "system", "user") == "live response"
    assert not list(tmp_path.rglob("*.json"))


def test_build_llm_replay_mode_uses_cassette_without_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("PATENTAGENT_LLM_MODE", "replay")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_DIR", str(tmp_path))
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_SUITE", "ci")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_CASE", "draft")
    key = cassette_key(
        provider="deepseek",
        model="deepseek-v4-pro",
        stage="claims",
        system_prompt="system",
        user_prompt="user",
    )
    cassette_path = tmp_path / "ci" / "draft.json"
    cassette_path.parent.mkdir(parents=True)
    cassette_path.write_text(
        json.dumps({"version": 1, "entries": {key: {"response": "replayed"}}}),
        encoding="utf-8",
    )

    client = build_llm(build_settings(load_env_file=False))

    assert client.complete_stage("claims", "system", "user") == "replayed"


def test_static_generation_cassette_drives_generate_api_without_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("PATENTAGENT_LLM_MODE", "replay")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_DIR", "tests/cassettes")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_SUITE", "generation")
    monkeypatch.setenv("PATENTAGENT_LLM_CASSETTE_CASE", "utility_model")
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "可调安装支架",
            "patent_type": "utility_model",
            "draft_text": (
                f"{UTILITY_MODEL_MODE_PREFIX}专利类型：实用新型。\n"
                "一种可调安装支架，包括底座、支撑臂和限位件，可根据角度矩阵调节安装位置。"
            ),
        },
    ).json()["id"]

    response = client.post(f"/api/projects/{project_id}/generate", json={})

    assert response.status_code == 200
    package = response.json()
    assert "可调安装支架" in package["title"]
    assert "一种可调安装支架" in package["claims"]
    assert "本实用新型" in package["abstract"]
    assert "flowchart TD" in package["mermaid"]


def test_cassette_key_normalizes_message_newlines() -> None:
    first = cassette_key(
        provider="fake",
        model="unit-test",
        stage="claims",
        system_prompt="system\r\nprompt",
        user_prompt="user\r\nprompt",
    )
    second = cassette_key(
        provider="fake",
        model="unit-test",
        stage="claims",
        system_prompt="system\nprompt",
        user_prompt="user\nprompt",
    )

    assert first == second
