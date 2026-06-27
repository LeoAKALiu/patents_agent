import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GuidedPatentFlowView } from "./GuidedPatentFlow";
import type {
  ClaimDefenseWorksheet,
  DraftCompletionRun,
  DraftPackage,
  FilingReadinessReport,
  OfficialCompileRun,
  ProjectRecord,
} from "./api";

const draftPackage: DraftPackage = {
  title: "一种城市体检智能体的任务编排与可信复核方法",
  abstract: "本发明公开一种城市体检智能体任务编排方法。",
  claims: "1. 一种方法，包括生成任务有向无环图并执行可信复核。",
  description: "本发明涉及城市体检智能体任务编排技术领域。",
  drawing_description: "图1为方法流程图。",
  mermaid: "",
  image_prompt: "",
  review_findings: [],
  citations: [],
  generation_logs: [],
};

const project: ProjectRecord = {
  id: "project-1",
  name: "城市体检智能体的任务编排与可信复核方法",
  draft_text: "城市体检智能体任务编排。",
  patent_type: "invention",
  package: draftPackage,
  created_at: "2026-06-25T00:00:00Z",
  updated_at: "2026-06-25T00:00:00Z",
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

const filingReport: FilingReadinessReport = {
  id: "filing-1",
  project_id: project.id,
  draft_package_hash: "draft-hash",
  status: "warning",
  rules_version: "v1",
  issues: [],
  created_at: "2026-06-25T00:01:00Z",
};

const worksheet: ClaimDefenseWorksheet = {
  id: "worksheet-1",
  project_id: project.id,
  status: "reviewed",
  source: "draft",
  feature_records: [],
  defense_recommendations: [],
  support_gaps: [],
  notes: [],
  created_at: "2026-06-25T00:02:00Z",
};

const completionRun: DraftCompletionRun = {
  id: "completion-1",
  project_id: project.id,
  snapshot_hash: "snapshot-hash",
  draft_package_hash: "draft-hash",
  status: "completed",
  issues: [],
  tasks: [],
  patches: [],
  support_matrix: [],
  scorecard: {
    authorization_stability: 80,
    protection_scope: 75,
    support_strength: 70,
    prior_art_distinction: 65,
    filing_maturity: 85,
    official_hygiene: 90,
    overall: 78,
  },
  notes: [],
  created_at: "2026-06-25T00:03:00Z",
};

const blockedCompileRun: OfficialCompileRun = {
  id: "compile-blocked",
  project_id: project.id,
  status: "blocked",
  source_draft_hash: "draft-hash",
  official_package_hash: "",
  official_package: null,
  contamination_removed: [],
  blocked_items: [{ category: "format_pollution", message: "正式稿包含 Markdown 格式污染。" }],
  sidecar_notes: [],
  logs: [],
  created_at: "2026-06-25T00:04:00Z",
  updated_at: "2026-06-25T00:04:00Z",
};

const actionableBlockedCompileRun: OfficialCompileRun = {
  ...blockedCompileRun,
  contamination_removed: [
    {
      category: "format_pollution",
      section: "claims",
      pattern: "markdown_heading",
      text: "### 权利要求书",
    },
    {
      category: "support_gap",
      section: "description",
      pattern: "support_gaps",
      text: "### support_gaps（提交前需补强的实验或工程材料）",
    },
  ],
};

const noop = () => undefined;
const asyncNoop = async () => undefined;

describe("GuidedPatentFlow official compile display", () => {
  it("shows the current blocked official compile run instead of treating it as missing", () => {
    render(
      <GuidedPatentFlowView
        project={project}
        materials={[]}
        disclosures={[]}
        deliberations={[]}
        patentPoints={[]}
        formulaRequirement={null}
        formulaRuns={[]}
        officialCompileRuns={[blockedCompileRun]}
        currentSourceDraftHash="draft-hash"
        postDraftReviews={[]}
        currentDraftHash="draft-hash"
        currentPackage={draftPackage}
        agentDoctor={null}
        selectedDeliberationProviders={[]}
        selectedDeliberationParticipantProviders={[]}
        selectedFormulaProviders={[]}
        filingReports={[filingReport]}
        worksheets={[worksheet]}
        completionRuns={[completionRun]}
        externalDraftSources={[]}
        externalDraftIntakeRuns={[]}
        busy=""
        busyElapsedSeconds={0}
        onCreateIdeaProject={asyncNoop}
        onCreateExternalDraft={asyncNoop}
        onUploadExternalDraft={asyncNoop}
        onStartExternalDraftIntake={asyncNoop}
        onConfirmExternalDraftIntake={asyncNoop}
        onUploadMaterial={noop}
        disclosureResearchMode="standard"
        onChangeDisclosureResearchMode={noop}
        onStartDisclosure={noop}
        onCancelDisclosureRun={noop}
        onRetryDisclosureRun={noop}
        onSelectPatentPoint={noop}
        onStartDeliberation={noop}
        onCancelDeliberationRun={noop}
        onRetryDeliberationRun={noop}
        onStartFormula={noop}
        onCancelFormulaRun={noop}
        onRetryFormulaRun={noop}
        onStartOfficialCompile={noop}
        onStartKimiLanguagePolish={noop}
        onStartPostDraftReview={noop}
        onApplyOfficialCompileCleanup={noop}
        onApplyPostDraftSafePatches={noop}
        onSaveDraftPackage={noop}
        onCancelPostDraftReviewRun={noop}
        onRetryPostDraftReviewRun={noop}
        onToggleDeliberationProvider={noop}
        onToggleDeliberationParticipantProvider={noop}
        onToggleFormulaProvider={noop}
        onGenerateDraft={noop}
        onRunQualityChecks={noop}
        onImproveScore={noop}
        onAcceptPatch={noop}
        onAcceptAllPatches={noop}
        onOpenExpertTool={noop}
      />,
    );

    expect(screen.getByText("当前正式稿编译已阻断")).toBeTruthy();
    expect(screen.getByText(/正式稿包含 Markdown 格式污染/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "编译报告" })).toHaveAttribute(
      "href",
      "/api/projects/project-1/official-compile-runs/compile-blocked/report.md",
    );
    expect(screen.queryByText("已有正式稿记录，但不属于当前源稿。请重新生成正式稿。")).toBeNull();
  });

  it("shows actionable cleanup text for a blocked compile and applies it", () => {
    const onApplyOfficialCompileCleanup = vi.fn();
    render(
      <GuidedPatentFlowView
        project={project}
        materials={[]}
        disclosures={[]}
        deliberations={[]}
        patentPoints={[]}
        formulaRequirement={null}
        formulaRuns={[]}
        officialCompileRuns={[actionableBlockedCompileRun]}
        currentSourceDraftHash="draft-hash"
        postDraftReviews={[]}
        currentDraftHash="draft-hash"
        currentPackage={draftPackage}
        agentDoctor={null}
        selectedDeliberationProviders={[]}
        selectedDeliberationParticipantProviders={[]}
        selectedFormulaProviders={[]}
        filingReports={[filingReport]}
        worksheets={[worksheet]}
        completionRuns={[completionRun]}
        externalDraftSources={[]}
        externalDraftIntakeRuns={[]}
        busy=""
        busyElapsedSeconds={0}
        onCreateIdeaProject={asyncNoop}
        onCreateExternalDraft={asyncNoop}
        onUploadExternalDraft={asyncNoop}
        onStartExternalDraftIntake={asyncNoop}
        onConfirmExternalDraftIntake={asyncNoop}
        onUploadMaterial={noop}
        disclosureResearchMode="standard"
        onChangeDisclosureResearchMode={noop}
        onStartDisclosure={noop}
        onCancelDisclosureRun={noop}
        onRetryDisclosureRun={noop}
        onSelectPatentPoint={noop}
        onStartDeliberation={noop}
        onCancelDeliberationRun={noop}
        onRetryDeliberationRun={noop}
        onStartFormula={noop}
        onCancelFormulaRun={noop}
        onRetryFormulaRun={noop}
        onStartOfficialCompile={noop}
        onStartKimiLanguagePolish={noop}
        onStartPostDraftReview={noop}
        onApplyOfficialCompileCleanup={onApplyOfficialCompileCleanup}
        onApplyPostDraftSafePatches={noop}
        onSaveDraftPackage={noop}
        onCancelPostDraftReviewRun={noop}
        onRetryPostDraftReviewRun={noop}
        onToggleDeliberationProvider={noop}
        onToggleDeliberationParticipantProvider={noop}
        onToggleFormulaProvider={noop}
        onGenerateDraft={noop}
        onRunQualityChecks={noop}
        onImproveScore={noop}
        onAcceptPatch={noop}
        onAcceptAllPatches={noop}
        onOpenExpertTool={noop}
      />,
    );

    expect(screen.getByText("可自动清理的源稿痕迹")).toBeTruthy();
    expect(screen.getByText("### 权利要求书")).toBeTruthy();
    expect(screen.getByText("### support_gaps（提交前需补强的实验或工程材料）")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /清理源稿并回到质量检查/ }));

    expect(onApplyOfficialCompileCleanup).toHaveBeenCalledWith("compile-blocked");
  });
});
