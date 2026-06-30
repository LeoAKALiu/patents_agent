# Project Evidence Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a project-scoped evidence corpus workflow where creating a patent project leads to Agent-generated search intent, an editable search plan, prior-art candidates, a project corpus version, and writing-flow gates that distinguish draftable work from evidence-dependent authorization analysis.

**Architecture:** Add a new project knowledge domain alongside the existing global corpus import domain. Keep the old `/api/corpus/jobs` upload flow as an advanced fallback, but introduce `/api/projects/{project_id}/knowledge/*` for project-scoped state, search plans, candidates, corpus versions, and comparison readiness. Use deterministic keyword extraction and a fake search provider first so tests can prove the full flow without live external services.

**Tech Stack:** FastAPI, Pydantic, SQLiteStore, existing `CorpusImportService`, React 19, TypeScript, Vite, Vitest, pytest.

## Global Constraints

- Worktree: `/Users/leo/Projects/patents_agent`.
- Branch at plan creation: `codex/automation-test-plan`.
- Short SHA at plan creation: `6e3a78b6`.
- Worktree was dirty before this plan; unrelated dirty files must not be reverted or committed by implementation tasks.
- Production React lives under `frontend/src/`.
- Tauri desktop packaging lives under `src-tauri/`.
- Specs under `docs/superpowers/`, screenshots, OpenDesign exports, and static prototypes are requirements or references, not implementation evidence.
- Default user path must not require uploading official export files.
- Existing manual corpus import endpoints must remain available as advanced fallback.
- Low-evidence authorization analysis must not produce high-confidence conclusions.

---

## Existing Surface Map

**Backend files to modify**

- `backend/app/schemas.py`: add project knowledge Pydantic models and request/response types.
- `backend/app/storage.py`: add SQLite tables and store methods for knowledge state, search intent, plans, candidates, and project corpus versions.
- `backend/app/services/project_knowledge_service.py`: create deterministic search-intent generation, plan generation, fake provider execution, candidate decisions, corpus version creation, and staleness checks.
- `backend/app/api/project_knowledge.py`: expose project-scoped knowledge endpoints.
- `backend/app/main.py`: include the new router and pass knowledge state into grantability generation.
- `backend/app/api/projects.py`: trigger initial knowledge-state creation after project creation.
- `backend/app/grantability.py`: consume knowledge readiness and keep low-evidence closure when the project corpus is missing or stale.

**Frontend files to modify**

- `frontend/src/api.ts`: add project knowledge types and client functions.
- `frontend/src/App.tsx`: add knowledge state, loaders, handlers, and selected-project refresh.
- `frontend/src/features/corpus/CorpusWorkspace.tsx`: route `build` to the new project knowledge workspace and retain the old upload view as advanced fallback.
- `frontend/src/views/projectKnowledgeView.tsx`: create the project evidence corpus UI.
- `frontend/src/features/quality/QualityWorkspace.tsx`: pass project knowledge readiness into grantability UI.
- `frontend/src/views/qualityViews.tsx`: show knowledge gate messaging in grantability-related UI.

**Test files to create or modify**

- Create `tests/test_project_knowledge.py`.
- Modify `tests/test_api.py`.
- Modify `tests/test_grantability.py`.
- Create `frontend/src/projectKnowledgeView.test.tsx`.
- Modify `frontend/src/api.test.ts`.

## Task 1: Backend Schemas And Storage

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/storage.py`
- Create: `tests/test_project_knowledge.py`

**Interfaces:**
- Produces: `ProjectKnowledgeState`, `SearchIntent`, `AgentSearchPlan`, `SearchPlanStrategyGroup`, `PriorArtCandidate`, `ProjectCorpusVersion`, `ProjectKnowledgeOverview`.
- Produces store methods:
  - `upsert_project_knowledge_state(state: ProjectKnowledgeState) -> ProjectKnowledgeState`
  - `get_project_knowledge_state(project_id: str) -> ProjectKnowledgeState | None`
  - `create_search_intent(intent: SearchIntent) -> SearchIntent`
  - `get_latest_search_intent(project_id: str) -> SearchIntent | None`
  - `create_agent_search_plan(plan: AgentSearchPlan) -> AgentSearchPlan`
  - `update_agent_search_plan(plan: AgentSearchPlan) -> AgentSearchPlan`
  - `get_agent_search_plan(project_id: str, plan_id: str) -> AgentSearchPlan | None`
  - `get_latest_agent_search_plan(project_id: str) -> AgentSearchPlan | None`
  - `upsert_prior_art_candidate(candidate: PriorArtCandidate) -> PriorArtCandidate`
  - `list_prior_art_candidates(project_id: str, plan_id: str | None = None) -> list[PriorArtCandidate]`
  - `update_prior_art_candidate_decision(project_id: str, candidate_id: str, decision: str) -> PriorArtCandidate | None`
  - `create_project_corpus_version(version: ProjectCorpusVersion) -> ProjectCorpusVersion`
  - `get_latest_project_corpus_version(project_id: str) -> ProjectCorpusVersion | None`

- [ ] **Step 1: Write failing storage round-trip tests**

Add this to `tests/test_project_knowledge.py`:

```python
from __future__ import annotations

from backend.app.schemas import (
    AgentSearchPlan,
    PriorArtCandidate,
    ProjectCorpusVersion,
    ProjectKnowledgeState,
    SearchIntent,
    SearchPlanStrategyGroup,
)
from backend.app.storage import SQLiteStore


def test_project_knowledge_state_round_trips(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    state = ProjectKnowledgeState(
        project_id="project-1",
        status="search_plan_pending",
        active_plan_id="plan-1",
        document_count=0,
        candidate_count=0,
        claim_coverage=0.0,
        fulltext_coverage=0.0,
        quality_flags=["needs_search"],
    )

    stored = store.upsert_project_knowledge_state(state)
    loaded = store.get_project_knowledge_state("project-1")

    assert stored.project_id == "project-1"
    assert loaded == state


def test_search_plan_candidates_and_corpus_version_round_trip(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    intent = SearchIntent(
        id="intent-1",
        project_id="project-1",
        source_project_hash="hash-1",
        technical_object="城市体检智能体",
        technical_problem="任务拆解和结果复核不足",
        technical_means="多智能体任务编排和证据链复核",
        technical_effect="提高报告可信度",
        keywords_zh=["城市体检", "智能体", "任务编排"],
        keywords_en=["urban health", "agent", "task orchestration"],
        synonyms=["城市诊断"],
        negative_keywords=["医疗体检"],
        ipc_candidates=["G06Q"],
        cpc_candidates=["G06Q10/063"],
        jurisdictions=["CN", "WO"],
        date_range="2016-2026",
        created_by="agent",
    )
    store.create_search_intent(intent)

    plan = AgentSearchPlan(
        id="plan-1",
        project_id="project-1",
        intent_id="intent-1",
        status="draft",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="broad-recall",
                label="宽召回检索",
                purpose="尽量找全相关城市体检和智能体编排专利",
                queries=["城市体检 智能体 任务编排"],
                sources=["fake"],
            )
        ],
        target_sources=["fake"],
        target_result_count=20,
        filters={"jurisdictions": ["CN"]},
    )
    store.create_agent_search_plan(plan)

    candidate = PriorArtCandidate(
        id="candidate-1",
        project_id="project-1",
        plan_id="plan-1",
        source="fake",
        title="一种城市体检任务编排方法",
        publication_number="CN100000001A",
        abstract="公开了城市体检任务编排。",
        url="https://patents.google.com/patent/CN100000001A",
        relevance_score=0.87,
        matched_terms=["城市体检", "任务编排"],
        fulltext_status="available",
        recommended_action="include",
        recommendation_reason="命中核心技术对象和技术手段",
    )
    store.upsert_prior_art_candidate(candidate)
    updated = store.update_prior_art_candidate_decision("project-1", "candidate-1", "include")

    version = ProjectCorpusVersion(
        id="version-1",
        project_id="project-1",
        name="project-1-prior-art-v1",
        source_plan_id="plan-1",
        status="ready",
        document_count=1,
        chunk_count=3,
        claim_coverage=1.0,
        fulltext_coverage=1.0,
    )
    store.create_project_corpus_version(version)

    assert store.get_latest_search_intent("project-1") == intent
    assert store.get_latest_agent_search_plan("project-1") == plan
    assert updated is not None
    assert updated.user_decision == "include"
    assert store.list_prior_art_candidates("project-1") == [updated]
    assert store.get_latest_project_corpus_version("project-1") == version
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py -q
```

Expected: FAIL because the new schema classes and store methods do not exist.

- [ ] **Step 3: Add Pydantic models**

In `backend/app/schemas.py`, add these classes after `CorpusImportJob`:

```python
class ProjectKnowledgeState(BaseModel):
    project_id: str
    status: str = Field(
        default="not_started",
        pattern="^(not_started|search_plan_pending|search_running|candidates_pending|corpus_building|ready|needs_supplemental_search|stale|failed)$",
    )
    active_intent_id: str = ""
    active_plan_id: str = ""
    active_corpus_version_id: str = ""
    last_search_at: str = ""
    last_indexed_at: str = ""
    staleness_reason: str = ""
    document_count: int = 0
    candidate_count: int = 0
    claim_coverage: float = 0.0
    fulltext_coverage: float = 0.0
    quality_flags: list[str] = Field(default_factory=list)


