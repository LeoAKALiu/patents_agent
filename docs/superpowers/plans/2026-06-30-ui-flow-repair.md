# UI Flow Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make PatentAgent's production UI present one reliable next action for the patent drafting flow, with document/export gates driven by the backend export-readiness source of truth.

**Architecture:** Keep the existing React/Tauri shell and the existing backend API contract. Repair the state derivation layer first, then adjust presentation components so workbench, document repair, and export all point to the same next action. Avoid broad style rewrites; this is a flow clarity and reliability fix.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, existing CSS classes, FastAPI export-readiness API.

## Global Constraints

- Source identity at planning time: branch `codex/grantatlas-readme-branding`, HEAD `f566fc09`, worktree `/Users/leo/Projects/patents_agent`.
- Worktree is dirty before this plan; do not revert unrelated changes.
- Production React lives under `frontend/src/`; specs and screenshots are not implementation evidence.
- No `DESIGN.md` exists in this repository; do not invent design tokens.
- Export gate pages must use `ExportReadiness.next_action` and related fields as the source of truth.
- Primary CTA must always match the real next action.
- If `next_action === "run_quality_checks"`, no page may show `编辑文稿` as the dominant action.
- Hidden internal content must stay available for review only after the user explicitly opens it.

---

## File Structure

- Modify `frontend/src/features/documentRepair/selectors.ts`
  - Owns document gate state, document primary action, issue summaries, and version chain.
  - Add export-readiness-first helpers here so all document tabs consume one consistent state.

- Modify `frontend/src/features/documentRepair/selectors.test.ts`
  - Add regression coverage for `next_action=run_quality_checks` and unknown quality checks.
  - Add regression coverage for failed/interrupted post-draft review recovery.

- Modify `frontend/src/features/documentRepair/DocumentOverviewTab.tsx`
  - Display the action produced by selectors and show a compact unlock reason.
  - Do not add API calls here.

- Modify `frontend/src/views/exportView.tsx`
  - Keep the locked gate visible.
  - Hide long draft preview while the official export gate is locked.

- Modify `frontend/src/views/exportView.test.tsx`
  - Add locked-preview regression tests.

- Modify `frontend/src/features/workbench/WorkbenchWorkspace.tsx`
  - Remove the generic no-project primary CTA.
  - Move secondary workspace links into a visually secondary `其他操作` disclosure.

- Modify `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`
  - Update no-project expectations.
  - Add coverage for hidden secondary actions.

- Modify `frontend/src/features/workbench/selectors.ts`
  - Add a compact five-phase user progress summary while preserving the existing nine-step data.

- Modify `frontend/src/features/workbench/selectors.test.ts`
  - Verify five-phase labels and current phase.

- Create during Task 6: `qa_runs/ui-flow-repair-2026-06-30/`
  - Store browser screenshots after implementation verification.

---

### Task 1: Make Document Repair Follow Export Readiness

**Files:**
- Modify: `frontend/src/features/documentRepair/selectors.ts`
- Modify: `frontend/src/features/documentRepair/selectors.test.ts`

**Interfaces:**
- Consumes: `ExportReadiness.next_action`, `quality_done`, `quality_check_states`, `missing_quality_checks`, `stale_quality_checks`, `failed_quality_checks`, `unknown_quality_checks`, `compile_status`, `review_gate_status`.
- Produces: `DocumentRepairState.gates`, `DocumentRepairState.primaryAction`, `DocumentRepairState.topConclusion`.

- [ ] **Step 1: Add failing selector tests for quality-readiness precedence**

Append this test inside `describe("deriveDocumentRepairState", () => { ... })` in `frontend/src/features/documentRepair/selectors.test.ts`:

```ts
  it("uses export-readiness quality state before artifact presence", () => {
    const state = deriveDocumentRepairState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makePackage() }),
        currentPackage: makePackage(),
        currentDraftHash: "draft-current",
        currentSourceDraftHash: "draft-current",
        officialCompileRuns: [makeOfficialCompileRun()],
        postDraftReviews: [
          makePostDraftReview({
            status: "failed",
            blocking_issues: [],
            role_results: [],
          }),
        ],
      }),
      exportReadiness: makeExportReadiness({
        export_allowed: false,
        quality_required: true,
        official_compile_required: false,
        post_draft_review_required: false,
        next_action: "run_quality_checks",
        reason: "当前初稿尚未完成质量检查。",
        quality_done: false,
        review_gate_status: "failed",
        review_blocking_issues: [],
        unknown_quality_checks: ["claim_defense_worksheet", "draft_completion"],
        quality_check_states: {
          filing_readiness: "current",
          claim_defense_worksheet: "unknown",
          draft_completion: "unknown",
        },
      }),
    });

    expect(state.gates.quality.state).toBe("待重新验证");
    expect(state.gates.quality.detail).toContain("质量检查");
    expect(state.gates.postDraftReview.state).toBe("运行失败");
    expect(state.primaryAction).toEqual({
      label: "运行质量检查",
      targetSection: "workbench",
    });
    expect(state.topConclusion).toBe("当前初稿尚未完成质量检查。");
  });
```

- [ ] **Step 2: Run the focused failing test**

Run:

```bash
npm --prefix frontend test -- --run src/features/documentRepair/selectors.test.ts -t "uses export-readiness quality state before artifact presence"
```

Expected: FAIL because `quality.state` is currently derived as `当前有效` and `primaryAction.label` is currently `编辑文稿`.

- [ ] **Step 3: Add export-readiness helper functions**

In `frontend/src/features/documentRepair/selectors.ts`, add these helpers near `derivePrimaryAction`:

```ts
function hasAnyQualityGap(exportReadiness: ExportReadiness | null | undefined): boolean {
  if (!exportReadiness) return false;
  if (exportReadiness.quality_done === false) return true;
  if (exportReadiness.quality_required) return true;
  if ((exportReadiness.missing_quality_checks?.length ?? 0) > 0) return true;
  if ((exportReadiness.stale_quality_checks?.length ?? 0) > 0) return true;
  if ((exportReadiness.failed_quality_checks?.length ?? 0) > 0) return true;
  if ((exportReadiness.unknown_quality_checks?.length ?? 0) > 0) return true;
  return Object.values(exportReadiness.quality_check_states ?? {}).some((state) => state !== "current");
}

function qualityPrimaryActionLabel(exportReadiness: ExportReadiness | null | undefined): string {
  const hasMissingOrUnknown = Boolean(
    (exportReadiness?.missing_quality_checks?.length ?? 0) > 0
      || (exportReadiness?.unknown_quality_checks?.length ?? 0) > 0
      || Object.values(exportReadiness?.quality_check_states ?? {}).some((state) =>
        state === "missing" || state === "unknown"
      ),
  );
  return hasMissingOrUnknown || exportReadiness?.quality_done === false
    ? "运行质量检查"
    : "重新质量检查";
}

function primaryActionFromNextAction(
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
): DocumentRepairState["primaryAction"] | null {
  if (!exportReadiness) return null;
  if (exportReadiness.export_allowed || exportReadiness.next_action === "export_ready" || facts.exportReady) {
    return { label: "导出正式稿", targetSection: "export" };
  }
  if (exportReadiness.next_action === "generate_draft") {
    return { label: "生成内部初稿", targetSection: "workbench" };
  }
  if (exportReadiness.next_action === "run_quality_checks") {
    return { label: qualityPrimaryActionLabel(exportReadiness), targetSection: "workbench" };
  }
  if (exportReadiness.next_action === "run_official_compile") {
    return { label: facts.latestOfficialCompile ? "重新编译正式稿" : "生成正式稿", targetSection: "workbench" };
  }
  if (exportReadiness.next_action === "run_post_draft_review") {
    if (facts.blockingIssues.length > 0) return { label: "进入标注修复", targetTab: "annotated" };
    return { label: facts.latestPostDraftReview ? "重新成稿会审" : "启动成稿会审", targetSection: "workbench" };
  }
  return null;
}
```

