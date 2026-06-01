import { describe, expect, it } from "vitest";

import {
  canExportPackage,
  completionCategoryLabel,
  completionScoreAverage,
  completionTargetLabel,
  evidenceStatusLabel,
  featureClassificationLabel,
  moatScoreTotal,
  readinessStatusLabel,
  sourceTypeLabel,
  splitLines,
  workspaceTabs,
} from "./domain";

describe("workspaceTabs", () => {
  it("keeps the planned workbench pages in order", () => {
    expect(workspaceTabs.map((tab) => tab.label)).toEqual([
      "语料库建设",
      "知识库",
      "创建专利项目",
      "护城河地图",
      "前置材料",
      "多 Agent 会审",
      "分步撰写",
      "提交成熟度",
      "权利要求防线",
      "初稿完善",
      "审查修改",
      "导出",
    ]);
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
  it("returns the first completed deliberation run", async () => {
    const { latestCompletedDeliberation } = await import("./domain");
    expect(
      latestCompletedDeliberation([
        { id: "running", status: "running" },
        { id: "completed", status: "completed" },
      ]),
    ).toEqual({ id: "completed", status: "completed" });
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
});
