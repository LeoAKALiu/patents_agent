import { describe, expect, it } from "vitest";

import type {
  ClaimDefenseWorksheet,
  DraftCompletionRun,
  ExportReadiness,
  FilingReadinessReport,
  OfficialCompileRun,
  PatentPointCandidate,
  PostDraftReviewRun,
  ProjectRecord,
} from "@/api";
import type { ProjectWorkspaceState } from "@/features/projects/ProjectWorkspace";

import { deriveWorkbenchState } from "./selectors";

function makeProject(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    id: "project-1",
    name: "城市体检智能体",
    draft_text: "一种城市体检智能体方案",
    patent_type: "invention",
    package: null,
    created_at: "2026-06-29T08:00:00Z",
    updated_at: "2026-06-29T08:00:00Z",
    applicant: "",
    inventors: "",
    technical_field: "",
    background: "",
    pain_point: "",
    technical_solution: "",
    innovation: "",
    embodiments: "",
    beneficial_effects: "",
    ...overrides,
  };
}

function makeProjectPackage(): NonNullable<ProjectRecord["package"]> {
  return {
    title: "城市体检智能体",
    abstract: "摘要",
    claims: "权利要求书",
    description: "说明书",
    drawing_description: "附图说明",
    mermaid: "",
    image_prompt: "",
    review_findings: [],
    citations: [],
    generation_logs: [],
  };
}

function makePatentPoint(): PatentPointCandidate {
  return {
    id: "point-1",
    title: "城市体检智能体任务编排",
    technical_problem: "城市体征数据难以可信复核。",
    innovation: "任务图与证据链联动。",
    technical_solution: "生成任务 DAG 并绑定证据包。",
    beneficial_effects: ["提升复核效率。"],
    protection_focus: ["任务编排"],
    grantability_score: 0.78,
    rationale: "主线发明点",
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
  };
}

function makeFilingReport(hash = "draft-hash"): FilingReadinessReport {
  return {
    id: "filing-1",
    project_id: "project-1",
    draft_package_hash: hash,
    status: "clean",
    rules_version: "v1",
    issues: [],
    created_at: "2026-06-29T08:10:00Z",
  };
}

function makeWorksheet(hash = "draft-hash"): ClaimDefenseWorksheet {
  return {
    id: "worksheet-1",
    project_id: "project-1",
    draft_package_hash: hash,
    status: "reviewed",
    source: "draft",
    feature_records: [],
    defense_recommendations: [],
    support_gaps: [],
    notes: [],
    created_at: "2026-06-29T08:15:00Z",
  };
}

function makeCompletionRun(hash = "draft-hash"): DraftCompletionRun {
  return {
    id: "completion-1",
    project_id: "project-1",
    snapshot_hash: "snapshot-hash",
    draft_package_hash: hash,
    status: "completed",
    issues: [],
    tasks: [],
    patches: [],
    support_matrix: [],
    scorecard: {
      authorization_stability: 0.9,
      protection_scope: 0.85,
      support_strength: 0.88,
      prior_art_distinction: 0.82,
      filing_maturity: 0.9,
      official_hygiene: 0.95,
      overall: 0.88,
    },
    notes: [],
    created_at: "2026-06-29T08:18:00Z",
  };
}

function makeOfficialCompileRun(hash = "draft-hash"): OfficialCompileRun {
  return {
    id: "compile-1",
    project_id: "project-1",
    status: "completed",
    source_draft_hash: hash,
    official_package_hash: "official-hash",
    official_package: {
      title: "城市体检智能体",
      abstract: "摘要",
      claims: "权利要求书",
      description: "说明书",
      drawing_description: "附图说明",
      figure_plan: [],
      compile_warnings: [],
      source_draft_hash: hash,
      official_package_hash: "official-hash",
    },
    contamination_removed: [],
    blocked_items: [],
    sidecar_notes: [],
    logs: [],
    created_at: "2026-06-29T08:20:00Z",
    updated_at: "2026-06-29T08:20:00Z",
  };
}

function makePostDraftReview(overrides: Partial<PostDraftReviewRun> = {}): PostDraftReviewRun {
  return {
    id: "review-1",
    project_id: "project-1",
    status: "completed",
    providers: [],
    prompt_pack_version: "v1",
    draft_package_hash: "draft-hash",
    official_compile_run_id: "compile-1",
    official_package_hash: "official-hash",
    role_results: [],
    chair_result: null,
    export_allowed: false,
    blocking_issues: ["权利要求1仍含内部评审说明"],
    contamination_hits: [],
    logs: [],
    created_at: "2026-06-29T08:30:00Z",
    updated_at: "2026-06-29T08:30:00Z",
    ...overrides,
  };
}

function makeExportReadiness(overrides: Partial<ExportReadiness> = {}): ExportReadiness {
  return {
    export_allowed: false,
    draft_required: false,
    quality_required: false,
    official_compile_required: false,
    post_draft_review_required: true,
    next_action: "run_post_draft_review",
    reason: "成稿会审阻断导出",
    review_gate_status: "blocked",
    review_blocking_issues: ["权利要求1仍含内部评审说明"],
    ...overrides,
  };
}

