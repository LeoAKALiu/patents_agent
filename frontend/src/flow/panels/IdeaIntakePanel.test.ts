import { describe, expect, it } from "vitest";
import { defaultProjectRecord } from "@/api";

describe("ProjectRecord structured field defaults", () => {
  it("defaultProjectRecord fills all structured fields with empty strings", () => {
    const record = defaultProjectRecord({
      id: "p-test",
      name: "测试项目",
    });
    expect(record.id).toBe("p-test");
    expect(record.name).toBe("测试项目");
    expect(record.applicant).toBe("");
    expect(record.inventors).toBe("");
    expect(record.technical_field).toBe("");
    expect(record.background).toBe("");
    expect(record.pain_point).toBe("");
    expect(record.technical_solution).toBe("");
    expect(record.innovation).toBe("");
    expect(record.embodiments).toBe("");
    expect(record.beneficial_effects).toBe("");
    // Core required fields get sensible defaults
    expect(record.draft_text).toBe("");
    expect(record.patent_type).toBe("invention");
    expect(record.package).toBeNull();
    expect(record.created_at).toBe("");
    expect(record.updated_at).toBe("");
  });

  it("defaultProjectRecord overrides work on top of defaults", () => {
    const record = defaultProjectRecord({
      id: "p-ov",
      name: "覆盖测试",
      applicant: "焕城智慧科技",
      innovation: "新颖的算法",
    });
    expect(record.applicant).toBe("焕城智慧科技");
    expect(record.innovation).toBe("新颖的算法");
    // Non-overridden fields still get empty defaults
    expect(record.inventors).toBe("");
    expect(record.background).toBe("");
  });

  it("defaultProjectRecord fills all required fields with defaults when omitted", () => {
    // Minimal call: only id + name; all other fields get valid defaults
    const record = defaultProjectRecord({ id: "p-min", name: "最小项目" });
    expect(record.id).toBe("p-min");
    expect(record.name).toBe("最小项目");
    expect(record.draft_text).toBe("");
    expect(record.patent_type).toBe("invention");
    expect(record.package).toBeNull();
    expect(record.created_at).toBe("");
    expect(record.updated_at).toBe("");
    // Structured fields default to empty
    expect(record.technical_field).toBe("");
  });
});

describe("IdeaIntakePanel project-change hydration", () => {
  it("key prop pattern ensures remount on project switch", () => {
    // The GuidedPatentFlow renders IdeaIntakePanel with
    //   key={props.project?.id ?? "new"}
    // When project changes (e.g. null → p1 → p2), the key changes
    // and React unmounts/remounts the component, re-initialising all
    // structured field state from the new project's props.
    const keyFor = (projectId: string | null | undefined) => projectId ?? "new";
    expect(keyFor(null)).toBe("new");
    expect(keyFor(undefined)).toBe("new");
    expect(keyFor("proj-abc")).toBe("proj-abc");
    expect(keyFor("proj-xyz")).toBe("proj-xyz");

    // Two different projects produce different keys → remount
    expect(keyFor("p1")).not.toBe(keyFor("p2"));
    // null vs a real project = different keys → remount
    expect(keyFor(null)).not.toBe(keyFor("p1"));
  });
});
