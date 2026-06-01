# Patent Moat Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current patent drafting workbench into a patent moat workbench where users can add feasible but unverified technical schemes, track evidence status, compare prior art, and inject selected schemes into disclosure and claim drafting without pretending unverified ideas are proven implementations.

**Architecture:** Add a small patent-point domain model shared by disclosure generation, drafting, storage, API, and frontend. Persist user-entered patent points separately from generated disclosure runs, merge them into disclosure generation, and carry evidence/moat metadata through exports and prompts. Keep the current RAG, corpus import, deliberation, and disclosure flows intact.

**Tech Stack:** FastAPI, Pydantic v2, SQLite, python-docx, React 19, Vite, TypeScript, Vitest, pytest.

---

## Current Constraints

- CodeGraph is not initialized in `/Users/leo/Projects/patents_agent`; use direct file reads during this plan execution unless the user explicitly asks to initialize CodeGraph with `codegraph init -i`.
- The project directory is not currently a git repository. Every task has a checkpoint command that first checks `git rev-parse --is-inside-work-tree`. If that command fails, skip the commit and record the completed task in the final execution summary.
- The root `.env` currently configures `DEEPSEEK_API_KEY`; tests for missing-provider behavior must isolate themselves from `.env`.
- Existing live verification anchors are backend port `8000`, frontend port `5174` when `5173` is occupied, `python3 -m pytest -q`, `npm test -- --run`, and `npm run build`.

## File Structure

- Modify `backend/app/schemas.py`: add evidence status, source type, moat scores, claim-chart item, patent-point create/update payloads, and backward-compatible fields on `PatentPointCandidate`.
- Modify `backend/app/storage.py`: add `project_patent_points` table and CRUD methods.
- Modify `backend/app/main.py`: add patent-point endpoints, pass saved user candidates into disclosure generation and final draft generation, and allow tests to disable `.env` loading.
- Modify `backend/app/settings.py`: support explicit settings construction without loading `.env` for tests.
- Modify `backend/app/disclosure/generator.py`: accept user candidates, preserve them during LLM candidate parsing, create per-candidate prior-art claim-chart data, and include evidence warnings.
- Modify `backend/app/generator.py`: update prompts so unverified feasible schemes are included as optional embodiments or variants, not as completed facts.
- Modify `backend/app/disclosure/exporter.py` and `backend/app/exporter.py`: expose moat metadata, evidence status, and claim charts in exported Markdown/DOCX.
- Modify `frontend/src/domain.ts`: add `moat` workspace tab and helper labels for evidence/source/scoring.
- Modify `frontend/src/api.ts`: add patent-point types and API methods.
- Modify `frontend/src/App.tsx`: add the "护城河地图" workspace, forms, candidate cards, and selected-point context in write/disclosure views.
- Modify `frontend/src/styles.css`: add compact styles for patent-point forms, score grids, status badges, and claim-chart blocks.
- Modify `frontend/src/domain.test.ts`: update tab order and add evidence/moat helper tests.
- Modify `tests/test_api.py`, `tests/test_disclosure.py`, and create `tests/test_patent_points.py`: cover missing-provider isolation, point CRUD, disclosure merge, and draft prompt injection.
- Modify `README.md`: document the patent moat workflow and the rule for feasible but unverified schemes.

---

### Task 1: Stabilize Settings And Missing-Provider Tests

**Files:**
- Modify: `backend/app/settings.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_disclosure.py`

- [ ] **Step 1: Write failing missing-provider isolation tests**

Add this helper and update the two missing-provider tests so they pass `load_env_file=False`:

```python
# tests/test_api.py
def _test_app_without_env(tmp_path):
    return TestClient(create_app(data_dir=tmp_path, load_env_file=False))
```

```python
# tests/test_api.py
def test_generate_fails_closed_without_llm_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = _test_app_without_env(tmp_path)
    project_response = client.post(
        "/api/projects",
        json={"name": "未配置模型", "draft_text": "一种AI方法，用于生成专利文本。"},
    )
    project_id = project_response.json()["id"]

    generate_response = client.post(f"/api/projects/{project_id}/generate")

    assert generate_response.status_code == 503
    assert "DEEPSEEK_API_KEY" in generate_response.json()["detail"]
```

```python
# tests/test_disclosure.py
def test_disclosure_generation_fails_closed_without_llm(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_response = client.post(
        "/api/projects",
        json={"name": "未配置模型", "draft_text": "一种AI方法，用于生成交底书。"},
    )
    project_id = project_response.json()["id"]
    material_response = client.post(
        f"/api/projects/{project_id}/materials",
        files={"file": ("material.txt", b"local material", "text/plain")},
    )
    assert material_response.status_code == 200

    disclosure_response = client.post(f"/api/projects/{project_id}/disclosures", json={"trace": False})

    assert disclosure_response.status_code == 503
    assert "DEEPSEEK_API_KEY" in disclosure_response.json()["detail"]
```

- [ ] **Step 2: Run tests to verify the current signature fails**

Run:

```bash
python3 -m pytest tests/test_api.py::test_generate_fails_closed_without_llm_configuration tests/test_disclosure.py::test_disclosure_generation_fails_closed_without_llm -q
```

Expected: FAIL with `TypeError: create_app() got an unexpected keyword argument 'load_env_file'`.

- [ ] **Step 3: Add explicit settings builder**

Add this function to `backend/app/settings.py`:

```python
def build_settings(*, load_env_file: bool = True) -> Settings:
    if load_env_file:
        return Settings()
    return Settings(_env_file=None)
```

- [ ] **Step 4: Use settings builder in app factory**

Update the import and `create_app` signature in `backend/app/main.py`:

```python
from backend.app.settings import Settings, build_settings
```

```python
def create_app(
    data_dir: Path | None = None,
    llm_client: LLMClient | None = None,
    provider_runner: object | None = None,
    prior_art_provider: object | None = None,
    load_env_file: bool = True,
) -> FastAPI:
    settings = build_settings(load_env_file=load_env_file)
```

Keep `app = create_app()` at the bottom unchanged so normal local startup still reads `.env`.

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_api.py::test_generate_fails_closed_without_llm_configuration tests/test_disclosure.py::test_disclosure_generation_fails_closed_without_llm -q
```

Expected: `2 passed`.

- [ ] **Step 6: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/settings.py backend/app/main.py tests/test_api.py tests/test_disclosure.py && git commit -m "test: isolate missing llm configuration" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 2: Add Patent Point Domain Types

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/domain.ts`
- Modify: `frontend/src/domain.test.ts`

- [ ] **Step 1: Write backend schema tests**

