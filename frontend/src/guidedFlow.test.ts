import { describe, expect, it } from "vitest";

import type {
  ClaimDefenseWorksheet,
  DisclosureRun,
  DraftCompletionRun,
  FilingReadinessReport,
  DeliberationRun,
  FormulaNeedAssessment,
  FormulaRun,
  OfficialCompileRun,
  PatentPointCandidate,
  PostDraftReviewRun,
  ProjectMaterial,
  ProjectRecord,
} from "./api";
import {
  defaultExpertToolId,
  defaultMainSectionId,
  buildPatentPointSelectionPayloads,
  deriveGuidedFlowState,
  expertToolGroups,
  guidedBusyLabel,
  guidedOperationLog,
  guidedStepLabels,
  mainSections,
  patentGoalModes,
  qualitySummaryFromRuns,
  selectCurrentOfficialCompileRun,
} from "./guidedFlow";

const projectWithIdea: ProjectRecord = {
  id: "p1",
  name: "外立面逆建模",
  draft_text: "一种外立面逆建模方法。",
  package: null,
  created_at: "2026-06-07T00:00:00Z",
  updated_at: "2026-06-07T00:00:00Z",
};

const processedMaterial: ProjectMaterial = {
  id: "m1",
  project_id: "p1",
  file_name: "交底.md",
  path: "data/materials/p1/m1.md",
  file_type: "md",
  status: "processed",
  text: "补充材料",
  warnings: [],
  metadata: {},
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
    export_warnings: [],
  },
  failures: [],
  events: ["done"],
};

