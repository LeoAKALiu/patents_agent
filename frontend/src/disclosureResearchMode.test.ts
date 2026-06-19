import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { startProjectDisclosure } from "./api";
import type {
  DeliberationRun,
  DisclosureRun,
  DraftCompletionRun,
  FilingReadinessReport,
  FormulaNeedAssessment,
  FormulaRun,
  OfficialCompileRun,
  PatentPointCandidate,
  PostDraftReviewRun,
  ProjectMaterial,
  ProjectRecord,
} from "./api";
import { deriveGuidedFlowState } from "./guidedFlow";

// --- API payload --------------------------------------------------------

describe("startProjectDisclosure", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "run-1", status: "queued" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("defaults research_mode to standard when not specified", async () => {
    await startProjectDisclosure("p1");
    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
    expect(calls).toHaveLength(1);
    const body = JSON.parse((calls[0][1] as RequestInit).body as string);
    expect(body.research_mode).toBe("standard");
    expect(body.trace).toBe(false);
    expect(body.max_prior_art_results).toBe(8);
  });

  it("forwards free_deep_research mode to the backend", async () => {
    await startProjectDisclosure("p1", true, "free_deep_research");
    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
    expect(calls).toHaveLength(1);
    const body = JSON.parse((calls[0][1] as RequestInit).body as string);
    expect(body.research_mode).toBe("free_deep_research");
    expect(body.trace).toBe(true);
  });
});

// --- Flow gating ---------------------------------------------------------

const project: ProjectRecord = {
  id: "p1",
  name: "图像缺陷识别",
  draft_text: "一种基于神经网络的图像缺陷识别方法。",
  patent_type: "invention",
  package: null,
  created_at: "2026-06-07T00:00:00Z",
  updated_at: "2026-06-07T00:00:00Z",
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

const processedMaterial: ProjectMaterial = {
  id: "m1",
  project_id: "p1",
  file_name: "draft.txt",
  path: "data/materials/p1/m1.txt",
  file_type: "txt",
  status: "processed",
  text: "draft",
  warnings: [],
  metadata: {},
};

const deepResearchDisclosure: DisclosureRun = {
  id: "d1",
  project_id: "p1",
  status: "completed",
  trace: false,
  max_prior_art_results: 8,
  research_mode: "free_deep_research",
  run_dir: "data/disclosures/p1/d1",
  stage_results: [
    { phase: "project_scan", payload: { summary: "ok" } },
    { phase: "deep_research_plan", payload: { search_themes: [] } },
    { phase: "deep_research_evidence", payload: { count: 1 } },
    { phase: "deep_research_final", payload: { summary: "done" } },
  ],
  package: {
    title: "图像缺陷识别交底书",
    summary: "交底摘要",
    materials_summary: "材料摘要",
    candidates: [],
    selected_candidate_id: null,
    prior_art_hits: [],
    prior_art_differences: "本地材料生成。\n\n补充现有技术差异分析：\n差异要点：闭环反馈。",
    body_markdown: "交底正文",
    mermaid: "flowchart TD",
    image_prompt: "黑白线稿",
    self_check_findings: [],
    generation_logs: [
      "free_deep_research: internal supporting research packet generated; does not replace deliberation or official export gate.",
    ],
    export_warnings: [],
  },
  failures: [],
  events: ["done"],
};

describe("free deep research disclosure does not skip gates", () => {
  const emptyDeliberations: DeliberationRun[] = [];
  const emptyFormulaRuns: FormulaRun[] = [];
  const emptyFilingReports: FilingReadinessReport[] = [];
  const emptyCompletionRuns: DraftCompletionRun[] = [];
  const emptyOfficialCompileRuns: OfficialCompileRun[] = [];
  const emptyPostReviews: PostDraftReviewRun[] = [];
  const formulaNotRequired: FormulaNeedAssessment = {
    required: false,
    signals: [],
    reasons: [],
  };
  const candidate: PatentPointCandidate = {
    id: "p1",
    title: "图像缺陷识别",
    technical_problem: "效率低",
    innovation: "神经网络",
    technical_solution: "采集图像并检测",
    beneficial_effects: [],
    protection_focus: ["方法"],
    grantability_score: 0.6,
    rationale: "",
    evidence_status: "feasible_unverified",
    source_type: "user",
    feasibility_basis: "",
    support_gaps: [],
    experiment_needed: [],
    moat_scores: {
      scope_width: 0,
      designaround_difficulty: 0,
      feasibility: 0,
      support_strength: 0,
      prior_art_distance: 0,
      strategic_value: 0,
    },
    claim_chart: [],
    selected: true,
  };

  it("requires deliberation, official compile, and post-draft review after a free_deep_research disclosure", () => {
    const state = deriveGuidedFlowState({
      project,
      materials: [processedMaterial],
      disclosures: [deepResearchDisclosure],
      deliberations: emptyDeliberations,
      patentPoints: [candidate],
      formulaRequirement: formulaNotRequired,
      formulaRuns: emptyFormulaRuns,
      filingReports: emptyFilingReports,
      worksheets: [],
      completionRuns: emptyCompletionRuns,
      officialCompileRuns: emptyOfficialCompileRuns,
      currentSourceDraftHash: "",
      postDraftReviews: emptyPostReviews,
    });

    // After a successful disclosure (deep research or not) the flow advances to
    // the invention/draft-side of the funnel, *not* directly to export.
    expect(state.currentStepId).not.toBe("export");
    expect(state.currentStepId).not.toBe("postReview");
    expect(state.currentStepId).not.toBe("officialCompile");

    // Deliberation step is reachable but not yet complete.
    const deliberationStep = state.steps.find((step) => step.id === "deliberation");
    expect(deliberationStep).toBeDefined();
    expect(deliberationStep?.status).not.toBe("done");

    // Official compile and post-review still gated.
    const officialCompileStep = state.steps.find((step) => step.id === "officialCompile");
    expect(officialCompileStep?.status).not.toBe("done");
    const postReviewStep = state.steps.find((step) => step.id === "postReview");
    expect(postReviewStep?.status).not.toBe("done");

    // The flow's terminal "export ready" gate stays closed.
    expect(state.exportReady).toBe(false);
    expect(state.hasCompletedDeliberation).toBe(false);
    expect(state.hasCompletedOfficialCompile).toBe(false);
    expect(state.hasPassedPostDraftReview).toBe(false);
  });
});
