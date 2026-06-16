import { describe, expect, it } from "vitest";

import source from "./App.tsx?raw";

describe("App refresh effect dependencies", () => {
  it("uses stable scalar keys instead of refreshed object identities", () => {
    expect(source).toContain("const selectedProjectIdForRefresh = selectedProject?.id ?? \"\"");
    expect(source).toContain("const latestOfficialCompileRunId = latestOfficialCompileRun?.id ?? \"\"");
    expect(source).toContain("const latestPostDraftReviewId = latestPostDraftReview?.id ?? \"\"");
    expect(source).toContain("const lastExportRefreshKey = lastExport");

    const refreshEffect = source.match(/useEffect\(\(\) => \{\n\s+void refreshAll\(\);\n\s+\}, \[([\s\S]*?)\]\);/);
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
});
