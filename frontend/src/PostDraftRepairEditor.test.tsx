import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { applyDraftRepairPatch, createDraftRepairPatch } from "@/api";
import { PostDraftRepairEditor } from "./flow/panels/PostDraftRepairEditor";

vi.mock("@/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api")>();
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

const mockCreateDraftRepairPatch = vi.mocked(createDraftRepairPatch);
const mockApplyDraftRepairPatch = vi.mocked(applyDraftRepairPatch);

function packageFromSections(fields: typeof session.sections): Awaited<ReturnType<typeof applyDraftRepairPatch>>["package"] {
  return {
    ...fields,
    mermaid: "",
    image_prompt: "",
    review_findings: [],
    citations: [],
    generation_logs: [],
  };
}

describe("PostDraftRepairEditor", () => {
  beforeEach(() => {
    mockCreateDraftRepairPatch.mockReset();
    mockApplyDraftRepairPatch.mockReset();
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

  it("does not send stale issue text as selected text for section-level fixes", async () => {
    const descriptionSession = {
      ...session,
      issues: [
        {
          id: "blocking-description",
          kind: "blocking" as const,
          severity: "critical" as const,
          source: "post_draft_review",
          message: "说明书使用绝对化表述，如“解决了”“消除了”“首次”",
          snippet: "说明书使用绝对化表述，如“解决了”“消除了”“首次”",
          target_section: "description" as const,
          anchor: {
            type: "section" as const,
            section: "description" as const,
            start: null,
            end: null,
            snippet: "说明书使用绝对化表述，如“解决了”“消除了”“首次”",
          },
          status: "open" as const,
        },
      ],
      sections: {
        ...session.sections,
        description: "本发明旨在缓解现有技术问题，并减少数据孤岛。",
      },
    };
    mockCreateDraftRepairPatch.mockResolvedValue({
      id: "patch-description",
      issue_id: "blocking-description",
      project_id: "p1",
      review_run_id: "r1",
      status: "proposed",
      target_section: "description",
      original: descriptionSession.sections.description,
      patched: "本发明旨在缓解现有技术问题，并减少数据壁垒。",
      diff_summary: "温和化绝对表述",
      risk_notes: [],
      draft_package_hash: "old",
    });

    render(
        <PostDraftRepairEditor
          open
          session={descriptionSession}
          saving={false}
          onClose={() => {}}
          onSave={vi.fn()}
        />,
    );

    await userEvent.click(screen.getByRole("button", { name: "生成 AI 修正" }));

    await waitFor(() => {
      expect(mockCreateDraftRepairPatch).toHaveBeenCalledWith(
        "p1",
        "r1",
        expect.objectContaining({
          selected_text: null,
          nearby_context: descriptionSession.sections.description,
        }),
      );
    });
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

    const rail = screen.getByRole("navigation", { name: "标注式修复问题导航" });
    const inspector = screen.getByRole("complementary", { name: "标注式修复详情面板" });
    expect(within(rail).getByText("待复核")).toBeInTheDocument();
    expect(within(inspector).getByText("待复核")).toBeInTheDocument();
  });

  it("removes an applied issue from the rail and advances to the next issue", async () => {
    const multiIssueSession = {
      ...session,
      issues: [
        session.issues[0],
        {
          id: "hit-claims",
          kind: "hit" as const,
          severity: "high" as const,
          source: "post_draft_review",
          message: "权利要求书开头存在内部提示",
          snippet: "好的，根据交底书撰写权利要求。",
          target_section: "claims" as const,
          anchor: {
            type: "text" as const,
            section: "claims" as const,
            start: 0,
            end: 15,
            snippet: "好的，根据交底书撰写权利要求。",
          },
          status: "open" as const,
        },
      ],
      sections: {
        ...session.sections,
        claims: "好的，根据交底书撰写权利要求。\n1. 一种方法。",
      },
    };
    mockCreateDraftRepairPatch.mockResolvedValue({
      id: "patch-title",
      issue_id: "blocking-1",
      project_id: "p1",
      review_run_id: "r1",
      status: "proposed",
      target_section: "title",
      original: "方法方法",
      patched: "方法",
      diff_summary: "清理重复词",
      risk_notes: [],
      draft_package_hash: "old",
    });
    mockApplyDraftRepairPatch.mockResolvedValue({
      current_draft_hash: "new",
      package: packageFromSections({
        title: "一种基于城市体检指标置信度的无人机主动采集方法",
        abstract: multiIssueSession.sections.abstract,
        claims: multiIssueSession.sections.claims,
        description: multiIssueSession.sections.description,
        drawing_description: multiIssueSession.sections.drawing_description,
      }),
    });

    render(
      <PostDraftRepairEditor
        open
        session={multiIssueSession}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    expect(screen.getByText("2 项")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "生成 AI 修正" }));
    await screen.findByText("清理重复词");
    await userEvent.click(screen.getByRole("button", { name: "应用 AI 修正" }));

    await screen.findByText("AI 修正已写回标题");
    expect(screen.getByText("1 项")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /标题存在重复词汇/ })).toBeNull();
    expect(screen.getByRole("button", { name: /权利要求书开头存在内部提示/ })).toHaveClass("selected");
  });

  it("applies a generated patch through onPatchApplied without triggering manual save", async () => {
    const onSave = vi.fn();
    const onPatchApplied = vi.fn();
    mockCreateDraftRepairPatch.mockResolvedValue({
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
    mockApplyDraftRepairPatch.mockResolvedValue({
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

    expect(mockCreateDraftRepairPatch).toHaveBeenCalledWith(
      "p1",
      "r1",
      expect.objectContaining({
        issue_id: "blocking-1",
        target_section: "title",
      }),
    );
    expect(mockApplyDraftRepairPatch).toHaveBeenCalledWith("p1", "r1", "patch-1");
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

  it("shows document and inspector feedback while applying an AI patch", async () => {
    let resolveApply: (value: Awaited<ReturnType<typeof applyDraftRepairPatch>>) => void = () => {};
    const applyPromise = new Promise<Awaited<ReturnType<typeof applyDraftRepairPatch>>>((resolve) => {
      resolveApply = resolve;
    });
    mockCreateDraftRepairPatch.mockResolvedValue({
      id: "patch-title",
      issue_id: "blocking-1",
      project_id: "p1",
      review_run_id: "r1",
      status: "proposed",
      target_section: "title",
      original: "方法方法",
      patched: "方法",
      diff_summary: "清理重复词",
      risk_notes: [],
      draft_package_hash: "old",
    });
    mockApplyDraftRepairPatch.mockReturnValue(applyPromise);

    render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "生成 AI 修正" }));
    await screen.findByText("清理重复词");
    await userEvent.click(screen.getByRole("button", { name: "应用 AI 修正" }));

    expect(screen.getByText("正在应用 AI 修正到标题")).toBeTruthy();
    expect(screen.getByLabelText("标题")).toHaveClass("patch-applying");

    await act(async () => {
      resolveApply({
        current_draft_hash: "new",
        package: packageFromSections({
          title: "一种基于城市体检指标置信度的无人机主动采集方法",
          abstract: session.sections.abstract,
          claims: session.sections.claims,
          description: session.sections.description,
          drawing_description: session.sections.drawing_description,
        }),
      });
      await applyPromise;
    });

    await screen.findByText("AI 修正已写回标题");
    expect(screen.getByLabelText("标题")).toHaveClass("patch-applied");
  });

  it("renders a stable three-pane layout in embedded mode and has an independently scrollable issue rail", () => {
    const { container } = render(
      <PostDraftRepairEditor
        open
        mode="embedded"
        session={session}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    // Three panes check
    expect(container.querySelector(".repair-issue-rail")).toBeInTheDocument();
    expect(container.querySelector(".repair-document-pane")).toBeInTheDocument();
    expect(container.querySelector(".repair-inspector")).toBeInTheDocument();

    // Independent scroll check for issue rail
    const scrollContainer = container.querySelector(".repair-issue-scroll");
    expect(scrollContainer).toBeInTheDocument();
  });

  it("renders 10+ issues, and selecting an issue updates selected draft section and inspector", async () => {
    const tenIssues = Array.from({ length: 12 }, (_, i) => {
      const targetSection: "title" | "abstract" = i % 2 === 0 ? "title" : "abstract";
      return {
        id: `issue-${i}`,
        kind: (i % 3 === 0 ? ("blocking" as const) : i % 3 === 1 ? ("hit" as const) : ("suggestion" as const)),
        severity: "high" as const,
        source: "post_draft_review" as const,
        message: `问题消息 ${i}`,
        snippet: null,
        target_section: targetSection,
        anchor: {
          type: "missing" as const,
          section: targetSection,
          start: null,
          end: null,
          snippet: null,
        },
        status: "open" as const,
      };
    });

    const sessionWithManyIssues = {
      ...session,
      issues: tenIssues,
    };

    render(
      <PostDraftRepairEditor
        open
        mode="embedded"
        session={sessionWithManyIssues}
        saving={false}
        onClose={() => {}}
        onSave={vi.fn()}
      />,
    );

    // Should display total item count (12)
    expect(screen.getByText("12 项")).toBeInTheDocument();

    // Select the 6th issue (index 5, which targets "abstract" since 5 % 2 === 1)
    const targetIssueButton = screen.getByRole("button", { name: /问题消息 5/ });
    await userEvent.click(targetIssueButton);

    // Inspector should update with the selected issue's message
    const rail = screen.getByRole("navigation", { name: "标注式修复问题导航" });
    const inspector = screen.getByRole("complementary", { name: "标注式修复详情面板" });
    const inspectorSummary = within(inspector).getByRole("region", { name: "当前问题摘要" });
    expect(within(rail).getByText("问题消息 5")).toBeInTheDocument();
    expect(within(inspectorSummary).getByText("问题消息 5")).toBeInTheDocument();

    // The abstract section should have the "selected" class
    const abstractLabel = screen.getByLabelText("摘要").closest(".annotated-draft-section");
    expect(abstractLabel).toHaveClass("selected");
  });

  it("shows pending revalidation status in rail and inspector after applying a patch", async () => {
    const onPatchApplied = vi.fn();
    mockCreateDraftRepairPatch.mockResolvedValue({
      id: "patch-1",
      issue_id: "blocking-1",
      project_id: "p1",
      review_run_id: "r1",
      status: "proposed",
      target_section: "title",
      original: "方法方法",
      patched: "方法",
      diff_summary: "删除重复词",
      risk_notes: [],
      draft_package_hash: "old",
    });
    mockApplyDraftRepairPatch.mockResolvedValue({
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

    const { rerender } = render(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        pendingRevalidationIssueIds={[]}
        onClose={() => {}}
        onSave={vi.fn()}
        onPatchApplied={onPatchApplied}
      />,
    );

    // Generate and apply patch
    await userEvent.click(screen.getByRole("button", { name: "生成 AI 修正" }));
    await screen.findByText("删除重复词");
    await userEvent.click(screen.getByRole("button", { name: "应用 AI 修正" }));

    expect(onPatchApplied).toHaveBeenCalledWith(expect.any(Object), "blocking-1");

    // Simulating parent state update: rerender with pendingRevalidationIssueIds including "blocking-1"
    rerender(
      <PostDraftRepairEditor
        open
        session={session}
        saving={false}
        pendingRevalidationIssueIds={["blocking-1"]}
        onClose={() => {}}
        onSave={vi.fn()}
        onPatchApplied={onPatchApplied}
      />,
    );

    // The issue should stay in the rail and show "待复核"
    const rail = screen.getByRole("navigation", { name: "标注式修复问题导航" });
    const inspector = screen.getByRole("complementary", { name: "标注式修复详情面板" });
    expect(within(rail).getByText("待复核")).toBeInTheDocument();
    expect(within(inspector).getByText("待复核")).toBeInTheDocument();
  });
});
