# Local Desktop Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor PatentAgent's local desktop architecture without changing the product into a multiplayer SaaS: keep Tauri + React + FastAPI, split backend/frontend boundaries, introduce generated API types and TanStack Query, and prepare local SQLite migrations.

**Architecture:** Use an incremental PR train. Backend work first extracts APIRouter/service/repository boundaries while preserving endpoint behavior. Frontend work then adds generated OpenAPI types, TanStack Query, and route/feature boundaries while preserving existing screens and desktop behavior. Storage work introduces SQLAlchemy/Alembic as a compatibility-tested migration path, not a one-shot rewrite.

**Tech Stack:** Tauri v2, React 19, TypeScript, Vite, Tailwind 4, Radix UI, TanStack Query, TanStack Router, openapi-typescript, openapi-fetch, React Hook Form, Zod, FastAPI, Pydantic v2, SQLite, SQLAlchemy 2, Alembic, pytest, Vitest, Playwright, Hermes Kanban.

---

## Source Identity

- Planning worktree: `/private/tmp/patents-agent-architecture-refactor-plan`
- Planning branch: `codex/architecture-refactor-plan`
- Base SHA: `f3948e4b`
- Baseline test: `python3 -m pytest tests/test_v1_agent_bootstrap.py -q` passed with 7 tests.
- Parent checkout: `/Users/leo/Projects/patents_agent`, branch `fix/code-review-hardening`, SHA `f3948e4b`, dirty. Do not use the parent checkout as a worker source tree.

## File Map

### PR-0 Planning

- Create: `docs/superpowers/specs/2026-06-23-local-desktop-architecture-refactor-design.md`
- Create: `docs/superpowers/plans/2026-06-23-local-desktop-architecture-refactor.md`

### PR-1 Backend Router Foundation

- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/system.py`
- Create: `backend/app/api/desktop_config.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/desktop_config_service.py`
- Create: `backend/app/services/llm_factory.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_api_router_foundation.py`

### PR-2 Backend Projects And Corpus Domains

- Create: `backend/app/api/projects.py`
- Create: `backend/app/api/corpus.py`
- Create: `backend/app/services/project_service.py`
- Create: `backend/app/services/corpus_service.py`
- Modify: `backend/app/main.py`
- Modify only if required for imports: `backend/app/storage.py`
- Test: `tests/test_projects_api_router.py`
- Test: `tests/test_corpus_api_router.py`

### PR-3 Frontend API And Query Foundation

- Create: `frontend/openapi.config.mjs`
- Create: `frontend/src/generated/api/schema.d.ts`
- Create: `frontend/src/lib/apiClient.ts`
- Create: `frontend/src/lib/queryClient.ts`
- Create: `frontend/src/features/system/queries.ts`
- Create: `frontend/src/features/settings/queries.ts`
- Create: `frontend/src/features/projects/queries.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/main.tsx`
- Test: `frontend/src/features/system/queries.test.ts`
- Test: `frontend/src/features/projects/queries.test.ts`

### PR-4 Frontend App Decomposition

- Create: `frontend/src/app/AppRoot.tsx`
- Create: `frontend/src/app/routes.tsx`
- Create: `frontend/src/app/ShellLayout.tsx`
- Create: `frontend/src/features/projects/ProjectWorkspace.tsx`
- Create: `frontend/src/features/corpus/CorpusWorkspace.tsx`
- Create: `frontend/src/features/quality/QualityWorkspace.tsx`
- Create: `frontend/src/features/postDraft/PostDraftWorkspace.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: existing feature views only for prop plumbing and imports
- Test: `frontend/src/app/routes.test.tsx`
- Test: affected existing Vitest files

### PR-5 Storage Repository And Migration Foundation

- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/migrations/README.md`
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/projects.py`
- Create: `tests/test_project_repository.py`
- Modify: `pyproject.toml`
- Modify: `backend/app/storage.py`
- Modify: `backend/app/settings.py`

### PR-6 Integration QA And Merge Readiness

- Create: `docs/release/local-desktop-architecture-refactor-handoff.md`
- Modify: `README.md` only if commands or architecture overview changed
- Run and report backend, frontend, and desktop smoke evidence.

## PR-0: Planning Baseline

**Owner:** Codex.

**Branch:** `codex/architecture-refactor-plan`

**Purpose:** Land the reviewed spec/plan and create Hermes cards.

- [ ] **Step 1: Verify source identity**

Run:

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

Expected:

```text
/private/tmp/patents-agent-architecture-refactor-plan
## codex/architecture-refactor-plan
/private/tmp/patents-agent-architecture-refactor-plan
codex/architecture-refactor-plan
f3948e4b
```

- [ ] **Step 2: Review spec and plan for placeholders**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

paths = [
    Path("docs/superpowers/specs/2026-06-23-local-desktop-architecture-refactor-design.md"),
    Path("docs/superpowers/plans/2026-06-23-local-desktop-architecture-refactor.md"),
]
forbidden = [
    "T" + "BD",
    "T" + "ODO",
    "implement " + "later",
    "fill in " + "details",
    "Similar to " + "Task",
    "appropriate " + "error handling",
]
matches = []
for path in paths:
    text = path.read_text(encoding="utf-8")
    for needle in forbidden:
        if needle in text:
            matches.append(f"{path}: contains {needle!r}")