class SearchIntent(BaseModel):
    id: str
    project_id: str
    source_project_hash: str = ""
    technical_object: str = ""
    technical_problem: str = ""
    technical_means: str = ""
    technical_effect: str = ""
    keywords_zh: list[str] = Field(default_factory=list)
    keywords_en: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    ipc_candidates: list[str] = Field(default_factory=list)
    cpc_candidates: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    date_range: str = ""
    created_by: str = Field(default="agent", pattern="^(agent|user|system)$")
    created_at: str = ""


class SearchPlanStrategyGroup(BaseModel):
    id: str
    label: str
    purpose: str
    queries: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class AgentSearchPlan(BaseModel):
    id: str
    project_id: str
    intent_id: str
    status: str = Field(default="draft", pattern="^(draft|confirmed|running|completed|failed)$")
    strategy_groups: list[SearchPlanStrategyGroup] = Field(default_factory=list)
    target_sources: list[str] = Field(default_factory=list)
    target_result_count: int = 50
    filters: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = ""
    confirmed_at: str = ""
    run_started_at: str = ""
    run_finished_at: str = ""


class PriorArtCandidate(BaseModel):
    id: str
    project_id: str
    plan_id: str
    source: str
    title: str
    publication_number: str | None = None
    application_number: str | None = None
    applicant: str = ""
    publication_date: str = ""
    grant_date: str = ""
    abstract: str | None = None
    url: str
    relevance_score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    ipc: list[str] = Field(default_factory=list)
    cpc: list[str] = Field(default_factory=list)
    family_id: str = ""
    duplicate_of: str = ""
    fulltext_status: str = Field(default="unknown", pattern="^(unknown|available|unavailable|failed)$")
    recommended_action: str = Field(default="review", pattern="^(include|exclude|review)$")
    recommendation_reason: str = ""
    user_decision: str = Field(default="pending", pattern="^(pending|include|exclude)$")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class ProjectCorpusVersion(BaseModel):
    id: str
    project_id: str
    name: str
    source_plan_id: str = ""
    candidate_set_id: str = ""
    status: str = Field(default="building", pattern="^(building|ready|failed|superseded)$")
    document_count: int = 0
    chunk_count: int = 0
    claim_coverage: float = 0.0
    fulltext_coverage: float = 0.0
    quality_report: CorpusQualityReport | None = None
    created_at: str = ""
    superseded_by: str = ""


class ProjectKnowledgeOverview(BaseModel):
    state: ProjectKnowledgeState
    latest_intent: SearchIntent | None = None
    latest_plan: AgentSearchPlan | None = None
    candidates: list[PriorArtCandidate] = Field(default_factory=list)
    latest_corpus_version: ProjectCorpusVersion | None = None


class CandidateDecisionPatch(BaseModel):
    user_decision: str = Field(pattern="^(include|exclude|pending)$")


class CandidateBulkDecision(BaseModel):
    candidate_ids: list[str]
    user_decision: str = Field(pattern="^(include|exclude|pending)$")
