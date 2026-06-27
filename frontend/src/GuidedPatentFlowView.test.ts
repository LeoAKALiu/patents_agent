import { describe, expect, it } from "vitest";

import appSource from "./App.tsx?raw";
import guidedSource from "./GuidedPatentFlow.tsx?raw";
import buttonSource from "./components/ui/button.tsx?raw";
// The patent-point selection logic lives in a dedicated pure module after
// the M4 extraction; the regression guard below pins its behaviour there.
import inventionSelectorsSource from "./flow/inventionSelectors.ts?raw";
import deliberationSource from "./flow/panels/DeliberationPanel.tsx?raw";
// InventionPointConfirmation (panel-level candidate surfacing) was extracted
// to its own module in M4; the panel-consumption guard points there now.
import inventionPointSource from "./flow/panels/InventionPointConfirmation.tsx?raw";
import runtimeWidgetsSource from "./flow/runtimeWidgets.tsx?raw";
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
    expect(inventionPointSource).toContain("button-row");
    expect(inventionPointSource).toContain("max-w-full whitespace-normal");
    expect(inventionPointSource).not.toMatch(/size="icon"[^>]+onOpenExpertTool\("materials"\)/s);
    expect(inventionPointSource).not.toMatch(/size="icon"[^>]+onOpenExpertTool\("moat"\)/s);
  });

  it("keeps guided text actions out of icon-sized buttons", () => {
    expect(inventionPointSource).toContain("max-w-full justify-self-start whitespace-normal");
    expect(inventionPointSource).not.toMatch(/size="icon"[^>]+onSelectPatentPoint/s);
    expect(deliberationSource).toContain("guided-panel-action");
    expect(deliberationSource).not.toMatch(/size="icon"[^>]+onOpenExpertTool\("deliberate"\)/s);
    expect(runtimeWidgetsSource).toContain("guided-runtime-action");
    expect(runtimeWidgetsSource).not.toMatch(/size="icon"[^>]+onCancel/s);
    expect(runtimeWidgetsSource).not.toMatch(/size="icon"[^>]+onRetry/s);
  });

  it("shows deliberation run history and logs in the guided panel", () => {
    expect(deliberationSource).toContain("DeliberationRunHistory");
    expect(deliberationSource).toContain("会审记录与日志");
    expect(deliberationSource).toContain("run.logs.slice");
    expect(deliberationSource).toContain("run.events.slice");
    expect(deliberationSource).toContain("run.failures.slice");
    expect(deliberationSource).not.toContain("已有会审记录，但尚无已完成的策略结果");
  });

  it("allows shared buttons to wrap inside constrained cards", () => {
    expect(buttonSource).toContain("min-w-0");
    expect(buttonSource).toContain("max-w-full");
    expect(buttonSource).toContain("whitespace-normal");
    expect(buttonSource).not.toContain("gap-2 whitespace-nowrap");
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

  it("guides external deep research reports into the invention point step", () => {
    expect(guidedSource).toContain("project={props.project}");
    expect(inventionPointSource).toContain("外部 Deep Research 辅助");
    expect(inventionPointSource).toContain("复制 Deep Research 提示词");
    expect(inventionPointSource).toContain("buildExternalDeepResearchPrompt");
    expect(inventionPointSource).toContain("最接近现有技术");
    expect(inventionPointSource).toContain("handleMaterialButtonClick");
    expect(inventionPointSource).toContain("requestSubmit");
    expect(inventionPointSource).toContain("multiple");
    expect(inventionPointSource).toContain("选择并上传多份报告/补充材料");
    expect(inventionPointSource).not.toContain("<MaterialSummary materials={materials} />");
    expect(appSource).toContain("Array.from(input.files ?? [])");
    expect(appSource).toContain("uploadedMaterials.length");
  });

  it("keeps text action buttons out of icon-only sizing", () => {
    const textButtonSources = [
      inventionPointSource,
      deliberationSource,
      runtimeWidgetsSource,
    ].join("\n");

    expect(textButtonSources).not.toMatch(/size="icon"[^>]*>\s*(?:<[^>]+>\s*)?查看/);
    expect(textButtonSources).not.toMatch(/size="icon"[^>]*>\s*(?:<[^>]+>\s*)?<span>取消运行<\/span>/);
    expect(textButtonSources).not.toMatch(/size="icon"[^>]*>\s*(?:<[^>]+>\s*)?选为主线/);
  });
});