Create `tests/test_patent_points.py` with:

```python
from backend.app.schemas import MoatScores, PatentPointCandidate, PatentPointCreate


def test_patent_point_defaults_support_unverified_user_schemes():
    payload = PatentPointCreate(
        title="遮挡构件语义补全方法",
        technical_problem="遮挡导致门窗洞口漏识别",
        innovation="用多视角互证补全遮挡洞口",
        technical_solution="获取多视角图像和点云，反投二维语义并补全洞口边界。",
        evidence_status="feasible_unverified",
        source_type="user",
        feasibility_basis="已有多视角图像和点云输入，算法路径可实现。",
    )

    candidate = payload.to_candidate("p-user-1")

    assert candidate.id == "p-user-1"
    assert candidate.evidence_status == "feasible_unverified"
    assert candidate.source_type == "user"
    assert candidate.moat_scores.support_strength == 0.2
    assert "提交前需补充实验或工程样例" in candidate.support_gaps


def test_existing_candidate_payloads_remain_backward_compatible():
    candidate = PatentPointCandidate(
        id="p1",
        title="图像缺陷识别方法及系统",
        technical_problem="人工检测效率低",
        innovation="基于神经网络输出缺陷位置",
        technical_solution="采集图像、训练模型并输出缺陷位置",
    )

    assert candidate.evidence_status == "model_generated"
    assert isinstance(candidate.moat_scores, MoatScores)
```

- [ ] **Step 2: Run test to verify missing types fail**

Run:

```bash
python3 -m pytest tests/test_patent_points.py -q
```

Expected: FAIL with import errors for `MoatScores` and `PatentPointCreate`.

- [ ] **Step 3: Add backend Pydantic types**

Add these classes above `PatentPointCandidate` in `backend/app/schemas.py`:

```python
class MoatScores(BaseModel):
    scope_width: float = Field(default=0.0, ge=0.0, le=1.0)
    designaround_difficulty: float = Field(default=0.0, ge=0.0, le=1.0)
    feasibility: float = Field(default=0.0, ge=0.0, le=1.0)
    support_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    prior_art_distance: float = Field(default=0.0, ge=0.0, le=1.0)
    strategic_value: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def weighted_total(self) -> float:
        return round(
            self.scope_width * 0.18
            + self.designaround_difficulty * 0.18
            + self.feasibility * 0.16
            + self.support_strength * 0.16
            + self.prior_art_distance * 0.16
            + self.strategic_value * 0.16,
            3,
        )


class ClaimChartItem(BaseModel):
    prior_art_id: str
    prior_art_title: str
    overlapping_features: list[str] = Field(default_factory=list)
    differentiating_features: list[str] = Field(default_factory=list)
    claim_drafting_advice: str = ""


class PatentPointCreate(BaseModel):
    title: str
    technical_problem: str
    innovation: str
    technical_solution: str
    beneficial_effects: list[str] = Field(default_factory=list)
    protection_focus: list[str] = Field(default_factory=list)
    evidence_status: str = Field(default="feasible_unverified", pattern="^(verified|feasible_unverified|needs_experiment|model_generated)$")
    source_type: str = Field(default="user", pattern="^(user|model|imported)$")
    feasibility_basis: str = ""
    support_gaps: list[str] = Field(default_factory=list)
    experiment_needed: list[str] = Field(default_factory=list)
    moat_scores: MoatScores = Field(default_factory=lambda: MoatScores(feasibility=0.5, support_strength=0.2, strategic_value=0.6))
    selected: bool = False
    rationale: str = ""

    def to_candidate(self, point_id: str) -> "PatentPointCandidate":
        gaps = list(self.support_gaps)
        if self.evidence_status in {"feasible_unverified", "needs_experiment"} and not gaps:
            gaps.append("提交前需补充实验或工程样例。")
        return PatentPointCandidate(
            id=point_id,
            title=self.title,
            technical_problem=self.technical_problem,
            innovation=self.innovation,
            technical_solution=self.technical_solution,
            beneficial_effects=self.beneficial_effects,
            protection_focus=self.protection_focus,
            evidence_status=self.evidence_status,
            source_type=self.source_type,
            feasibility_basis=self.feasibility_basis,
            support_gaps=gaps,
            experiment_needed=self.experiment_needed,
            moat_scores=self.moat_scores,
            selected=self.selected,
            rationale=self.rationale,
        )


class PatentPointUpdate(BaseModel):
    title: str | None = None
    technical_problem: str | None = None
    innovation: str | None = None
    technical_solution: str | None = None
    beneficial_effects: list[str] | None = None
    protection_focus: list[str] | None = None
    evidence_status: str | None = Field(default=None, pattern="^(verified|feasible_unverified|needs_experiment|model_generated)$")
    source_type: str | None = Field(default=None, pattern="^(user|model|imported)$")
    feasibility_basis: str | None = None
    support_gaps: list[str] | None = None
    experiment_needed: list[str] | None = None
    moat_scores: MoatScores | None = None
    selected: bool | None = None
    rationale: str | None = None
```

Extend `PatentPointCandidate` with defaults:

```python
class PatentPointCandidate(BaseModel):
    id: str
    title: str
    technical_problem: str
    innovation: str
    technical_solution: str
    beneficial_effects: list[str] = Field(default_factory=list)
    protection_focus: list[str] = Field(default_factory=list)
    grantability_score: float = 0.0
    rationale: str = ""
    evidence_status: str = Field(default="model_generated", pattern="^(verified|feasible_unverified|needs_experiment|model_generated)$")
    source_type: str = Field(default="model", pattern="^(user|model|imported)$")
    feasibility_basis: str = ""
    support_gaps: list[str] = Field(default_factory=list)
    experiment_needed: list[str] = Field(default_factory=list)
    moat_scores: MoatScores = Field(default_factory=MoatScores)
    claim_chart: list[ClaimChartItem] = Field(default_factory=list)
    selected: bool = False
```

- [ ] **Step 4: Add frontend API types**

In `frontend/src/api.ts`, add:

```ts
export type EvidenceStatus = "verified" | "feasible_unverified" | "needs_experiment" | "model_generated";
export type PatentPointSourceType = "user" | "model" | "imported";

export interface MoatScores {
  scope_width: number;
  designaround_difficulty: number;
  feasibility: number;
  support_strength: number;
  prior_art_distance: number;
  strategic_value: number;
}

export interface ClaimChartItem {
  prior_art_id: string;
  prior_art_title: string;
  overlapping_features: string[];
  differentiating_features: string[];
  claim_drafting_advice: string;
}
```