if matches:
    raise SystemExit("\n".join(matches))
PY
```

Expected: no matches.

- [ ] **Step 3: Run lightweight board contract tests**

Run:

```bash
python3 -m pytest tests/test_v1_agent_bootstrap.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 4: Commit planning docs**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-local-desktop-architecture-refactor-design.md docs/superpowers/plans/2026-06-23-local-desktop-architecture-refactor.md
git commit -m "docs: plan local desktop architecture refactor"
```

Expected: commit includes only the two planning documents.

## PR-1: Backend Router Foundation

**Owner:** `deepseekworker`

**Branch:** `codex/refactor-backend-router-foundation`

**Workspace:** Hermes worktree.

**Depends On:** PR-0.

**In Scope:** system health, agent doctor, desktop config endpoints, router registration, dependency helpers.

**Out Of Scope:** project/corpus endpoint migration, storage rewrite, frontend changes, Tauri packaging.

- [ ] **Step 1: Write failing router tests**

Create `tests/test_api_router_foundation.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_still_reports_version_and_counts(tmp_path: Path):
    app = create_app(data_dir=tmp_path, load_env_file=False)
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "llm_configured" in payload
    assert payload["data_dir"] == str(tmp_path)
    assert payload["model"]
    assert payload["embedding_model"]


def test_desktop_config_origin_guard_survives_router_extraction(tmp_path: Path):
    app = create_app(data_dir=tmp_path, load_env_file=False)
    client = TestClient(app)

    response = client.patch(
        "/api/desktop-config",
        headers={"Origin": "https://example.invalid"},
        json={"deepseek_api_key": "should-not-write"},
    )

    assert response.status_code == 403
```

Run:

```bash
python3 -m pytest tests/test_api_router_foundation.py -q
```

Expected: tests pass before extraction or fail only because import paths for new router modules do not exist after the worker starts editing.

- [ ] **Step 2: Add API dependency helpers**

Create `backend/app/api/__init__.py`:

```python
"""FastAPI router modules for PatentAgent."""
```

Create `backend/app/api/deps.py`:

```python
from __future__ import annotations

from fastapi import Request


def get_store(request: Request):
    return request.app.state.store


def get_settings(request: Request):
    return request.app.state.settings


def get_index(request: Request):
    return request.app.state.index


def get_llm(request: Request):
    return request.app.state.llm


def get_desktop_config(request: Request):
    return request.app.state.desktop_config
```

- [ ] **Step 3: Move health and doctor endpoints into a router**

Create `backend/app/api/system.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.api.deps import get_store
from backend.app.deliberation.doctor import inspect_agent_environment
from backend.app.llm import MissingLLMClient

router = APIRouter()


@router.get("/api/health")
def health(request: Request, store=Depends(get_store)) -> dict:
    return {
        "ok": True,
        "llm_configured": not isinstance(request.app.state.llm, MissingLLMClient),
        "data_dir": str(request.app.state.settings.data_dir),
        "model": request.app.state.settings.llm_model,
        "embedding_model": request.app.state.settings.embedding_model,
    }


@router.get("/api/agents/doctor")
def agent_doctor(request: Request) -> dict:
    return inspect_agent_environment(request.app.state.provider_runner)
```

When copying from `backend/app/main.py`, preserve the exact response fields used by current tests. If the current implementation has extra fields, include them in this router.

- [ ] **Step 4: Extract LLM factory**

Create `backend/app/services/llm_factory.py`:

```python
from __future__ import annotations

from backend.app.desktop_config import DesktopConfig, effective_settings
from backend.app.llm import DeepSeekLLMClient, LLMClient, MissingLLMClient
from backend.app.settings import Settings


def build_llm(settings: Settings, desktop_config: DesktopConfig | None = None) -> LLMClient:
    effective = effective_settings(settings, desktop_config or DesktopConfig())
    api_key = effective["api_key"]
    if not api_key:
        return MissingLLMClient()
    return DeepSeekLLMClient(
        api_key=api_key,
        base_url=effective["base_url"] or None,
        model=effective["model"],
    )
```

Modify `backend/app/main.py` to import `build_llm` and replace `_build_llm(...)` calls with `build_llm(...)`. Remove the old `_build_llm` function only after tests pass.

- [ ] **Step 5: Extract desktop config service**

Create `backend/app/services/__init__.py`:

```python
"""Domain services for PatentAgent backend operations."""
```

Create `backend/app/services/desktop_config_service.py`:

```python
from __future__ import annotations

import re
import time
from pathlib import Path

from fastapi import HTTPException, Request

from backend.app.desktop_config import (
    DesktopConfig,
    DesktopConfigError,
    apply_update,
    effective_settings,
    redacted_view,
    save_desktop_config,
)
from backend.app.schemas import DesktopConfigUpdate, DesktopConfigView

