import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import appSource from "@/App.tsx?raw";
import { AppRoot, type AppRootProps } from "./AppRoot";

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
    onOpenExpertTool: noop,
  } as AppRootProps["projectHandlers"];

  return {
    activeSection: "generate",
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
      currentDraftHash: "",
      currentSourceDraftHash: "",
      selectedDeliberationProviders: [],
      lastExport: null,
      busy: "",
      desktopDialogsAvailable: false,
    },
    postDraftHandlers: {} as AppRootProps["postDraftHandlers"],
  };
}

describe("AppRoot routes", () => {
  it("renders the production shell navigation", () => {
    render(<AppRoot {...makeRootProps()} />);

    expect(screen.getAllByText("开始").length).toBeGreaterThan(0);
    expect(screen.getAllByText("项目").length).toBeGreaterThan(0);
    expect(screen.getAllByText("设置").length).toBeGreaterThan(0);
  });

  it("is wired from App.tsx instead of the legacy inline shell renderer", () => {
    expect(appSource).toContain("from \"@/app/AppRoot\"");
    expect(appSource).toContain("<AppRoot");
    expect(appSource).not.toContain("function renderExpertTool");
  });
});
