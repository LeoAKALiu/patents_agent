import { describe, expect, it } from "vitest";

import source from "./App.tsx?raw";

function extractFunctionBody(name: string, nextName: string): string {
  const start = source.indexOf(`async function ${name}`);
  const end = source.indexOf(`async function ${nextName}`, start + 1);
  expect(start).toBeGreaterThanOrEqual(0);
  expect(end).toBeGreaterThan(start);
  return source.slice(start, end);
}

describe("App refresh effect dependencies", () => {
  it("uses stable scalar keys instead of refreshed object identities", () => {
    expect(source).toContain("const selectedProjectIdForRefresh = selectedProject?.id ?? \"\"");
    expect(source).toContain("const latestOfficialCompileRunId = latestOfficialCompileRun?.id ?? \"\"");
    expect(source).toContain("const latestPostDraftReviewId = latestPostDraftReview?.id ?? \"\"");
    expect(source).toContain("const lastExportRefreshKey = lastExport");

    const refreshEffect = source.match(/useEffect\(\(\) => \{[\s\S]*?void refreshAll\(\);[\s\S]*?\}, \[([\s\S]*?)\]\);/);
    expect(refreshEffect?.[1]).toBeDefined();
    const dependencies = refreshEffect?.[1] ?? "";

    expect(dependencies).toContain("selectedProjectIdForRefresh");
    expect(dependencies).toContain("latestOfficialCompileRunId");
    expect(dependencies).toContain("latestPostDraftReviewId");
    expect(dependencies).toContain("lastExportRefreshKey");
    expect(dependencies).not.toContain("selectedProject,");
    expect(dependencies).not.toContain("latestOfficialCompileRun,");
    expect(dependencies).not.toContain("latestPostDraftReview,");
    expect(dependencies).not.toContain("lastExport,");
  });

  it("App.tsx contains no hard-coded hex colours (M5 visual-consistency guard)", () => {
    // Every colour must flow through a design token (var(--*)). Strip // line
    // comments first so palette references in prose don't trip the check.
    const code = source
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"))
      .join("\n");
    // Reject #rgb / #rrggbb / #rrggbbaa anywhere in code.
    expect(code).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });

  it("refreshes project knowledge after patent-point mutations reload the selected project", () => {
    expect(source).toMatch(
      /async function handleCreatePatentPoint[\s\S]*const stillSelected = await loadPatentPoints\(projectId\);[\s\S]*if \(!stillSelected\) return;[\s\S]*await loadProjectKnowledge\(projectId\);/,
    );
    expect(source).toMatch(
      /async function handleSelectPatentPoint[\s\S]*const stillSelected = await loadPatentPoints\(projectId\);[\s\S]*if \(!stillSelected\) return;[\s\S]*await loadProjectKnowledge\(projectId\);/,
    );
    expect(source).toMatch(
      /async function handleDeletePatentPoint[\s\S]*const stillSelected = await loadPatentPoints\(projectId\);[\s\S]*if \(!stillSelected\) return;[\s\S]*await loadProjectKnowledge\(projectId\);/,
    );
  });

  it("announces gated synthetic-only corpus builds without the ready toast", () => {
    expect(source).toContain('if (overview.state.quality_flags.includes("synthetic_evidence"))');
    expect(source).toContain("项目证据库建库完成：");
    expect(source).toContain("仍需补充检索");
  });

  it("refreshes stale draft and gate state after an embedded repair patch is applied", () => {
    const handler = source.match(/async function handleDraftRepairPatchApplied[\s\S]*?^  async function handleStartOfficialCompile/m);
    expect(handler?.[0]).toBeDefined();
    const body = handler?.[0] ?? "";

    expect(body).toContain("refreshProjectsPreservingSelection(projectId)");
    expect(body).toContain("setFilingReports([])");
    expect(body).toContain("setWorksheets([])");
    expect(body).toContain("setCompletionRuns([])");
    expect(body).toContain("await loadOfficialCompileRuns(projectId)");
    expect(body).toContain("await loadPostDraftReviews(projectId)");
    expect(body).toContain("await loadExportReadiness(projectId)");
    expect(body).not.toContain("updateProjectDraftPackage");
    expect(source).toContain("onDraftRepairPatchApplied: (issueId) => void handleDraftRepairPatchApplied(issueId)");
  });

  it("keeps the main knowledge overview loaded when CNIPA supplemental fetches fail", () => {
    const body = extractFunctionBody("loadProjectKnowledge(projectId: string): Promise<boolean>", "loadPatentPoints(projectId: string): Promise<boolean>");

    expect(body).toContain("const overview = await getProjectKnowledge(projectId);");
    expect(body).toContain("setProjectKnowledge(overview);");
    expect(body).toContain("const queryPack = await getProjectCnipaQueryPack(projectId);");
    expect(body).toContain("setCnipaQueryPack(queryPack);");
    expect(body).toContain("setCnipaQueryPack(null);");
    expect(body).toContain("if (!overview.latest_plan) {");
    expect(body).toContain("setProjectKnowledgeImportLedgers([]);");
    expect(body).toContain("const ledgers = await listProjectKnowledgeImportLedgers(projectId, overview.latest_plan.id);");
    expect(body).toContain("setProjectKnowledgeImportLedgers(ledgers);");
    expect(body).toContain("return true;");
    expect(body).toContain("setProjectKnowledge(null);");
    expect(body).toContain("return false;");
  });

  it("isolates CNIPA supplemental failures during plan generation so stale ledgers are cleared", () => {
    const body = extractFunctionBody("handleGenerateKnowledgePlan(): Promise<void>", "handleRunKnowledgeSearch(): Promise<void>");

    expect(body).toContain("setProjectKnowledge(overview);");
    expect(body).toContain("try {");
    expect(body).toContain("const queryPack = await getProjectCnipaQueryPack(projectId);");
    expect(body).toContain("setCnipaQueryPack(queryPack);");
    expect(body).toContain("if (overview.latest_plan) {");
    expect(body).toContain(
      "const ledgers = await listProjectKnowledgeImportLedgers(projectId, overview.latest_plan.id);",
    );
    expect(body).toContain("} else {");
    expect(body).toContain("setProjectKnowledgeImportLedgers([]);");
    expect(body).toContain("} catch {");
    expect(body).toContain("setCnipaQueryPack(null);");
    expect(body).toContain("setProjectKnowledgeImportLedgers([]);");
    expect(body).toContain('setMessage("已生成 Agent 检索计划。");');
  });
});