LOCAL_RENDERER_ORIGINS = frozenset(
    {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    }
)

_API_KEY_REDACT_PATTERN = re.compile(r"(sk-[A-Za-z0-9_-]{6,})")


def enforce_desktop_config_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in LOCAL_RENDERER_ORIGINS:
        raise HTTPException(status_code=403, detail="Forbidden desktop config origin.")


def view_config(config: DesktopConfig) -> DesktopConfigView:
    return DesktopConfigView.model_validate(redacted_view(config))


def update_config(data_dir: Path, config: DesktopConfig, update: DesktopConfigUpdate) -> DesktopConfig:
    try:
        updated = apply_update(
            config,
            provider=update.provider,
            base_url=update.base_url,
            model=update.model,
            api_key=update.api_key,
            clear_api_key=update.clear_api_key,
        )
    except DesktopConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return save_desktop_config(data_dir, updated)


def effective_config(config: DesktopConfig) -> dict[str, str | None]:
    return effective_settings(config)


def health_probe(settings, config: DesktopConfig) -> dict:
    effective = effective_settings(settings, config)
    api_key = effective["api_key"]
    model = effective["model"]
    base_url = effective["base_url"]
    result: dict = {
        "ok": False,
        "model": model,
        "api_key_source": effective["api_key_source"],
        "latency_ms": 0,
        "status_code": 0,
        "error": "",
    }
    if not api_key:
        result["error"] = "no_api_key"
        return result
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url or None)
    started = time.monotonic()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "ping"},
                {"role": "user", "content": "ping"},
            ],
            max_tokens=1,
            temperature=0,
        )
        result["ok"] = bool(completion.choices)
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        result["status_code"] = 200
    except Exception as exc:  # noqa: BLE001 - report, do not raise
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        result["error"] = _API_KEY_REDACT_PATTERN.sub("sk-...", f"{type(exc).__name__}: {exc}")[:512]
        status = getattr(exc, "status_code", None) or 0
        result["status_code"] = int(status) if isinstance(status, int) else 0
    return result
```

If existing `desktop_config.py` uses different function names, keep this service as a thin wrapper over the existing names and update imports accordingly.

- [ ] **Step 6: Move desktop config endpoints into a router**

Create `backend/app/api/desktop_config.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.api.deps import get_settings
from backend.app.schemas import DesktopConfigHealthResult, DesktopConfigUpdate, DesktopConfigView
from backend.app.services.llm_factory import build_llm
from backend.app.services.desktop_config_service import (
    enforce_desktop_config_origin,
    health_probe,
    update_config,
    view_config,
)

router = APIRouter()


@router.get("/api/desktop-config", response_model=DesktopConfigView)
def get_desktop_config(request: Request) -> DesktopConfigView:
    enforce_desktop_config_origin(request)
    return view_config(request.app.state.desktop_config)


@router.patch("/api/desktop-config", response_model=DesktopConfigView)
def patch_desktop_config(
    payload: DesktopConfigUpdate,
    request: Request,
    settings=Depends(get_settings),
) -> DesktopConfigView:
    enforce_desktop_config_origin(request)
    saved = update_config(settings.data_dir, request.app.state.desktop_config, payload)
    request.app.state.desktop_config = saved
    if not request.app.state.llm_client_override:
        request.app.state.llm = build_llm(settings, saved)
    return view_config(saved)


@router.post("/api/desktop-config/health", response_model=DesktopConfigHealthResult)
def desktop_config_health(request: Request, settings=Depends(get_settings)) -> DesktopConfigHealthResult:
    enforce_desktop_config_origin(request)
    return health_probe(settings, request.app.state.desktop_config)
```

This router must not import `backend.app.main`; otherwise `main.py` router registration will create a circular import.

- [ ] **Step 7: Register routers from app factory**

Modify `backend/app/main.py` after app state setup:

```python
from backend.app.api.desktop_config import router as desktop_config_router
from backend.app.api.system import router as system_router


def _register_routers(app: FastAPI) -> None:
    app.include_router(system_router)
    app.include_router(desktop_config_router)
```

Call `_register_routers(app)` inside `create_app()` before returning `app`. Remove the inline endpoint definitions that moved to routers after tests pass.

- [ ] **Step 8: Verify backend behavior**

Run:

```bash
python3 -m pytest tests/test_api_router_foundation.py tests/test_tauri_desktop_skeleton.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add backend/app/api backend/app/services backend/app/main.py tests/test_api_router_foundation.py
git commit -m "refactor: introduce backend router foundation"
```

## PR-2: Backend Projects And Corpus Domains

**Owner:** `deepseekworker`

**Branch:** `codex/refactor-backend-projects-corpus`

**Workspace:** Hermes worktree.

**Depends On:** PR-1.

**In Scope:** projects, materials, patent points, corpus listing/jobs/search, service extraction.

**Out Of Scope:** quality endpoints, post-draft endpoints, SQLAlchemy migration, frontend changes.

- [ ] **Step 1: Add regression tests for migrated domains**

Create `tests/test_projects_api_router.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_project_crud_survives_router_extraction(tmp_path: Path):
    app = create_app(data_dir=tmp_path, load_env_file=False)
    client = TestClient(app)

    created = client.post("/api/projects", json={"name": "Router Refactor", "draft_text": "技术方案"}).json()
    project_id = created["id"]

    assert client.get("/api/projects").status_code == 200
    assert client.get(f"/api/projects/{project_id}").json()["name"] == "Router Refactor"

    updated = client.put(f"/api/projects/{project_id}", json={"name": "Router Refactor Updated"}).json()
    assert updated["name"] == "Router Refactor Updated"


