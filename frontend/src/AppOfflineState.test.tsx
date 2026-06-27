import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { SystemStatusPanel } from "./ui/SystemStatusPanel";
import { ProjectSelect, ProjectsOverview } from "./views/projectViews";
import type { ProjectRecord } from "./api";

const project: ProjectRecord = {
  id: "p-1",
  name: "Cached Project",
  draft_text: "idea",
  patent_type: "invention",
  package: null,
  created_at: "2026-06-27T00:00:00Z",
  updated_at: "2026-06-27T00:00:00Z",
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

describe("offline app state", () => {
  it("does not label capabilities as available when backend status is offline", () => {
    const html = renderToStaticMarkup(
      createElement(SystemStatusPanel, {
        selectedProject: null,
        health: null,
        agentDoctor: null,
        backendStatus: "offline",
        projectListStatus: "failed",
        agentRunModeLabel: (mode: string) => mode,
      }),
    );

    expect(html).toContain("后端离线");
    expect(html).toContain("离线");
    expect(html).not.toContain("可用");
  });

  it("distinguishes failed project loading from a true empty project list", () => {
    const failedSelect = renderToStaticMarkup(
      createElement(ProjectSelect, {
        projects: [],
        selectedProjectId: "",
        loadStatus: "failed",
        onChange: () => undefined,
      }),
    );
    const emptySelect = renderToStaticMarkup(
      createElement(ProjectSelect, {
        projects: [],
        selectedProjectId: "",
        loadStatus: "ready",
        onChange: () => undefined,
      }),
    );

    expect(failedSelect).toContain("项目加载失败");
    expect(emptySelect).toContain("暂无项目");
  });

  it("labels cached project data as stale after a failed refresh", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectsOverview, {
        projects: [project],
        selectedProjectId: "p-1",
        loadStatus: "failed",
        onSelect: () => undefined,
        onDelete: () => undefined,
        busy: "",
      }),
    );

    expect(html).toContain("项目列表加载失败");
    expect(html).toContain("显示上次成功加载的数据");
    expect(html).toContain("Cached Project");
  });
});
