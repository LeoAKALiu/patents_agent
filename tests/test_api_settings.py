"""Tests for the PR6 desktop configuration endpoints (issue #20).

These tests cover:
  * GET /api/desktop-config returns a redacted view (no raw key)
  * PATCH /api/desktop-config persists the new values locally
  * PATCH never touches the .env file
  * POST /api/desktop-config/health returns a structured result with no key
  * 0o600 file permissions on the local config file (POSIX only)
  * The endpoint does not accept both api_key and clear_api_key
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"


@pytest.fixture
def data_dir(tmp_path) -> Path:
    return tmp_path


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(data_dir=data_dir, load_env_file=False))


def _assert_no_raw_key(payload: dict, key: str) -> None:
    """Make sure ``key`` (the raw API key) is absent from every string field."""
    blob = json.dumps(payload, ensure_ascii=False)
    assert key not in blob, f"raw api key leaked in payload: {blob!r}"


def test_get_desktop_config_returns_defaults(client: TestClient) -> None:
    response = client.get("/api/desktop-config")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "deepseek"
    assert body["model"]
    assert body["base_url"].startswith("http")
    assert body["api_key_present"] is False
    assert body["api_key_fingerprint"] == ""
    assert body["api_key_source"] == "none"
    assert "api_key" not in body
    assert body["version"] >= 1


def test_app_reports_release_version(client: TestClient) -> None:
    assert client.app.version == "1.0.0"


def test_cors_allows_renderer_origin_without_credentials(client: TestClient) -> None:
    origin = "http://127.0.0.1:5173"
    response = client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers


def test_cors_rejects_untrusted_browser_origin_preflight(client: TestClient) -> None:
    response = client.options(
        "/api/desktop-config",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_desktop_config_rejects_untrusted_browser_origin(client: TestClient) -> None:
    response = client.patch(
        "/api/desktop-config",
        json={"base_url": "https://attacker.example"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert "Forbidden desktop config origin" in response.json()["detail"]


def test_desktop_config_allows_electron_file_origin(client: TestClient) -> None:
    response = client.patch(
        "/api/desktop-config",
        json={"model": "deepseek-release-test"},
        headers={"Origin": "null"},
    )
    assert response.status_code == 200
    assert response.json()["model"] == "deepseek-release-test"


def test_patch_persists_provider_base_url_and_model(client: TestClient) -> None:
    response = client.patch(
        "/api/desktop-config",
        json={
            "provider": "deepseek",
            "base_url": "https://api.deepseek.example",
            "model": "deepseek-test",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["base_url"] == "https://api.deepseek.example"
    assert body["model"] == "deepseek-test"
    assert body["api_key_present"] is False

    # Re-read
    second = client.get("/api/desktop-config")
    assert second.json()["base_url"] == "https://api.deepseek.example"
    assert second.json()["model"] == "deepseek-test"


def test_patch_persists_api_key_with_redaction(client: TestClient) -> None:
    secret = "sk-very-secret-1234567890"
    response = client.patch(
        "/api/desktop-config",
        json={"api_key": secret},
    )
    assert response.status_code == 200
    body = response.json()
    _assert_no_raw_key(body, secret)
    assert body["api_key_present"] is True
    assert body["api_key_fingerprint"].endswith("7890")
    assert body["api_key_fingerprint"].startswith("•")
    assert body["api_key_source"] == "desktop_config"
    assert "api_key_hash" not in body

    # Reload from disk and re-check redaction
    second = client.get("/api/desktop-config")
    second_body = second.json()
    _assert_no_raw_key(second_body, secret)
    assert second_body["api_key_present"] is True
    assert second_body["api_key_fingerprint"].endswith("7890")


def test_patch_clear_api_key_removes_secret(client: TestClient) -> None:
    secret = "sk-very-secret-clear-test-9999"
    client.patch("/api/desktop-config", json={"api_key": secret})
    response = client.patch(
        "/api/desktop-config",
        json={"clear_api_key": True},
    )
    assert response.status_code == 200
    body = response.json()
    _assert_no_raw_key(body, secret)
    assert body["api_key_present"] is False
    assert body["api_key_fingerprint"] == ""
    assert body["api_key_source"] == "none"


def test_patch_rejects_mutually_exclusive_flags(client: TestClient) -> None:
    response = client.patch(
        "/api/desktop-config",
        json={"api_key": "sk-1234", "clear_api_key": True},
    )
    assert response.status_code == 422
    detail = str(response.json())
    assert "api_key" in detail and "clear_api_key" in detail


def test_patch_rejects_invalid_provider(client: TestClient) -> None:
    response = client.patch("/api/desktop-config", json={"provider": "Bad Name"})
    assert response.status_code == 422
    body = response.json()
    assert "Invalid provider" in str(body)


def test_patch_rejects_invalid_base_url(client: TestClient) -> None:
    response = client.patch("/api/desktop-config", json={"base_url": "ftp://x.example"})
    assert response.status_code == 422
    body = response.json()
    assert "Invalid base_url" in str(body)


def test_patch_never_touches_env_file(client: TestClient, data_dir: Path) -> None:
    # Snapshot the .env file (or absence) before the request.
    env_exists_before = ENV_FILE.exists()
    env_content_before = ENV_FILE.read_text(encoding="utf-8") if env_exists_before else None

    client.patch(
        "/api/desktop-config",
        json={"api_key": "sk-should-not-leak", "model": "deepseek-v4-pro"},
    )

    if env_exists_before:
        assert ENV_FILE.read_text(encoding="utf-8") == env_content_before
    else:
        assert not ENV_FILE.exists()


def test_desktop_config_file_permissions_are_owner_only(
    client: TestClient, data_dir: Path
) -> None:
    if os.name == "nt":
        pytest.skip("POSIX file mode bits do not apply on Windows")
    secret = "sk-perm-check-1234567890"
    client.patch("/api/desktop-config", json={"api_key": secret})
    cfg_path = data_dir / "desktop-config.json"
    assert cfg_path.is_file()
    mode = stat.S_IMODE(cfg_path.stat().st_mode)
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"


def test_desktop_config_rebuilds_llm_after_patch(
    client: TestClient, app_state=None
) -> None:
    """After PATCH sets a key, /api/health.llm_configured should become true."""
    # Sanity: no key yet
    health0 = client.get("/api/health").json()
    assert health0["llm_configured"] is False

    # Set a key
    response = client.patch(
        "/api/desktop-config",
        json={"api_key": "sk-1234567890abcdef"},
    )
    assert response.status_code == 200

    health1 = client.get("/api/health").json()
    assert health1["llm_configured"] is True
    assert health1["model"] == "deepseek-v4-pro"


def test_env_model_and_base_url_win_when_no_desktop_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-model-test")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://env.example")
    monkeypatch.setenv("LLM_MODEL", "env-model")

    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))

    body = client.get("/api/desktop-config").json()
    assert body["base_url"] == "https://env.example"
    assert body["model"] == "env-model"
    assert body["api_key_source"] == "env"


def test_health_endpoint_returns_no_api_key_structured(
    client: TestClient,
) -> None:
    """Health endpoint never echoes the configured key in its response."""
    secret = "sk-health-endpoint-leak-check-9999"
    client.patch("/api/desktop-config", json={"api_key": secret})
    response = client.post("/api/desktop-config/health")
    assert response.status_code == 200
    body = response.json()
    assert body["model"]
    assert body["api_key_source"] in {"env", "desktop_config", "none"}
    _assert_no_raw_key(body, secret)
    # We can't assert a specific OK/Failure because we don't know whether the
    # bundled fake key talks to a real provider; the contract is that the
    # response shape is stable and the secret does not leak.
    assert "ok" in body
    assert "latency_ms" in body
    assert "status_code" in body
    assert "error" in body


def test_health_endpoint_reports_no_api_key(client: TestClient) -> None:
    response = client.post("/api/desktop-config/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "no_api_key"
    assert body["api_key_source"] == "none"


def test_desktop_config_does_not_break_fake_llm(
    data_dir: Path, tmp_path: Path
) -> None:
    """Passing llm_client should still work with the desktop config plumbing."""
    llm = FakeLLMClient({"claims": "1. 一种测试。", "description": "测试说明。"})
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False))
    response = client.patch(
        "/api/desktop-config",
        json={"api_key": "sk-when-injected-1234", "model": "fake-model"},
    )
    assert response.status_code == 200
    # The injected LLM should be preserved even though we tried to set a key.
    health = client.get("/api/health").json()
    assert health["llm_configured"] is True
    assert client.app.state.llm is llm


def test_atomic_write_preserves_existing_config(
    client: TestClient, data_dir: Path
) -> None:
    """A bad partial write should not corrupt an existing config file."""
    client.patch("/api/desktop-config", json={"api_key": "sk-keep-me-1234", "model": "m1"})
    cfg_path = data_dir / "desktop-config.json"
    assert cfg_path.is_file()
    original = cfg_path.read_text(encoding="utf-8")
    # Simulate a partial write by writing a stale copy next to it.
    (data_dir / "desktop-config.json.tmp").write_text("garbage", encoding="utf-8")
    second = client.get("/api/desktop-config")
    assert second.status_code == 200
    assert second.json()["model"] == "m1"
    # The atomic implementation should not have replaced the original.
    assert cfg_path.read_text(encoding="utf-8") == original