def test_patent_points_survive_router_extraction(tmp_path: Path):
    app = create_app(data_dir=tmp_path, load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "Point Project", "draft_text": "技术方案"}).json()

    point = client.post(
        f"/api/projects/{project['id']}/patent-points",
        json={"title": "主动采集", "summary": "基于置信度触发采集"},
    ).json()

    assert point["title"] == "主动采集"
    assert client.get(f"/api/projects/{project['id']}/patent-points").json()[0]["id"] == point["id"]
```

Create `tests/test_corpus_api_router.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_corpus_stats_and_versions_survive_router_extraction(tmp_path: Path):
    app = create_app(data_dir=tmp_path, load_env_file=False)
    client = TestClient(app)

    stats = client.get("/api/corpus/stats")
    versions = client.get("/api/corpus/versions")

    assert stats.status_code == 200
    assert versions.status_code == 200
    assert isinstance(versions.json(), list)
```

Run:

```bash
python3 -m pytest tests/test_projects_api_router.py tests/test_corpus_api_router.py -q
```

Expected: pass before extraction.

- [ ] **Step 2: Extract project service**

Create `backend/app/services/project_service.py`:

```python
from __future__ import annotations

from backend.app.schemas import ProjectCreate, ProjectRecord, ProjectUpdate


class ProjectService:
    def __init__(self, store):
        self.store = store

    def list_projects(self) -> list[ProjectRecord]:
        return self.store.list_projects()

    def create_project(self, payload: ProjectCreate) -> ProjectRecord:
        return self.store.create_project(payload)

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return self.store.get_project(project_id)

    def update_project(self, project_id: str, payload: ProjectUpdate) -> ProjectRecord:
        return self.store.update_project(project_id, payload)

    def delete_project(self, project_id: str) -> None:
        self.store.delete_project(project_id)
```

Adjust method calls to match the actual `SQLiteStore` method signatures. Keep the service thin in this PR.

- [ ] **Step 3: Extract corpus service**

Create `backend/app/services/corpus_service.py`:

```python
from __future__ import annotations


class CorpusService:
    def __init__(self, store, corpus_import_service):
        self.store = store
        self.corpus_import_service = corpus_import_service

    def list_corpus(self):
        return self.store.list_documents()

    def list_versions(self):
        return self.store.list_corpus_versions()

    def stats(self):
        return self.store.corpus_stats()
```

Adjust method names to the existing store API while preserving current endpoint responses.

- [ ] **Step 4: Move project routes**

Create `backend/app/api/projects.py` by moving project, material, and patent-point route handlers from `backend/app/main.py`. Use this shape:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import get_store
from backend.app.schemas import ProjectCreate, ProjectRecord, ProjectUpdate
from backend.app.services.project_service import ProjectService

router = APIRouter()


def get_project_service(store=Depends(get_store)) -> ProjectService:
    return ProjectService(store)


@router.get("/api/projects", response_model=list[ProjectRecord])
def list_projects(service: ProjectService = Depends(get_project_service)) -> list[ProjectRecord]:
    return service.list_projects()


@router.post("/api/projects", response_model=ProjectRecord)
def create_project(payload: ProjectCreate, service: ProjectService = Depends(get_project_service)) -> ProjectRecord:
    return service.create_project(payload)


@router.get("/api/projects/{project_id}", response_model=ProjectRecord)
def get_project(project_id: str, service: ProjectService = Depends(get_project_service)) -> ProjectRecord:
    project = service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

Move the remaining project-related handlers using the same dependency pattern.

- [ ] **Step 5: Move corpus routes**

Create `backend/app/api/corpus.py` by moving corpus route handlers from `backend/app/main.py`. Keep upload, job run, search, document fetch, versions, and stats behavior unchanged.

- [ ] **Step 6: Register migrated routers**

Modify `_register_routers(app)` in `backend/app/main.py`:

```python
from backend.app.api.corpus import router as corpus_router
from backend.app.api.projects import router as projects_router


def _register_routers(app: FastAPI) -> None:
    app.include_router(system_router)
    app.include_router(desktop_config_router)
    app.include_router(projects_router)
    app.include_router(corpus_router)