- [ ] **Step 4: Make quality gate state honor export-readiness**

In `deriveQualityGateState(...)`, place this block after the running/failed checks and before artifact hash checks:

```ts
  if (hasAnyQualityGap(exportReadiness)) {
    return "待重新验证";
  }
  if (exportReadiness?.quality_done === true) {
    return "当前有效";
  }
```

Keep the existing `failed_quality_checks` branch before this block so failed checks still return `运行失败`.

- [ ] **Step 5: Make primary action honor export-readiness**

Replace the top of `derivePrimaryAction(...)` with:

```ts
  if (!facts.hasInternalDraft) return { label: "生成内部初稿", targetSection: "workbench" };

  const exportReadinessAction = primaryActionFromNextAction(exportReadiness, facts);
  if (exportReadinessAction) return exportReadinessAction;

  if (facts.exportReady) return { label: "导出正式稿", targetSection: "export" };
```

Leave the existing fallback branches after this block so older data without export-readiness still works.

- [ ] **Step 6: Make top conclusion prefer backend reason for locked flows**

In `deriveTopConclusion(...)`, before generic stale/gate conclusions, add:

```ts
  if (exportReadiness?.reason && exportReadiness.next_action !== "export_ready") {
    return exportReadiness.reason;
  }
```

Do not use this branch when export is ready; the ready conclusion remains more useful than raw backend copy.

- [ ] **Step 7: Run focused document repair selector tests**

Run:

```bash
npm --prefix frontend test -- --run src/features/documentRepair/selectors.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/documentRepair/selectors.ts frontend/src/features/documentRepair/selectors.test.ts
git commit -m "fix: align document repair gates with export readiness"
```

---

### Task 2: Surface the Correct Unlock Action in Document Overview

**Files:**
- Modify: `frontend/src/features/documentRepair/DocumentOverviewTab.tsx`
- Modify: `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`

**Interfaces:**
- Consumes: `DocumentRepairState.topConclusion`, `DocumentRepairState.primaryAction`, `DocumentRepairState.gates`.
- Produces: screen-level copy that makes the next unlock action obvious.

- [ ] **Step 1: Add failing workspace rendering test**

Append this test to `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`:

```ts
  it("shows quality-check recovery as the dominant document overview action", () => {
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState({
          filingReports: [],
          worksheets: [],
          completionRuns: [],
        })}
        handlers={makeHandlers()}
        exportReadiness={makeExportReadiness({
          export_allowed: false,
          quality_required: true,
          post_draft_review_required: false,
          next_action: "run_quality_checks",
          reason: "当前初稿尚未完成质量检查。",
          quality_done: false,
          review_gate_status: "failed",
          review_blocking_issues: [],
          unknown_quality_checks: ["claim_defense_worksheet", "draft_completion"],
          quality_check_states: {
            filing_readiness: "current",
            claim_defense_worksheet: "unknown",
            draft_completion: "unknown",
          },
        })}
        onNavigate={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "当前初稿尚未完成质量检查。" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /运行质量检查/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "编辑文稿" })).toBeNull();
    expect(screen.getByText("质量检查")).toBeInTheDocument();
    expect(screen.getByText("待重新验证")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Run the failing rendering test**

Run:

```bash
npm --prefix frontend test -- --run src/features/documentRepair/DocumentRepairWorkspace.test.tsx -t "shows quality-check recovery"
```

Expected: FAIL before Task 1 is integrated, or PASS after Task 1. If it passes after Task 1, keep the test because it protects the rendered surface.

- [ ] **Step 3: Add an unlock route hint in the overview hero**

In `DocumentOverviewTab.tsx`, add this helper before the `DocumentOverviewTab` export:

```ts
function primaryActionHint(state: DocumentRepairState): string {
  if (state.primaryAction.targetSection === "workbench") {
    return "该操作会回到工作台，由主流程启动对应 Agent 门禁。";
  }
  if (state.primaryAction.targetSection === "export") {
    return "导出门禁已放行，可以进入导出工作区保存正式提交稿。";
  }
  if (state.primaryAction.targetTab === "annotated") {
    return "该操作会打开标注修复，按问题定位到正文并生成安全补丁。";
  }
  if (state.primaryAction.targetTab === "issues") {
    return "该操作会打开问题队列，先处理阻断项再重新验证。";
  }
  return "该操作只影响当前文稿工作区，不会启动新的 Agent 运行。";
}
```

Then add this line inside `.document-overview-hero`, directly under the existing `<p>{state.issueSummary.explanation}</p>`:

```tsx
          <p className="document-action-hint">{primaryActionHint(state)}</p>
