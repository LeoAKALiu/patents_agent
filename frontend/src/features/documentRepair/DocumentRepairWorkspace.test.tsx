import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  DraftPackage,
  DraftReviewIssue,
  ExportReadiness,
  OfficialCompileRun,
  PostDraftRepairSession,
  PostDraftReviewRun,
  ProjectRecord,
} from "@/api";
import type {
  ProjectWorkspaceHandlers,
  ProjectWorkspaceState,
} from "@/features/projects/ProjectWorkspace";

import { DocumentRepairWorkspace } from "./DocumentRepairWorkspace";
import * as api from "@/api";

vi.mock("@/api", async () => {
  const actual = await vi.importActual<typeof import("@/api")>("@/api");
  return {
    ...actual,
    getPostDraftRepairSession: vi.fn(),
  };
});

function makeProject(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    id: "project-1",
    name: "城市体检智能体",
    draft_text: "技术方案",
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
    generation_logs: ["generation_logs should stay hidden"],
    ...overrides,
  };
}

function makeOfficialCompileRun(overrides: Partial<OfficialCompileRun> = {}): OfficialCompileRun {
  return {
    id: "compile-raw-run-id-1234567890",
    project_id: "project-1",
    status: "completed",
    source_draft_hash: "draft-current-1234567890abcdef",
    official_package_hash: "official-current-1234567890abcdef",
    official_package: {
      title: "城市体检智能体正式稿",
      abstract: "正式摘要",
      claims: "正式权利要求书",
      description: "正式说明书",
      drawing_description: "正式附图说明",
      figure_plan: [],
      compile_warnings: [],
      source_draft_hash: "draft-current-1234567890abcdef",
      official_package_hash: "official-current-1234567890abcdef",
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
    id: "review-raw-run-id-1234567890",
    project_id: "project-1",
    status: "completed",
    providers: [],
    prompt_pack_version: "v1",
    draft_package_hash: "draft-current-1234567890abcdef",
    official_compile_run_id: "compile-raw-run-id-1234567890",
    official_package_hash: "official-current-1234567890abcdef",
    role_results: [
      {
        role: "claims_reviewer",
        status: "blocked",
        blocking_issues: ["权利要求1仍含内部评审说明"],
        contamination_hits: [],
        rewrite_suggestions: [],
        official_safe_patches: ["official_safe_patches should stay hidden"],
        attorney_memo: [],
      },
    ],
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

function makeRepairIssue(overrides: Partial<DraftReviewIssue> = {}): DraftReviewIssue {
  return {
    id: "issue-1",
    kind: "blocking",
    severity: "high",
    source: "post_draft_review",
    message: "标题存在重复词汇方法方法",
    snippet: "方法方法",
    target_section: "title",
    anchor: {
      type: "text",
      section: "title",
      start: 0,
      end: 4,
      snippet: "方法方法",
    },
    status: "open",
    ...overrides,
  };
}

function makeRepairSession(overrides: Partial<PostDraftRepairSession> = {}): PostDraftRepairSession {
  return {
    project_id: "project-1",
    review_run_id: "review-raw-run-id-1234567890",
    draft_package_hash: "draft-current-1234567890abcdef",
    current_draft_hash: "draft-current-1234567890abcdef",
    stale: false,
    issues: [makeRepairIssue()],
    sections: {
      title: "一种基于城市体检指标置信度的无人机主动采集方法方法",
      abstract: "摘要",
      claims: "权利要求书",
      description: "说明书",
      drawing_description: "附图说明",
    },
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
    official_package_hash: "official-current-1234567890abcdef",
    current_source_draft_hash: "draft-current-1234567890abcdef",
    ...overrides,
  };
}

function makeProjectState(overrides: Partial<ProjectWorkspaceState> = {}): ProjectWorkspaceState {
  const currentPackage = makePackage();
  return {
    startChoice: null,
    selectedProject: makeProject({ package: currentPackage }),
    projects: [],
    projectMaterials: [],
    disclosureRuns: [],
    deliberationRuns: [],
    visiblePatentPoints: [],
    formulaRequirement: null,
    formulaRuns: [],
    officialCompileRuns: [makeOfficialCompileRun()],
    currentSourceDraftHash: "draft-current-1234567890abcdef",
    postDraftReviews: [makePostDraftReview()],
    currentDraftHash: "draft-current-1234567890abcdef",
    currentPackage,
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

function makeHandlers(overrides: Partial<ProjectWorkspaceHandlers> = {}): ProjectWorkspaceHandlers {
  return {
    onStartChoice: vi.fn(),
    onSelectProjectId: vi.fn(),
    onDeleteProject: vi.fn(),
    onCreateIdeaProject: vi.fn(),
    onCreateExternalDraft: vi.fn(),
    onUploadExternalDraft: vi.fn(),
    onStartExternalDraftIntake: vi.fn(),
    onConfirmExternalDraftIntake: vi.fn(),
    onUploadMaterial: vi.fn(),
    onChangeDisclosureResearchMode: vi.fn(),
    onStartDisclosure: vi.fn(),
    onCancelDisclosureRun: vi.fn(),
    onRetryDisclosureRun: vi.fn(),
    onSelectPatentPoint: vi.fn(),
    onStartDeliberation: vi.fn(),
    onCancelDeliberationRun: vi.fn(),
    onRetryDeliberationRun: vi.fn(),
    onStartFormula: vi.fn(),
    onCancelFormulaRun: vi.fn(),
    onRetryFormulaRun: vi.fn(),
    onStartOfficialCompile: vi.fn(),
    onStartKimiLanguagePolish: vi.fn(),
    onStartPostDraftReview: vi.fn(),
    onApplyOfficialCompileCleanup: vi.fn(),
    onApplyPostDraftSafePatches: vi.fn(),
    onSaveDraftPackage: vi.fn(),
    onCancelPostDraftReviewRun: vi.fn(),
    onRetryPostDraftReviewRun: vi.fn(),
    onToggleDeliberationProvider: vi.fn(),
    onToggleDeliberationParticipantProvider: vi.fn(),
    onToggleFormulaProvider: vi.fn(),
    onGenerateDraft: vi.fn(),
    onRunQualityChecks: vi.fn(),
    onImproveScore: vi.fn(),
    onAcceptPatch: vi.fn(),
    onAcceptAllPatches: vi.fn(),
    onOpenExpertTool: vi.fn(),
    ...overrides,
  };
}

describe("DocumentRepairWorkspace", () => {
  beforeEach(() => {
    vi.mocked(api.getPostDraftRepairSession).mockReset();
    vi.mocked(api.getPostDraftRepairSession).mockResolvedValue(makeRepairSession());
  });

  it("renders readable document-repair tabs and overview content", () => {
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState()}
        exportReadiness={makeExportReadiness()}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    for (const label of ["总览", "编辑", "问题", "标注修复", "版本"]) {
      expect(screen.getByRole("tab", { name: label })).toBeInTheDocument();
    }

    expect(screen.getByRole("heading", { name: /阻断导出/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "进入标注修复" })).toBeInTheDocument();
    expect(screen.getAllByText("内部初稿").length).toBeGreaterThan(0);
    expect(screen.getAllByText("正式稿").length).toBeGreaterThan(0);
    expect(screen.getByText("问题摘要")).toBeInTheDocument();
    expect(screen.getByText("最近记录")).toBeInTheDocument();
  });

  it("opens the annotated repair workspace tab with issue queue, document body, and inspector", async () => {
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState()}
        exportReadiness={makeExportReadiness()}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "进入标注修复" }));

    expect(await screen.findByText("问题队列")).toBeInTheDocument();
    expect(screen.getByText("正文定位")).toBeInTheDocument();
    expect(screen.getByText("修复面板")).toBeInTheDocument();
    expect(api.getPostDraftRepairSession).toHaveBeenCalledWith(
      "project-1",
      "review-raw-run-id-1234567890",
    );
  });

  it("routes export-ready primary action to the export destination", async () => {
    const navigate = vi.fn();
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState({
          postDraftReviews: [makePostDraftReview({ export_allowed: true, blocking_issues: [], role_results: [] })],
        })}
        exportReadiness={makeExportReadiness({
          export_allowed: true,
          post_draft_review_required: false,
          next_action: "export_ready",
          reason: "可导出",
          review_gate_status: "passed",
          review_blocking_issues: [],
        })}
        handlers={makeHandlers()}
        onNavigate={navigate}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "导出正式稿" }));

    expect(navigate).toHaveBeenCalledWith("export");
  });

  it("keeps raw internals out of the overview by default", () => {
    const { container } = render(
      <DocumentRepairWorkspace
        projectState={makeProjectState()}
        exportReadiness={makeExportReadiness()}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    const overview = within(screen.getByRole("tabpanel"));
    expect(overview.queryByText(/generation_logs/)).not.toBeInTheDocument();
    expect(overview.queryByText(/official_safe_patches/)).not.toBeInTheDocument();
    expect(container).not.toHaveTextContent("compile-raw-run-id-1234567890");
    expect(container).not.toHaveTextContent("review-raw-run-id-1234567890");
    expect(container).not.toHaveTextContent("draft-current-1234567890abcdef");
    expect(container).not.toHaveTextContent("official-current-1234567890abcdef");
  });

  it("saves section-level internal draft edits", async () => {
    const onSaveDraftPackage = vi.fn();
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState()}
        exportReadiness={makeExportReadiness()}
        handlers={makeHandlers({ onSaveDraftPackage })}
        onNavigate={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "编辑" }));
    expect(screen.getByLabelText("标题")).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("标题"));
    await userEvent.type(screen.getByLabelText("标题"), "新标题");
    await userEvent.click(screen.getByRole("button", { name: "保存当前初稿" }));

    expect(onSaveDraftPackage).toHaveBeenCalledWith(expect.objectContaining({ title: "新标题" }));
  });

  it("keeps unsaved draft edits through equivalent parent rerenders", async () => {
    const handlers = makeHandlers();
    const onNavigate = vi.fn();
    const { rerender } = render(
      <DocumentRepairWorkspace
        projectState={makeProjectState()}
        exportReadiness={makeExportReadiness()}
        handlers={handlers}
        onNavigate={onNavigate}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "编辑" }));
    await userEvent.clear(screen.getByLabelText("标题"));
    await userEvent.type(screen.getByLabelText("标题"), "暂存标题");

    rerender(
      <DocumentRepairWorkspace
        projectState={makeProjectState({ busyElapsedSeconds: 1 })}
        exportReadiness={makeExportReadiness()}
        handlers={handlers}
        onNavigate={onNavigate}
      />,
    );

    expect(screen.getByLabelText("标题")).toHaveValue("暂存标题");
  });

  it("filters the issue inbox down to blocking rows", async () => {
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState({
          postDraftReviews: [
            makePostDraftReview({
              role_results: [
                {
                  role: "claims_reviewer",
                  status: "blocked",
                  blocking_issues: ["权利要求1仍含内部评审说明"],
                  contamination_hits: [],
                  rewrite_suggestions: ["建议补充系统边界说明"],
                  official_safe_patches: ["official_safe_patches should stay hidden"],
                  attorney_memo: [],
                },
              ],
            }),
          ],
        })}
        exportReadiness={makeExportReadiness()}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "问题" }));
    expect(screen.getByText("阻断")).toBeInTheDocument();
    expect(screen.getByText("建议")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "只看阻断" }));

    expect(screen.queryByText("建议")).toBeNull();
  });

  it("shows the document version chain", async () => {
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState()}
        exportReadiness={makeExportReadiness()}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "版本" }));

    expect(screen.getByText("内部初稿")).toBeInTheDocument();
    expect(screen.getByText("正式稿")).toBeInTheDocument();
    expect(screen.getByText("成稿会审")).toBeInTheDocument();
    expect(screen.getAllByText(/当前有效|已失效|等待生成/).length).toBeGreaterThan(0);
  });

  it("does not show full hashes in the default version chain labels", async () => {
    const shortButFullHash = "abc";
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState({
          currentDraftHash: shortButFullHash,
          currentSourceDraftHash: shortButFullHash,
          officialCompileRuns: [
            makeOfficialCompileRun({
              source_draft_hash: shortButFullHash,
              official_package_hash: shortButFullHash,
              official_package: {
                ...makeOfficialCompileRun().official_package!,
                source_draft_hash: shortButFullHash,
                official_package_hash: shortButFullHash,
              },
            }),
          ],
          postDraftReviews: [
            makePostDraftReview({
              draft_package_hash: shortButFullHash,
              official_package_hash: shortButFullHash,
            }),
          ],
        })}
        exportReadiness={makeExportReadiness({
          current_source_draft_hash: shortButFullHash,
          official_package_hash: shortButFullHash,
        })}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "版本" }));

    const versionPanel = screen.getByRole("tabpanel");
    const shortLabels = Array.from(versionPanel.querySelectorAll(".document-short-hash")).map((node) => node.textContent ?? "");

    expect(shortLabels.length).toBeGreaterThan(0);
    expect(shortLabels.join(" ")).not.toContain(shortButFullHash);
    expect(screen.getAllByText("查看哈希详情").length).toBeGreaterThan(0);
  });

  it("shows an empty state when no repairable post-draft review exists", async () => {
    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState({
          postDraftReviews: [
            makePostDraftReview({
              export_allowed: true,
              blocking_issues: [],
              contamination_hits: [],
              role_results: [],
            }),
          ],
        })}
        exportReadiness={makeExportReadiness({
          export_allowed: true,
          post_draft_review_required: false,
          review_gate_status: "passed",
          review_blocking_issues: [],
        })}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "标注修复" }));

    expect(screen.getByText("暂无可修复会审")).toBeInTheDocument();
    expect(api.getPostDraftRepairSession).not.toHaveBeenCalled();
  });

  it("shows a loading state while the repair session is being fetched", async () => {
    let resolveSession!: (value: PostDraftRepairSession) => void;
    vi.mocked(api.getPostDraftRepairSession).mockReturnValueOnce(
      new Promise<PostDraftRepairSession>((resolve) => {
        resolveSession = resolve;
      }),
    );

    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState()}
        exportReadiness={makeExportReadiness()}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "标注修复" }));

    expect(screen.getByText("正在加载修复会话")).toBeInTheDocument();

    resolveSession(makeRepairSession());
    expect(await screen.findByText("问题队列")).toBeInTheDocument();
  });

  it("shows an error state and retry affordance when repair session loading fails", async () => {
    vi.mocked(api.getPostDraftRepairSession)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce(makeRepairSession());

    render(
      <DocumentRepairWorkspace
        projectState={makeProjectState()}
        exportReadiness={makeExportReadiness()}
        handlers={makeHandlers()}
        onNavigate={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "标注修复" }));

    expect(await screen.findByText("修复会话加载失败")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "重新加载" }));

    expect(await screen.findByText("问题队列")).toBeInTheDocument();
  });
});