```

Remove duplicate inline handlers after all tests pass.

- [ ] **Step 7: Verify migrated domains**

Run:

```bash
python3 -m pytest tests/test_projects_api_router.py tests/test_corpus_api_router.py tests/test_v1_agent_bootstrap.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add backend/app/api backend/app/services backend/app/main.py tests/test_projects_api_router.py tests/test_corpus_api_router.py
git commit -m "refactor: move projects and corpus endpoints into routers"
```

## PR-3: Frontend API And Query Foundation

**Owner:** `qwenworker`

**Branch:** `codex/refactor-frontend-api-query-foundation`

**Workspace:** Hermes worktree.

**Depends On:** PR-1.

**In Scope:** dependencies, OpenAPI type generation, typed fetch helper, QueryClient provider, health/settings/project list reads.

**Out Of Scope:** large `App.tsx` decomposition, visual redesign, backend endpoint moves beyond PR-1.

- [ ] **Step 1: Add dependencies**

Run:

```bash
npm --prefix frontend install @tanstack/react-query @tanstack/react-router openapi-typescript openapi-fetch react-hook-form zod
```

Expected: `frontend/package.json` and lockfile update only for these dependencies and their transitive dependencies.

- [ ] **Step 2: Add OpenAPI generation config**

Create `frontend/openapi.config.mjs`:

```javascript
export default {
  input: "../.artifacts/openapi/patentagent-openapi.json",
  output: "src/generated/api/schema.d.ts",
};
```

Add scripts to `frontend/package.json`:

```json
{
  "scripts": {
    "generate:api": "openapi-typescript ../.artifacts/openapi/patentagent-openapi.json -o src/generated/api/schema.d.ts"
  }
}
```

Keep existing scripts unchanged.

- [ ] **Step 3: Add backend OpenAPI export command**

Create a temporary OpenAPI JSON during worker testing:

```bash
mkdir -p .artifacts/openapi
python3 - <<'PY'
import json
from backend.app.main import create_app

app = create_app(load_env_file=False)
with open(".artifacts/openapi/patentagent-openapi.json", "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, ensure_ascii=False, indent=2, sort_keys=True)
PY
npm --prefix frontend run generate:api
```

Expected: `frontend/src/generated/api/schema.d.ts` is created and contains `/api/health`.

- [ ] **Step 4: Add typed API client**

Create `frontend/src/lib/apiClient.ts`:

```typescript
import createClient from "openapi-fetch";
import type { paths } from "@/generated/api/schema";

type TauriInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>;

declare global {
  interface Window {
    __TAURI__?: {
      core?: {
        invoke?: TauriInvoke;
      };
    };
  }
}

let backendBaseUrlPromise: Promise<string | null> | null = null;

async function resolveBackendBaseUrl(): Promise<string | null> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return null;
  if (!backendBaseUrlPromise) {
    backendBaseUrlPromise = invoke<string>("get_backend_base_url").catch(() => null);
  }
  return backendBaseUrlPromise;
}

export async function resolveApiUrl(path: string): Promise<string> {
  const baseUrl = await resolveBackendBaseUrl();
  if (baseUrl) {
    return `${baseUrl}${path}`;
  }
  return path;
}

export const apiClient = createClient<paths>({
  baseUrl: "",
  fetch: async (input, init) => {
    const raw = typeof input === "string" ? input : input.toString();
    const url = raw.startsWith("/api/") ? await resolveApiUrl(raw) : raw;
    return fetch(url, init);
  },
});
```

- [ ] **Step 5: Add QueryClient provider**

Create `frontend/src/lib/queryClient.ts`:

```typescript
import { QueryClient } from "@tanstack/react-query";

export function createPatentAgentQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
```

Modify `frontend/src/main.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { createPatentAgentQueryClient } from "./lib/queryClient";

const queryClient = createPatentAgentQueryClient();

root.render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>,
);
```

Preserve existing Tauri bridge initialization.

- [ ] **Step 6: Add initial query hooks**

Create `frontend/src/features/system/queries.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";

export const systemQueryKeys = {
  health: ["system", "health"] as const,
};

export function useHealthQuery() {
  return useQuery({
    queryKey: systemQueryKeys.health,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/health");
      if (error) throw error;
      return data;
    },
  });
}
```

Create `frontend/src/features/projects/queries.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";

export const projectQueryKeys = {
  all: ["projects"] as const,
  list: () => [...projectQueryKeys.all, "list"] as const,
};

export function useProjectsQuery() {
  return useQuery({
    queryKey: projectQueryKeys.list(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/projects");
      if (error) throw error;
      return data ?? [];
    },
  });
}
```

- [ ] **Step 7: Add hook tests**

Create `frontend/src/features/system/queries.test.ts`:

```typescript
import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createPatentAgentQueryClient } from "@/lib/queryClient";
import { useHealthQuery } from "./queries";

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={createPatentAgentQueryClient()}>{children}</QueryClientProvider>;
}

