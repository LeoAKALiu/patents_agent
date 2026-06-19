# Post-Draft Review Annotated Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full annotated post-draft repair editor that merges the blocker workbench and current internal draft into one review-and-edit window with manual fixes and previewed AI fixes.

**Architecture:** Keep the already-built incremental repair workbench as the baseline. Add a backend repair-session layer that normalizes post-draft review findings into anchored issues, then add a frontend full-screen editor that consumes those anchors, edits the five draft sections, and later calls a hash-bound repair-patch API. AI changes are always proposed, previewed, safety-checked, and applied through the existing draft-package save path so old official drafts and old post-draft reviews become stale.

**Tech Stack:** FastAPI, Pydantic, project JSON store, React 19, TypeScript, Vite, Vitest, Playwright, pytest, Hermes Kanban.

---

## Base Rule For This PR Stack

The current incremental workbench changes must land first:

- `PUT /api/projects/{project_id}/draft-package`
- independent blocker scrolling
- large draft editor dialog
- per-issue `人工修正` / `一键AI修正` affordances
- tests in `tests/test_post_draft_review.py` and `frontend/src/PostDraftReviewPanel.test.tsx`

Do not dispatch PR-1 through PR-5 against a dirty worktree. Workers should use dedicated worktrees and branches after the baseline branch is reviewed and merged.

## File Map

- `backend/app/schemas.py`: add repair-session and repair-patch request/response models.
- `backend/app/post_draft_repair.py`: create pure issue normalization, section inference, snippet anchoring, and safe-patch validation helpers.
- `backend/app/main.py`: expose repair-session and repair-patch endpoints.
- `tests/test_post_draft_repair.py`: backend unit/API tests for issue anchors, stale hash checks, unsafe patch rejection, and apply behavior.
- `frontend/src/api.ts`: add repair-session and repair-patch API types/functions.
- `frontend/src/flow/postDraftRepairAnchors.ts`: frontend-only fallback helpers for grouping and displaying anchored issues.
- `frontend/src/flow/panels/PostDraftReviewPanel.tsx`: add entry point and pass current review/draft state into the editor.
- `frontend/src/flow/panels/PostDraftRepairEditor.tsx`: full-screen editor shell and state orchestration.
- `frontend/src/flow/panels/PostDraftIssueRail.tsx`: grouped issue navigation.
- `frontend/src/flow/panels/AnnotatedDraftSection.tsx`: editable draft section with anchor/highlight preview.
- `frontend/src/flow/panels/DraftRepairInspector.tsx`: selected issue details, manual/AI actions, patch preview.
- `frontend/src/PostDraftRepairEditor.test.tsx`: frontend interaction tests.
- `frontend/src/styles.css`: editor layout, responsive three-column-to-stacked behavior, safe fixed heights.
- `docs/superpowers/specs/2026-06-19-post-draft-review-annotated-editor-design.md`: source spec, update only if implementation intentionally changes scope.

## PR Split

### PR-0: Baseline Repair Workbench Review And Merge

**Owner:** Codex as reviewer/merger.

**Purpose:** Make the already-implemented incremental workbench the stable base for agent work.

**Acceptance:**

- [ ] Verify the baseline branch contains the current workbench implementation and no unrelated local files.
- [ ] Run `python3 -m pytest tests/test_post_draft_review.py -q`.
- [ ] Run `npm --prefix frontend test -- PostDraftReviewPanel.test.tsx`.
- [ ] Run `npm --prefix frontend run build`.
- [ ] Review browser smoke screenshots for desktop and mobile.
- [ ] Merge only after tests are green and unrelated dirty files are excluded.

### PR-1: Backend Repair Session And Issue Anchoring

**Owner:** `deepseekworker`

**Branch:** `codex/repair-editor-session-anchors`

**Depends On:** PR-0

**Files:**

- Create: `backend/app/post_draft_repair.py`
- Create: `tests/test_post_draft_repair.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing backend tests**

Add `tests/test_post_draft_repair.py` with these cases:

```python
from backend.app.post_draft_repair import (
    infer_target_section,
    locate_issue_anchor,
    normalize_post_draft_issues,
)


def test_infer_target_section_from_chinese_messages():
    assert infer_target_section("标题存在重复词汇方法方法") == "title"
    assert infer_target_section("权利要求6末尾残留内部审查备注") == "claims"
    assert infer_target_section("说明书有益效果使用颠覆") == "description"
    assert infer_target_section("附图说明中图1缺少说明") == "drawing_description"


