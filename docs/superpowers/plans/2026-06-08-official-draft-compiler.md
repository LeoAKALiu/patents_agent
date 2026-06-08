# Official Draft Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a formal filing draft compiler that isolates official patent text from internal notes, then routes post-draft review and official export through the compiled official package.

**Architecture:** Add a focused backend compiler module that converts `DraftPackage` into `OfficialDraftPackage`, persists `OfficialCompileRun`, and exposes compile/report APIs. Post-draft review will consume the latest completed official compile run and bind its decision to both the source draft hash and official package hash. The frontend guided flow gains a “正式稿编译” step between quality checks and post-draft review.

**Tech Stack:** Python 3, FastAPI, Pydantic, SQLite, pytest, TypeScript, React, Vitest, Vite.

---

## File Structure

- Create: `backend/app/official_compile.py`
  - Responsibility: hash helpers, official text sanitization, contamination classification, `OfficialDraftCompiler`, Markdown report rendering, official Markdown/DOCX export helpers for `OfficialDraftPackage`.
- Create: `tests/test_official_compile.py`
  - Responsibility: backend unit/API/gate tests for compile runs, contamination removal, blocked compile, post-draft review gate, and official export source.
- Modify: `backend/app/schemas.py`
  - Add `OfficialFigurePlanItem`, `OfficialDraftPackage`, `OfficialCompileRun`, `OfficialCompileRunCreate`.
  - Add `official_compile_run_id` and `official_package_hash` to `PostDraftReviewRun`.
- Modify: `backend/app/storage.py`
  - Add `official_compile_runs` table and CRUD methods.
  - Delete compile runs on project deletion.
  - Persist the new post-draft review hash fields.
- Modify: `backend/app/main.py`
  - Add official compile endpoints.
  - Require completed official compile before post-draft review.
  - Route official export through `OfficialDraftPackage`.
- Modify: `backend/app/post_draft_review.py`
  - Review `OfficialDraftPackage` instead of raw `DraftPackage`.
  - Persist both source draft hash and official package hash.
- Modify: `frontend/src/api.ts`
  - Add official compile types and API methods.
  - Add `official_package_hash` and `official_compile_run_id` to `PostDraftReviewRun`.
- Modify: `frontend/src/guidedFlow.ts`
  - Add `officialCompile` guided step and flow state gates.
- Modify: `frontend/src/guidedFlow.test.ts`
  - Add flow tests for compile required, blocked compile, completed compile, and passed post-review.
- Modify: `frontend/src/App.tsx`
  - Load compile runs, start compile, pass compile state into guided view and expert export.
- Modify: `frontend/src/GuidedPatentFlow.tsx`
  - Add the official compile panel and update post-draft review/export panels to show official package hash.

---

### Task 1: Backend Models and Compiler Core

**Files:**
- Create: `backend/app/official_compile.py`
- Modify: `backend/app/schemas.py`
- Test: `tests/test_official_compile.py`

- [ ] **Step 1: Write failing compiler unit tests**

Create `tests/test_official_compile.py` with:

```python
from backend.app.official_compile import (
    OfficialDraftCompiler,
    official_package_to_markdown,
)
from backend.app.schemas import DraftPackage


def test_compiler_removes_internal_pollution_from_official_package():
    package = _draft_package(
        claims="好的，下面撰写权利要求书。\n1. 一种方法。\n\n撰写说明与支撑不足提示 support_gap: 需要补矩阵。",
        description=(
            "## 说明书\n"
            "本发明涉及无人机采集。\n"
            "```mermaid\nflowchart TD\nA-->B\n```\n"
            "generation_logs: claims generated\n"
            "根据会审策略补充。"
        ),
        drawing_description="图1为方法流程图。\nimage_prompt: 黑白线稿。",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "completed"
    assert run.official_package is not None
    official_text = official_package_to_markdown(run.official_package)
    assert "好的" not in official_text
    assert "support_gap" not in official_text
    assert "```" not in official_text
    assert "flowchart TD" not in official_text
    assert "generation_logs" not in official_text
    assert "image_prompt" not in official_text
    assert "根据会审策略" not in official_text
    assert any(item["pattern"] == "support_gap" for item in run.contamination_removed)


def test_compiler_blocks_cross_project_title_contamination():
    package = _draft_package(
        description="本说明书还包括：基于边缘端动态推理的无人机飞行中任务调整方法。"
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["category"] == "cross_project_contamination" for item in run.blocked_items)


def test_compiler_blocks_when_cleaning_empties_required_section():
    package = _draft_package(description="support_gap: 说明书待补充。")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["category"] == "empty_required_section" for item in run.blocked_items)


def _draft_package(**overrides) -> DraftPackage:
    data = {
        "title": "一种城市体检指标驱动无人机主动采集方法",
        "abstract": "本发明公开了一种无人机主动采集方法。",
        "claims": "1. 一种方法，包括生成无人机任务包。",
        "description": "本发明涉及无人机任务规划技术领域。",
        "drawing_description": "图1为方法流程图。",
        "mermaid": "flowchart TD",
        "image_prompt": "黑白线稿",
        "review_findings": [],
        "citations": [],
        "generation_logs": ["claims generated"],
    }
    data.update(overrides)
    return DraftPackage(**data)
```

- [ ] **Step 2: Run compiler tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_official_compile.py -q
```

Expected: FAIL because `backend.app.official_compile` does not exist.

- [ ] **Step 3: Add official compile schemas**

Modify `backend/app/schemas.py` after `DraftPackage`:

```python
class OfficialFigurePlanItem(BaseModel):
    figure_no: str
    title: str
    description: str
    referenced_sections: list[str] = Field(default_factory=list)


class OfficialDraftPackage(BaseModel):
    title: str
    abstract: str
    claims: str
    description: str
    drawing_description: str
    figure_plan: list[OfficialFigurePlanItem] = Field(default_factory=list)
    compile_warnings: list[str] = Field(default_factory=list)
    source_draft_hash: str = ""
    official_package_hash: str = ""


class OfficialCompileRunCreate(BaseModel):
    pass


class OfficialCompileRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(completed|blocked|failed)$")
    source_draft_hash: str = ""
    official_package_hash: str = ""
    official_package: OfficialDraftPackage | None = None
    contamination_removed: list[dict[str, str]] = Field(default_factory=list)
    blocked_items: list[dict[str, str]] = Field(default_factory=list)
    sidecar_notes: list[dict[str, str]] = Field(default_factory=list)
    logs: list[DeliberationLogEntry] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
```

