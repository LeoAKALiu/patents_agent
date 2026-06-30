import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExportWorkspace } from "./ExportWorkspace";
import type { ExportWorkspaceProps } from "./ExportWorkspace";

const packageValue = {
  title: "一种输入数据处理方法",
  abstract: "摘要",
  claims: "1. 一种方法。",
  description: "说明书",
  drawing_description: "图1为流程图。",
  mermaid: "flowchart TD",
  image_prompt: "黑白线稿",
  review_findings: [],
  citations: [],
  generation_logs: [],
};

function makeProps(): ExportWorkspaceProps {
  return {
    postDraftState: {
      selectedProject: {
        id: "p-1",
        name: "输入数据处理",
        draft_text: "draft",
        patent_type: "invention",
        package: packageValue,
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
      },
      agentDoctor: null,
      visiblePatentPoints: [],
      projectMaterials: [],
      disclosureRuns: [],
      deliberationRuns: [],
      currentDisclosure: null,
      currentDeliberation: null,
      formulaRequirement: null,
      currentFormulaRun: null,
      currentPackage: packageValue,
      latestOfficialCompileRun: null,
      latestPostDraftReview: null,
      exportReadiness: {
        export_allowed: false,
        draft_required: false,
        quality_required: false,
        official_compile_required: true,
        post_draft_review_required: true,
        next_action: "run_official_compile",
        reason: "locked",
      },
      currentDraftHash: "draft-hash",
      currentSourceDraftHash: "source-hash",
      currentQualityChecked: false,
      selectedDeliberationProviders: [],
      lastExport: null,
      busy: "",
      desktopDialogsAvailable: false,
    },
    postDraftHandlers: {
      onCreatePatentPoint: vi.fn(),
      onSelectPatentPoint: vi.fn(),
      onDeletePatentPoint: vi.fn(),
      onEvaluatePatentPointMoat: vi.fn(),
      onUploadMaterial: vi.fn(),
      onStartDisclosure: vi.fn(),
      onRefreshDisclosures: vi.fn(),
      onCancelDisclosureRun: vi.fn(),
      onRetryDisclosureRun: vi.fn(),
      onStartDeliberation: vi.fn(),
      onToggleDeliberationProvider: vi.fn(),
      onRefreshDeliberations: vi.fn(),
      onCancelDeliberationRun: vi.fn(),
      onRetryDeliberationRun: vi.fn(),
      onGenerate: vi.fn(),
      onNativeExport: vi.fn(),
      onOpenExportFolder: vi.fn(),
    },
    onNavigateDocuments: vi.fn(),
  };
}

describe("ExportWorkspace", () => {
  it("renders overview cards and locked guidance without repair UI, then navigates to document tabs", async () => {
    const props = makeProps();

    render(<ExportWorkspace {...props} />);

    expect(screen.getAllByText("正式提交稿").length).toBeGreaterThan(0);
    expect(screen.getAllByText("内部复核材料").length).toBeGreaterThan(0);
    expect(screen.getAllByText("风险说明与追溯").length).toBeGreaterThan(0);
    expect(screen.getByText("请回到文稿与修复处理门禁或阻断问题；导出区只呈现文件与追溯信息，不承载正文修复面板。")).toBeInTheDocument();
    expect(screen.queryByText(/人工修正/)).toBeNull();
    expect(screen.queryByText(/一键AI修正/)).toBeNull();
    expect(screen.queryByText(/一键 AI 修正/)).toBeNull();
    expect(screen.queryByText(/标注修复面板/)).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "返回文稿与修复 / 总览" }));
    expect(props.onNavigateDocuments).toHaveBeenCalledWith("overview");

    await userEvent.click(screen.getByRole("button", { name: "查看文稿与修复 / 标注修复" }));
    expect(props.onNavigateDocuments).toHaveBeenCalledWith("annotated");
  });
});
