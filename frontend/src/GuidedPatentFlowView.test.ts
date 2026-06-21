import { describe, expect, it } from "vitest";

import appSource from "./App.tsx?raw";
import guidedSource from "./GuidedPatentFlow.tsx?raw";
// The patent-point selection logic lives in a dedicated pure module after
// the M4 extraction; the regression guard below pins its behaviour there.
import inventionSelectorsSource from "./flow/inventionSelectors.ts?raw";
// InventionPointConfirmation (panel-level candidate surfacing) was extracted
// to its own module in M4; the panel-consumption guard points there now.
import inventionPointSource from "./flow/panels/InventionPointConfirmation.tsx?raw";
// The disclosure-settling poll loop + patent-point loader were extracted to
// store/projectData in M3-B. The guard asserts the behaviour — the loop
// exists, reloads patent points, and App.tsx still wires it — wherever the
// code now lives, rather than pinning it to a literal location in App.tsx.
import projectDataSource from "./store/projectData.ts?raw";

describe("Guided patent flow UI regressions", () => {
  it("does not render the external draft intake as a side entry in downstream guided steps", () => {
    expect(guidedSource).not.toContain("external-draft-side-entry");
    expect(guidedSource).not.toContain('displayedStepId !== "idea"');
  });

  it("surfaces patent point candidates from an in-progress disclosure stage result", () => {
    // Selection logic (moved to ./flow/inventionSelectors in M4).
    expect(inventionSelectorsSource).toContain("function patentPointCandidatesFromStageResults");
    expect(inventionSelectorsSource).toContain('result.phase !== "patent_points"');
    // Panel-level consumption moved to ./flow/panels/InventionPointConfirmation (M4).
    expect(inventionPointSource).toContain("activeRunCandidates.length");
    expect(inventionPointSource).toContain("候选发明点已返回");
  });

  it("keeps invention helper actions as text buttons instead of icon-only controls", () => {
    expect(inventionPointSource).toContain("guided-panel-actions");
    expect(inventionPointSource).toContain("guided-panel-action");
    expect(inventionPointSource).not.toMatch(/size="icon"[^>]+onOpenExpertTool\("materials"\)/s);
    expect(inventionPointSource).not.toMatch(/size="icon"[^>]+onOpenExpertTool\("moat"\)/s);
  });

  it("refreshes disclosure runs after starting patent point extraction", () => {
    // Behaviour contract (location-agnostic after the M3-B extraction):
    //   • the poll loop lives in store/projectData
    //   • it reloads patent points each pass
    //   • App.tsx still invokes it after starting a disclosure
    expect(projectDataSource).toContain("refreshDisclosureRunUntilSettled");
    expect(projectDataSource).toContain("loadPatentPoints");
    expect(appSource).toContain("refreshDisclosureRunUntilSettled");
  });
});
