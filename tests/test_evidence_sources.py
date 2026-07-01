import json
import os
import stat

import pytest

from backend.app.evidence_sources import (
    EVIDENCE_SOURCE_CONFIG_FILENAME,
    check_evidence_source_config,
    evidence_source_views,
    update_evidence_source_config,
)
from backend.app.schemas import EvidenceSourceConfigPatch


def _by_id(items):
    return {item.source_id: item for item in items}


def test_evidence_sources_default_to_not_configured(tmp_path):
    views = _by_id(evidence_source_views(tmp_path, env={}))

    assert views["patsnap_api"].display_name == "智慧芽 PatSnap"
    assert views["patsnap_api"].source_type == "patent"
    assert views["patsnap_api"].evidence_tier == "primary_patent"
    assert views["patsnap_api"].status == "not_configured"
    assert views["patsnap_api"].api_key_present is False
    assert views["patsnap_api"].api_key_masked == ""
    assert views["patsnap_api"].can_satisfy_patent_gate is True
    assert "open.zhihuiya.com" in views["patsnap_api"].application_url

    assert views["wanfang_api"].display_name == "万方"
    assert views["wanfang_api"].source_type == "non_patent_literature"
    assert views["wanfang_api"].evidence_tier == "supplemental_literature"
    assert views["wanfang_api"].status == "not_configured"
    assert views["wanfang_api"].can_satisfy_patent_gate is False
    assert "apps.wanfangdata.com.cn" in views["wanfang_api"].docs_url


def test_update_evidence_source_config_persists_redacted_secret_with_owner_only_permissions(tmp_path):
    view = update_evidence_source_config(
        tmp_path,
        "patsnap_api",
        EvidenceSourceConfigPatch(api_key="ps-test-secret-1234", base_url="https://connect.zhihuiya.com", enabled=True),
    )

    assert view.api_key_present is True
    assert view.api_key_masked.endswith("1234")
    assert "ps-test-secret" not in view.model_dump_json()

    config_path = tmp_path / EVIDENCE_SOURCE_CONFIG_FILENAME
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    assert raw["sources"]["patsnap_api"]["api_key"] == "ps-test-secret-1234"
    if os.name == "posix":
        assert stat.S_IMODE(config_path.stat().st_mode) == 0o600


def test_environment_api_key_overrides_local_config_without_exposing_secret(tmp_path):
    update_evidence_source_config(
        tmp_path,
        "patsnap_api",
        EvidenceSourceConfigPatch(api_key="local-secret-0000", base_url="https://local.example", enabled=True),
    )

    views = _by_id(
        evidence_source_views(
            tmp_path,
            env={"PATSNAP_API_KEY": "env-secret-9999", "PATSNAP_BASE_URL": "https://env.example"},
        )
    )

    assert views["patsnap_api"].api_key_present is True
    assert views["patsnap_api"].api_key_source == "env"
    assert views["patsnap_api"].api_key_masked.endswith("9999")
    assert views["patsnap_api"].base_url == "https://env.example"
    assert "env-secret" not in views["patsnap_api"].model_dump_json()


def test_clear_evidence_source_key_keeps_source_disabled_or_enabled_explicitly(tmp_path):
    update_evidence_source_config(
        tmp_path,
        "wanfang_api",
        EvidenceSourceConfigPatch(api_key="wf-secret-5678", enabled=True),
    )

    cleared = update_evidence_source_config(
        tmp_path,
        "wanfang_api",
        EvidenceSourceConfigPatch(clear_api_key=True, enabled=False),
    )

    assert cleared.enabled is False
    assert cleared.api_key_present is False
    assert cleared.status == "not_configured"


def test_check_evidence_source_config_reports_configured_without_vendor_network_call(tmp_path):
    update_evidence_source_config(
        tmp_path,
        "patsnap_api",
        EvidenceSourceConfigPatch(api_key="ps-test-secret-1234", enabled=True),
    )

    result = check_evidence_source_config(tmp_path, "patsnap_api", env={})

    assert result.source_id == "patsnap_api"
    assert result.ok is True
    assert result.status == "configured"
    assert result.detail == "configured_local_check_only"
    assert result.live_search_available is False


def test_unknown_evidence_source_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unknown evidence source"):
        update_evidence_source_config(tmp_path, "unknown_source", EvidenceSourceConfigPatch(api_key="secret"))
