import { describe, expect, it } from "vitest";
import type { DisclosureRun, PatentPointCandidate } from "@/api";
import {
  isPatentPointCandidate,
  isRecord,
  patentPointCandidatesFromStageResults,
  patentPointCandidatesFromDisclosureRun,
  evidenceStatusText,
} from "./inventionSelectors";

const baseCandidate = {
  id: "p1",
  title: "候选一",
  protection_focus: [],
  support_gaps: [],
  innovation: "inn",
  technical_solution: "sol",
  evidence_status: "verified",
} as unknown as PatentPointCandidate;

function runWith(stages: Array<{ phase: string; payload: unknown }>): DisclosureRun {
  // Minimal shape; only the fields the selector reads are required.
  return { stage_results: stages as DisclosureRun["stage_results"] } as DisclosureRun;
}

describe("isRecord / isPatentPointCandidate", () => {
  it("isRecord rejects null and primitives", () => {
    expect(isRecord(null)).toBe(false);
    expect(isRecord(undefined)).toBe(false);
    expect(isRecord("x")).toBe(false);
    expect(isRecord({})).toBe(true);
  });

  it("isPatentPointCandidate validates the full candidate shape", () => {
    expect(isPatentPointCandidate(baseCandidate)).toBe(true);
    expect(isPatentPointCandidate({ ...baseCandidate, id: 1 })).toBe(false);
    expect(isPatentPointCandidate({ ...baseCandidate, protection_focus: "x" })).toBe(false);
  });
});

describe("patentPointCandidatesFromStageResults", () => {
  it("returns the newest patent_points stage payload", () => {
    const run = runWith([
      { phase: "patent_points", payload: { candidates: [baseCandidate] } },
      { phase: "patent_points", payload: { candidates: [{ ...baseCandidate, id: "p2" }] } },
    ]);
    const result = patentPointCandidatesFromStageResults(run);
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("p2");
  });

  it("skips non-patent_points phases", () => {
    const run = runWith([
      { phase: "other", payload: { candidates: [baseCandidate] } },
    ]);
    expect(patentPointCandidatesFromStageResults(run)).toEqual([]);
  });

  it("filters out malformed candidates", () => {
    const run = runWith([
      { phase: "patent_points", payload: { candidates: [baseCandidate, { id: "bad" }] } },
    ]);
    expect(patentPointCandidatesFromStageResults(run)).toEqual([baseCandidate]);
  });

  it("returns [] for null run", () => {
    expect(patentPointCandidatesFromStageResults(null)).toEqual([]);
  });
});

describe("patentPointCandidatesFromDisclosureRun", () => {
  it("prefers settled package candidates over in-flight stage results", () => {
    const run = {
      package: { candidates: [{ ...baseCandidate, id: "pkg" }] },
      stage_results: [
        { phase: "patent_points", payload: { candidates: [{ ...baseCandidate, id: "stage" }] } },
      ],
    } as unknown as DisclosureRun;
    expect(patentPointCandidatesFromDisclosureRun(run)[0].id).toBe("pkg");
  });

  it("falls back to stage results when no package candidates", () => {
    const run = {
      package: { candidates: [] },
      stage_results: [
        { phase: "patent_points", payload: { candidates: [{ ...baseCandidate, id: "stage" }] } },
      ],
    } as unknown as DisclosureRun;
    expect(patentPointCandidatesFromDisclosureRun(run)[0].id).toBe("stage");
  });
});

describe("evidenceStatusText", () => {
  it("maps every status to a zh-CN label", () => {
    expect(evidenceStatusText("verified")).toBe("已验证");
    expect(evidenceStatusText("needs_experiment")).toBe("需实验");
    expect(evidenceStatusText("feasible_unverified")).toBe("可行未验证");
    expect(evidenceStatusText("model_generated")).toBe("模型生成");
  });
});
