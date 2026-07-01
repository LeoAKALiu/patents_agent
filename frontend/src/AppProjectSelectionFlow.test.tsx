import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DisclosureRun, PatentPointCandidate, ProjectRecord } from "./api";
import App from "./App";

const apiMock = vi.hoisted(() => ({
  createProject: vi.fn(),
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
  startProjectDisclosure: vi.fn(),
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
  draft_text: "一种视觉检测闭环项目的授权稳健方案。",
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

const createdProject: ProjectRecord = {
  id: "proj-created-001",
  name: "浏览器创建项目",
  draft_text: "目标模式：授权稳健。\n一种低置信区域驱动的无人机补采方法。",
  patent_type: "invention",
  package: null,
  created_at: "2026-06-21T03:00:00Z",
  updated_at: "2026-06-21T03:00:00Z",
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

const disclosureCandidate: PatentPointCandidate = {
  id: "candidate-1",
  title: "低置信区域驱动的无人机补采任务生成",
  technical_problem: "无人机巡检中低置信区域需要重复确认。",
  innovation: "根据识别置信度生成补采任务。",
  technical_solution: "将低置信区域映射为补采航点并闭环更新识别结果。",
  beneficial_effects: ["提升缺陷识别可靠性。"],
  protection_focus: ["补采任务生成"],
  grantability_score: 0.76,
  rationale: "浏览器回归候选。",
  evidence_status: "feasible_unverified",
  source_type: "model",
  feasibility_basis: "",
  support_gaps: [],
  experiment_needed: [],
  moat_scores: {
    scope_width: 0.7,
    designaround_difficulty: 0.7,
    feasibility: 0.8,
    support_strength: 0.6,
    prior_art_distance: 0.6,
    strategic_value: 0.7,
  },
  claim_chart: [],
  selected: false,
};

const completedDisclosureRun: DisclosureRun = {
  id: "disclosure-run-1",
  project_id: existingProject.id,
  status: "completed",
  trace: false,
  max_prior_art_results: 8,
  run_dir: "",
  stage_results: [
    { phase: "patent_points", payload: { candidates: [disclosureCandidate] } },
  ],
  package: {
    title: "低置信区域补采交底书",
    summary: "交底摘要",
    materials_summary: "材料摘要",
    candidates: [disclosureCandidate],
    selected_candidate_id: null,
    prior_art_hits: [],
    prior_art_differences: "",
    body_markdown: "正文",
    mermaid: "",
    image_prompt: "",
    self_check_findings: [],
    generation_logs: [],
    export_warnings: [],
  },
  failures: [],
  events: [],
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((innerResolve, innerReject) => {
    resolve = innerResolve;
    reject = innerReject;
  });
  return { promise, resolve, reject };
}

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
  apiMock.startProjectDisclosure.mockResolvedValue(completedDisclosureRun);
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
    window.localStorage.clear();
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

  it("keeps a newly created guided project selected when an older refresh returns late", async () => {
    const user = userEvent.setup();
    const staleRefresh = deferred<ProjectRecord[]>();
    apiMock.createProject.mockResolvedValue(createdProject);
    apiMock.listProjects
      .mockReturnValueOnce(staleRefresh.promise)
      .mockResolvedValue([createdProject]);

    render(<App />);
    await screen.findByRole("heading", { level: 2, name: "工作台" });

    await user.click(screen.getByRole("button", { name: /从技术想法撰写发明专利/ }));
    await user.type(screen.getByLabelText("项目名称"), createdProject.name);
    await user.type(screen.getByLabelText("一句话想法"), "一种低置信区域驱动的无人机补采方法。");
    await user.click(screen.getByRole("button", { name: /创建并继续/ }));

    await waitFor(() => {
      expect(screen.getByLabelText("当前项目")).toHaveValue(createdProject.id);
    });

    staleRefresh.resolve([]);

    await waitFor(() => {
      expect(screen.getByLabelText("当前项目")).toHaveValue(createdProject.id);
    });
    expect(screen.queryByText("未选择项目")).not.toBeInTheDocument();
  });

  it("shows candidates from a disclosure run that completes before the list refresh catches up", async () => {
    const user = userEvent.setup();
    const createdDisclosureRun = { ...completedDisclosureRun, project_id: createdProject.id };
    apiMock.createProject.mockResolvedValue(createdProject);
    apiMock.listProjects.mockResolvedValue([createdProject]);
    apiMock.startProjectDisclosure.mockResolvedValue(createdDisclosureRun);

    render(<App />);
    await screen.findByRole("heading", { level: 2, name: "工作台" });

    await user.click(screen.getByRole("button", { name: /从技术想法撰写发明专利/ }));
    await user.type(screen.getByLabelText("项目名称"), createdProject.name);
    await user.type(screen.getByLabelText("一句话想法"), "一种低置信区域驱动的无人机补采方法。");
    await user.click(screen.getByRole("button", { name: /创建并继续/ }));
    await waitFor(() => {
      expect(screen.getByLabelText("当前项目")).toHaveValue(createdProject.id);
    });
    const disclosureButtons = await screen.findAllByRole("button", { name: /^提炼发明点$/ });
    await user.click(disclosureButtons[disclosureButtons.length - 1]);

    await waitFor(() => {
      expect(apiMock.startProjectDisclosure).toHaveBeenCalledWith(createdProject.id, false, "standard");
    });
    await screen.findByText(disclosureCandidate.title);
    expect(screen.getByRole("button", { name: "选为主线并保存后备路线" })).toBeEnabled();
  });
});
