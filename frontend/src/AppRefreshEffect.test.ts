import { describe, expect, it } from "vitest";

import source from "./App.tsx?raw";

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
    expect(source).toMatch(
      /async function loadProjectKnowledge\(projectId: string\): Promise<boolean> \{[\s\S]*const overview = await getProjectKnowledge\(projectId\);[\s\S]*setProjectKnowledge\(overview\);[\s\S]*try \{[\s\S]*const queryPack = await getProjectCnipaQueryPack\(projectId\);[\s\S]*setCnipaQueryPack\(queryPack\);[\s\S]*\} catch \{[\s\S]*setCnipaQueryPack\(null\);[\s\S]*\}[\s\S]*if \(!overview\.latest_plan\) \{[\s\S]*setProjectKnowledgeImportLedgers\(\[\]\);[\s\S]*return true;[\s\S]*\}[\s\S]*try \{[\s\S]*const ledgers = await listProjectKnowledgeImportLedgers\(projectId, overview\.latest_plan\.id\);[\s\S]*setProjectKnowledgeImportLedgers\(ledgers\);[\s\S]*\} catch \{[\s\S]*setProjectKnowledgeImportLedgers\(\[\]\);[\s\S]*\}[\s\S]*return true;[\s\S]*catch \{[\s\S]*setProjectKnowledge\(null\);[\s\S]*setCnipaQueryPack\(null\);[\s\S]*setProjectKnowledgeImportLedgers\(\[\]\);[\s\S]*return false;[\s\S]*\}/,
    );
  });
});