const completedDeliberation: DeliberationRun = {
  id: "dr1",
  project_id: "p1",
  status: "completed",
  providers: ["codex", "gemini", "claude"],
  run_mode: "full",
  round_depth: "converged_two_round",
  trace: false,
  run_dir: "data/deliberation-runs/p1/dr1",
  stage_results: [
    ...["codex", "gemini", "claude"].map((provider) => ({
      phase: "opening",
      provider_id: provider,
      label: `opening ${provider}`,
      payload: {},
      status: "completed" as const,
    })),
    ...["pair codex-vs-gemini", "pair codex-vs-claude", "pair gemini-vs-claude"].map((label) => ({
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
      status: "completed",
    },
  ],
  strategy_brief: {
    summary: "会审建议收敛权利要求边界。",
    claim_strategy: ["方法独权", "系统独权"],
    description_strategy: ["补充实施例"],
    risk_controls: ["避免功能性概括"],
    agent_consensus: "三方一致建议先会审再生成。",
  },
  failures: [],
  events: ["run started", "strategy generated"],
  logs: [],
};

const failedDeliberation: DeliberationRun = {
  ...completedDeliberation,
  id: "dr-failed",
  status: "failed",
  strategy_brief: null,
  failures: [{ provider_id: "codex", phase: "opening", reason: "process_error", message: "codex failed" }],
  logs: [
    {
      level: "error",
      phase: "opening",
      provider_id: "codex",
      attempt: 1,
      message: "attempt failed",
      detail: "stderr: readonly db",
      repair_suggestion: "以后端非沙箱权限重启并检查 Codex 登录状态。",
      elapsed_ms: 20,
      created_at: "2026-06-07T00:00:00Z",
    },
  ],
};

const formulaRequired: FormulaNeedAssessment = {
  required: true,
  signals: ["置信度", "贡献矩阵", "增益"],
  reasons: ["项目文本包含公式型信号。"],
};

const formulaNotRequired: FormulaNeedAssessment = {
  required: false,
  signals: [],
  reasons: [],
};

const completedFormulaRun: FormulaRun = {
  id: "fr1",
  project_id: "p1",
  status: "completed",
  providers: ["codex", "gemini", "claude"],
  requirement: formulaRequired,
  package: {
    summary: "以指标置信度增益作为核心公式。",
    formula_blocks: [
      {
        id: "F01",
        name: "指标置信度增益",
        latex: "\\Delta C_i = C_i^{post} - C_i^{prior}",
        purpose: "衡量置信度提升。",
        claim_hook: "根据指标置信度增益生成任务包",
      },
    ],
    variable_definitions: [],
    derivation_notes: [],
    claim_hooks: ["写入任务优化目标"],
    description_insert: "公式F01用于计算置信度增益。",
    latex_markdown: "# 核心公式",
    generation_logs: [],
  },
  failures: [],
  events: ["formula package generated"],
  created_at: "2026-06-07T00:00:00Z",
  updated_at: "2026-06-07T00:00:00Z",
};

function filingReport(status: FilingReadinessReport["status"]): FilingReadinessReport {
  return {
    id: `fr-${status}`,
    project_id: "p1",
    draft_package_hash: "hash",
    rules_version: "v1",
    status,
    issues: [],
    created_at: "2026-06-02T00:00:00Z",
  };
}

const worksheet: ClaimDefenseWorksheet = {
  id: "w1",
  project_id: "p1",
  source: "generated_package",
  status: "reviewed",
  feature_records: [],
  defense_recommendations: [],
  support_gaps: [],
  notes: [],
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
    drawing_description: "附图说明",
    figure_plan: [],
    compile_warnings: [],
    source_draft_hash: "draft-hash",
    official_package_hash: "official-hash",
  },
  contamination_removed: [],
  blocked_items: [],
  sidecar_notes: [],
  logs: [],
  created_at: "2026-06-02T00:00:00Z",
  updated_at: "2026-06-02T00:00:00Z",
};

const blockedOfficialCompileRun: OfficialCompileRun = {
  ...completedOfficialCompileRun,
  id: "ocr-blocked",
  status: "blocked",
  official_package_hash: "",
  official_package: null,
  blocked_items: [{ category: "cross_project_contamination", message: "检测到其他项目标题" }],
};

const passedPostDraftReview: PostDraftReviewRun = {
  id: "pdr1",
  project_id: "p1",
  status: "completed",
  providers: ["codex", "gemini", "claude"],
  prompt_pack_version: "post-draft-review-v1",
  draft_package_hash: "draft-hash",
  official_compile_run_id: "ocr1",
  official_package_hash: "official-hash",
  role_results: [],
  chair_result: {
    status: "passed",
    export_allowed: true,
    blocking_issues: [],
    contamination_hits: [],
    claim_1_rewrite: "",
    system_claim_rewrite: "",
    abstract_rewrite: "",
    description_rewrite_tasks: [],
    official_safe_patches: [],
    attorney_memo: [],
    next_actions: [],
  },
  export_allowed: true,
  blocking_issues: [],
  contamination_hits: [],
  logs: [],
  created_at: "2026-06-02T00:00:00Z",
  updated_at: "2026-06-02T00:00:00Z",
};

function patentPoint(selected: boolean): PatentPointCandidate {
  return {
    id: selected ? "pp-selected" : "pp-candidate",
    title: "外立面点云逆建模",
    technical_problem: "人工建模效率低。",
    innovation: "从单图估计结构线并反推立面几何。",
    technical_solution: "检测楼层线、窗洞和立面边界后生成参数化模型。",
    beneficial_effects: ["提高逆建模效率"],
    protection_focus: ["图像到立面参数的转换链路"],
    grantability_score: 0.8,
    rationale: "材料中已有技术链路。",
    evidence_status: "feasible_unverified",
    source_type: "model",
    feasibility_basis: "已有视觉模型可支撑。",
    support_gaps: [],
    experiment_needed: [],
    moat_scores: {
      scope_width: 0.8,
      designaround_difficulty: 0.7,
      feasibility: 0.7,
      support_strength: 0.6,
      prior_art_distance: 0.6,
      strategic_value: 0.8,
    },
    claim_chart: [],
    selected,
  };
}

describe("guided flow navigation", () => {
  it("uses three main sections and keeps expert tools grouped", () => {
    expect(mainSections.map((item) => item.label)).toEqual(["专利生成", "项目", "专家工具"]);
    expect(expertToolGroups.map((group) => group.label)).toEqual(["知识库", "发明点", "交底与策略", "质检", "导出"]);
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
  });
});

describe("guided flow defaults", () => {
  it("opens on patent generation and keeps expert tools on knowledge import", () => {
    expect(defaultMainSectionId).toBe("generate");
    expect(defaultExpertToolId).toBe("build");
  });
});

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

describe("guidedBusyLabel", () => {
  it("translates internal busy keys into user-facing progress", () => {
    expect(guidedBusyLabel("guided-quality")).toBe("正在运行质量检查");
    expect(guidedBusyLabel("official-compile")).toBe("正在编译正式稿");
    expect(guidedBusyLabel("disclosure")).toBe("正在提炼发明点");
    expect(guidedBusyLabel("generate")).toBe("正在生成专利初稿");
    expect(guidedBusyLabel("")).toBe("");
  });
});

describe("guidedOperationLog", () => {
  it("returns terminal-style operation logs instead of ETA progress", () => {
    const log = guidedOperationLog("disclosure", 30);

    expect(log?.label).toBe("正在提炼发明点");
    expect(log?.lines.join("\n")).toContain("[00:00]");
    expect(log?.lines.join("\n")).toContain("等待模型或服务返回");
    expect(log?.lines.join("\n")).not.toContain("预计剩余");
  });

  it("logs official compile progress without ETA language", () => {
    const log = guidedOperationLog("official-compile", 8);

    expect(log?.label).toBe("正在编译正式稿");
    expect(log?.lines.join("\n")).toContain("生成正式稿包");
    expect(log?.lines.join("\n")).not.toContain("预计剩余");
  });

  it("keeps short project actions as concise system logs", () => {
    const log = guidedOperationLog("patent-point-select", 2);

    expect(log?.label).toBe("正在保存主路线和后备路线");
    expect(log?.lines.length).toBeGreaterThanOrEqual(2);
  });
});

describe("buildPatentPointSelectionPayloads", () => {
  it("keeps non-selected generated candidates as backup routes when a main route is selected", () => {
    const selected = patentPoint(false);
    const backup = {
      ...patentPoint(false),
      id: "pp-backup",
      title: "热红外补采路线",
      innovation: "根据热红外窗口补采围护结构证据。",
    };

    const payloads = buildPatentPointSelectionPayloads(selected, [selected, backup]);

    expect(payloads).toHaveLength(2);
    expect(payloads[0].candidateId).toBe(selected.id);
    expect(payloads[0].payload.selected).toBe(true);
    expect(payloads[0].payload.source_candidate_id).toBe(selected.id);
    expect(payloads[1].candidateId).toBe(backup.id);
    expect(payloads[1].payload.selected).toBe(false);
    expect(payloads[1].payload.source_candidate_id).toBe(backup.id);
  });
});

describe("deriveGuidedFlowState", () => {
  it("starts at idea intake when no project exists", () => {
    const state = deriveGuidedFlowState({
      project: null,
      materials: [],
      disclosures: [],
      deliberations: [],
      patentPoints: [],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(state.currentStepId).toBe("idea");
    expect(state.steps.map((step) => step.status)).toEqual([
      "current",
      "locked",
      "locked",
      "locked",
      "locked",
      "locked",
      "locked",
      "locked",
      "locked",
    ]);
  });

  it("moves to invention confirmation after disclosure is completed", () => {
    const state = deriveGuidedFlowState({
      project: projectWithIdea,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [],
      patentPoints: [],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(state.currentStepId).toBe("invention");
    expect(state.hasInventionCandidates).toBe(true);
    expect(state.hasConfirmedInventionPoint).toBe(false);
    expect(state.steps[0].status).toBe("done");
    expect(state.steps[1].status).toBe("current");
  });

  it("distinguishes available invention candidates from confirmed selections", () => {
    const state = deriveGuidedFlowState({
      project: projectWithIdea,
      materials: [processedMaterial],
      disclosures: [],
      deliberations: [],
      patentPoints: [patentPoint(false)],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(state.currentStepId).toBe("invention");
    expect(state.hasInventionCandidates).toBe(true);
    expect(state.hasConfirmedInventionPoint).toBe(false);
  });

  it("requires completed multi-agent deliberation before draft generation", () => {
    const selectedPoint = patentPoint(true);
    const awaitingDeliberation = deriveGuidedFlowState({
      project: projectWithIdea,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [],
      patentPoints: [selectedPoint],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(awaitingDeliberation.currentStepId).toBe("deliberation");
    expect(awaitingDeliberation.hasCompletedDeliberation).toBe(false);

    const readyForDraft = deriveGuidedFlowState({
      project: projectWithIdea,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [selectedPoint],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(readyForDraft.currentStepId).toBe("draft");
    expect(readyForDraft.hasCompletedDeliberation).toBe(true);
  });

  it("requires a completed formula package when formula assessment is required", () => {
    const selectedPoint = patentPoint(true);
    const awaitingFormula = deriveGuidedFlowState({
      project: projectWithIdea,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [selectedPoint],
      formulaRequirement: formulaRequired,
      formulaRuns: [],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(awaitingFormula.currentStepId).toBe("formula");
    expect(awaitingFormula.hasCompletedFormula).toBe(false);

    const readyForDraft = deriveGuidedFlowState({
      project: projectWithIdea,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [selectedPoint],
      formulaRequirement: formulaRequired,
      formulaRuns: [completedFormulaRun],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(readyForDraft.currentStepId).toBe("draft");
    expect(readyForDraft.hasCompletedFormula).toBe(true);
  });

  it("does not treat failed deliberation as completed", () => {
    const selectedPoint = patentPoint(true);
    const state = deriveGuidedFlowState({
      project: projectWithIdea,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [failedDeliberation],
      patentPoints: [selectedPoint],
      formulaRequirement: formulaNotRequired,
      formulaRuns: [],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(state.currentStepId).toBe("deliberation");
    expect(state.hasCompletedDeliberation).toBe(false);
  });

  it("requires official compile before post-draft review", () => {
    const packageProject = {
      ...projectWithIdea,
      package: {
        title: "一种外立面逆建模方法",
        abstract: "摘要",
        claims: "1. 一种方法。",
        description: "说明书",
        drawing_description: "附图说明",
        mermaid: "flowchart TD",
        image_prompt: "黑白线稿",
        review_findings: [],
        citations: [],
        generation_logs: [],
      },
    };
    const state = deriveGuidedFlowState({
      project: packageProject,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
    });

    expect(state.currentStepId).toBe("officialCompile");
    expect(state.hasCompletedOfficialCompile).toBe(false);
    expect(state.exportReady).toBe(false);
  });

  it("blocked official compile does not advance", () => {
    const state = deriveGuidedFlowState({
      project: {
        ...projectWithIdea,
        package: {
          title: "一种外立面逆建模方法",
          abstract: "摘要",
          claims: "1. 一种方法。",
          description: "说明书",
          drawing_description: "附图说明",
          mermaid: "flowchart TD",
          image_prompt: "黑白线稿",
          review_findings: [],
          citations: [],
          generation_logs: [],
        },
      },
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
      officialCompileRuns: [blockedOfficialCompileRun],
    });

    expect(state.currentStepId).toBe("officialCompile");
    expect(state.hasCompletedOfficialCompile).toBe(false);
    expect(state.exportReady).toBe(false);
  });

  it("completed official compile moves to postReview", () => {
    const state = deriveGuidedFlowState({
      project: {
        ...projectWithIdea,
        package: {
          title: "一种外立面逆建模方法",
          abstract: "摘要",
          claims: "1. 一种方法。",
          description: "说明书",
          drawing_description: "附图说明",
          mermaid: "flowchart TD",
          image_prompt: "黑白线稿",
          review_findings: [],
          citations: [],
          generation_logs: [],
        },
      },
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
      officialCompileRuns: [completedOfficialCompileRun],
    });

    expect(state.currentStepId).toBe("postReview");
    expect(state.hasCompletedOfficialCompile).toBe(true);
    expect(state.exportReady).toBe(false);
  });

  it("requires passed post-draft review after official compile", () => {
    const packageProject = {
      ...projectWithIdea,
      package: {
        title: "一种外立面逆建模方法",
        abstract: "摘要",
        claims: "1. 一种方法。",
        description: "说明书",
        drawing_description: "附图说明",
        mermaid: "flowchart TD",
        image_prompt: "黑白线稿",
        review_findings: [],
        citations: [],
        generation_logs: [],
      },
    };

    const passedState = deriveGuidedFlowState({
      project: packageProject,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
      officialCompileRuns: [completedOfficialCompileRun],
      postDraftReviews: [passedPostDraftReview],
    });

    expect(passedState.currentStepId).toBe("export");
    expect(passedState.exportReady).toBe(true);
    expect(passedState.steps.map((step) => step.status)).toEqual([
      "done",
      "done",
      "done",
      "done",
      "done",
      "done",
      "done",
      "done",
      "current",
    ]);
  });

  it("uses latest completed compile for the current source when a newer run is blocked", () => {
    const packageProject = {
      ...projectWithIdea,
      package: {
        title: "一种外立面逆建模方法",
        abstract: "摘要",
        claims: "1. 一种方法。",
        description: "说明书",
        drawing_description: "附图说明",
        mermaid: "flowchart TD",
        image_prompt: "黑白线稿",
        review_findings: [],
        citations: [],
        generation_logs: [],
      },
    };
    const blockedNewerCompileRun: OfficialCompileRun = {
      ...blockedOfficialCompileRun,
      created_at: "2026-06-02T01:00:00Z",
      updated_at: "2026-06-02T01:00:00Z",
    };
    const runs = [blockedNewerCompileRun, completedOfficialCompileRun];

    expect(selectCurrentOfficialCompileRun(runs, "draft-hash")?.id).toBe(completedOfficialCompileRun.id);

    const state = deriveGuidedFlowState({
      project: packageProject,
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
      officialCompileRuns: runs,
      currentSourceDraftHash: "draft-hash",
      postDraftReviews: [passedPostDraftReview],
    });

    expect(state.currentStepId).toBe("export");
    expect(state.hasCompletedOfficialCompile).toBe(true);
    expect(state.hasPassedPostDraftReview).toBe(true);
    expect(state.exportReady).toBe(true);
  });

  it("does not advance to export when post-draft review belongs to a different official compile", () => {
    const state = deriveGuidedFlowState({
      project: {
        ...projectWithIdea,
        package: {
          title: "一种外立面逆建模方法",
          abstract: "摘要",
          claims: "1. 一种方法。",
          description: "说明书",
          drawing_description: "附图说明",
          mermaid: "flowchart TD",
          image_prompt: "黑白线稿",
          review_findings: [],
          citations: [],
          generation_logs: [],
        },
      },
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
      officialCompileRuns: [completedOfficialCompileRun],
      postDraftReviews: [
        {
          ...passedPostDraftReview,
          id: "review-for-stale-compile",
          draft_package_hash: "stale-draft-hash",
          official_compile_run_id: "stale-compile",
          official_package_hash: "stale-official-hash",
        },
      ],
    });

    expect(state.currentStepId).toBe("postReview");
    expect(state.hasCompletedOfficialCompile).toBe(true);
    expect(state.hasPassedPostDraftReview).toBe(false);
    expect(state.exportReady).toBe(false);
  });

  it("uses the latest matching post-draft review instead of an older pass", () => {
    const state = deriveGuidedFlowState({
      project: {
        ...projectWithIdea,
        package: {
          title: "一种外立面逆建模方法",
          abstract: "摘要",
          claims: "1. 一种方法。",
          description: "说明书",
          drawing_description: "附图说明",
          mermaid: "flowchart TD",
          image_prompt: "黑白线稿",
          review_findings: [],
          citations: [],
          generation_logs: [],
        },
      },
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
      officialCompileRuns: [completedOfficialCompileRun],
      postDraftReviews: [
        {
          ...passedPostDraftReview,
          id: "older-pass",
          created_at: "2026-06-02T00:00:00Z",
          updated_at: "2026-06-02T00:00:00Z",
        },
        {
          ...passedPostDraftReview,
          id: "newer-block",
          export_allowed: false,
          blocking_issues: ["正式稿支持不足。"],
          created_at: "2026-06-02T00:01:00Z",
          updated_at: "2026-06-02T00:01:00Z",
        },
      ],
    });

    expect(state.currentStepId).toBe("postReview");
    expect(state.hasPassedPostDraftReview).toBe(false);
    expect(state.exportReady).toBe(false);
  });

  it("does not treat blocked post-draft review as export ready", () => {
    const state = deriveGuidedFlowState({
      project: {
        ...projectWithIdea,
        package: {
          title: "一种外立面逆建模方法",
          abstract: "摘要",
          claims: "1. 一种方法。",
          description: "说明书",
          drawing_description: "附图说明",
          mermaid: "flowchart TD",
          image_prompt: "黑白线稿",
          review_findings: [],
          citations: [],
          generation_logs: [],
        },
      },
      materials: [processedMaterial],
      disclosures: [completedDisclosure],
      deliberations: [completedDeliberation],
      patentPoints: [],
      filingReports: [filingReport("warning")],
      worksheets: [worksheet],
      completionRuns: [completionRun],
      officialCompileRuns: [completedOfficialCompileRun],
      postDraftReviews: [{ ...passedPostDraftReview, id: "blocked", export_allowed: false }],
    });

    expect(state.currentStepId).toBe("postReview");
    expect(state.exportReady).toBe(false);
  });
});

describe("qualitySummaryFromRuns", () => {
  it("summarizes formal gate status and scorecards", () => {
    const summary = qualitySummaryFromRuns({
      filingReport: filingReport("high_risk"),
      worksheet,
      completionRun,
    });

    expect(summary.statusLabel).toBe("高风险，等待成稿会审");
    expect(summary.authorizationStability).toBe(70);
    expect(summary.protectionScope).toBe(80);
    expect(summary.filingMaturity).toBe(75);
    expect(summary.officialExportAllowed).toBe(false);
  });
});

describe("guidedStepLabels", () => {
  it("uses user-action language instead of internal module names", () => {
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
  });
});
