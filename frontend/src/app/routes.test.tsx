import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import appSource from "@/App.tsx?raw";
import { AppRoot, type AppRootProps } from "./AppRoot";
import { resolveRoute } from "./routes";
import { SystemStatusPanel } from "@/ui/SystemStatusPanel";
import type { AgentDoctorReport, Health, ProjectRecord } from "@/api";

vi.mock("@/features/corpus/CorpusWorkspace", () => ({
  CorpusWorkspace: ({ tool }: { tool: string }) => <div data-testid="corpus-workspace">{tool}</div>,
}));

vi.mock("@/features/postDraft/PostDraftWorkspace", () => ({
  PostDraftWorkspace: ({ tool }: { tool: string }) => <div data-testid="postdraft-workspace">{tool}</div>,
}));

function noop() {}

function asyncNoop() {
  return Promise.resolve();
}

function makeProject(): ProjectRecord {
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
  };
}

function makeRootProps(): AppRootProps {
  const projectHandlers = {
    onStartChoice: noop,
    onSelectProjectId: noop,
    onDeleteProject: noop,
    onCreateIdeaProject: asyncNoop,
    onCreateExternalDraft: asyncNoop,
    onUploadExternalDraft: asyncNoop,
    onStartExternalDraftIntake: asyncNoop,
    onConfirmExternalDraftIntake: asyncNoop,
    onUploadMaterial: asyncNoop,
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
  } as AppRootProps["projectHandlers"];

  return {
    activeSection: "workbench",
    activeExpertTool: "build",
    startChoice: null,
    selectedProject: null,
    projects: [],
    busy: "",
    busyElapsedSeconds: 0,
    message: "",
    error: "",
    health: null,
    agentDoctor: null,
    backendStatus: "unknown",
    projectListStatus: "idle",
    theme: "light",
    onSelectSection: vi.fn(),
    onSelectExpertTool: vi.fn(),
    onSelectProjectId: vi.fn(),
    onReturnToStartChoices: vi.fn(),
    onChangeTheme: vi.fn(),
    onRefresh: vi.fn(),
    projectState: {
      startChoice: null,
      selectedProject: null,
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
    },
    projectHandlers,
    corpusState: {
      corpusJobForm: {
        source_type: "cnipa_export",
        source_name: "CNIPA",
        query: "",
        domain: "",
        version_name: "",
      },
      corpusJob: null,
      corpusVersions: [],
      corpusStats: null,
      documents: [],
      searchText: "",
      searchSection: "",
      searchResults: [],
      busy: "",
    },
    corpusHandlers: {} as AppRootProps["corpusHandlers"],
    qualityState: {
      selectedProject: null,
      filingReports: [],
      latestFilingReport: null,
      grantabilityReports: [],
      latestGrantabilityReport: null,
      worksheets: [],
      latestWorksheet: null,
      completionRuns: [],
      latestCompletionRun: null,
      latestOfficialCompileRun: null,
      latestPostDraftReview: null,
      currentDraftHash: "",
      currentSourceDraftHash: "",
      busy: "",
    },
    qualityHandlers: {} as AppRootProps["qualityHandlers"],
    postDraftState: {
      selectedProject: null,
      agentDoctor: null,
      visiblePatentPoints: [],
      projectMaterials: [],
      disclosureRuns: [],
      deliberationRuns: [],
      currentDisclosure: null,
      currentDeliberation: null,
      formulaRequirement: null,
      currentFormulaRun: null,
      currentPackage: null,
      latestOfficialCompileRun: null,
      latestPostDraftReview: null,
      exportReadiness: null,
      currentDraftHash: "",
      currentSourceDraftHash: "",
      currentQualityChecked: false,
      selectedDeliberationProviders: [],
      lastExport: null,
      busy: "",
      desktopDialogsAvailable: false,
    },
    postDraftHandlers: {} as AppRootProps["postDraftHandlers"],
  };
}