Modify `PostDraftReviewRun`:

```python
class PostDraftReviewRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(queued|running|completed|failed)$")
    providers: list[str] = Field(default_factory=list)
    prompt_pack_version: str = "post-draft-review-v1"
    draft_package_hash: str = ""
    official_compile_run_id: str = ""
    official_package_hash: str = ""
    role_results: list[PostDraftReviewRoleResult] = Field(default_factory=list)
    chair_result: PostDraftReviewChairResult | None = None
    export_allowed: bool = False
    blocking_issues: list[str] = Field(default_factory=list)
    contamination_hits: list[str] = Field(default_factory=list)
    logs: list[DeliberationLogEntry] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
```

- [ ] **Step 4: Implement compiler module**

Create `backend/app/official_compile.py`:

```python
from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from docx import Document

from backend.app.schemas import (
    DeliberationLogEntry,
    DraftPackage,
    OfficialCompileRun,
    OfficialDraftPackage,
    OfficialFigurePlanItem,
)


SAFE_REMOVAL_PATTERNS = (
    ("ai_preface", r"好的[，,].{0,80}(?:撰写|继续|严格按照).{0,80}(?:\n|$)"),
    ("support_gap", r"(?is)(?:撰写说明与支撑不足提示|支持材料补强说明|support_gaps?|支撑不足提示)[^\n]*(?:\n|$)"),
    ("markdown_fence", r"(?is)```.*?```"),
    ("markdown_heading", r"(?m)^#{1,6}\s+"),
    ("mermaid", r"(?im)^\s*(flowchart|graph|sequenceDiagram)\b.*$"),
    ("internal_field", r"(?im)^\s*(image_prompt|prompt|diagram|generation_logs)\s*[:：].*$"),
    ("internal_trace", r"(根据会审策略|多\s*Agent\s*会审|主席汇总|deliberation|generation_logs)"),
    ("unfavorable_statement", r"(可能不具备创造性|禁止直接提交|存在充分公开风险)"),
)

CROSS_PROJECT_PATTERNS = (
    "基于边缘端动态推理的无人机飞行中任务调整方法",
)


def source_draft_hash(package: DraftPackage) -> str:
    return hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def official_package_hash(package: OfficialDraftPackage) -> str:
    payload = package.model_copy(update={"official_package_hash": ""}).model_dump_json()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class OfficialDraftCompiler:
    def compile(self, *, project_id: str, package: DraftPackage) -> OfficialCompileRun:
        run_id = uuid.uuid4().hex
        draft_hash = source_draft_hash(package)
        removed: list[dict[str, str]] = []
        blocked: list[dict[str, str]] = []
        sidecar_notes: list[dict[str, str]] = []
        logs = [
            DeliberationLogEntry(
                level="info",
                phase="official_compile",
                provider_id="compiler",
                message="official compile started",
                detail=f"source_draft_hash={draft_hash}",
            )
        ]

        fields = {
            "abstract": package.abstract,
            "claims": package.claims,
            "description": package.description,
            "drawing_description": package.drawing_description,
        }
        cleaned: dict[str, str] = {}
        for field, text in fields.items():
            if _contains_cross_project_contamination(text):
                blocked.append(
                    {
                        "category": "cross_project_contamination",
                        "field": field,
                        "message": "正式文本疑似串入其他专利标题或其他项目内容。",
                    }
                )
            next_text, field_removed, field_notes = _clean_official_text(field, text)
            cleaned[field] = next_text.strip()
            removed.extend(field_removed)
            sidecar_notes.extend(field_notes)

        for field in ("abstract", "claims", "description", "drawing_description"):
            if not cleaned[field]:
                blocked.append(
                    {
                        "category": "empty_required_section",
                        "field": field,
                        "message": f"{field} 清污后为空，不能形成正式稿。",
                    }
                )
        residual = _scan_residual_internal_text(cleaned)
        blocked.extend(residual)

        if blocked:
            logs.append(
                DeliberationLogEntry(
                    level="error",
                    phase="official_compile",
                    provider_id="compiler",
                    message="official compile blocked",
                    detail=f"blocked_items={len(blocked)}",
                    repair_suggestion="查看正式稿编译报告，修复阻断项后重新编译。",
                )
            )
            return OfficialCompileRun(
                id=run_id,
                project_id=project_id,
                status="blocked",
                source_draft_hash=draft_hash,
                contamination_removed=removed,
                blocked_items=blocked,
                sidecar_notes=sidecar_notes,
                logs=logs,
            )

        official = OfficialDraftPackage(
            title=_clean_title(package.title),
            abstract=cleaned["abstract"],
            claims=cleaned["claims"],
            description=cleaned["description"],
            drawing_description=cleaned["drawing_description"],
            figure_plan=_figure_plan(cleaned["drawing_description"]),
            compile_warnings=[],
            source_draft_hash=draft_hash,
        )
        final_hash = official_package_hash(official)
        official = official.model_copy(update={"official_package_hash": final_hash})
        logs.append(
            DeliberationLogEntry(
                level="info",
                phase="official_compile",
                provider_id="compiler",
                message="official compile completed",
                detail=f"official_package_hash={final_hash}",
            )
        )
        return OfficialCompileRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            source_draft_hash=draft_hash,
            official_package_hash=final_hash,
            official_package=official,
            contamination_removed=removed,
            blocked_items=[],
            sidecar_notes=sidecar_notes,
            logs=logs,
        )


def official_package_to_markdown(package: OfficialDraftPackage) -> str:
    return f"""# {package.title}

## 摘要
{package.abstract}

## 权利要求书
{package.claims}

## 说明书
{package.description}

## 附图说明
{package.drawing_description}
"""


def export_official_package_docx(package: OfficialDraftPackage, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_heading(package.title, level=0)
    for heading, text in [
        ("摘要", package.abstract),
        ("权利要求书", package.claims),
        ("说明书", package.description),
        ("附图说明", package.drawing_description),
    ]:
        doc.add_heading(heading, level=1)
        for paragraph in text.splitlines():
            if paragraph.strip():
                doc.add_paragraph(paragraph.strip())
    doc.save(output_path)
    return output_path


def official_compile_run_to_markdown(run: OfficialCompileRun) -> str:
    lines = [
        "# OFFICIAL_COMPILE_REPORT",
        "",
        f"- run_id: {run.id}",
        f"- project_id: {run.project_id}",
        f"- status: {run.status}",
        f"- source_draft_hash: {run.source_draft_hash}",
        f"- official_package_hash: {run.official_package_hash}",
        "",
        "## Contamination Removed",
    ]
    lines.extend(_item_lines(run.contamination_removed))
    lines.extend(["", "## Blocked Items"])
    lines.extend(_item_lines(run.blocked_items))
    lines.extend(["", "## Sidecar Notes"])
    lines.extend(_item_lines(run.sidecar_notes))
    lines.extend(["", "## Logs"])
    for log in run.logs:
        lines.append(f"- [{log.level}] {log.phase}/{log.provider_id}: {log.message} {log.detail}")
    return "\n".join(lines).rstrip() + "\n"


def _clean_official_text(field: str, text: str) -> tuple[str, list[dict[str, str]], list[dict[str, str]]]:
    cleaned = text or ""
    removed: list[dict[str, str]] = []
    sidecar_notes: list[dict[str, str]] = []
    for pattern_name, pattern in SAFE_REMOVAL_PATTERNS:
        matches = [match.group(0).strip() for match in re.finditer(pattern, cleaned)]
        if not matches:
            continue
        for match_text in matches:
            removed.append({"field": field, "pattern": pattern_name, "text": match_text[:240]})
            if "support" in pattern_name:
                sidecar_notes.append({"field": field, "category": "support_gap", "text": match_text[:500]})
        cleaned = re.sub(pattern, "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), removed, sidecar_notes


def _contains_cross_project_contamination(text: str) -> bool:
    return any(pattern in text for pattern in CROSS_PROJECT_PATTERNS)


def _scan_residual_internal_text(fields: dict[str, str]) -> list[dict[str, str]]:
    blocked: list[dict[str, str]] = []
    residual_patterns = ("support_gap", "support_gaps", "generation_logs", "image_prompt", "好的，下面")
    for field, text in fields.items():
        for pattern in residual_patterns:
            if pattern in text:
                blocked.append(
                    {
                        "category": "residual_internal_text",
                        "field": field,
                        "message": f"清污后仍残留内部文本：{pattern}",
                    }
                )
    return blocked


def _figure_plan(drawing_description: str) -> list[OfficialFigurePlanItem]:
    items: list[OfficialFigurePlanItem] = []
    for line in drawing_description.splitlines():
        match = re.match(r"\s*(图\d+)[为是](.+)", line.strip())
        if match:
            items.append(
                OfficialFigurePlanItem(
                    figure_no=match.group(1),
                    title=match.group(2).strip("。；; "),
                    description=line.strip(),
                    referenced_sections=["drawing_description"],
                )
            )
    return items


def _clean_title(title: str) -> str:
    return re.sub(r"[\r\n]+", " ", title).strip()


def _item_lines(items: list[dict[str, str]]) -> list[str]:
    if not items:
        return ["- 无"]
    return [f"- {item}" for item in items]
```