def test_locate_issue_anchor_matches_snippet_in_section():
    sections = {
        "title": "一种基于城市体检指标置信度的无人机主动采集方法方法",
        "abstract": "",
        "claims": "1. 一种方法。\n*(注：内部备注)**",
        "description": "本发明颠覆了固定航线模式。",
        "drawing_description": "",
    }
    anchor = locate_issue_anchor(
        sections,
        target_section="claims",
        snippet="注：内部备注",
    )
    assert anchor["type"] == "text"
    assert anchor["section"] == "claims"
    assert anchor["start"] >= 0
    assert anchor["end"] > anchor["start"]


def test_normalize_post_draft_issues_falls_back_to_section_anchor():
    review = {
        "blocking_issues": ["说明书具体实施方式缺少后验更新公式"],
        "contamination_hits": [],
        "rewrite_suggestions": [],
    }
    sections = {
        "title": "",
        "abstract": "",
        "claims": "",
        "description": "具体实施方式。",
        "drawing_description": "",
    }
    issues = normalize_post_draft_issues(review, sections)
    assert len(issues) == 1
    assert issues[0]["kind"] == "blocking"
    assert issues[0]["target_section"] == "description"
    assert issues[0]["anchor"]["type"] == "section"
```

Run: `python3 -m pytest tests/test_post_draft_repair.py -q`

Expected: fail because `backend.app.post_draft_repair` does not exist.

- [ ] **Step 2: Add schema models**

Add these models to `backend/app/schemas.py`:

```python
class DraftIssueAnchor(BaseModel):
    type: Literal["text", "section", "missing"]
    section: Literal["title", "abstract", "claims", "description", "drawing_description", "unknown"]
    start: int | None = None
    end: int | None = None
    snippet: str | None = None


class DraftReviewIssue(BaseModel):
    id: str
    kind: Literal["blocking", "hit", "suggestion"]
    severity: Literal["critical", "high", "medium", "low"]
    source: str
    message: str
    snippet: str | None = None
    target_section: Literal["title", "abstract", "claims", "description", "drawing_description", "unknown"]
    anchor: DraftIssueAnchor
    status: Literal["open", "fixed", "skipped", "stale", "unanchored"] = "open"


class PostDraftRepairSession(BaseModel):
    project_id: str
    review_run_id: str
    draft_package_hash: str | None = None
    current_draft_hash: str | None = None
    stale: bool = False
    issues: list[DraftReviewIssue] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
```

- [ ] **Step 3: Implement pure repair helpers**

Create `backend/app/post_draft_repair.py` with:

```python
from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

SectionName = Literal["title", "abstract", "claims", "description", "drawing_description", "unknown"]

SECTION_KEYWORDS: list[tuple[SectionName, tuple[str, ...]]] = [
    ("title", ("标题", "方法方法")),
    ("abstract", ("摘要",)),
    ("claims", ("权利要求", "权利要求书", "claim")),
    ("description", ("说明书", "具体实施方式", "有益效果", "背景技术")),
    ("drawing_description", ("附图说明", "图1", "图2", "图3")),
]

CONTAMINATION_TERMS = (
    "好的，根据",
    "注：",
    "待验证",
    "补充实施方式",
    "主席修订",
    "主席补充",
    "需补充",
    "提交前补充",
)


def infer_target_section(message: str | None) -> SectionName:
    text = message or ""
    for section, keywords in SECTION_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return section
    return "unknown"


def _clean_snippet(snippet: str | None) -> str | None:
    if not snippet:
        return None
    value = re.sub(r"\s+", " ", snippet).strip()
    return value or None


