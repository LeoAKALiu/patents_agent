# PatentAgent UI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the PatentAgent production UI around a current-project workbench, a full document-and-repair workspace, clear top-level navigation, consolidated status, and a restrained liquid-glass shell.

**Architecture:** Keep the existing React/Tauri data flow in `App.tsx`, but move product navigation and page composition into focused feature workspaces under `frontend/src/features/`. Reuse the existing guided-flow, export, corpus, post-draft review, and annotated repair data paths; do not replace proven backend/API wiring while restructuring the UI.

**Tech Stack:** React 19, Vite 7, TypeScript 5.9, TanStack React Query, shadcn/Radix primitives, lucide-react, Vitest, Testing Library, Tauri desktop shell.

## Global Constraints

- Source identity at plan capture: branch `codex/automation-test-plan`, short SHA `efd94397`, worktree `/Users/leo/Projects/patents_agent`, dirty worktree `true`.
- Production UI evidence must come from `frontend/src/`, `src-tauri/`, and the actual running app.
- `docs/ui-redesign/04-workbench-document-repair-spec.md` is the product spec, not implementation proof.
- Left sidebar top-level navigation must be: `工作台`, `项目`, `文稿与修复`, `知识库`, `专家工具`, `导出`, `设置`.
- `知识库` and `导出` remain top-level destinations.
- The 9 guided steps remain part of the product model, but not global navigation.
- Do not expose raw JSON, run IDs, full hashes, or logs by default.
- Official submission materials and internal review/strategy materials must be visually distinct.
- Liquid glass is allowed on shell chrome, chips, drawers, overlays, and compact status surfaces; dense document, editor, issue, and risk surfaces stay solid and readable.
- Do not revert unrelated dirty files. Current unrelated dirty files include backend, tests, QA docs, and `.superpowers/sdd` reports.

---

## File Structure

Planned source changes:

- `frontend/src/guidedFlow.ts`
  - Owns global nav ids, labels, guided step groups, compatibility helpers, and next-action labels.
- `frontend/src/app/routes.tsx`
  - Maps `MainSectionId` to route kinds for shell rendering.
- `frontend/src/app/AppRoot.tsx`
  - Composes shell chrome and routes to feature workspaces.
- `frontend/src/app/ShellLayout.tsx`
  - Keeps sidebar/topbar/workspace layout.
- `frontend/src/App.tsx`
  - Keeps app state, persistence, API handlers, and native menu integration.
- `frontend/src/ui/ShellSidebar.tsx`
  - Destination-only sidebar and compact footer slot.
- `frontend/src/ui/ShellTopbar.tsx`
  - Project selector, run/export/backend status chips, refresh action, and optional diagnostic trigger.
- `frontend/src/ui/SystemStatusPanel.tsx`
  - Compact health summary plus diagnostic drawer trigger.
- `frontend/src/features/workbench/WorkbenchWorkspace.tsx`
  - Default current-project command center.
- `frontend/src/features/workbench/selectors.ts`
  - Pure derivations for current project state, next action, risk summary, and 9-step grouping.
- `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
  - Tabs: `总览`, `编辑`, `问题`, `标注修复`, `版本`.
- `frontend/src/features/documentRepair/selectors.ts`
  - Pure derivations for gate chain, issue inbox, version chain, stale state, and document status.
- `frontend/src/features/documentRepair/DocumentEditTab.tsx`
  - Section-level internal draft editing.
- `frontend/src/features/documentRepair/DocumentIssuesTab.tsx`
  - Filterable issue inbox.
- `frontend/src/features/documentRepair/DocumentOverviewTab.tsx`
  - Export lock explanation, gate chain, draft status cards, and top issues.
- `frontend/src/features/documentRepair/DocumentVersionsTab.tsx`
  - Internal draft, official draft, review, export version chain.
- `frontend/src/features/documentRepair/AnnotatedRepairTab.tsx`
  - In-workspace entry for the existing annotated repair editor flow.
- `frontend/src/features/knowledge/KnowledgeWorkspace.tsx`
  - Top-level knowledge route wrapper around corpus build/search.
- `frontend/src/features/export/ExportWorkspace.tsx`
  - Top-level export route wrapper around `ExportView`.
- `frontend/src/features/expert/ExpertToolsWorkspace.tsx`
  - Low-frequency expert tool grouping without competing with normal flow.
- `frontend/src/styles.css`
  - Layout, responsive, workbench, document-repair, export, and expert workspace styles.
- `frontend/src/styles/tokens.css`
  - Token adjustments only if needed for shell/chip/readability consistency.
- `frontend/src/styles/glass.css`
  - Glass tier reuse; avoid broad new glass effects.

Planned tests:

- `frontend/src/guidedFlow.test.ts`
- `frontend/src/domain.test.ts`
- `frontend/src/AppStateRecovery.test.ts`
- `frontend/src/app/routes.test.tsx`
- `frontend/src/features/workbench/selectors.test.ts`
- `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`
- `frontend/src/features/documentRepair/selectors.test.ts`
- `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- `frontend/src/PostDraftRepairEditor.test.tsx`
- `frontend/src/views/exportView.test.tsx`