describe("AppRoot routes", () => {
  it("resolves the seven public route kinds from top-level destinations", () => {
    expect(resolveRoute("workbench", "build", false, false)).toBe("workbench");
    expect(resolveRoute("projects", "build", false, false)).toBe("projects-overview");
    expect(resolveRoute("documents", "review", true, false)).toBe("documents");
    expect(resolveRoute("knowledge", "corpus", true, false)).toBe("knowledge");
    expect(resolveRoute("export", "export", true, false)).toBe("export");
    expect(resolveRoute("expert", "moat", true, false)).toBe("expert");
    expect(resolveRoute("settings", "build", false, false)).toBe("settings");
  });

  it("renders destination-only shell navigation", () => {
    render(<AppRoot {...makeRootProps()} />);

    for (const label of ["工作台", "项目", "文稿与修复", "知识库", "专家工具", "导出", "设置"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it("does not render the old project key-node group in shell chrome", () => {
    const selectedProject = makeProject();

    render(
      <AppRoot
        {...makeRootProps()}
        selectedProject={selectedProject}
        projects={[selectedProject]}
        projectState={{
          ...makeRootProps().projectState,
          selectedProject,
          projects: [selectedProject],
        }}
      />,
    );

    expect(screen.queryByText("关键节点")).not.toBeInTheDocument();
    expect(screen.queryByText("01 想法与材料")).not.toBeInTheDocument();
    expect(screen.queryByText("02 发明点确认")).not.toBeInTheDocument();
  });

  it("renders the corpus workspace for the knowledge section", () => {
    render(<AppRoot {...makeRootProps()} activeSection="knowledge" activeExpertTool="corpus" />);

    expect(screen.getByTestId("corpus-workspace")).toHaveTextContent("corpus");
  });

  it("defaults knowledge to the build tool when the active expert tool is outside corpus", () => {
    render(<AppRoot {...makeRootProps()} activeSection="knowledge" activeExpertTool="materials" />);

    expect(screen.getByTestId("corpus-workspace")).toHaveTextContent("build");
  });

  it("renders the documents title while reusing the current project workspace surface", () => {
    render(<AppRoot {...makeRootProps()} activeSection="documents" activeExpertTool="materials" />);

    expect(screen.getByRole("heading", { level: 1, name: "文稿与修复" })).toBeInTheDocument();
    expect(screen.getByText("处理当前项目的正文、问题和版本链路")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "开始撰写" })).toBeInTheDocument();
  });

  it("renders the export workspace for the export section", () => {
    render(<AppRoot {...makeRootProps()} activeSection="export" activeExpertTool="materials" />);

    expect(screen.getByTestId("postdraft-workspace")).toHaveTextContent("export");
  });

  it("renders status-only topbar chrome without global nav buttons", () => {
    const selectedProject = makeProject();

    render(
      <AppRoot
        {...makeRootProps()}
        selectedProject={selectedProject}
        projects={[selectedProject]}
        activeSection="workbench"
        backendStatus="online"
        busy="postDraftReview"
        projectState={{
          ...makeRootProps().projectState,
          selectedProject,
          projects: [selectedProject],
        }}
        postDraftState={{
          ...makeRootProps().postDraftState,
          selectedProject,
          exportReadiness: {
            export_allowed: false,
            draft_required: false,
            quality_required: false,
            official_compile_required: false,
            post_draft_review_required: true,
            next_action: "run_post_draft_review",
            reason: "成稿会审未通过",
          },
        }}
      />,
    );

    expect(screen.getByLabelText("当前项目")).toBeInTheDocument();
    expect(screen.getByText("导出锁定")).toBeInTheDocument();
    expect(screen.getByText("处理中")).toBeInTheDocument();
    expect(screen.getByText("后端在线")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "刷新运行状态" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "专家工具" })).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "返回向导" })).not.toBeInTheDocument();
  });

  it("keeps return-to-start-choice recovery only when the workbench start path is active", () => {
    render(<AppRoot {...makeRootProps()} activeSection="workbench" startChoice="invention" />);

    expect(screen.getByRole("button", { name: "返回三选一" })).toBeInTheDocument();
  });

  it("renders compact system health by default", () => {
    const health: Health = {
      ok: true,
      llm_configured: true,
      data_dir: "/tmp/patent-agent",
      model: "qwen",
      embedding_model: "bge",
    };
    const agentDoctor: AgentDoctorReport = {
      status: "degraded",
      run_mode: "partial",
      commands: {},
      active_provider_ids: [],
      missing_required: [],
      missing_optional: ["codex"],
      unknown_required: [],
    };

    render(
      <SystemStatusPanel
        health={health}
        agentDoctor={agentDoctor}
        backendStatus="online"
        agentRunModeLabel={(mode) => (mode === "partial" ? "部分可用" : mode)}
      />,
    );

    expect(screen.getByText("模型")).toBeInTheDocument();
    expect(screen.getByText("智能体")).toBeInTheDocument();
    expect(screen.getByText("后端")).toBeInTheDocument();
    expect(screen.getByText("在线")).toBeInTheDocument();
    expect(screen.queryByText("当前项目")).not.toBeInTheDocument();
    expect(screen.queryByText("内部痕迹检查")).not.toBeInTheDocument();
    expect(screen.queryByText("模型名称")).not.toBeInTheDocument();
    expect(screen.queryByText("向量模型")).not.toBeInTheDocument();
    expect(screen.queryByText("数据目录")).not.toBeInTheDocument();
    expect(screen.queryByText("/tmp/patent-agent")).not.toBeInTheDocument();
    expect(screen.queryByText("qwen")).not.toBeInTheDocument();
    expect(screen.queryByText("bge")).not.toBeInTheDocument();
  });

  it("opens backend diagnostics from the topbar backend chip", async () => {
    const selectedProject = makeProject();
    const health: Health = {
      ok: true,
      llm_configured: true,
      data_dir: "/tmp/patent-agent",
      model: "qwen-plus",
      embedding_model: "bge-m3",
    };
    const agentDoctor: AgentDoctorReport = {
      status: "degraded",
      run_mode: "partial",
      commands: {},
      active_provider_ids: [],
      missing_required: [],
      missing_optional: ["codex"],
      unknown_required: [],
    };

    render(
      <AppRoot
        {...makeRootProps()}
        selectedProject={selectedProject}
        projects={[selectedProject]}
        health={health}
        agentDoctor={agentDoctor}
        backendStatus="online"
        projectListStatus="ready"
        projectState={{
          ...makeRootProps().projectState,
          selectedProject,
          projects: [selectedProject],
        }}
      />,
    );

    expect(screen.queryByText("模型名称")).not.toBeInTheDocument();
    expect(screen.queryByText("/tmp/patent-agent")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "后端在线" }));

    const dialog = screen.getByRole("dialog", { name: "后端诊断" });
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText("后端状态")).toBeInTheDocument();
    expect(within(dialog).getByText("在线")).toBeInTheDocument();
    expect(within(dialog).getByText("项目列表")).toBeInTheDocument();
    expect(within(dialog).getByText("正常")).toBeInTheDocument();
    expect(within(dialog).getByText("模型名称")).toBeInTheDocument();
    expect(within(dialog).getByText("qwen-plus")).toBeInTheDocument();
    expect(within(dialog).getByText("向量模型")).toBeInTheDocument();
    expect(within(dialog).getByText("bge-m3")).toBeInTheDocument();
    expect(within(dialog).getByText("数据目录")).toBeInTheDocument();
    expect(within(dialog).getByText("/tmp/patent-agent")).toBeInTheDocument();
    expect(within(dialog).getByText("智能体状态")).toBeInTheDocument();
    expect(within(dialog).getByText("部分可用")).toBeInTheDocument();
  });

  it("is wired from App.tsx instead of the legacy inline shell renderer", () => {
    expect(appSource).toContain("from \"@/app/AppRoot\"");
    expect(appSource).toContain("<AppRoot");
    expect(appSource).not.toContain("function renderExpertTool");
  });
});
