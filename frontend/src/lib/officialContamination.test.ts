import { describe, expect, it } from "vitest";

import { findOfficialContaminationMarkers } from "./officialContamination";
import type { OfficialDraftPackage } from "@/api";

function makePackage(overrides: Partial<OfficialDraftPackage> = {}): OfficialDraftPackage {
  return {
    title: "一种无人机主动采集方法",
    abstract: "本发明公开了一种无人机主动采集方法。",
    claims: "1. 一种方法，包括生成无人机任务包。",
    description: "本发明涉及无人机任务规划技术领域。",
    drawing_description: "图1为方法流程图。",
    figure_plan: [],
    compile_warnings: [],
    source_draft_hash: "abc123",
    official_package_hash: "def456",
    ...overrides,
  };
}

describe("findOfficialContaminationMarkers", () => {
  // ── PR-5: Chinese annotation labels — label-style only ──────────────

  it("does not flag normal patent prose that contains 支撑不足", () => {
    const pkg = makePackage({
      description: "本发明对支撑不足的问题进行了改进，提升了检测精度。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const chineseLabels = matches.filter((m) => m.pattern === "撰写说明与支撑不足提示");
    expect(chineseLabels).toHaveLength(0);
  });

  it("does not flag normal patent prose that contains 支撑不足提示 without colon", () => {
    const pkg = makePackage({
      description: "本发明解决了现有技术中支撑不足提示不明确的问题。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const chineseLabels = matches.filter((m) => m.pattern === "撰写说明与支撑不足提示");
    expect(chineseLabels).toHaveLength(0);
  });

  it("does not flag normal patent prose that contains 撰写说明 without colon", () => {
    const pkg = makePackage({
      description: "本发明的撰写说明如下：首先确定采集区域。",
    });
    // This shouldn't match because "撰写说明" is followed inline by "如下" not ":"
    // but the regex requires optional whitespace then colon, so "撰写说明如下" won't match.
    const matches = findOfficialContaminationMarkers(pkg);
    const chineseLabels = matches.filter((m) => m.pattern === "撰写说明与支撑不足提示");
    expect(chineseLabels).toHaveLength(0);
  });

  it("flags 支撑不足提示： as chinese_label (colon-delimited annotation)", () => {
    const pkg = makePackage({
      description: "支撑不足提示：说明书未充分公开实施方式。\n本发明涉及AI检测技术领域。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const chineseLabels = matches.filter((m) => m.pattern === "撰写说明与支撑不足提示");
    expect(chineseLabels.length).toBeGreaterThanOrEqual(1);
    expect(chineseLabels[0].section).toBe("description");
  });

  it("flags 撰写说明： as chinese_label (colon-delimited annotation)", () => {
    const pkg = makePackage({
      description: "撰写说明：需要补充具体实施方式。\n本发明涉及AI检测技术领域。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const chineseLabels = matches.filter((m) => m.pattern === "撰写说明与支撑不足提示");
    expect(chineseLabels.length).toBeGreaterThanOrEqual(1);
    expect(chineseLabels[0].section).toBe("description");
  });

  it("flags 撰写说明与支撑不足提示 as chinese_label (compound label)", () => {
    const pkg = makePackage({
      description: "撰写说明与支撑不足提示：说明书需要补充实施例。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const chineseLabels = matches.filter((m) => m.pattern === "撰写说明与支撑不足提示");
    expect(chineseLabels.length).toBeGreaterThanOrEqual(1);
  });

  it("flags 支撑不足提示： with half-width colon too", () => {
    const pkg = makePackage({
      description: "支撑不足提示:说明书未充分公开。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const chineseLabels = matches.filter((m) => m.pattern === "撰写说明与支撑不足提示");
    expect(chineseLabels.length).toBeGreaterThanOrEqual(1);
  });

  // ── support_gap / support_gaps — preserved key detection ────────────

  it("flags support_gap as substring match", () => {
    const pkg = makePackage({
      description: "support_gap: 说明书待补充。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const supportGapMatches = matches.filter((m) => m.pattern === "support_gap");
    expect(supportGapMatches.length).toBeGreaterThanOrEqual(1);
  });

  it("flags support_gaps as substring match", () => {
    const pkg = makePackage({
      description: "support_gaps: 说明书待补充。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const supportGapsMatches = matches.filter((m) => m.pattern === "support_gaps");
    expect(supportGapsMatches.length).toBeGreaterThanOrEqual(1);
  });

  // ── Internal field / mermaid / fence detection — preserved ──────────

  it("flags internal_field patterns like image_prompt:", () => {
    const pkg = makePackage({
      drawing_description: "图1为方法流程图。\nimage_prompt: 黑白线稿。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const internalFields = matches.filter((m) => m.pattern === "internal_field");
    expect(internalFields.length).toBeGreaterThanOrEqual(1);
  });

  it("flags mermaid fences", () => {
    const pkg = makePackage({
      description: "flowchart TD\nA --> B",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const mermaidMatches = matches.filter((m) => m.pattern === "mermaid");
    expect(mermaidMatches.length).toBeGreaterThanOrEqual(1);
  });

  it("flags markdown fences", () => {
    const pkg = makePackage({
      description: "```\ncode block\n```",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const fenceMatches = matches.filter((m) => m.pattern === "markdown_fence");
    expect(fenceMatches.length).toBeGreaterThanOrEqual(1);
  });

  // ── Clean package returns no matches ─────────────────────────────────

  it("returns no matches for a clean official package", () => {
    const pkg = makePackage();
    const matches = findOfficialContaminationMarkers(pkg);
    expect(matches).toHaveLength(0);
  });

  // ── Unfavorable statements — preserved ───────────────────────────────

  it("flags 可能不具备创造性 in claims", () => {
    const pkg = makePackage({
      claims: "1. 一种方法，可能不具备创造性。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const unfavorable = matches.filter((m) => m.pattern === "可能不具备创造性");
    expect(unfavorable.length).toBeGreaterThanOrEqual(1);
  });

  // ── PR-5 v2: anchored detection regression tests ─────────────────────

  it("preserves inline Chinese colon prose (does not flag)", () => {
    const pkg = makePackage({
      description:
        "传感器数据 支撑不足提示：仍是描述，不应被识别。\n在专利撰写说明中，需要详细阐述技术方案。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    const chineseLabelMatches = matches.filter(
      (m) => m.pattern === "撰写说明与支撑不足提示"
    );
    expect(chineseLabelMatches).toHaveLength(0);
  });

  it("flags compound line-leading 撰写说明与支撑不足提示 in claims", () => {
    const pkg = makePackage({
      claims: "1. 一种方法。\n\n撰写说明与支撑不足提示 support_gap: 需要补矩阵。",
    });
    const matches = findOfficialContaminationMarkers(pkg);
    // CHINESE_LABEL_RE requires a colon delimiter directly after the Chinese label;
    // when an English keyword like support_gap intervenes, it is caught by the
    // substring patterns instead.
    expect(matches.some(
      (m) => m.section === "claims" && (m.pattern === "撰写说明与支撑不足提示" || m.pattern === "support_gap")
    )).toBe(true);
  });
});
