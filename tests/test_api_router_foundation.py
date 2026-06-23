"""PR-1: Backend router foundation - integration tests.

Verify that the new router modules (system, desktop_config) are correctly
registered in the FastAPI application and that:

* The health endpoint returns the unchanged contract shape.
* The agent doctor endpoint still responds.
* Desktop config CRUD endpoints work through the router layer.
* LLM rebuild on PATCH still works.
* Origin guard still blocks untrusted origins.
* No circular imports exist between routers and main.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"


def _assert_no_raw_key(payload: dict, key: str) -> None:
    blob = json.dumps(payload, ensure_ascii=False)
    assert key not in blob, f"raw api key leaked in payload: {blob!r}"


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_endpoint_shape_unchanged(tmp_path: Path) -> None:
    """GET /api/health returns the same contract as before the refactor."""
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "llm_configured" in body
    assert "data_dir" in body
    assert "model" in body
    assert "embedding_model" in body
    # No raw key should ever appear
    assert "api_key" not in body


def test_health_reports_llm_not_configured_without_key(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    body = client.get("/api/health").json()
    assert body["llm_configured"] is False


def test_health_reports_llm_configured_with_fake_client(tmp_path: Path) -> None:
    llm = FakeLLMClient({"claims": "test"})
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    body = client.get("/api/health").json()
    assert body["llm_configured"] is True


# ---------------------------------------------------------------------------
# Agent doctor
# ---------------------------------------------------------------------------


def test_agent_doctor_responds(tmp_path: Path) -> None:
    """GET /api/agents/doctor returns a structured dict."""
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    response = client.get("/api/agents/doctor")
    assert response.status_code == 200
    body = response.json()
    assert "profile_path" in body or "active_provider_ids" in body


# ---------------------------------------------------------------------------
# Desktop config through router layer
# ---------------------------------------------------------------------------


def test_desktop_config_get_returns_redacted_defaults(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    response = client.get("/api/desktop-config")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "deepseek"
    assert body["base_url"].startswith("http")
    assert body["api_key_present"] is False
    assert body["api_key_fingerprint"] == ""
    assert body["api_key_source"] == "none"
    assert "api_key" not in body
    assert body["version"] >= 1


def test_desktop_config_patch_persists_and_rebuilds_llm(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    # Before: no key
    health0 = client.get("/api/health").json()
    assert health0["llm_configured"] is False

    # Set a key
    secret = "sk-router-test-7890"
    response = client.patch(
        "/api/desktop-config",
        json={"api_key": secret, "model": "router-test-model"},
    )
    assert response.status_code == 200
    body = response.json()
    _assert_no_raw_key(body, secret)
    assert body["api_key_present"] is True
    assert body["api_key_fingerprint"].endswith("7890")
    assert body["model"] == "router-test-model"
    assert body["api_key_source"] == "desktop_config"

    # After: LLM should be rebuilt (key is fake but configured)
    health1 = client.get("/api/health").json()
    assert health1["llm_configured"] is True
    assert health1["model"] == "deepseek-v4-pro"  # settings, not payload

    # Re-read from the router layer
    second = client.get("/api/desktop-config")
    second_body = second.json()
    _assert_no_raw_key(second_body, secret)
    assert second_body["model"] == "router-test-model"

    # Origin guard still enforced
    evil = client.patch(
        "/api/desktop-config",
        json={"model": "hijacked"},
        headers={"Origin": "https://evil.example"},
    )
    assert evil.status_code == 403
    assert "Forbidden desktop config origin" in evil.json()["detail"]


def test_desktop_config_clear_key(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    client.patch("/api/desktop-config", json={"api_key": "sk-clear-me-1234"})
    clear = client.patch("/api/desktop-config", json={"clear_api_key": True})
    assert clear.status_code == 200
    body = clear.json()
    assert body["api_key_present"] is False
    assert body["api_key_fingerprint"] == ""
    assert body["api_key_source"] == "none"


def test_desktop_config_health_no_key(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    response = client.post("/api/desktop-config/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "no_api_key"
    assert body["api_key_source"] == "none"


def test_desktop_config_origin_guard_preserved(tmp_path: Path) -> None:
    """Origin guard moved to the service layer must behave identically."""
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))

    # Absent Origin is allowed (Tauri commands don't send it)
    response = client.get("/api/desktop-config")
    assert response.status_code == 200

    # Allowed renderer origins
    for origin in [
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "tauri://localhost",
    ]:
        response = client.get("/api/desktop-config", headers={"Origin": origin})
        assert response.status_code == 200, f"Origin {origin} was rejected"

    # Untrusted origins rejected
    for origin in ["https://evil.example", "null"]:
        response = client.patch(
            "/api/desktop-config",
            json={"model": "bad"},
            headers={"Origin": origin},
        )
        assert response.status_code == 403, f"Origin {origin} was not rejected"


def test_desktop_config_llm_override_preserved(tmp_path: Path) -> None:
    """Passing llm_client should keep the injected LLM after patch."""
    llm = FakeLLMClient({"claims": "1. preserved."})
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False))
    response = client.patch(
        "/api/desktop-config",
        json={"api_key": "sk-override-9999"},
    )
    assert response.status_code == 200
    # Injected LLM must stay
    assert client.app.state.llm is llm


def test_cors_middleware_still_applied(tmp_path: Path) -> None:
    """CORS middleware (using LOCAL_RENDERER_ORIGINS from service) still works."""
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
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


# ---------------------------------------------------------------------------
# No circular imports
# ---------------------------------------------------------------------------


def test_router_imports_dont_import_main() -> None:
    """Routers must never import backend.app.main (circular import guard)."""
    import ast
    import sys
    from pathlib import Path

    router_files = [
        Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "system.py",
        Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "desktop_config.py",
        Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "deps.py",
    ]
    for path in router_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "backend.app.main" in module:
                    assert False, f"{path.name} imports backend.app.main (circular)"


def test_service_imports_dont_import_main() -> None:
    """Service modules must never import backend.app.main."""
    import ast
    from pathlib import Path

    service_files = [
        Path(__file__).resolve().parents[1] / "backend" / "app" / "services" / "llm_factory.py",
        Path(__file__).resolve().parents[1] / "backend" / "app" / "services" / "desktop_config_service.py",
    ]
    for path in service_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "backend.app.main" in module:
                    assert False, f"{path.name} imports backend.app.main (circular)"


def test_desktop_config_env_file_never_touched(tmp_path: Path) -> None:
    """PATCH must never touch the project .env file (even when absent)."""
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    env_exists_before = ENV_FILE.exists()
    env_content_before = ENV_FILE.read_text(encoding="utf-8") if env_exists_before else None

    client.patch("/api/desktop-config", json={"api_key": "sk-env-safe-0000"})

    if env_exists_before:
        assert ENV_FILE.read_text(encoding="utf-8") == env_content_before
    else:
        assert not ENV_FILE.exists()
