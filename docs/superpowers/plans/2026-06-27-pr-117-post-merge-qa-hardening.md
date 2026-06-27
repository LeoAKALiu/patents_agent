# PR #117 Post-Merge QA Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the PR #117 QA audit into executable post-merge regression hardening without changing unrelated product scope.

**Architecture:** Keep the behavior split clear: ordinary app/backend failures use generic app copy, runtime/model failures use LLM/runtime copy, and material upload batch orchestration is testable outside the full `App` component. Add focused tests at the smallest reliable layer first, then keep one manual/e2e checklist for real browser and multi-tab gaps.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, FastAPI TestClient, pytest, Markdown QA docs.

## Global Constraints

- Current repository: `/Users/leo/Projects/patents_agent`.
- Current branch observed while writing this plan: `codex/product-repair-qa-clean-20260627`.
- Current HEAD observed while writing this plan: `6b0f34ac`.
- PR #117 was already merged when this plan was written; treat this as post-merge hardening.
- Do not modify business code until the user explicitly asks to execute this plan.
- Do not introduce mobile maintenance, DMG packaging, release docs, old planning directories, or unrelated refactors.
- Do not create placeholder `BUGS.md`; create a defect ledger only when recording reproduced defects.
- Preserve the error-copy boundary: `userFacingAppErrorMessage` for ordinary app/backend errors, `userFacingErrorMessage` / `runtimeFailureCopy` only for LLM/runtime paths.

---

## File Structure

- Modify `frontend/src/SettingsPanel.tsx`: switch settings load/save/clear failures to generic app error copy.
- Modify `frontend/src/SettingsPanel.test.tsx`: keep the current failing save-validation regression and add load/clear variants.
- Create `frontend/src/materialUploadBatch.ts`: extract material upload batch orchestration into a small injected-dependency helper.
- Create `frontend/src/materialUploadBatch.test.ts`: prove first-invalid-later-valid refreshes materials and all-invalid does not refresh.
- Modify `frontend/src/App.tsx`: replace inline `Promise.all` upload orchestration with the helper while preserving `summarizeMaterialUploadOutcome`.
- Create `tests/test_qa_docs.py`: static guard that QA docs do not imply required docs already exist before first use.
- Modify `docs/qa/pr-117-risk-audit-2026-06-27.md`: mark newly covered automated gates and leave manual gaps explicit.

---

### Task 1: Fix SettingsPanel Ordinary Backend Error Copy

**Files:**
- Modify: `frontend/src/SettingsPanel.tsx:36`
- Test: `frontend/src/SettingsPanel.test.tsx`

**Interfaces:**
- Consumes: `userFacingAppErrorMessage(error, { fallbackTitle })` from `frontend/src/runtimeDisplay.ts`
- Produces: Settings load/save/clear errors that preserve backend HTTP detail and never show LLM outage copy for ordinary backend failures

- [ ] **Step 1: Run the existing failing regression**

Run:

```bash
npm --prefix frontend test -- --run src/SettingsPanel.test.tsx
```

Expected: FAIL in `uses generic app copy for settings save validation errors`, with received text not containing `输入未通过校验`.

- [ ] **Step 2: Change the SettingsPanel import**

Replace:

```ts
import { userFacingErrorCopy, userFacingErrorMessage } from "./runtimeDisplay";
```

With:

```ts
import { userFacingAppErrorMessage, userFacingErrorCopy } from "./runtimeDisplay";
```

- [ ] **Step 3: Change settings load/save/clear catch blocks**

Replace:

```ts
setLoadError(userFacingErrorMessage(err, { fallbackTitle: "设置加载失败" }));
```

With:

```ts
setLoadError(userFacingAppErrorMessage(err, { fallbackTitle: "设置加载失败" }));
```

Replace:

```ts
message: userFacingErrorMessage(err, { fallbackTitle: "设置保存失败" }),
```

With:

```ts
message: userFacingAppErrorMessage(err, { fallbackTitle: "设置保存失败" }),
```

Replace:

```ts
message: userFacingErrorMessage(err, { fallbackTitle: "密钥清除失败" }),
```

