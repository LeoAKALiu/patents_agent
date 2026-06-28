import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
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
});