def locate_issue_anchor(
    sections: dict[str, str],
    *,
    target_section: SectionName,
    snippet: str | None,
) -> dict[str, Any]:
    clean = _clean_snippet(snippet)
    candidate_sections = [target_section] if target_section != "unknown" else []
    candidate_sections.extend(
        section for section in ("title", "abstract", "claims", "description", "drawing_description")
        if section not in candidate_sections
    )

    if clean:
        for section in candidate_sections:
            text = sections.get(section, "") or ""
            index = text.find(clean)
            if index >= 0:
                return {
                    "type": "text",
                    "section": section,
                    "start": index,
                    "end": index + len(clean),
                    "snippet": clean,
                }

    for term in CONTAMINATION_TERMS:
        for section in candidate_sections:
            text = sections.get(section, "") or ""
            index = text.find(term)
            if index >= 0:
                return {
                    "type": "text",
                    "section": section,
                    "start": index,
                    "end": index + len(term),
                    "snippet": term,
                }

    if target_section != "unknown":
        return {"type": "section", "section": target_section, "start": None, "end": None, "snippet": clean}

    return {"type": "missing", "section": "unknown", "start": None, "end": None, "snippet": clean}


def _issue_id(kind: str, index: int, message: str) -> str:
    digest = hashlib.sha1(f"{kind}:{index}:{message}".encode("utf-8")).hexdigest()[:10]
    return f"{kind}-{digest}"