With:

```ts
message: userFacingAppErrorMessage(err, { fallbackTitle: "密钥清除失败" }),
```

- [ ] **Step 4: Verify SettingsPanel regression passes**

Run:

```bash
npm --prefix frontend test -- --run src/SettingsPanel.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit this task**

```bash
git add frontend/src/SettingsPanel.tsx frontend/src/SettingsPanel.test.tsx
git commit -m "fix: use app error copy for settings backend failures"
```

---

### Task 2: Extend SettingsPanel Error-Copy Coverage

**Files:**
- Modify: `frontend/src/SettingsPanel.test.tsx`

**Interfaces:**
- Consumes: mocked `getDesktopConfig`, `updateDesktopConfig`, `clearDesktopConfigKey`
- Produces: regression coverage for load, save, and clear ordinary backend failures

- [ ] **Step 1: Add load and clear error tests**

Append these tests inside `describe("SettingsPanel error copy", () => { ... })`:

```tsx
it("uses generic app copy for settings load 404 errors", async () => {
  vi.mocked(getDesktopConfig).mockRejectedValue(
    new Error("GET /api/desktop-config 返回 404：Desktop config not found."),
  );

  render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);

  const panel = await screen.findByText(/加载失败：/);
  expect(panel).toHaveTextContent("资源不存在");
  expect(panel).toHaveTextContent("Desktop config not found.");
  expect(panel).not.toHaveTextContent("LLM");
});

it("uses generic app copy for settings clear conflict errors", async () => {
  vi.mocked(clearDesktopConfigKey).mockRejectedValue(
    new Error("DELETE /api/desktop-config/api-key 返回 409：Config was modified by another session."),
  );

  render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);
  await screen.findByTestId("settings-save");

  await userEvent.click(screen.getByRole("button", { name: /清除密钥/ }));

  const status = await screen.findByTestId("settings-save-status");
  await waitFor(() => {
    expect(status).toHaveTextContent("操作冲突");
    expect(status).toHaveTextContent("Config was modified by another session.");
    expect(status).not.toHaveTextContent("LLM");
  });
});
```

- [ ] **Step 2: Run the focused tests**

Run:

```bash
npm --prefix frontend test -- --run src/SettingsPanel.test.tsx src/runtimeDisplay.test.ts
```

Expected: PASS for all tests in both files.

- [ ] **Step 3: Commit this task**

```bash
git add frontend/src/SettingsPanel.test.tsx
git commit -m "test: cover settings app error copy paths"
```

---

### Task 3: Extract Testable Material Upload Batch Orchestration

**Files:**
- Create: `frontend/src/materialUploadBatch.ts`
- Modify: `frontend/src/App.tsx:1268-1301`
- Test: `frontend/src/materialUploadBatch.test.ts`

**Interfaces:**
- Consumes: `ProjectMaterial` type from `frontend/src/api.ts`
- Produces:
  - `uploadProjectMaterialBatch(projectId, files, deps): Promise<MaterialUploadBatchResult>`
  - `MaterialUploadBatchResult = { uploadedMaterials: ProjectMaterial[]; rejectedUploads: MaterialUploadFailure[]; refreshed: boolean }`

- [ ] **Step 1: Write the failing helper tests**

Create `frontend/src/materialUploadBatch.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";

import type { ProjectMaterial } from "./api";
import { uploadProjectMaterialBatch } from "./materialUploadBatch";

const material = (fileName: string): ProjectMaterial => ({
  id: `m-${fileName}`,
  project_id: "project-1",
  file_name: fileName,
  path: `data/project-materials/project-1/${fileName}`,
  file_type: fileName.split(".").pop() ?? "txt",
  text: "有效材料",
  status: "processed",
  warnings: [],
  metadata: {},
});

