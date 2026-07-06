import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DraftCompletionRun } from "@/api";
import type { GuidedActionGate } from "@/guidedFlow";
import { QualityPanel } from "./QualityPanel";

const allowedGate: GuidedActionGate = { allowed: true, reason: "" };

function makeCompletionRun(): DraftCompletionRun {
  return {
    id: "run-1",
    project_id: "project-1",
    snapshot_hash: "snapshot",
    draft_package_hash: "draft",
    status: "completed",
    issues: [],
    tasks: [
      {
        id: "task-1",
        issue_id: "issue-1",
        task_type: "revise_draft_support",
        priority: 100,
        input_refs: [],
        expected_output: "补充实施例。",
        draft_section_target: "description",
        status: "proposed",
      },
      {
        id: "task-2",
        issue_id: "issue-2",
        task_type: "clean_export_trace",
        priority: 90,
        input_refs: [],
        expected_output: "清除内部痕迹。",
        draft_section_target: "export",
        status: "proposed",
      },
    ],
    patches: [
      {
        id: "patch-1",
        task_id: "task-1",
        target_section: "description",
        patch_kind: "insert",
        before_text: "",
        after_text: "在一个实施例中，系统形成结构化记录。",
        rationale: "补充实施例支撑。",
        risk_delta: "降低提交成熟度风险。",
        evidence_refs: ["task:1"],
        can_enter_official_draft: false,
        status: "proposed",
      },
      {
        id: "patch-2",
        task_id: "task-2",
        target_section: "export",
        patch_kind: "sidecar_only",
        before_text: "",
        after_text: "删除制图提示词。",
        rationale: "清除内部痕迹。",
        risk_delta: "降低格式污染风险。",
        evidence_refs: ["task:2"],
        can_enter_official_draft: false,
        status: "proposed",
      },
    ],
    support_matrix: [],
    scorecard: {
      authorization_stability: 20,
      protection_scope: 30,
      support_strength: 25,
      prior_art_distinction: 40,
      filing_maturity: 35,
      official_hygiene: 45,
      overall: 33,
    },
    notes: [],
    created_at: "2026-06-25T00:00:00Z",
  };
}

describe("QualityPanel", () => {
  it("offers one-click acceptance for all proposed completion patches", async () => {
    const onAcceptAllPatches = vi.fn();
    render(
      <QualityPanel
        actionGate={allowedGate}
        filingReport={null}
        worksheet={null}
        completionRun={makeCompletionRun()}
        busy=""
        busyElapsedSeconds={0}
        onRunQualityChecks={vi.fn()}
        onImproveScore={vi.fn()}
        onAcceptPatch={vi.fn()}
        onAcceptAllPatches={onAcceptAllPatches}
        onOpenExpertTool={vi.fn()}
      />,
    );

    expect(screen.getByText("初稿完善").closest(".info-card")).toHaveTextContent("2 个任务，2 个候选补丁");

    await userEvent.click(screen.getByRole("button", { name: /一键接受补强/ }));

    expect(onAcceptAllPatches).toHaveBeenCalledWith("run-1");
  });

  it("disables one-click acceptance button if no proposed patches exist", () => {
    const onAcceptAllPatches = vi.fn();
    const run = makeCompletionRun();
    run.patches = []; // empty proposed patches
    render(
      <QualityPanel
        actionGate={allowedGate}
        filingReport={null}
        worksheet={null}
        completionRun={run}
        busy=""
        busyElapsedSeconds={0}
        onRunQualityChecks={vi.fn()}
        onImproveScore={vi.fn()}
        onAcceptPatch={vi.fn()}
        onAcceptAllPatches={onAcceptAllPatches}
        onOpenExpertTool={vi.fn()}
      />,
    );

    const button = screen.getByRole("button", { name: /一键接受补强/ });
    expect(button).toBeDisabled();
  });

  it("disables one-click acceptance button if busy state is active", () => {
    const onAcceptAllPatches = vi.fn();
    render(
      <QualityPanel
        actionGate={allowedGate}
        filingReport={null}
        worksheet={null}
        completionRun={makeCompletionRun()}
        busy="guided-quality"
        busyElapsedSeconds={5}
        onRunQualityChecks={vi.fn()}
        onImproveScore={vi.fn()}
        onAcceptPatch={vi.fn()}
        onAcceptAllPatches={onAcceptAllPatches}
        onOpenExpertTool={vi.fn()}
      />,
    );

    const button = screen.getByRole("button", { name: /一键接受补强/ });
    expect(button).toBeDisabled();
  });

  it("disables completion patch mutations when the workflow gate is closed", async () => {
    const onAcceptPatch = vi.fn();
    const onAcceptAllPatches = vi.fn();
    render(
      <QualityPanel
        actionGate={{ allowed: false, reason: "请先完成发明点确认" }}
        filingReport={null}
        worksheet={null}
        completionRun={makeCompletionRun()}
        busy=""
        busyElapsedSeconds={0}
        onRunQualityChecks={vi.fn()}
        onImproveScore={vi.fn()}
        onAcceptPatch={onAcceptPatch}
        onAcceptAllPatches={onAcceptAllPatches}
        onOpenExpertTool={vi.fn()}
      />,
    );

    const acceptAllButton = screen.getByRole("button", { name: /一键接受补强/ });
    expect(acceptAllButton).toBeDisabled();
    await userEvent.click(acceptAllButton);
    expect(onAcceptAllPatches).not.toHaveBeenCalled();

    for (const acceptButton of screen.getAllByRole("button", { name: "接受补强建议" })) {
      expect(acceptButton).toBeDisabled();
      await userEvent.click(acceptButton);
    }
    expect(onAcceptPatch).not.toHaveBeenCalled();
  });

  it("marks quality entry cards with a dedicated layout hook", () => {
    render(
      <QualityPanel
        actionGate={allowedGate}
        filingReport={null}
        worksheet={null}
        completionRun={null}
        busy=""
        busyElapsedSeconds={0}
        onRunQualityChecks={vi.fn()}
        onImproveScore={vi.fn()}
        onAcceptPatch={vi.fn()}
        onAcceptAllPatches={vi.fn()}
        onOpenExpertTool={vi.fn()}
      />,
    );

    const entryGroup = screen.getByRole("heading", { name: "检查入口" }).closest(".settings-group");

    if (!(entryGroup instanceof HTMLElement)) {
      throw new Error("Expected the quality entry settings group to render.");
    }

    for (const label of ["提交成熟度", "权利要求防线", "初稿完善"]) {
      expect(within(entryGroup).getByText(label).closest(".info-card")).toHaveClass("quality-tool-card");
    }
  });
});
