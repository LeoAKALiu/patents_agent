import { describe, expect, it } from "vitest";

import appSource from "./App.tsx?raw";
import guidedSource from "./GuidedPatentFlow.tsx?raw";

describe("Guided patent flow UI regressions", () => {
  it("does not render the external draft intake as a side entry in downstream guided steps", () => {
    expect(guidedSource).not.toContain("external-draft-side-entry");
    expect(guidedSource).not.toContain('displayedStepId !== "idea"');
  });

  it("surfaces patent point candidates from an in-progress disclosure stage result", () => {
    expect(guidedSource).toContain("function patentPointCandidatesFromStageResults");
    expect(guidedSource).toContain('result.phase !== "patent_points"');
    expect(guidedSource).toContain("activeRunCandidates.length");
    expect(guidedSource).toContain("候选发明点已返回");
  });

  it("refreshes disclosure runs after starting patent point extraction", () => {
    expect(appSource).toContain("function refreshDisclosureRunUntilSettled");
    expect(appSource).toContain("void refreshDisclosureRunUntilSettled(projectId, run.id)");
    expect(appSource).toContain("await loadPatentPoints(projectId)");
  });
});
