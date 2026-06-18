import { describe, expect, it } from "vitest";

import appSource from "./App.tsx?raw";
import domainSource from "./domain.ts?raw";
import guidedSource from "./GuidedPatentFlow.tsx?raw";
import exportViewSource from "./views/exportView.tsx?raw";
// The patent-point selection logic lives in a dedicated pure module after
// the M4 extraction; the regression guard below pins its behaviour there.
import inventionSelectorsSource from "./flow/inventionSelectors.ts?raw";
// InventionPointConfirmation (panel-level candidate surfacing) was extracted
// to its own module in M4; the panel-consumption guard points there now.
import inventionPointSource from "./flow/panels/InventionPointConfirmation.tsx?raw";
import postDraftReviewPanelSource from "./flow/panels/PostDraftReviewPanel.tsx?raw";
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

  it("refreshes disclosure runs after starting patent point extraction", () => {
    // Behaviour contract (location-agnostic after the M3-B extraction):
    //   • the poll loop lives in store/projectData
    //   • it reloads patent points each pass
    //   • App.tsx still invokes it after starting a disclosure
    expect(projectDataSource).toContain("refreshDisclosureRunUntilSettled");
    expect(projectDataSource).toContain("loadPatentPoints");
    expect(appSource).toContain("refreshDisclosureRunUntilSettled");
  });

  it("lets blocked post-draft review users inspect blocker guidance and edit the current draft", () => {
    expect(postDraftReviewPanelSource).toContain("阻断修复工作台");
    expect(postDraftReviewPanelSource).toContain("当前内部初稿");
    expect(postDraftReviewPanelSource).toContain("onSaveDraftPackage");
    expect(postDraftReviewPanelSource).toContain("guidanceFromReview");
    expect(postDraftReviewPanelSource).toContain("重新编译正式稿");
    expect(guidedSource).toContain("onSaveDraftPackage={props.onSaveDraftPackage}");
    expect(appSource).toContain("handleSaveDraftPackage");
    expect(appSource).toContain("updateProjectPackage");
  });

  it("shows explicit official export gate diagnostics instead of a single waiting state", () => {
    expect(domainSource).toContain("exportGateDiagnostics");
    expect(exportViewSource).toContain("源稿版本一致");
    expect(exportViewSource).toContain("正式稿已编译");
    expect(exportViewSource).toContain("成稿会审通过");
    expect(exportViewSource).toContain("去重新编译");
    expect(exportViewSource).toContain("去成稿会审");
  });
});
