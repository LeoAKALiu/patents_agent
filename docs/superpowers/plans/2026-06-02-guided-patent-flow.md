# Guided Patent Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 12-tab workbench as the default experience with a guided patent-generation flow that starts from one idea paragraph, pauses at invention-point confirmation and export-risk confirmation, and keeps existing expert tools available.

**Architecture:** Build a frontend-first orchestration layer that derives workflow state from existing project, disclosure, draft, quality, and export data. Keep existing FastAPI endpoints and quality engines unchanged for the first implementation pass. Add focused React components for guided intake, invention confirmation, quality summary, export confirmation, and expert-tool routing while preserving old views behind `专家工具`.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, FastAPI existing endpoints, SQLite existing persistence.

---

## Current Constraints

- The confirmed spec is `docs/superpowers/specs/2026-06-02-guided-patent-flow-design.md`.
- Existing frontend routing is local state in `frontend/src/App.tsx`; there is no router package.
- Existing tab definitions live in `frontend/src/domain.ts`.
- Existing API helpers in `frontend/src/api.ts` are sufficient for v0.5 first pass.
- The app has Vitest domain tests but no React component testing library. Use helper-level tests plus `npm run build` and browser smoke testing.
- Preserve warning-mode export: high risk can warn but must not hard-block official export links.
- Preserve expert access to all old modules.

## File Structure

- Create `frontend/src/guidedFlow.ts`: workflow types, main navigation entries, expert tool entries, status derivation, labels, and quality summary helpers.
- Create `frontend/src/guidedFlow.test.ts`: helper tests for navigation shape, step derivation, quality summary, and export readiness.
- Modify `frontend/src/domain.ts`: keep patent-domain labels, remove the old 12-tab `workspaceTabs` responsibility or re-export expert tool metadata from `guidedFlow.ts`.
- Modify `frontend/src/domain.test.ts`: update old tab-order test to the new three-entry main navigation and expert tool grouping.
- Create `frontend/src/GuidedPatentFlow.tsx`: guided patent generation page and subcomponents.
- Modify `frontend/src/App.tsx`: replace default `activeTab` shell with `activeSection` and `activeExpertTool`, add guided action handlers, and route old views under expert tools.
- Modify `frontend/src/styles.css`: add guided-flow layout, stepper, intake, confirmation, quality, export, and expert-tool styles.
- Modify `README.md`: document the new default `专利生成` workflow and the location of expert tools.

---

### Task 1: Add Guided Flow Domain Model

**Files:**
- Create: `frontend/src/guidedFlow.ts`
- Create: `frontend/src/guidedFlow.test.ts`
- Modify: `frontend/src/domain.ts`
- Modify: `frontend/src/domain.test.ts`

- [ ] **Step 1: Write failing guided-flow helper tests**

Create `frontend/src/guidedFlow.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import type {
  ClaimDefenseWorksheet,
  DisclosureRun,
  DraftCompletionRun,
  FilingReadinessReport,
  ProjectMaterial,
  ProjectRecord,
} from "./api";
import {
  deriveGuidedFlowState,
  expertToolGroups,
  guidedStepLabels,
  mainSections,
  qualitySummaryFromRuns,
} from "./guidedFlow";

const projectWithIdea: ProjectRecord = {
  id: "p1",
  name: "外立面逆建模",
  draft_text: "一种外立面逆建模方法。",
  package: null,
  created_at: "2026-06-02T00:00:00Z",
  updated_at: "2026-06-02T00:00:00Z",
};

const processedMaterial: ProjectMaterial = {
  id: "m1",
  project_id: "p1",
  file_name: "交底.md",
  file_type: "md",
  status: "processed",
  text: "补充材料",
  warnings: [],
  created_at: "2026-06-02T00:00:00Z",
};

const completedDisclosure: DisclosureRun = {
  id: "d1",
  project_id: "p1",
  status: "completed",
  trace: false,
  max_prior_art_results: 8,
  run_dir: "data/disclosures/p1/d1",
  stage_results: [],
  package: {
    title: "外立面逆建模交底书",
    summary: "交底摘要",
    materials_summary: "材料摘要",
    candidates: [],
    selected_candidate_id: null,
    prior_art_hits: [],
    prior_art_differences: "本地材料生成。",
    body_markdown: "交底正文",
    mermaid: "flowchart TD",
    image_prompt: "黑白线稿",
    self_check_findings: [],
    generation_logs: [],
  },
  failures: [],
  events: ["done"],
  created_at: "2026-06-02T00:00:00Z",
  updated_at: "2026-06-02T00:00:00Z",
};

function filingReport(status: FilingReadinessReport["status"]): FilingReadinessReport {
  return {
    id: `fr-${status}`,
    project_id: "p1",
    rules_version: "v1",
    status,
    issues: [],
    official_export_allowed: true,
    internal_export_allowed: true,
    created_at: "2026-06-02T00:00:00Z",
  };
}

const worksheet: ClaimDefenseWorksheet = {
  id: "w1",
  project_id: "p1",
  source: "generated_package",
  status: "completed",
  feature_records: [],
  defense_recommendations: [],
  support_gaps: [],
  created_at: "2026-06-02T00:00:00Z",
};

const completionRun: DraftCompletionRun = {
  id: "c1",
  project_id: "p1",
  snapshot_hash: "hash",
  status: "completed",
  issues: [],
  tasks: [],
  patches: [],
  support_matrix: [],
  scorecard: {
    authorization_stability: 70,
    protection_scope: 80,
    support_strength: 65,
    prior_art_distinction: 60,
    filing_maturity: 75,
    official_hygiene: 90,
    overall: 73,
  },
  notes: [],
  created_at: "2026-06-02T00:00:00Z",
};

describe("guided flow navigation", () => {
  it("uses three main sections and keeps expert tools grouped", () => {
    expect(mainSections.map((item) => item.label)).toEqual(["专利生成", "项目", "专家工具"]);
    expect(expertToolGroups.map((group) => group.label)).toEqual(["知识库", "发明点", "交底与策略", "质检", "导出"]);
  });
});

describe("deriveGuidedFlowState", () => {
  it("starts at idea intake when no project exists", () => {
    const state = deriveGuidedFlowState({
      project: null,
      materials: [],
      disclosures: [],
      patentPoints: [],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(state.currentStepId).toBe("idea");
    expect(state.steps.map((step) => step.status)).toEqual(["current", "locked", "locked", "locked", "locked"]);
  });

  it("moves to invention confirmation after disclosure is completed", () => {
    const state = deriveGuidedFlowState({
      project: projectWithIdea,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      patentPoints: [],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(state.currentStepId).toBe("invention");
    expect(state.steps[0].status).toBe("done");
    expect(state.steps[1].status).toBe("current");
  });

  it("marks export ready after package and quality runs exist", () => {
    const state = deriveGuidedFlowState({
      project: {
        ...projectWithIdea,
        package: {
          title: "一种外立面逆建模方法",
          abstract: "摘要",
          claims: "1. 一种方法。",
          description: "说明书",
          drawings: "附图说明",
          mermaid: "flowchart TD",
          image_prompt: "黑白线稿",
          review_findings: [],
          cited_chunks: [],
          generation_logs: [],
        },
      },
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
    });

    expect(state.currentStepId).toBe("export");
    expect(state.exportReady).toBe(true);
    expect(state.steps.map((step) => step.status)).toEqual(["done", "done", "done", "done", "current"]);
  });
});

describe("qualitySummaryFromRuns", () => {
  it("summarizes warning-mode export and scorecards", () => {
    const summary = qualitySummaryFromRuns({
      filingReport: filingReport("high_risk"),
      worksheet,
      completionRun,
    });

    expect(summary.statusLabel).toBe("高风险但可导出");
    expect(summary.authorizationStability).toBe(70);
    expect(summary.protectionScope).toBe(80);
    expect(summary.filingMaturity).toBe(75);
    expect(summary.officialExportAllowed).toBe(true);
  });
});

describe("guidedStepLabels", () => {
  it("uses user-action language instead of internal module names", () => {
    expect(guidedStepLabels).toEqual(["想法与材料", "发明点", "生成初稿", "质量检查", "导出"]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend
npm test -- --run src/guidedFlow.test.ts src/domain.test.ts
```