---

## Task 1: Navigation Model And Persisted-State Migration

**Files:**
- Modify: `frontend/src/guidedFlow.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/guidedFlow.test.ts`
- Modify: `frontend/src/domain.test.ts`
- Modify: `frontend/src/AppStateRecovery.test.ts`

**Interfaces:**
- Produces: `MainSectionId = "workbench" | "projects" | "documents" | "knowledge" | "expert" | "export" | "settings"`
- Produces: `mainSections` with labels `工作台`, `项目`, `文稿与修复`, `知识库`, `专家工具`, `导出`, `设置`
- Produces: `defaultMainSectionId = "workbench"`
- Produces: `normalizeMainSectionId(value: unknown, activeExpertTool?: ExpertToolId): MainSectionId`
- Consumes: existing `ExpertToolId`, `expertToolGroups`, and localStorage state in `App.tsx`

- [ ] **Step 1: Add failing tests for the new top-level nav**

Update `frontend/src/guidedFlow.test.ts` navigation expectations:

```ts
expect(mainSections.map((item) => item.label)).toEqual([
  "工作台",
  "项目",
  "文稿与修复",
  "知识库",
  "专家工具",
  "导出",
  "设置",
]);
expect(defaultMainSectionId).toBe("workbench");
expect(normalizeMainSectionId("generate")).toBe("workbench");
expect(normalizeMainSectionId("utility")).toBe("workbench");
expect(normalizeMainSectionId("expert", "build")).toBe("knowledge");
expect(normalizeMainSectionId("expert", "corpus")).toBe("knowledge");
expect(normalizeMainSectionId("expert", "export")).toBe("export");
expect(normalizeMainSectionId("expert", "moat")).toBe("expert");
```

Update `frontend/src/domain.test.ts` to expect the same top-level labels.

- [ ] **Step 2: Add failing persisted-state migration tests**

Update `frontend/src/AppStateRecovery.test.ts`:

```ts
expect(
  sanitizePersistedAppState({
    selectedProjectId: "p-1",
    activeSection: "generate",
    activeExpertTool: "materials",
    startChoice: "external",
    disclosureResearchMode: "standard",
  }),
).toEqual({
  selectedProjectId: "p-1",
  activeSection: "workbench",
  activeExpertTool: "materials",
  startChoice: "external",
  disclosureResearchMode: "standard",
});

expect(
  sanitizePersistedAppState({
    selectedProjectId: "p-1",
    activeSection: "expert",
    activeExpertTool: "export",
    startChoice: null,
    disclosureResearchMode: "standard",
  }),
).toEqual({
  selectedProjectId: "p-1",
  activeSection: "export",
  activeExpertTool: "export",
  startChoice: null,
  disclosureResearchMode: "standard",
});
```

- [ ] **Step 3: Run the failing tests**

Run:

```bash
cd frontend && npm test -- guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts
```

Expected: failures on old labels/default section and missing `normalizeMainSectionId`.

- [ ] **Step 4: Implement the navigation model**

In `frontend/src/guidedFlow.ts`, change `MainSectionId`, `defaultMainSectionId`, and `mainSections`.

Implement:

```ts
export function normalizeMainSectionId(
  value: unknown,
  activeExpertTool: ExpertToolId = defaultExpertToolId,
): MainSectionId {
  if (value === "workbench" || value === "projects" || value === "documents" ||
      value === "knowledge" || value === "expert" || value === "export" ||
      value === "settings") {
    return value;
  }
  if (value === "generate" || value === "utility") return "workbench";
  if (value === "expert") {
    if (activeExpertTool === "build" || activeExpertTool === "corpus") return "knowledge";
    if (activeExpertTool === "export") return "export";
    return "expert";
  }
  return defaultMainSectionId;
}
```

In `frontend/src/App.tsx`, replace the hard-coded `validMainSectionIds` branch inside `sanitizePersistedAppState` with `normalizeMainSectionId(record.activeSection, activeExpertTool)`.

Update `handleStartChoice()` and `returnToStartChoices()` to call `setActiveSection("workbench")`.

Update `openExpertTool()`:

```ts
function openExpertTool(tool: ExpertToolId) {
  setActiveExpertTool(tool);
  if (tool === "build" || tool === "corpus") {
    setActiveSection("knowledge");
  } else if (tool === "export") {
    setActiveSection("export");
  } else {
    setActiveSection("expert");
  }
}
```

Update native menu actions:

- import draft actions set `activeSection` to `expert` and tool `materials`
- export actions set `activeSection` to `export` and tool `export`

- [ ] **Step 5: Run targeted tests**

Run:

```bash
cd frontend && npm test -- guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts
```

Expected: all targeted tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/guidedFlow.ts frontend/src/App.tsx frontend/src/guidedFlow.test.ts frontend/src/domain.test.ts frontend/src/AppStateRecovery.test.ts
git commit -m "refactor(ui): define top-level navigation model"
```

---

## Task 2: Route Mapping And Shell Chrome

**Files:**
- Modify: `frontend/src/app/routes.tsx`
- Modify: `frontend/src/app/AppRoot.tsx`
- Modify: `frontend/src/app/ShellLayout.tsx`
- Modify: `frontend/src/ui/ShellSidebar.tsx`
- Modify: `frontend/src/ui/ShellTopbar.tsx`
- Modify: `frontend/src/ui/SystemStatusPanel.tsx`
- Modify: `frontend/src/app/routes.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: new `MainSectionId`
- Produces: `RouteKind = "workbench" | "projects-overview" | "documents" | "knowledge" | "expert" | "export" | "settings"`
- Produces: shell sidebar with destination-only nav
- Produces: topbar status chips for run, export, and backend

- [ ] **Step 1: Add failing route tests**

Update `frontend/src/app/routes.test.tsx`:

```ts
expect(resolveRoute("workbench", "build", false, false)).toBe("workbench");
expect(resolveRoute("documents", "review", true, false)).toBe("documents");
expect(resolveRoute("knowledge", "corpus", true, false)).toBe("knowledge");
expect(resolveRoute("export", "export", true, false)).toBe("export");
expect(resolveRoute("expert", "moat", true, false)).toBe("expert");
expect(resolveRoute("settings", "build", false, false)).toBe("settings");
```

Update the shell rendering test to expect all seven sidebar labels.

- [ ] **Step 2: Run the failing route tests**

Run:

```bash
cd frontend && npm test -- app/routes.test.tsx
```

Expected: old route kinds and old sidebar labels fail.

- [ ] **Step 3: Implement route mapping**

In `frontend/src/app/routes.tsx`, make `resolveRoute()` return:

```ts
if (activeSection === "projects") return "projects-overview";
if (activeSection === "documents") return "documents";
if (activeSection === "knowledge") return "knowledge";
if (activeSection === "expert") return "expert";
if (activeSection === "export") return "export";
if (activeSection === "settings") return "settings";
return "workbench";
```

Keep `classifyExpertTool()` because existing expert-tool routing still needs it.

- [ ] **Step 4: Implement shell composition without page blanks**

In `frontend/src/app/AppRoot.tsx`:

- Remove the old `keySections` sidebar block.
- Remove `topbarActions()` returning `专家工具` / `返回向导` as topbar navigation.
- Keep `返回三选一` only when it is relevant to workbench start-choice recovery.
- Render these temporary route targets until later tasks replace them:
  - `workbench`: existing `ProjectWorkspace` guided/start flow
  - `projects-overview`: existing project overview
  - `knowledge`: `CorpusWorkspace` with tool `build` or `corpus`
  - `expert`: `ExpertToolChooser` plus classified expert workspace
  - `export`: `PostDraftWorkspace` with tool `export`
  - `documents`: a new thin document-repair entry shell created in Task 4; until Task 4 lands, keep this task behind its branch and do not merge

