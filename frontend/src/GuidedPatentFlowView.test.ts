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
// PR-11B: generate-run polling guards.
import draftGenPanelSource from "./flow/panels/DraftGenerationPanel.tsx?raw";
import runtimeWidgetsSource from "./flow/runtimeWidgets.tsx?raw";
import apiSource from "./api.ts?raw";

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

  it("renders llm-blocked recovery card with four visible recovery actions", () => {
    // The recovery card must appear when llmBlocked is true (needsGeneration && !llmConfigured).
    expect(inventionPointSource).toContain("const llmBlocked = needsGeneration && !llmConfigured");
    // The card container.
    expect(inventionPointSource).toContain('data-testid="llm-blocked-recovery"');
    // Four action buttons, each with a predictable testid.
    expect(inventionPointSource).toContain('data-testid="llm-recovery-goto-settings"');
    expect(inventionPointSource).toContain('data-testid="llm-recovery-manual-intake"');
    expect(inventionPointSource).toContain('data-testid="llm-recovery-sample-draft"');
    expect(inventionPointSource).toContain('data-testid="llm-recovery-retry-check"');
    // Each button has a visible label.
    expect(inventionPointSource).toContain("<span>去设置</span>");
    expect(inventionPointSource).toContain("<span>手动录入</span>");
    expect(inventionPointSource).toContain("<span>使用示例草稿</span>");
    expect(inventionPointSource).toContain("<span>重试检测</span>");
    // GuidedPatentFlow wires the props through.
    expect(guidedSource).toContain("llmConfigured={props.llmConfigured}");
    expect(guidedSource).toContain("onNavigateToSettings={props.onNavigateToSettings}");
    expect(guidedSource).toContain("onRetryHealthCheck={props.onRetryHealthCheck}");
    expect(guidedSource).toContain("onManualIntake={props.onManualIntake}");
    expect(guidedSource).toContain("onSampleDraft={props.onSampleDraft}");
  });

  it("App gates disclosure start on llm_configured", () => {
    // App reads health.llm_configured to decide whether to block disclosure.
    expect(appSource).toContain("llmConfigured={health?.llm_configured ?? false}");
    expect(appSource).toContain('if (!health?.llm_configured)');
    expect(appSource).toContain("LLM 未配置");
    // Retry health check wired.
    expect(appSource).toContain("onRetryHealthCheck={() => void (async () => {");
    expect(appSource).toContain("const h = await getHealth();");
    expect(appSource).toContain("setHealth(h);");
  });

  // PR-11B: generate-run polling — verify the frontend wiring exists.
  it("exposes generate-run Create/List/Get/Cancel/Retry in api.ts", () => {
    expect(apiSource).toContain("function createGenerateRun");
    expect(apiSource).toContain("function getGenerateRun");
    expect(apiSource).toContain("function listGenerateRuns");
    expect(apiSource).toContain("function cancelGenerateRun");
    expect(apiSource).toContain("function retryGenerateRun");
    expect(apiSource).toContain("interface GenerateRun");
    expect(apiSource).toContain("interface GenerateRunCreate");
  });

  it("wires generate-run polling into the draft generation handler", () => {
    // App.tsx handler uses createGenerateRun + polling loop.
    expect(appSource).toContain("createGenerateRun(");
    expect(appSource).toContain("getGenerateRun(");
    // Legacy fallback should remain for backends without the new endpoint.
    expect(appSource).toContain("generateProject(");
    // DraftGenerationPanel shows busy state label during generation.
    expect(draftGenPanelSource).toContain('busy === "generate"');
  });

  it("passes generateRuns + cancel/retry handlers through GuidedPatentFlowView", () => {
    expect(appSource).toContain("generateRuns={generateRuns}");
    expect(appSource).toContain("onCancelGenerateRun=");
    expect(appSource).toContain("onRetryGenerateRun=");
    expect(guidedSource).toContain("generateRuns: GenerateRun[]");
    expect(guidedSource).toContain("onCancelGenerateRun: (runId: string) => void");
    expect(guidedSource).toContain("onRetryGenerateRun: (runId: string) => void");
  });

  it("surfaces generate-run status + cancel/retry in DraftGenerationPanel", () => {
    // Panel shows runtime console and actions for generate runs.
    expect(draftGenPanelSource).toContain("GuidedRuntimeConsole");
    expect(draftGenPanelSource).toContain("GuidedRuntimeActions");
    expect(draftGenPanelSource).toContain("GuidedRuntimeFailures");
    expect(draftGenPanelSource).toContain("guidedActiveRun(generateRuns)");
    expect(draftGenPanelSource).toContain("onCancelGenerateRun");
    expect(draftGenPanelSource).toContain("onRetryGenerateRun");
    // Button shows "运行中..." when active run exists.
    expect(draftGenPanelSource).toContain('"运行中..."');
  });
});
