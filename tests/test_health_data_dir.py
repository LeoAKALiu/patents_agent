"""Tests for the data-dir precedence helpers and the ``/api/health`` payload.

PR-7 makes the desktop backend honor a documented precedence for the data
directory and surface the resolved source through ``/api/health`` so QA can
tell at a glance which launch they are looking at.

These tests cover three concerns:

1. The pure ``resolve_backend_data_dir`` / ``data_dir_source`` /
   ``resolve_qa_profile`` helpers in :mod:`backend.app.settings`.
2. The ``build_settings`` entrypoint honors the env precedence even when
   no explicit ``data_dir`` is passed.
3. The ``/api/health`` endpoint exposes the diagnostics block on
   :class:`backend.app.main.create_app`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.settings import (
    BACKEND_DATA_DIR_ENV,
    QA_PROFILE_ENV,
    build_settings,
    data_dir_source,
    resolve_backend_data_dir,
    resolve_qa_profile,
)


# --- Pure helper tests -----------------------------------------------------


def test_resolve_backend_data_dir_explicit_wins(tmp_path):
    explicit = tmp_path / "explicit-dir"
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setenv("PATENTAGENT_BACKEND_DATA_DIR", str(tmp_path / "env-dir"))
        monkey.setenv("DATA_DIR", str(tmp_path / "legacy-dir"))
        assert resolve_backend_data_dir(explicit=explicit) == explicit.expanduser()
    finally:
        monkey.undo()


def test_resolve_backend_data_dir_prefers_namespaced_env(tmp_path):
    primary = tmp_path / "primary"
    legacy = tmp_path / "legacy"
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setenv("PATENTAGENT_BACKEND_DATA_DIR", str(primary))
        monkey.setenv("DATA_DIR", str(legacy))
        assert resolve_backend_data_dir() == primary
    finally:
        monkey.undo()


def test_resolve_backend_data_dir_falls_back_to_legacy_env(tmp_path):
    legacy = tmp_path / "legacy"
    monkey = pytest.MonkeyPatch()
    try:
        monkey.delenv("PATENTAGENT_BACKEND_DATA_DIR", raising=False)
        monkey.setenv("DATA_DIR", str(legacy))
        assert resolve_backend_data_dir() == legacy
    finally:
        monkey.undo()


def test_resolve_backend_data_dir_default_when_no_env(tmp_path, monkeypatch):
    monkeypatch.delenv("PATENTAGENT_BACKEND_DATA_DIR", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert resolve_backend_data_dir() == __import__("pathlib").Path("data")


def test_data_dir_source_explicit():
    assert data_dir_source(explicit="/tmp/x") == "explicit"


def test_data_dir_source_prefers_namespaced_env(monkeypatch):
    monkeypatch.setenv("PATENTAGENT_BACKEND_DATA_DIR", "/tmp/a")
    monkeypatch.setenv("DATA_DIR", "/tmp/b")
    assert data_dir_source() == "PATENTAGENT_BACKEND_DATA_DIR"
    assert BACKEND_DATA_DIR_ENV[0] == "PATENTAGENT_BACKEND_DATA_DIR"


def test_data_dir_source_legacy_env_label(monkeypatch):
    monkeypatch.delenv("PATENTAGENT_BACKEND_DATA_DIR", raising=False)
    monkeypatch.setenv("DATA_DIR", "/tmp/legacy")
    assert data_dir_source() == "DATA_DIR"


def test_data_dir_source_default_when_no_env(monkeypatch):
    monkeypatch.delenv("PATENTAGENT_BACKEND_DATA_DIR", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert data_dir_source() == "default"


@pytest.mark.parametrize("raw", ["1", "true", "yes", "on", "TRUE", "Yes"])
def test_resolve_qa_profile_truthy(monkeypatch, raw):
    monkeypatch.setenv(QA_PROFILE_ENV, raw)
    assert resolve_qa_profile() is True


@pytest.mark.parametrize("raw", ["0", "false", "no", "off", "", "garbage"])
def test_resolve_qa_profile_falsy(monkeypatch, raw):
    monkeypatch.setenv(QA_PROFILE_ENV, raw)
    assert resolve_qa_profile() is False


def test_resolve_qa_profile_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv(QA_PROFILE_ENV, "1")
    assert resolve_qa_profile(explicit=False) is False
    assert resolve_qa_profile(explicit=True) is True


def test_resolve_qa_profile_missing_env_is_false(monkeypatch):
    monkeypatch.delenv(QA_PROFILE_ENV, raising=False)
    assert resolve_qa_profile() is False


# --- build_settings integration -------------------------------------------


def test_build_settings_uses_explicit_data_dir(tmp_path):
    settings = build_settings(data_dir=tmp_path, load_env_file=False)
    assert settings.data_dir == tmp_path


def test_build_settings_honors_namespaced_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PATENTAGENT_BACKEND_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("DATA_DIR", raising=False)
    settings = build_settings(load_env_file=False)
    assert settings.data_dir == tmp_path


def test_build_settings_legacy_env_still_works(tmp_path, monkeypatch):
    monkeypatch.delenv("PATENTAGENT_BACKEND_DATA_DIR", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings = build_settings(load_env_file=False)
    assert settings.data_dir == tmp_path


def test_build_settings_default_when_no_override(tmp_path, monkeypatch):
    monkeypatch.delenv("PATENTAGENT_BACKEND_DATA_DIR", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    settings = build_settings(load_env_file=False)
    assert settings.data_dir == __import__("pathlib").Path("data")


# --- /api/health payload --------------------------------------------------


def test_health_payload_reflects_explicit_data_dir(tmp_path):
    explicit = tmp_path / "from-test"
    client = TestClient(
        create_app(
            data_dir=explicit,
            load_env_file=False,
            qa_profile=False,
            instance_id="test-instance",
            backend_port=8123,
        )
    )
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data_dir"] == str(explicit)
    assert body["data_dir_source"] == "explicit"
    assert body["qa_profile"] is False
    assert body["instance_id"] == "test-instance"
    assert body["backend_port"] == 8123
    assert body["qa_profile_env"] == QA_PROFILE_ENV
    assert body["version"]


def test_health_payload_surfaces_qa_profile(tmp_path):
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            load_env_file=False,
            qa_profile=True,
        )
    )
    response = client.get("/api/health")
    body = response.json()
    assert body["qa_profile"] is True
    assert body["data_dir_source"] == "explicit"


def test_health_payload_picks_up_env_data_dir(tmp_path, monkeypatch):
    env_dir = tmp_path / "env-dir"
    monkeypatch.setenv("PATENTAGENT_BACKEND_DATA_DIR", str(env_dir))
    monkeypatch.delenv("DATA_DIR", raising=False)
    client = TestClient(create_app(load_env_file=False))
    try:
        response = client.get("/api/health")
        body = response.json()
        assert body["data_dir"] == str(env_dir)
        assert body["data_dir_source"] == "PATENTAGENT_BACKEND_DATA_DIR"
    finally:
        # Tear the app down so the SQLiteStore released the file lock
        # before monkeypatch restores the env var (avoids fd leakage on
        # Windows CI runners).
        client.close()


def test_health_payload_picks_up_legacy_env_data_dir(tmp_path, monkeypatch):
    env_dir = tmp_path / "legacy"
    monkeypatch.delenv("PATENTAGENT_BACKEND_DATA_DIR", raising=False)
    monkeypatch.setenv("DATA_DIR", str(env_dir))
    client = TestClient(create_app(load_env_file=False))
    try:
        body = client.get("/api/health").json()
        assert body["data_dir"] == str(env_dir)
        assert body["data_dir_source"] == "DATA_DIR"
    finally:
        client.close()