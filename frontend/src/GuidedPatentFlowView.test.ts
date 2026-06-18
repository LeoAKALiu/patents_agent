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
});
