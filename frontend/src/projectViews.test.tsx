import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DraftPackage, ProjectRecord } from "./api";
import { ProjectsOverview } from "./views/projectViews";

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
    expect(within(table as HTMLTableElement).getByText("需成稿会审")).toBeInTheDocument();
    expect(within(table as HTMLTableElement).queryByText("可进入导出")).not.toBeInTheDocument();

    const mobileCards = container.querySelectorAll("article");
    expect(mobileCards).toHaveLength(2);
    expect(within(mobileCards[0]).getByText("需成稿会审")).toBeInTheDocument();
    expect(within(mobileCards[0]).queryByText("可进入导出")).not.toBeInTheDocument();
  });
});
