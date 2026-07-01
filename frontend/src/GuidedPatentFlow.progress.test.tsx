import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GuidedPatentFlowView } from "./GuidedPatentFlow";
import type {
  DeliberationRun,
  DisclosureRun,
  PatentPointCandidate,
  ProjectRecord,
} from "./api";

const project: ProjectRecord = {
  id: "project-1",
  name: "城市体检智能体任务编排",
  draft_text: "一种城市体检智能体的任务编排与可信复核方法。",
  patent_type: "invention",
  package: null,
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

const disclosure: DisclosureRun = {
  id: "disclosure-1",
  project_id: project.id,
  status: "completed",
  trace: false,
  max_prior_art_results: 8,
  run_dir: "",
  stage_results: [],
  package: {
    title: "城市体检智能体交底书",
    summary: "交底摘要",
    materials_summary: "材料摘要",
    candidates: [],
    selected_candidate_id: null,
    prior_art_hits: [],
    prior_art_differences: "差异点",
    body_markdown: "正文",
    mermaid: "",
    image_prompt: "",
    self_check_findings: [],
    generation_logs: [],
    export_warnings: [],
  },
  failures: [],
  events: [],
};

const deliberation: DeliberationRun = {
  id: "deliberation-1",
  project_id: project.id,
  status: "completed",
  providers: ["codex", "deepseek", "kimicode"],
  run_mode: "full",
  round_depth: "converged_two_round",
  trace: false,
  run_dir: "",
  stage_results: [
    ...["codex", "deepseek", "kimicode"].map((provider) => ({
      phase: "opening",
      provider_id: provider,
      label: `opening ${provider}`,
      payload: {},
      status: "completed" as const,
    })),
    ...["pair codex-vs-deepseek", "pair codex-vs-kimicode", "pair deepseek-vs-kimicode"].map((label) => ({
      phase: "pair",
      provider_id: "codex",
      label,
      payload: {},
      status: "completed" as const,
    })),
    {
      phase: "chair",
      provider_id: "codex",
      label: "chair synthesis",
      payload: {},
      status: "completed" as const,
    },
  ],
  strategy_brief: {
    summary: "会审完成。",
    claim_strategy: [],
    description_strategy: [],
    risk_controls: [],
    agent_consensus: "一致通过。",
  },
  failures: [],
  events: [],
  logs: [],
};

const selectedPoint: PatentPointCandidate = {
  id: "point-1",
  title: "任务编排与可信复核",
  technical_problem: "多源结论难以复核。",
  innovation: "任务图与证据链联动。",
  technical_solution: "生成任务 DAG 并绑定证据包。",
  beneficial_effects: ["提升可追溯性。"],
  protection_focus: ["任务编排"],
  grantability_score: 0.78,
  evidence_status: "feasible_unverified",
  source_type: "model",
  feasibility_basis: "",
  support_gaps: [],
  experiment_needed: [],
  moat_scores: {
    scope_width: 0.7,
    designaround_difficulty: 0.7,
    feasibility: 0.8,
    support_strength: 0.6,
    prior_art_distance: 0.6,
    strategic_value: 0.7,
  },
  claim_chart: [],
  selected: true,
  rationale: "主路线",
};

const noop = () => undefined;
const asyncNoop = async () => undefined;

function renderFlow(overrides: Partial<React.ComponentProps<typeof GuidedPatentFlowView>> = {}) {
  const props: React.ComponentProps<typeof GuidedPatentFlowView> = {
    project,
    materials: [],
    disclosures: [disclosure],
    deliberations: [deliberation],
    patentPoints: [selectedPoint],
    formulaRequirement: { required: false, signals: [], reasons: [] },
    formulaRuns: [],
    officialCompileRuns: [],
    currentSourceDraftHash: "",
    postDraftReviews: [],
    currentDraftHash: "",
    currentPackage: null,
    agentDoctor: null,
    selectedDeliberationProviders: ["codex", "deepseek", "kimicode"],
    selectedDeliberationParticipantProviders: [],
    selectedFormulaProviders: [],
    filingReports: [],
    worksheets: [],
    completionRuns: [],
    externalDraftSources: [],
    externalDraftIntakeRuns: [],
    busy: "",
    busyElapsedSeconds: 0,
    onCreateIdeaProject: asyncNoop,
    onCreateExternalDraft: asyncNoop,
    onUploadExternalDraft: asyncNoop,
    onStartExternalDraftIntake: asyncNoop,
    onConfirmExternalDraftIntake: asyncNoop,
    onUploadMaterial: noop,
    disclosureResearchMode: "standard",
    onChangeDisclosureResearchMode: noop,
    onStartDisclosure: noop,
    onCancelDisclosureRun: noop,
    onRetryDisclosureRun: noop,
    onSelectPatentPoint: noop,
    onStartDeliberation: noop,
    onCancelDeliberationRun: noop,
    onRetryDeliberationRun: noop,
    onStartFormula: noop,
    onCancelFormulaRun: noop,
    onRetryFormulaRun: noop,
    onStartOfficialCompile: noop,
    onStartKimiLanguagePolish: noop,
    onStartPostDraftReview: noop,
    onApplyOfficialCompileCleanup: noop,
    onApplyPostDraftSafePatches: noop,
    onSaveDraftPackage: noop,
    onCancelPostDraftReviewRun: noop,
    onRetryPostDraftReviewRun: noop,
    onToggleDeliberationProvider: noop,
    onToggleDeliberationParticipantProvider: noop,
    onToggleFormulaProvider: noop,
    onGenerateDraft: noop,
    onRunQualityChecks: noop,
    onImproveScore: noop,
    onAcceptPatch: noop,
    onAcceptAllPatches: noop,
    onOpenExpertTool: noop,
    ...overrides,
  };
  return render(<GuidedPatentFlowView {...props} />);
}

describe("GuidedPatentFlow progress action", () => {
  it("shows the next-step button for the current workflow action", () => {
    renderFlow();

    expect(screen.getByRole("button", { name: /下一步：生成专利初稿/ })).toBeEnabled();
  });

  it("does not show first-mile jargon while waiting for project intake", () => {
    renderFlow({
      project: null,
      disclosures: [],
      deliberations: [],
      patentPoints: [],
    });

    expect(screen.getByRole("button", { name: /下一步：填写并创建项目/ })).toBeDisabled();
    expect(screen.queryByText("等待首 Mile 输入")).not.toBeInTheDocument();
    expect(screen.queryByText(/首 Mile/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/首 Mile/)).not.toBeInTheDocument();
  });

  it("returns to the current step without starting it while browsing a completed step", () => {
    const onGenerateDraft = vi.fn();
    renderFlow({ onGenerateDraft });

    fireEvent.click(screen.getByRole("button", { name: /多智能体会审/ }));
    fireEvent.click(screen.getByRole("button", { name: /回到当前步骤/ }));

    expect(onGenerateDraft).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /下一步：生成专利初稿/ })).toBeEnabled();
  });
});