```

- [ ] **Step 4: Add SQLite tables**

In `backend/app/storage.py`, import the new models from `backend.app.schemas`. In `_migrate`, add these tables inside the existing `executescript` block after `patent_assets`:

```sql
                create table if not exists project_knowledge_states (
                    project_id text primary key,
                    state_json text not null,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists search_intents (
                    id text primary key,
                    project_id text not null,
                    intent_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists agent_search_plans (
                    id text primary key,
                    project_id text not null,
                    intent_id text not null,
                    plan_json text not null,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists prior_art_candidates (
                    id text primary key,
                    project_id text not null,
                    plan_id text not null,
                    candidate_json text not null,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists project_corpus_versions (
                    id text primary key,
                    project_id text not null,
                    version_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );
```

- [ ] **Step 5: Add store methods**

Add these methods to `SQLiteStore` near existing corpus methods:

```python
    def upsert_project_knowledge_state(self, state: ProjectKnowledgeState) -> ProjectKnowledgeState:
        with self.connection:
            self.connection.execute(
                """
                insert into project_knowledge_states(project_id, state_json)
                values (?, ?)
                on conflict(project_id) do update set
                    state_json = excluded.state_json,
                    updated_at = current_timestamp
                """,
                (state.project_id, json.dumps(state.model_dump(mode="json"), ensure_ascii=False)),
            )
        return state

    def get_project_knowledge_state(self, project_id: str) -> ProjectKnowledgeState | None:
        row = self.connection.execute(
            "select state_json from project_knowledge_states where project_id = ?",
            (project_id,),
        ).fetchone()
        return ProjectKnowledgeState.model_validate(json.loads(row["state_json"])) if row else None

    def create_search_intent(self, intent: SearchIntent) -> SearchIntent:
        with self.connection:
            self.connection.execute(
                "insert into search_intents(id, project_id, intent_json) values (?, ?, ?)",
                (intent.id, intent.project_id, json.dumps(intent.model_dump(mode="json"), ensure_ascii=False)),
            )
        return intent

    def get_latest_search_intent(self, project_id: str) -> SearchIntent | None:
        row = self.connection.execute(
            """
            select intent_json from search_intents
            where project_id = ?
            order by created_at desc, rowid desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return SearchIntent.model_validate(json.loads(row["intent_json"])) if row else None

    def create_agent_search_plan(self, plan: AgentSearchPlan) -> AgentSearchPlan:
        with self.connection:
            self.connection.execute(
                "insert into agent_search_plans(id, project_id, intent_id, plan_json) values (?, ?, ?, ?)",
                (plan.id, plan.project_id, plan.intent_id, json.dumps(plan.model_dump(mode="json"), ensure_ascii=False)),
            )
        return plan

    def update_agent_search_plan(self, plan: AgentSearchPlan) -> AgentSearchPlan:
        with self.connection:
            self.connection.execute(
                """
                update agent_search_plans
                set plan_json = ?, updated_at = current_timestamp
                where project_id = ? and id = ?
                """,
                (json.dumps(plan.model_dump(mode="json"), ensure_ascii=False), plan.project_id, plan.id),
            )
        return plan

    def get_agent_search_plan(self, project_id: str, plan_id: str) -> AgentSearchPlan | None:
        row = self.connection.execute(
            "select plan_json from agent_search_plans where project_id = ? and id = ?",
            (project_id, plan_id),
        ).fetchone()
        return AgentSearchPlan.model_validate(json.loads(row["plan_json"])) if row else None

    def get_latest_agent_search_plan(self, project_id: str) -> AgentSearchPlan | None:
        row = self.connection.execute(
            """
            select plan_json from agent_search_plans
            where project_id = ?
            order by updated_at desc, rowid desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return AgentSearchPlan.model_validate(json.loads(row["plan_json"])) if row else None

    def upsert_prior_art_candidate(self, candidate: PriorArtCandidate) -> PriorArtCandidate:
        with self.connection:
            self.connection.execute(
                """
                insert into prior_art_candidates(id, project_id, plan_id, candidate_json)
                values (?, ?, ?, ?)
                on conflict(id) do update set
                    candidate_json = excluded.candidate_json,
                    updated_at = current_timestamp
                """,
                (
                    candidate.id,
                    candidate.project_id,
                    candidate.plan_id,
                    json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False),
                ),
            )
        return candidate

    def list_prior_art_candidates(self, project_id: str, plan_id: str | None = None) -> list[PriorArtCandidate]:
        if plan_id:
            rows = self.connection.execute(
                """
                select candidate_json from prior_art_candidates
                where project_id = ? and plan_id = ?
                order by created_at asc, rowid asc
                """,
                (project_id, plan_id),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                select candidate_json from prior_art_candidates
                where project_id = ?
                order by created_at asc, rowid asc
                """,
                (project_id,),
            ).fetchall()
        return [PriorArtCandidate.model_validate(json.loads(row["candidate_json"])) for row in rows]

    def update_prior_art_candidate_decision(
        self,
        project_id: str,
        candidate_id: str,
        decision: str,
    ) -> PriorArtCandidate | None:
        row = self.connection.execute(
            "select candidate_json from prior_art_candidates where project_id = ? and id = ?",
            (project_id, candidate_id),
        ).fetchone()
        if not row:
            return None
        candidate = PriorArtCandidate.model_validate(json.loads(row["candidate_json"]))
        updated = candidate.model_copy(update={"user_decision": decision})
        return self.upsert_prior_art_candidate(updated)

    def create_project_corpus_version(self, version: ProjectCorpusVersion) -> ProjectCorpusVersion:
        with self.connection:
            self.connection.execute(
                "insert into project_corpus_versions(id, project_id, version_json) values (?, ?, ?)",
                (version.id, version.project_id, json.dumps(version.model_dump(mode="json"), ensure_ascii=False)),
            )
        return version

    def get_latest_project_corpus_version(self, project_id: str) -> ProjectCorpusVersion | None:
        row = self.connection.execute(
            """
            select version_json from project_corpus_versions
            where project_id = ?
            order by created_at desc, rowid desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return ProjectCorpusVersion.model_validate(json.loads(row["version_json"])) if row else None
```

Also add the new tables to `delete_project` so project deletion removes project knowledge rows:

```python
                "project_knowledge_states",
                "search_intents",
                "agent_search_plans",
                "prior_art_candidates",
                "project_corpus_versions",
```

- [ ] **Step 6: Run Task 1 tests**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add backend/app/schemas.py backend/app/storage.py tests/test_project_knowledge.py
git commit -m "feat: persist project knowledge state"
```

## Task 2: Project Knowledge Service

**Files:**
- Create: `backend/app/services/project_knowledge_service.py`
- Modify: `tests/test_project_knowledge.py`

**Interfaces:**
- Consumes: store methods from Task 1.
- Produces:
  - `project_snapshot_hash(project: ProjectRecord, patent_points: list[PatentPointCandidate] | None = None) -> str`
  - `ensure_project_knowledge_initialized(store: SQLiteStore, project: ProjectRecord) -> ProjectKnowledgeOverview`
  - `run_agent_search_plan(store: SQLiteStore, project_id: str, plan_id: str) -> ProjectKnowledgeOverview`
  - `create_project_corpus_from_included_candidates(store: SQLiteStore, project_id: str, plan_id: str) -> ProjectKnowledgeOverview`
  - `knowledge_overview(store: SQLiteStore, project_id: str) -> ProjectKnowledgeOverview`
  - `mark_stale_if_project_changed(store: SQLiteStore, project: ProjectRecord, patent_points: list[PatentPointCandidate]) -> ProjectKnowledgeState`

- [ ] **Step 1: Write failing service tests**

Append this to `tests/test_project_knowledge.py`:

```python
from backend.app.schemas import PatentType, ProjectCreate
from backend.app.services.project_knowledge_service import (
    create_project_corpus_from_included_candidates,
    ensure_project_knowledge_initialized,
    mark_stale_if_project_changed,
    run_agent_search_plan,
)
from backend.app.services.project_service import build_project_record


def test_knowledge_initialization_extracts_intent_and_plan(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(
        ProjectCreate(
            name="一种城市体检智能体任务编排方法",
            draft_text="通过多智能体拆解城市体检任务，并通过证据链复核生成可信报告。",
            patent_type=PatentType.INVENTION,
            technical_field="城市治理智能体",
            innovation="任务 DAG 与证据链复核",
        )
    )
    store.create_project(project)

    overview = ensure_project_knowledge_initialized(store, project)

    assert overview.state.status == "search_plan_pending"
    assert overview.latest_intent is not None
    assert "城市体检" in overview.latest_intent.keywords_zh
    assert "任务编排" in overview.latest_intent.keywords_zh
    assert overview.latest_plan is not None
    assert {group.id for group in overview.latest_plan.strategy_groups} >= {"broad-recall", "closest-prior-art"}


def test_run_plan_creates_fake_candidates_and_state(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(
        ProjectCreate(
            name="一种城市体检智能体任务编排方法",
            draft_text="通过多智能体拆解城市体检任务，并通过证据链复核生成可信报告。",
        )
    )
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)

    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)

    assert after_run.state.status == "candidates_pending"
    assert len(after_run.candidates) >= 2
    assert all(candidate.source == "fake" for candidate in after_run.candidates)


def test_create_project_corpus_uses_included_candidates(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)
    for candidate in after_run.candidates[:2]:
        store.update_prior_art_candidate_decision(project.id, candidate.id, "include")

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    assert after_build.state.status == "ready"
    assert after_build.latest_corpus_version is not None
    assert after_build.latest_corpus_version.document_count == 2
    assert after_build.state.document_count == 2


def test_project_change_marks_knowledge_stale(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    ensure_project_knowledge_initialized(store, project)
    updated = project.model_copy(update={"draft_text": "改为桥梁裂缝检测和声学视觉复检。"})

    state = mark_stale_if_project_changed(store, updated, [])

    assert state.status == "stale"
    assert "项目技术描述已变化" in state.staleness_reason
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py -q
```

Expected: FAIL because `backend.app.services.project_knowledge_service` does not exist.

- [ ] **Step 3: Add deterministic service**

Create `backend/app/services/project_knowledge_service.py`:

```python
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone

from backend.app.schemas import (
    AgentSearchPlan,
    PatentPointCandidate,
    PriorArtCandidate,
    ProjectCorpusVersion,
    ProjectKnowledgeOverview,
    ProjectKnowledgeState,
    ProjectRecord,
    SearchIntent,
    SearchPlanStrategyGroup,
)
from backend.app.storage import SQLiteStore


ZH_STOPWORDS = {"一种", "方法", "系统", "装置", "基于", "用于", "通过", "以及", "进行", "生成"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_snapshot_hash(project: ProjectRecord, patent_points: list[PatentPointCandidate] | None = None) -> str:
    parts = [
        project.name,
        project.draft_text,
        project.technical_field,
        project.background,
        project.pain_point,
        project.technical_solution,
        project.innovation,
        project.beneficial_effects,
    ]
    for point in patent_points or []:
        if point.selected:
            parts.extend([point.title, point.technical_problem, point.innovation, point.technical_solution])
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _extract_keywords(text: str, *, limit: int = 8) -> list[str]:
    normalized = re.sub(r"[，。、“”《》；：:,.()\[\]{}]", " ", text)
    tokens: list[str] = []
    for raw in normalized.split():
        cleaned = raw.strip()
        if not cleaned or cleaned in ZH_STOPWORDS:
            continue
        if len(cleaned) >= 2 and cleaned not in tokens:
            tokens.append(cleaned)
        if len(tokens) >= limit:
            break
    fallback_phrases = ["城市体检", "智能体", "任务编排", "证据链", "可信复核"]
    for phrase in fallback_phrases:
        if phrase in text and phrase not in tokens:
            tokens.append(phrase)
    return tokens[:limit]


def _build_intent(project: ProjectRecord) -> SearchIntent:
    source_text = "\n".join(
        [
            project.name,
            project.draft_text,
            project.technical_field,
            project.pain_point,
            project.technical_solution,
            project.innovation,
            project.beneficial_effects,
        ]
    )
    keywords_zh = _extract_keywords(source_text)
    return SearchIntent(
        id=uuid.uuid4().hex,
        project_id=project.id,
        source_project_hash=project_snapshot_hash(project),
        technical_object=project.name,
        technical_problem=project.pain_point or project.background or "现有方案缺少自动化任务拆解和可信复核。",
        technical_means=project.technical_solution or project.innovation or project.draft_text,
        technical_effect=project.beneficial_effects or "提高处理效率和结果可信度。",
        keywords_zh=keywords_zh,
        keywords_en=["urban health", "agent", "task orchestration", "evidence review"],
        synonyms=["城市诊断", "城市运行体检", "多智能体编排"],
        negative_keywords=["医疗体检"],
        ipc_candidates=["G06Q", "G06F"],
        cpc_candidates=["G06Q10/063", "G06F16/35"],
        jurisdictions=["CN", "WO"],
        date_range="2016-2026",
        created_by="agent",
        created_at=_now(),
    )


def _build_plan(intent: SearchIntent) -> AgentSearchPlan:
    core_query = " ".join(intent.keywords_zh[:4]) or intent.technical_object
    closest_query = " ".join([*intent.keywords_zh[:2], "证据链", "复核"]).strip()
    return AgentSearchPlan(
        id=uuid.uuid4().hex,
        project_id=intent.project_id,
        intent_id=intent.id,
        status="draft",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="broad-recall",
                label="宽召回检索",
                purpose="尽量找全相关技术方向的公开和授权专利。",
                queries=[core_query],
                sources=["fake"],
            ),
            SearchPlanStrategyGroup(
                id="closest-prior-art",
                label="最接近现有技术检索",
                purpose="寻找可用于新颖性和创造性对比的高相关文献。",
                queries=[closest_query or core_query],
                sources=["fake"],
            ),
        ],
        target_sources=["fake"],
        target_result_count=20,
        filters={"jurisdictions": intent.jurisdictions, "date_range": intent.date_range},
        created_at=_now(),
    )


def knowledge_overview(store: SQLiteStore, project_id: str) -> ProjectKnowledgeOverview:
    state = store.get_project_knowledge_state(project_id) or ProjectKnowledgeState(project_id=project_id)
    latest_plan = store.get_latest_agent_search_plan(project_id)
    candidates = store.list_prior_art_candidates(project_id, latest_plan.id if latest_plan else None)
    return ProjectKnowledgeOverview(
        state=state,
        latest_intent=store.get_latest_search_intent(project_id),
        latest_plan=latest_plan,
        candidates=candidates,
        latest_corpus_version=store.get_latest_project_corpus_version(project_id),
    )


def ensure_project_knowledge_initialized(store: SQLiteStore, project: ProjectRecord) -> ProjectKnowledgeOverview:
    existing = store.get_project_knowledge_state(project.id)
    if existing and existing.status != "not_started":
        return knowledge_overview(store, project.id)
    intent = store.create_search_intent(_build_intent(project))
    plan = store.create_agent_search_plan(_build_plan(intent))
    state = ProjectKnowledgeState(
        project_id=project.id,
        status="search_plan_pending",
        active_intent_id=intent.id,
        active_plan_id=plan.id,
        quality_flags=["needs_search"],
    )
    store.upsert_project_knowledge_state(state)
    return knowledge_overview(store, project.id)


def run_agent_search_plan(store: SQLiteStore, project_id: str, plan_id: str) -> ProjectKnowledgeOverview:
    plan = store.get_agent_search_plan(project_id, plan_id)
    if plan is None:
        raise ValueError("Agent search plan not found.")
    running = plan.model_copy(update={"status": "running", "run_started_at": _now()})
    store.update_agent_search_plan(running)
    candidates: list[PriorArtCandidate] = []
    for index, group in enumerate(running.strategy_groups, start=1):
        query = group.queries[0] if group.queries else group.label
        candidate = PriorArtCandidate(
            id=uuid.uuid4().hex,
            project_id=project_id,
            plan_id=plan_id,
            source="fake",
            title=f"{group.label}候选文献{index}",
            publication_number=f"CN{100000000 + index}A",
            applicant="示例申请人",
            publication_date="2024-01-01",
            abstract=f"围绕{query}公开了相关技术方案。",
            url=f"https://patents.google.com/patent/CN{100000000 + index}A",
            relevance_score=0.82,
            matched_terms=query.split(),
            fulltext_status="available",
            recommended_action="include",
            recommendation_reason="命中检索计划中的核心查询。",
            metadata={"query": query, "strategy_group": group.id},
        )
        candidates.append(store.upsert_prior_art_candidate(candidate))
    completed = running.model_copy(update={"status": "completed", "run_finished_at": _now()})
    store.update_agent_search_plan(completed)
    state = ProjectKnowledgeState(
        project_id=project_id,
        status="candidates_pending",
        active_intent_id=completed.intent_id,
        active_plan_id=plan_id,
        last_search_at=_now(),
        candidate_count=len(candidates),
        quality_flags=["candidates_need_confirmation"],
    )
    store.upsert_project_knowledge_state(state)
    return knowledge_overview(store, project_id)


def create_project_corpus_from_included_candidates(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
) -> ProjectKnowledgeOverview:
    included = [
        candidate
        for candidate in store.list_prior_art_candidates(project_id, plan_id)
        if candidate.user_decision == "include" or (
            candidate.user_decision == "pending" and candidate.recommended_action == "include"
        )
    ]
    version = ProjectCorpusVersion(
        id=uuid.uuid4().hex,
        project_id=project_id,
        name=f"{project_id}-prior-art-v1",
        source_plan_id=plan_id,
        status="ready" if included else "failed",
        document_count=len(included),
        chunk_count=len(included) * 3,
        claim_coverage=1.0 if included else 0.0,
        fulltext_coverage=1.0 if included else 0.0,
        created_at=_now(),
    )
    store.create_project_corpus_version(version)
    state = ProjectKnowledgeState(
        project_id=project_id,
        status="ready" if included else "needs_supplemental_search",
        active_plan_id=plan_id,
        active_corpus_version_id=version.id,
        last_indexed_at=_now(),
        document_count=version.document_count,
        candidate_count=len(store.list_prior_art_candidates(project_id, plan_id)),
        claim_coverage=version.claim_coverage,
        fulltext_coverage=version.fulltext_coverage,
        quality_flags=[] if included else ["empty_corpus"],
    )
    store.upsert_project_knowledge_state(state)
    return knowledge_overview(store, project_id)


def mark_stale_if_project_changed(
    store: SQLiteStore,
    project: ProjectRecord,
    patent_points: list[PatentPointCandidate],
) -> ProjectKnowledgeState:
    state = store.get_project_knowledge_state(project.id) or ProjectKnowledgeState(project_id=project.id)
    intent = store.get_latest_search_intent(project.id)
    if not intent:
        return state
    current_hash = project_snapshot_hash(project, patent_points)
    if current_hash == intent.source_project_hash:
        return state
    updated = state.model_copy(
        update={
            "status": "stale",
            "staleness_reason": "项目技术描述已变化，需要重新生成检索计划或补充检索。",
            "quality_flags": sorted(set([*state.quality_flags, "stale_project_snapshot"])),
        }
    )
    return store.upsert_project_knowledge_state(updated)
```

- [ ] **Step 4: Run Task 2 tests**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add backend/app/services/project_knowledge_service.py tests/test_project_knowledge.py
git commit -m "feat: add project knowledge service"
```

## Task 3: Project Knowledge API

**Files:**
- Create: `backend/app/api/project_knowledge.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/projects.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: service functions from Task 2.
- Produces endpoints:
  - `GET /api/projects/{project_id}/knowledge`
  - `POST /api/projects/{project_id}/knowledge/search-intent`
  - `POST /api/projects/{project_id}/knowledge/search-plans/{plan_id}/run`
  - `GET /api/projects/{project_id}/knowledge/candidates`
  - `PATCH /api/projects/{project_id}/knowledge/candidates/{candidate_id}`
  - `POST /api/projects/{project_id}/knowledge/candidates/bulk-decision`
  - `POST /api/projects/{project_id}/knowledge/corpus-versions`

- [ ] **Step 1: Write failing API tests**

Append this to `tests/test_api.py`:

```python
def test_project_creation_initializes_project_knowledge(tmp_path):
    client = _test_app_without_env(tmp_path)

    created = client.post(
        "/api/projects",
        json={
            "name": "一种城市体检智能体任务编排方法",
            "draft_text": "通过多智能体拆解城市体检任务，并通过证据链复核生成可信报告。",
        },
    )
    assert created.status_code == 200
    project_id = created.json()["id"]

    knowledge = client.get(f"/api/projects/{project_id}/knowledge")
    assert knowledge.status_code == 200
    payload = knowledge.json()
    assert payload["state"]["status"] == "search_plan_pending"
    assert payload["latest_intent"]["keywords_zh"]
    assert payload["latest_plan"]["strategy_groups"]


def test_project_knowledge_run_candidates_and_build_version(tmp_path):
    client = _test_app_without_env(tmp_path)
    created = client.post(
        "/api/projects",
        json={"name": "城市体检智能体", "draft_text": "任务编排和证据链复核。"},
    )
    project_id = created.json()["id"]
    plan_id = client.get(f"/api/projects/{project_id}/knowledge").json()["latest_plan"]["id"]

    run = client.post(f"/api/projects/{project_id}/knowledge/search-plans/{plan_id}/run")
    assert run.status_code == 200
    assert run.json()["state"]["status"] == "candidates_pending"

    candidates = client.get(f"/api/projects/{project_id}/knowledge/candidates")
    assert candidates.status_code == 200
    candidate_ids = [candidate["id"] for candidate in candidates.json()["candidates"]]
    assert candidate_ids

    decision = client.patch(
        f"/api/projects/{project_id}/knowledge/candidates/{candidate_ids[0]}",
        json={"user_decision": "include"},
    )
    assert decision.status_code == 200
    assert decision.json()["user_decision"] == "include"

    version = client.post(
        f"/api/projects/{project_id}/knowledge/corpus-versions",
        json={"plan_id": plan_id},
    )
    assert version.status_code == 200
    assert version.json()["state"]["status"] == "ready"
    assert version.json()["latest_corpus_version"]["document_count"] >= 1
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_api.py::test_project_creation_initializes_project_knowledge tests/test_api.py::test_project_knowledge_run_candidates_and_build_version -q
```

Expected: FAIL because endpoints do not exist.

- [ ] **Step 3: Add request schema**

In `backend/app/schemas.py`, add:

```python
class BuildProjectCorpusRequest(BaseModel):
    plan_id: str
```

- [ ] **Step 4: Add router**

Create `backend/app/api/project_knowledge.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.app.api.deps import get_project_repository, require_project
from backend.app.schemas import (
    BuildProjectCorpusRequest,
    CandidateBulkDecision,
    CandidateDecisionPatch,
)
from backend.app.services.project_knowledge_service import (
    create_project_corpus_from_included_candidates,
    ensure_project_knowledge_initialized,
    knowledge_overview,
    run_agent_search_plan,
)

router = APIRouter(tags=["project-knowledge"])


@router.get("/api/projects/{project_id}/knowledge")
def get_project_knowledge(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    return knowledge_overview(request.app.state.store, project_id).model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/search-intent")
def create_project_search_intent(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    project = require_project(project_id, repo)
    return ensure_project_knowledge_initialized(request.app.state.store, project).model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/search-plans/{plan_id}/run")
def run_project_search_plan(project_id: str, plan_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    try:
        overview = run_agent_search_plan(request.app.state.store, project_id, plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return overview.model_dump(mode="json")


@router.get("/api/projects/{project_id}/knowledge/candidates")
def list_project_candidates(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    store = request.app.state.store
    plan = store.get_latest_agent_search_plan(project_id)
    candidates = store.list_prior_art_candidates(project_id, plan.id if plan else None)
    return {"candidates": [candidate.model_dump(mode="json") for candidate in candidates]}


@router.patch("/api/projects/{project_id}/knowledge/candidates/{candidate_id}")
def update_project_candidate_decision(
    project_id: str,
    candidate_id: str,
    payload: CandidateDecisionPatch,
    request: Request,
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    candidate = request.app.state.store.update_prior_art_candidate_decision(
        project_id,
        candidate_id,
        payload.user_decision,
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Prior-art candidate not found.")
    return candidate.model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/candidates/bulk-decision")
def update_project_candidate_decisions(project_id: str, payload: CandidateBulkDecision, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    updated = []
    for candidate_id in payload.candidate_ids:
        candidate = request.app.state.store.update_prior_art_candidate_decision(
            project_id,
            candidate_id,
            payload.user_decision,
        )
        if candidate:
            updated.append(candidate.model_dump(mode="json"))
    return {"candidates": updated}


@router.post("/api/projects/{project_id}/knowledge/corpus-versions")
def create_project_corpus_version(
    project_id: str,
    payload: BuildProjectCorpusRequest,
    request: Request,
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    return create_project_corpus_from_included_candidates(
        request.app.state.store,
        project_id,
        payload.plan_id,
    ).model_dump(mode="json")
```

- [ ] **Step 5: Register router**

In `backend/app/main.py`, import and include the router:

```python
from backend.app.api.project_knowledge import router as project_knowledge_router
```

Inside `create_app`, near other router includes:

```python
    app.include_router(project_knowledge_router)
```

- [ ] **Step 6: Trigger initialization on project creation**

In `backend/app/api/projects.py`, import:

```python
from backend.app.services.project_knowledge_service import ensure_project_knowledge_initialized
```

Update `create_project`:

```python
@router.post("/api/projects")
def create_project(payload: ProjectCreate, request: Request) -> dict:
    repo = get_project_repository(request)
    project = build_project_record(payload)
    stored = repo.create(project)
    ensure_project_knowledge_initialized(request.app.state.store, stored)
    return stored.model_dump(mode="json")
```

- [ ] **Step 7: Run API tests**

Run:

```bash
python3 -m pytest tests/test_api.py::test_project_creation_initializes_project_knowledge tests/test_api.py::test_project_knowledge_run_candidates_and_build_version -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 3**

```bash
git add backend/app/schemas.py backend/app/api/project_knowledge.py backend/app/main.py backend/app/api/projects.py tests/test_api.py
git commit -m "feat: expose project knowledge API"
```

## Task 4: Frontend API And State Wiring

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/features/corpus/CorpusWorkspace.tsx`
- Modify: `frontend/src/api.test.ts`

**Interfaces:**
- Produces TypeScript types matching Task 1 schemas.
- Produces API functions:
  - `getProjectKnowledge(projectId: string): Promise<ProjectKnowledgeOverview>`
  - `createProjectSearchIntent(projectId: string): Promise<ProjectKnowledgeOverview>`
  - `runProjectSearchPlan(projectId: string, planId: string): Promise<ProjectKnowledgeOverview>`
  - `listProjectKnowledgeCandidates(projectId: string): Promise<PriorArtCandidate[]>`
  - `updateProjectKnowledgeCandidate(projectId: string, candidateId: string, userDecision: PriorArtCandidate["user_decision"]): Promise<PriorArtCandidate>`
  - `buildProjectCorpusVersion(projectId: string, planId: string): Promise<ProjectKnowledgeOverview>`

- [ ] **Step 1: Write failing API client tests**

Append to `frontend/src/api.test.ts`:

```ts
import {
  buildProjectCorpusVersion,
  getProjectKnowledge,
  runProjectSearchPlan,
  updateProjectKnowledgeCandidate,
} from "./api";

it("calls project knowledge endpoints", async () => {
  const requests: Array<{ url: string; init?: RequestInit }> = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    requests.push({ url, init });
    if (url.endsWith("/knowledge/candidates/c-1")) {
      return new Response(JSON.stringify({ id: "c-1", user_decision: "include" }), { status: 200 });
    }
    return new Response(JSON.stringify({ state: { project_id: "p-1", status: "ready" } }), { status: 200 });
  }));

  await getProjectKnowledge("p-1");
  await runProjectSearchPlan("p-1", "plan-1");
  await updateProjectKnowledgeCandidate("p-1", "c-1", "include");
  await buildProjectCorpusVersion("p-1", "plan-1");

  expect(requests.map((request) => request.url)).toEqual([
    "/api/projects/p-1/knowledge",
    "/api/projects/p-1/knowledge/search-plans/plan-1/run",
    "/api/projects/p-1/knowledge/candidates/c-1",
    "/api/projects/p-1/knowledge/corpus-versions",
  ]);
  expect(requests[2].init?.method).toBe("PATCH");
  expect(requests[3].init?.body).toBe(JSON.stringify({ plan_id: "plan-1" }));
});
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts
```

Expected: FAIL because the new functions do not exist.

- [ ] **Step 3: Add frontend types and API functions**

In `frontend/src/api.ts`, add types near corpus interfaces:

```ts
export type ProjectKnowledgeStatus =
  | "not_started"
  | "search_plan_pending"
  | "search_running"
  | "candidates_pending"
  | "corpus_building"
  | "ready"
  | "needs_supplemental_search"
  | "stale"
  | "failed";

export interface ProjectKnowledgeState {
  project_id: string;
  status: ProjectKnowledgeStatus;
  active_intent_id: string;
  active_plan_id: string;
  active_corpus_version_id: string;
  last_search_at: string;
  last_indexed_at: string;
  staleness_reason: string;
  document_count: number;
  candidate_count: number;
  claim_coverage: number;
  fulltext_coverage: number;
  quality_flags: string[];
}

export interface SearchIntent {
  id: string;
  project_id: string;
  source_project_hash: string;
  technical_object: string;
  technical_problem: string;
  technical_means: string;
  technical_effect: string;
  keywords_zh: string[];
  keywords_en: string[];
  synonyms: string[];
  negative_keywords: string[];
  ipc_candidates: string[];
  cpc_candidates: string[];
  jurisdictions: string[];
  date_range: string;
  created_by: "agent" | "user" | "system";
  created_at: string;
}

export interface SearchPlanStrategyGroup {
  id: string;
  label: string;
  purpose: string;
  queries: string[];
  sources: string[];
}

export interface AgentSearchPlan {
  id: string;
  project_id: string;
  intent_id: string;
  status: "draft" | "confirmed" | "running" | "completed" | "failed";
  strategy_groups: SearchPlanStrategyGroup[];
  target_sources: string[];
  target_result_count: number;
  filters: Record<string, unknown>;
  warnings: string[];
  created_at: string;
  confirmed_at: string;
  run_started_at: string;
  run_finished_at: string;
}

export interface PriorArtCandidate {
  id: string;
  project_id: string;
  plan_id: string;
  source: string;
  title: string;
  publication_number?: string | null;
  application_number?: string | null;
  applicant: string;
  publication_date: string;
  grant_date: string;
  abstract?: string | null;
  url: string;
  relevance_score: number;
  matched_terms: string[];
  ipc: string[];
  cpc: string[];
  family_id: string;
  duplicate_of: string;
  fulltext_status: "unknown" | "available" | "unavailable" | "failed";
  recommended_action: "include" | "exclude" | "review";
  recommendation_reason: string;
  user_decision: "pending" | "include" | "exclude";
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ProjectCorpusVersion {
  id: string;
  project_id: string;
  name: string;
  source_plan_id: string;
  candidate_set_id: string;
  status: "building" | "ready" | "failed" | "superseded";
  document_count: number;
  chunk_count: number;
  claim_coverage: number;
  fulltext_coverage: number;
  quality_report: CorpusQualityReport | null;
  created_at: string;
  superseded_by: string;
}

export interface ProjectKnowledgeOverview {
  state: ProjectKnowledgeState;
  latest_intent: SearchIntent | null;
  latest_plan: AgentSearchPlan | null;
  candidates: PriorArtCandidate[];
  latest_corpus_version: ProjectCorpusVersion | null;
}
```

Add API functions near corpus functions:

```ts
export async function getProjectKnowledge(projectId: string): Promise<ProjectKnowledgeOverview> {
  return request<ProjectKnowledgeOverview>(`/api/projects/${projectId}/knowledge`);
}

export async function createProjectSearchIntent(projectId: string): Promise<ProjectKnowledgeOverview> {
  return request<ProjectKnowledgeOverview>(`/api/projects/${projectId}/knowledge/search-intent`, {
    method: "POST",
  });
}

export async function runProjectSearchPlan(projectId: string, planId: string): Promise<ProjectKnowledgeOverview> {
  return request<ProjectKnowledgeOverview>(`/api/projects/${projectId}/knowledge/search-plans/${planId}/run`, {
    method: "POST",
  });
}

export async function listProjectKnowledgeCandidates(projectId: string): Promise<PriorArtCandidate[]> {
  const data = await request<{ candidates: PriorArtCandidate[] }>(`/api/projects/${projectId}/knowledge/candidates`);
  return data.candidates;
}

export async function updateProjectKnowledgeCandidate(
  projectId: string,
  candidateId: string,
  userDecision: PriorArtCandidate["user_decision"],
): Promise<PriorArtCandidate> {
  return request<PriorArtCandidate>(`/api/projects/${projectId}/knowledge/candidates/${candidateId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_decision: userDecision }),
  });
}

export async function buildProjectCorpusVersion(projectId: string, planId: string): Promise<ProjectKnowledgeOverview> {
  return request<ProjectKnowledgeOverview>(`/api/projects/${projectId}/knowledge/corpus-versions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId }),
  });
}
```

- [ ] **Step 4: Wire App state**

In `frontend/src/App.tsx`, import the new type and functions. Add state:

```ts
  const [projectKnowledge, setProjectKnowledge] = useState<ProjectKnowledgeOverview | null>(null);
```

Add loader:

```ts
  async function loadProjectKnowledge(projectId: string): Promise<void> {
    const overview = await getProjectKnowledge(projectId);
    if (selectedProjectIdRef.current === projectId) {
      setProjectKnowledge(overview);
    }
  }
```

Add handlers:

```ts
  async function handleGenerateKnowledgePlan(): Promise<void> {
    if (!selectedProject) return;
    await withStatus("knowledge-plan", async () => {
      const overview = await createProjectSearchIntent(selectedProject.id);
      setProjectKnowledge(overview);
      setMessage("已生成 Agent 检索计划。");
    });
  }

  async function handleRunKnowledgeSearch(): Promise<void> {
    if (!selectedProject || !projectKnowledge?.latest_plan) return;
    await withStatus("knowledge-search", async () => {
      const overview = await runProjectSearchPlan(selectedProject.id, projectKnowledge.latest_plan!.id);
      setProjectKnowledge(overview);
      setMessage(`已生成 ${overview.candidates.length} 条候选文献。`);
    });
  }

  async function handleCandidateDecision(candidateId: string, decision: PriorArtCandidate["user_decision"]): Promise<void> {
    if (!selectedProject) return;
    await withStatus("knowledge-candidate", async () => {
      await updateProjectKnowledgeCandidate(selectedProject.id, candidateId, decision);
      await loadProjectKnowledge(selectedProject.id);
    });
  }

  async function handleBuildProjectCorpus(): Promise<void> {
    if (!selectedProject || !projectKnowledge?.latest_plan) return;
    await withStatus("knowledge-build", async () => {
      const overview = await buildProjectCorpusVersion(selectedProject.id, projectKnowledge.latest_plan!.id);
      setProjectKnowledge(overview);
      setMessage(`项目语料库已就绪：${overview.state.document_count} 件文献。`);
    });
  }
```

Update selected-project data loading so `loadProjectKnowledge(projectId)` runs alongside existing project loaders after project selection and refresh.

- [ ] **Step 5: Extend CorpusWorkspace props**

In `frontend/src/features/corpus/CorpusWorkspace.tsx`, extend state and handlers:

```ts
  selectedProject: ProjectRecord | null;
  projectKnowledge: ProjectKnowledgeOverview | null;
```

```ts
  onGenerateKnowledgePlan: () => Promise<void> | void;
  onRunKnowledgeSearch: () => Promise<void> | void;
  onCandidateDecision: (candidateId: string, decision: PriorArtCandidate["user_decision"]) => Promise<void> | void;
  onBuildProjectCorpus: () => Promise<void> | void;
```

For now, continue rendering `CorpusBuildView`; Task 5 replaces it with `ProjectKnowledgeView`. This keeps Task 4 focused on compile-safe wiring.

- [ ] **Step 6: Run frontend API test**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts
```

Expected: PASS.

- [ ] **Step 7: Run frontend build**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS.

- [ ] **Step 8: Commit Task 4**

```bash
git add frontend/src/api.ts frontend/src/App.tsx frontend/src/features/corpus/CorpusWorkspace.tsx frontend/src/api.test.ts
git commit -m "feat: wire project knowledge client state"
```

## Task 5: Knowledge Workspace UI

**Files:**
- Create: `frontend/src/views/projectKnowledgeView.tsx`
- Create: `frontend/src/projectKnowledgeView.test.tsx`
- Modify: `frontend/src/features/corpus/CorpusWorkspace.tsx`
- Modify: `frontend/src/views/corpusBuildView.tsx`

**Interfaces:**
- Consumes `ProjectKnowledgeOverview`, `ProjectRecord`, and handlers from Task 4.
- Produces a project evidence status UI for the `build` knowledge tab.
- Keeps manual upload path available under a secondary advanced section.

- [ ] **Step 1: Write failing UI test**

Create `frontend/src/projectKnowledgeView.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProjectKnowledgeView } from "./views/projectKnowledgeView";
import type { ProjectKnowledgeOverview, ProjectRecord } from "./api";

const project: ProjectRecord = {
  id: "p-1",
  name: "城市体检智能体",
  draft_text: "任务编排和证据链复核。",
  patent_type: "invention",
  package: null,
  created_at: "",
  updated_at: "",
  applicant: "",
  inventors: "",
  technical_field: "",
  background: "",
  pain_point: "",
  technical_solution: "",
  innovation: "",
  embodiments: "",
  beneficial_effects: "",
};

const overview: ProjectKnowledgeOverview = {
  state: {
    project_id: "p-1",
    status: "search_plan_pending",
    active_intent_id: "intent-1",
    active_plan_id: "plan-1",
    active_corpus_version_id: "",
    last_search_at: "",
    last_indexed_at: "",
    staleness_reason: "",
    document_count: 0,
    candidate_count: 0,
    claim_coverage: 0,
    fulltext_coverage: 0,
    quality_flags: ["needs_search"],
  },
  latest_intent: {
    id: "intent-1",
    project_id: "p-1",
    source_project_hash: "hash",
    technical_object: "城市体检智能体",
    technical_problem: "任务复核不足",
    technical_means: "任务编排和证据链复核",
    technical_effect: "提高可信度",
    keywords_zh: ["城市体检", "智能体", "任务编排"],
    keywords_en: ["urban health", "agent"],
    synonyms: ["城市诊断"],
    negative_keywords: ["医疗体检"],
    ipc_candidates: ["G06Q"],
    cpc_candidates: ["G06Q10/063"],
    jurisdictions: ["CN"],
    date_range: "2016-2026",
    created_by: "agent",
    created_at: "",
  },
  latest_plan: {
    id: "plan-1",
    project_id: "p-1",
    intent_id: "intent-1",
    status: "draft",
    strategy_groups: [
      {
        id: "broad-recall",
        label: "宽召回检索",
        purpose: "尽量找全相关专利",
        queries: ["城市体检 智能体 任务编排"],
        sources: ["fake"],
      },
    ],
    target_sources: ["fake"],
    target_result_count: 20,
    filters: {},
    warnings: [],
    created_at: "",
    confirmed_at: "",
    run_started_at: "",
    run_finished_at: "",
  },
  candidates: [
    {
      id: "c-1",
      project_id: "p-1",
      plan_id: "plan-1",
      source: "fake",
      title: "一种城市体检任务编排方法",
      publication_number: "CN100A",
      application_number: null,
      applicant: "示例申请人",
      publication_date: "2024-01-01",
      grant_date: "",
      abstract: "公开了城市体检任务编排。",
      url: "https://patents.google.com/patent/CN100A",
      relevance_score: 0.87,
      matched_terms: ["城市体检"],
      ipc: [],
      cpc: [],
      family_id: "",
      duplicate_of: "",
      fulltext_status: "available",
      recommended_action: "include",
      recommendation_reason: "命中核心技术对象",
      user_decision: "pending",
      metadata: {},
      created_at: "",
    },
  ],
  latest_corpus_version: null,
};

describe("ProjectKnowledgeView", () => {
  it("renders plan, candidates, and calls handlers", () => {
    const onRunKnowledgeSearch = vi.fn();
    const onCandidateDecision = vi.fn();
    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={overview}
        busy=""
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={onRunKnowledgeSearch}
        onCandidateDecision={onCandidateDecision}
        onBuildProjectCorpus={vi.fn()}
      />,
    );

    expect(screen.getByText("项目现有技术库")).toBeInTheDocument();
    expect(screen.getByText("检索计划待确认")).toBeInTheDocument();
    expect(screen.getByText("宽召回检索")).toBeInTheDocument();
    expect(screen.getByText("一种城市体检任务编排方法")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "开始官方源检索" }));
    fireEvent.click(screen.getByRole("button", { name: "入库" }));

    expect(onRunKnowledgeSearch).toHaveBeenCalled();
    expect(onCandidateDecision).toHaveBeenCalledWith("c-1", "include");
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx
```

Expected: FAIL because `ProjectKnowledgeView` does not exist.

- [ ] **Step 3: Create project knowledge view**

Create `frontend/src/views/projectKnowledgeView.tsx`:

```tsx
import type { ReactNode } from "react";

import { AlertTriangle, CheckCircle2, Database, RefreshCw, Search, Wand2 } from "@/lib/icons";
import type { PriorArtCandidate, ProjectKnowledgeOverview, ProjectRecord } from "@/api";
import { StatusPill } from "./widgets";

const statusLabels: Record<string, string> = {
  not_started: "未生成检索计划",
  search_plan_pending: "检索计划待确认",
  search_running: "官方源检索中",
  candidates_pending: "候选文献待确认",
  corpus_building: "语料库建库中",
  ready: "语料库就绪",
  needs_supplemental_search: "需要补充检索",
  stale: "语料库过期",
  failed: "检索失败",
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function ProjectKnowledgeView({
  selectedProject,
  knowledge,
  busy,
  onGenerateKnowledgePlan,
  onRunKnowledgeSearch,
  onCandidateDecision,
  onBuildProjectCorpus,
  advancedFallback,
}: {
  selectedProject: ProjectRecord | null;
  knowledge: ProjectKnowledgeOverview | null;
  busy: string;
  onGenerateKnowledgePlan: () => void;
  onRunKnowledgeSearch: () => void;
  onCandidateDecision: (candidateId: string, decision: PriorArtCandidate["user_decision"]) => void;
  onBuildProjectCorpus: () => void;
  advancedFallback?: ReactNode;
}) {
  if (!selectedProject) {
    return (
      <section className="border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6">
        <h3>项目现有技术库</h3>
        <p className="text-sm text-[var(--text-primary)]/60">请先创建或选择项目，Agent 会根据项目题目和一句话介绍生成检索计划。</p>
      </section>
    );
  }

  const status = knowledge?.state.status ?? "not_started";
  const candidates = knowledge?.candidates ?? [];
  const plan = knowledge?.latest_plan ?? null;
  const intent = knowledge?.latest_intent ?? null;
  const state = knowledge?.state;

  return (
    <div className="flex flex-col gap-4">
      <section className="border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3>项目现有技术库</h3>
            <p className="text-sm text-[var(--text-primary)]/65">Agent 根据项目题目和一句话介绍生成检索计划、候选文献池和项目语料库。</p>
          </div>
          <button
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium disabled:opacity-50"
            disabled={busy.startsWith("knowledge")}
            onClick={status === "not_started" ? onGenerateKnowledgePlan : status === "search_plan_pending" ? onRunKnowledgeSearch : status === "candidates_pending" ? onBuildProjectCorpus : onGenerateKnowledgePlan}
            type="button"
          >
            {status === "search_plan_pending" ? <Search size={17} /> : status === "candidates_pending" ? <Database size={17} /> : <Wand2 size={17} />}
            <span>{status === "search_plan_pending" ? "开始官方源检索" : status === "candidates_pending" ? "确认建库" : status === "ready" ? "补充检索" : "让 Agent 生成检索计划"}</span>
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-5">
          <StatusPill label="知识状态" value={statusLabels[status] ?? status} />
          <StatusPill label="候选文献" value={String(state?.candidate_count ?? candidates.length)} />
          <StatusPill label="入库文献" value={String(state?.document_count ?? 0)} />
          <StatusPill label="权利要求覆盖" value={percent(state?.claim_coverage ?? 0)} />
          <StatusPill label="全文覆盖" value={percent(state?.fulltext_coverage ?? 0)} />
        </div>
        {status === "stale" && (
          <p className="mt-4 text-sm text-[var(--danger)] flex items-center gap-2">
            <AlertTriangle size={16} />
            {state?.staleness_reason || "项目技术方案已变化，需要补充检索。"}
          </p>
        )}
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6">
          <h3>Agent 检索计划</h3>
          {intent ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-[var(--text-primary)]/70">{intent.technical_means || intent.technical_object}</p>
              <div className="flex flex-wrap gap-2">
                {intent.keywords_zh.map((keyword) => (
                  <span className="tag" key={keyword}>{keyword}</span>
                ))}
              </div>
              {plan?.strategy_groups.map((group) => (
                <article className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-inset)] p-4" key={group.id}>
                  <p className="font-semibold">{group.label}</p>
                  <p className="text-sm text-[var(--text-primary)]/65">{group.purpose}</p>
                  <p className="text-xs text-[var(--text-primary)]/55 mt-2">{group.queries.join(" / ")}</p>
                </article>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-primary)]/50 italic">还没有检索计划。</p>
          )}
        </div>

        <div className="border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6">
          <h3>候选文献池</h3>
          <div className="flex flex-col gap-3">
            {candidates.map((candidate) => (
              <article className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-inset)] p-4" key={candidate.id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{candidate.title}</p>
                    <p className="text-xs text-[var(--text-primary)]/55">{candidate.publication_number || "未记录公开号"} · {candidate.source}</p>
                  </div>
                  <button
                    className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-sm"
                    onClick={() => onCandidateDecision(candidate.id, "include")}
                    type="button"
                  >
                    <CheckCircle2 size={15} />
                    入库
                  </button>
                </div>
                <p className="mt-2 text-sm text-[var(--text-primary)]/65">{candidate.abstract}</p>
                <p className="mt-2 text-xs text-[var(--text-primary)]/55">{candidate.recommendation_reason}</p>
              </article>
            ))}
            {candidates.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic">运行官方源检索后会出现候选文献。</p>}
          </div>
        </div>
      </section>

      {advancedFallback && (
        <details className="border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6">
          <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)]">
            <span className="inline-flex items-center gap-2">
              <RefreshCw size={16} />
              从本地文件补充语料
            </span>
          </summary>
          <div className="mt-4">{advancedFallback}</div>
        </details>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Route build tab to ProjectKnowledgeView**

In `frontend/src/features/corpus/CorpusWorkspace.tsx`, import `ProjectKnowledgeView`. Replace the `tool === "build"` render with:

```tsx
    return (
      <ProjectKnowledgeView
        selectedProject={state.selectedProject}
        knowledge={state.projectKnowledge}
        busy={state.busy}
        onGenerateKnowledgePlan={() => void handlers.onGenerateKnowledgePlan()}
        onRunKnowledgeSearch={() => void handlers.onRunKnowledgeSearch()}
        onCandidateDecision={(candidateId, decision) => void handlers.onCandidateDecision(candidateId, decision)}
        onBuildProjectCorpus={() => void handlers.onBuildProjectCorpus()}
        advancedFallback={
          <CorpusBuildView
            form={state.corpusJobForm}
            job={state.corpusJob}
            versions={state.corpusVersions}
            stats={state.corpusStats}
            busy={state.busy}
            onFormChange={handlers.onCorpusFormChange}
            onCreateJob={(event) => void handlers.onCreateCorpusJob(event)}
            onUploadFile={(event) => void handlers.onUploadCorpusJobFile(event)}
            onRunJob={() => void handlers.onRunCorpusJob()}
          />
        }
      />
    );
```

Keep `CorpusBuildView` exported for advanced fallback and future reuse; do not delete it in this task.

- [ ] **Step 5: Run UI test**

Run:

```bash
npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Run frontend build**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

```bash
git add frontend/src/views/projectKnowledgeView.tsx frontend/src/projectKnowledgeView.test.tsx frontend/src/features/corpus/CorpusWorkspace.tsx frontend/src/views/corpusBuildView.tsx
git commit -m "feat: show project evidence corpus workspace"
```

## Task 6: Writing-Flow Gates

**Files:**
- Modify: `backend/app/grantability.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_grantability.py`
- Modify: `frontend/src/features/quality/QualityWorkspace.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/views/qualityViews.tsx`

**Interfaces:**
- Consumes: `ProjectKnowledgeState`.
- Produces low-evidence blocking flags in grantability reports when project knowledge is missing, stale, or below coverage thresholds.
- Produces frontend copy that explains the evidence gate before running grantability.

- [ ] **Step 1: Write failing backend gate test**

Append this to `tests/test_grantability.py`:

```python
def test_grantability_low_evidence_when_project_corpus_missing() -> None:
    package = _basic_package()

    report = generate_grantability_report(
        project_id="project-knowledge-gate",
        package=package,
        disclosures=[],
        patent_points=[],
        strategy_brief=None,
        project_knowledge_state=None,
    )

    assert report.status in {"low", "medium"}
    assert any("项目语料库未就绪" in flag for flag in report.low_evidence_flags)
    assert "现有技术证据不足" in report.overall_assessment
```

If `_basic_package()` does not exist in the file, add this helper near existing helpers:

```python
def _basic_package() -> DraftPackage:
    return DraftPackage(
        title="城市体检智能体任务编排方法",
        abstract="通过任务编排和证据链复核生成可信报告。",
        claims="1. 一种城市体检智能体任务编排方法，其特征在于，生成任务 DAG 并绑定证据链复核节点。",
        description="本实施例生成任务 DAG 并绑定证据链复核节点。",
        drawing_description="",
        mermaid="",
        image_prompt="",
    )
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_grantability.py::test_grantability_low_evidence_when_project_corpus_missing -q
```

Expected: FAIL because `generate_grantability_report` does not accept `project_knowledge_state`.

- [ ] **Step 3: Extend grantability input**

In `backend/app/grantability.py`, import `ProjectKnowledgeState`. Update `generate_grantability_report` signature:

```python
def generate_grantability_report(
    project_id: str,
    package: DraftPackage,
    disclosures: list[DisclosureRun],
    patent_points: list[PatentPointCandidate],
    strategy_brief: PatentStrategyBrief | None = None,
    deep_research_packets: list[DeepResearchPacket] | None = None,
    project_knowledge_state: ProjectKnowledgeState | None = None,
) -> GrantabilityReport:
```

Near the existing low-evidence flag aggregation, add:

```python
    if project_knowledge_state is None:
        low_evidence_flags.append("项目语料库未就绪，授权前景不能给出高置信结论。")
    elif project_knowledge_state.status in {"not_started", "search_plan_pending", "search_running", "candidates_pending", "corpus_building"}:
        low_evidence_flags.append(f"项目语料库状态为{project_knowledge_state.status}，尚不能支撑高置信授权判断。")
    elif project_knowledge_state.status == "stale":
        low_evidence_flags.append("项目语料库已过期，需要补充检索后再确认授权前景。")
    elif project_knowledge_state.document_count < 2:
        low_evidence_flags.append("项目语料库入库文献少于 2 件，现有技术证据不足。")
```

Keep existing prior-art hit checks. Do not remove current low-evidence behavior.

- [ ] **Step 4: Pass state from API**

In `backend/app/main.py`, update the grantability endpoint:

```python
        knowledge_state = store.get_project_knowledge_state(project_id)
        report = generate_grantability_report(
            project_id=project_id,
            package=package,
            disclosures=disclosures,
            patent_points=patent_points,
            strategy_brief=strategy_brief,
            deep_research_packets=_deep_research_packets_from_disclosures(disclosures),
            project_knowledge_state=knowledge_state,
        )
```

- [ ] **Step 5: Pass project knowledge into quality workspace**

In `frontend/src/features/quality/QualityWorkspace.tsx`, import `ProjectKnowledgeOverview` and add it to `QualityWorkspaceState`:

```ts
import type {
  ClaimDefenseWorksheet,
  DraftCompletionRun,
  FilingReadinessReport,
  GrantabilityReport,
  OfficialCompileRun,
  PostDraftReviewRun,
  ProjectKnowledgeOverview,
  ProjectRecord,
} from "@/api";
```

```ts
  projectKnowledge: ProjectKnowledgeOverview | null;
```

Pass it to `GrantabilityView`:

```tsx
        <GrantabilityView
          project={state.selectedProject}
          projectKnowledge={state.projectKnowledge}
          report={state.latestGrantabilityReport}
          reports={state.grantabilityReports}
          busy={state.busy}
          onGenerate={() => void handlers.onCreateGrantabilityReport()}
        />
```

In `frontend/src/App.tsx`, add `projectKnowledge` to the `qualityState` object:

```tsx
      qualityState={{
        selectedProject,
        projectKnowledge,
        filingReports,
        latestFilingReport,
        grantabilityReports,
        latestGrantabilityReport,
        worksheets,
        latestWorksheet,
        completionRuns,
        latestCompletionRun,
        latestOfficialCompileRun,
        latestPostDraftReview,
        currentDraftHash,
        currentSourceDraftHash,
        busy,
      }}
```

- [ ] **Step 6: Add frontend gate copy**

In `frontend/src/views/qualityViews.tsx`, import `ProjectKnowledgeOverview`, add a `projectKnowledge` prop to `GrantabilityView`, and derive this status note:

```tsx
export function GrantabilityView({
  project,
  projectKnowledge,
  report,
  reports,
  busy,
  onGenerate,
}: {
  project: ProjectRecord | null;
  projectKnowledge: ProjectKnowledgeOverview | null;
  report: GrantabilityReport | null;
  reports: GrantabilityReport[];
  busy: string;
  onGenerate: () => void;
}) {
```

Use this copy:

```tsx
const knowledgeGateCopy =
  !projectKnowledge || projectKnowledge.state.status !== "ready"
    ? "项目语料库未就绪：可以生成草案，但授权前景和权利要求防线只能输出证据不足结论。"
    : `项目语料库已就绪：已入库 ${projectKnowledge.state.document_count} 件文献，可用于授权前景分析。`;
```

Render the note above the grantability button:

```tsx
<p className="text-sm text-[var(--text-primary)]/65">{knowledgeGateCopy}</p>
```

- [ ] **Step 7: Run backend gate tests**

Run:

```bash
python3 -m pytest tests/test_grantability.py::test_grantability_low_evidence_when_project_corpus_missing tests/test_api.py::test_grantability_report_api_generates_persists_and_exports -q
```

Expected: PASS.

- [ ] **Step 8: Run frontend build**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS.

- [ ] **Step 9: Commit Task 6**

```bash
git add backend/app/grantability.py backend/app/main.py tests/test_grantability.py frontend/src/features/quality/QualityWorkspace.tsx frontend/src/views/qualityViews.tsx frontend/src/App.tsx
git commit -m "feat: gate grantability on project corpus readiness"
```

## Task 7: End-To-End Verification And Documentation Update

**Files:**
- Modify: `docs/project-design-overview.md`
- Modify: `docs/superpowers/specs/2026-06-29-project-evidence-corpus-design.md`
- Test-only commands across backend and frontend.

**Interfaces:**
- Consumes all previous tasks.
- Produces updated architecture docs and full verification output.

- [ ] **Step 1: Update project overview**

In `docs/project-design-overview.md`, replace the knowledge row currently describing “导入官方导出物，检索授权专利片段” with:

```md
| 知识库 | 项目现有技术库、知识库检索、高级导入 | Agent 从项目题目和一句话介绍生成检索计划，检索官方/公开源，形成项目级现有技术语料库；高级用户仍可导入本地官方导出物 |
```

In the API section, replace the corpus paragraph with:

```md
### 项目现有技术库和语料库

- `GET /api/projects/{project_id}/knowledge`：查看项目知识状态、最新检索意图、检索计划、候选文献和语料库版本。
- `POST /api/projects/{project_id}/knowledge/search-intent`：从项目题目和一句话介绍生成检索意图与 Agent 检索计划。
- `POST /api/projects/{project_id}/knowledge/search-plans/{plan_id}/run`：执行官方/公开源检索，写入候选文献池。
- `GET/PATCH /api/projects/{project_id}/knowledge/candidates`：查看并确认候选文献。
- `POST /api/projects/{project_id}/knowledge/corpus-versions`：从已确认候选文献创建项目语料库版本。
- `POST /api/corpus/jobs`、`POST /api/corpus/jobs/{job_id}/files`、`POST /api/corpus/jobs/{job_id}/run`：高级本地文件补充语料。
```

- [ ] **Step 2: Run backend targeted tests**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py tests/test_api.py::test_project_creation_initializes_project_knowledge tests/test_api.py::test_project_knowledge_run_candidates_and_build_version tests/test_grantability.py::test_grantability_low_evidence_when_project_corpus_missing -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend targeted tests**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts src/projectKnowledgeView.test.tsx
```

Expected: PASS.

- [ ] **Step 4: Run broad gates**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py tests/test_api.py tests/test_grantability.py -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Expected: PASS. If a broad test fails outside files touched by this plan, record the failure and run the narrow gates again before handoff.

- [ ] **Step 5: Manual dev-server smoke**

Start backend and frontend in separate terminals:

```bash
uvicorn backend.app.main:app --reload
npm --prefix frontend run dev
```

Open the app and verify:

1. Create a project named `城市体检智能体`.
2. Navigate to `知识库`.
3. Confirm the first screen shows `项目现有技术库`, not `官方导出物批量建库`.
4. Confirm status is `检索计划待确认`.
5. Click `开始官方源检索`.
6. Confirm candidate cards appear.
7. Click `入库` on at least one candidate.
8. Click `确认建库`.
9. Confirm status becomes `语料库就绪`.
10. Navigate to `授权前景` and confirm the evidence note references the project corpus state.

- [ ] **Step 6: Commit Task 7**

```bash
git add docs/project-design-overview.md docs/superpowers/specs/2026-06-29-project-evidence-corpus-design.md
git commit -m "docs: describe project evidence corpus workflow"
```

## Self-Review

**Spec coverage**

- Project creation triggers search intent: Task 3 initializes knowledge from `POST /api/projects`.
- Agent-generated search plan: Task 2 creates deterministic intent and plan; Task 3 exposes endpoints.
- Official/public-source retrieval without upload: Task 2 uses fake provider first; provider abstraction is isolated for later live sources.
- Candidate prior-art pool: Tasks 1-3 persist and expose candidates; Task 5 renders them.
- Project corpus version: Tasks 1-3 persist and create versions; Task 5 displays readiness.
- Writing-flow gates: Task 6 gates grantability; quality UI gets readiness copy.
- Advanced upload fallback: Task 5 keeps old import view available as a fallback; Task 7 documents it.
- Tests: Each task has narrow tests and Task 7 has broad gates.

**Type consistency**

- Backend uses `ProjectKnowledgeState`, `SearchIntent`, `AgentSearchPlan`, `PriorArtCandidate`, and `ProjectCorpusVersion`.
- Frontend mirrors these names and endpoint payloads.
- Candidate decisions use `pending | include | exclude` in both Python and TypeScript.
- Knowledge status uses the same enum strings in Python and TypeScript.

**Risk notes**

- Task 2 deliberately uses a fake provider. Live CNIPA/Google Patents provider implementation should be a later plan after the product flow is proven.
- Task 5 creates the new default knowledge UI but does not delete the manual import implementation.
- Task 6 only gates high-confidence grantability; it does not make formal export impossible solely because project corpus is missing.