describe("uploadProjectMaterialBatch", () => {
  it("refreshes materials when the first file is rejected but a later file succeeds", async () => {
    const badFile = new File(["bad"], "first-bad.xyz", { type: "application/octet-stream" });
    const goodFile = new File(["valid"], "valid-after-bad.md", { type: "text/markdown" });
    const uploadProjectMaterial = vi
      .fn()
      .mockRejectedValueOnce(new Error("材料上传失败：不支持的文件类型。"))
      .mockResolvedValueOnce(material("valid-after-bad.md"));
    const loadMaterials = vi.fn().mockResolvedValue(true);

    const result = await uploadProjectMaterialBatch("project-1", [badFile, goodFile], {
      uploadProjectMaterial,
      loadMaterials,
    });

    expect(uploadProjectMaterial).toHaveBeenCalledTimes(2);
    expect(loadMaterials).toHaveBeenCalledWith("project-1");
    expect(result.refreshed).toBe(true);
    expect(result.uploadedMaterials.map((item) => item.file_name)).toEqual(["valid-after-bad.md"]);
    expect(result.rejectedUploads).toHaveLength(1);
    expect(result.rejectedUploads[0]?.fileName).toBe("first-bad.xyz");
  });

  it("does not refresh materials when every file is rejected", async () => {
    const files = [
      new File(["bad"], "bad-1.xyz", { type: "application/octet-stream" }),
      new File(["empty"], "empty.md", { type: "text/markdown" }),
    ];
    const uploadProjectMaterial = vi
      .fn()
      .mockRejectedValueOnce(new Error("材料上传失败：不支持的文件类型。"))
      .mockRejectedValueOnce(new Error("材料上传失败：文件为空或没有可解析文本。"));
    const loadMaterials = vi.fn().mockResolvedValue(true);

    const result = await uploadProjectMaterialBatch("project-1", files, {
      uploadProjectMaterial,
      loadMaterials,
    });

    expect(uploadProjectMaterial).toHaveBeenCalledTimes(2);
    expect(loadMaterials).not.toHaveBeenCalled();
    expect(result.refreshed).toBe(false);
    expect(result.uploadedMaterials).toEqual([]);
    expect(result.rejectedUploads.map((item) => item.fileName)).toEqual(["bad-1.xyz", "empty.md"]);
  });
});
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
npm --prefix frontend test -- --run src/materialUploadBatch.test.ts
```

Expected: FAIL because `frontend/src/materialUploadBatch.ts` does not exist yet.

- [ ] **Step 3: Create the helper**

Create `frontend/src/materialUploadBatch.ts`:

```ts
import type { ProjectMaterial } from "./api";

export type MaterialUploadFailure = {
  fileName: string;
  error: unknown;
};

export type MaterialUploadBatchResult = {
  uploadedMaterials: ProjectMaterial[];
  rejectedUploads: MaterialUploadFailure[];
  refreshed: boolean;
};

type MaterialUploadBatchDeps = {
  uploadProjectMaterial: (projectId: string, file: File) => Promise<ProjectMaterial>;
  loadMaterials: (projectId: string) => Promise<boolean>;
};

export async function uploadProjectMaterialBatch(
  projectId: string,
  files: File[],
  deps: MaterialUploadBatchDeps,
): Promise<MaterialUploadBatchResult> {
  const results = await Promise.all(
    files.map(async (file) => {
      try {
        return {
          status: "fulfilled" as const,
          fileName: file.name,
          material: await deps.uploadProjectMaterial(projectId, file),
        };
      } catch (error) {
        return {
          status: "rejected" as const,
          fileName: file.name,
          error,
        };
      }
    }),
  );

  const uploadedMaterials = results.flatMap((result) =>
    result.status === "fulfilled" ? [result.material] : [],
  );
  const rejectedUploads = results.flatMap((result) =>
    result.status === "rejected" ? [{ fileName: result.fileName, error: result.error }] : [],
  );

  if (uploadedMaterials.length === 0) {
    return { uploadedMaterials, rejectedUploads, refreshed: false };
  }

  const refreshed = await deps.loadMaterials(projectId);
  return { uploadedMaterials, rejectedUploads, refreshed };
}
```

- [ ] **Step 4: Wire App.tsx to the helper**

Add imports near the existing API/runtime imports:

```ts
import { uploadProjectMaterialBatch, type MaterialUploadFailure } from "./materialUploadBatch";
```

Remove the local `MaterialUploadFailure` type if `App.tsx` has one, or change it to use the imported type.

Replace the body inside `withStatus("material-upload", async () => { ... })` with:

```ts
const { uploadedMaterials, rejectedUploads, refreshed } = await uploadProjectMaterialBatch(projectId, files, {
  uploadProjectMaterial,
  loadMaterials,
});
if (uploadedMaterials.length > 0 && !refreshed) return;
const outcome = summarizeMaterialUploadOutcome(files.length, uploadedMaterials, rejectedUploads);
if (outcome.level === "error") {
  setError(outcome.text);
} else {
  setMessage(outcome.text);
}
input.value = "";
```

- [ ] **Step 5: Run focused upload tests**

Run:

```bash
npm --prefix frontend test -- --run src/materialUploadBatch.test.ts src/AppStateRecovery.test.ts src/GuidedMaterialStatus.test.tsx src/flow/panels/MaterialSummary.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit this task**