Extend `PatentPointCandidate` with matching optional-safe fields:

```ts
  evidence_status: EvidenceStatus;
  source_type: PatentPointSourceType;
  feasibility_basis: string;
  support_gaps: string[];
  experiment_needed: string[];
  moat_scores: MoatScores;
  claim_chart: ClaimChartItem[];
  selected: boolean;
```

- [ ] **Step 5: Add frontend domain helpers and update tab order test**

In `frontend/src/domain.ts`, add `ShieldCheck` to lucide imports and insert the tab after `"create"`:

```ts
export type WorkspaceTabId = "build" | "corpus" | "create" | "moat" | "materials" | "deliberate" | "write" | "review" | "export";
```

```ts
{ id: "moat", label: "护城河地图", icon: ShieldCheck },
```

Add helpers:

```ts
export function evidenceStatusLabel(status: string): string {
  if (status === "verified") return "已验证";
  if (status === "feasible_unverified") return "可行未验证";
  if (status === "needs_experiment") return "需实验";
  return "模型生成";
}

export function sourceTypeLabel(source: string): string {
  if (source === "user") return "用户输入";
  if (source === "imported") return "材料导入";
  return "模型生成";
}

export function moatScoreTotal(scores: {
  scope_width: number;
  designaround_difficulty: number;
  feasibility: number;
  support_strength: number;
  prior_art_distance: number;
  strategic_value: number;
}): number {
  return Number(
    (
      scores.scope_width * 0.18
      + scores.designaround_difficulty * 0.18
      + scores.feasibility * 0.16
      + scores.support_strength * 0.16
      + scores.prior_art_distance * 0.16
      + scores.strategic_value * 0.16
    ).toFixed(3),
  );
}
```

Update `frontend/src/domain.test.ts` expected tab labels to include `"护城河地图"` after `"创建专利项目"` and add:

```ts
describe("patent moat helpers", () => {
  it("labels evidence status and computes weighted moat score", async () => {
    const { evidenceStatusLabel, moatScoreTotal, sourceTypeLabel } = await import("./domain");
    expect(evidenceStatusLabel("feasible_unverified")).toBe("可行未验证");
    expect(sourceTypeLabel("user")).toBe("用户输入");
    expect(moatScoreTotal({
      scope_width: 1,
      designaround_difficulty: 1,
      feasibility: 0.5,
      support_strength: 0,
      prior_art_distance: 0.5,
      strategic_value: 1,
    })).toBe(0.7);
  });
});
```

- [ ] **Step 6: Run schema and frontend helper tests**

Run:

```bash
python3 -m pytest tests/test_patent_points.py -q
cd frontend && npm test -- --run
```

Expected: backend test passes; frontend test passes with updated tab order.

- [ ] **Step 7: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/schemas.py frontend/src/api.ts frontend/src/domain.ts frontend/src/domain.test.ts tests/test_patent_points.py && git commit -m "feat: add patent moat point types" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 3: Persist User Patent Points Through API

**Files:**
- Modify: `backend/app/storage.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_patent_points.py`

- [ ] **Step 1: Add failing API lifecycle test**

Append to `tests/test_patent_points.py`:

```python
from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


def test_project_patent_point_crud_and_selection(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_response = client.post(
        "/api/projects",
        json={"name": "外立面逆建模", "draft_text": "一种既有建筑外立面逆建模方法。"},
    )
    project_id = project_response.json()["id"]

    create_response = client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "遮挡洞口语义补全",
            "technical_problem": "树木和防盗网遮挡导致洞口漏识别",
            "innovation": "多视角语义互证并补全洞口边界",
            "technical_solution": "融合点云、图像和楼层规律生成洞口边界。",
            "beneficial_effects": ["降低洞口漏检率"],
            "protection_focus": ["方法", "系统", "介质"],
            "evidence_status": "feasible_unverified",
            "source_type": "user",
            "feasibility_basis": "已有多视角图像、点云和人工复核记录。",
            "selected": True,
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["source_type"] == "user"
    assert created["selected"] is True

    list_response = client.get(f"/api/projects/{project_id}/patent-points")
    assert list_response.status_code == 200
    assert list_response.json()["points"][0]["title"] == "遮挡洞口语义补全"

    patch_response = client.patch(
        f"/api/projects/{project_id}/patent-points/{created['id']}",
        json={"evidence_status": "needs_experiment", "experiment_needed": ["用10栋楼样例统计洞口召回率"]},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["evidence_status"] == "needs_experiment"

    delete_response = client.delete(f"/api/projects/{project_id}/patent-points/{created['id']}")
    assert delete_response.status_code == 200
    assert client.get(f"/api/projects/{project_id}/patent-points").json()["points"] == []
```

- [ ] **Step 2: Run test to verify endpoints fail**

Run:

```bash
python3 -m pytest tests/test_patent_points.py::test_project_patent_point_crud_and_selection -q
```

Expected: FAIL with HTTP 404 for `/api/projects/{project_id}/patent-points`.

- [ ] **Step 3: Add SQLite table and CRUD methods**

In `backend/app/storage.py`, import `PatentPointCandidate` and add this table to `_migrate()`:

```sql
create table if not exists project_patent_points (
    id text primary key,
    project_id text not null,
    candidate_json text not null,
    selected integer not null default 0,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    foreign key(project_id) references projects(id)
);
```

Add these methods to `SQLiteStore`:

```python
    def add_project_patent_point(self, project_id: str, point: PatentPointCandidate) -> PatentPointCandidate:
        with self.connection:
            if point.selected:
                self.connection.execute("update project_patent_points set selected = 0 where project_id = ?", (project_id,))
            self.connection.execute(
                """
                insert or replace into project_patent_points(id, project_id, candidate_json, selected, updated_at)
                values (?, ?, ?, ?, current_timestamp)
                """,
                (
                    point.id,
                    project_id,
                    json.dumps(point.model_dump(mode="json"), ensure_ascii=False),
                    1 if point.selected else 0,
                ),
            )
        return point

    def list_project_patent_points(self, project_id: str) -> list[PatentPointCandidate]:
        rows = self.connection.execute(
            "select * from project_patent_points where project_id = ? order by selected desc, updated_at desc",
            (project_id,),
        ).fetchall()
        points: list[PatentPointCandidate] = []
        for row in rows:
            point = PatentPointCandidate(**json.loads(row["candidate_json"]))
            points.append(point.model_copy(update={"selected": bool(row["selected"])}))
        return points

    def get_project_patent_point(self, project_id: str, point_id: str) -> PatentPointCandidate | None:
        row = self.connection.execute(
            "select * from project_patent_points where project_id = ? and id = ?",
            (project_id, point_id),
        ).fetchone()
        if not row:
            return None
        point = PatentPointCandidate(**json.loads(row["candidate_json"]))
        return point.model_copy(update={"selected": bool(row["selected"])})

    def delete_project_patent_point(self, project_id: str, point_id: str) -> bool:
        with self.connection:
            cursor = self.connection.execute(
                "delete from project_patent_points where project_id = ? and id = ?",
                (project_id, point_id),
            )
        return cursor.rowcount > 0
```