```

- [ ] **Step 4: Run document repair workspace tests**

Run:

```bash
npm --prefix frontend test -- --run src/features/documentRepair/DocumentRepairWorkspace.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documentRepair/DocumentOverviewTab.tsx frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx
git commit -m "fix: make document overview recovery action explicit"
```

---

### Task 3: Hide Long Draft Preview While Export Is Locked

**Files:**
- Modify: `frontend/src/views/exportView.tsx`
- Modify: `frontend/src/views/exportView.test.tsx`

**Interfaces:**
- Consumes: `officialAllowed` derived inside `ExportView`.
- Produces: locked export page with unlock guidance first and no long draft preview until official export is unlocked.

- [ ] **Step 1: Add failing locked-preview test**

Append this test to `frontend/src/views/exportView.test.tsx`:

```ts
  it("hides the long package preview while official export is locked", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={{
          ...packageValue,
          claims: "1. 一种方法。".repeat(80),
          description: "说明书长文本。".repeat(120),
        }}
        postDraftReview={null}
        officialCompileRun={null}
        exportReadiness={{
          export_allowed: false,
          draft_required: false,
          quality_required: true,
          official_compile_required: false,
          post_draft_review_required: false,
          next_action: "run_quality_checks",
          reason: "quality_required",
          quality_done: false,
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={false}
        qualityCheckStates={{
          filing_readiness: "current",
          claim_defense_worksheet: "unknown",
          draft_completion: "unknown",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.getByText("质量检查未完成")).toBeInTheDocument();
    expect(screen.getByText("导出解锁前隐藏申请文本预览")).toBeInTheDocument();
    expect(screen.queryByText(/说明书长文本。说明书长文本。/)).toBeNull();
  });
```

- [ ] **Step 2: Run the focused failing test**

Run:

```bash
npm --prefix frontend test -- --run src/views/exportView.test.tsx -t "hides the long package preview"
```

Expected: FAIL because `PackagePreview` currently renders in the locked state.

- [ ] **Step 3: Replace locked preview with explicit locked copy**

In `frontend/src/views/exportView.tsx`, replace:

```tsx
      <div className="report-preview-pane">
        <PackagePreview packageValue={packageValue} compact />
      </div>
```

with:

```tsx
      {officialAllowed ? (
        <div className="report-preview-pane">
          <PackagePreview packageValue={packageValue} compact />
        </div>
      ) : (
        <div className="callout callout-warn">
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>导出解锁前隐藏申请文本预览</strong>
            <p>先完成上方门禁后再复核正式提交稿内容；内部稿仍可在文稿工作区查看和编辑。</p>
          </div>
        </div>
      )}
```

This uses the already imported `AlertTriangle`.

- [ ] **Step 4: Run export view tests**

Run:

```bash
npm --prefix frontend test -- --run src/views/exportView.test.tsx src/features/export/ExportWorkspace.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/exportView.tsx frontend/src/views/exportView.test.tsx
git commit -m "fix: hide export preview until official gate unlocks"
```

---

### Task 4: Reduce Workbench Routing Noise

**Files:**
- Modify: `frontend/src/features/workbench/WorkbenchWorkspace.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`

**Interfaces:**
- Consumes: `WorkbenchState.hasProject`, `primaryTarget`, `nextAction`.
- Produces: no-project workbench with three explicit start cards and selected-project workbench with secondary routes under `其他操作`.

- [ ] **Step 1: Update no-project test to reject generic CTA**

In `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`, replace the final assertion in `it("shows compact start paths when no project is selected", ...)`:

```ts
    await userEvent.click(screen.getByRole("button", { name: "创建项目" }));

    expect(handlers.onStartChoice).toHaveBeenCalledWith("invention");
```

with:

```ts
    expect(screen.queryByRole("button", { name: "创建项目" })).toBeNull();

    await userEvent.click(screen.getByRole("button", {
      name: /从技术想法撰写发明专利/,
    }));

    expect(handlers.onStartChoice).toHaveBeenCalledWith("invention");
```

- [ ] **Step 2: Add failing secondary-action disclosure test**

Append this test to `WorkbenchWorkspace.test.tsx`:

```ts
  it("keeps secondary workspaces behind an other-actions disclosure", async () => {
    const navigate = vi.fn();
    render(<WorkbenchWorkspace state={makeState()} handlers={makeHandlers()} onNavigate={navigate} />);

    expect(screen.getByRole("button", { name: "进入文稿与修复" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "知识库" })).toBeNull();
    expect(screen.queryByRole("button", { name: "专家工具" })).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "其他操作" }));

    await userEvent.click(screen.getByRole("button", { name: "知识库" }));
    expect(navigate).toHaveBeenCalledWith("knowledge");

    await userEvent.click(screen.getByRole("button", { name: "专家工具" }));
    expect(navigate).toHaveBeenCalledWith("expert");
  });