- [ ] **Step 5: Consolidate chrome status**

In `ShellTopbar`, add props:

```ts
backendStatus?: "unknown" | "online" | "offline";
exportStatusLabel?: string;
exportStatusVariant?: "idle" | "busy" | "error" | "success" | "warning";
onOpenDiagnostics?: () => void;
```

Render chips in this order:

```text
[project selector] [export status] [run status] [backend status icon] [refresh]
```

Use icons from `lucide-react` and existing `Button`.

- [ ] **Step 6: Compact system health**

In `SystemStatusPanel`, reduce default sidebar footprint to three compact rows:

```text
模型 可用/未配置/离线
智能体 可用/部分可用/离线
后端 在线/离线/检测中
```

Detailed diagnostics should be available through a drawer/modal trigger, not expanded by default.

- [ ] **Step 7: Run targeted tests**

Run:

```bash
cd frontend && npm test -- app/routes.test.tsx
```

Expected: route and shell tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/app/routes.tsx frontend/src/app/AppRoot.tsx frontend/src/app/ShellLayout.tsx frontend/src/ui/ShellSidebar.tsx frontend/src/ui/ShellTopbar.tsx frontend/src/ui/SystemStatusPanel.tsx frontend/src/app/routes.test.tsx frontend/src/styles.css
git commit -m "refactor(ui): consolidate shell navigation and status"
```

---

## Task 3: Workbench Workspace

**Files:**
- Create: `frontend/src/features/workbench/selectors.ts`
- Create: `frontend/src/features/workbench/WorkbenchWorkspace.tsx`
- Create: `frontend/src/features/workbench/selectors.test.ts`
- Create: `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`
- Modify: `frontend/src/app/AppRoot.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `ProjectWorkspaceState`, `ProjectWorkspaceHandlers`, `deriveGuidedFlowState`
- Produces: `deriveWorkbenchState(input): WorkbenchState`
- Produces: `WorkbenchWorkspace`

- [ ] **Step 1: Add selector tests**

Create `frontend/src/features/workbench/selectors.test.ts` with cases:

```ts
expect(state.nextAction.label).toBe("创建项目");
expect(state.primaryTarget).toBe("workbench-start");

expect(blockedState.nextAction.label).toBe("处理成稿会审阻断项");
expect(blockedState.primaryTarget).toBe("documents");

expect(exportReadyState.nextAction.label).toBe("导出正式稿");
expect(exportReadyState.primaryTarget).toBe("export");
```

- [ ] **Step 2: Implement `deriveWorkbenchState`**

Create a pure selector that returns:

```ts
export type WorkbenchPrimaryTarget =
  | "workbench-start"
  | "documents"
  | "knowledge"
  | "expert"
  | "export";

export interface WorkbenchState {
  hasProject: boolean;
  projectName: string;
  currentStepId: GuidedStepId;
  stepGroups: Array<{ label: string; steps: GuidedStepState[] }>;
  nextAction: { label: string; description: string };
  primaryTarget: WorkbenchPrimaryTarget;
  riskSummary: {
    blockingCount: number;
    issueCount: number;
    exportLocked: boolean;
    exportReady: boolean;
  };
  runSummary: { label: string; busy: boolean };
}
```

Rules:

- no project: primary target `workbench-start`, label `创建项目`
- blocked post-draft review: primary target `documents`, label `处理成稿会审阻断项`
- export ready: primary target `export`, label `导出正式稿`
- current step before draft: primary target `workbench-start`, label from `guidedNextActionLabel`
- running busy state: run summary uses `guidedBusyLabel(busy)`

- [ ] **Step 3: Add component test**

Create `WorkbenchWorkspace.test.tsx`:

