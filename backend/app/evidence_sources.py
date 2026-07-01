from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from backend.app.schemas import (
    EvidenceSourceCheckResult,
    EvidenceSourceConfig,
    EvidenceSourceConfigPatch,
)

EVIDENCE_SOURCE_CONFIG_FILENAME = "evidence-sources.json"
CONFIG_VERSION = 1
MASK_TAIL_LEN = 4

SOURCE_DEFINITIONS: dict[str, dict[str, str | bool]] = {
    "patsnap_api": {
        "display_name": "智慧芽 PatSnap",
        "source_type": "patent",
        "evidence_tier": "primary_patent",
        "default_base_url": "https://connect.zhihuiya.com",
        "api_key_env": "PATSNAP_API_KEY",
        "base_url_env": "PATSNAP_BASE_URL",
        "application_url": "https://open.zhihuiya.com/",
        "docs_url": "https://open.zhihuiya.com/devportal",
        "guidance": "配置智慧芽 API key 后可启用中文及全球专利主检索；当前骨架只做本地配置检查。",
        "can_satisfy_patent_gate": True,
    },
    "wanfang_api": {
        "display_name": "万方",
        "source_type": "non_patent_literature",
        "evidence_tier": "supplemental_literature",
        "default_base_url": "https://apps.wanfangdata.com.cn/open",
        "api_key_env": "WANFANG_API_KEY",
        "base_url_env": "WANFANG_BASE_URL",
        "application_url": "https://apps.wanfangdata.com.cn/open/market/apis",
        "docs_url": "https://apps.wanfangdata.com.cn/open/docs",
        "guidance": "配置万方 API key 后可补充论文、期刊、会议与科技文献；该来源不替代专利证据门控。",
        "can_satisfy_patent_gate": False,
    },
}


@dataclass
class StoredEvidenceSourceConfig:
    enabled: bool = True
    base_url: str = ""
    api_key: str = ""
    last_checked_at: str = ""
    last_error: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _config_path(data_dir: Path) -> Path:
    return Path(data_dir) / EVIDENCE_SOURCE_CONFIG_FILENAME


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= MASK_TAIL_LEN:
        return "•" * len(value)
    return "•" * (len(value) - MASK_TAIL_LEN) + value[-MASK_TAIL_LEN:]


def _validate_source_id(source_id: str) -> None:
    if source_id not in SOURCE_DEFINITIONS:
        raise ValueError(f"Unknown evidence source: {source_id}")


def _validate_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        raise ValueError("base_url must start with http:// or https://")
    if len(value) > 512:
        raise ValueError("base_url is too long")
    return value