```

- [ ] **Step 3: Run focused failing workbench tests**

Run:

```bash
npm --prefix frontend test -- --run src/features/workbench/WorkbenchWorkspace.test.tsx
```

Expected: FAIL because the generic no-project CTA still exists and secondary links are always visible.

- [ ] **Step 4: Hide primary button when no project is selected**

In `WorkbenchWorkspace.tsx`, replace the current primary `<Button>` in `.workbench-section-heading` with:

```tsx
          {state.hasProject && (
            <Button
              type="button"
              onClick={() => runPrimaryAction(state, handlers, onNavigate)}
              disabled={isPrimaryActionDisabled(state)}
            >
              {primaryButtonLabel(state)}
              <ArrowRight size={16} aria-hidden="true" />
            </Button>
          )}
```

This keeps the no-project screen driven by the three explicit start cards.

- [ ] **Step 5: Move secondary links into an explicit disclosure**

Replace the visible `workbench-secondary-links` block with:

```tsx
        {state.hasProject && (
          <details className="workbench-other-actions">
            <summary>
              <span>其他操作</span>
              <ArrowRight size={14} aria-hidden="true" />
            </summary>
            <div className="workbench-secondary-links" aria-label="常用工作区">
              <button type="button" onClick={() => onNavigate("documents")}>
                <FileText size={15} aria-hidden="true" />
                <span>文稿与修复</span>
              </button>
              <button type="button" onClick={() => onNavigate("knowledge")}>
                <BookOpen size={15} aria-hidden="true" />
                <span>知识库</span>
              </button>
              <button type="button" onClick={() => onNavigate("expert")}>
                <Gauge size={15} aria-hidden="true" />
                <span>专家工具</span>
              </button>
            </div>
          </details>
        )}
```

- [ ] **Step 6: Keep document route dominant when the primary target is documents**

Because the primary button already shows `进入文稿与修复` for `primaryTarget === "documents"`, no extra document button is needed outside the disclosure. Confirm by reading `primaryButtonLabel(...)` and keeping this branch:

```ts
  if (state.primaryTarget === "documents") return "进入文稿与修复";
