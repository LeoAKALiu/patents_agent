import { describe, expect, it } from "vitest";

import type {
  DraftPackage,
  ExportReadiness,
  OfficialCompileRun,
  PostDraftReviewRun,
  ProjectRecord,
} from "@/api";
import type { ProjectWorkspaceState } from "@/features/projects/ProjectWorkspace";

import { APPROVED_GATE_STATES, deriveDocumentRepairState } from "./selectors";

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

function makePackage(overrides: Partial<DraftPackage> = {}): DraftPackage {
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
    generation_logs: ["raw generation log should not render"],
    ...overrides,
  };
}

function makeOfficialCompileRun(overrides: Partial<OfficialCompileRun> = {}): OfficialCompileRun {
  return {
    id: "compile-1",
    project_id: "project-1",
    status: "completed",
    source_draft_hash: "draft-current",
    official_package_hash: "official-current",
    official_package: {
      title: "城市体检智能体正式稿",
      abstract: "正式摘要",
      claims: "正式权利要求书",
      description: "正式说明书",
      drawing_description: "正式附图说明",
      figure_plan: [],
      compile_warnings: [],
      source_draft_hash: "draft-current",
      official_package_hash: "official-current",
    },
    contamination_removed: [],
    blocked_items: [],
    sidecar_notes: [],
    logs: [],
    created_at: "2026-06-29T08:20:00Z",
    updated_at: "2026-06-29T08:20:00Z",
    ...overrides,
  };
}

function makePostDraftReview(overrides: Partial<PostDraftReviewRun> = {}): PostDraftReviewRun {
  return {
    id: "review-1",
    project_id: "project-1",
    status: "completed",
    providers: [],
    prompt_pack_version: "v1",
    draft_package_hash: "draft-current",
    official_compile_run_id: "compile-1",
    official_package_hash: "official-current",
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

describe("deriveDocumentRepairState", () => {
  it("reports no internal draft as the top conclusion", () => {
    const noDraft = deriveDocumentRepairState({
      projectState: makeProjectState({ selectedProject: makeProject({ package: null }) }),
      exportReadiness: null,
    });

    expect(noDraft.topConclusion).toBe("当前项目尚未生成内部初稿。");
    expect(noDraft.gates.internalDraft.state).toBe("等待生成");
  });

  it("routes blocked post-draft repair to the annotated tab", () => {
    const blocked = deriveDocumentRepairState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makePackage() }),
        currentPackage: makePackage(),
        currentDraftHash: "draft-current",
        currentSourceDraftHash: "draft-current",
        officialCompileRuns: [makeOfficialCompileRun()],
        postDraftReviews: [makePostDraftReview()],
      }),
      exportReadiness: makeExportReadiness(),
    });

    expect(blocked.topConclusion).toContain("阻断导出");
    expect(blocked.primaryAction.targetTab).toBe("annotated");
    expect(blocked.gates.export.state).toBe("导出锁定");
  });

  it("marks an official draft compiled from an old internal draft as stale", () => {
    const staleOfficial = deriveDocumentRepairState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makePackage() }),
        currentPackage: makePackage(),
        currentDraftHash: "draft-current",
        currentSourceDraftHash: "draft-current",
        officialCompileRuns: [
          makeOfficialCompileRun({
            source_draft_hash: "draft-old",
            official_package: {
              ...makeOfficialCompileRun().official_package!,
              source_draft_hash: "draft-old",
            },
          }),
        ],
      }),
      exportReadiness: makeExportReadiness({
        official_compile_required: true,
        next_action: "run_official_compile",
        review_gate_status: "missing",
        review_blocking_issues: [],
      }),
    });

    expect(staleOfficial.gates.officialCompile.state).toBe("已失效");
  });

  it("points export-ready projects at the export route", () => {
    const exportReady = deriveDocumentRepairState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makePackage() }),
        currentPackage: makePackage(),
        currentDraftHash: "draft-current",
        currentSourceDraftHash: "draft-current",
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

    expect(exportReady.primaryAction.label).toBe("导出正式稿");
    expect(exportReady.primaryAction.targetSection).toBe("export");
  });

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

  it("uses export-readiness next action before stale export artifacts", () => {
    const state = deriveDocumentRepairState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makePackage() }),
        currentPackage: makePackage(),
        currentDraftHash: "draft-current",
        currentSourceDraftHash: "draft-current",
        officialCompileRuns: [makeOfficialCompileRun()],
        postDraftReviews: [makePostDraftReview({ export_allowed: true, blocking_issues: [] })],
      }),
      exportReadiness: makeExportReadiness({
        export_allowed: false,
        quality_required: true,
        post_draft_review_required: false,
        next_action: "run_quality_checks",
        reason: "当前初稿尚未完成质量检查。",
        quality_done: false,
        review_gate_status: "passed",
        review_blocking_issues: [],
      }),
    });

    expect(state.gates.export.state).not.toBe("可导出");
    expect(state.primaryAction).toEqual({
      label: "运行质量检查",
      targetSection: "workbench",
    });
    expect(state.topConclusion).toBe("当前初稿尚未完成质量检查。");
  });

  it("uses only the approved gate vocabulary", () => {
    const state = deriveDocumentRepairState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makePackage() }),
        currentPackage: makePackage(),
        currentDraftHash: "draft-current",
        currentSourceDraftHash: "draft-current",
        officialCompileRuns: [makeOfficialCompileRun()],
        postDraftReviews: [makePostDraftReview()],
        busy: "post-draft-review",
      }),
      exportReadiness: makeExportReadiness({
        review_gate_status: "running",
      }),
    });

    for (const gate of Object.values(state.gates)) {
      expect(APPROVED_GATE_STATES).toContain(gate.state);
    }
  });

  it("elides version-chain short hashes without exposing complete values", () => {
    const veryShortHash = "abc";
    const shortButCompleteHash = "abc123def456";
    const state = deriveDocumentRepairState({
      projectState: makeProjectState({
        selectedProject: makeProject({ package: makePackage() }),
        currentPackage: makePackage(),
        currentDraftHash: veryShortHash,
        currentSourceDraftHash: veryShortHash,
        officialCompileRuns: [
          makeOfficialCompileRun({
            source_draft_hash: veryShortHash,
            official_package_hash: shortButCompleteHash,
            official_package: {
              ...makeOfficialCompileRun().official_package!,
              source_draft_hash: veryShortHash,
              official_package_hash: shortButCompleteHash,
            },
          }),
        ],
        postDraftReviews: [
          makePostDraftReview({
            draft_package_hash: veryShortHash,
            official_package_hash: shortButCompleteHash,
          }),
        ],
      }),
      exportReadiness: makeExportReadiness({
        current_source_draft_hash: veryShortHash,
        official_package_hash: shortButCompleteHash,
      }),
    });

    const internalDraftNode = state.versionChain.nodes.find((node) => node.id === "internalDraft");
    const officialCompileNode = state.versionChain.nodes.find((node) => node.id === "officialCompile");

    expect(internalDraftNode?.shortHash).toBe("a...");
    expect(internalDraftNode?.shortHash).not.toContain(veryShortHash);
    expect(officialCompileNode?.shortHash).toBe("abc123de...");
    expect(officialCompileNode?.shortHash).not.toContain(shortButCompleteHash);
  });
});