def _validate_api_key(api_key: str) -> str:
    if not isinstance(api_key, str):
        raise ValueError("api_key must be a string")
    if len(api_key) > 4096:
        raise ValueError("api_key is too long")
    return api_key


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.chmod(tmp_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _load_stored_configs(data_dir: Path) -> dict[str, StoredEvidenceSourceConfig]:
    path = _config_path(data_dir)
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Evidence source config at {path} must be a JSON object")
    sources = raw.get("sources", {})
    if not isinstance(sources, dict):
        raise ValueError(f"Evidence source config at {path} must contain a JSON object at 'sources'")
    configs: dict[str, StoredEvidenceSourceConfig] = {}
    for source_id, payload in sources.items():
        if source_id in SOURCE_DEFINITIONS and isinstance(payload, dict):
            configs[source_id] = StoredEvidenceSourceConfig(
                enabled=bool(payload.get("enabled", True)),
                base_url=_validate_base_url(str(payload.get("base_url", ""))),
                api_key=_validate_api_key(str(payload.get("api_key", ""))),
                last_checked_at=str(payload.get("last_checked_at", "")),
                last_error=str(payload.get("last_error", "")),
            )
    return configs


def _save_stored_configs(data_dir: Path, configs: dict[str, StoredEvidenceSourceConfig]) -> None:
    payload = {
        "version": CONFIG_VERSION,
        "sources": {
            source_id: asdict(config)
            for source_id, config in configs.items()
            if source_id in SOURCE_DEFINITIONS
        },
    }
    _atomic_write_json(_config_path(data_dir), payload)


def _view_for_source(
    source_id: str,
    stored: StoredEvidenceSourceConfig | None,
    env: Mapping[str, str],
) -> EvidenceSourceConfig:
    _validate_source_id(source_id)
    definition = SOURCE_DEFINITIONS[source_id]
    local = stored or StoredEvidenceSourceConfig()
    env_key = str(definition["api_key_env"])
    env_base_url = str(definition["base_url_env"])
    env_api_key = env.get(env_key) or ""
    api_key = env_api_key or local.api_key
    api_key_source = "env" if env_api_key else ("local" if local.api_key else "none")
    base_url = _validate_base_url(env.get(env_base_url) or local.base_url or str(definition["default_base_url"]))
    enabled = local.enabled
    status = "configured" if enabled and api_key else "not_configured"
    return EvidenceSourceConfig(
        source_id=source_id,
        display_name=str(definition["display_name"]),
        source_type=str(definition["source_type"]),
        evidence_tier=str(definition["evidence_tier"]),
        enabled=enabled,
        status=status,
        base_url=base_url,
        api_key_present=bool(api_key),
        api_key_masked=_mask_secret(api_key),
        api_key_source=api_key_source,
        last_checked_at=local.last_checked_at,
        last_error=local.last_error,
        application_url=str(definition["application_url"]),
        docs_url=str(definition["docs_url"]),
        guidance=str(definition["guidance"]),
        can_satisfy_patent_gate=bool(definition["can_satisfy_patent_gate"]),
    )


def evidence_source_views(data_dir: Path, env: Mapping[str, str] | None = None) -> list[EvidenceSourceConfig]:
    stored = _load_stored_configs(data_dir)
    effective_env = os.environ if env is None else env
    return [
        _view_for_source(source_id, stored.get(source_id), effective_env)
        for source_id in SOURCE_DEFINITIONS
    ]


def update_evidence_source_config(
    data_dir: Path,
    source_id: str,
    patch: EvidenceSourceConfigPatch,
) -> EvidenceSourceConfig:
    _validate_source_id(source_id)
    configs = _load_stored_configs(data_dir)
    current = configs.get(source_id, StoredEvidenceSourceConfig())
    if patch.api_key is not None and patch.clear_api_key:
        raise ValueError("Pass either api_key or clear_api_key, not both.")
    next_config = StoredEvidenceSourceConfig(
        enabled=current.enabled if patch.enabled is None else patch.enabled,
        base_url=current.base_url if patch.base_url is None else _validate_base_url(patch.base_url),
        api_key="" if patch.clear_api_key else (_validate_api_key(patch.api_key) if patch.api_key is not None else current.api_key),
        last_checked_at=current.last_checked_at,
        last_error=current.last_error,
    )
    configs[source_id] = next_config
    _save_stored_configs(data_dir, configs)
    return _view_for_source(source_id, next_config, {})


def check_evidence_source_config(
    data_dir: Path,
    source_id: str,
    env: Mapping[str, str] | None = None,
) -> EvidenceSourceCheckResult:
    _validate_source_id(source_id)
    configs = _load_stored_configs(data_dir)
    effective_env = os.environ if env is None else env
    view = _view_for_source(source_id, configs.get(source_id), effective_env)
    checked_at = _now_iso()
    stored = configs.get(source_id, StoredEvidenceSourceConfig())
    stored.last_checked_at = checked_at
    stored.last_error = "" if view.status == "configured" else "not_configured"
    configs[source_id] = stored
    _save_stored_configs(data_dir, configs)
    return EvidenceSourceCheckResult(
        source_id=source_id,
        ok=view.status == "configured",
        status=view.status,
        detail="configured_local_check_only" if view.status == "configured" else "not_configured",
        live_search_available=False,
        last_checked_at=checked_at,
    )