```

- [ ] **Step 7: Run workbench tests**

Run:

```bash
npm --prefix frontend test -- --run src/features/workbench/WorkbenchWorkspace.test.tsx src/features/workbench/selectors.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/workbench/WorkbenchWorkspace.tsx frontend/src/features/workbench/WorkbenchWorkspace.test.tsx
git commit -m "fix: reduce workbench routing noise"
```

---

### Task 5: Add Compact Five-Phase Progress Model

**Files:**
- Modify: `frontend/src/features/workbench/selectors.ts`
- Modify: `frontend/src/features/workbench/selectors.test.ts`
- Modify: `frontend/src/features/workbench/WorkbenchWorkspace.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`

**Interfaces:**
- Consumes: existing `GuidedStepState[]`.
- Produces: `WorkbenchState.phaseGroups`, a five-phase user-facing summary that preserves the existing nine-step internal model.

- [ ] **Step 1: Add failing selector test for five phases**

Append this test to `frontend/src/features/workbench/selectors.test.ts`:

```ts
  it("summarizes the nine internal steps into five user-facing phases", () => {
    const state = deriveWorkbenchState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makeProjectPackage() }),
        currentPackage: makeProjectPackage(),
        visiblePatentPoints: [makePatentPoint()],
        currentSourceDraftHash: "draft-hash",
        filingReports: [makeFilingReport("draft-hash")],
        worksheets: [makeWorksheet("draft-hash")],
        completionRuns: [makeCompletionRun("draft-hash")],
        officialCompileRuns: [makeOfficialCompileRun("draft-hash")],
        postDraftReviews: [
          makePostDraftReview({
            status: "completed",
            export_allowed: false,
            blocking_issues: ["说明书仍需补强"],
          }),
        ],
      }),
      exportReadiness: makeExportReadiness({
        review_gate_status: "blocked",
        review_blocking_issues: ["说明书仍需补强"],
      }),
    });

    expect(state.phaseGroups.map((phase) => phase.label)).toEqual([
      "输入",
      "提炼",
      "成稿",
      "质检修复",
      "导出",
    ]);
    expect(state.phaseGroups.find((phase) => phase.label === "质检修复")?.status).toBe("current");
  });
```

- [ ] **Step 2: Run the failing selector test**

Run:

```bash
npm --prefix frontend test -- --run src/features/workbench/selectors.test.ts -t "summarizes the nine internal steps"
```

Expected: FAIL because `phaseGroups` does not exist.

- [ ] **Step 3: Add phase types and mapping**

In `frontend/src/features/workbench/selectors.ts`, add this type near `WorkbenchState`:

```ts
export interface WorkbenchPhase {
  label: "输入" | "提炼" | "成稿" | "质检修复" | "导出";
  status: "done" | "current" | "locked";
  stepIds: GuidedStepId[];
}
```

Add `phaseGroups: WorkbenchPhase[];` to `WorkbenchState`.

Add this helper below `groupGuidedSteps(...)`:

```ts
function groupUserPhases(steps: GuidedStepState[]): WorkbenchPhase[] {
  const phaseDefs: Array<Pick<WorkbenchPhase, "label" | "stepIds">> = [
    { label: "输入", stepIds: ["idea"] },
    { label: "提炼", stepIds: ["invention"] },
    { label: "成稿", stepIds: ["deliberation", "formula", "draft"] },
    { label: "质检修复", stepIds: ["quality", "officialCompile", "postReview"] },
    { label: "导出", stepIds: ["export"] },
  ];

  return phaseDefs.map((phase) => {
    const phaseSteps = steps.filter((step) => phase.stepIds.includes(step.id));
    const status: WorkbenchPhase["status"] = phaseSteps.some((step) => step.status === "current")
      ? "current"
      : phaseSteps.every((step) => step.status === "done")
        ? "done"
        : "locked";
    return { ...phase, status };
  });
}
```

Then set the field in the `deriveWorkbenchState(...)` return object:

```ts
    phaseGroups: groupUserPhases(guidedState.steps),