```ts
render(<WorkbenchWorkspace state={state} handlers={handlers} onNavigate={navigate} />);
expect(screen.getByRole("heading", { name: "工作台" })).toBeTruthy();
expect(screen.getByText("下一步")).toBeTruthy();
expect(screen.getByRole("button", { name: /进入文稿与修复|创建项目|导出正式稿/ })).toBeTruthy();
expect(screen.queryByText(/generation_logs|official_safe_patches/)).toBeNull();
```

- [ ] **Step 4: Implement `WorkbenchWorkspace`**

Use four sections:

```text
当前项目
下一步
流程进度
风险与运行
```

For no-project state, embed the existing `StartChoiceScreen` through `ProjectWorkspace` behavior or call `handlers.onStartChoice` directly from three start cards.

For a selected project, render one primary button and compact secondary links.

- [ ] **Step 5: Wire workbench route**

In `AppRoot`, route `"workbench"` to `WorkbenchWorkspace`.

Pass `onNavigate` that maps:

- `documents` -> `onSelectSection("documents")`
- `export` -> `onSelectSection("export")`
- `knowledge` -> `onSelectSection("knowledge")`
- `expert` -> `onSelectSection("expert")`

- [ ] **Step 6: Run tests**

Run:

```bash
cd frontend && npm test -- features/workbench/selectors.test.ts features/workbench/WorkbenchWorkspace.test.tsx app/routes.test.tsx
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/workbench frontend/src/app/AppRoot.tsx frontend/src/styles.css
git commit -m "feat(ui): add current project workbench"
```

---

## Task 4: Document And Repair Overview Route

