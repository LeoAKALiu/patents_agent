# Commercial Evidence Provider Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable PatSnap and Wanfang evidence-source skeletons so GrantAtlas can show source setup, evidence tiers, and gate semantics before live vendor calls are connected.

**Architecture:** Add a local evidence-source config store beside the existing desktop LLM config, expose redacted source status through a small API router, and register PatSnap/Wanfang as capability-aware provider skeletons. Project knowledge keeps patent evidence and non-patent literature counts separate, while the frontend adds source setup controls and source coverage indicators without creating fake candidates.

**Tech Stack:** FastAPI, Pydantic v2, local JSON config with 0600 permissions, existing SQLite project knowledge storage, React + TypeScript, Vitest, pytest.

## Global Constraints

- Start implementation from a clean worktree based on latest `origin/main`; if PR #130 has not landed in `origin/main`, wait for it or explicitly rebase this plan after it lands.
- Do not implement live PatSnap or Wanfang HTTP calls in this plan.
- Do not create synthetic/fake PatSnap or Wanfang candidates.
- Missing API keys must produce `not_configured` guidance, not `failed` or `no_hits`.
- PatSnap is a patent main evidence source and can satisfy the patent evidence gate once real candidates exist.
- Wanfang is a non-patent literature supplement and cannot satisfy the patent evidence gate by itself.
- Raw API keys must never be returned to the renderer, logged, written into reports, or stored in project knowledge JSON.
- Frontend copy must state that Wanfang improves background/creativity support but does not replace patent prior-art evidence.
- Keep changes scoped to source configuration and project evidence status; do not refactor unrelated project, export, deliberation, or drafting flows.

---

## File Structure

- Create `backend/app/evidence_sources.py`
  - Owns evidence-source definitions, local config persistence, validation, redaction, environment override, and source status views.
- Create `backend/app/api/evidence_sources.py`
  - Owns `GET /api/evidence-sources`, `PUT /api/evidence-sources/{source_id}/config`, and `POST /api/evidence-sources/{source_id}/check`.
- Modify `backend/app/main.py`
  - Includes the evidence source router.
- Modify `backend/app/schemas.py`
  - Adds evidence source API schemas and extends project knowledge schemas with patent/non-patent counts and candidate evidence fields.
- Modify `backend/app/knowledge/patent_search.py`
  - Adds `PatSnapPatentProvider` skeleton and includes it in the default provider chain ahead of fallback public sources.
- Create `backend/app/knowledge/non_patent_search.py`
  - Adds `WanfangLiteratureProvider` skeleton and a small typed interface for non-patent literature providers.
- Modify `backend/app/services/project_knowledge_service.py`
  - Adds source layering to search plans and enforces patent gate counts separately from non-patent literature counts.
- Modify `backend/app/api/project_knowledge.py`
  - Attaches evidence source status to project knowledge overview responses.
- Modify `frontend/src/api.ts`
  - Adds evidence source types and client functions.
- Modify `frontend/src/SettingsPanel.tsx`
  - Adds data source configuration cards.
- Modify `frontend/src/views/projectKnowledgeView.tsx`
  - Shows source coverage, evidence tier, and patent-gate status.
- Test files:
  - Create `tests/test_evidence_sources.py`
  - Create `tests/test_evidence_sources_api.py`
  - Modify `tests/test_patent_search_providers.py`
  - Modify `tests/test_project_knowledge.py`
  - Modify `frontend/src/api.test.ts`
  - Modify `frontend/src/SettingsPanel.test.tsx`
  - Modify `frontend/src/projectKnowledgeView.test.tsx`

## Task 0: Prepare Clean Implementation Worktree

**Files:**
- No file changes.

**Interfaces:**
- Consumes: Git repository and latest `origin/main`.
- Produces: Clean implementation branch `codex/commercial-evidence-provider-skeleton`.

- [ ] **Step 1: Record source identity**

Run:

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

Expected: current worktree identity is recorded in the worker notes before any edits.

- [ ] **Step 2: Create an isolated implementation worktree**

Run:

```bash
git fetch origin
git worktree add .worktrees/commercial-evidence-provider-skeleton -b codex/commercial-evidence-provider-skeleton origin/main
cd .worktrees/commercial-evidence-provider-skeleton
```

Expected: new branch `codex/commercial-evidence-provider-skeleton` exists in a clean worktree.

- [ ] **Step 3: Verify clean target**

Run:

```bash
git status --short --branch
git rev-parse --short HEAD
```

Expected: status has no modified, staged, or untracked files.

## Task 1: Backend Evidence Source Config Store

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/evidence_sources.py`
- Test: `tests/test_evidence_sources.py`

**Interfaces:**
- Consumes: `Settings.data_dir` paths used by existing desktop config.
- Produces:
  - `EvidenceSourceConfig`
  - `EvidenceSourceConfigPatch`
  - `EvidenceSourceCheckResult`
  - `evidence_source_views(data_dir: Path, env: Mapping[str, str] | None = None) -> list[EvidenceSourceConfig]`
  - `update_evidence_source_config(data_dir: Path, source_id: str, patch: EvidenceSourceConfigPatch) -> EvidenceSourceConfig`
  - `check_evidence_source_config(data_dir: Path, source_id: str, env: Mapping[str, str] | None = None) -> EvidenceSourceCheckResult`

- [ ] **Step 1: Write failing tests for config defaults, persistence, env override, and redaction**

Create `tests/test_evidence_sources.py`:

```python
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
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```bash
python3 -m pytest tests/test_evidence_sources.py -q
```

Expected: FAIL because `backend.app.evidence_sources` and the new schemas do not exist.

- [ ] **Step 3: Add evidence source schemas**

Modify `backend/app/schemas.py` near the desktop config schemas:

```python
class EvidenceSourceConfig(BaseModel):
    source_id: str
    display_name: str
    source_type: str = Field(pattern="^(patent|non_patent_literature|web_discovery)$")
    evidence_tier: str = Field(pattern="^(primary_patent|supplemental_literature|discovery_signal)$")
    enabled: bool = True
    status: str = Field(pattern="^(not_configured|configured|unavailable|quota_limited)$")
    base_url: str = ""
    api_key_present: bool = False
    api_key_masked: str = ""
    api_key_source: str = Field(default="none", pattern="^(env|local|none)$")
    last_checked_at: str = ""
    last_error: str = ""
    application_url: str = ""
    docs_url: str = ""
    guidance: str = ""
    can_satisfy_patent_gate: bool = False


class EvidenceSourceConfigPatch(BaseModel):
    api_key: str | None = None
    clear_api_key: bool = False
    base_url: str | None = None
    enabled: bool | None = None


class EvidenceSourceCheckResult(BaseModel):
    source_id: str
    ok: bool
    status: str = Field(pattern="^(not_configured|configured|unavailable|quota_limited)$")
    detail: str = ""
    live_search_available: bool = False
    last_checked_at: str = ""
```