```bash
git add frontend/src/materialUploadBatch.ts frontend/src/materialUploadBatch.test.ts frontend/src/App.tsx
git commit -m "test: cover mixed material upload refresh path"
```

---

### Task 4: Add QA Documentation Static Guard

**Files:**
- Create: `tests/test_qa_docs.py`
- Verify: `docs/qa/ai-scenario-testing-pipeline.md`

**Interfaces:**
- Consumes: QA Markdown document text
- Produces: pytest guard against wording that assumes `BUGS.md` already exists

- [ ] **Step 1: Write the failing-or-passing guard test**

Create `tests/test_qa_docs.py`:

```py
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ai_scenario_pipeline_does_not_assume_bug_ledger_already_exists() -> None:
    text = (ROOT / "docs/qa/ai-scenario-testing-pipeline.md").read_text(encoding="utf-8")

    forbidden_phrases = [
        "-> BUGS.md ->",
        "按 BUGS.md 模板记录",
        "## 4. BUGS.md 台账",
        "请读取 BUGS.md",
        "更新 BUGS.md 状态",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in text

    assert "首次使用" in text
    assert "缺陷台账" in text
    assert "如果 `BUGS.md` 尚不存在" in text
```

- [ ] **Step 2: Run the docs test**

Run:

```bash
python3 -m pytest -q tests/test_qa_docs.py
```

Expected: PASS. If it fails, update only `docs/qa/ai-scenario-testing-pipeline.md` wording; do not create `BUGS.md`.

- [ ] **Step 3: Commit this task**

```bash
git add tests/test_qa_docs.py docs/qa/ai-scenario-testing-pipeline.md
git commit -m "test: guard QA defect ledger wording"
```

---

### Task 5: Run Targeted Regression Suite and Update Audit Status

**Files:**
- Modify: `docs/qa/pr-117-risk-audit-2026-06-27.md`

**Interfaces:**
- Consumes: results from Tasks 1-4
- Produces: audit doc status that separates automated coverage from manual gaps

- [ ] **Step 1: Run frontend targeted regression**

Run:

```bash
npm --prefix frontend test -- --run src/SettingsPanel.test.tsx src/materialUploadBatch.test.ts src/AppStateRecovery.test.ts src/runtimeDisplay.test.ts src/GuidedMaterialStatus.test.tsx src/flow/panels/MaterialSummary.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run backend targeted regression**

Run:

```bash
python3 -m pytest -q tests/test_disclosure.py tests/test_official_compile.py tests/test_post_draft_review.py tests/test_post_draft_repair.py tests/test_runtime_controls.py tests/test_qa_docs.py
```

Expected: PASS, with any existing skips unchanged.

- [ ] **Step 3: Update audit doc status**

Append this section to `docs/qa/pr-117-risk-audit-2026-06-27.md`:

```md
## Post-Merge Hardening Status