Expected: FAIL because `frontend/src/guidedFlow.ts` does not exist and `workspaceTabs` still represents the old 12-tab layout.

- [ ] **Step 3: Add guided-flow helpers**

Create `frontend/src/guidedFlow.ts`:

```ts
import {
  BookOpen,
  ClipboardCheck,
  ClipboardList,
  Download,
  FileArchive,
  FilePlus2,
  Gauge,
  PenLine,
  Scale,
  SearchCheck,
  ShieldCheck,
  UsersRound,
  Wand2,
  type LucideIcon,
} from "lucide-react";

import type {
  ClaimDefenseWorksheet,
  DisclosureRun,
  DraftCompletionRun,
  FilingReadinessReport,
  PatentPointCandidate,
  ProjectMaterial,
  ProjectRecord,
} from "./api";
import { canExportPackage } from "./domain";

export type MainSectionId = "generate" | "projects" | "expert";

export type ExpertToolId =
  | "build"
  | "corpus"
  | "moat"
  | "materials"
  | "deliberate"
  | "write"
  | "readiness"
  | "claimDefense"
  | "completion"
  | "review"
  | "export";

export type GuidedStepId = "idea" | "invention" | "draft" | "quality" | "export";
export type GuidedStepStatus = "done" | "current" | "ready" | "locked";
export type PatentGoalMode = "stable" | "broad" | "fast" | "moat";

export type NavEntry<T extends string> = {
  id: T;
  label: string;
  description: string;
  icon: LucideIcon;
};

export type ExpertToolGroup = {
  id: string;
  label: string;
  tools: Array<NavEntry<ExpertToolId>>;
};

export type GuidedStepState = {
  id: GuidedStepId;
  label: string;
  description: string;
  status: GuidedStepStatus;
};

export type GuidedFlowInput = {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  disclosures: DisclosureRun[];
  patentPoints: PatentPointCandidate[];
  filingReports: FilingReadinessReport[];
  worksheets: ClaimDefenseWorksheet[];
  completionRuns: DraftCompletionRun[];
};

export type GuidedFlowState = {
  currentStepId: GuidedStepId;
  steps: GuidedStepState[];
  processedMaterialCount: number;
  hasCompletedDisclosure: boolean;
  hasConfirmedInventionPoint: boolean;
  draftReady: boolean;
  qualityChecked: boolean;
  exportReady: boolean;
};

export type QualitySummary = {
  statusLabel: string;
  authorizationStability: number | null;
  protectionScope: number | null;
  filingMaturity: number | null;
  issueCount: number;
  supportGapCount: number;
  taskCount: number;
  officialExportAllowed: boolean;
};

export const mainSections: Array<NavEntry<MainSectionId>> = [
  { id: "generate", label: "专利生成", description: "从一句想法到可导出文件", icon: Wand2 },
  { id: "projects", label: "项目", description: "查看历史项目和运行记录", icon: FileArchive },
  { id: "expert", label: "专家工具", description: "进入旧工作台和高级检查", icon: Gauge },
];

export const expertToolGroups: ExpertToolGroup[] = [
  {
    id: "knowledge",
    label: "知识库",
    tools: [
      { id: "build", label: "语料库建设", description: "导入官方导出物", icon: FileArchive },
      { id: "corpus", label: "知识库检索", description: "检索授权专利片段", icon: BookOpen },
    ],
  },
  {
    id: "invention",
    label: "发明点",
    tools: [{ id: "moat", label: "护城河地图", description: "管理发明点和证据状态", icon: ShieldCheck }],
  },
  {
    id: "strategy",
    label: "交底与策略",
    tools: [
      { id: "materials", label: "前置材料", description: "生成交底书和候选发明点", icon: ClipboardList },
      { id: "deliberate", label: "多 Agent 会审", description: "生成撰写策略", icon: UsersRound },
      { id: "write", label: "分步撰写", description: "手动生成申请文本", icon: PenLine },
    ],
  },
  {
    id: "quality",
    label: "质检",
    tools: [
      { id: "readiness", label: "提交成熟度", description: "检查正式稿清洁度", icon: ClipboardCheck },
      { id: "claimDefense", label: "权利要求防线", description: "分析区别特征和支撑缺口", icon: Scale },
      { id: "completion", label: "初稿完善", description: "生成补强任务和候选补丁", icon: Gauge },
      { id: "review", label: "审查修改", description: "生成审查意见", icon: SearchCheck },
    ],
  },
  {
    id: "export",
    label: "导出",
    tools: [{ id: "export", label: "导出文件", description: "导出正式稿和内部稿", icon: Download }],
  },
];

export const guidedStepDefinitions: Array<Omit<GuidedStepState, "status">> = [
  { id: "idea", label: "想法与材料", description: "输入一句想法，上传可选材料。" },
  { id: "invention", label: "发明点", description: "确认主发明点、证据状态和护城河方向。" },
  { id: "draft", label: "生成初稿", description: "生成摘要、权利要求书和说明书。" },
  { id: "quality", label: "质量检查", description: "运行提交成熟度、权利要求防线和初稿完善。" },
  { id: "export", label: "导出", description: "确认风险并导出正式稿和内部报告。" },
];

export const guidedStepLabels = guidedStepDefinitions.map((step) => step.label);

export function deriveGuidedFlowState(input: GuidedFlowInput): GuidedFlowState {
  const processedMaterialCount = input.materials.filter((material) => material.status === "processed").length;
  const hasIdea = Boolean(input.project?.draft_text.trim());
  const hasCompletedDisclosure = input.disclosures.some((run) => run.status === "completed" && run.package);
  const hasConfirmedInventionPoint = hasCompletedDisclosure || input.patentPoints.some((point) => point.selected);
  const draftReady = canExportPackage(input.project?.package);
  const qualityChecked = Boolean(input.filingReports[0] || input.worksheets[0] || input.completionRuns[0]);
  const exportReady = draftReady && qualityChecked;

  let currentStepId: GuidedStepId = "idea";
  if (!hasIdea) {
    currentStepId = "idea";
  } else if (!hasConfirmedInventionPoint) {
    currentStepId = "invention";
  } else if (!draftReady) {
    currentStepId = "draft";
  } else if (!qualityChecked) {
    currentStepId = "quality";
  } else {
    currentStepId = "export";
  }

  const currentIndex = guidedStepDefinitions.findIndex((step) => step.id === currentStepId);
  const steps = guidedStepDefinitions.map((step, index) => ({
    ...step,
    status: stepStatusForIndex(index, currentIndex, hasIdea) as GuidedStepStatus,
  }));

  return {
    currentStepId,
    steps,
    processedMaterialCount,
    hasCompletedDisclosure,
    hasConfirmedInventionPoint,
    draftReady,
    qualityChecked,
    exportReady,
  };
}

function stepStatusForIndex(index: number, currentIndex: number, hasIdea: boolean): GuidedStepStatus {
  if (!hasIdea && index > 0) return "locked";
  if (index < currentIndex) return "done";
  if (index === currentIndex) return "current";
  return "ready";
}

export function qualitySummaryFromRuns(input: {
  filingReport: FilingReadinessReport | null;
  worksheet: ClaimDefenseWorksheet | null;
  completionRun: DraftCompletionRun | null;
}): QualitySummary {
  const completion = input.completionRun?.scorecard ?? null;
  const statusLabel =
    input.filingReport?.status === "high_risk"
      ? "高风险但可导出"
      : input.filingReport?.status === "warning"
        ? "建议补强"
        : input.filingReport
          ? "可导出"
          : "尚未检查";

  return {
    statusLabel,
    authorizationStability: completion?.authorization_stability ?? null,
    protectionScope: completion?.protection_scope ?? null,
    filingMaturity: completion?.filing_maturity ?? null,
    issueCount: input.filingReport?.issues.length ?? 0,
    supportGapCount: input.worksheet?.support_gaps.length ?? 0,
    taskCount: input.completionRun?.tasks.length ?? 0,
    officialExportAllowed: input.filingReport?.official_export_allowed ?? true,
  };
}
```