describe("useHealthQuery", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ status: "ok", version: "1.1.0", projects: 0, chunks: 0 }))));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads backend health through the typed client", async () => {
    const { result } = renderHook(() => useHealthQuery(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("ok");
  });
});
```

If TypeScript requires an explicit React import for JSX in the test file, add `import React from "react";`.

- [ ] **Step 8: Verify frontend**

Run:

```bash
npm --prefix frontend test -- features/system/queries.test.ts
npm --prefix frontend run build
```

Expected: pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add frontend/package.json frontend/package-lock.json frontend/openapi.config.mjs frontend/src/generated frontend/src/lib frontend/src/features frontend/src/main.tsx
git commit -m "refactor: add typed api and query foundation"
```

## PR-4: Frontend App Decomposition

**Owner:** `qwenworker`

**Branch:** `codex/refactor-frontend-app-decomposition`

**Workspace:** Hermes worktree.

**Depends On:** PR-3.

**In Scope:** route tree, shell extraction, project/corpus/quality/post-draft workspace extraction, `App.tsx` shrink.

**Out Of Scope:** new visual design, backend behavior, storage migration.

- [ ] **Step 1: Add route smoke test**

Create `frontend/src/app/routes.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppRoot } from "./AppRoot";
import { createPatentAgentQueryClient } from "@/lib/queryClient";

describe("AppRoot", () => {
  it("renders the desktop shell without replacing production navigation", () => {
    render(
      <QueryClientProvider client={createPatentAgentQueryClient()}>
        <AppRoot />
      </QueryClientProvider>,
    );

    expect(screen.getByText("开始")).toBeInTheDocument();
    expect(screen.getByText("项目")).toBeInTheDocument();
    expect(screen.getByText("设置")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Extract shell layout**

Create `frontend/src/app/ShellLayout.tsx`:

```tsx
import { ReactNode } from "react";

import { ShellSidebar } from "@/ui/ShellSidebar";
import { ShellTopbar } from "@/ui/ShellTopbar";

type ShellLayoutProps = {
  children: ReactNode;
  activeSection: string;
  onSectionChange: (section: string) => void;
};

export function ShellLayout({ children, activeSection, onSectionChange }: ShellLayoutProps) {
  return (
    <div className="app-shell">
      <ShellSidebar activeSection={activeSection} onSectionChange={onSectionChange} />
      <main className="app-main">
        <ShellTopbar activeSection={activeSection} />
        {children}
      </main>
    </div>
  );
}
```

Adjust props to match the current `ShellSidebar` and `ShellTopbar` signatures.

- [ ] **Step 3: Add AppRoot**

Create `frontend/src/app/AppRoot.tsx`:

```tsx
import { useState } from "react";

import { defaultMainSectionId, type MainSectionId } from "@/guidedFlow";
import { ShellLayout } from "./ShellLayout";
import { ProjectWorkspace } from "@/features/projects/ProjectWorkspace";

export function AppRoot() {
  const [activeSection, setActiveSection] = useState<MainSectionId>(defaultMainSectionId);

  return (
    <ShellLayout activeSection={activeSection} onSectionChange={(value) => setActiveSection(value as MainSectionId)}>
      <ProjectWorkspace activeSection={activeSection} />
    </ShellLayout>
  );
}
```

Use the current `App.tsx` logic as the source of truth for section IDs, topbar behavior, and settings routing.

- [ ] **Step 4: Extract ProjectWorkspace**

Create `frontend/src/features/projects/ProjectWorkspace.tsx`:

```tsx
import { ProjectsOverview, StartChoiceScreen } from "@/views/projectViews";
import type { MainSectionId } from "@/guidedFlow";

type ProjectWorkspaceProps = {
  activeSection: MainSectionId;
};

export function ProjectWorkspace({ activeSection }: ProjectWorkspaceProps) {
  if (activeSection === "start") {
    return <StartChoiceScreen />;
  }

  return <ProjectsOverview projects={[]} selectedProjectId="" onSelectProject={() => {}} onCreateProject={() => {}} />;
}
```

Replace placeholder props by moving the existing state and handlers from `App.tsx`. Do not leave empty arrays or no-op handlers in the committed version.

- [ ] **Step 5: Move one feature group at a time**

Move state and handlers from `frontend/src/App.tsx` into feature workspaces in this order:

1. system health and settings into `frontend/src/features/settings/`.
2. project list and selection into `frontend/src/features/projects/`.
3. corpus state into `frontend/src/features/corpus/`.
4. quality/report state into `frontend/src/features/quality/`.
5. post-draft review state into `frontend/src/features/postDraft/`.

After each group, run:

```bash
npm --prefix frontend test -- AppRefreshEffect.test.ts guidedFlow.test.ts
```

Expected: pass after each group.

- [ ] **Step 6: Preserve App compatibility**

Modify `frontend/src/App.tsx` to become:

```tsx
import { AppRoot } from "@/app/AppRoot";

