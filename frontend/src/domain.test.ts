import { describe, expect, it } from "vitest";

import {
  canExportPackage,
  completionCategoryLabel,
  completionPatchKindLabel,
  completionPatchStatusLabel,
  completionScoreAverage,
  completionTargetLabel,
  completionTaskStatusLabel,
  draftSectionLabel,
  evidenceStatusLabel,
  featureClassificationLabel,
  moatScoreTotal,
  pipelineRunStatusLabel,
  readinessStatusLabel,
  sourceTypeLabel,
  splitLines,
  worksheetSourceLabel,
  worksheetStatusLabel,
  workspaceTabs,
} from "./domain";
import { expertToolGroups, mainSections } from "./guidedFlow";

describe("guided navigation", () => {
  it("uses four primary sections and preserves expert tools", () => {
    expect(mainSections.map((section) => section.label)).toEqual(["专利生成", "实用新型轻量版", "项目", "专家工具"]);
    expect(expertToolGroups.flatMap((group) => group.tools.map((tool) => tool.label))).toEqual([
      "语料库建设",
      "知识库检索",
      "护城河地图",
      "前置材料",
      "多智能体会审",
      "分步撰写",
      "提交成熟度",
      "权利要求防线",
      "初稿完善",
      "审查修改",
      "导出文件",
    ]);
  });
});

describe("workspaceTabs compatibility", () => {
  it("keeps the legacy project creation tab until the shell migrates", () => {
    expect(workspaceTabs.map((tab) => tab.id)).toEqual([
      "build",
      "corpus",
      "create",
      "moat",
      "materials",
      "deliberate",
      "write",
      "readiness",
      "claimDefense",
      "completion",
      "review",
      "export",
    ]);
    expect(workspaceTabs.find((tab) => tab.id === "create")?.label).toBe("创建专利项目");
  });
});

describe("patent moat helpers", () => {
  it("labels evidence/source values and calculates weighted moat totals", () => {
    expect(evidenceStatusLabel("verified")).toBe("已验证");
    expect(evidenceStatusLabel("feasible_unverified")).toBe("可行未验证");
    expect(evidenceStatusLabel("needs_experiment")).toBe("需实验");
    expect(evidenceStatusLabel("model_generated")).toBe("模型生成");
    expect(sourceTypeLabel("user")).toBe("用户输入");
    expect(sourceTypeLabel("imported")).toBe("材料导入");
    expect(sourceTypeLabel("model")).toBe("模型生成");
    expect(
      moatScoreTotal({
        scope_width: 1,
        designaround_difficulty: 0.5,
        feasibility: 0.5,
        support_strength: 0.2,
        prior_art_distance: 0.75,
        strategic_value: 0.6,
      }),
    ).toBe(0.598);
  });

  it("normalizes newline, comma, and semicolon separated moat form lists", () => {
    expect(splitLines("方法\n系统；介质, 装置\n\n")).toEqual(["方法", "系统", "介质", "装置"]);
  });
});

describe("latestCompletedDeliberation", () => {
  it("returns the first strict completed deliberation run", async () => {
    const { latestCompletedDeliberation } = await import("./domain");
    const result = latestCompletedDeliberation([
        { id: "running", status: "running" },
        { id: "failed", status: "failed" },
        { id: "partial", status: "completed", providers: ["codex"], failures: [], stage_results: [], strategy_brief: {} },
        {
          id: "completed",
          status: "completed",
          providers: ["codex", "gemini", "claude"],
          failures: [],
          strategy_brief: {},
          stage_results: [
            ...["codex", "gemini", "claude"].map((provider) => ({
              phase: "opening",
              provider_id: provider,
              label: `opening ${provider}`,
              status: "completed",
            })),
            ...["pair codex-vs-gemini", "pair codex-vs-claude", "pair gemini-vs-claude"].map((label) => ({
              phase: "pair",
              provider_id: "codex",
              label,
              status: "completed",
            })),
            { phase: "chair", provider_id: "codex", label: "chair synthesis", status: "completed" },
          ],
        },
      ]);
    expect(result?.id).toBe("completed");
  });
});

describe("canExportPackage", () => {
  it("requires a generated package before export actions are enabled", () => {
    expect(canExportPackage(null)).toBe(false);
    expect(canExportPackage({ title: "一种方法", claims: "1. 一种方法。" })).toBe(true);
  });
});

describe("filing readiness helpers", () => {
  it("labels readiness status and feature classifications", () => {
    expect(readinessStatusLabel("clean")).toBe("干净");
    expect(readinessStatusLabel("warning")).toBe("有警告");
    expect(readinessStatusLabel("high_risk")).toBe("高风险");
    expect(featureClassificationLabel("core_combo")).toBe("核心组合");
    expect(featureClassificationLabel("support_needed")).toBe("需支撑");
  });
});

describe("draft completion helpers", () => {
  it("labels completion fields and averages scorecards", () => {
    expect(completionCategoryLabel("claim_support_gap")).toBe("权利要求支撑缺口");
    expect(completionTargetLabel("description")).toBe("说明书");
    expect(
      completionScoreAverage({
        authorization_stability: 80,
        protection_scope: 70,
        support_strength: 60,
        prior_art_distinction: 90,
        filing_maturity: 50,
        official_hygiene: 100,
        overall: 75,
      }),
    ).toBe(75);
  });

  it("labels completion tasks, patches, and draft sections", () => {
    expect(completionTaskStatusLabel("open")).toBe("待处理");
    expect(completionPatchStatusLabel("proposed")).toBe("待确认");
    expect(completionPatchKindLabel("rewrite")).toBe("改写");
    expect(draftSectionLabel("claims")).toBe("权利要求书");
    expect(draftSectionLabel("drawing_description")).toBe("附图说明");
  });
});

describe("expert tool status labels", () => {
  it("labels pipeline, worksheet, and source values", () => {
    expect(pipelineRunStatusLabel("queued")).toBe("排队中");
    expect(pipelineRunStatusLabel("interrupted")).toBe("已中断");
    expect(worksheetStatusLabel("reviewed")).toBe("已审阅");
    expect(worksheetSourceLabel("generated_package")).toBe("生成稿");
  });
});
