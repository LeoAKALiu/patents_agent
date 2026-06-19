import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PostDraftRepairEditor } from "./flow/panels/PostDraftRepairEditor";

const session = {
  project_id: "p1",
  review_run_id: "r1",
  draft_package_hash: "old",
  current_draft_hash: "old",
  stale: false,
  issues: [
    {
      id: "blocking-1",
      kind: "blocking" as const,
      severity: "critical" as const,
      source: "post_draft_review",
      message: "标题存在重复词汇方法方法",
      snippet: "方法方法",
      target_section: "title" as const,
      anchor: { type: "text" as const, section: "title" as const, start: 22, end: 26, snippet: "方法方法" },
      status: "open" as const,
    },
  ],
  sections: {
    title: "一种基于城市体检指标置信度的无人机主动采集方法方法",
    abstract: "摘要文本",
    claims: "权利要求文本",
    description: "说明书文本",
    drawing_description: "图1说明",
  },
};

describe("PostDraftRepairEditor", () => {
  it("renders issue rail, editable sections, and inspector actions", async () => {
    render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    expect(screen.getByText("阻断")).toBeTruthy();
    expect(screen.getByDisplayValue(/方法方法/)).toBeTruthy();

    // Click on an issue to select it, which reveals inspector buttons
    const issueButton = screen.getByRole("button", { name: /标题存在重复词汇/ });
    await userEvent.click(issueButton);

    expect(screen.getByRole("button", { name: "人工修正" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "生成 AI 修正" })).toBeTruthy();
  });

  it("saves edited section content", async () => {
    const onSave = vi.fn();
    render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={onSave}
      />,
    );

    const titleField = screen.getByLabelText("标题");
    await userEvent.clear(titleField);
    await userEvent.type(titleField, "一种基于城市体检指标置信度的无人机主动采集方法");

    await userEvent.click(screen.getByRole("button", { name: "保存当前初稿" }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "一种基于城市体检指标置信度的无人机主动采集方法",
      }),
    );
  });

  it("returns null when closed", () => {
    const { container } = render(
      <PostDraftRepairEditor
        open={false}
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("returns null when session is null", () => {
    const { container } = render(
      <PostDraftRepairEditor
        open
        session={null}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("disables AI generate button", async () => {
    render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    // Select the issue first
    const issueButton = screen.getByRole("button", { name: /标题存在重复词汇/ });
    await userEvent.click(issueButton);

    const aiButton = screen.getByRole("button", { name: "生成 AI 修正" });
    expect((aiButton as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows stale warning when draft has changed", () => {
    const staleSession = { ...session, stale: true };
    render(
      <PostDraftRepairEditor
        open
        session={staleSession}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByText(/初稿已变更/)).toBeTruthy();
  });
});