- [ ] **Step 4: Add FastAPI endpoints**

In `backend/app/main.py`, import `PatentPointCandidate`, `PatentPointCreate`, and `PatentPointUpdate`.

Add endpoints after `list_project_materials`:

```python
    @app.get("/api/projects/{project_id}/patent-points")
    def list_project_patent_points(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"points": [point.model_dump(mode="json") for point in store.list_project_patent_points(project_id)]}

    @app.post("/api/projects/{project_id}/patent-points")
    def create_project_patent_point(project_id: str, payload: PatentPointCreate) -> dict:
        _require_project(store, project_id)
        point = payload.to_candidate(f"user-{uuid.uuid4().hex}")
        stored = store.add_project_patent_point(project_id, point)
        return stored.model_dump(mode="json")

    @app.patch("/api/projects/{project_id}/patent-points/{point_id}")
    def update_project_patent_point(project_id: str, point_id: str, payload: PatentPointUpdate) -> dict:
        _require_project(store, project_id)
        existing = store.get_project_patent_point(project_id, point_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Patent point not found.")
        patch = payload.model_dump(exclude_unset=True)
        if patch.get("evidence_status") in {"feasible_unverified", "needs_experiment"} and not patch.get("support_gaps") and not existing.support_gaps:
            patch["support_gaps"] = ["提交前需补充实验或工程样例。"]
        updated = existing.model_copy(update=patch)
        stored = store.add_project_patent_point(project_id, updated)
        return stored.model_dump(mode="json")

    @app.delete("/api/projects/{project_id}/patent-points/{point_id}")
    def delete_project_patent_point(project_id: str, point_id: str) -> dict:
        _require_project(store, project_id)
        deleted = store.delete_project_patent_point(project_id, point_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Patent point not found.")
        return {"ok": True}
```

- [ ] **Step 5: Run focused API test**

Run:

```bash
python3 -m pytest tests/test_patent_points.py::test_project_patent_point_crud_and_selection -q
```

Expected: `1 passed`.

- [ ] **Step 6: Run storage-adjacent regression tests**

Run:

```bash
python3 -m pytest tests/test_patent_points.py tests/test_api.py tests/test_disclosure.py -q
```

Expected: all selected tests pass with no network calls.

- [ ] **Step 7: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/storage.py backend/app/main.py tests/test_patent_points.py && git commit -m "feat: persist project patent points" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 4: Merge User Patent Points Into Disclosure Generation

**Files:**
- Modify: `backend/app/disclosure/generator.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_disclosure.py`
- Modify: `tests/test_patent_points.py`

- [ ] **Step 1: Add failing disclosure merge test**

Append to `tests/test_patent_points.py`:

```python
from backend.app.disclosure.prior_art import StaticPriorArtProvider


def test_user_patent_point_is_preserved_in_disclosure_generation(tmp_path):
    llm = FakeLLMClient(
        {
            "disclosure_scan": '{"summary":"外立面逆建模项目","materials_summary":"材料覆盖点云和图像","technical_keywords":["点云","图像"],"implementation_gaps":[]}',
            "patent_points": '{"candidates":[{"id":"p-model","title":"模型生成点","technical_problem":"人工建模效率低","innovation":"自动生成构件","technical_solution":"采集点云并生成构件","beneficial_effects":["提高效率"],"protection_focus":["方法"],"grantability_score":0.7,"rationale":"结构完整"}],"selected_candidate_id":"p-model"}',
            "prior_art_terms": '["外立面 逆建模 遮挡"]',
            "prior_art_relevance": '{"prior_art_differences":"用户点区别在遮挡洞口补全。","hits":[]}',
            "disclosure_body": "# 技术交底书\n包含遮挡洞口语义补全作为可选实施例。",
            "disclosure_mermaid": "flowchart TD\nA[图像] --> B[补全]",
            "disclosure_image_prompt": "黑白线稿，展示遮挡洞口补全。",
            "disclosure_self_check": "[]",
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=llm,
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_id = client.post(
        "/api/projects",
        json={"name": "外立面逆建模", "draft_text": "一种既有建筑外立面逆建模方法。"},
    ).json()["id"]
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "遮挡洞口语义补全",
            "technical_problem": "遮挡导致洞口漏识别",
            "innovation": "多视角互证补全洞口",
            "technical_solution": "融合点云和图像补全洞口边界。",
            "evidence_status": "feasible_unverified",
            "source_type": "user",
            "selected": True,
        },
    )

    run = client.post(f"/api/projects/{project_id}/disclosures", json={"trace": False, "max_prior_art_results": 0}).json()

    titles = [item["title"] for item in run["package"]["candidates"]]
    assert titles[0] == "遮挡洞口语义补全"
    assert run["package"]["selected_candidate_id"].startswith("user-")
    assert run["package"]["candidates"][0]["support_gaps"] == ["提交前需补充实验或工程样例。"]
```

- [ ] **Step 2: Run test to verify user candidates are not injected**

Run:

```bash
python3 -m pytest tests/test_patent_points.py::test_user_patent_point_is_preserved_in_disclosure_generation -q
```

Expected: FAIL because the disclosure package contains only the model-generated candidate.

- [ ] **Step 3: Update disclosure generator signature**

Change `DisclosureGenerator.generate()` signature:

```python
    def generate(
        self,
        *,
        project: ProjectRecord,
        materials: list[ProjectMaterial],
        context_chunks: list[PatentChunk],
        max_prior_art_results: int,
        user_candidates: list[PatentPointCandidate] | None = None,
    ) -> tuple[DisclosurePackage, list[dict[str, Any]], list[str]]:
```

At the top of the method add:

```python
        user_candidates = user_candidates or []
        strategic_context = _format_user_candidates(user_candidates)
```

Pass `strategic_context` into `_points_prompt()` and `_terms_prompt()`.

- [ ] **Step 4: Merge candidates deterministically**

Add this helper to `backend/app/disclosure/generator.py`:

```python
def _merge_candidates(
    user_candidates: list[PatentPointCandidate],
    generated: list[PatentPointCandidate],
    generated_selected_id: str | None,
) -> tuple[list[PatentPointCandidate], str | None]:
    merged: list[PatentPointCandidate] = []
    seen: set[str] = set()
    for candidate in user_candidates:
        patched = candidate
        if candidate.evidence_status in {"feasible_unverified", "needs_experiment"} and not candidate.support_gaps:
            patched = candidate.model_copy(update={"support_gaps": ["提交前需补充实验或工程样例。"]})
        merged.append(patched)
        seen.add(patched.id)
    for candidate in generated:
        if candidate.id not in seen:
            merged.append(candidate)
            seen.add(candidate.id)
    selected_user = next((candidate for candidate in merged if candidate.selected), None)
    if selected_user:
        return merged, selected_user.id
    if generated_selected_id in seen:
        return merged, generated_selected_id
    return merged, merged[0].id if merged else None
```

After `_parse_candidates()` call:

```python
        generated_candidates, generated_selected_id = _parse_candidates(points_raw, project)
        candidates, selected_id = _merge_candidates(user_candidates, generated_candidates, generated_selected_id)
```

- [ ] **Step 5: Add user-candidate prompt context**

Add helper:

```python
def _format_user_candidates(candidates: list[PatentPointCandidate]) -> str:
    if not candidates:
        return "无用户指定专利点。"
    return json.dumps([candidate.model_dump(mode="json") for candidate in candidates], ensure_ascii=False, indent=2)
```

Change `_points_prompt()` to include:

```python
用户指定专利点：
{strategic_context}
```

Change prompt wording to:

```text
如果存在用户指定专利点，必须保留这些专利点，不得因为证据状态为 feasible_unverified 而删除；可以补充 support_gaps、experiment_needed 和 rationale。
```

- [ ] **Step 6: Pass saved candidates from API**

In `_execute_disclosure()` in `backend/app/main.py`, load and pass candidates:

```python
        user_candidates = store.list_project_patent_points(project.id)
        package, stage_results, warnings = generator.generate(
            project=project,
            materials=materials,
            context_chunks=context,
            max_prior_art_results=run.max_prior_art_results,
            user_candidates=user_candidates,
        )
```

- [ ] **Step 7: Run disclosure merge tests**

Run:

```bash
python3 -m pytest tests/test_patent_points.py::test_user_patent_point_is_preserved_in_disclosure_generation tests/test_disclosure.py::test_disclosure_generator_runs_pipeline_and_records_prior_art -q
```

Expected: `2 passed`.

- [ ] **Step 8: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/disclosure/generator.py backend/app/main.py tests/test_patent_points.py tests/test_disclosure.py && git commit -m "feat: inject user patent points into disclosures" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 5: Generate Claim Charts And Evidence-Aware Drafts

**Files:**
- Modify: `backend/app/disclosure/generator.py`
- Modify: `backend/app/generator.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_patent_points.py`
- Modify: `tests/test_disclosure.py`

- [ ] **Step 1: Add failing claim-chart test**

Append to `tests/test_patent_points.py`:

```python
def test_disclosure_adds_claim_chart_to_user_candidate(tmp_path):
    llm = FakeLLMClient(
        {
            "disclosure_scan": '{"summary":"外立面逆建模项目","materials_summary":"材料覆盖点云","technical_keywords":["点云"],"implementation_gaps":[]}',
            "patent_points": '{"candidates":[],"selected_candidate_id":""}',
            "prior_art_terms": '["外立面 逆建模"]',
            "prior_art_relevance": '{"prior_art_differences":"区别在遮挡洞口补全。","hits":[{"id":"h1","relevance_summary":"公开点云建模。","differentiators":["未公开遮挡洞口补全"]}],"claim_charts":[{"candidate_id":"user-fixed","prior_art_id":"h1","prior_art_title":"一种点云建模方法","overlapping_features":["点云建模"],"differentiating_features":["遮挡洞口补全"],"claim_drafting_advice":"将多视角互证补全写入从属权利要求。"}]}',
            "disclosure_body": "# 技术交底书\n遮挡洞口补全。",
            "disclosure_mermaid": "flowchart TD\nA[点云] --> B[补全]",
            "disclosure_image_prompt": "黑白线稿。",
            "disclosure_self_check": "[]",
        }
    )
    provider = StaticPriorArtProvider(
        hits=[
            PriorArtHit(
                id="h1",
                source="Google Patents",
                query="外立面 逆建模",
                title="一种点云建模方法",
                publication_number="CN000000001A",
                url="https://patents.google.com/patent/CN000000001A",
            )
        ]
    )
    generator = DisclosureGenerator(llm, provider)
    user_candidate = PatentPointCreate(
        title="遮挡洞口语义补全",
        technical_problem="遮挡导致洞口漏识别",
        innovation="多视角互证补全洞口",
        technical_solution="融合点云和图像补全洞口边界。",
        evidence_status="feasible_unverified",
        source_type="user",
        selected=True,
    ).to_candidate("user-fixed")

    package, _, _ = generator.generate(
        project=ProjectRecord(id="p1", name="外立面逆建模", draft_text="一种既有建筑外立面逆建模方法。"),
        materials=[],
        context_chunks=[],
        max_prior_art_results=8,
        user_candidates=[user_candidate],
    )

    assert package.candidates[0].claim_chart[0].differentiating_features == ["遮挡洞口补全"]
    assert package.candidates[0].claim_chart[0].claim_drafting_advice == "将多视角互证补全写入从属权利要求。"
```

- [ ] **Step 2: Run test to verify claim chart missing**

Run:

```bash
python3 -m pytest tests/test_patent_points.py::test_disclosure_adds_claim_chart_to_user_candidate -q
```

Expected: FAIL because `claim_chart` is empty.

- [ ] **Step 3: Parse claim charts from relevance payload**

In `_enrich_prior_art()` in `backend/app/disclosure/generator.py`, after `data = _json_object(raw, {})`, parse charts:

```python
        charts_by_candidate: dict[str, list[ClaimChartItem]] = {}
        for item in data.get("claim_charts", []):
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id") or "")
            if not candidate_id:
                continue
            chart = ClaimChartItem(
                prior_art_id=str(item.get("prior_art_id") or ""),
                prior_art_title=str(item.get("prior_art_title") or ""),
                overlapping_features=_string_list(item.get("overlapping_features")),
                differentiating_features=_string_list(item.get("differentiating_features")),
                claim_drafting_advice=str(item.get("claim_drafting_advice") or ""),
            )
            charts_by_candidate.setdefault(candidate_id, []).append(chart)
```

