import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import appSource from "@/App.tsx?raw";
import { AppRoot, type AppRootProps } from "./AppRoot";
import { resolveRoute } from "./routes";

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
  it("resolves documents, knowledge, and export as dedicated route kinds", () => {
    expect(resolveRoute("documents", "materials", false, false)).toBe("documents");
    expect(resolveRoute("knowledge", "build", false, false)).toBe("knowledge");
    expect(resolveRoute("export", "materials", true, true)).toBe("export");
  });

  it("renders the production shell navigation", () => {
    render(<AppRoot {...makeRootProps()} />);

    expect(screen.getAllByText("工作台").length).toBeGreaterThan(0);
    expect(screen.getAllByText("项目").length).toBeGreaterThan(0);
    expect(screen.getAllByText("设置").length).toBeGreaterThan(0);
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

  it("is wired from App.tsx instead of the legacy inline shell renderer", () => {
    expect(appSource).toContain("from \"@/app/AppRoot\"");
    expect(appSource).toContain("<AppRoot");
    expect(appSource).not.toContain("function renderExpertTool");
  });
});
