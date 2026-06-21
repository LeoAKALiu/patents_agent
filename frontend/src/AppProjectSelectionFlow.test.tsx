import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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
  await screen.findByRole("heading", { name: "开始撰写" });
  await screen.findByRole("option", { name: existingProject.name });
}

function getAriaLabelledContainer(label: string): HTMLElement {
  const element = document.querySelector(`[aria-label="${label}"]`);
  expect(element).not.toBeNull();
  return element as HTMLElement;
}

async function expectExternalDraftEntryBoundToSelectedProject() {
  await waitFor(() => {
    expect(screen.queryByRole("heading", { name: "开始撰写" })).not.toBeInTheDocument();
  });
  expect(screen.getByText(/当前进度：/)).toBeInTheDocument();

  const firstMileSummary = getAriaLabelledContainer("首 Mile 摘要");
  expect(within(firstMileSummary).getByText(existingProject.name)).toBeInTheDocument();
  expect(within(firstMileSummary).queryByText("未选择")).not.toBeInTheDocument();

  await userEvent.click(screen.getByRole("tab", { name: "导入外部初稿" }));
  await screen.findByRole("heading", { name: "保存外部初稿" });
  const externalDraftSummary = getAriaLabelledContainer("外部初稿导入摘要");
  expect(within(externalDraftSummary).getByText(existingProject.name)).toBeInTheDocument();
  expect(within(externalDraftSummary).queryByText("未选择")).not.toBeInTheDocument();
}

describe("App existing project selection flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockInitialApi();
  });

  afterEach(() => {
    cleanup();
  });

  it("opens the guided workbench with the selected existing project from the topbar selector", async () => {
    const user = userEvent.setup();
    await renderLoadedApp();

    await user.selectOptions(screen.getByLabelText("当前项目"), existingProject.id);

    await expectExternalDraftEntryBoundToSelectedProject();
    expect(apiMock.listProjectMaterials).toHaveBeenCalledWith(existingProject.id);
  });

  it("opens the guided workbench with the selected existing project from the project list", async () => {
    const user = userEvent.setup();
    await renderLoadedApp();

    await user.click(screen.getAllByRole("button", { name: "项目" })[0]);
    await screen.findByRole("heading", { name: "项目列表" });
    await user.click(screen.getByRole("button", { name: "选择" }));

    await expectExternalDraftEntryBoundToSelectedProject();
    expect(apiMock.listProjectMaterials).toHaveBeenCalledWith(existingProject.id);
  });
});
