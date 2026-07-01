from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_list_evidence_sources_returns_redacted_setup_guidance(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))

    response = client.get("/api/evidence-sources")

    assert response.status_code == 200
    payload = response.json()
    sources = {source["source_id"]: source for source in payload["sources"]}
    assert sources["patsnap_api"]["status"] == "not_configured"
    assert sources["patsnap_api"]["can_satisfy_patent_gate"] is True
    assert "智慧芽" in sources["patsnap_api"]["display_name"]
    assert "api_key" not in sources["patsnap_api"]
    assert sources["wanfang_api"]["can_satisfy_patent_gate"] is False


def test_update_evidence_source_config_never_returns_raw_secret(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))

    response = client.put(
        "/api/evidence-sources/patsnap_api/config",
        json={
            "api_key": "ps-secret-value-1234",
            "base_url": "https://connect.zhihuiya.com",
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_key_present"] is True
    assert payload["api_key_masked"].endswith("1234")
    assert "ps-secret-value" not in response.text


def test_update_evidence_source_config_rejects_conflicting_secret_fields_without_echoing_secret(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))

    response = client.put(
        "/api/evidence-sources/patsnap_api/config",
        json={
            "api_key": "ps-secret-value-1234",
            "clear_api_key": True,
        },
    )

    assert response.status_code == 422
    assert "Pass either api_key or clear_api_key, not both." in response.text
    assert "ps-secret-value-1234" not in response.text


def test_update_evidence_source_config_rejects_oversized_secret_without_echoing_raw_input(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    oversized_secret = "ps-oversized-secret-1234-" + ("x" * 5000)

    response = client.put(
        "/api/evidence-sources/patsnap_api/config",
        json={"api_key": oversized_secret, "enabled": True},
    )

    assert response.status_code == 422
    assert "api_key is too long" in response.text
    assert oversized_secret not in response.text
    assert "ps-oversized-secret-1234" not in response.text


def test_update_evidence_source_config_rejects_oversized_secret_with_clear_flag_without_echoing_raw_input(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    oversized_secret = "ps-oversized-secret-5678-" + ("y" * 5000)

    response = client.put(
        "/api/evidence-sources/patsnap_api/config",
        json={"api_key": oversized_secret, "clear_api_key": True},
    )

    assert response.status_code == 422
    assert "Pass either api_key or clear_api_key, not both." in response.text
    assert oversized_secret not in response.text
    assert "ps-oversized-secret-5678" not in response.text


def test_check_evidence_source_config_is_local_only(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    client.put(
        "/api/evidence-sources/wanfang_api/config",
        json={"api_key": "wf-secret-5678", "enabled": True},
    )

    response = client.post("/api/evidence-sources/wanfang_api/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_id"] == "wanfang_api"
    assert payload["ok"] is True
    assert payload["detail"] == "configured_local_check_only"
    assert payload["live_search_available"] is False


def test_unknown_evidence_source_api_returns_404(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))

    response = client.put("/api/evidence-sources/unknown/config", json={"api_key": "secret"})

    assert response.status_code == 404
    assert "Unknown evidence source" in response.json()["detail"]