- [ ] **Step 5: Run compiler unit tests**

Run:

```bash
python3 -m pytest tests/test_official_compile.py::test_compiler_removes_internal_pollution_from_official_package tests/test_official_compile.py::test_compiler_blocks_cross_project_title_contamination tests/test_official_compile.py::test_compiler_blocks_when_cleaning_empties_required_section -q
```

Expected: PASS.

- [ ] **Step 6: Commit backend compiler core**

Run:

```bash
git add backend/app/schemas.py backend/app/official_compile.py tests/test_official_compile.py
git commit -m "feat: add official draft compiler core"
```

---

### Task 2: Persistence and Compile APIs

**Files:**
- Modify: `backend/app/storage.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_official_compile.py`

- [ ] **Step 1: Add failing storage and API tests**

Append to `tests/test_official_compile.py`:

```python
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.storage import SQLiteStore


def test_store_persists_official_compile_runs(tmp_path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    run = OfficialDraftCompiler().compile(project_id="p1", package=_draft_package())

    stored = store.create_official_compile_run(run)

    assert stored.id == run.id
    assert store.get_official_compile_run("p1", run.id).official_package_hash == run.official_package_hash
    assert store.list_official_compile_runs("p1")[0].id == run.id
    assert store.get_latest_completed_official_compile_run("p1").id == run.id


def test_official_compile_api_runs_lists_gets_and_exports_report(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())

    response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["official_package_hash"]
    assert run["official_package"]["claims"].startswith("1. 一种方法")

    list_response = client.get(f"/api/projects/{project_id}/official-compile-runs")
    assert list_response.status_code == 200
    assert list_response.json()["runs"][0]["id"] == run["id"]
    assert list_response.json()["current_source_draft_hash"] == run["source_draft_hash"]

    get_response = client.get(f"/api/projects/{project_id}/official-compile-runs/{run['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == run["id"]

    report_response = client.get(f"/api/projects/{project_id}/official-compile-runs/{run['id']}/report.md")
    assert report_response.status_code == 200
    assert "OFFICIAL_COMPILE_REPORT" in report_response.text


def _create_project_with_package(client: TestClient, package: DraftPackage) -> str:
    project_id = client.post(
        "/api/projects",
        json={"name": "正式稿编译测试", "draft_text": "一种城市体检指标驱动无人机采集方法。"},
    ).json()["id"]
    client.app.state.store.update_project_package(project_id, package)
    return project_id
```

- [ ] **Step 2: Run storage/API tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_official_compile.py::test_store_persists_official_compile_runs tests/test_official_compile.py::test_official_compile_api_runs_lists_gets_and_exports_report -q
```

Expected: FAIL because storage methods and API routes are missing.

- [ ] **Step 3: Add storage imports and delete cascade**

Modify `backend/app/storage.py` imports:

```python
    OfficialCompileRun,
    OfficialDraftPackage,