function makeProjectState(overrides: Partial<ProjectWorkspaceState> = {}): ProjectWorkspaceState {
  return {
    startChoice: null,
    selectedProject: makeProject(),
    projects: [],
    projectMaterials: [],
    disclosureRuns: [],
    deliberationRuns: [],
    visiblePatentPoints: [],
    formulaRequirement: null,
    formulaRuns: [],
    officialCompileRuns: [],
    currentSourceDraftHash: "",
    postDraftReviews: [],
    currentDraftHash: "",
    currentPackage: null,
    agentDoctor: null,
    selectedDeliberationProviders: [],
    selectedDeliberationParticipantProviders: [],
    selectedFormulaProviders: [],
    filingReports: [],
    worksheets: [],
    completionRuns: [],
    externalDraftSources: [],
    externalDraftIntakeRuns: [],
    busy: "",
    busyElapsedSeconds: 0,
    disclosureResearchMode: "standard",
    ...overrides,
  };
}

describe("deriveWorkbenchState", () => {
  it("points an empty workspace at project creation", () => {
    const state = deriveWorkbenchState({
      projectState: makeProjectState({ selectedProject: null, projects: [] }),
      exportReadiness: null,
    });

    expect(state.hasProject).toBe(false);
    expect(state.nextAction.label).toBe("创建项目");
    expect(state.primaryTarget).toBe("workbench-start");
    expect(state.stepGroups.map((group) => group.label)).toEqual(["构思输入", "生成成稿", "提交放行"]);
    expect(state.stepGroups.flatMap((group) => group.steps)).toHaveLength(9);
  });

  it("sends blocked post-draft review work to documents", () => {
    const blockedState = deriveWorkbenchState({
      projectState: makeProjectState({
        officialCompileRuns: [makeOfficialCompileRun()],
        postDraftReviews: [makePostDraftReview()],
        currentSourceDraftHash: "draft-hash",
      }),
      exportReadiness: makeExportReadiness(),
    });

    expect(blockedState.nextAction.label).toBe("处理成稿会审阻断项");
    expect(blockedState.primaryTarget).toBe("documents");
    expect(blockedState.riskSummary.blockingCount).toBe(1);
    expect(blockedState.riskSummary.exportLocked).toBe(true);
  });

  it("sends export-ready projects to export", () => {
    const exportReadyState = deriveWorkbenchState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makeProjectPackage() }),
        currentPackage: makeProjectPackage(),
        currentSourceDraftHash: "draft-hash",
        filingReports: [makeFilingReport()],
        officialCompileRuns: [makeOfficialCompileRun()],
        postDraftReviews: [makePostDraftReview({ export_allowed: true, blocking_issues: [] })],
      }),
      exportReadiness: makeExportReadiness({
        export_allowed: true,
        post_draft_review_required: false,
        next_action: "export_ready",
        reason: "可导出",
        review_gate_status: "passed",
        review_blocking_issues: [],
      }),
    });

    expect(exportReadyState.nextAction.label).toBe("导出正式稿");
    expect(exportReadyState.primaryTarget).toBe("export");
    expect(exportReadyState.riskSummary.exportReady).toBe(true);
  });

  it("keeps ordinary guided flow on the workbench with guided labels", () => {
    const state = deriveWorkbenchState({
      projectState: makeProjectState(),
      exportReadiness: null,
    });

    expect(state.nextAction.label).toBe("提炼发明点");
    expect(state.primaryTarget).toBe("workbench-start");
  });

  it("exposes the deliberation provider-count block reason", () => {
    const state = deriveWorkbenchState({
      projectState: makeProjectState({
        visiblePatentPoints: [makePatentPoint()],
        selectedDeliberationProviders: ["codex", "deepseek"],
      }),
      exportReadiness: null,
    });

    expect(state.currentStepId).toBe("deliberation");
    expect(state.primaryTarget).toBe("workbench-start");
    expect(state.primaryActionBlockReason).toBe("至少需要 Codex 主席 + 2 个可用专家才能启动会审。");
  });

  it("exposes the post-draft review provider-count block reason", () => {
    const state = deriveWorkbenchState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makeProjectPackage() }),
        currentSourceDraftHash: "draft-hash",
        filingReports: [makeFilingReport()],
        worksheets: [makeWorksheet()],
        completionRuns: [makeCompletionRun()],
        officialCompileRuns: [makeOfficialCompileRun()],
        selectedDeliberationProviders: ["codex", "deepseek"],
      }),
      exportReadiness: null,
    });

    expect(state.currentStepId).toBe("postReview");
    expect(state.primaryTarget).toBe("workbench-start");
    expect(state.primaryActionBlockReason).toBe("至少需要 Codex 主席 + 2 个可用专家才能启动成稿会审。");
  });

  it("uses guided busy labels for the running summary", () => {
    const state = deriveWorkbenchState({
      projectState: makeProjectState({ busy: "post-draft-review" }),
      exportReadiness: null,
    });

    expect(state.runSummary).toEqual({
      label: "正在运行成稿会审",
      busy: true,
    });
  });
});
