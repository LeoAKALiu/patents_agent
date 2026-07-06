import { describe, expect, it } from "vitest";

import type { OfficialDraftPackage } from "@/api";
import { findOfficialContaminationMarkers } from "./officialContamination";

function officialPackage(overrides: Partial<OfficialDraftPackage> = {}): OfficialDraftPackage {
  return {
    title: "一种城市体检无人机补采方法",
    abstract: "本发明公开一种城市体检无人机补采方法。",
    claims: "1. 一种城市体检无人机补采方法。",
    description: "本发明涉及城市体检数据补采。",
    drawing_description: "图1为方法流程图。",
    figure_plan: [],
    compile_warnings: [],
    source_draft_hash: "draft-hash",
    official_package_hash: "official-hash",
    ...overrides,
  };
}

describe("findOfficialContaminationMarkers", () => {
  it("flags residual internal notes in official claims", () => {
    const matches = findOfficialContaminationMarkers(
      officialPackage({
        claims: "1. 一种城市体检无人机补采方法。\n*(注：内部备注)**",
      }),
    );

    expect(matches).toContainEqual({ section: "claims", pattern: "内部备注" });
  });
});