**Files:**
- Create: `frontend/src/features/documentRepair/selectors.ts`
- Create: `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
- Create: `frontend/src/features/documentRepair/DocumentOverviewTab.tsx`
- Create: `frontend/src/features/documentRepair/selectors.test.ts`
- Create: `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- Modify: `frontend/src/app/AppRoot.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `ProjectWorkspaceState`, `ProjectWorkspaceHandlers`
- Produces: `deriveDocumentRepairState(input): DocumentRepairState`
- Produces: `DocumentRepairWorkspace` tabs: `overview`, `edit`, `issues`, `annotated`, `versions`

- [ ] **Step 1: Add selector tests for gate state**

Test these cases:

```ts
expect(noDraft.topConclusion).toBe("当前项目尚未生成内部初稿。");
expect(blocked.topConclusion).toContain("阻断导出");
expect(blocked.primaryAction.targetTab).toBe("annotated");
expect(staleOfficial.gates.officialCompile.state).toBe("已失效");
expect(exportReady.primaryAction.label).toBe("导出正式稿");
```

- [ ] **Step 2: Implement document-repair selectors**

Return:

```ts
export interface DocumentRepairState {
  activeTab: "overview" | "edit" | "issues" | "annotated" | "versions";
  topConclusion: string;
  primaryAction: { label: string; targetTab?: DocumentRepairTabId; targetSection?: MainSectionId };
  gates: {
    internalDraft: GateNode;
    quality: GateNode;
    officialCompile: GateNode;
    postDraftReview: GateNode;
    export: GateNode;
  };
  internalDraft: DraftStatusCardState;
  officialDraft: DraftStatusCardState;
  issueSummary: IssueSummaryState;
}
```

Gate labels must use approved vocabulary from the spec: `可编辑`, `当前有效`, `已失效`, `需要修复`, `待重新验证`, `导出锁定`, `可导出`, `运行中`, `等待生成`, `运行失败`.

- [ ] **Step 3: Implement overview tab**

`DocumentOverviewTab` renders:

```text
top conclusion
primary action
gate chain
内部初稿 card
正式稿 card
issue summary
recent records
```

Do not render raw JSON, full hashes, or logs. Short hashes may be shown only behind `<details>`.

- [ ] **Step 4: Implement workspace shell**

`DocumentRepairWorkspace` owns tab state and renders tab buttons:

```text
总览 编辑 问题 标注修复 版本
```

At this task, non-overview tabs can render their real heading and a disabled state that routes users back to overview. Do not merge this task as complete UI until Tasks 5 and 6 fill the tabs.

- [ ] **Step 5: Wire `documents` route**

In `AppRoot`, route `"documents"` to `DocumentRepairWorkspace`.

The topbar title for `documents` is:

```text
文稿与修复
处理当前项目的正文、问题和版本链路
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd frontend && npm test -- features/documentRepair/selectors.test.ts features/documentRepair/DocumentRepairWorkspace.test.tsx app/routes.test.tsx
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/documentRepair frontend/src/app/AppRoot.tsx frontend/src/styles.css
git commit -m "feat(ui): add document repair overview workspace"
```

---

## Task 5: Document Edit, Issues, And Versions Tabs

**Files:**
- Create: `frontend/src/features/documentRepair/DocumentEditTab.tsx`
- Create: `frontend/src/features/documentRepair/DocumentIssuesTab.tsx`
- Create: `frontend/src/features/documentRepair/DocumentVersionsTab.tsx`
- Modify: `frontend/src/features/documentRepair/selectors.ts`
- Modify: `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
- Modify: `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `onSaveDraftPackage`, `currentPackage`, `currentDraftHash`, `currentSourceDraftHash`, `officialCompileRuns`, `postDraftReviews`
- Produces: section-level editor and issue/version views

- [ ] **Step 1: Add edit tab tests**

Test:

```ts
await userEvent.click(screen.getByRole("tab", { name: "编辑" }));
expect(screen.getByLabelText("标题")).toBeTruthy();
await userEvent.clear(screen.getByLabelText("标题"));
await userEvent.type(screen.getByLabelText("标题"), "新标题");
await userEvent.click(screen.getByRole("button", { name: "保存当前初稿" }));
expect(onSaveDraftPackage).toHaveBeenCalledWith(expect.objectContaining({ title: "新标题" }));
```

- [ ] **Step 2: Implement edit tab**

Use section-level editing only for the first implementation:

```text
标题
摘要
权利要求书
说明书
附图说明
```

Saving must display this consequence:

```text
保存后旧正式稿、旧成稿会审和旧导出状态将失效，需要重新编译正式稿并重新成稿会审。
```

- [ ] **Step 3: Add issues tab tests**

Test filters:

```ts
await userEvent.click(screen.getByRole("tab", { name: "问题" }));
expect(screen.getByText("阻断")).toBeTruthy();
await userEvent.click(screen.getByRole("button", { name: "只看阻断" }));
expect(screen.queryByText("建议")).toBeNull();
```

- [ ] **Step 4: Implement issues tab**

Use sources:

- post-draft review blocking issues
- contamination hits
- role rewrite suggestions
- chair description rewrite tasks
- chair next actions
- quality check issue/task counts

Each issue row shows:

```text
severity/kind, source, target section, short message, state
```

Issue states:

- `open`
- `applied`
- `pending_revalidation`
- `resolved_by_new_review`
- `dismissed`

If persisted state does not yet exist, derive row state from current data and label it `open` or `pending_revalidation`.

- [ ] **Step 5: Add versions tab tests**

Test:

```ts
await userEvent.click(screen.getByRole("tab", { name: "版本" }));
expect(screen.getByText("内部初稿")).toBeTruthy();
expect(screen.getByText("正式稿")).toBeTruthy();
expect(screen.getByText("成稿会审")).toBeTruthy();
expect(screen.getByText(/当前有效|已失效|等待生成/)).toBeTruthy();
```

- [ ] **Step 6: Implement versions tab**

Show compact version chain:

```text
内部初稿 -> 质量检查 -> 正式稿 -> 成稿会审 -> 导出
```

Full hashes go inside `<details>`.

- [ ] **Step 7: Run tests**

Run:

```bash
cd frontend && npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx features/documentRepair/selectors.test.ts
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/documentRepair frontend/src/styles.css
git commit -m "feat(ui): add document edit issues and versions tabs"
```

---

## Task 6: Annotated Repair As A First-Class Workspace Tab

**Files:**
- Create: `frontend/src/features/documentRepair/AnnotatedRepairTab.tsx`
- Modify: `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
- Modify: `frontend/src/flow/panels/PostDraftRepairEditor.tsx`
- Modify: `frontend/src/flow/panels/PostDraftIssueRail.tsx`
- Modify: `frontend/src/flow/panels/DraftRepairInspector.tsx`
- Modify: `frontend/src/PostDraftRepairEditor.test.tsx`
- Modify: `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `getPostDraftRepairSession`, `createDraftRepairPatch`, `applyDraftRepairPatch`
- Produces: in-workspace annotated repair tab while preserving modal-compatible editor behavior if still needed by old flows

- [ ] **Step 1: Add workspace repair tests**

Test:

```ts
await userEvent.click(screen.getByRole("tab", { name: "标注修复" }));
expect(screen.getByText("问题队列")).toBeTruthy();
expect(screen.getByText("正文定位")).toBeTruthy();
expect(screen.getByText("修复面板")).toBeTruthy();
```

Existing regression requirements remain:

- non-empty repair session issues render
- draft sections render
- selecting issue updates highlighted section and inspector
- long issue list scrolls independently

- [ ] **Step 2: Refactor editor shell for embedded mode**

Add prop to `PostDraftRepairEditor`:

```ts
mode?: "modal" | "embedded";
```

Behavior:

- `modal`: current overlay behavior
- `embedded`: no fixed overlay, no dialog backdrop, fills parent grid

Keep existing tests passing by defaulting `mode` to `"modal"`.

- [ ] **Step 3: Implement `AnnotatedRepairTab`**

Responsibilities:

- load repair session for selected project and repairable review
- show loading and error states
- pass session to `PostDraftRepairEditor mode="embedded"`
- save through `onSaveDraftPackage`
- after patch application, mark issue as `pending_revalidation` in local display copy

- [ ] **Step 4: Adjust responsive layout**

Desktop:

```text
left issue queue | middle document body | right inspector
```

Mobile:

```text
stage 1 issue queue -> stage 2 document -> stage 3 inspector
```

No forced three-column layout below `920px`.

- [ ] **Step 5: Run tests**

Run:

```bash
cd frontend && npm test -- PostDraftRepairEditor.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/documentRepair/AnnotatedRepairTab.tsx frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx frontend/src/flow/panels/PostDraftRepairEditor.tsx frontend/src/flow/panels/PostDraftIssueRail.tsx frontend/src/flow/panels/DraftRepairInspector.tsx frontend/src/PostDraftRepairEditor.test.tsx frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx frontend/src/styles.css
git commit -m "feat(ui): embed annotated repair in document workspace"
```

---

## Task 7: Knowledge, Export, And Expert Tool Reframing

**Files:**
- Create: `frontend/src/features/knowledge/KnowledgeWorkspace.tsx`
- Create: `frontend/src/features/export/ExportWorkspace.tsx`
- Create: `frontend/src/features/expert/ExpertToolsWorkspace.tsx`
- Modify: `frontend/src/app/AppRoot.tsx`
- Modify: `frontend/src/views/exportView.tsx`
- Modify: `frontend/src/views/exportView.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: existing `CorpusWorkspace`, `ExportView`, `ExpertToolChooser`, `QualityWorkspace`, `PostDraftWorkspace`
- Produces: top-level knowledge/export pages and lower-priority expert tools