- [ ] **Step 4: Implement local config store and views**

Create `backend/app/evidence_sources.py`:

```python
from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from backend.app.schemas import EvidenceSourceCheckResult, EvidenceSourceConfig, EvidenceSourceConfigPatch

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
    sources = raw.get("sources", {}) if isinstance(raw, dict) else {}
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
    api_key = env.get(env_key) or local.api_key
    api_key_source = "env" if env.get(env_key) else ("local" if local.api_key else "none")
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
    return _view_for_source(source_id, next_config, os.environ)


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
```

- [ ] **Step 5: Run backend config tests**

Run:

```bash
python3 -m pytest tests/test_evidence_sources.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add backend/app/schemas.py backend/app/evidence_sources.py tests/test_evidence_sources.py
git commit -m "feat: add evidence source config store"
```

## Task 2: Evidence Source API Router

**Files:**
- Create: `backend/app/api/evidence_sources.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_evidence_sources_api.py`

**Interfaces:**
- Consumes:
  - `evidence_source_views(data_dir)`
  - `update_evidence_source_config(data_dir, source_id, patch)`
  - `check_evidence_source_config(data_dir, source_id)`
- Produces:
  - `GET /api/evidence-sources`
  - `PUT /api/evidence-sources/{source_id}/config`
  - `POST /api/evidence-sources/{source_id}/check`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_evidence_sources_api.py`:

```python
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
        json={"api_key": "ps-secret-value-1234", "base_url": "https://connect.zhihuiya.com", "enabled": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_key_present"] is True
    assert payload["api_key_masked"].endswith("1234")
    assert "ps-secret-value" not in response.text


def test_check_evidence_source_config_is_local_only(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    client.put("/api/evidence-sources/wanfang_api/config", json={"api_key": "wf-secret-5678", "enabled": True})

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
```

- [ ] **Step 2: Run the API tests and verify failure**

Run:

```bash
python3 -m pytest tests/test_evidence_sources_api.py -q
```

Expected: FAIL because the router is not registered.

- [ ] **Step 3: Add API router**

Create `backend/app/api/evidence_sources.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.app.evidence_sources import (
    check_evidence_source_config,
    evidence_source_views,
    update_evidence_source_config,
)
from backend.app.schemas import EvidenceSourceConfigPatch
from backend.app.services.desktop_config_service import enforce_desktop_config_origin

router = APIRouter(tags=["evidence-sources"])


@router.get("/api/evidence-sources")
def list_evidence_sources(request: Request) -> dict:
    enforce_desktop_config_origin(request)
    return {"sources": [source.model_dump(mode="json") for source in evidence_source_views(request.app.state.settings.data_dir)]}


@router.put("/api/evidence-sources/{source_id}/config")
def put_evidence_source_config(source_id: str, payload: EvidenceSourceConfigPatch, request: Request) -> dict:
    enforce_desktop_config_origin(request)
    try:
        view = update_evidence_source_config(request.app.state.settings.data_dir, source_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "Unknown evidence source" in str(exc) else 422, detail=str(exc)) from exc
    return view.model_dump(mode="json")


@router.post("/api/evidence-sources/{source_id}/check")
def post_evidence_source_check(source_id: str, request: Request) -> dict:
    enforce_desktop_config_origin(request)
    try:
        result = check_evidence_source_config(request.app.state.settings.data_dir, source_id)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "Unknown evidence source" in str(exc) else 422, detail=str(exc)) from exc
    return result.model_dump(mode="json")
```

- [ ] **Step 4: Register the router**

Modify `backend/app/main.py`:

```python
from backend.app.api.evidence_sources import router as evidence_sources_router
```

Inside `create_app(...)`, beside other routers:

```python
app.include_router(evidence_sources_router)
```

- [ ] **Step 5: Run API tests**

Run:

```bash
python3 -m pytest tests/test_evidence_sources.py tests/test_evidence_sources_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add backend/app/api/evidence_sources.py backend/app/main.py tests/test_evidence_sources_api.py
git commit -m "feat: expose evidence source config api"
```

## Task 3: Provider Skeletons and Source Capabilities

**Files:**
- Modify: `backend/app/knowledge/patent_search.py`
- Create: `backend/app/knowledge/non_patent_search.py`
- Modify: `tests/test_patent_search_providers.py`
- Test: `tests/test_patent_search_providers.py`

**Interfaces:**
- Consumes:
  - `evidence_source_views(data_dir)`
  - `EvidenceSourceConfig`
- Produces:
  - `PatSnapPatentProvider(config: EvidenceSourceConfig)`
  - `WanfangLiteratureProvider(config: EvidenceSourceConfig)`
  - `NonPatentSearchHit`
  - `NonPatentSearchProvider`

- [ ] **Step 1: Write failing provider skeleton tests**

Append to `tests/test_patent_search_providers.py`:

```python
from backend.app.evidence_sources import evidence_source_views, update_evidence_source_config
from backend.app.knowledge.non_patent_search import WanfangLiteratureProvider
from backend.app.knowledge.patent_search import PatSnapPatentProvider, default_project_patent_providers
from backend.app.schemas import EvidenceSourceConfigPatch, PatentSearchFilters


def _source(tmp_path, source_id: str, *, configured: bool):
    if configured:
        update_evidence_source_config(tmp_path, source_id, EvidenceSourceConfigPatch(api_key=f"{source_id}-secret-1234", enabled=True))
    return {source.source_id: source for source in evidence_source_views(tmp_path, env={})}[source_id]


def test_patsnap_provider_skips_when_not_configured(tmp_path):
    provider = PatSnapPatentProvider(_source(tmp_path, "patsnap_api", configured=False))

    available, reason = provider.available()

    assert available is False
    assert "智慧芽" in reason
    assert "API key" in reason


def test_patsnap_provider_configured_skeleton_returns_no_fake_hits(tmp_path):
    provider = PatSnapPatentProvider(_source(tmp_path, "patsnap_api", configured=True))

    available, reason = provider.available()
    hits, warnings = provider.search("城市体检 智能体", filters=PatentSearchFilters(), limit=10)

    assert available is True
    assert reason is None
    assert hits == []
    assert warnings == ["patsnap_api_live_search_not_implemented"]


def test_default_patent_providers_put_patsnap_before_public_fallbacks(tmp_path):
    providers = default_project_patent_providers(data_dir=tmp_path)

    assert [provider.source_id for provider in providers][:2] == ["patsnap_api", "cnipa_epub"]


def test_wanfang_provider_is_non_patent_and_never_patent_gate(tmp_path):
    provider = WanfangLiteratureProvider(_source(tmp_path, "wanfang_api", configured=True))

    available, reason = provider.available()
    hits, warnings = provider.search("城市体检 任务编排", limit=10)

    assert available is True
    assert reason is None
    assert hits == []
    assert warnings == ["wanfang_api_live_search_not_implemented"]
    assert provider.can_satisfy_patent_gate is False
```

- [ ] **Step 2: Run provider tests and verify failure**

Run:

```bash
python3 -m pytest tests/test_patent_search_providers.py -q
```

Expected: FAIL because provider classes and `default_project_patent_providers(data_dir=...)` do not exist.

- [ ] **Step 3: Add PatSnap patent provider skeleton**

Modify `backend/app/knowledge/patent_search.py` imports:

```python
from pathlib import Path

from backend.app.evidence_sources import evidence_source_views
from backend.app.schemas import EvidenceSourceConfig
```

Add class before `CnipaEpubPatentProvider`:

```python
class PatSnapPatentProvider:
    name = "智慧芽 PatSnap"
    source_id = "patsnap_api"

    def __init__(self, config: EvidenceSourceConfig) -> None:
        self.config = config

    def available(self) -> tuple[bool, str | None]:
        if self.config.status != "configured" or not self.config.api_key_present:
            return False, "智慧芽 PatSnap API key 未配置；请在设置页的数据源中配置后启用商业专利检索。"
        return True, None

    def search(
        self,
        query: str,
        *,
        filters: PatentSearchFilters,
        limit: int,
    ) -> tuple[list[PatentSearchHit], list[str]]:
        del query, filters, limit
        return [], ["patsnap_api_live_search_not_implemented"]
```

Modify default provider factory:

```python
def default_project_patent_providers(data_dir: str | Path | None = None) -> list[PatentSearchProvider]:
    providers: list[PatentSearchProvider] = []
    if data_dir is not None:
        sources = {source.source_id: source for source in evidence_source_views(Path(data_dir))}
        providers.append(PatSnapPatentProvider(sources["patsnap_api"]))
    return [
        *providers,
        CnipaEpubPatentProvider(),
        GooglePatentsProvider(),
    ]
```

Modify `run_agent_search_plan(...)` provider construction in `backend/app/services/project_knowledge_service.py` in Task 4 to pass `data_dir` from the API path; for this task keep direct tests passing by allowing `data_dir=None`.

- [ ] **Step 4: Add Wanfang non-patent provider skeleton**

Create `backend/app/knowledge/non_patent_search.py`:

```python
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from backend.app.schemas import EvidenceSourceConfig


class NonPatentSearchHit(BaseModel):
    id: str
    source: str
    query: str
    title: str
    url: str = ""
    authors: list[str] = Field(default_factory=list)
    publication_year: str = ""
    abstract: str = ""
    evidence_kind: str = "non_patent_literature"


class NonPatentSearchProvider(Protocol):
    name: str
    source_id: str
    can_satisfy_patent_gate: bool

    def available(self) -> tuple[bool, str | None]: ...

    def search(self, query: str, *, limit: int) -> tuple[list[NonPatentSearchHit], list[str]]: ...


class WanfangLiteratureProvider:
    name = "万方"
    source_id = "wanfang_api"
    can_satisfy_patent_gate = False

    def __init__(self, config: EvidenceSourceConfig) -> None:
        self.config = config

    def available(self) -> tuple[bool, str | None]:
        if self.config.status != "configured" or not self.config.api_key_present:
            return False, "万方 API key 未配置；请在设置页的数据源中配置后启用非专利文献补强。"
        return True, None

    def search(self, query: str, *, limit: int) -> tuple[list[NonPatentSearchHit], list[str]]:
        del query, limit
        return [], ["wanfang_api_live_search_not_implemented"]
```

- [ ] **Step 5: Run provider tests**

Run:

```bash
python3 -m pytest tests/test_evidence_sources.py tests/test_patent_search_providers.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add backend/app/knowledge/patent_search.py backend/app/knowledge/non_patent_search.py tests/test_patent_search_providers.py
git commit -m "feat: add commercial evidence provider skeletons"
```

## Task 4: Project Knowledge Evidence Gate Integration

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/project_knowledge_service.py`
- Modify: `backend/app/api/project_knowledge.py`
- Modify: `tests/test_project_knowledge.py`
- Test: `tests/test_project_knowledge.py`

**Interfaces:**
- Consumes:
  - `EvidenceSourceConfig`
  - `default_project_patent_providers(data_dir=...)`
- Produces:
  - `ProjectKnowledgeOverview.source_statuses`
  - `ProjectKnowledgeState.patent_document_count`
  - `ProjectKnowledgeState.non_patent_document_count`
  - `PriorArtCandidate.evidence_kind`
  - `PriorArtCandidate.can_satisfy_patent_gate`

- [ ] **Step 1: Write failing project knowledge tests**

Append to `tests/test_project_knowledge.py`:

```python
from backend.app.knowledge.patent_search import patent_hit_to_candidate
from backend.app.schemas import (
    AgentSearchPlan,
    PatentSearchHit,
    PriorArtCandidate,
    ProjectKnowledgeState,
    ProjectSearchLedger,
)
from backend.app.services.project_knowledge_service import create_project_corpus_from_included_candidates, knowledge_overview


def test_knowledge_overview_includes_evidence_source_statuses(store, sample_project):
    overview = knowledge_overview(store, sample_project.id, source_statuses=[])

    assert overview.source_statuses == []


def test_non_patent_only_included_candidates_do_not_make_project_ready(store, sample_project):
    state = ProjectKnowledgeState(
        project_id=sample_project.id,
        status="candidates_pending",
        active_plan_id="plan-1",
        last_search_at="2026-07-01T00:00:00Z",
        candidate_count=1,
    )
    store.upsert_project_knowledge_state(state)
    candidate = PriorArtCandidate(
        id="wanfang-candidate-1",
        project_id=sample_project.id,
        plan_id="plan-1",
        source="wanfang_api",
        title="城市体检智能体任务编排研究",
        url="https://apps.wanfangdata.com.cn/example",
        user_decision="include",
        evidence_kind="non_patent_literature",
        can_satisfy_patent_gate=False,
    )
    store.replace_agent_search_run(
        project_id=sample_project.id,
        plan=store.create_agent_search_plan(
            AgentSearchPlan(
                id="plan-1",
                project_id=sample_project.id,
                intent_id="intent-1",
                status="completed",
            )
        ),
        candidates=[candidate],
        ledger=ProjectSearchLedger(id="ledger-1", project_id=sample_project.id, plan_id="plan-1"),
        state=state,
    )

    overview = create_project_corpus_from_included_candidates(store, sample_project.id, "plan-1")

    assert overview.state.status == "needs_supplemental_search"
    assert overview.state.document_count == 1
    assert overview.state.patent_document_count == 0
    assert overview.state.non_patent_document_count == 1
    assert "non_patent_only" in overview.state.quality_flags


def test_patent_candidate_sets_patent_gate_fields(store, sample_project):
    hit = PatentSearchHit(
        id="hit-1",
        source="patsnap_api",
        query="城市体检 智能体",
        title="城市体检智能体调度方法",
        publication_number="CN112233445A",
        url="https://example.com/patent/CN112233445A",
    )

    candidate = patent_hit_to_candidate(hit, project_id=sample_project.id, plan_id="plan-1", strategy_group_id="broad")

    assert candidate.evidence_kind == "patent"
    assert candidate.can_satisfy_patent_gate is True
```

If the existing `tests/test_project_knowledge.py` fixtures use different fixture names than `store` or `sample_project`, adapt the test to the local fixture names by reusing the existing fixture creation helpers in that file.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py -q
```

Expected: FAIL because the new fields and optional `source_statuses` parameter do not exist.

- [ ] **Step 3: Extend project knowledge schemas**

Modify `ProjectKnowledgeState` in `backend/app/schemas.py`:

```python
    patent_document_count: int = 0
    non_patent_document_count: int = 0
```

Modify `PriorArtCandidate`:

```python
    evidence_kind: str = Field(default="patent", pattern="^(patent|non_patent_literature|web_discovery)$")
    can_satisfy_patent_gate: bool = True
```

Modify `ProjectKnowledgeOverview`:

```python
    source_statuses: list[EvidenceSourceConfig] = Field(default_factory=list)
```

- [ ] **Step 4: Set evidence gate fields on patent candidates**

Modify `patent_hit_to_candidate(...)` in `backend/app/knowledge/patent_search.py` so returned `PriorArtCandidate` includes:

```python
        evidence_kind="patent",
        can_satisfy_patent_gate=hit.source in {"patsnap_api", "cnipa_official_export", "cnipa_epub", "wipo_patentscope", "google_patents"},
```

- [ ] **Step 5: Add source statuses to overview**

Modify `knowledge_overview(...)` in `backend/app/services/project_knowledge_service.py`:

```python
def knowledge_overview(
    store: SQLiteStore,
    project_id: str,
    source_statuses: list[EvidenceSourceConfig] | None = None,
) -> ProjectKnowledgeOverview:
    state = store.get_project_knowledge_state(project_id) or ProjectKnowledgeState(project_id=project_id)
    latest_plan = store.get_latest_agent_search_plan(project_id)
    candidates = store.list_prior_art_candidates(project_id, latest_plan.id if latest_plan else None)
    latest_corpus_version = None
    if state.status != "stale" and state.active_corpus_version_id:
        latest_corpus_version = store.get_project_corpus_version(project_id, state.active_corpus_version_id)
    return ProjectKnowledgeOverview(
        state=state,
        latest_intent=store.get_latest_search_intent(project_id),
        latest_plan=latest_plan,
        candidates=candidates,
        latest_corpus_version=latest_corpus_version,
        source_statuses=source_statuses or [],
    )
```

Modify `backend/app/api/project_knowledge.py`:

```python
from backend.app.evidence_sources import evidence_source_views
```

In `get_project_knowledge(...)`:

```python
    source_statuses = evidence_source_views(request.app.state.settings.data_dir)
    return knowledge_overview(request.app.state.store, project_id, source_statuses=source_statuses).model_dump(mode="json")
```

Apply the same `source_statuses` wrapping in API responses after `regenerate_project_knowledge`, `run_agent_search_plan`, and `create_project_corpus_from_included_candidates` by replacing returned overview with:

```python
overview = overview.model_copy(update={"source_statuses": evidence_source_views(request.app.state.settings.data_dir)})
return overview.model_dump(mode="json")
```

- [ ] **Step 6: Keep search plans source-layered**

Modify constants and `_build_plan(...)` in `backend/app/services/project_knowledge_service.py`:

```python
PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES = ["patsnap_api", "cnipa_official_export", "cnipa_epub", "wipo_patentscope", "google_patents"]
PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES = ["wanfang_api"]
PROJECT_PATENT_PROVIDER_SOURCE_SET = frozenset(PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES)
```

Set plan metadata:

```python
        target_sources=[*PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES, *PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES],
        metadata={
            "primary_patent_sources": PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES,
            "supplemental_literature_sources": PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES,
            "fallback_sources": ["cnipa_official_export", "cnipa_epub", "wipo_patentscope", "google_patents"],
        },
```

Set each patent strategy group's `sources` to `PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES`. Add a third strategy group for literature supplement:

```python
            SearchPlanStrategyGroup(
                id="supplemental-literature",
                label="非专利文献补强",
                purpose="补充论文、期刊、会议和科技文献线索，用于背景技术和创造性论证补强。",
                queries=[core_query],
                sources=list(PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES),
            ),
```

- [ ] **Step 7: Enforce patent and non-patent corpus counts**

Modify `create_project_corpus_from_included_candidates(...)`:

```python
    patent_included = [candidate for candidate in included if candidate.can_satisfy_patent_gate and candidate.evidence_kind == "patent"]
    non_patent_included = [candidate for candidate in included if candidate.evidence_kind == "non_patent_literature" or not candidate.can_satisfy_patent_gate]
    non_patent_only = bool(non_patent_included) and not patent_included
```

Use these state updates:

```python
            "document_count": version.document_count,
            "patent_document_count": len(patent_included),
            "non_patent_document_count": len(non_patent_included),
```

Set quality flags:

```python
    if non_patent_only:
        quality_flags = ["non_patent_only"]
        state_status = "needs_supplemental_search"
    elif non_patent_included:
        quality_flags = ["non_patent_source"]
        state_status = "needs_supplemental_search"
    elif patent_included:
        quality_flags = []
        state_status = "ready"
    else:
        quality_flags = ["empty_corpus"]
        state_status = "needs_supplemental_search"
```

- [ ] **Step 8: Pass data dir into default providers from API runtime**

Modify `run_agent_search_plan(...)` signature:

```python
def run_agent_search_plan(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
    providers: list[PatentSearchProvider] | None = None,
    data_dir: str | Path | None = None,
) -> ProjectKnowledgeOverview:
```

Modify provider creation:

```python
provider_chain = list(providers) if providers is not None else default_project_patent_providers(data_dir=data_dir)
```

Modify `backend/app/api/project_knowledge.py` call:

```python
            data_dir=request.app.state.settings.data_dir,
```

- [ ] **Step 9: Run project knowledge tests**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py tests/test_patent_search_providers.py tests/test_evidence_sources.py tests/test_evidence_sources_api.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit Task 4**

```bash
git add backend/app/schemas.py backend/app/knowledge/patent_search.py backend/app/services/project_knowledge_service.py backend/app/api/project_knowledge.py tests/test_project_knowledge.py
git commit -m "feat: add evidence source gates to project knowledge"
```

## Task 5: Frontend API Types and Client Functions

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/api.test.ts`

**Interfaces:**
- Consumes:
  - `GET /api/evidence-sources`
  - `PUT /api/evidence-sources/{source_id}/config`
  - `POST /api/evidence-sources/{source_id}/check`
- Produces:
  - `EvidenceSourceConfig`
  - `EvidenceSourceConfigPatch`
  - `EvidenceSourceCheckResult`
  - `listEvidenceSources()`
  - `updateEvidenceSourceConfig(sourceId, payload)`
  - `checkEvidenceSourceConfig(sourceId)`

- [ ] **Step 1: Write failing API client tests**

Append to `frontend/src/api.test.ts`:

```typescript
import {
  checkEvidenceSourceConfig,
  listEvidenceSources,
  updateEvidenceSourceConfig,
  type EvidenceSourceConfig,
} from "./api";

describe("evidence source api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("lists evidence sources", async () => {
    const sources: EvidenceSourceConfig[] = [
      {
        source_id: "patsnap_api",
        display_name: "智慧芽 PatSnap",
        source_type: "patent",
        evidence_tier: "primary_patent",
        enabled: true,
        status: "not_configured",
        base_url: "https://connect.zhihuiya.com",
        api_key_present: false,
        api_key_masked: "",
        api_key_source: "none",
        last_checked_at: "",
        last_error: "",
        application_url: "https://open.zhihuiya.com/",
        docs_url: "https://open.zhihuiya.com/devportal",
        guidance: "配置智慧芽 API key 后可启用中文及全球专利主检索。",
        can_satisfy_patent_gate: true,
      },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ sources }), { status: 200 })),
    );

    await expect(listEvidenceSources()).resolves.toEqual(sources);
  });

  it("updates evidence source config without requiring caller to include raw key in response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            source_id: "patsnap_api",
            display_name: "智慧芽 PatSnap",
            source_type: "patent",
            evidence_tier: "primary_patent",
            enabled: true,
            status: "configured",
            base_url: "https://connect.zhihuiya.com",
            api_key_present: true,
            api_key_masked: "••••1234",
            api_key_source: "local",
            last_checked_at: "",
            last_error: "",
            application_url: "https://open.zhihuiya.com/",
            docs_url: "https://open.zhihuiya.com/devportal",
            guidance: "配置智慧芽 API key 后可启用中文及全球专利主检索。",
            can_satisfy_patent_gate: true,
          }),
          { status: 200 },
        ),
      ),
    );

    const result = await updateEvidenceSourceConfig("patsnap_api", { api_key: "secret-1234", enabled: true });

    expect(result.api_key_masked).toBe("••••1234");
    expect(fetch).toHaveBeenCalledWith(
      "/api/evidence-sources/patsnap_api/config",
      expect.objectContaining({ method: "PUT" }),
    );
  });

  it("checks evidence source config", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            source_id: "wanfang_api",
            ok: true,
            status: "configured",
            detail: "configured_local_check_only",
            live_search_available: false,
            last_checked_at: "2026-07-01T00:00:00Z",
          }),
          { status: 200 },
        ),
      ),
    );

    await expect(checkEvidenceSourceConfig("wanfang_api")).resolves.toMatchObject({
      source_id: "wanfang_api",
      live_search_available: false,
    });
  });
});
```

- [ ] **Step 2: Run frontend API test and verify failure**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts
```

Expected: FAIL because the types and functions do not exist.

- [ ] **Step 3: Add frontend API types**

Modify `frontend/src/api.ts` near config types:

```typescript
export type EvidenceSourceType = "patent" | "non_patent_literature" | "web_discovery";
export type EvidenceTier = "primary_patent" | "supplemental_literature" | "discovery_signal";
export type EvidenceSourceStatus = "not_configured" | "configured" | "unavailable" | "quota_limited";
export type EvidenceSourceKeySource = "env" | "local" | "none";

export interface EvidenceSourceConfig {
  source_id: string;
  display_name: string;
  source_type: EvidenceSourceType;
  evidence_tier: EvidenceTier;
  enabled: boolean;
  status: EvidenceSourceStatus;
  base_url: string;
  api_key_present: boolean;
  api_key_masked: string;
  api_key_source: EvidenceSourceKeySource;
  last_checked_at: string;
  last_error: string;
  application_url: string;
  docs_url: string;
  guidance: string;
  can_satisfy_patent_gate: boolean;
}

export interface EvidenceSourceConfigPatch {
  api_key?: string;
  clear_api_key?: boolean;
  base_url?: string;
  enabled?: boolean;
}

export interface EvidenceSourceCheckResult {
  source_id: string;
  ok: boolean;
  status: EvidenceSourceStatus;
  detail: string;
  live_search_available: boolean;
  last_checked_at: string;
}
```

Extend existing interfaces:

```typescript
export interface ProjectKnowledgeState {
  patent_document_count?: number;
  non_patent_document_count?: number;
}

export interface PriorArtCandidate {
  evidence_kind?: "patent" | "non_patent_literature" | "web_discovery";
  can_satisfy_patent_gate?: boolean;
}

export interface ProjectKnowledgeOverview {
  source_statuses?: EvidenceSourceConfig[];
}
```

Preserve existing fields in these interfaces; add only the new optional fields.

- [ ] **Step 4: Add frontend API functions**

Modify `frontend/src/api.ts`:

```typescript
export async function listEvidenceSources(): Promise<EvidenceSourceConfig[]> {
  const data = await request<{ sources: EvidenceSourceConfig[] }>("/api/evidence-sources");
  return data.sources;
}

export async function updateEvidenceSourceConfig(
  sourceId: string,
  payload: EvidenceSourceConfigPatch,
): Promise<EvidenceSourceConfig> {
  return request<EvidenceSourceConfig>(`/api/evidence-sources/${sourceId}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function checkEvidenceSourceConfig(sourceId: string): Promise<EvidenceSourceCheckResult> {
  return request<EvidenceSourceCheckResult>(`/api/evidence-sources/${sourceId}/check`, {
    method: "POST",
  });
}
```

- [ ] **Step 5: Run frontend API tests**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add frontend/src/api.ts frontend/src/api.test.ts
git commit -m "feat: add evidence source frontend api"
```

## Task 6: Settings Page Data Source Cards

**Files:**
- Modify: `frontend/src/SettingsPanel.tsx`
- Modify: `frontend/src/SettingsPanel.test.tsx`

**Interfaces:**
- Consumes:
  - `listEvidenceSources()`
  - `updateEvidenceSourceConfig(sourceId, payload)`
  - `checkEvidenceSourceConfig(sourceId)`
- Produces:
  - A “数据源” settings section with PatSnap and Wanfang configuration cards.

- [ ] **Step 1: Write failing settings UI tests**

Extend mocks in `frontend/src/SettingsPanel.test.tsx`:

```typescript
  checkEvidenceSourceConfig: vi.fn(),
  listEvidenceSources: vi.fn(),
  updateEvidenceSourceConfig: vi.fn(),
```

Add test data:

```typescript
const evidenceSources = [
  {
    source_id: "patsnap_api",
    display_name: "智慧芽 PatSnap",
    source_type: "patent",
    evidence_tier: "primary_patent",
    enabled: true,
    status: "not_configured",
    base_url: "https://connect.zhihuiya.com",
    api_key_present: false,
    api_key_masked: "",
    api_key_source: "none",
    last_checked_at: "",
    last_error: "",
    application_url: "https://open.zhihuiya.com/",
    docs_url: "https://open.zhihuiya.com/devportal",
    guidance: "配置智慧芽 API key 后可启用中文及全球专利主检索。",
    can_satisfy_patent_gate: true,
  },
  {
    source_id: "wanfang_api",
    display_name: "万方",
    source_type: "non_patent_literature",
    evidence_tier: "supplemental_literature",
    enabled: true,
    status: "not_configured",
    base_url: "https://apps.wanfangdata.com.cn/open",
    api_key_present: false,
    api_key_masked: "",
    api_key_source: "none",
    last_checked_at: "",
    last_error: "",
    application_url: "https://apps.wanfangdata.com.cn/open/market/apis",
    docs_url: "https://apps.wanfangdata.com.cn/open/docs",
    guidance: "配置万方 API key 后可补充论文、期刊、会议与科技文献。",
    can_satisfy_patent_gate: false,
  },
] as const;
```

Add tests:

```typescript
it("renders evidence source setup guidance", async () => {
  vi.mocked(getDesktopConfig).mockResolvedValue(configView);
  vi.mocked(listEvidenceSources).mockResolvedValue([...evidenceSources]);
  vi.mocked(checkDesktopConfigHealth).mockResolvedValue({
    ok: false,
    model: "deepseek-chat",
    api_key_source: "none",
    latency_ms: 0,
    status_code: 0,
    error: "no_api_key",
  });

  render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);

  expect(await screen.findByText("数据源")).toBeInTheDocument();
  expect(screen.getByText("智慧芽 PatSnap")).toBeInTheDocument();
  expect(screen.getByText("万方")).toBeInTheDocument();
  expect(screen.getByText(/不替代专利证据门控/)).toBeInTheDocument();
});

it("saves a PatSnap evidence source key", async () => {
  vi.mocked(getDesktopConfig).mockResolvedValue(configView);
  vi.mocked(listEvidenceSources).mockResolvedValue([...evidenceSources]);
  vi.mocked(updateEvidenceSourceConfig).mockResolvedValue({
    ...evidenceSources[0],
    status: "configured",
    api_key_present: true,
    api_key_masked: "••••1234",
    api_key_source: "local",
  });

  render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);
  await screen.findByText("智慧芽 PatSnap");
  await userEvent.type(screen.getByLabelText("智慧芽 PatSnap API Key"), "ps-secret-1234");
  await userEvent.click(screen.getByRole("button", { name: "保存智慧芽 PatSnap" }));

  expect(updateEvidenceSourceConfig).toHaveBeenCalledWith("patsnap_api", expect.objectContaining({ api_key: "ps-secret-1234" }));
  expect(await screen.findByText("••••1234")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run settings tests and verify failure**

Run:

```bash
npm --prefix frontend test -- --run src/SettingsPanel.test.tsx
```

Expected: FAIL because settings panel does not load or render evidence sources.

- [ ] **Step 3: Import evidence source API functions**

Modify `frontend/src/SettingsPanel.tsx` imports:

```typescript
  checkEvidenceSourceConfig,
  listEvidenceSources,
  updateEvidenceSourceConfig,
  type EvidenceSourceConfig,
```

- [ ] **Step 4: Add component state and loader**

Inside `SettingsPanel`:

```typescript
const [evidenceSources, setEvidenceSources] = useState<EvidenceSourceConfig[]>([]);
const [evidenceSourceInputs, setEvidenceSourceInputs] = useState<Record<string, { apiKey: string; baseUrl: string }>>({});
const [evidenceSourceMessage, setEvidenceSourceMessage] = useState<string>("");
```

In the existing load effect, after desktop config load:

```typescript
const sources = await listEvidenceSources();
setEvidenceSources(sources);
setEvidenceSourceInputs(
  Object.fromEntries(sources.map((source) => [source.source_id, { apiKey: "", baseUrl: source.base_url }]))
);
```

- [ ] **Step 5: Add save/check handlers**

Inside `SettingsPanel`:

```typescript
async function handleSaveEvidenceSource(source: EvidenceSourceConfig) {
  const input = evidenceSourceInputs[source.source_id] ?? { apiKey: "", baseUrl: source.base_url };
  const updated = await updateEvidenceSourceConfig(source.source_id, {
    api_key: input.apiKey || undefined,
    base_url: input.baseUrl || undefined,
    enabled: source.enabled,
  });
  setEvidenceSources((current) => current.map((item) => (item.source_id === updated.source_id ? updated : item)));
  setEvidenceSourceInputs((current) => ({ ...current, [source.source_id]: { apiKey: "", baseUrl: updated.base_url } }));
  setEvidenceSourceMessage(`${source.display_name} 配置已保存`);
}

async function handleCheckEvidenceSource(source: EvidenceSourceConfig) {
  const result = await checkEvidenceSourceConfig(source.source_id);
  setEvidenceSourceMessage(
    result.ok ? `${source.display_name} 本地配置已就绪，真实检索接口仍保持关闭。` : `${source.display_name} 尚未配置 API key。`,
  );
}
```

- [ ] **Step 6: Render data source cards**

Add a settings group below the LLM config group:

```tsx
<section className="settings-group">
  <div className="settings-group-header">
    <div>
      <h3>数据源</h3>
      <p>配置商业专利库和非专利文献库。未配置时只显示接入指引，不会被当作检索失败。</p>
    </div>
  </div>
  <div className="settings-source-grid">
    {evidenceSources.map((source) => {
      const input = evidenceSourceInputs[source.source_id] ?? { apiKey: "", baseUrl: source.base_url };
      return (
        <article className="settings-source-card" key={source.source_id}>
          <div className="settings-source-card-header">
            <div>
              <h4>{source.display_name}</h4>
              <p>{source.can_satisfy_patent_gate ? "专利主证据源" : "非专利文献补强源"}</p>
            </div>
            <span className="status-pill">{source.status === "configured" ? "已配置" : "未配置"}</span>
          </div>
          <p className="text-sm text-[var(--text-primary)]/65">{source.guidance}</p>
          {!source.can_satisfy_patent_gate && (
            <p className="text-sm text-[var(--text-primary)]/65">万方命中只用于背景技术和创造性论证补强，不替代专利证据门控。</p>
          )}
          <label>
            {source.display_name} API Key
            <input
              aria-label={`${source.display_name} API Key`}
              value={input.apiKey}
              onChange={(event) =>
                setEvidenceSourceInputs((current) => ({
                  ...current,
                  [source.source_id]: { ...input, apiKey: event.target.value },
                }))
              }
              type="password"
            />
          </label>
          <label>
            Base URL
            <input
              value={input.baseUrl}
              onChange={(event) =>
                setEvidenceSourceInputs((current) => ({
                  ...current,
                  [source.source_id]: { ...input, baseUrl: event.target.value },
                }))
              }
            />
          </label>
          {source.api_key_masked && <p>{source.api_key_masked}</p>}
          <div className="settings-source-actions">
            <button type="button" onClick={() => handleSaveEvidenceSource(source)}>
              保存{source.display_name}
            </button>
            <button type="button" onClick={() => handleCheckEvidenceSource(source)}>
              测试配置
            </button>
            <a href={source.application_url} rel="noreferrer" target="_blank">
              申请入口
            </a>
          </div>
        </article>
      );
    })}
  </div>
  {evidenceSourceMessage && <p>{evidenceSourceMessage}</p>}
</section>
```

- [ ] **Step 7: Run settings tests**

Run:

```bash
npm --prefix frontend test -- --run src/SettingsPanel.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit Task 6**

```bash
git add frontend/src/SettingsPanel.tsx frontend/src/SettingsPanel.test.tsx
git commit -m "feat: add evidence source settings cards"
```

## Task 7: Knowledge Page Source Coverage and Gate Copy

**Files:**
- Modify: `frontend/src/views/projectKnowledgeView.tsx`
- Modify: `frontend/src/projectKnowledgeView.test.tsx`

**Interfaces:**
- Consumes:
  - `ProjectKnowledgeOverview.source_statuses`
  - `ProjectKnowledgeState.patent_document_count`
  - `ProjectKnowledgeState.non_patent_document_count`
  - `PriorArtCandidate.evidence_kind`
  - `PriorArtCandidate.can_satisfy_patent_gate`
- Produces:
  - Knowledge status cards for patent evidence coverage and non-patent literature coverage.
  - Candidate cards with evidence tier and gate eligibility.
  - Warning copy for `source_not_configured`, `source_configured_not_implemented`, and `non_patent_only`.

- [ ] **Step 1: Write failing knowledge UI tests**

Append to `frontend/src/projectKnowledgeView.test.tsx`:

```typescript
it("shows PatSnap and Wanfang source setup separately from search failure", () => {
  render(
    <ProjectKnowledgeView
      selectedProject={project}
      knowledge={{
        state: {
          project_id: project.id,
          status: "search_plan_pending",
          active_intent_id: "intent-1",
          active_plan_id: "plan-1",
          active_corpus_version_id: "",
          last_search_at: "",
          last_indexed_at: "",
          staleness_reason: "",
          document_count: 0,
          patent_document_count: 0,
          non_patent_document_count: 0,
          candidate_count: 0,
          claim_coverage: 0,
          fulltext_coverage: 0,
          quality_flags: ["source_not_configured"],
        },
        latest_intent: null,
        latest_plan: null,
        candidates: [],
        latest_corpus_version: null,
        source_statuses: [
          {
            source_id: "patsnap_api",
            display_name: "智慧芽 PatSnap",
            source_type: "patent",
            evidence_tier: "primary_patent",
            enabled: true,
            status: "not_configured",
            base_url: "https://connect.zhihuiya.com",
            api_key_present: false,
            api_key_masked: "",
            api_key_source: "none",
            last_checked_at: "",
            last_error: "",
            application_url: "https://open.zhihuiya.com/",
            docs_url: "https://open.zhihuiya.com/devportal",
            guidance: "配置智慧芽 API key 后可启用中文及全球专利主检索。",
            can_satisfy_patent_gate: true,
          },
          {
            source_id: "wanfang_api",
            display_name: "万方",
            source_type: "non_patent_literature",
            evidence_tier: "supplemental_literature",
            enabled: true,
            status: "not_configured",
            base_url: "https://apps.wanfangdata.com.cn/open",
            api_key_present: false,
            api_key_masked: "",
            api_key_source: "none",
            last_checked_at: "",
            last_error: "",
            application_url: "https://apps.wanfangdata.com.cn/open/market/apis",
            docs_url: "https://apps.wanfangdata.com.cn/open/docs",
            guidance: "配置万方 API key 后可补充论文、期刊、会议与科技文献。",
            can_satisfy_patent_gate: false,
          },
        ],
      }}
      busy=""
      onGenerateKnowledgePlan={() => undefined}
      onRunKnowledgeSearch={() => undefined}
      onCandidateDecision={() => undefined}
      onBuildProjectCorpus={() => undefined}
    />,
  );

  expect(screen.getByText("专利证据覆盖")).toBeInTheDocument();
  expect(screen.getByText("非专利文献覆盖")).toBeInTheDocument();
  expect(screen.getByText(/智慧芽 PatSnap/)).toBeInTheDocument();
  expect(screen.getByText(/万方/)).toBeInTheDocument();
  expect(screen.getByText(/未配置不是检索失败/)).toBeInTheDocument();
});

it("marks Wanfang candidate as supplemental and not patent-gate eligible", () => {
  render(
    <ProjectKnowledgeView
      selectedProject={project}
      knowledge={{
        state: {
          project_id: project.id,
          status: "needs_supplemental_search",
          active_intent_id: "intent-1",
          active_plan_id: "plan-1",
          active_corpus_version_id: "version-1",
          last_search_at: "2026-07-01T00:00:00Z",
          last_indexed_at: "2026-07-01T00:00:00Z",
          staleness_reason: "",
          document_count: 1,
          patent_document_count: 0,
          non_patent_document_count: 1,
          candidate_count: 1,
          claim_coverage: 0,
          fulltext_coverage: 0,
          quality_flags: ["non_patent_only"],
        },
        latest_intent: null,
        latest_plan: null,
        candidates: [
          {
            id: "wanfang-1",
            project_id: project.id,
            plan_id: "plan-1",
            source: "wanfang_api",
            title: "城市体检智能体任务编排研究",
            publication_number: null,
            application_number: null,
            applicant: "",
            publication_date: "",
            grant_date: "",
            abstract: "讨论城市体检任务编排。",
            url: "https://apps.wanfangdata.com.cn/example",
            relevance_score: 0,
            matched_terms: [],
            ipc: [],
            cpc: [],
            family_id: "",
            duplicate_of: "",
            fulltext_status: "unknown",
            recommended_action: "review",
            recommendation_reason: "",
            user_decision: "include",
            metadata: {},
            evidence_kind: "non_patent_literature",
            can_satisfy_patent_gate: false,
            created_at: "",
          },
        ],
        latest_corpus_version: null,
        source_statuses: [],
      }}
      busy=""
      onGenerateKnowledgePlan={() => undefined}
      onRunKnowledgeSearch={() => undefined}
      onCandidateDecision={() => undefined}
      onBuildProjectCorpus={() => undefined}
    />,
  );

  expect(screen.getByText("补强证据")).toBeInTheDocument();
  expect(screen.getByText("不可用于授权门控")).toBeInTheDocument();
  expect(screen.getByText(/尚未形成可支撑授权判断的专利证据库/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run knowledge UI tests and verify failure**

Run:

```bash
npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx
```

Expected: FAIL because the UI does not render the new source coverage or gate labels.

- [ ] **Step 3: Add quality flag copy**

Modify `qualityFlagCopy(...)` in `frontend/src/views/projectKnowledgeView.tsx`:

```typescript
    case "source_not_configured":
      return {
        tone: "info",
        text: "商业数据源未配置不是检索失败。配置智慧芽可扩大专利主检索覆盖，配置万方可补充非专利文献。",
      };
    case "source_configured_not_implemented":
      return {
        tone: "info",
        text: "数据源本地配置已就绪，真实供应商检索接口仍保持关闭；当前不会生成假候选。",
      };
    case "non_patent_only":
      return {
        tone: "warning",
        text: "已找到非专利文献线索，但尚未形成可支撑授权判断的专利证据库。请配置或运行专利检索源。",
      };
```

- [ ] **Step 4: Add evidence labels**

Add helper functions:

```typescript
function evidenceTierLabel(candidate: PriorArtCandidate): string {
  if (candidate.evidence_kind === "non_patent_literature") return "补强证据";
  if (candidate.can_satisfy_patent_gate === false) return "发现线索";
  return "主证据";
}

function patentGateLabel(candidate: PriorArtCandidate): string {
  return candidate.can_satisfy_patent_gate === false ? "不可用于授权门控" : "可用于授权门控";
}
```

- [ ] **Step 5: Add source coverage status cards**

In the top status grid, replace the five-card grid with seven cards:

```tsx
<StatusPill label="知识状态" value={statusLabels[status] ?? status} />
<StatusPill label="候选文献" value={String(state?.candidate_count ?? candidates.length)} />
<StatusPill label="入库文献" value={String(state?.document_count ?? 0)} />
<StatusPill label="专利证据覆盖" value={String(state?.patent_document_count ?? 0)} />
<StatusPill label="非专利文献覆盖" value={String(state?.non_patent_document_count ?? 0)} />
<StatusPill label="权利要求覆盖" value={percent(state?.claim_coverage ?? 0)} />
<StatusPill label="全文覆盖" value={percent(state?.fulltext_coverage ?? 0)} />
```

- [ ] **Step 6: Render source setup summary**

Below guidance cards:

```tsx
{(knowledge?.source_statuses ?? []).length > 0 && (
  <div className="grid gap-3 md:grid-cols-2">
    {(knowledge?.source_statuses ?? []).map((source) => (
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-3" key={source.source_id}>
        <div className="flex items-center justify-between gap-3">
          <strong>{source.display_name}</strong>
          <span>{source.status === "configured" ? "已配置" : "未配置"}</span>
        </div>
        <p className="text-sm text-[var(--text-primary)]/65">
          {source.can_satisfy_patent_gate ? "专利主证据源" : "非专利文献补强源"}
        </p>
        <p className="text-sm text-[var(--text-primary)]/65">{source.guidance}</p>
        {source.status === "not_configured" && <p className="text-sm text-[var(--text-primary)]/65">未配置不是检索失败。</p>}
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 7: Render evidence tier on candidate cards**

Inside each candidate card badge row:

```tsx
<span className="rounded-full border border-[var(--border-subtle)] px-2 py-1 text-xs">{evidenceTierLabel(candidate)}</span>
<span className="rounded-full border border-[var(--border-subtle)] px-2 py-1 text-xs">{patentGateLabel(candidate)}</span>
```

- [ ] **Step 8: Run knowledge UI tests**

Run:

```bash
npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx
```

Expected: PASS.

- [ ] **Step 9: Commit Task 7**

```bash
git add frontend/src/views/projectKnowledgeView.tsx frontend/src/projectKnowledgeView.test.tsx
git commit -m "feat: show evidence source coverage in knowledge view"
```

## Task 8: Integrated Verification

**Files:**
- No product code changes unless verification exposes a defect.

**Interfaces:**
- Consumes: All prior task outputs.
- Produces: A verified branch ready for PR.

- [ ] **Step 1: Run backend targeted tests**

Run:

```bash
python3 -m pytest tests/test_evidence_sources.py tests/test_evidence_sources_api.py tests/test_patent_search_providers.py tests/test_project_knowledge.py tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend targeted tests**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts src/SettingsPanel.test.tsx src/projectKnowledgeView.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS.

- [ ] **Step 4: Run backend full pytest if time allows**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS. If this fails outside the touched area, record the failing test names and failure messages before deciding whether it belongs to this branch.

- [ ] **Step 5: Manual smoke through local app**

Run backend and frontend in the implementation worktree:

```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

Expected:

- Settings page shows “数据源”.
- PatSnap and Wanfang cards show `未配置`.
- Saving a test key changes the card to `已配置` with a masked key.
- Testing config reports local readiness and states that live vendor search remains closed.
- Knowledge page shows 专利证据覆盖 and 非专利文献覆盖 separately.
- Wanfang copy says it does not replace patent evidence gate.

- [ ] **Step 6: Final branch status**

Run:

```bash
git status --short --branch
git log --oneline -8
```

Expected: branch is clean and contains the task commits.
