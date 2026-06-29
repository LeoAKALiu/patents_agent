import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ProjectWorkspaceHandlers } from "@/features/projects/ProjectWorkspace";

import { WorkbenchWorkspace } from "./WorkbenchWorkspace";
import type { WorkbenchState } from "./selectors";

function makeState(overrides: Partial<WorkbenchState> = {}): WorkbenchState {
  return {
    hasProject: true,
    projectName: "城市体检智能体",
    currentStepId: "postReview",
    stepGroups: [
      {
        label: "构思输入",
        steps: [
          { id: "idea", label: "想法与材料", description: "输入材料", status: "done" },
          { id: "invention", label: "发明点", description: "确认发明点", status: "done" },
        ],
      },
      {
        label: "生成成稿",
        steps: [
          { id: "deliberation", label: "多智能体会审", description: "会审", status: "done" },
          { id: "formula", label: "核心公式", description: "公式", status: "done" },
          { id: "draft", label: "生成初稿", description: "初稿", status: "done" },
          { id: "quality", label: "质量检查", description: "质量检查", status: "done" },
        ],
      },
      {
        label: "提交放行",
        steps: [
          { id: "officialCompile", label: "正式稿编译", description: "编译", status: "done" },
          { id: "postReview", label: "成稿会审", description: "会审", status: "current" },
          { id: "export", label: "导出", description: "导出", status: "locked" },
        ],
      },
    ],
    nextAction: {
      label: "处理成稿会审阻断项",
      description: "进入文稿与修复处理阻断项。",
    },
    primaryTarget: "documents",
    primaryActionBlockReason: "",
    riskSummary: {
      blockingCount: 2,
      issueCount: 3,
      exportLocked: true,
      exportReady: false,
    },
    runSummary: {
      label: "空闲",
      busy: false,
    },
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

describe("WorkbenchWorkspace", () => {
  it("renders the workbench sections, primary action, and no raw internals", () => {
    render(<WorkbenchWorkspace state={makeState()} handlers={makeHandlers()} onNavigate={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "工作台" })).toBeInTheDocument();
    expect(screen.getByText("当前项目")).toBeInTheDocument();
    expect(screen.getByText("下一步")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "流程进度" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "风险与运行" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /进入文稿与修复|创建项目|导出正式稿/ })).toBeInTheDocument();
    expect(screen.queryByText(/generation_logs|official_safe_patches/)).toBeNull();
  });

  it("navigates blocked review work to documents", async () => {
    const navigate = vi.fn();
    render(<WorkbenchWorkspace state={makeState()} handlers={makeHandlers()} onNavigate={navigate} />);

    await userEvent.click(screen.getByRole("button", { name: "进入文稿与修复" }));

    expect(navigate).toHaveBeenCalledWith("documents");
  });

  it("disables the guided primary action and does not start post-draft review when provider count is blocked", async () => {
    const handlers = makeHandlers();
    render(
      <WorkbenchWorkspace
        state={makeState({
          currentStepId: "postReview",
          nextAction: {
            label: "启动成稿会审",
            description: "正式提交前复核当前版本、权利要求质量并清理内部痕迹。",
          },
          primaryTarget: "workbench-start",
          primaryActionBlockReason: "至少需要 Codex 主席 + 2 个可用专家才能启动成稿会审。",
          riskSummary: {
            blockingCount: 0,
            issueCount: 0,
            exportLocked: false,
            exportReady: false,
          },
        })}
        handlers={handlers}
        onNavigate={vi.fn()}
      />,
    );

    const button = screen.getByRole("button", { name: "启动成稿会审" });

    expect(button).toBeDisabled();
    expect(screen.getByText("至少需要 Codex 主席 + 2 个可用专家才能启动成稿会审。")).toBeInTheDocument();

    await userEvent.click(button);

    expect(handlers.onStartPostDraftReview).not.toHaveBeenCalled();
  });

  it("shows compact start paths when no project is selected", async () => {
    const handlers = makeHandlers();
    render(
      <WorkbenchWorkspace
        state={makeState({
          hasProject: false,
          projectName: "未选择项目",
          currentStepId: "idea",
          nextAction: { label: "创建项目", description: "选择起步路径。" },
          primaryTarget: "workbench-start",
          riskSummary: {
            blockingCount: 0,
            issueCount: 0,
            exportLocked: false,
            exportReady: false,
          },
        })}
        handlers={handlers}
        onNavigate={vi.fn()}
      />,
    );

    expect(screen.getByText("从技术想法撰写发明专利")).toBeInTheDocument();
    expect(screen.getByText("从结构方案撰写实用新型")).toBeInTheDocument();
    expect(screen.getByText("导入已有稿件进行润色提升")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "创建项目" }));

    expect(handlers.onStartChoice).toHaveBeenCalledWith("invention");
  });
});