- [ ] **Step 1: Implement knowledge wrapper**

`KnowledgeWorkspace` shows:

```text
语料库建设
知识库检索
```

It uses existing `CorpusWorkspace` tools `build` and `corpus`, with tabs or segmented control.

- [ ] **Step 2: Implement export wrapper**

`ExportWorkspace` wraps `ExportView` and enforces three visual sections:

```text
正式提交稿
内部复核材料
风险说明与追溯
```

Locked export must link back to `文稿与修复 / 总览` or `文稿与修复 / 标注修复`, not show repair UI inline.

- [ ] **Step 3: Update export tests**

Add assertions:

```ts
expect(screen.getByText("正式提交稿")).toBeTruthy();
expect(screen.getByText("内部复核材料")).toBeTruthy();
expect(screen.getByText("风险说明与追溯")).toBeTruthy();
expect(screen.queryByText("人工修正")).toBeNull();
expect(screen.queryByText("一键AI修正")).toBeNull();
```

- [ ] **Step 4: Implement expert tools wrapper**

`ExpertToolsWorkspace` groups advanced tools by current `expertToolGroups`, but copy must say these are advanced tools. Do not make expert tools the default path for normal repair/export workflow.

- [ ] **Step 5: Wire routes**

In `AppRoot`:

- `knowledge` -> `KnowledgeWorkspace`
- `export` -> `ExportWorkspace`
- `expert` -> `ExpertToolsWorkspace`