```

Add `"official_compile_runs"` to `delete_project` table list immediately after `"formula_runs"`.

- [ ] **Step 4: Add official compile storage methods**

Add to `SQLiteStore` after formula run methods:

```python
    def create_official_compile_run(self, run: OfficialCompileRun) -> OfficialCompileRun:
        with self.connection:
            self.connection.execute(
                """
                insert into official_compile_runs(
                    id, project_id, status, source_draft_hash, official_package_hash,
                    official_package_json, contamination_removed_json, blocked_items_json,
                    sidecar_notes_json, logs_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._official_compile_run_values(run),
            )
        return self.get_official_compile_run(run.project_id, run.id) or run

    def list_official_compile_runs(self, project_id: str) -> list[OfficialCompileRun]:
        rows = self.connection.execute(
            "select * from official_compile_runs where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._official_compile_run_from_row(row) for row in rows]

    def get_official_compile_run(self, project_id: str, run_id: str) -> OfficialCompileRun | None:
        row = self.connection.execute(
            "select * from official_compile_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._official_compile_run_from_row(row) if row else None

    def get_latest_completed_official_compile_run(self, project_id: str) -> OfficialCompileRun | None:
        row = self.connection.execute(
            """
            select * from official_compile_runs
            where project_id = ? and status = 'completed'
            order by updated_at desc, rowid desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return self._official_compile_run_from_row(row) if row else None
```

- [ ] **Step 5: Add table migration**

Add to `_migrate()` SQL script:

```sql
                create table if not exists official_compile_runs (
                    id text primary key,
                    project_id text not null,
                    status text not null,
                    source_draft_hash text not null,
                    official_package_hash text not null,
                    official_package_json text,
                    contamination_removed_json text not null,
                    blocked_items_json text not null,
                    sidecar_notes_json text not null,
                    logs_json text not null default '[]',
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );
```

- [ ] **Step 6: Add row serializers**

Add near `_formula_run_from_row`:

```python
    def _official_compile_run_values(self, run: OfficialCompileRun) -> tuple:
        return (
            run.id,
            run.project_id,
            run.status,
            run.source_draft_hash,
            run.official_package_hash,
            json.dumps(run.official_package.model_dump(mode="json"), ensure_ascii=False)
            if run.official_package
            else None,
            json.dumps(run.contamination_removed, ensure_ascii=False),
            json.dumps(run.blocked_items, ensure_ascii=False),
            json.dumps(run.sidecar_notes, ensure_ascii=False),
            json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
        )

    def _official_compile_run_from_row(self, row: sqlite3.Row) -> OfficialCompileRun:
        package_json: str | None = row["official_package_json"]
        run = OfficialCompileRun(
            id=row["id"],
            project_id=row["project_id"],
            status=row["status"],
            source_draft_hash=row["source_draft_hash"],
            official_package_hash=row["official_package_hash"],
            official_package=OfficialDraftPackage.model_validate(json.loads(package_json)) if package_json else None,
            contamination_removed=json.loads(row["contamination_removed_json"]),
            blocked_items=json.loads(row["blocked_items_json"]),
            sidecar_notes=json.loads(row["sidecar_notes_json"]),
            logs=json.loads(row["logs_json"]),
        )
        return run.model_copy(update={"created_at": row["created_at"], "updated_at": row["updated_at"]})
```

- [ ] **Step 7: Add API routes**

Modify `backend/app/main.py` imports:

```python
from backend.app.official_compile import (
    OfficialDraftCompiler,
    official_compile_run_to_markdown,
    source_draft_hash,
)
```

Import `OfficialCompileRunCreate`.

Add routes before post-draft review routes:

```python
    @app.post("/api/projects/{project_id}/official-compile-runs")
    def create_official_compile_run(project_id: str, payload: OfficialCompileRunCreate | None = None) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        run = OfficialDraftCompiler().compile(project_id=project_id, package=package)
        stored = store.create_official_compile_run(run)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/official-compile-runs")
    def list_official_compile_runs(project_id: str) -> dict:
        project = _require_project(store, project_id)
        current_hash = source_draft_hash(project.package) if project.package else ""
        return {
            "runs": [run.model_dump(mode="json") for run in store.list_official_compile_runs(project_id)],
            "current_source_draft_hash": current_hash,
        }

    @app.get("/api/projects/{project_id}/official-compile-runs/{run_id}")
    def get_official_compile_run(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_official_compile_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Official compile run not found.")
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/official-compile-runs/{run_id}/report.md")
    def export_official_compile_report(project_id: str, run_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        run = store.get_official_compile_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Official compile run not found.")
        return PlainTextResponse(official_compile_run_to_markdown(run), media_type="text/markdown; charset=utf-8")
```

- [ ] **Step 8: Run storage/API tests**

Run:

```bash
python3 -m pytest tests/test_official_compile.py::test_store_persists_official_compile_runs tests/test_official_compile.py::test_official_compile_api_runs_lists_gets_and_exports_report -q
```

Expected: PASS.

- [ ] **Step 9: Commit persistence and API**

Run:

```bash
git add backend/app/storage.py backend/app/main.py tests/test_official_compile.py
git commit -m "feat: add official compile api"
```

---

### Task 3: Route Post-Draft Review and Official Export Through Compiled Drafts

**Files:**
- Modify: `backend/app/post_draft_review.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/storage.py`
- Test: `tests/test_official_compile.py`
- Test: `tests/test_post_draft_review.py`
- Test: `tests/test_filing_readiness.py`

- [ ] **Step 1: Add failing gate tests**

Append to `tests/test_official_compile.py`:

```python
def test_post_draft_review_requires_completed_official_compile(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 409
    assert "Official draft compile is required" in response.json()["detail"]


def test_post_draft_review_records_official_package_hash_and_unlocks_export(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    compile_run = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert review_response.status_code == 200
    review = review_response.json()
    assert review["official_compile_run_id"] == compile_run["id"]
    assert review["official_package_hash"] == compile_run["official_package_hash"]
    assert review["draft_package_hash"] == compile_run["source_draft_hash"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 200
    assert "权利要求书" in export_response.text


def test_official_export_uses_compiled_package_not_raw_draft(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _draft_package(claims="好的，下面撰写。\n1. 一种方法，包括生成任务包。"),
    )
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 200
    assert "好的" not in response.text
    assert "1. 一种方法，包括生成任务包。" in response.text


def test_official_export_requires_recompile_when_draft_changes(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    client.app.state.store.update_project_package(project_id, _draft_package(abstract="修改后的摘要。"))

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 409
    assert "Official draft compile is required for the current draft" in response.json()["detail"]
```

Add `_review_llm` helper to `tests/test_official_compile.py`:

```python
from backend.app.llm import FakeLLMClient


def _review_llm(*, export_allowed: bool) -> FakeLLMClient:
    role_status = "passed" if export_allowed else "blocked"
    chair_status = "passed" if export_allowed else "blocked"
    blocking_issues = [] if export_allowed else ["正式稿存在阻断问题。"]
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": _role_json("claims_reviewer", role_status, blocking_issues),
            "post_draft_spec_cleaner": _role_json("spec_cleaner", role_status, blocking_issues),
            "post_draft_technical_hardness": _role_json("technical_hardness", role_status, blocking_issues),
            "post_draft_chair_synthesis": f"""
{{
  "status": "{chair_status}",
  "export_allowed": {str(export_allowed).lower()},
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": [],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": ["内部备忘。"],
  "next_actions": []
}}
""".replace("'", '"'),
        }
    )


def _role_json(role: str, status: str, blocking_issues: list[str]) -> str:
    return f"""
{{
  "role": "{role}",
  "status": "{status}",
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": ["内部备忘。"]
}}
""".replace("'", '"')
```

- [ ] **Step 2: Run gate tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_official_compile.py::test_post_draft_review_requires_completed_official_compile tests/test_official_compile.py::test_post_draft_review_records_official_package_hash_and_unlocks_export tests/test_official_compile.py::test_official_export_uses_compiled_package_not_raw_draft tests/test_official_compile.py::test_official_export_requires_recompile_when_draft_changes -q
```

Expected: FAIL because post-draft review still accepts raw drafts and official export still reads `DraftPackage`.

- [ ] **Step 3: Update post-draft review runner signature**

Modify `backend/app/post_draft_review.py` imports:

```python
from backend.app.schemas import (
    DeliberationLogEntry,
    OfficialDraftPackage,
    PostDraftReviewChairResult,
    PostDraftReviewRoleResult,
    PostDraftReviewRun,
)
```

Replace `draft_package_hash` with:

```python
def package_hash_for_review(package: OfficialDraftPackage) -> str:
    return package.official_package_hash or hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()
```

Change `run_post_draft_review` signature:

```python
def run_post_draft_review(
    *,
    project_id: str,
    package: OfficialDraftPackage,
    llm: LLMClient,
    providers: list[str],
    official_compile_run_id: str,
) -> PostDraftReviewRun:
```

Inside the function set:

```python
    package_hash = package_hash_for_review(package)
    source_hash = package.source_draft_hash
```

Return completed run with:

```python
            draft_package_hash=source_hash,
            official_compile_run_id=official_compile_run_id,
            official_package_hash=package_hash,
```

Return failed run with the same three fields.

Change `_role_prompt` and `_chair_prompt` parameter type to `OfficialDraftPackage`. Keep the field name in prompt text as “当前正式稿”.

- [ ] **Step 4: Persist new post-draft review fields**

Modify `backend/app/storage.py` post-draft review insert SQL to include:

```sql
official_compile_run_id, official_package_hash
```

Update `_post_draft_review_run_values` to include:

```python
            run.official_compile_run_id,
            run.official_package_hash,
```

Update `_post_draft_review_run_from_row`:

```python
            official_compile_run_id=row["official_compile_run_id"] if "official_compile_run_id" in row.keys() else "",
            official_package_hash=row["official_package_hash"] if "official_package_hash" in row.keys() else "",
```

Add `_ensure_column` calls in `_migrate()`:

```python
            self._ensure_column("post_draft_review_runs", "official_compile_run_id", "text not null default ''")
            self._ensure_column("post_draft_review_runs", "official_package_hash", "text not null default ''")
```

- [ ] **Step 5: Update post-draft review API to require compile run**

Modify `create_post_draft_review` in `backend/app/main.py`:

```python
        project = _require_project(store, project_id)
        _require_package(project)
        compile_run = _require_latest_completed_official_compile(store, project_id)
        if isinstance(app.state.llm, MissingLLMClient):
            raise HTTPException(status_code=503, detail="LLM is not configured for post-draft multi-agent review.")
        providers = list(payload.providers if payload and payload.providers else STRICT_DELIBERATION_PROVIDERS)
        run = run_post_draft_review(
            project_id=project_id,
            package=compile_run.official_package,
            llm=app.state.llm,
            providers=providers,
            official_compile_run_id=compile_run.id,
        )
```

Add helper:

```python
def _require_latest_completed_official_compile(store: SQLiteStore, project_id: str) -> OfficialCompileRun:
    run = store.get_latest_completed_official_compile_run(project_id)
    if not run or not run.official_package:
        raise HTTPException(status_code=409, detail="Official draft compile is required before post-draft review.")
    return run
```

- [ ] **Step 6: Update official export gate and source**

Modify `backend/app/main.py` official export routes:

```python
        project = _require_project(store, project_id)
        _require_package(project)
        compile_run = _require_official_export_gate(store, project_id, project.package)
        output_path = export_official_package_docx(
            compile_run.official_package,
            settings.data_dir / "exports" / f"{project.id}-official.docx",
        )
```

Markdown route:

```python
        project = _require_project(store, project_id)
        _require_package(project)
        compile_run = _require_official_export_gate(store, project_id, project.package)
        return PlainTextResponse(official_package_to_markdown(compile_run.official_package), media_type="text/markdown; charset=utf-8")
```

Replace `_require_post_draft_export_gate` with:

```python
def _require_official_export_gate(store: SQLiteStore, project_id: str, package: DraftPackage) -> OfficialCompileRun:
    current_source_hash = source_draft_hash(package)
    compile_run = store.get_latest_completed_official_compile_run(project_id)
    if not compile_run or not compile_run.official_package or compile_run.source_draft_hash != current_source_hash:
        raise HTTPException(
            status_code=409,
            detail="Official draft compile is required for the current draft before official export.",
        )
    reviews = store.list_post_draft_review_runs(project_id)
    matching_review = next(
        (
            run
            for run in reviews
            if run.status == "completed"
            and run.export_allowed
            and run.draft_package_hash == current_source_hash
            and run.official_package_hash == compile_run.official_package_hash
        ),
        None,
    )
    if not matching_review:
        raise HTTPException(
            status_code=409,
            detail="Post-draft multi-agent review is required for the current official draft before official export.",
        )
    return compile_run
```

Add imports from `backend.app.official_compile`:

```python
    export_official_package_docx,
    official_package_to_markdown,
```

- [ ] **Step 7: Update old tests to compile before review/export**

In `tests/test_post_draft_review.py`, before successful `post-draft-reviews` calls, insert:

```python
client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
```

In `tests/test_filing_readiness.py::test_filing_readiness_api_warning_allows_official_markdown_and_docx_export`, insert the compile call before post-draft review:

```python
compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
assert compile_response.status_code == 200
```

Update no-review official export assertions to expect the new compile detail when no compile exists:

```python
assert "Official draft compile is required" in official_md.json()["detail"]
```

- [ ] **Step 8: Run backend gate tests**

Run:

```bash
python3 -m pytest tests/test_official_compile.py tests/test_post_draft_review.py tests/test_filing_readiness.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit review/export routing**

Run:

```bash
git add backend/app/main.py backend/app/post_draft_review.py backend/app/storage.py tests/test_official_compile.py tests/test_post_draft_review.py tests/test_filing_readiness.py
git commit -m "feat: route official review through compiled drafts"
```

---

### Task 4: Frontend API and Guided Flow State

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/guidedFlow.ts`
- Modify: `frontend/src/guidedFlow.test.ts`

- [ ] **Step 1: Add failing guided flow tests**

Modify `frontend/src/guidedFlow.test.ts` imports to include `OfficialCompileRun`.

Add test fixtures:

```ts
const completedOfficialCompileRun: OfficialCompileRun = {
  id: "ocr1",
  project_id: "p1",
  status: "completed",
  source_draft_hash: "draft-hash",
  official_package_hash: "official-hash",
  official_package: {
    title: "一种外立面逆建模方法",
    abstract: "摘要",
    claims: "1. 一种方法。",
    description: "说明书",
    drawing_description: "图1为方法流程图。",
    figure_plan: [],
    compile_warnings: [],
    source_draft_hash: "draft-hash",
    official_package_hash: "official-hash",
  },
  contamination_removed: [],
  blocked_items: [],
  sidecar_notes: [],
  logs: [],
  created_at: "2026-06-08T00:00:00Z",
  updated_at: "2026-06-08T00:00:00Z",
};

const blockedOfficialCompileRun: OfficialCompileRun = {
  id: "ocr-blocked",
  project_id: "p1",
  status: "blocked",
  source_draft_hash: "draft-hash",
  official_package_hash: "",
  official_package: null,
  contamination_removed: [],
  blocked_items: [{ category: "cross_project_contamination", field: "description", message: "疑似他案串稿。" }],
  sidecar_notes: [],
  logs: [],
  created_at: "2026-06-08T00:00:00Z",
  updated_at: "2026-06-08T00:00:00Z",
};
```

Update `guidedStepLabels` expectations:

```ts
expect(guidedStepLabels).toEqual([
  "想法与材料",
  "发明点",
  "多 Agent 会审",
  "核心公式",
  "生成初稿",
  "质量检查",
  "正式稿编译",
  "成稿会审",
  "导出",
]);
```

Add tests:

```ts
it("requires official compile before post-draft review", () => {
  const state = deriveGuidedFlowState({
    project: packageProject(),
    materials: [processedMaterial],
    disclosures: [completedDisclosure],
    deliberations: [completedDeliberation],
    patentPoints: [],
    filingReports: [filingReport("warning")],
    worksheets: [worksheet],
    completionRuns: [completionRun],
    officialCompileRuns: [],
    postDraftReviews: [],
  });

  expect(state.currentStepId).toBe("officialCompile");
  expect(state.hasCompletedOfficialCompile).toBe(false);
  expect(state.exportReady).toBe(false);
});

it("does not advance when official compile is blocked", () => {
  const state = deriveGuidedFlowState({
    project: packageProject(),
    materials: [processedMaterial],
    disclosures: [completedDisclosure],
    deliberations: [completedDeliberation],
    patentPoints: [],
    filingReports: [filingReport("warning")],
    worksheets: [worksheet],
    completionRuns: [completionRun],
    officialCompileRuns: [blockedOfficialCompileRun],
    postDraftReviews: [],
  });

  expect(state.currentStepId).toBe("officialCompile");
  expect(state.hasCompletedOfficialCompile).toBe(false);
});

it("moves to post-draft review after completed official compile", () => {
  const state = deriveGuidedFlowState({
    project: packageProject(),
    materials: [processedMaterial],
    disclosures: [completedDisclosure],
    deliberations: [completedDeliberation],
    patentPoints: [],
    filingReports: [filingReport("warning")],
    worksheets: [worksheet],
    completionRuns: [completionRun],
    officialCompileRuns: [completedOfficialCompileRun],
    postDraftReviews: [],
  });

  expect(state.currentStepId).toBe("postReview");
  expect(state.hasCompletedOfficialCompile).toBe(true);
});
```

Add helper:

```ts
function packageProject(): ProjectRecord {
  return {
    id: "p1",
    name: "外立面逆建模",
    draft_text: "一种外立面逆建模方法。",
    package: {
      title: "一种外立面逆建模方法",
      abstract: "摘要",
      claims: "1. 一种方法。",
      description: "说明书",
      drawing_description: "图1为方法流程图。",
      mermaid: "flowchart TD",
      image_prompt: "黑白线稿",
      review_findings: [],
      citations: [],
      generation_logs: [],
    },
    created_at: "2026-06-07T00:00:00Z",
    updated_at: "2026-06-07T00:00:00Z",
  };
}
```

- [ ] **Step 2: Run guided flow tests to verify they fail**

Run:

```bash
npm test -- --run src/guidedFlow.test.ts
```

Expected: FAIL because `OfficialCompileRun` and the `officialCompile` step do not exist.

- [ ] **Step 3: Add frontend API types and functions**

Modify `frontend/src/api.ts`:

```ts
export interface OfficialFigurePlanItem {
  figure_no: string;
  title: string;
  description: string;
  referenced_sections: string[];
}

export interface OfficialDraftPackage {
  title: string;
  abstract: string;
  claims: string;
  description: string;
  drawing_description: string;
  figure_plan: OfficialFigurePlanItem[];
  compile_warnings: string[];
  source_draft_hash: string;
  official_package_hash: string;
}

export interface OfficialCompileRun {
  id: string;
  project_id: string;
  status: "completed" | "blocked" | "failed";
  source_draft_hash: string;
  official_package_hash: string;
  official_package: OfficialDraftPackage | null;
  contamination_removed: Array<Record<string, string>>;
  blocked_items: Array<Record<string, string>>;
  sidecar_notes: Array<Record<string, string>>;
  logs: DeliberationLogEntry[];
  created_at: string;
  updated_at: string;
}
```

Extend `PostDraftReviewRun`:

```ts
  official_compile_run_id: string;
  official_package_hash: string;
```

Add API functions:

```ts
export async function startOfficialCompileRun(projectId: string): Promise<OfficialCompileRun> {
  return request<OfficialCompileRun>(`/api/projects/${projectId}/official-compile-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export async function listOfficialCompileRuns(
  projectId: string,
): Promise<{ runs: OfficialCompileRun[]; current_source_draft_hash: string }> {
  return request<{ runs: OfficialCompileRun[]; current_source_draft_hash: string }>(
    `/api/projects/${projectId}/official-compile-runs`,
  );
}

export function officialCompileReportUrl(projectId: string, runId: string): string {
  return `/api/projects/${projectId}/official-compile-runs/${runId}/report.md`;
}
```

- [ ] **Step 4: Update guided flow state**

Modify `frontend/src/guidedFlow.ts`:

```ts
export type GuidedStepId =
  | "idea"
  | "invention"
  | "deliberation"
  | "formula"
  | "draft"
  | "quality"
  | "officialCompile"
  | "postReview"
  | "export";
```

Add `OfficialCompileRun` import and `GuidedFlowInput` field:

```ts
  officialCompileRuns?: OfficialCompileRun[];
```

Add state field:

```ts
  hasCompletedOfficialCompile: boolean;
```

Insert step definition before postReview:

```ts
  { id: "officialCompile", label: "正式稿编译", description: "隔离内部痕迹，生成正式申请文本专用包。" },
```

Update derived state:

```ts
  const hasCompletedOfficialCompile = Boolean(
    input.officialCompileRuns?.some((run) => run.status === "completed" && run.official_package),
  );
```

Change transition after quality:

```ts
  } else if (!qualityChecked) {
    currentStepId = "quality";
  } else if (!hasCompletedOfficialCompile) {
    currentStepId = "officialCompile";
  } else if (!hasPassedPostDraftReview) {
    currentStepId = "postReview";
  } else {
    currentStepId = "export";
  }
```

Return `hasCompletedOfficialCompile`.

Add busy label and operation log:

```ts
  if (value === "official-compile") return "正在编译正式稿";
```

```ts
  if (value === "official-compile") {
    return [
      { at: 0, text: "读取当前草稿并计算源 draft hash" },
      { at: 4, text: "抽取摘要、权利要求书、说明书和附图说明" },
      { at: 9, text: "删除或隔离内部痕迹、support gaps 和绘图提示" },
      { at: 18, text: "检查正式章节完整性和疑似他案串稿" },
      { at: 30, text: "写入正式稿编译结果和报告" },
    ];
  }
```

- [ ] **Step 5: Run frontend flow tests**

Run:

```bash
npm test -- --run src/guidedFlow.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit frontend API and flow state**

Run:

```bash
git add frontend/src/api.ts frontend/src/guidedFlow.ts frontend/src/guidedFlow.test.ts
git commit -m "feat: add official compile flow state"
```

---

### Task 5: Frontend UI Wiring

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/GuidedPatentFlow.tsx`

- [ ] **Step 1: Add official compile state and loader in App**

Modify `frontend/src/App.tsx` imports:

```ts
  OfficialCompileRun,
  listOfficialCompileRuns,
  officialCompileReportUrl,
  startOfficialCompileRun,
```

Add state:

```ts
  const [officialCompileRuns, setOfficialCompileRuns] = useState<OfficialCompileRun[]>([]);
  const [currentSourceDraftHash, setCurrentSourceDraftHash] = useState("");
```

Add derived value:

```ts
  const latestOfficialCompileRun = officialCompileRuns[0] ?? null;
```

In selected project effect, load and clear compile runs:

```ts
      void loadOfficialCompileRuns(selectedProject.id);
```

```ts
      setOfficialCompileRuns([]);
      setCurrentSourceDraftHash("");
```

Add loader:

```ts
  async function loadOfficialCompileRuns(projectId: string): Promise<boolean> {
    try {
      const { runs, current_source_draft_hash } = await listOfficialCompileRuns(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setOfficialCompileRuns(runs);
      setCurrentSourceDraftHash(current_source_draft_hash);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setOfficialCompileRuns([]);
        setCurrentSourceDraftHash("");
      }
      return false;
    }
  }
```

After draft-changing operations call `loadOfficialCompileRuns(projectId)`:

```ts
      await loadOfficialCompileRuns(projectId);
```

Add handler:

```ts
  async function handleStartOfficialCompile() {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("official-compile", async () => {
      const run = await startOfficialCompileRun(projectId);
      const stillSelected = await loadOfficialCompileRuns(projectId);
      if (!stillSelected) return;
      setMessage(run.status === "completed" ? "正式稿编译完成" : `正式稿编译${run.status}`);
    });
  }
```

Pass props to `GuidedPatentFlowView`:

```tsx
            officialCompileRuns={officialCompileRuns}
            currentSourceDraftHash={currentSourceDraftHash}
            onStartOfficialCompile={() => void handleStartOfficialCompile()}
```

- [ ] **Step 2: Add GuidedPatentFlow props and panel**

Modify `frontend/src/GuidedPatentFlow.tsx` imports:

```ts
  officialCompileReportUrl,
  type OfficialCompileRun,
```

Extend props:

```ts
  officialCompileRuns: OfficialCompileRun[];
  currentSourceDraftHash: string;
  onStartOfficialCompile: () => void;
```

Pass compile runs into `deriveGuidedFlowState`.

Add latest compile:

```ts
  const latestOfficialCompileRun =
    props.officialCompileRuns.find((run) => run.source_draft_hash === props.currentSourceDraftHash) ?? null;
```

Render before postReview:

```tsx
      {state.currentStepId === "officialCompile" && (
        <OfficialCompilePanel
          project={props.project}
          run={latestOfficialCompileRun}
          runs={props.officialCompileRuns}
          currentSourceDraftHash={props.currentSourceDraftHash}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartOfficialCompile={props.onStartOfficialCompile}
        />
      )}
```

Create panel:

```tsx
function OfficialCompilePanel({
  project,
  run,
  runs,
  currentSourceDraftHash,
  busy,
  busyElapsedSeconds,
  onStartOfficialCompile,
}: {
  project: ProjectRecord | null;
  run: OfficialCompileRun | null;
  runs: OfficialCompileRun[];
  currentSourceDraftHash: string;
  busy: string;
  busyElapsedSeconds: number;
  onStartOfficialCompile: () => void;
}) {
  const completed = Boolean(run?.status === "completed" && run.official_package);
  const blocked = Boolean(run?.status === "blocked");
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>正式稿编译</h3>
          <p>隔离内部痕迹、support gaps、绘图提示和会审过程文本，生成正式申请文本专用包。</p>
        </div>
        <FileText size={24} />
      </div>
      <div className="result-meta">
        <span className={completed ? "status-badge" : blocked ? "status-badge danger" : "status-badge warn"}>
          {completed ? "已完成" : blocked ? "已阻断" : "等待编译"}
        </span>
        <span>源 hash：{currentSourceDraftHash ? currentSourceDraftHash.slice(0, 12) : "未生成"}</span>
      </div>
      <button
        className="primary"
        disabled={!project?.package || busy === "official-compile"}
        onClick={onStartOfficialCompile}
        type="button"
      >
        {busy === "official-compile" ? <Loader2 className="spin" size={17} /> : <FileText size={17} />}
        <span>{run ? "重新编译正式稿" : "编译正式稿"}</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "official-compile"} />
      {run && (
        <article className={completed ? "guided-choice selected" : "guided-choice"}>
          <div className="result-meta">
            <span className={completed ? "status-badge" : "status-badge danger"}>{run.status}</span>
            <span>official hash：{run.official_package_hash ? run.official_package_hash.slice(0, 12) : "未生成"}</span>
            {project && (
              <a href={officialCompileReportUrl(project.id, run.id)} rel="noreferrer" target="_blank">
                编译报告
              </a>
            )}
          </div>
          <h4>{completed ? "正式稿包已生成" : "正式稿编译被阻断"}</h4>
          <p>已移除污染项：{run.contamination_removed.length}</p>
          {run.blocked_items.length > 0 && (
            <p>阻断项：{run.blocked_items.map((item) => item.message || item.category).slice(0, 3).join("；")}</p>
          )}
        </article>
      )}
      {!run && runs.length > 0 && <p className="workflow-hint">已有正式稿编译记录，但未匹配当前源 draft hash。</p>}
    </section>
  );
}
```

- [ ] **Step 3: Update post-review and export panels to show official hash**

In `PostDraftReviewPanel`, add `officialCompileRun: OfficialCompileRun | null` prop and show:

```tsx
        <span>official hash：{officialCompileRun?.official_package_hash.slice(0, 12) ?? "未编译"}</span>
```

Change `officialAllowed` checks in export panels to require:

```ts
      && postDraftReview.official_package_hash === officialCompileRun?.official_package_hash
```

Use `latestOfficialCompileRun` in `ExportConfirmationPanel` props.

- [ ] **Step 4: Run frontend tests and build**

Run:

```bash
npm test
npm run build
```

Expected: PASS for both commands.

- [ ] **Step 5: Commit UI wiring**

Run:

```bash
git add frontend/src/App.tsx frontend/src/GuidedPatentFlow.tsx
git commit -m "feat: add official compile guided panel"
```

---

### Task 6: Regression, Text Cleanup, and Final Verification

**Files:**
- Modify only files needed by failing tests.

- [ ] **Step 1: Run backend full test suite**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS. If tests fail because old official export assumptions skipped compile runs, update those tests to create a completed official compile run before post-draft review and official export.

- [ ] **Step 2: Run frontend full test suite**

Run:

```bash
npm test
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 4: Run diff whitespace check**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 5: Search for obsolete warning-mode export language**

Run:

```bash
rg -n "高风险.*允许|不会阻止导出|warning-mode export|仍允许导出|直接读取 DraftPackage" backend frontend tests docs -g '*.{py,ts,tsx,md}'
```

Expected: no matches in current source files except historical plan/spec documents. If a current source file matches, update the wording to explain that formal export requires official compile plus post-draft review.

- [ ] **Step 6: Commit final cleanup if needed**

If Step 1 through Step 5 required code or test edits, run:

```bash
git add backend frontend tests
git commit -m "test: update official compile regressions"
```

If no edits were needed after the last task commit, do not create an empty commit.

- [ ] **Step 7: Final status**

Run:

```bash
git status --short
git log --oneline -5
```

Expected: clean working tree and recent commits for compiler core, compile API, review/export routing, flow state, and guided panel.

---

## Plan Self-Review

- Spec coverage:
  - `OfficialDraftPackage` and `OfficialCompileRun`: Task 1.
  - Compiler rules for safe deletion and blocking: Task 1.
  - Storage and APIs: Task 2.
  - Post-draft review uses compiled official package: Task 3.
  - Official export source and hash gate: Task 3.
  - Frontend guided step: Tasks 4 and 5.
  - Testing and regression commands: Task 6.
- Empty-marker scan:
  - This plan contains no deferred implementation language.
- Type consistency:
  - Backend uses `OfficialCompileRun`, `OfficialDraftPackage`, `source_draft_hash`, and `official_package_hash`.
  - Frontend mirrors those names exactly.
  - Existing `PostDraftReviewRun.draft_package_hash` remains the source draft hash, while `official_package_hash` binds the compiled official package.