Import `ClaimChartItem`.

Change `_enrich_prior_art()` return type to:

```python
    ) -> tuple[list[PriorArtHit], str, dict[str, list[ClaimChartItem]]]:
```

Return `enriched, differences, charts_by_candidate`.

Patch candidates after enrichment:

```python
        prior_art_hits, prior_art_differences, charts_by_candidate = self._enrich_prior_art(project, candidates, selected_id, prior_art_hits)
        candidates = [
            candidate.model_copy(update={"claim_chart": charts_by_candidate.get(candidate.id, candidate.claim_chart)})
            for candidate in candidates
        ]
```

- [ ] **Step 4: Update relevance prompt schema**

Add `claim_charts` to `_relevance_prompt()` JSON schema:

```text
  "claim_charts": [
    {
      "candidate_id": "候选专利点id",
      "prior_art_id": "命中id",
      "prior_art_title": "现有技术标题",
      "overlapping_features": ["重合技术特征"],
      "differentiating_features": ["区别技术特征"],
      "claim_drafting_advice": "权利要求规避建议"
    }
  ]
```

- [ ] **Step 5: Add evidence-aware draft prompt assertions**

Append to `tests/test_patent_points.py`:

```python
def test_draft_generation_prompt_marks_unverified_schemes_as_optional(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种外立面逆建模方法。\n2. 根据权利要求1所述的方法，其中可选地进行遮挡洞口语义补全。",
            "description": "具体实施方式\n在可选实施例中，执行遮挡洞口语义补全。",
            "abstract": "本发明公开了一种外立面逆建模方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[点云] --> B[模型]",
            "image_prompt": "黑白线稿。",
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=llm,
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_id = client.post(
        "/api/projects",
        json={"name": "外立面逆建模", "draft_text": "一种既有建筑外立面逆建模方法。"},
    ).json()["id"]
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "遮挡洞口语义补全",
            "technical_problem": "遮挡导致洞口漏识别",
            "innovation": "多视角互证补全洞口",
            "technical_solution": "融合点云和图像补全洞口边界。",
            "evidence_status": "feasible_unverified",
            "source_type": "user",
            "selected": True,
        },
    )

    client.post(f"/api/projects/{project_id}/generate", json={})

    claims_prompt = next(call.user_prompt for call in llm.calls if call.stage == "claims")
    assert "feasible_unverified" in claims_prompt
    assert "不得写成已经完成验证的实施事实" in claims_prompt
```

- [ ] **Step 6: Inject selected user points into draft generation even without disclosure**

In `backend/app/main.py`, before `brief = _brief_from_draft(...)` in `generate_project()`:

```python
        user_candidates = store.list_project_patent_points(project_id)
        selected_user_candidates = [candidate for candidate in user_candidates if candidate.selected]
```

When no completed disclosure exists but selected user candidates exist, construct a lightweight `DisclosurePackage`:

```python
        if not disclosure_package and selected_user_candidates:
            selected_candidate = selected_user_candidates[0]
            disclosure_package = DisclosurePackage(
                title=selected_candidate.title,
                summary=f"用户指定护城河专利点：{selected_candidate.title}",
                materials_summary=selected_candidate.feasibility_basis,
                candidates=selected_user_candidates,
                selected_candidate_id=selected_candidate.id,
                prior_art_hits=[],
                prior_art_differences="尚未完成公开现有技术差异分析。",
                body_markdown=selected_candidate.technical_solution,
                mermaid="flowchart TD\nA[用户指定技术方案] --> B[待补充验证]",
                image_prompt="黑白线稿，展示用户指定技术方案的数据流和模块关系。",
                self_check_findings=[],
                generation_logs=["disclosure: synthesized from selected user patent point"],
            )
```

- [ ] **Step 7: Update draft prompts**

In `_claims_prompt()` and `_description_prompt()` in `backend/app/generator.py`, add this instruction under `要求：`:

```text
4. 对 evidence_status 为 feasible_unverified 或 needs_experiment 的方案，只能写成可选实施例、变形例、从属限定或待验证改进方向，不得写成已经完成验证的实施事实；
5. 对用户指定专利点，要保留其保护意图，并用 support_gaps 指明提交前需补强的实验或工程材料。
```

- [ ] **Step 8: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_patent_points.py::test_disclosure_adds_claim_chart_to_user_candidate tests/test_patent_points.py::test_draft_generation_prompt_marks_unverified_schemes_as_optional -q
```

Expected: `2 passed`.

- [ ] **Step 9: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/disclosure/generator.py backend/app/generator.py backend/app/main.py tests/test_patent_points.py && git commit -m "feat: add claim charts and evidence-aware drafting" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 6: Add Frontend Patent Moat Workspace

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/domain.test.ts`

- [ ] **Step 1: Add frontend API methods**

In `frontend/src/api.ts`, add:

```ts
export interface PatentPointCreatePayload {
  title: string;
  technical_problem: string;
  innovation: string;
  technical_solution: string;
  beneficial_effects: string[];
  protection_focus: string[];
  evidence_status: EvidenceStatus;
  source_type: PatentPointSourceType;
  feasibility_basis: string;
  support_gaps: string[];
  experiment_needed: string[];
  moat_scores: MoatScores;
  selected: boolean;
  rationale: string;
}

export async function listProjectPatentPoints(projectId: string): Promise<PatentPointCandidate[]> {
  const data = await request<{ points: PatentPointCandidate[] }>(`/api/projects/${projectId}/patent-points`);
  return data.points;
}

export async function createProjectPatentPoint(projectId: string, payload: PatentPointCreatePayload): Promise<PatentPointCandidate> {
  return request<PatentPointCandidate>(`/api/projects/${projectId}/patent-points`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateProjectPatentPoint(
  projectId: string,
  pointId: string,
  payload: Partial<PatentPointCreatePayload>,
): Promise<PatentPointCandidate> {
  return request<PatentPointCandidate>(`/api/projects/${projectId}/patent-points/${pointId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteProjectPatentPoint(projectId: string, pointId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/patent-points/${pointId}`, { method: "DELETE" });
}
```

- [ ] **Step 2: Wire state and loading in App**

In `frontend/src/App.tsx`, import the new API methods and helpers. Add state:

```ts
  const [patentPoints, setPatentPoints] = useState<PatentPointCandidate[]>([]);
```

Add loader:

```ts
  async function loadPatentPoints(projectId: string) {
    try {
      setPatentPoints(await listProjectPatentPoints(projectId));
    } catch {
      setPatentPoints([]);
    }
  }
```

In the project-selection `useEffect`, call `loadPatentPoints(selectedProject.id)` and clear points when no project is selected.

- [ ] **Step 3: Add create/select/delete handlers**

Add these handlers in `App()`:

```ts
  async function handleCreatePatentPoint(payload: PatentPointCreatePayload) {
    if (!selectedProject) return;
    await withStatus("patent-point-create", async () => {
      await createProjectPatentPoint(selectedProject.id, payload);
      setPatentPoints(await listProjectPatentPoints(selectedProject.id));
      setMessage("已加入护城河专利点");
    });
  }

  async function handleSelectPatentPoint(point: PatentPointCandidate) {
    if (!selectedProject) return;
    await withStatus("patent-point-select", async () => {
      await updateProjectPatentPoint(selectedProject.id, point.id, { selected: true });
      setPatentPoints(await listProjectPatentPoints(selectedProject.id));
      setMessage(`已选择专利点：${point.title}`);
    });
  }

  async function handleDeletePatentPoint(point: PatentPointCandidate) {
    if (!selectedProject) return;
    await withStatus("patent-point-delete", async () => {
      await deleteProjectPatentPoint(selectedProject.id, point.id);
      setPatentPoints(await listProjectPatentPoints(selectedProject.id));
      setMessage(`已删除专利点：${point.title}`);
    });
  }
```

- [ ] **Step 4: Add MoatView component**

Add a compact component in `frontend/src/App.tsx`:

```tsx
function MoatView({
  project,
  points,
  busy,
  onCreate,
  onSelect,
  onDelete,
}: {
  project: ProjectRecord | null;
  points: PatentPointCandidate[];
  busy: string;
  onCreate: (payload: PatentPointCreatePayload) => void;
  onSelect: (point: PatentPointCandidate) => void;
  onDelete: (point: PatentPointCandidate) => void;
}) {
  const [form, setForm] = useState<PatentPointCreatePayload>({
    title: "",
    technical_problem: "",
    innovation: "",
    technical_solution: "",
    beneficial_effects: [],
    protection_focus: ["方法", "系统", "介质"],
    evidence_status: "feasible_unverified",
    source_type: "user",
    feasibility_basis: "",
    support_gaps: [],
    experiment_needed: [],
    moat_scores: {
      scope_width: 0.6,
      designaround_difficulty: 0.6,
      feasibility: 0.5,
      support_strength: 0.2,
      prior_art_distance: 0.4,
      strategic_value: 0.7,
    },
    selected: true,
    rationale: "",
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!form.title.trim() || !form.technical_solution.trim()) return;
    onCreate({
      ...form,
      beneficial_effects: splitLines(form.beneficial_effects.join("\n")),
      protection_focus: splitLines(form.protection_focus.join("\n")),
      support_gaps: splitLines(form.support_gaps.join("\n")),
      experiment_needed: splitLines(form.experiment_needed.join("\n")),
    });
    setForm((current) => ({ ...current, title: "", technical_problem: "", innovation: "", technical_solution: "", feasibility_basis: "" }));
  }

  return (
    <div className="two-column">
      <section className="panel">
        <h3>新增专利点</h3>
        <form className="stack" onSubmit={submit}>
          <label><span>名称</span><input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} disabled={!project} /></label>
          <label><span>技术问题</span><textarea className="small-textarea" value={form.technical_problem} onChange={(event) => setForm({ ...form, technical_problem: event.target.value })} disabled={!project} /></label>
          <label><span>创新点</span><textarea className="small-textarea" value={form.innovation} onChange={(event) => setForm({ ...form, innovation: event.target.value })} disabled={!project} /></label>
          <label><span>技术方案</span><textarea className="draft-input" value={form.technical_solution} onChange={(event) => setForm({ ...form, technical_solution: event.target.value })} disabled={!project} /></label>
          <label><span>可行依据</span><textarea className="small-textarea" value={form.feasibility_basis} onChange={(event) => setForm({ ...form, feasibility_basis: event.target.value })} disabled={!project} /></label>
          <label>
            <span>证据状态</span>
            <select value={form.evidence_status} onChange={(event) => setForm({ ...form, evidence_status: event.target.value as EvidenceStatus })} disabled={!project}>
              <option value="feasible_unverified">可行未验证</option>
              <option value="needs_experiment">需实验</option>
              <option value="verified">已验证</option>
            </select>
          </label>
          <button className="primary" disabled={!project || busy === "patent-point-create"} type="submit">
            <ShieldCheck size={17} />
            <span>加入护城河</span>
          </button>
        </form>
      </section>
      <section className="panel">
        <h3>专利点地图</h3>
        <div className="list">
          {points.map((point) => (
            <article className={point.selected ? "result-item selected-point" : "result-item"} key={point.id}>
              <div className="result-meta">
                <span>{evidenceStatusLabel(point.evidence_status)}</span>
                <span>{sourceTypeLabel(point.source_type)}</span>
                <span>护城河 {moatScoreTotal(point.moat_scores).toFixed(3)}</span>
              </div>
              <strong>{point.title}</strong>
              <p>{point.innovation}</p>
              <p>{point.support_gaps.join("；") || "无显式支撑缺口。"}</p>
              <div className="button-row">
                <button className="icon-button" type="button" onClick={() => onSelect(point)} disabled={point.selected}>选择</button>
                <button className="icon-button ghost" type="button" onClick={() => onDelete(point)}>删除</button>
              </div>
            </article>
          ))}
          {points.length === 0 && <p className="empty">暂无用户指定专利点。</p>}
        </div>
      </section>
    </div>
  );
}

function splitLines(value: string): string[] {
  return value.split(/\n|；|;/).map((item) => item.trim()).filter(Boolean);
}
```

- [ ] **Step 5: Render new workspace**

In `App()` render switch, add:

```tsx
        {activeTab === "moat" && (
          <MoatView
            project={selectedProject}
            points={patentPoints}
            busy={busy}
            onCreate={handleCreatePatentPoint}
            onSelect={handleSelectPatentPoint}
            onDelete={handleDeletePatentPoint}
          />
        )}
```

- [ ] **Step 6: Add CSS**

Add to `frontend/src/styles.css`:

```css
.selected-point {
  border-color: #2563eb;
  background: #eff6ff;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.claim-chart {
  display: grid;
  gap: 10px;
}
```

- [ ] **Step 7: Build frontend**

Run:

```bash
cd frontend && npm test -- --run && npm run build
```

Expected: Vitest passes and Vite build completes.

- [ ] **Step 8: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add frontend/src/api.ts frontend/src/App.tsx frontend/src/styles.css frontend/src/domain.ts frontend/src/domain.test.ts && git commit -m "feat: add patent moat workspace" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 7: Export And Document The Patent Moat Workflow

**Files:**
- Modify: `backend/app/disclosure/exporter.py`
- Modify: `backend/app/exporter.py`
- Modify: `README.md`
- Modify: `tests/test_disclosure.py`
- Modify: `tests/test_export.py`

- [ ] **Step 1: Add export assertions**

In `tests/test_disclosure.py::test_disclosure_api_lifecycle_and_generation_injection`, after the Markdown export assertion, add:

```python
    assert "候选专利点" in export_response.text
    assert "证据状态" in export_response.text
```

In `tests/test_export.py`, add a `DraftPackage` with `patent_point_summary="遮挡洞口语义补全"` and assert Markdown contains `推荐专利点`.

- [ ] **Step 2: Run tests to verify metadata missing**

Run:

```bash
python3 -m pytest tests/test_disclosure.py::test_disclosure_api_lifecycle_and_generation_injection tests/test_export.py -q
```

Expected: FAIL on missing `证据状态` or `推荐专利点` text.

- [ ] **Step 3: Update disclosure Markdown export**

In `backend/app/disclosure/exporter.py`, change candidate rendering to include evidence fields:

```python
    candidates = "\n".join(
        "\n".join(
            [
                f"- {candidate.id} {candidate.title}：{candidate.innovation}",
                f"  - 证据状态：{candidate.evidence_status}",
                f"  - 来源：{candidate.source_type}",
                f"  - 可行依据：{candidate.feasibility_basis or '未填写'}",
                f"  - 支撑缺口：{'；'.join(candidate.support_gaps) or '无显式缺口'}",
                f"  - 护城河评分：{candidate.moat_scores.weighted_total}",
            ]
        )
        for candidate in package.candidates
    )
```

Render claim charts:

```python
    claim_charts = "\n".join(
        f"- {candidate.title} / {chart.prior_art_title}: 区别点 {'；'.join(chart.differentiating_features)}；建议 {chart.claim_drafting_advice}"
        for candidate in package.candidates
        for chart in candidate.claim_chart
    )
```

Add a `## Claim Chart` section in Markdown output with `claim_charts or "暂无。"` .

- [ ] **Step 4: Update DOCX export**

In `export_disclosure_docx()`, add a section:

```python
    _add_section(
        doc,
        "护城河与证据状态",
        "\n".join(
            f"{item.id}. {item.title}\n证据状态：{item.evidence_status}\n来源：{item.source_type}\n支撑缺口：{'；'.join(item.support_gaps) or '无显式缺口'}"
            for item in package.candidates
        ),
    )
```

- [ ] **Step 5: Update final draft Markdown export**

In `backend/app/exporter.py`, add `patent_point_summary` and `disclosure_summary` sections to `package_to_markdown()`:

```python
## 推荐专利点

{package.patent_point_summary or "未注入前置专利点。"}

## 前置交底摘要

{package.disclosure_summary or "未注入前置交底书。"}
```

- [ ] **Step 6: Update README**

Add a section after "功能":

```markdown
## 专利护城河工作流

本版本允许用户把“未验证但可行”的技术方案加入护城河地图。系统不会把这类方案伪装成已验证实施例，而是记录证据状态、可行依据、支撑缺口、建议实验、现有技术差异和权利要求撰写建议。

推荐流程：

1. 在“创建专利项目”输入基础技术交底。
2. 在“护城河地图”加入用户判断有战略价值的专利点。
3. 对每个专利点标注 `已验证`、`可行未验证` 或 `需实验`。
4. 运行“前置材料”生成交底书和现有技术差异。
5. 运行“分步撰写”生成申请文本；未验证方案只进入可选实施例、变形例、从属限定或待验证改进方向。
6. 导出 DOCX/Markdown 后交给代理人或律师复核。
```

- [ ] **Step 7: Run export and docs-adjacent tests**

Run:

```bash
python3 -m pytest tests/test_disclosure.py tests/test_export.py -q
```

Expected: tests pass.

- [ ] **Step 8: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/disclosure/exporter.py backend/app/exporter.py README.md tests/test_disclosure.py tests/test_export.py && git commit -m "docs: document patent moat workflow" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 8: Full Verification And Manual Smoke

**Files:**
- No code changes unless verification exposes a defect.

- [ ] **Step 1: Run backend tests with `.env` isolation**

Run:

```bash
DEEPSEEK_API_KEY= python3 -m pytest -q
```

Expected: all tests pass without making network calls.

- [ ] **Step 2: Run frontend tests and build**

Run:

```bash
cd frontend && npm test -- --run && npm run build
```

Expected: Vitest passes and Vite build succeeds.

- [ ] **Step 3: Start backend**

Run:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Expected: backend starts and `GET http://127.0.0.1:8000/api/health` returns `{"ok": true, ...}`.

- [ ] **Step 4: Start frontend**

Run in `frontend/`:

```bash
npm run dev -- --port 5174
```

Expected: frontend starts at `http://127.0.0.1:5174`.

- [ ] **Step 5: Browser smoke path**

Open `http://127.0.0.1:5174` and verify:

1. Sidebar contains `护城河地图` after `创建专利项目`.
2. Create a project named `外立面逆建模`.
3. Open `护城河地图`.
4. Add point `遮挡洞口语义补全` with evidence status `可行未验证`.
5. Confirm the point appears selected and shows a support-gap warning.
6. Open `前置材料` and run disclosure generation if the local LLM key is configured.
7. Open `分步撰写`; if no disclosure was completed, generation still injects the selected user point as a lightweight pre-filing package.
8. Export Markdown and confirm it contains `推荐专利点` and evidence status.

- [ ] **Step 6: Final checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git status --short || true
```

Expected in the current directory: `fatal: not a git repository` or an equivalent non-git response. Include this in the final execution summary.

---

## Self-Review

**Spec coverage:** The plan covers the product shift from drafting to patent moat building, user-entered feasible but unverified schemes, explicit evidence state, claim-chart style prior-art comparison, evidence-aware drafting, frontend workflow, export, documentation, and test isolation.

**Placeholder scan:** The plan contains no unresolved markers or vague implementation instructions. Each code-changing task includes exact files, concrete snippets, focused tests, and commands.

**Type consistency:** Backend and frontend use the same names: `evidence_status`, `source_type`, `feasibility_basis`, `support_gaps`, `experiment_needed`, `moat_scores`, `claim_chart`, and `selected`. API endpoints consistently use `/api/projects/{project_id}/patent-points`.

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-05-24-patent-moat-workbench.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.
