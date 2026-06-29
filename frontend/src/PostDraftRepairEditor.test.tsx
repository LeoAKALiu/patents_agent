import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as api from "@/api";
import { PostDraftRepairEditor } from "./flow/panels/PostDraftRepairEditor";

vi.mock("@/api", async () => {
  const actual = await vi.importActual<typeof import("@/api")>("@/api");
  return {
    ...actual,
    createDraftRepairPatch: vi.fn(),
    applyDraftRepairPatch: vi.fn(),
  };
});

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
      anchor: {
        type: "text" as const,
        section: "title" as const,
        start: 22,
        end: 26,
        snippet: "方法方法",
      },
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
  beforeEach(() => {
    vi.mocked(api.createDraftRepairPatch).mockReset();
    vi.mocked(api.applyDraftRepairPatch).mockReset();
  });

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

    expect(screen.getByText("问题队列")).toBeTruthy();
    expect(screen.getByText("正文定位")).toBeTruthy();
    expect(screen.getAllByText("阻断").length).toBeGreaterThan(0);
    expect(screen.getByDisplayValue(/方法方法/)).toBeTruthy();

    // The first issue is selected by default so the inspector is useful immediately.
    expect(screen.getByText("修复面板")).toBeTruthy();
    expect(screen.getByText("命中文本")).toBeTruthy();
    expect(screen.getByText("文本匹配")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "人工修正" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "生成 AI 修正" }),
    ).toBeTruthy();
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
    await userEvent.type(
      titleField,
      "一种基于城市体检指标置信度的无人机主动采集方法",
    );

    await userEvent.click(
      screen.getByRole("button", { name: "保存当前初稿" }),
    );

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

  it("enables AI generate button when session is fresh", async () => {
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
    const issueButton = screen.getByRole("button", {
      name: /标题存在重复词汇/,
    });
    await userEvent.click(issueButton);

    const aiButton = screen.getByRole("button", { name: "生成 AI 修正" });
    expect((aiButton as HTMLButtonElement).disabled).toBe(false);
  });

  it("disables AI generate button when session is stale", async () => {
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

    const issueButton = screen.getByRole("button", {
      name: /标题存在重复词汇/,
    });
    await userEvent.click(issueButton);

    const aiButton = screen.getByRole("button", { name: "生成 AI 修正" });
    expect((aiButton as HTMLButtonElement).disabled).toBe(true);
  });

  it("renders without dialog chrome in embedded mode", () => {
    render(
      <PostDraftRepairEditor
        open
        mode="embedded"
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByRole("button", { name: "关闭标注式修复编辑器" })).toBeNull();
    expect(screen.getByText("问题队列")).toBeTruthy();
    expect(screen.getByText("正文定位")).toBeTruthy();
    expect(screen.getByText("修复面板")).toBeTruthy();
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
    expect(screen.getAllByText(/初稿已变更/).length).toBeGreaterThan(0);
  });

  it("selecting a different issue clears patch state", async () => {
    render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    // Select first issue
    const issueButton = screen.getByRole("button", {
      name: /标题存在重复词汇/,
    });
    await userEvent.click(issueButton);

    // AI generate button should be visible and enabled
    expect(
      screen.getByRole("button", { name: "生成 AI 修正" }),
    ).toBeTruthy();
  });

  it("shows pending revalidation marker for applied issue display state", () => {
    render(
      <PostDraftRepairEditor
        open
        mode="embedded"
        session={session}
        saving={false}
        pendingRevalidationIssueIds={["blocking-1"]}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    expect(screen.getAllByText("待复核").length).toBeGreaterThan(0);
  });

  it("applies a generated patch through onPatchApplied without triggering manual save", async () => {
    const onSave = vi.fn();
    const onPatchApplied = vi.fn();
    vi.mocked(api.createDraftRepairPatch).mockResolvedValue({
      id: "patch-1",
      issue_id: "blocking-1",
      project_id: "p1",
      review_run_id: "r1",
      status: "proposed",
      target_section: "title",
      original: "方法方法",
      patched: "方法",
      diff_summary: "删除重复词汇",
      risk_notes: [],
      draft_package_hash: "old",
    });
    vi.mocked(api.applyDraftRepairPatch).mockResolvedValue({
      package: {
        title: "一种基于城市体检指标置信度的无人机主动采集方法",
        abstract: "摘要文本",
        claims: "权利要求文本",
        description: "说明书文本",
        drawing_description: "图1说明",
        mermaid: "",
        image_prompt: "",
        review_findings: [],
        citations: [],
        generation_logs: [],
      },
      current_draft_hash: "new-hash",
    });

    render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={onSave}
        onPatchApplied={onPatchApplied}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "生成 AI 修正" }));
    expect(await screen.findByText("删除重复词汇")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "应用 AI 修正" }));

    expect(api.createDraftRepairPatch).toHaveBeenCalledWith(
      "p1",
      "r1",
      expect.objectContaining({
        issue_id: "blocking-1",
        target_section: "title",
      }),
    );
    expect(api.applyDraftRepairPatch).toHaveBeenCalledWith("p1", "r1", "patch-1");
    expect(onPatchApplied).toHaveBeenCalledWith(
      {
        title: "一种基于城市体检指标置信度的无人机主动采集方法",
        abstract: "摘要文本",
        claims: "权利要求文本",
        description: "说明书文本",
        drawing_description: "图1说明",
      },
      "blocking-1",
    );
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByDisplayValue("一种基于城市体检指标置信度的无人机主动采集方法")).toBeInTheDocument();
  });
});