def _iter_review_items(review: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    items: list[tuple[str, str, str | None]] = []
    for value in review.get("blocking_issues") or []:
        items.append(("blocking", str(value), None))
    for value in review.get("contamination_hits") or []:
        if isinstance(value, dict):
            items.append(("hit", str(value.get("content") or value.get("snippet") or value), value.get("snippet")))
        else:
            items.append(("hit", str(value), None))
    for value in review.get("rewrite_suggestions") or []:
        items.append(("suggestion", str(value), None))
    return items


def normalize_post_draft_issues(review: dict[str, Any], sections: dict[str, str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for index, (kind, message, snippet) in enumerate(_iter_review_items(review)):
        target_section = infer_target_section(message)
        anchor = locate_issue_anchor(sections, target_section=target_section, snippet=snippet or message)
        status = "unanchored" if anchor["type"] == "missing" else "open"
        severity = "critical" if kind == "blocking" else "high" if kind == "hit" else "medium"
        issues.append(
            {
                "id": _issue_id(kind, index, message),
                "kind": kind,
                "severity": severity,
                "source": "post_draft_review",
                "message": message,
                "snippet": snippet,
                "target_section": anchor["section"] if anchor["section"] != "unknown" else target_section,
                "anchor": anchor,
                "status": status,
            }
        )
    return issues
```

- [ ] **Step 4: Add repair-session endpoint**

In `backend/app/main.py`, add:

```python
@app.get(
    "/api/projects/{project_id}/post-draft-reviews/{run_id}/repair-session",
    response_model=PostDraftRepairSession,
)
def get_post_draft_repair_session(project_id: str, run_id: str) -> PostDraftRepairSession:
    project = store.get_project(project_id)
    review = _get_post_draft_review_or_404(project, run_id)
    package = store.get_project_package(project_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Draft package not found")

    sections = {
        "title": package.title,
        "abstract": package.abstract,
        "claims": package.claims,
        "description": package.description,
        "drawing_description": package.drawing_description,
    }
    current_hash = _draft_package_hash(package)
    review_hash = getattr(review, "draft_package_hash", None)
    issues = normalize_post_draft_issues(review.model_dump(), sections)
    return PostDraftRepairSession(
        project_id=project_id,
        review_run_id=run_id,
        draft_package_hash=review_hash,
        current_draft_hash=current_hash,
        stale=bool(review_hash and review_hash != current_hash),
        issues=issues,
        sections=sections,
    )
```

If `_get_post_draft_review_or_404` or `_draft_package_hash` do not yet exist, add small private helpers near the existing post-draft review endpoints and reuse the project store’s existing hash logic.

- [ ] **Step 5: Verify PR-1**

Run:

```bash
python3 -m pytest tests/test_post_draft_repair.py -q
python3 -m pytest tests/test_post_draft_review.py -q
```

Expected: all tests pass.

### PR-2: Frontend Full-Screen Annotated Editor Manual Flow

**Owner:** `qwenworker`

**Branch:** `codex/repair-editor-shell-manual`

**Depends On:** PR-1

**Files:**

- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/flow/panels/PostDraftReviewPanel.tsx`
- Create: `frontend/src/flow/panels/PostDraftRepairEditor.tsx`
- Create: `frontend/src/flow/panels/PostDraftIssueRail.tsx`
- Create: `frontend/src/flow/panels/AnnotatedDraftSection.tsx`
- Create: `frontend/src/flow/panels/DraftRepairInspector.tsx`
- Create: `frontend/src/PostDraftRepairEditor.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add API types and client**

Add to `frontend/src/api.ts`:

```ts
export type DraftIssueAnchor = {
  type: "text" | "section" | "missing";
  section: "title" | "abstract" | "claims" | "description" | "drawing_description" | "unknown";
  start?: number | null;
  end?: number | null;
  snippet?: string | null;
};

export type DraftReviewIssue = {
  id: string;
  kind: "blocking" | "hit" | "suggestion";
  severity: "critical" | "high" | "medium" | "low";
  source: string;
  message: string;
  snippet?: string | null;
  target_section: DraftIssueAnchor["section"];
  anchor: DraftIssueAnchor;
  status: "open" | "fixed" | "skipped" | "stale" | "unanchored";
};

export type PostDraftRepairSession = {
  project_id: string;
  review_run_id: string;
  draft_package_hash?: string | null;
  current_draft_hash?: string | null;
  stale: boolean;
  issues: DraftReviewIssue[];
  sections: Record<string, string>;
};

export async function getPostDraftRepairSession(projectId: string, runId: string): Promise<PostDraftRepairSession> {
  return request<PostDraftRepairSession>(`/api/projects/${projectId}/post-draft-reviews/${runId}/repair-session`);
}
```

- [ ] **Step 2: Write editor interaction tests**

Create `frontend/src/PostDraftRepairEditor.test.tsx` with:

```tsx
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { PostDraftRepairEditor } from "./flow/panels/PostDraftRepairEditor";

const session = {
  project_id: "p1",
  review_run_id: "r1",
  draft_package_hash: "old",
  current_draft_hash: "old",
  stale: false,
  issues: [
    {
      id: "blocking-1",
      kind: "blocking",
      severity: "critical",
      source: "post_draft_review",
      message: "标题存在重复词汇方法方法",
      snippet: "方法方法",
      target_section: "title",
      anchor: { type: "text", section: "title", start: 22, end: 26, snippet: "方法方法" },
      status: "open",
    },
  ],
  sections: {
    title: "一种基于城市体检指标置信度的无人机主动采集方法方法",
    abstract: "摘要文本",
    claims: "权利要求文本",
    description: "说明书文本",
    drawing_description: "图1说明",
  },
} as const;

describe("PostDraftRepairEditor", () => {
  it("renders issue rail, editable sections, and inspector actions", () => {
    render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    expect(screen.getByText("阻断")).toBeTruthy();
    expect(screen.getByDisplayValue(/方法方法/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "人工修正" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "生成 AI 修正" })).toBeTruthy();
  });

  it("saves edited section content", () => {
    const onSave = vi.fn();
    render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={onSave}
      />,
    );

    fireEvent.change(screen.getByLabelText("标题"), {
      target: { value: "一种基于城市体检指标置信度的无人机主动采集方法" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存当前初稿" }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "一种基于城市体检指标置信度的无人机主动采集方法",
      }),
    );
  });
});
```

Run: `npm --prefix frontend test -- PostDraftRepairEditor.test.tsx`

Expected: fail because components do not exist.

- [ ] **Step 3: Create editor shell and child components**

Implement a textarea-first editor. Required exported component signature:

```ts
export function PostDraftRepairEditor(props: {
  open: boolean;
  session: PostDraftRepairSession | null;
  saving: boolean;
  onClose: () => void;
  onSave: (fields: DraftPackageManualUpdate) => Promise<void> | void;
}): JSX.Element | null
```

Required behavior:

- Left rail groups issues by `blocking`, `hit`, `suggestion`, `unanchored`.
- Clicking an issue selects it and selects the issue’s target section.
- Center area renders labeled fields for `title`, `abstract`, `claims`, `description`, `drawing_description`.
- Right inspector shows the selected issue message, snippet, target section, `人工修正`, and disabled `生成 AI 修正` when `session.stale` is true.
- Save calls `onSave` with all five section fields.

- [ ] **Step 4: Add entry point in post-draft review panel**

In `PostDraftReviewPanel.tsx`, add `打开标注式修复编辑器` near the existing workbench header. The button is disabled when no current package exists. On click, fetch `getPostDraftRepairSession(projectId, latestReviewRunId)` and open `PostDraftRepairEditor`.

- [ ] **Step 5: Add layout CSS**

Add CSS classes:

- `.repair-editor-shell`
- `.repair-editor-grid`
- `.repair-issue-rail`
- `.repair-document-pane`
- `.repair-inspector`
- `.annotated-draft-section`

Desktop behavior: three columns `minmax(220px, 280px) minmax(420px, 1fr) minmax(260px, 340px)`, height capped with internal scrolling.

Mobile behavior under `760px`: single column with issue rail, document pane, inspector stacked and no text overlap.

- [ ] **Step 6: Verify PR-2**

Run:

```bash
npm --prefix frontend test -- PostDraftRepairEditor.test.tsx PostDraftReviewPanel.test.tsx
npm --prefix frontend run build
```

Expected: all tests and build pass.

### PR-3: Backend Single-Issue AI Patch Lifecycle

**Owner:** `deepseekworker`

**Branch:** `codex/repair-editor-ai-patches-api`

**Depends On:** PR-1

**Files:**

- Modify: `backend/app/schemas.py`
- Modify: `backend/app/post_draft_repair.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_post_draft_repair.py`

- [ ] **Step 1: Add failing stale and unsafe patch tests**

Append tests that:

- generate a patch with `draft_package_hash="h1"`;
- mutate the current draft so the hash becomes `"h2"`;
- applying the old patch returns HTTP 409;
- patch text containing `注：`, `主席修订`, `补充实施方式`, or JSON `{"action":` is rejected with HTTP 422.

- [ ] **Step 2: Add patch schemas**

Add:

```python
class DraftRepairPatchCreate(BaseModel):
    issue_id: str
    draft_package_hash: str
    target_section: Literal["title", "abstract", "claims", "description", "drawing_description"]
    selected_text: str | None = None
    nearby_context: str | None = None


class DraftRepairPatch(BaseModel):
    id: str
    issue_id: str
    status: Literal["proposed", "stale", "unsafe", "applied"]
    target_section: Literal["title", "abstract", "claims", "description", "drawing_description"]
    original: str
    patched: str
    diff_summary: str
    risk_notes: list[str] = Field(default_factory=list)
    draft_package_hash: str


class DraftRepairPatchApplyResult(BaseModel):
    package: DraftPackage
    current_draft_hash: str
```

- [ ] **Step 3: Add safety helpers**

In `post_draft_repair.py`, add:

```python
UNSAFE_PATCH_TERMS = ("注：", "待验证", "主席", "补充实施方式", "需补充", "提交前补充", "{\"action\"", "\"patched\"")


def validate_repair_patch_text(text: str) -> list[str]:
    return [term for term in UNSAFE_PATCH_TERMS if term in text]


def apply_section_patch(section_text: str, original: str, patched: str) -> str:
    if original not in section_text:
        raise ValueError("Patch original text is no longer present")
    return section_text.replace(original, patched, 1)
```

- [ ] **Step 4: Add endpoints**

Add:

- `POST /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-patches`
- `POST /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-patches/{patch_id}/apply`

First implementation may be deterministic:

- if `selected_text` exists, use it as `original`;
- create `patched` by removing known internal terms and duplicate `方法方法`;
- return `unsafe` if the proposed patched text still contains unsafe terms.

Do not call an external model in this PR.

- [ ] **Step 5: Verify PR-3**

Run:

```bash
python3 -m pytest tests/test_post_draft_repair.py -q
python3 -m pytest tests/test_post_draft_review.py -q
```

Expected: all tests pass.

### PR-4: Frontend AI Patch Preview And Apply

**Owner:** `qwenworker`

**Branch:** `codex/repair-editor-ai-inspector`

**Depends On:** PR-2 and PR-3

**Files:**

- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/flow/panels/DraftRepairInspector.tsx`
- Modify: `frontend/src/flow/panels/PostDraftRepairEditor.tsx`
- Modify: `frontend/src/PostDraftRepairEditor.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add repair patch API functions**

Add:

```ts
export type DraftRepairPatch = {
  id: string;
  issue_id: string;
  status: "proposed" | "stale" | "unsafe" | "applied";
  target_section: "title" | "abstract" | "claims" | "description" | "drawing_description";
  original: string;
  patched: string;
  diff_summary: string;
  risk_notes: string[];
  draft_package_hash: string;
};

export async function createDraftRepairPatch(
  projectId: string,
  runId: string,
  payload: {
    issue_id: string;
    draft_package_hash: string;
    target_section: DraftRepairPatch["target_section"];
    selected_text?: string | null;
    nearby_context?: string | null;
  },
): Promise<DraftRepairPatch> {
  return request<DraftRepairPatch>(`/api/projects/${projectId}/post-draft-reviews/${runId}/repair-patches`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

Also add `applyDraftRepairPatch`.

- [ ] **Step 2: Expand tests**

Add Vitest cases:

- `生成 AI 修正` calls `createDraftRepairPatch`;
- patch preview renders original/patched text;
- `应用 AI 修正` is disabled for `unsafe` and `stale`;
- applying a safe patch updates the local section content and shows the recompile/re-review next-step hint.

- [ ] **Step 3: Wire inspector actions**

`DraftRepairInspector` must show:

- selected issue details;
- `生成 AI 修正`;
- patch diff preview;
- risk notes;
- disabled apply button with reason for stale/unsafe patches;
- successful apply message: `已写回当前初稿，请重新编译正式稿并重新成稿会审。`

- [ ] **Step 4: Verify PR-4**

Run:

```bash
npm --prefix frontend test -- PostDraftRepairEditor.test.tsx
npm --prefix frontend run build
```

Expected: all tests and build pass.

### PR-5: Patent Text QA, Browser QA, And Merge Hardening

**Owner:** `kimiworker` for patent text review, `codexreviewer` for final review.

**Branch:** `codex/repair-editor-qa-hardening`

**Depends On:** PR-1 through PR-4

**Files:**

- Modify: `docs/superpowers/specs/2026-06-19-post-draft-review-annotated-editor-design.md`
- Modify or create: `docs/release/post-draft-repair-editor-qa.md`
- Modify tests if review finds specific misses.

- [ ] **Step 1: Add Chinese patent contamination fixtures**

Create a QA note containing at least these fixture phrases:

- `好的，根据技术交底书`
- `主席修订补强`
- `补充实施方式`
- `待验证`
- `需在提交前补充`
- `方法方法`
- `颠覆了固定航线模式`

- [ ] **Step 2: Run browser QA**

With the frontend dev server running, run Playwright at:

- desktop `1440x1100`
- mobile `390x1100`

Validate:

- three columns visible on desktop;
- no text overlap on mobile;
- long issue list scrolls independently;
- save and stale-state hints are visible.

- [ ] **Step 3: Final review gate**

Codex reviewer must check:

- no AI patch can apply when draft hash is stale;
- no unsafe patch text is written into official draft fields;
- export gate still requires recompile and post-draft review after edits;
- all new endpoints have tests;
- frontend build is green;
- screenshots are attached to the PR or QA note.

## Hermes Kanban Mapping

Create these cards on board `patents-post-draft-repair-editor`:

| Card | Assignee | Branch | Workspace | Status |
|---|---|---|---|---|
| PR-0 Baseline repair workbench review and merge | `codexreviewer` | current baseline branch | current repo | manual review |
| PR-1 Backend repair session and issue anchoring | `deepseekworker` | `codex/repair-editor-session-anchors` | worktree | blocked until PR-0 |
| PR-2 Frontend full-screen annotated editor manual flow | `qwenworker` | `codex/repair-editor-shell-manual` | worktree | blocked until PR-1 |
| PR-3 Backend single-issue AI patch lifecycle | `deepseekworker` | `codex/repair-editor-ai-patches-api` | worktree | blocked until PR-1 |
| PR-4 Frontend AI patch preview and apply | `qwenworker` | `codex/repair-editor-ai-inspector` | worktree | blocked until PR-2 and PR-3 |
| PR-5 Patent text QA, browser QA, and merge hardening | `kimiworker` + `codexreviewer` | `codex/repair-editor-qa-hardening` | worktree | blocked until PR-4 |

Before any worker dispatch:

```bash
hermes kanban dispatch --dry-run --max 1
```

Only run a real bounded dispatch after PR-0 is merged and the worktree is clean.

## Merge Policy

- Each PR must include its own tests and command output summary.
- No PR may relax formal export gates.
- No worker may commit `.env`, provider auth, generated secrets, or unrelated dirty files.
- Codex reviews each worker PR before merge.
- Merge order is PR-0 -> PR-1 -> PR-2 and PR-3 in parallel -> PR-4 -> PR-5.
- After PR-5, run a full local release smoke before enabling the feature for normal use.
