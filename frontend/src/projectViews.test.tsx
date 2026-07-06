import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DraftPackage, ProjectRecord } from "./api";
import { CorpusView, ProjectSelect, ProjectsOverview } from "./views/projectViews";

const draftPackage: DraftPackage = {
  title: "一种无人机主动采集方法",
  abstract: "本发明公开一种无人机主动采集方法。",
  claims: "1. 一种方法，包括基于置信度热力图生成采集任务。",
  description: "本发明涉及无人机主动采集技术领域。",
  drawing_description: "图1为方法流程图。",
  mermaid: "",
  image_prompt: "",
  review_findings: [],
  citations: [],
  generation_logs: [],
};

function makeProject(overrides: Partial<ProjectRecord>): ProjectRecord {
  return {
    id: "project-1",
    name: "城市体检无人机采集",
    draft_text: "",
    patent_type: "invention",
    package: null,
    created_at: "2026-06-19T00:00:00Z",
    updated_at: "2026-06-19T00:00:00Z",
    applicant: "",
    inventors: "",
    technical_field: "",
    background: "",
    pain_point: "",
    technical_solution: "",
    innovation: "",
    embodiments: "",
    beneficial_effects: "",
    ...overrides,
  };
}

describe("ProjectsOverview export status", () => {
  it("shows conservative export gate copy for packaged projects in desktop and mobile markup", () => {
    const packagedProject = makeProject({
      id: "packaged-1",
      name: "已生成初稿项目",
      package: draftPackage,
    });
    const ideaOnlyProject = makeProject({
      id: "idea-1",
      name: "仅有想法项目",
      draft_text: "一个待生成初稿的想法",
    });

    const { container } = render(
      <ProjectsOverview
        projects={[packagedProject, ideaOnlyProject]}
        selectedProjectId=""
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        busy=""
      />,
    );

    expect(screen.queryByText("可进入导出")).not.toBeInTheDocument();
    expect(screen.getAllByText("需成稿会审")).toHaveLength(2);
    expect(screen.getAllByText("未生成初稿")).toHaveLength(2);

    const table = container.querySelector("table");
    expect(table).toBeTruthy();
    expect(table).toHaveClass("min-w-[840px]");
    expect(within(table as HTMLTableElement).getByText("需成稿会审")).toBeInTheDocument();
    expect(within(table as HTMLTableElement).queryByText("可进入导出")).not.toBeInTheDocument();
    expect(within(table as HTMLTableElement).getByRole("columnheader", { name: "当前步骤" })).toHaveClass("whitespace-nowrap");
    expect(within(table as HTMLTableElement).getByRole("columnheader", { name: "更新时间" })).toHaveClass("whitespace-nowrap");
    const desktopSelectButton = within(table as HTMLTableElement).getAllByRole("button", { name: "选择" })[0];
    const desktopDeleteButton = within(table as HTMLTableElement).getAllByRole("button", { name: "删除" })[0];
    expect(desktopSelectButton).toHaveClass("whitespace-nowrap");
    expect(desktopSelectButton).toHaveClass("min-w-[72px]");
    expect(desktopDeleteButton).toHaveClass("whitespace-nowrap");
    expect(desktopDeleteButton).toHaveClass("min-w-[68px]");

    const mobileCards = container.querySelectorAll("article");
    expect(mobileCards).toHaveLength(2);
    expect(within(mobileCards[0]).getByText("需成稿会审")).toBeInTheDocument();
    expect(within(mobileCards[0]).queryByText("可进入导出")).not.toBeInTheDocument();
  });
});

describe("Project list load recovery", () => {
  it("associates the failed load helper with the selector while keeping stale projects selectable", () => {
    render(
      <ProjectSelect
        projects={[
          makeProject({
            id: "stale-project",
            name: "上次加载的项目",
          }),
        ]}
        selectedProjectId=""
        loadStatus="failed"
        onChange={vi.fn()}
      />,
    );

    const select = screen.getByRole("combobox", { name: "当前项目" });
    const helper = screen.getByText("项目列表加载失败。恢复后端连接后，使用右上角刷新重试。");

    expect(select).toHaveAttribute("aria-describedby", helper.id);
    expect(select).toHaveAccessibleDescription("项目列表加载失败。恢复后端连接后，使用右上角刷新重试。");
    expect(screen.getByRole("option", { name: "上次加载的项目" })).toBeInTheDocument();
  });

  it("explains failed empty project results are not a true empty workspace", () => {
    render(
      <ProjectsOverview
        projects={[]}
        selectedProjectId=""
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        busy=""
        loadStatus="failed"
      />,
    );

    expect(screen.getAllByText("项目列表加载失败。恢复后端连接后，使用右上角刷新重试；这不是空项目列表。")).toHaveLength(2);
    expect(screen.queryByText("暂无项目。进入“专利生成”输入想法即可创建。")).not.toBeInTheDocument();
  });
});

describe("CorpusView reference imports", () => {
  it("allows selecting multiple reference files", () => {
    const { container } = render(
      <CorpusView
        documents={[]}
        searchText=""
        searchSection=""
        searchResults={[]}
        busy=""
        onImport={vi.fn()}
        onSearch={vi.fn()}
        onSearchText={vi.fn()}
        onSearchSection={vi.fn()}
      />,
    );

    const input = screen.getByLabelText("导入参考材料") as HTMLInputElement;
    expect(input).toHaveAttribute("multiple");
    expect(container.querySelector(".corpus-search-card .info-card-icon")).toBeTruthy();
    expect(screen.getByRole("button", { name: "检索" })).toHaveClass("corpus-search-button");
  });

  it("submits the reference import form with all selected files intact", () => {
    const onImport = vi.fn((event) => event.preventDefault());
    render(
      <CorpusView
        documents={[]}
        searchText=""
        searchSection=""
        searchResults={[]}
        busy=""
        onImport={onImport}
        onSearch={vi.fn()}
        onSearchText={vi.fn()}
        onSearchSection={vi.fn()}
      />,
    );

    const input = screen.getByLabelText("导入参考材料") as HTMLInputElement;
    const files = [
      new File(["alpha"], "agent-alpha.md", { type: "text/markdown" }),
      new File(["beta"], "agent-beta.md", { type: "text/markdown" }),
    ];
    fireEvent.change(input, { target: { files } });
    fireEvent.submit(input.form as HTMLFormElement);

    expect(onImport).toHaveBeenCalledTimes(1);
    expect(input.files).toHaveLength(2);
  });
});
