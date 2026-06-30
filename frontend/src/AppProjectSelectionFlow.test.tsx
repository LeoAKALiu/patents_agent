import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectRecord } from "./api";
import App from "./App";

const apiMock = vi.hoisted(() => ({
  getHealth: vi.fn(),
  getAgentDoctor: vi.fn(),
  getCorpusStats: vi.fn(),
  getFormulaRequirement: vi.fn(),
  listClaimDefenseWorksheets: vi.fn(),
  listCorpus: vi.fn(),
  listCorpusVersions: vi.fn(),
  listDraftCompletionRuns: vi.fn(),
  listExternalDraftIntakeRuns: vi.fn(),
  listExternalDraftSources: vi.fn(),
  listFilingReadinessReports: vi.fn(),
  listFormulaRuns: vi.fn(),
  listGrantabilityReports: vi.fn(),
  listOfficialCompileRuns: vi.fn(),
  listPostDraftReviews: vi.fn(),
  listProjectDeliberations: vi.fn(),
  listProjectDisclosures: vi.fn(),
  listProjectMaterials: vi.fn(),
  listProjectPatentPoints: vi.fn(),
  listProjects: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    ...apiMock,
  };
});

const existingProject: ProjectRecord = {
  id: "proj-existing-001",
  name: "视觉检测闭环项目",
  draft_text: "",
  patent_type: "invention",
  package: null,
  created_at: "2026-06-21T01:00:00Z",
  updated_at: "2026-06-21T02:00:00Z",
  applicant: "",
  inventors: "",
  technical_field: "计算机视觉",
  background: "",
  pain_point: "",
  technical_solution: "",
  innovation: "",
  embodiments: "",
  beneficial_effects: "",
};

function mockInitialApi() {
  apiMock.getHealth.mockResolvedValue({
    ok: true,
    llm_configured: true,
    data_dir: "/tmp/patentagent-test",
    model: "test-model",
    embedding_model: "test-embedding",
  });
  apiMock.getAgentDoctor.mockResolvedValue({
    status: "ready",
    run_mode: "full",
    commands: {},
    active_provider_ids: [],
    missing_required: [],
    missing_optional: [],
    unknown_required: [],
  });
  apiMock.listCorpus.mockResolvedValue([]);
  apiMock.listProjects.mockResolvedValue([existingProject]);
  apiMock.listCorpusVersions.mockResolvedValue([]);
  apiMock.getCorpusStats.mockResolvedValue(null);

  apiMock.listProjectDeliberations.mockResolvedValue([]);
  apiMock.listProjectMaterials.mockResolvedValue([]);
  apiMock.listProjectDisclosures.mockResolvedValue([]);
  apiMock.getFormulaRequirement.mockResolvedValue({ required: false, signals: [], reasons: [] });
  apiMock.listFormulaRuns.mockResolvedValue([]);
  apiMock.listOfficialCompileRuns.mockResolvedValue({ runs: [], current_source_draft_hash: "" });
  apiMock.listPostDraftReviews.mockResolvedValue({ runs: [], current_draft_hash: "" });
  apiMock.listExternalDraftSources.mockResolvedValue([]);
  apiMock.listExternalDraftIntakeRuns.mockResolvedValue([]);
  apiMock.listProjectPatentPoints.mockResolvedValue([]);
  apiMock.listFilingReadinessReports.mockResolvedValue({ reports: [], current_source_draft_hash: "" });
  apiMock.listGrantabilityReports.mockResolvedValue({ reports: [], current_source_draft_hash: "" });
  apiMock.listClaimDefenseWorksheets.mockResolvedValue({ worksheets: [], current_source_draft_hash: "" });
  apiMock.listDraftCompletionRuns.mockResolvedValue({ runs: [], current_source_draft_hash: "" });
}

async function renderLoadedApp() {
  render(<App />);
  await screen.findByRole("heading", { level: 2, name: "工作台" });
  await screen.findByRole("option", { name: existingProject.name });
}

async function expectWorkbenchBoundToSelectedProject() {
  await screen.findByRole("heading", { level: 2, name: "工作台" });
  await waitFor(() => {
    expect(screen.getByLabelText("当前项目")).toHaveValue(existingProject.id);
  });
  expect(screen.getAllByText(existingProject.name).length).toBeGreaterThan(0);
}

describe("App existing project selection flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockInitialApi();
  });

  afterEach(() => {
    cleanup();
  });

  it("binds the selected existing project from the topbar selector to the workbench", async () => {
    const user = userEvent.setup();
    await renderLoadedApp();

    await user.selectOptions(screen.getByLabelText("当前项目"), existingProject.id);

    await expectWorkbenchBoundToSelectedProject();
    expect(apiMock.listProjectMaterials).toHaveBeenCalledWith(existingProject.id);
  });

  it("binds the selected existing project from the project list to the workbench", async () => {
    const user = userEvent.setup();
    await renderLoadedApp();

    await user.click(screen.getAllByRole("button", { name: "项目" })[0]);
    await screen.findByRole("heading", { name: "项目列表" });
    const selectButton = screen.queryByRole("button", { name: "选择" });
    if (selectButton) {
      await user.click(selectButton);
    } else {
      expect(screen.getAllByRole("button", { name: "当前项目" }).length).toBeGreaterThan(0);
    }
    await user.click(screen.getAllByRole("button", { name: "工作台" })[0]);

    await expectWorkbenchBoundToSelectedProject();
    expect(apiMock.listProjectMaterials).toHaveBeenCalledWith(existingProject.id);
  });
});