- [ ] **Step 4: Update domain exports and tests**

Modify `frontend/src/domain.ts` so old workspace navigation is replaced by a compatibility export for expert tools:

```ts
import {
  BookOpen,
  ClipboardCheck,
  ClipboardList,
  Database,
  Download,
  FilePlus2,
  Gauge,
  PenLine,
  Scale,
  SearchCheck,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import type { ExpertToolId } from "./guidedFlow";

export type WorkspaceTabId = ExpertToolId;
```

Keep the existing `workspaceTabs` export temporarily as an expert-tool flat list:

```ts
export const workspaceTabs = [
  { id: "build", label: "语料库建设", icon: Database },
  { id: "corpus", label: "知识库", icon: BookOpen },
  { id: "moat", label: "护城河地图", icon: ShieldCheck },
  { id: "materials", label: "前置材料", icon: ClipboardList },
  { id: "deliberate", label: "多 Agent 会审", icon: UsersRound },
  { id: "write", label: "分步撰写", icon: PenLine },
  { id: "readiness", label: "提交成熟度", icon: ClipboardCheck },
  { id: "claimDefense", label: "权利要求防线", icon: Scale },
  { id: "completion", label: "初稿完善", icon: Gauge },
  { id: "review", label: "审查修改", icon: SearchCheck },
  { id: "export", label: "导出", icon: Download },
] satisfies Array<{ id: WorkspaceTabId; label: string; icon: typeof BookOpen }>;
```

Modify the `workspaceTabs` test in `frontend/src/domain.test.ts`:

```ts
import { expertToolGroups, mainSections } from "./guidedFlow";

describe("guided navigation", () => {
  it("uses three primary sections and preserves expert tools", () => {
    expect(mainSections.map((section) => section.label)).toEqual(["专利生成", "项目", "专家工具"]);
    expect(expertToolGroups.flatMap((group) => group.tools.map((tool) => tool.label))).toEqual([
      "语料库建设",
      "知识库检索",
      "护城河地图",
      "前置材料",
      "多 Agent 会审",
      "分步撰写",
      "提交成熟度",
      "权利要求防线",
      "初稿完善",
      "审查修改",
      "导出文件",
    ]);
  });
});
```

Remove the old `"创建专利项目"` expectation because creation moves into the guided `专利生成` intake.

- [ ] **Step 5: Run helper tests**

Run:

```bash
cd frontend
npm test -- --run src/guidedFlow.test.ts src/domain.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit domain model**

```bash
git add frontend/src/guidedFlow.ts frontend/src/guidedFlow.test.ts frontend/src/domain.ts frontend/src/domain.test.ts
git commit -m "feat: add guided patent flow model"
```

---

### Task 2: Replace Default Navigation Shell

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/guidedFlow.test.ts`

- [ ] **Step 1: Add a navigation regression test**

Extend `frontend/src/guidedFlow.test.ts`:

```ts
import { defaultExpertToolId, defaultMainSectionId } from "./guidedFlow";

describe("guided flow defaults", () => {
  it("opens on patent generation and keeps expert tools on knowledge import", () => {
    expect(defaultMainSectionId).toBe("generate");
    expect(defaultExpertToolId).toBe("build");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd frontend
npm test -- --run src/guidedFlow.test.ts
```

Expected: FAIL because `defaultMainSectionId` and `defaultExpertToolId` are not exported.

- [ ] **Step 3: Add default exports**

Add to `frontend/src/guidedFlow.ts`:

```ts
export const defaultMainSectionId: MainSectionId = "generate";
export const defaultExpertToolId: ExpertToolId = "build";
```

- [ ] **Step 4: Change App shell state**

In `frontend/src/App.tsx`, add imports:

```ts
import {
  defaultExpertToolId,
  defaultMainSectionId,
  deriveGuidedFlowState,
  expertToolGroups,
  mainSections,
  type ExpertToolId,
  type MainSectionId,
} from "./guidedFlow";
```

Replace:

```ts
const [activeTab, setActiveTab] = useState<WorkspaceTabId>("build");
```

with:

```ts
const [activeSection, setActiveSection] = useState<MainSectionId>(defaultMainSectionId);
const [activeExpertTool, setActiveExpertTool] = useState<ExpertToolId>(defaultExpertToolId);
```

Add the derived state after `latestCompletionRun`:

```ts
const guidedFlowState = deriveGuidedFlowState({
  project: selectedProject,
  materials: projectMaterials,
  disclosures: disclosureRuns,
  patentPoints: visiblePatentPoints,
  filingReports,
  worksheets,
  completionRuns,
});
```

- [ ] **Step 5: Replace sidebar primary nav**

Replace the old `<nav className="tab-list">` block with:

```tsx
<nav className="tab-list" aria-label="主导航">
  {mainSections.map((section) => {
    const Icon = section.icon;
    return (
      <button
        className={activeSection === section.id ? "tab active" : "tab"}
        key={section.id}
        onClick={() => setActiveSection(section.id)}
        type="button"
        title={section.description}
      >
        <Icon size={18} />
        <span>{section.label}</span>
      </button>
    );
  })}
</nav>
```

Add expert quick section inside the sidebar after primary nav:

```tsx
{activeSection === "expert" && (
  <div className="expert-nav">
    {expertToolGroups.map((group) => (
      <div className="expert-nav-group" key={group.id}>
        <p>{group.label}</p>
        {group.tools.map((tool) => {
          const Icon = tool.icon;
          return (
            <button
              className={activeExpertTool === tool.id ? "expert-tab active" : "expert-tab"}
              key={tool.id}
              onClick={() => setActiveExpertTool(tool.id)}
              type="button"
              title={tool.description}
            >
              <Icon size={16} />
              <span>{tool.label}</span>
            </button>
          );
        })}
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 6: Replace topbar title**

Replace:

```tsx
<p className="eyebrow">RAG Patent Workbench</p>
<h2>{workspaceTabs.find((tab) => tab.id === activeTab)?.label}</h2>
```

with:

```tsx
<p className="eyebrow">Guided Patent Workbench</p>
<h2>
  {activeSection === "generate"
    ? "专利生成"
    : activeSection === "projects"
      ? "项目"
      : expertToolGroups.flatMap((group) => group.tools).find((tool) => tool.id === activeExpertTool)?.label}
</h2>
```

- [ ] **Step 7: Add section routing**

Replace the old `activeTab === ...` render checks with:

```tsx
{activeSection === "generate" && (
  <section className="panel wide">
    <h3>专利生成</h3>
    <p>主流程向导将在下一任务接入。当前可从专家工具继续使用旧工作台。</p>
  </section>
)}

{activeSection === "projects" && (
  <ProjectsOverview projects={projects} selectedProjectId={selectedProject?.id ?? ""} onSelect={setSelectedProjectId} />
)}

{activeSection === "expert" && (
  renderExpertTool()
)}
```

Add this local function inside `App()` above `return (`:

```tsx
function renderExpertTool() {
  switch (activeExpertTool) {
    case "build":
      return (
        <CorpusBuildView
          form={corpusJobForm}
          job={corpusJob}
          versions={corpusVersions}
          stats={corpusStats}
          busy={busy}
          onFormChange={(patch) => setCorpusJobForm((current) => ({ ...current, ...patch }))}
          onCreateJob={handleCreateCorpusJob}
          onUploadFile={handleUploadCorpusJobFile}
          onRunJob={handleRunCorpusJob}
        />
      );
    case "corpus":
      return (
        <CorpusView
          documents={documents}
          searchText={searchText}
          searchSection={searchSection}
          searchResults={searchResults}
          busy={busy}
          onImport={handleImport}
          onSearch={handleSearch}
          onSearchText={setSearchText}
          onSearchSection={setSearchSection}
        />
      );
    case "moat":
      return (
        <MoatView
          project={selectedProject}
          points={visiblePatentPoints}
          busy={busy}
          onCreate={handleCreatePatentPoint}
          onSelect={handleSelectPatentPoint}
          onDelete={handleDeletePatentPoint}
        />
      );
    case "deliberate":
      return (
        <DeliberationView
          project={selectedProject}
          doctor={agentDoctor}
          runs={deliberationRuns}
          disclosure={currentDisclosure}
          busy={busy}
          onStart={handleStartDeliberation}
          onRefresh={() => selectedProject && loadDeliberations(selectedProject.id)}
        />
      );
    case "materials":
      return (
        <DisclosureView
          project={selectedProject}
          materials={projectMaterials}
          runs={disclosureRuns}
          busy={busy}
          onUpload={handleUploadMaterial}
          onStart={handleStartDisclosure}
          onRefresh={() => selectedProject && loadDisclosures(selectedProject.id)}
        />
      );
    case "write":
      return (
        <WriteView
          project={selectedProject}
          deliberation={currentDeliberation}
          disclosure={currentDisclosure}
          busy={busy}
          onGenerate={handleGenerate}
        />
      );
    case "readiness":
      return (
        <FilingReadinessView
          project={selectedProject}
          report={latestFilingReport}
          reports={filingReports}
          busy={busy}
          onRun={handleRunFilingReadiness}
        />
      );
    case "claimDefense":
      return (
        <ClaimDefenseView
          project={selectedProject}
          worksheet={latestWorksheet}
          worksheets={worksheets}
          busy={busy}
          onGenerate={handleCreateWorksheet}
        />
      );
    case "completion":
      return (
        <DraftCompletionView
          project={selectedProject}
          run={latestCompletionRun}
          runs={completionRuns}
          busy={busy}
          onRun={handleRunDraftCompletion}
          onPatch={handleCompletionPatch}
        />
      );
    case "review":
      return <ReviewView project={selectedProject} busy={busy} onReview={handleReview} />;
    case "export":
      return <ExportView project={selectedProject} packageValue={currentPackage} />;
  }
}
```

- [ ] **Step 8: Add `ProjectsOverview`**

Add this component near `ProjectSelect`:

```tsx
function ProjectsOverview({
  projects,
  selectedProjectId,
  onSelect,
}: {
  projects: ProjectRecord[];
  selectedProjectId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="panel wide">
      <h3>项目</h3>
      <p>选择历史项目后，可以继续生成、质检或导出。</p>
      <div className="project-grid">
        {projects.map((project) => (
          <button
            className={project.id === selectedProjectId ? "project-card selected" : "project-card"}
            key={project.id}
            onClick={() => onSelect(project.id)}
            type="button"
          >
            <strong>{project.name}</strong>
            <span>{project.package ? "已有初稿" : "仅有想法"}</span>
            <small>{project.updated_at}</small>
          </button>
        ))}
        {projects.length === 0 && <p className="empty">暂无项目。进入“专利生成”输入想法即可创建。</p>}
      </div>
    </section>
  );
}
```

- [ ] **Step 9: Add navigation styles**

Append to `frontend/src/styles.css`:

```css
.expert-nav {
  display: grid;
  gap: 16px;
}

.expert-nav-group {
  display: grid;
  gap: 6px;
}

.expert-nav-group p {
  margin: 0 0 2px;
  color: #cbd7d1;
  font-size: 12px;
  font-weight: 700;
}

.expert-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  border: 1px solid transparent;
  border-radius: 8px;
  color: #e8eee9;
  background: transparent;
  cursor: pointer;
  padding: 0 10px;
  text-align: left;
}

