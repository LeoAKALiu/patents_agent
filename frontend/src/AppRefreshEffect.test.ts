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
});
