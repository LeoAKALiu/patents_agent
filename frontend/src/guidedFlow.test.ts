import { describe, expect, it } from "vitest";

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
  defaultExpertToolId,
  defaultMainSectionId,
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
  });
});

describe("guided flow defaults", () => {
  it("opens on patent generation and keeps expert tools on knowledge import", () => {
    expect(defaultMainSectionId).toBe("generate");
    expect(defaultExpertToolId).toBe("build");
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
      patentPoints: [patentPoint(false)],
      filingReports: [],
      worksheets: [],
      completionRuns: [],
    });

    expect(state.currentStepId).toBe("invention");
    expect(state.hasInventionCandidates).toBe(true);
    expect(state.hasConfirmedInventionPoint).toBe(false);
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