- SettingsPanel app/backend error copy: automated regression added and passing.
- Mixed material upload refresh path: helper-level regression added and passing.
- QA defect ledger wording: static docs regression added and passing.
- Still requires manual/e2e validation: real browser/Tauri upload refresh, two-tab concurrency, offline recovery, real repair-session UI evidence.
```

- [ ] **Step 4: Run static diff checks**

Run:

```bash
git diff --check
rg -n "请读取 BUGS\\.md|更新 BUGS\\.md 状态|-> BUGS\\.md|BUGS\\.md 台账" docs/qa tests | cat
git status --short --branch
```

Expected: `git diff --check` exits 0; `rg` prints no forbidden doc wording; status shows only intended files.

- [ ] **Step 5: Commit this task**

```bash
git add docs/qa/pr-117-risk-audit-2026-06-27.md
git commit -m "docs: record PR 117 QA hardening status"
```

---

### Task 6: Manual QA Gate for Remaining High-Risk Paths

**Files:**
- Modify: `docs/qa/pr-117-risk-audit-2026-06-27.md`

**Interfaces:**
- Consumes: running dev app and a real test project
- Produces: manual evidence notes for paths that unit/integration tests cannot prove

- [ ] **Step 1: Start the app stack**

Run backend and frontend in separate terminals:

```bash
uvicorn backend.app.main:app --reload
npm --prefix frontend run dev
```

Expected: backend health succeeds and Vite prints a local URL.

- [ ] **Step 2: Execute material upload manual cases**

Use one real project and record project id in the audit doc.

Cases:

```text
1. Upload first-bad.xyz + valid-after-bad.md together.
2. Upload valid-1.txt + bad.xyz + valid-2.md together.
3. Upload two invalid files.
4. Upload 20+ small mixed files.
5. Start upload and refresh the page while it is in flight.
```

Expected:

```text
Successful files appear in the material list after refresh.
Failed files appear in the failure summary.
No fake success appears for all-invalid or offline cases.
```

- [ ] **Step 3: Execute error-copy manual cases**

Trigger or mock ordinary backend errors:

```text
404 stale project
409 stale repair hash
422 invalid SettingsPanel Base URL
500 ordinary backend error outside runtime/model call
```

Expected:

```text
Generic app copy appears and backend detail is retained.
The phrase "LLM 服务暂时不可用" appears only for runtime/model failures.
```

- [ ] **Step 4: Execute state-machine and multi-tab cases**

Cases:

```text
1. Double-click official compile.
2. Double-click repair patch create/apply.
3. Open two tabs for one project and run compile/review/upload concurrently.
4. Start repair/review and edit runtime controls.
5. Switch offline and back online before retrying upload.
```

Expected:

```text
No duplicate visible runs in single-tab flows.
Two-tab conflicts either reject cleanly or recover after refresh.
No stuck loading state remains after failure or retry.
```

- [ ] **Step 5: Record manual outcome**

Append either this pass block:

```md
## Manual QA Evidence

- Date:
- Source branch/SHA:
- Backend URL:
- Frontend URL:
- Project id:
- Material upload destructive cases: pass
- Error-copy cases: pass
- State-machine/multi-tab cases: pass
- Evidence paths:
```

Or this fail block:

```md
## Manual QA Evidence

- Date:
- Source branch/SHA:
- Backend URL:
- Frontend URL:
- Project id:
- Failed case:
- Reproduction steps:
- Actual:
- Expected:
- Likely files:
- Recommended regression:
```

- [ ] **Step 6: Commit manual audit update**

```bash
git add docs/qa/pr-117-risk-audit-2026-06-27.md
git commit -m "docs: record PR 117 manual QA evidence"
```

---

## Self-Review

- Spec coverage: The plan covers confirmed SettingsPanel error-copy failure, mixed batch upload refresh proof, QA docs first-use wording, targeted regression commands, and manual/e2e gaps.
- Placeholder scan: No placeholder markers or unspecified test steps remain.
- Type consistency: `MaterialUploadFailure` and `MaterialUploadBatchResult` are defined in Task 3 before use; SettingsPanel imports use existing `userFacingAppErrorMessage`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-27-pr-117-post-merge-qa-hardening.md`. Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Execution still requires explicit user approval because the current request asked for a plan, not implementation.