```

- [ ] **Step 4: Render five-phase progress before detailed groups**

In `WorkbenchWorkspace.tsx`, inside the `workbench-progress` section and before `.workbench-progress-groups`, add:

```tsx
        <ol className="workbench-phase-rail" aria-label="用户流程阶段">
          {state.phaseGroups.map((phase) => (
            <li className={`workbench-phase is-${phase.status}`} key={phase.label}>
              <span>{phase.label}</span>
              <small>{phase.status === "done" ? "已完成" : phase.status === "current" ? "当前阶段" : "未解锁"}</small>
            </li>
          ))}
        </ol>
```

- [ ] **Step 5: Add rendering assertion**

In `WorkbenchWorkspace.test.tsx`, add these assertions to `it("renders the workbench sections, primary action, and no raw internals", ...)`:

```ts
    expect(screen.getByLabelText("用户流程阶段")).toBeInTheDocument();
    expect(screen.getByText("输入")).toBeInTheDocument();
    expect(screen.getByText("质检修复")).toBeInTheDocument();
```

Update `makeState(...)` in the same file to include:

```ts
    phaseGroups: [
      { label: "输入", status: "done", stepIds: ["idea"] },
      { label: "提炼", status: "done", stepIds: ["invention"] },
      { label: "成稿", status: "done", stepIds: ["deliberation", "formula", "draft"] },
      { label: "质检修复", status: "current", stepIds: ["quality", "officialCompile", "postReview"] },
      { label: "导出", status: "locked", stepIds: ["export"] },
    ],
```

- [ ] **Step 6: Run workbench selector and component tests**

Run:

```bash
npm --prefix frontend test -- --run src/features/workbench/selectors.test.ts src/features/workbench/WorkbenchWorkspace.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/workbench/selectors.ts frontend/src/features/workbench/selectors.test.ts frontend/src/features/workbench/WorkbenchWorkspace.tsx frontend/src/features/workbench/WorkbenchWorkspace.test.tsx
git commit -m "feat: add compact workbench phase progress"
```

---

### Task 6: Regression Verification and Evidence

**Files:**
- Create: `qa_runs/ui-flow-repair-2026-06-30/verification.md`
- Create screenshots under: `qa_runs/ui-flow-repair-2026-06-30/screenshots/`

**Interfaces:**
- Consumes: all modified frontend components.
- Produces: local verification record with test commands, screenshot paths, and known limits.

- [ ] **Step 1: Run all affected frontend tests**

Run:

```bash
npm --prefix frontend test -- --run \
  src/features/documentRepair/selectors.test.ts \
  src/features/documentRepair/DocumentRepairWorkspace.test.tsx \
  src/views/exportView.test.tsx \
  src/features/export/ExportWorkspace.test.tsx \
  src/features/workbench/selectors.test.ts \
  src/features/workbench/WorkbenchWorkspace.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS with Vite build output and no TypeScript errors.

- [ ] **Step 3: Start dev servers for visual verification**

Run in terminal 1:

```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Run in terminal 2:

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

Expected:

```text
Uvicorn running on http://127.0.0.1:8000
Local:   http://127.0.0.1:5174/
```

- [ ] **Step 4: Capture visual evidence**

Use the in-app browser or Playwright against `http://127.0.0.1:5174/` and save:

```text
qa_runs/ui-flow-repair-2026-06-30/screenshots/01-workbench-no-project.png
qa_runs/ui-flow-repair-2026-06-30/screenshots/02-workbench-selected-project.png
qa_runs/ui-flow-repair-2026-06-30/screenshots/03-document-repair-quality-required.png
qa_runs/ui-flow-repair-2026-06-30/screenshots/04-export-locked-preview-hidden.png
qa_runs/ui-flow-repair-2026-06-30/screenshots/05-mobile-workbench.png
```

Accepted evidence criteria:

- No-project workbench shows three path cards and no generic `创建项目` primary button.
- Selected-project workbench shows one dominant next action and `其他操作` for secondary routes.
- Document repair quality-required state shows `运行质量检查` as the primary action.
- Export locked state shows unlock guidance and does not expose the long draft preview.
- Mobile/narrow screenshot shows no overlapping topbar, progress, or CTA text.

- [ ] **Step 5: Write verification report**

Create `qa_runs/ui-flow-repair-2026-06-30/verification.md` with this command after all screenshots are accepted:

```bash
mkdir -p qa_runs/ui-flow-repair-2026-06-30
{
  echo "# UI Flow Repair Verification - 2026-06-30"
  echo
  echo "## Source Identity"
  echo
  echo "- Branch: $(git branch --show-current)"
  echo "- HEAD: $(git rev-parse --short HEAD)"
  echo "- Dirty worktree summary:"
  git status --short | sed 's/^/  - /'
  echo
  echo "## Commands"
  echo
  echo "- \`npm --prefix frontend test -- --run src/features/documentRepair/selectors.test.ts src/features/documentRepair/DocumentRepairWorkspace.test.tsx src/views/exportView.test.tsx src/features/export/ExportWorkspace.test.tsx src/features/workbench/selectors.test.ts src/features/workbench/WorkbenchWorkspace.test.tsx\`: PASS"
  echo "- \`npm --prefix frontend run build\`: PASS"
  echo
  echo "## Screenshots"
  echo
  echo "- \`screenshots/01-workbench-no-project.png\`: accepted; no-project workbench shows three path cards and no generic primary create button."
  echo "- \`screenshots/02-workbench-selected-project.png\`: accepted; selected-project workbench shows one dominant next action and secondary routes under other actions."
  echo "- \`screenshots/03-document-repair-quality-required.png\`: accepted; document repair shows run quality checks as the primary action."
  echo "- \`screenshots/04-export-locked-preview-hidden.png\`: accepted; export locked state hides long draft preview."
  echo "- \`screenshots/05-mobile-workbench.png\`: accepted; narrow viewport has no overlapping topbar, progress, or CTA text."
  echo
  echo "## Result"
  echo
  echo "- Workbench primary action: aligned to the current recommended next action."
  echo "- Document repair source-of-truth alignment: export-readiness controls gates and primary action."
  echo "- Export locked preview behavior: long package preview remains hidden until official export unlocks."
  echo "- Remaining risks: none found in this verification run."
} > qa_runs/ui-flow-repair-2026-06-30/verification.md
```

If any command or screenshot criterion fails, stop this step, fix the failing task, and rerun Step 1 through Step 5.

- [ ] **Step 6: Stop dev servers**

Stop the dev servers started in Step 3. Confirm:

```bash
lsof -iTCP:8000 -sTCP:LISTEN -n -P || true
lsof -iTCP:5174 -sTCP:LISTEN -n -P || true
```

Expected: no listening process for either port unless the user already had a separate server running before this task.

- [ ] **Step 7: Commit**

```bash
git add qa_runs/ui-flow-repair-2026-06-30
git commit -m "test: record ui flow repair verification"
```

---

## Self-Review

Spec coverage:

- P0 document repair gate derivation: Task 1.
- P0 document repair primary action: Tasks 1 and 2.
- P0 export locked preview behavior: Task 3.
- P1 workbench secondary action noise and no-project CTA: Task 4.
- P2 five-phase progress: Task 5.
- P2 screenshot and narrow-window checks: Task 6.

Placeholder scan:

- No forbidden placeholder tokens from the planning skill are present.
- Every code-changing step includes exact code to add or replace.
- Every test step includes exact command and expected result.

Type consistency:

- `ExportReadiness.next_action` values match `frontend/src/api.ts`.
- `DocumentRepairState["primaryAction"]` return shape matches existing selector types.
- `WorkbenchPhase.status` uses local `done | current | locked` and does not alter `GuidedStepStatus`.
