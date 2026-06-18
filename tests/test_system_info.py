"""Tests for the /api/system/info runtime diagnostics endpoint."""

import os

from fastapi.testclient import TestClient

from backend.app.main import create_app


def _test_app_without_env(tmp_path):
    return TestClient(create_app(data_dir=tmp_path, load_env_file=False))


def test_system_info_returns_expected_fields(tmp_path):
    """The /api/system/info endpoint returns all required runtime diagnostics fields."""
    client = _test_app_without_env(tmp_path)
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()

    assert "app_version" in data
    assert "data_dir" in data
    assert "source_kind" in data
    assert "python_version" in data
    assert "model" in data
    assert "embedding_model" in data

    assert data["data_dir"] == str(tmp_path)
    assert data["source_kind"] in ("tauri", "web")
    assert data["app_version"] == "1.1.0"
    assert isinstance(data["python_version"], str)
    assert data["python_version"].count(".") >= 1  # e.g. "3.12.0"


def test_system_info_web_mode_when_no_data_dir_env(tmp_path):
    """When DATA_DIR env is not set, source_kind should be 'web'."""
    # Ensure DATA_DIR is not set in the environment
    old_data_dir = os.environ.pop("DATA_DIR", None)
    try:
        client = _test_app_without_env(tmp_path)
        response = client.get("/api/system/info")
        assert response.status_code == 200
        assert response.json()["source_kind"] == "web"
    finally:
        if old_data_dir is not None:
            os.environ["DATA_DIR"] = old_data_dir


def test_system_info_tauri_mode_when_data_dir_env_set(tmp_path):
    """When DATA_DIR env is set, source_kind should be 'tauri'."""
    old_data_dir = os.environ.get("DATA_DIR")
    os.environ["DATA_DIR"] = str(tmp_path)
    try:
        client = _test_app_without_env(tmp_path)
        response = client.get("/api/system/info")
        assert response.status_code == 200
        assert response.json()["source_kind"] == "tauri"
    finally:
        if old_data_dir is not None:
            os.environ["DATA_DIR"] = old_data_dir
        else:
            os.environ.pop("DATA_DIR", None)
