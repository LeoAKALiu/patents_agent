import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { SystemStatusPanel } from "./ui/SystemStatusPanel";
import type { SystemStatusPanelProps } from "./ui/SystemStatusPanel";
import type { ProjectRecord, Health, AgentDoctorReport, DraftPackage } from "./api";

function makeDraftPackage(): DraftPackage {
  return {
    title: "测试初稿",
    abstract: "摘要。",
    claims: "1. 一种测试方法。",
    description: "说明书。",
    drawing_description: "图1。",
    mermaid: "flowchart TD\nA --> B",
    image_prompt: "线稿。",
    review_findings: [],
    citations: [],
    generation_logs: [],
  };
}

function makeProject(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    id: overrides.id ?? "proj-1",
    name: overrides.name ?? "测试项目",
    draft_text: overrides.draft_text ?? "测试交底文本",
    patent_type: overrides.patent_type ?? "invention",
    package: overrides.package ?? null,
    created_at: overrides.created_at ?? "2026-06-18T00:00:00Z",
    updated_at: overrides.updated_at ?? "2026-06-18T00:00:00Z",
  };
}

function makeHealth(overrides: Partial<Health> = {}): Health {
  return {
    ok: overrides.ok ?? true,
    llm_configured: overrides.llm_configured ?? true,
    data_dir: overrides.data_dir ?? "/tmp/patentagent-test",
    model: overrides.model ?? "test-model",
    embedding_model: overrides.embedding_model ?? "test-embedding",
  };
}

function makeAgentDoctor(overrides: Partial<AgentDoctorReport> = {}): AgentDoctorReport {
  return {
    status: overrides.status ?? "ready",
    run_mode: overrides.run_mode ?? "full",
    active_provider_ids: overrides.active_provider_ids ?? [],
    missing_required: overrides.missing_required ?? [],
    missing_optional: overrides.missing_optional ?? [],
    unknown_required: overrides.unknown_required ?? [],
    commands: overrides.commands ?? {},
  };
}

function render(props: SystemStatusPanelProps): string {
  return renderToStaticMarkup(createElement(SystemStatusPanel, props));
}

describe("SystemStatusPanel", () => {
  it("renders current project name when selected", () => {
    const html = render({
      selectedProject: makeProject({ name: "智能施工监控系统" }),
    });
    expect(html).toContain("智能施工监控系统");
    expect(html).toContain("当前项目");
  });

  it("shows '未选择' when no project selected", () => {
    const html = render({ selectedProject: null });
    expect(html).toContain("未选择");
  });

  it("shows '已有初稿' badge when project has a package", () => {
    const html = render({
      selectedProject: makeProject({ package: makeDraftPackage() }),
    });
    expect(html).toContain("已有初稿");
  });

  it("shows '新建中' badge when project has no package", () => {
    const html = render({
      selectedProject: makeProject({ package: null }),
    });
    expect(html).toContain("新建中");
  });

  it("shows '可用' for configured LLM", () => {
    const html = render({
      health: makeHealth({ llm_configured: true }),
    });
    expect(html).toContain("可用");
    expect(html).toContain("模型与智能体");
  });

  it("shows '未配置' for missing LLM", () => {
    const html = render({
      health: makeHealth({ llm_configured: false }),
    });
    expect(html).toContain("未配置");
  });

  it("renders agent run mode from agentDoctor", () => {
    const html = render({
      agentDoctor: makeAgentDoctor({ run_mode: "full", status: "ready" }),
      agentRunModeLabel: (mode: string) => `模式: ${mode}`,
    });
    expect(html).toContain("模式: full");
  });

  it("shows refresh button when onRefresh provided", () => {
    const html = render({ onRefresh: () => {} });
    expect(html).toContain("刷新运行状态");
  });

  it("hides refresh button when onRefresh not provided", () => {
    const html = render({});
    expect(html).not.toContain("刷新运行状态");
  });

  it("renders all three information cards", () => {
    const html = render({
      selectedProject: makeProject(),
      health: makeHealth(),
      agentDoctor: makeAgentDoctor(),
      onRefresh: () => {},
    });
    // Key labels from each card
    expect(html).toContain("当前项目");
    expect(html).toContain("模型与智能体");
    expect(html).toContain("刷新运行状态");
  });
});