- [ ] **Step 6: Run tests**

Run:

```bash
cd frontend && npm test -- views/exportView.test.tsx app/routes.test.tsx
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/knowledge frontend/src/features/export frontend/src/features/expert frontend/src/app/AppRoot.tsx frontend/src/views/exportView.tsx frontend/src/views/exportView.test.tsx frontend/src/styles.css
git commit -m "feat(ui): promote knowledge and export workspaces"
```

---

## Task 8: Visual System, Responsive QA, And Running-App Evidence

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/glass.css`
- Optional create: `docs/ui-redesign/evidence/2026-06-29-ui-refactor-smoke.md`

**Interfaces:**
- Consumes: all completed UI workspaces
- Produces: consistent shell, glass, spacing, typography, responsive behavior, and evidence notes

- [ ] **Step 1: Apply visual rules**

CSS rules:

- sidebar and topbar use `.glass-strong`-like treatment or equivalent tokenized glass
- status chips use compact glass/solid variants
- document editor, issue table, repair document body, export file sections use solid readable surfaces
- no gradient orbs, decorative blobs, one-hue palette, or oversized hero layout
- no nested cards inside cards
- no font scaling with viewport width
- letter spacing remains `0`

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 3: Run full frontend tests**

Run:

```bash
cd frontend && npm test
```

Expected: all frontend tests pass.

- [ ] **Step 4: Start dev server**

Run:

```bash
cd frontend && npm run dev -- --port 5173
```

Expected: Vite serves at `http://127.0.0.1:5173/`.

- [ ] **Step 5: Browser smoke**

Verify at desktop width and mobile width:

- sidebar has seven top-level destinations
- mobile nav does not overflow
- workbench shows one primary action
- document-repair tabs are visible
- annotated repair long issue list scrolls inside its pane
- export page separates official/internal/trace materials
- no visible horizontal overflow
- no button text overlap

- [ ] **Step 6: Tauri running-app evidence before handoff**

If packaging or installed-app handoff is requested, follow:

- `docs/release/dmg-ui-regression-guard.md`
- `docs/release/v1.1.0-tauri-release-gate.md`
- `docs/release/v1.1.0-tauri-packaging.md`

Do not claim packaged UI completion from dev-server evidence.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/styles.css frontend/src/styles/tokens.css frontend/src/styles/glass.css docs/ui-redesign/evidence/2026-06-29-ui-refactor-smoke.md
git commit -m "style(ui): unify refactored shell and workspace visuals"
```

---

## Execution Notes

- Use a fresh branch or worktree before implementation if current dirty backend/test changes are unrelated to this UI refactor.
- Recommended first execution slice is Tasks 1-3 only. That gets navigation, shell, and workbench in place without touching the heavy document editor.
- Do not merge Task 2 alone if `documents` opens a blank or disabled-only page. Ship the sidebar switch with at least Task 4 overview available.
- Keep `PostDraftRepairEditor` data flow intact until Task 6; regression risk is mostly layout/state wiring, not backend repair API behavior.
- Avoid moving backend endpoints or changing repair-session payloads in this UI refactor.

## Self-Review

Spec coverage:

- Main navigation: Tasks 1-2.
- Status consolidation: Task 2.
- 9-step redesign inside workbench: Task 3.
- Clear function zones: Tasks 3-7.
- Document and repair workspace: Tasks 4-6.
- Export separation: Task 7.
- Liquid glass constraints: Task 8.
- Running-app evidence: Task 8.

Known gaps intentionally deferred:

- Persisted issue-history as first-class backend data is not in this plan; Task 5 derives state from existing reports and patch events first.
- Paragraph-level editing is not in the first implementation; Task 5 starts with section-level editing.
- Full hash display defaults to collapsed details; Task 5 handles version details with `<details>`.

Plan red-flag scan:

- No unfinished implementation tasks.
- Every task has exact files, commands, and acceptance.
- Route and nav types are defined before components consume them.

## Execution Handoff

Plan complete. Use one of these execution modes:

1. **Subagent-Driven (recommended)** - one fresh worker per task, review between tasks, lower merge risk.
2. **Inline Execution** - execute tasks in this session with checkpoints after each task.
