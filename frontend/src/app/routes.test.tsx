import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
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

vi.mock("@/features/knowledge/KnowledgeWorkspace", () => ({
  KnowledgeWorkspace: () => <div data-testid="knowledge-workspace">knowledge-wrapper</div>,
}));

vi.mock("@/features/export/ExportWorkspace", () => ({
  ExportWorkspace: ({
    onNavigateDocuments,
  }: {
    onNavigateDocuments: (target: "overview" | "annotated") => void;
  }) => (
    <div data-testid="export-workspace">
      <button onClick={() => onNavigateDocuments("overview")} type="button">
        去总览
      </button>
      <button onClick={() => onNavigateDocuments("annotated")} type="button">
        去标注修复
      </button>
      <span>export-wrapper</span>
    </div>
  ),
}));

vi.mock("@/features/expert/ExpertToolsWorkspace", () => ({
  ExpertToolsWorkspace: () => <div data-testid="expert-tools-workspace">expert-wrapper</div>,
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
      projectKnowledge: null,
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

function AppRootHarness({
  initialSection = "export",
}: {
  initialSection?: AppRootProps["activeSection"];
}) {
  const baseProps = makeRootProps();
  const selectedProject = makeProject();
  const [activeSection, setActiveSection] = useState<AppRootProps["activeSection"]>(initialSection);

  return (
    <AppRoot
      {...baseProps}
      activeSection={activeSection}
      selectedProject={selectedProject}
      projects={[selectedProject]}
      onSelectSection={setActiveSection}
      projectState={{
        ...baseProps.projectState,
        selectedProject,
        projects: [selectedProject],
      }}
      postDraftState={{
        ...baseProps.postDraftState,
        selectedProject,
      }}
    />
  );
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
    const sidebar = document.querySelector(".sidebar") as HTMLElement;
    expect(within(sidebar).queryByText("Main")).not.toBeInTheDocument();
  });

  it.each([
    {
      section: "workbench",
      testId: "primary-surface-workbench",
      copy: "从起步入口推进到生成、复核、修复和导出，把当前项目状态放在同一处判断。",
      routeText: "工作台",
    },
    {
      section: "projects",
      testId: "primary-surface-projects",
      copy: "集中查看项目、起草阶段、风险状态和导出准备度，避免在列表里迷路。",
      routeText: "项目列表",
    },
    {
      section: "documents",
      testId: "primary-surface-documents",
      copy: "管理内部初稿、正式稿、问题修复和版本链路，把导出前阻断留在同一处处理。",
      routeText: "当前项目尚未生成内部初稿。",
    },
    {
      section: "knowledge",
      testId: "primary-surface-knowledge",
      copy: "沉淀参考材料、语料版本和检索片段，为发明点确认与正文补强提供证据来源。",
      routeText: "knowledge-wrapper",
    },
    {
      section: "expert",
      testId: "primary-surface-expert",
      copy: "集中处理语料建设、质量检查、授权评估和成稿会审等专业工具。",
      routeText: "expert-wrapper",
    },
    {
      section: "export",
      testId: "primary-surface-export",
      copy: "分离正式提交稿、内部复核材料和风险追溯，只在门禁满足后开放提交文件。",
      routeText: "export-wrapper",
    },
    {
      section: "settings",
      testId: "primary-surface-settings",
      copy: "配置主题、模型接入和智能体运行环境，让系统状态与工作流门禁保持一致。",
      routeText: "设置",
    },
  ] as const)("renders shared primary surface chrome for $section", ({ section, testId, copy, routeText }) => {
    render(<AppRoot {...makeRootProps()} activeSection={section} />);

    const surface = screen.getByTestId(testId);
    expect(surface).toBeInTheDocument();
    expect(within(surface).getByText(copy)).toBeInTheDocument();
    expect(within(surface).getAllByText(routeText).length).toBeGreaterThan(0);
    expect(within(surface).getByLabelText("状态指标")).toBeInTheDocument();
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

    expect(screen.getByTestId("knowledge-workspace")).toHaveTextContent("knowledge-wrapper");
  });

  it("defaults knowledge to the build tool when the active expert tool is outside corpus", () => {
    render(<AppRoot {...makeRootProps()} activeSection="knowledge" activeExpertTool="materials" />);

    expect(screen.getByTestId("knowledge-workspace")).toHaveTextContent("knowledge-wrapper");
  });

  it("renders the document repair workspace for the documents section", () => {
    render(<AppRoot {...makeRootProps()} activeSection="documents" activeExpertTool="materials" />);

    expect(screen.getByRole("heading", { level: 1, name: "文稿与修复" })).toBeInTheDocument();
    const topbar = document.querySelector(".topbar") as HTMLElement;
    expect(within(topbar).queryByText("处理当前项目的正文、问题和版本链路")).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "总览" })).toBeInTheDocument();
    expect(screen.getByText("当前项目尚未生成内部初稿。")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "开始撰写" })).not.toBeInTheDocument();
  });

  it("renders the export workspace for the export section", () => {
    render(<AppRoot {...makeRootProps()} activeSection="export" activeExpertTool="materials" />);

    expect(screen.getByTestId("export-workspace")).toHaveTextContent("export-wrapper");
  });

  it("renders the expert tools workspace for the expert section", () => {
    render(<AppRoot {...makeRootProps()} activeSection="expert" activeExpertTool="materials" />);

    expect(screen.getByTestId("expert-tools-workspace")).toHaveTextContent("expert-wrapper");
  });

  it("routes export guidance into the requested document-repair tab", async () => {
    render(<AppRootHarness />);

    await userEvent.click(screen.getByRole("button", { name: "去标注修复" }));
    expect(await screen.findByRole("tab", { name: "标注修复", selected: true })).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("button", { name: "工作台" })[0]);
    await userEvent.click(screen.getAllByRole("button", { name: "文稿与修复" })[0]);
    expect(await screen.findByRole("tab", { name: "总览", selected: true })).toBeInTheDocument();
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
    const topbar = document.querySelector(".topbar") as HTMLElement;
    expect(within(topbar).queryByText("当前项目、下一步和导出风险概览")).not.toBeInTheDocument();
    expect(within(topbar).queryByRole("button", { name: "专家工具" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "返回向导" })).not.toBeInTheDocument();
  });

  it("demotes workbench health-check failures into state coverage without showing raw diagnostics", () => {
    render(
      <AppRoot
        {...makeRootProps()}
        activeSection="workbench"
        backendStatus="offline"
        error="服务器操作失败:GET /api/health 返回 500:"
      />,
    );

    expect(screen.queryByText(/GET \/api\/health/)).not.toBeInTheDocument();
    expect(screen.getByText("错误降级")).toBeInTheDocument();
    expect(screen.queryByText("后端诊断")).not.toBeInTheDocument();
    expect(screen.getByText("后端离线")).toBeInTheDocument();
  });

  it("demotes health-check failures on every primary surface without showing raw API paths", () => {
    render(
      <AppRoot
        {...makeRootProps()}
        activeSection="expert"
        backendStatus="offline"
        error="服务器操作失败:GET /api/health 返回 500:"
      />,
    );

    expect(screen.queryByText(/GET \/api\/health/)).not.toBeInTheDocument();
    expect(screen.getByTestId("primary-surface-expert")).toBeInTheDocument();
    expect(screen.getByText("后端离线")).toBeInTheDocument();
  });

  it("keeps return-to-start-choice recovery only when the workbench start path is active", () => {
    render(<AppRoot {...makeRootProps()} activeSection="workbench" startChoice="invention" />);

    expect(screen.getByRole("button", { name: "返回三选一" })).toBeInTheDocument();
  });

  it("does not show start-choice recovery when a selected project is already on the OD workbench", () => {
    const selectedProject = makeProject();

    render(
      <AppRoot
        {...makeRootProps()}
        activeSection="workbench"
        startChoice="invention"
        selectedProject={selectedProject}
        projects={[selectedProject]}
        projectState={{
          ...makeRootProps().projectState,
          startChoice: "invention",
          selectedProject,
          projects: [selectedProject],
        }}
      />,
    );

    expect(screen.queryByRole("button", { name: "返回工作台总览" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "返回三选一" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "项目与工作队列" })).toBeInTheDocument();
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