export default function App() {
  return <AppRoot />;
}
```

Only do this after all moved state is owned by feature modules and tests pass.

- [ ] **Step 7: Verify frontend build**

Run:

```bash
npm --prefix frontend test -- app/routes.test.tsx GuidedPatentFlowView.test.ts PostDraftRepairEditor.test.tsx
npm --prefix frontend run build
```

Expected: pass.

- [ ] **Step 8: Browser QA**

Start:

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

Use Playwright or the existing browser QA skill to capture:

- desktop `1440x1100`;
- mobile `390x1100`;
- start screen;
- project overview;
- settings screen;
- post-draft repair editor entry if a fixture project is available.

Merge blocker: visible overlap, missing sidebar/topbar, blank route, or broken existing workflow.

- [ ] **Step 9: Commit**

Run:

```bash
git add frontend/src/app frontend/src/features frontend/src/App.tsx frontend/src/views frontend/src/ui frontend/src/guidedFlow.ts frontend/src/*.test.tsx
git commit -m "refactor: split frontend app shell and feature workspaces"
```

Stage only files actually changed by this PR.

## PR-5: Storage Repository And Migration Foundation

**Owner:** `deepseekworker`

**Branch:** `codex/refactor-storage-repository-migrations`

**Workspace:** Hermes worktree.

**Depends On:** PR-2.

**In Scope:** repository seam, SQLAlchemy/Alembic dependencies and scaffold, project table compatibility tests.

**Out Of Scope:** full database migration, frontend changes, export behavior changes.

- [ ] **Step 1: Add dependencies**

Modify `pyproject.toml`:

```toml
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.8.0",
  "pydantic-settings>=2.4.0",
  "python-multipart>=0.0.9",
  "python-docx>=1.1.2",
  "PyMuPDF>=1.24.0",
  "json-repair>=0.35.0",
  "openpyxl>=3.1.0",
  "openai>=1.40.0",
  "sqlalchemy>=2.0.0",
  "alembic>=1.13.0",
]
```

- [ ] **Step 2: Add database session module**

Create `backend/app/db/__init__.py`:

```python
"""Database session and migration helpers."""
```

Create `backend/app/db/session.py`:

```python
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


def sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


def create_sqlite_engine(db_path: Path) -> Engine:
    return create_engine(sqlite_url(db_path), future=True)


def create_session_factory(engine: Engine):
    return sessionmaker(bind=engine, future=True)
```

Create `backend/app/db/base.py`:

```python
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 3: Add project repository tests**

Create `tests/test_project_repository.py`:

```python
from pathlib import Path

from backend.app.repositories.projects import ProjectRepository
from backend.app.schemas import ProjectCreate
from backend.app.storage import SQLiteStore


def test_project_repository_wraps_existing_store(tmp_path: Path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    repository = ProjectRepository(store)

    project = repository.create(ProjectCreate(name="Repository Project", draft_text="技术方案"))

    assert repository.get(project.id).name == "Repository Project"
    assert repository.list()[0].id == project.id
```

Run:

```bash
python3 -m pytest tests/test_project_repository.py -q
```

Expected: fail because `backend.app.repositories.projects` does not exist.

- [ ] **Step 4: Add repository wrapper**

Create `backend/app/repositories/__init__.py`:

```python
"""Persistence repositories for local PatentAgent data."""
```

Create `backend/app/repositories/projects.py`:

```python
from __future__ import annotations

from backend.app.schemas import ProjectCreate, ProjectRecord, ProjectUpdate


class ProjectRepository:
    def __init__(self, store):
        self.store = store

    def list(self) -> list[ProjectRecord]:
        return self.store.list_projects()

    def create(self, payload: ProjectCreate) -> ProjectRecord:
        return self.store.create_project(payload)

    def get(self, project_id: str) -> ProjectRecord | None:
        return self.store.get_project(project_id)

    def update(self, project_id: str, payload: ProjectUpdate) -> ProjectRecord:
        return self.store.update_project(project_id, payload)

    def delete(self, project_id: str) -> None:
        self.store.delete_project(project_id)
```

- [ ] **Step 5: Route project service through repository**

Modify `backend/app/services/project_service.py`:

```python
from backend.app.repositories.projects import ProjectRepository


class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository

    def list_projects(self):
        return self.repository.list()
```

Update the service methods to call the repository. Update router dependency construction so it passes `ProjectRepository(store)`.

- [ ] **Step 6: Add migration README**

Create `backend/app/db/migrations/README.md`:

```markdown
# PatentAgent Local SQLite Migrations

This directory is reserved for Alembic migrations used by the local desktop app.

Rules:

- Migrations must preserve existing user data under the desktop data directory.
- A migration PR must include a compatibility test that creates data with the pre-migration store and reads it with the post-migration repository.
- Do not require network access, cloud services, or multi-user tenancy.
- Do not run destructive migrations automatically without a backup strategy.
```

- [ ] **Step 7: Verify backend**

Run:

```bash
python3 -m pytest tests/test_project_repository.py tests/test_projects_api_router.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add pyproject.toml backend/app/db backend/app/repositories backend/app/services/project_service.py backend/app/api/projects.py tests/test_project_repository.py
git commit -m "refactor: add local sqlite repository and migration foundation"
```

## PR-6: Integration QA And Merge Readiness

**Owner:** `kimiworker` for patent workflow QA, `codexreviewer` for final review and merge recommendation.

**Branch:** `codex/refactor-architecture-integration-qa`

**Workspace:** Hermes worktree.

**Depends On:** PR-4 and PR-5.

**In Scope:** integrated test run, patent workflow smoke, desktop UI evidence, docs update, final risk review.

**Out Of Scope:** implementing new architecture changes.

- [ ] **Step 1: Verify source identity**

Run:

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

Include the output in the QA handoff.

- [ ] **Step 2: Run backend tests**

Run:

```bash
python3 -m pytest tests/test_api_router_foundation.py tests/test_projects_api_router.py tests/test_corpus_api_router.py tests/test_project_repository.py -q
```

Expected: all pass.

- [ ] **Step 3: Run frontend tests and build**

Run:

```bash
npm --prefix frontend test -- features/system/queries.test.ts app/routes.test.tsx GuidedPatentFlowView.test.ts PostDraftRepairEditor.test.tsx
npm --prefix frontend run build
```

Expected: all pass.

- [ ] **Step 4: Run desktop-relevant smoke**

Run:

```bash
python3 -m pytest tests/test_tauri_desktop_skeleton.py tests/test_tauri_build_prereqs.py -q
```

Expected: pass.

If code changes touch `src-tauri/`, packaging scripts, or production resource paths, run:

```bash
scripts/package_dmg.sh --with-smoke
```

Expected: DMG report written under `.artifacts/dmg/` with SHA256 and packaged UI smoke evidence.

- [ ] **Step 5: Write QA handoff**

Create `docs/release/local-desktop-architecture-refactor-handoff.md`:

```markdown
# Local Desktop Architecture Refactor Handoff

## Source

- Branch:
- Short SHA:
- Worktree:
- Dirty status:

## PRs Reviewed

- PR-1:
- PR-2:
- PR-3:
- PR-4:
- PR-5:

## Commands

- `python3 -m pytest ...`
- `npm --prefix frontend test -- ...`
- `npm --prefix frontend run build`
- `python3 -m pytest tests/test_tauri_desktop_skeleton.py tests/test_tauri_build_prereqs.py -q`

## UI Evidence

- Desktop screenshot:
- Mobile screenshot:
- Packaged app smoke report, if required:

## Merge Recommendation

- Verdict:
- Blockers:
- Residual risks:
```

Fill every field with concrete evidence before committing.

- [ ] **Step 6: Commit**

Run:

```bash
git add docs/release/local-desktop-architecture-refactor-handoff.md README.md
git commit -m "docs: record architecture refactor integration QA"
```

Stage `README.md` only if it changed.

## Hermes Kanban Mapping

Create or reuse board `patents-local-architecture-refactor`:

```bash
hermes kanban boards create patents-local-architecture-refactor \
  --name "PatentAgent Local Architecture Refactor" \
  --description "Single-user desktop architecture refactor PR train for PatentAgent" \
  --default-workdir /Users/leo/Projects/patents_agent \
  --switch
```

Cards:

| Card | Assignee | Branch | Workspace | Dependency |
|---|---|---|---|---|
| PR-1 Backend router foundation | `deepseekworker` | `codex/refactor-backend-router-foundation` | `worktree` | PR-0 |
| PR-2 Backend projects and corpus domains | `deepseekworker` | `codex/refactor-backend-projects-corpus` | `worktree` | PR-1 |
| PR-3 Frontend API and query foundation | `qwenworker` | `codex/refactor-frontend-api-query-foundation` | `worktree` | PR-1 |
| PR-4 Frontend app decomposition | `qwenworker` | `codex/refactor-frontend-app-decomposition` | `worktree` | PR-3 |
| PR-5 Storage repository and migration foundation | `deepseekworker` | `codex/refactor-storage-repository-migrations` | `worktree` | PR-2 |
| PR-6 Integration QA and merge readiness | `kimiworker` then `codexreviewer` | `codex/refactor-architecture-integration-qa` | `worktree` | PR-4 and PR-5 |

Before real dispatch:

```bash
hermes kanban dispatch --dry-run --max 1
```

Only run real bounded dispatch after PR-0 is committed and the board has the cards above with dependencies linked.

## Merge Blockers

- Worker did not record source branch, SHA, worktree, and dirty status.
- Worker touched files outside its declared scope without explaining why.
- Worker reverted unrelated user or worker changes.
- Backend tests for migrated endpoints are missing or weak.
- Frontend build is broken.
- UI worker uses spec-only evidence instead of running app evidence.
- API contract generation produces unreviewed drift.
- Desktop config origin guard is weakened.
- Official export, post-draft review, or repair safety gates are weakened.
- DMG handoff is incomplete for any PR that touches packaging or Tauri resources.

## Plan Self-Review

- Spec coverage: every spec goal maps to a PR task or merge gate.
- Placeholder scan: no placeholder task text remains.
- Type consistency: proposed module names and dependencies are consistent across PR descriptions.
- Scope check: the plan establishes and proves the architecture pattern without attempting a risky one-shot full migration.