.expert-tab.active,
.expert-tab:hover {
  background: rgba(248, 250, 244, 0.14);
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.project-card {
  display: grid;
  gap: 8px;
  border: 1px solid #d8ddd5;
  border-radius: 8px;
  background: #fff;
  color: #202124;
  padding: 16px;
  text-align: left;
  cursor: pointer;
}

.project-card.selected {
  border-color: #2f7d7e;
  box-shadow: 0 0 0 2px rgba(47, 125, 126, 0.16);
}
```

- [ ] **Step 10: Run frontend verification**

Run:

```bash
cd frontend
npm test -- --run src/guidedFlow.test.ts src/domain.test.ts
npm run build
```

Expected: tests pass and Vite build completes.

- [ ] **Step 11: Commit navigation shell**

```bash
git add frontend/src/App.tsx frontend/src/styles.css frontend/src/guidedFlow.ts frontend/src/guidedFlow.test.ts
git commit -m "feat: simplify workbench navigation"
```

---

### Task 3: Build Idea Intake and Invention Confirmation

**Files:**
- Create: `frontend/src/GuidedPatentFlow.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/guidedFlow.test.ts`

- [ ] **Step 1: Add a mode-label test**

Extend `frontend/src/guidedFlow.test.ts`:

```ts
import { patentGoalModes } from "./guidedFlow";

describe("patent goal modes", () => {
  it("exposes user-facing goal modes for the idea intake", () => {
    expect(patentGoalModes.map((mode) => mode.label)).toEqual([
      "授权稳健",
      "保护范围优先",
      "快速初稿",
      "专利护城河",
    ]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- --run src/guidedFlow.test.ts
```

Expected: FAIL because `patentGoalModes` is missing.

- [ ] **Step 3: Add goal modes**

Add to `frontend/src/guidedFlow.ts`:

```ts
export const patentGoalModes: Array<{ id: PatentGoalMode; label: string; description: string }> = [
  { id: "stable", label: "授权稳健", description: "收紧独权，强调组合闭环和说明书支撑。" },
  { id: "broad", label: "保护范围优先", description: "先上位覆盖，再用从权兜底替代实现。" },
  { id: "fast", label: "快速初稿", description: "优先生成可审阅的完整初稿。" },
  { id: "moat", label: "专利护城河", description: "允许可行未验证方案进入内部策略和分案布局。" },
];
```

- [ ] **Step 4: Create guided flow components**

Create `frontend/src/GuidedPatentFlow.tsx`:

```tsx
import { FormEvent, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Download, FileText, Gauge, Loader2, Upload, Wand2 } from "lucide-react";

import type {
  ClaimDefenseWorksheet,
  DisclosureRun,
  DraftCompletionRun,
  FilingReadinessReport,
  PatentPointCandidate,
  ProjectMaterial,
  ProjectRecord,
} from "./api";
import {
  deriveGuidedFlowState,
  patentGoalModes,
  qualitySummaryFromRuns,
  type GuidedFlowState,
  type PatentGoalMode,
} from "./guidedFlow";
import { draftCompletionReportUrl, exportUrl, filingReadinessReportUrl, officialExportUrl } from "./api";

export type GuidedPatentFlowProps = {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  disclosures: DisclosureRun[];
  patentPoints: PatentPointCandidate[];
  filingReports: FilingReadinessReport[];
  worksheets: ClaimDefenseWorksheet[];
  completionRuns: DraftCompletionRun[];
  busy: string;
  onCreateIdeaProject: (payload: { name: string; idea: string; mode: PatentGoalMode }) => Promise<void>;
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => void;
  onStartDisclosure: () => void;
  onSelectPatentPoint: (point: PatentPointCandidate) => void;
  onGenerateDraft: () => void;
  onRunQualityChecks: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
};

export function GuidedPatentFlowView(props: GuidedPatentFlowProps) {
  const state = useMemo(
    () =>
      deriveGuidedFlowState({
        project: props.project,
        materials: props.materials,
        disclosures: props.disclosures,
        patentPoints: props.patentPoints,
        filingReports: props.filingReports,
        worksheets: props.worksheets,
        completionRuns: props.completionRuns,
      }),
    [props.project, props.materials, props.disclosures, props.patentPoints, props.filingReports, props.worksheets, props.completionRuns],
  );
  const latestDisclosure = props.disclosures.find((run) => run.status === "completed" && run.package) ?? null;
  const latestFilingReport = props.filingReports[0] ?? null;
  const latestWorksheet = props.worksheets[0] ?? null;
  const latestCompletionRun = props.completionRuns[0] ?? null;

  return (
    <div className="guided-flow">
      <WorkflowStepper state={state} />
      {state.currentStepId === "idea" && (
        <IdeaIntakePanel
          project={props.project}
          materials={props.materials}
          busy={props.busy}
          onCreateIdeaProject={props.onCreateIdeaProject}
          onUploadMaterial={props.onUploadMaterial}
        />
      )}
      {state.currentStepId === "invention" && (
        <InventionPointConfirmation
          disclosure={latestDisclosure}
          patentPoints={props.patentPoints}
          busy={props.busy}
          onStartDisclosure={props.onStartDisclosure}
          onSelectPatentPoint={props.onSelectPatentPoint}
        />
      )}
      {state.currentStepId === "draft" && (
        <DraftGenerationPanel project={props.project} disclosure={latestDisclosure} busy={props.busy} onGenerateDraft={props.onGenerateDraft} />
      )}
      {state.currentStepId === "quality" && (
        <QualityPanel
          filingReport={latestFilingReport}
          worksheet={latestWorksheet}
          completionRun={latestCompletionRun}
          busy={props.busy}
          onRunQualityChecks={props.onRunQualityChecks}
          onAcceptPatch={props.onAcceptPatch}
        />
      )}
      {state.currentStepId === "export" && (
        <ExportConfirmationPanel
          project={props.project}
          filingReport={latestFilingReport}
          completionRun={latestCompletionRun}
        />
      )}
    </div>
  );
}

function WorkflowStepper({ state }: { state: GuidedFlowState }) {
  return (
    <section className="guided-stepper">
      {state.steps.map((step, index) => (
        <article className={`guided-step ${step.status}`} key={step.id}>
          <span>{index + 1}</span>
          <div>
            <strong>{step.label}</strong>
            <p>{step.description}</p>
          </div>
        </article>
      ))}
    </section>
  );
}

function IdeaIntakePanel({
  project,
  materials,
  busy,
  onCreateIdeaProject,
  onUploadMaterial,
}: {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  busy: string;
  onCreateIdeaProject: GuidedPatentFlowProps["onCreateIdeaProject"];
  onUploadMaterial: GuidedPatentFlowProps["onUploadMaterial"];
}) {
  const [name, setName] = useState(project?.name ?? "");
  const [idea, setIdea] = useState(project?.draft_text ?? "");
  const [mode, setMode] = useState<PatentGoalMode>("stable");
  const canSubmit = Boolean(name.trim() && idea.trim() && !project);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    await onCreateIdeaProject({ name: name.trim(), idea: idea.trim(), mode });
  }

  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>把你的想法写成一段话</h3>
          <p>系统会基于这段想法提炼发明点、生成专利初稿、运行质检并准备导出文件。</p>
        </div>
        <Wand2 size={24} />
      </div>
      <form className="guided-intake" onSubmit={handleSubmit}>
        <label>
          <span>项目名称</span>
          <input value={name} onChange={(event) => setName(event.target.value)} disabled={Boolean(project)} />
        </label>
        <label>
          <span>一句话想法</span>
          <textarea
            className="idea-input"
            value={idea}
            onChange={(event) => setIdea(event.target.value)}
            disabled={Boolean(project)}
            placeholder="例如：通过点云和多视角影像自动生成外立面 IFC 模型，并回链工程量清单。"
          />
        </label>
        <div className="mode-grid">
          {patentGoalModes.map((item) => (
            <button
              className={mode === item.id ? "mode-card selected" : "mode-card"}
              key={item.id}
              onClick={() => setMode(item.id)}
              type="button"
            >
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </button>
          ))}
        </div>
        <button className="primary" disabled={!canSubmit || busy === "guided-create"} type="submit">
          <FileText size={17} />
          <span>{project ? "已创建想法" : "创建并继续"}</span>
        </button>
      </form>
      {project && (
        <form className="guided-upload" onSubmit={onUploadMaterial}>
          <input id="project-material-file" name="project-material-file" type="file" accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown" />
          <button className="primary" disabled={busy === "material-upload"} type="submit">
            <Upload size={17} />
            <span>上传补充材料</span>
          </button>
        </form>
      )}
      <MaterialSummary materials={materials} />
    </section>
  );
}

function MaterialSummary({ materials }: { materials: ProjectMaterial[] }) {
  return (
    <div className="guided-summary-list">
      {materials.map((material) => (
        <article className="guided-summary-row" key={material.id}>
          {material.status === "processed" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          <div>
            <strong>{material.file_name}</strong>
            <span>{material.status === "processed" ? `${material.file_type} / ${material.text.length} 字` : material.warnings.join("；")}</span>
          </div>
        </article>
      ))}
      {materials.length === 0 && <p className="empty">可先不上传材料，系统会基于想法生成第一版。</p>}
    </div>
  );
}

function InventionPointConfirmation({
  disclosure,
  patentPoints,
  busy,
  onStartDisclosure,
  onSelectPatentPoint,
}: {
  disclosure: DisclosureRun | null;
  patentPoints: PatentPointCandidate[];
  busy: string;
  onStartDisclosure: () => void;
  onSelectPatentPoint: (point: PatentPointCandidate) => void;
}) {
  const candidates = disclosure?.package?.candidates.length ? disclosure.package.candidates : patentPoints;
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>确认发明点与护城河</h3>
          <p>这里是默认流程的第一个暂停点。确认主线后，系统才进入初稿生成。</p>
        </div>
        <ShieldCheck size={24} />
      </div>
      {!disclosure && (
        <button className="primary" disabled={busy === "disclosure"} onClick={onStartDisclosure} type="button">
          {busy === "disclosure" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
          <span>提炼发明点</span>
        </button>
      )}
      <div className="guided-card-grid">
        {candidates.map((point) => (
          <article className={point.selected ? "guided-choice selected" : "guided-choice"} key={point.id}>
            <div className="result-meta">
              <span className="status-badge">{point.evidence_status === "verified" ? "已验证" : point.evidence_status === "needs_experiment" ? "需实验" : "可行未验证"}</span>
              <span>{point.protection_focus.join(" / ") || "方法 / 系统"}</span>
            </div>
            <h4>{point.title}</h4>
            <p>{point.innovation || point.technical_solution}</p>
            {point.support_gaps.length > 0 && <p className="workflow-hint">支撑缺口：{point.support_gaps.join("；")}</p>}
            <button className="icon-button" onClick={() => onSelectPatentPoint(point)} type="button">
              选为主线
            </button>
          </article>
        ))}
        {candidates.length === 0 && <p className="empty">点击“提炼发明点”后显示候选主线。</p>}
      </div>
    </section>
  );
}

function DraftGenerationPanel({
  project,
  disclosure,
  busy,
  onGenerateDraft,
}: {
  project: ProjectRecord | null;
  disclosure: DisclosureRun | null;
  busy: string;
  onGenerateDraft: () => void;
}) {
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>生成专利初稿</h3>
          <p>{disclosure ? `将使用交底书 run：${disclosure.id}` : "将使用当前想法和已确认发明点生成。"}</p>
        </div>
        <FileText size={24} />
      </div>
      <button className="primary" disabled={!project || busy === "generate"} onClick={onGenerateDraft} type="button">
        {busy === "generate" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
        <span>生成初稿</span>
      </button>
      {project?.package && <pre className="guided-preview">{project.package.claims.slice(0, 1200)}</pre>}
    </section>
  );
}

function QualityPanel({
  filingReport,
  worksheet,
  completionRun,
  busy,
  onRunQualityChecks,
  onAcceptPatch,
}: {
  filingReport: FilingReadinessReport | null;
  worksheet: ClaimDefenseWorksheet | null;
  completionRun: DraftCompletionRun | null;
  busy: string;
  onRunQualityChecks: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
}) {
  const summary = qualitySummaryFromRuns({ filingReport, worksheet, completionRun });
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>质量检查与补强</h3>
          <p>系统会运行提交成熟度、权利要求防线、初稿完善和审查意见。</p>
        </div>
        <Gauge size={24} />
      </div>
      <button className="primary" disabled={busy === "guided-quality"} onClick={onRunQualityChecks} type="button">
        {busy === "guided-quality" ? <Loader2 className="spin" size={17} /> : <Gauge size={17} />}
        <span>运行质量检查</span>
      </button>
      <div className="guided-score-grid">
        <ScoreTile label="状态" value={summary.statusLabel} />
        <ScoreTile label="授权稳定性" value={summary.authorizationStability === null ? "未评分" : `${summary.authorizationStability}/100`} />
        <ScoreTile label="保护范围" value={summary.protectionScope === null ? "未评分" : `${summary.protectionScope}/100`} />
        <ScoreTile label="提交成熟度" value={summary.filingMaturity === null ? "未评分" : `${summary.filingMaturity}/100`} />
      </div>
      {filingReport?.issues.slice(0, 5).map((issue, index) => (
        <article className={`finding ${issue.severity}`} key={`${issue.category}-${index}`}>
          <span>{issue.severity === "high" ? "高" : issue.severity === "medium" ? "中" : "低"}</span>
          <div>
            <strong>{issue.category}</strong>
            <p>{issue.message}</p>
            <p>{issue.suggestion}</p>
          </div>
        </article>
      ))}
      {completionRun?.patches.filter((patch) => patch.status === "proposed").slice(0, 3).map((patch) => (
        <article className="guided-choice" key={patch.id}>
          <h4>{patch.rationale}</h4>
          <p>{patch.risk_delta}</p>
          <pre className="patch-preview">{patch.after_text}</pre>
          <button className="primary" onClick={() => onAcceptPatch(completionRun.id, patch.id)} type="button">
            接受补强建议
          </button>
        </article>
      ))}
    </section>
  );
}

function ScoreTile({ label, value }: { label: string; value: string }) {
  return (
    <article className="score-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function ExportConfirmationPanel({
  project,
  filingReport,
  completionRun,
}: {
  project: ProjectRecord | null;
  filingReport: FilingReadinessReport | null;
  completionRun: DraftCompletionRun | null;
}) {
  if (!project?.package) {
    return <section className="guided-panel"><p className="empty">生成初稿后才能导出。</p></section>;
  }
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>导出前确认</h3>
          <p>这是默认流程的第二个暂停点。高风险不会阻止导出，但会保留在内部报告中。</p>
        </div>
        <Download size={24} />
      </div>
      {filingReport?.status === "high_risk" && <p className="workflow-hint">当前为高风险但允许导出。请先查看检查报告。</p>}
      <div className="export-grid">
        <a className="export-link" href={officialExportUrl(project.id, "docx")}><Download size={18} /><span>正式提交稿 DOCX</span></a>
        <a className="export-link" href={officialExportUrl(project.id, "md")}><Download size={18} /><span>正式提交稿 MD</span></a>
        <a className="export-link" href={exportUrl(project.id, "md")}><Download size={18} /><span>内部策略稿 MD</span></a>
        {filingReport && <a className="export-link" href={filingReadinessReportUrl(project.id, filingReport.id)}><Download size={18} /><span>提交成熟度报告</span></a>}
        {completionRun && <a className="export-link" href={draftCompletionReportUrl(project.id, completionRun.id)}><Download size={18} /><span>初稿完善报告</span></a>}
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Wire guided component into App**

In `frontend/src/App.tsx`, import:

```ts
import { GuidedPatentFlowView } from "./GuidedPatentFlow";
import type { PatentGoalMode } from "./guidedFlow";
```

Add handler:

```ts
async function handleCreateIdeaProject(payload: { name: string; idea: string; mode: PatentGoalMode }) {
  await withStatus("guided-create", async () => {
    const prefix =
      payload.mode === "stable"
        ? "目标模式：授权稳健。"
        : payload.mode === "broad"
          ? "目标模式：保护范围优先。"
          : payload.mode === "fast"
            ? "目标模式：快速初稿。"
            : "目标模式：专利护城河，允许可行未验证方案进入内部策略。";
    const project = await createProject(payload.name, `${prefix}\n${payload.idea}`);
    const nextProjects = await listProjects();
    setProjects(nextProjects);
    setSelectedProjectId(project.id);
    setMessage(`已创建项目：${project.name}`);
  });
}
```

Render under `activeSection === "generate"`:

```tsx
<GuidedPatentFlowView
  project={selectedProject}
  materials={projectMaterials}
  disclosures={disclosureRuns}
  patentPoints={visiblePatentPoints}
  filingReports={filingReports}
  worksheets={worksheets}
  completionRuns={completionRuns}
  busy={busy}
  onCreateIdeaProject={handleCreateIdeaProject}
  onUploadMaterial={handleUploadMaterial}
  onStartDisclosure={() => void handleStartDisclosure(false)}
  onSelectPatentPoint={(point) => void handleSelectPatentPoint(point)}
  onGenerateDraft={() => void handleGenerate()}
  onRunQualityChecks={() => void handleRunGuidedQualityChecks()}
  onAcceptPatch={(runId, patchId) => void handleCompletionPatch(runId, patchId, "accept")}
/>
```

`handleRunGuidedQualityChecks` is added in Task 4. Temporarily add:

```ts
async function handleRunGuidedQualityChecks() {
  await handleRunFilingReadiness();
}
```

- [ ] **Step 6: Add guided styles**

Append to `frontend/src/styles.css`:

```css
.guided-flow {
  display: grid;
  gap: 18px;
}

.guided-stepper {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.guided-step {
  display: flex;
  gap: 10px;
  min-height: 94px;
  border: 1px solid #d8ddd5;
  border-radius: 8px;
  background: #fff;
  padding: 14px;
}

.guided-step > span {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #e8eee9;
  color: #26332f;
  font-weight: 800;
}

.guided-step.current {
  border-color: #2f7d7e;
  box-shadow: 0 0 0 2px rgba(47, 125, 126, 0.14);
}

.guided-step.done > span {
  background: #2f7d7e;
  color: #fff;
}

.guided-step.locked {
  opacity: 0.5;
}

.guided-step p,
.guided-panel p,
.mode-card span,
.guided-summary-row span {
  margin: 0;
  color: #56615d;
  line-height: 1.5;
}

.guided-panel {
  display: grid;
  gap: 18px;
  border: 1px solid #d8ddd5;
  border-radius: 8px;
  background: #fff;
  padding: 22px;
}

.guided-panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.guided-intake,
.guided-upload {
  display: grid;
  gap: 14px;
}

.idea-input {
  min-height: 180px;
}

.mode-grid,
.guided-card-grid,
.guided-score-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.mode-card,
.guided-choice {
  display: grid;
  gap: 8px;
  border: 1px solid #d8ddd5;
  border-radius: 8px;
  background: #fff;
  color: #202124;
  padding: 14px;
  text-align: left;
}

.mode-card.selected,
.guided-choice.selected {
  border-color: #2f7d7e;
  box-shadow: 0 0 0 2px rgba(47, 125, 126, 0.14);
}

.guided-summary-list {
  display: grid;
  gap: 8px;
}

.guided-summary-row {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #edf0ea;
  border-radius: 8px;
  padding: 10px 12px;
}

.guided-preview {
  max-height: 360px;
  overflow: auto;
  border-radius: 8px;
  background: #f6f8f5;
  padding: 14px;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .guided-stepper {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 7: Run frontend verification**

Run:

```bash
cd frontend
npm test -- --run src/guidedFlow.test.ts src/domain.test.ts
npm run build
```

Expected: tests pass and Vite build completes.

- [ ] **Step 8: Commit guided intake**

```bash
git add frontend/src/GuidedPatentFlow.tsx frontend/src/App.tsx frontend/src/styles.css frontend/src/guidedFlow.ts frontend/src/guidedFlow.test.ts
git commit -m "feat: add guided patent intake"
```

---

### Task 4: Add Guided Quality Orchestration

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/GuidedPatentFlow.tsx`
- Test: `frontend/src/guidedFlow.test.ts`

- [ ] **Step 1: Add busy-label helper test**

Add to `frontend/src/guidedFlow.test.ts`:

```ts
import { guidedBusyLabel } from "./guidedFlow";

describe("guidedBusyLabel", () => {
  it("translates internal busy keys into user-facing progress", () => {
    expect(guidedBusyLabel("guided-quality")).toBe("正在运行质量检查");
    expect(guidedBusyLabel("disclosure")).toBe("正在提炼发明点");
    expect(guidedBusyLabel("generate")).toBe("正在生成专利初稿");
    expect(guidedBusyLabel("")).toBe("");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- --run src/guidedFlow.test.ts
```

Expected: FAIL because `guidedBusyLabel` is missing.

- [ ] **Step 3: Add busy-label helper**

Add to `frontend/src/guidedFlow.ts`:

```ts
export function guidedBusyLabel(value: string): string {
  if (value === "guided-quality") return "正在运行质量检查";
  if (value === "disclosure") return "正在提炼发明点";
  if (value === "generate") return "正在生成专利初稿";
  if (value === "guided-create") return "正在创建专利项目";
  if (value === "material-upload") return "正在上传材料";
  if (value.startsWith("completion-")) return "正在处理补强建议";
  return value ? "正在处理" : "";
}
```

- [ ] **Step 4: Implement sequential quality orchestration**

Replace the initial `handleRunGuidedQualityChecks` in `frontend/src/App.tsx` with:

```ts
async function handleRunGuidedQualityChecks() {
  if (!selectedProject?.package) return;
  const projectId = selectedProject.id;
  await withStatus("guided-quality", async () => {
    await reviewProject(projectId);
    const report = await createFilingReadinessReport(projectId);
    const worksheet = await createClaimDefenseWorksheet(projectId);
    const completion = await createDraftCompletionRun(projectId);
    const nextProjects = await listProjects();
    if (selectedProjectIdRef.current !== projectId) return;
    setProjects(nextProjects);
    setSelectedProjectId(projectId);
    setFilingReports((current) => [report, ...current.filter((item) => item.id !== report.id)]);
    setWorksheets((current) => [worksheet, ...current.filter((item) => item.id !== worksheet.id)]);
    setCompletionRuns((current) => [completion, ...current.filter((item) => item.id !== completion.id)]);
    setMessage(`质量检查完成：整体评分 ${completion.scorecard.overall}/100`);
  });
}
```

- [ ] **Step 5: Improve visible progress text**

In `frontend/src/App.tsx`, import `guidedBusyLabel` from `./guidedFlow`.

Replace notice text:

```tsx
<span>{error || message || "处理中"}</span>
```

with:

```tsx
<span>{error || message || guidedBusyLabel(busy) || "处理中"}</span>
```

- [ ] **Step 6: Keep the quality step in place after partial failures**

In `frontend/src/GuidedPatentFlow.tsx`, make `QualityPanel` render existing partial data before the run button:

```tsx
{(filingReport || worksheet || completionRun) && (
  <p className="workflow-hint">已获得部分检查结果。可以继续补强，也可以重新运行质量检查。</p>
)}
```

Place it under the heading and before the run button.

- [ ] **Step 7: Run frontend verification**

Run:

```bash
cd frontend
npm test -- --run src/guidedFlow.test.ts src/domain.test.ts
npm run build
```

Expected: tests pass and Vite build completes.

- [ ] **Step 8: Commit quality orchestration**

```bash
git add frontend/src/App.tsx frontend/src/GuidedPatentFlow.tsx frontend/src/guidedFlow.ts frontend/src/guidedFlow.test.ts
git commit -m "feat: orchestrate guided quality checks"
```

---

### Task 5: Finish Export Confirmation and Expert Shortcuts

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/GuidedPatentFlow.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `README.md`

- [ ] **Step 1: Add direct expert shortcut from guided panels**

Add an optional prop to `GuidedPatentFlowProps`:

```ts
onOpenExpertTool: (tool: "materials" | "moat" | "readiness" | "claimDefense" | "completion" | "export") => void;
```

Add small secondary buttons:

```tsx
<button className="icon-button" onClick={() => onOpenExpertTool("materials")} type="button">
  查看前置材料详情
</button>
```

Place shortcuts in:

- `InventionPointConfirmation`: `materials` and `moat`
- `QualityPanel`: `readiness`, `claimDefense`, `completion`
- `ExportConfirmationPanel`: `export`

Wire in `App.tsx`:

```ts
function openExpertTool(tool: ExpertToolId) {
  setActiveExpertTool(tool);
  setActiveSection("expert");
}
```

- [ ] **Step 2: Make export confirmation explicit**

In `ExportConfirmationPanel`, add a risk summary block before links:

```tsx
<div className="export-confirmation">
  <article>
    <strong>正式稿</strong>
    <span>只包含摘要、权利要求书、说明书和附图说明。</span>
  </article>
  <article>
    <strong>内部稿</strong>
    <span>保留策略、风险、会审、支撑矩阵和补强报告。</span>
  </article>
  <article>
    <strong>导出原则</strong>
    <span>高风险会提示，但不会阻止导出。</span>
  </article>
</div>
```

- [ ] **Step 3: Add export confirmation styles**

Append to `frontend/src/styles.css`:

```css
.export-confirmation {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.export-confirmation article {
  display: grid;
  gap: 6px;
  border: 1px solid #d8ddd5;
  border-radius: 8px;
  background: #f8faf4;
  padding: 14px;
}

.export-confirmation span {
  color: #56615d;
  line-height: 1.5;
}
```

- [ ] **Step 4: Update README**

In `README.md`, replace the old feature list emphasis with a new section after `## 功能`:

```md
## 默认专利生成流程

v0.5 默认入口是 `专利生成`。用户或助手只需要输入一段想法，系统按五步向导执行：

1. 想法与材料：创建项目并上传可选材料。
2. 发明点：提炼候选发明点、证据状态和护城河方向，并暂停给用户确认。
3. 生成初稿：生成摘要、权利要求书、说明书和附图说明。
4. 质量检查：自动运行提交成熟度、权利要求防线、初稿完善和审查意见。
5. 导出：在风险确认后导出正式提交稿、内部策略稿和侧车报告。

高级用户仍可从 `专家工具` 进入语料库建设、知识库检索、护城河地图、前置材料、多 Agent 会审、提交成熟度、权利要求防线和初稿完善等旧工作台。
```

- [ ] **Step 5: Run frontend verification**

Run:

```bash
cd frontend
npm test -- --run
npm run build
```

Expected: all Vitest tests pass and Vite build completes.

- [ ] **Step 6: Commit export shortcuts and docs**

```bash
git add frontend/src/App.tsx frontend/src/GuidedPatentFlow.tsx frontend/src/styles.css README.md
git commit -m "feat: expose expert tools behind guided flow"
```

---

### Task 6: Browser Smoke Test and Polish

**Files:**
- Inspect: `frontend/src/App.tsx`
- Inspect: `frontend/src/GuidedPatentFlow.tsx`
- Inspect: `frontend/src/styles.css`
- Modify only when the smoke test exposes a concrete visual or flow defect: `frontend/src/App.tsx`, `frontend/src/GuidedPatentFlow.tsx`, `frontend/src/styles.css`

- [ ] **Step 1: Start backend with proxy and fast model**

Run:

```bash
HTTPS_PROXY=http://127.0.0.1:6152 HTTP_PROXY=http://127.0.0.1:6152 LLM_MODEL=deepseek-chat python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Expected: Uvicorn reports `http://127.0.0.1:8000`.

- [ ] **Step 2: Start frontend**

Run:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

Expected: Vite reports `http://127.0.0.1:5174/`.

- [ ] **Step 3: Verify health**

Run:

```bash
curl -s http://127.0.0.1:8000/api/health
```

Expected JSON contains:

```json
{"ok":true,"llm_configured":true,"model":"deepseek-chat"}
```

- [ ] **Step 4: Manual guided flow smoke**

Open `http://127.0.0.1:5174/` and verify:

1. The left navigation shows only `专利生成`、`项目`、`专家工具`.
2. The default page is `专利生成`.
3. Enter project name `烟雾测试专利` and idea `一种通过多模态数据生成工程量清单并回链证据的方法。`.
4. Click `创建并继续`.
5. The stepper moves from `想法与材料` to `发明点`.
6. Click `提炼发明点`.
7. When the run completes, candidate invention points are visible.
8. Select one candidate as main line.
9. Click `生成初稿`.
10. Run quality checks.
11. Confirm export links are visible even if high risk is shown.
12. Click `专家工具`; verify old modules are reachable.

- [ ] **Step 5: Fix visual issues found during smoke**

Only make targeted fixes for observed issues. Examples of acceptable fixes:

```css
.guided-step strong {
  line-height: 1.25;
}

.guided-choice h4 {
  margin: 0;
  font-size: 16px;
}
```

Do not add new features during smoke polish.

- [ ] **Step 6: Final verification**

Run:

```bash
python3 -m pytest -q
cd frontend
npm test -- --run
npm run build
```

Expected:

- pytest passes with the existing skip count.
- Vitest passes.
- Vite build completes.

- [ ] **Step 7: Commit smoke polish**

If files changed:

```bash
git add frontend/src/App.tsx frontend/src/GuidedPatentFlow.tsx frontend/src/styles.css
git commit -m "fix: polish guided patent flow"
```

If no files changed, do not create an empty commit.

---

## Execution Notes

- Use `superpowers:subagent-driven-development` for execution. Dispatch one subagent per task and review after each task.
- Do not rewrite backend orchestration in v0.5 first pass.
- Do not delete old views; move them behind expert tools.
- Keep warning-mode export unchanged.
- When LLM calls are needed locally, start backend with proxy env and `LLM_MODEL=deepseek-chat` for practical testing.
