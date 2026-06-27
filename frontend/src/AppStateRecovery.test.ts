import { describe, expect, it, vi } from "vitest";

import {
  installAppHistoryGuard,
  sanitizePersistedAppState,
  resolveRecoveredProjectSelection,
  summarizeMaterialUploadOutcome,
  type PersistedAppState,
} from "./App";
import type { ProjectMaterial, ProjectRecord } from "./api";

const project = (id: string): ProjectRecord => ({
  id,
  name: `Project ${id}`,
  draft_text: "idea",
  patent_type: "invention",
  package: null,
  created_at: "2026-06-27T00:00:00Z",
  updated_at: "2026-06-27T00:00:00Z",
  applicant: "",
  inventors: "",
  technical_field: "",
  background: "",
  pain_point: "",
  technical_solution: "",
  innovation: "",
  embodiments: "",
  beneficial_effects: "",
});

const material = (fileName: string, status: ProjectMaterial["status"] = "processed"): ProjectMaterial => ({
  id: fileName,
  project_id: "p-1",
  file_name: fileName,
  path: `data/project-materials/p-1/${fileName}`,
  file_type: "md",
  text: status === "processed" ? "有效材料" : "",
  status,
  warnings: status === "processed" ? [] : ["文件为空或没有可解析文本。"],
  metadata: {},
});

describe("app state recovery", () => {
  it("restores selected project and guided context when the project still exists", () => {
    const persisted: PersistedAppState = {
      selectedProjectId: "p-2",
      activeSection: "generate",
      activeExpertTool: "materials",
      startChoice: "external",
      disclosureResearchMode: "free_deep_research",
    };

    expect(sanitizePersistedAppState(persisted)).toEqual(persisted);
    expect(resolveRecoveredProjectSelection([project("p-1"), project("p-2")], "p-2")).toEqual({
      selectedProjectId: "p-2",
      clearedMissingProject: false,
    });
  });

  it("clears stale selected project instead of silently selecting another project", () => {
    expect(resolveRecoveredProjectSelection([project("p-1")], "missing-project")).toEqual({
      selectedProjectId: "",
      clearedMissingProject: true,
    });
  });

  it("drops invalid persisted navigation values so browser history cannot restore a blank app body", () => {
    expect(
      sanitizePersistedAppState({
        selectedProjectId: "p-1",
        activeSection: "about:blank",
        activeExpertTool: "missing-tool",
        startChoice: "bad-choice",
        disclosureResearchMode: "bad-mode",
      }),
    ).toEqual({
      selectedProjectId: "p-1",
      activeSection: "generate",
      activeExpertTool: "build",
      startChoice: null,
      disclosureResearchMode: "standard",
    });
  });

  it("marks same-document browser history entries so Back stays inside the app shell", () => {
    const recover = vi.fn();
    const cleanup = installAppHistoryGuard(window, recover);

    expect(window.history.state?.__patentAgentApp).toBe(true);
    window.dispatchEvent(new PopStateEvent("popstate", { state: null }));
    expect(window.history.state?.__patentAgentApp).toBe(true);
    expect(recover).toHaveBeenCalledTimes(1);

    window.dispatchEvent(new PageTransitionEvent("pageshow"));
    expect(recover).toHaveBeenCalledTimes(2);

    cleanup();
  });

  it("summarizes mixed material upload results without hiding successful files", () => {
    const outcome = summarizeMaterialUploadOutcome(
      3,
      [material("valid.md"), material("empty.md", "failed")],
      [{ fileName: "bad.xyz", error: new Error("材料上传失败：不支持的文件类型。") }],
    );

    expect(outcome.level).toBe("message");
    expect(outcome.text).toContain("3 份材料");
    expect(outcome.text).toContain("1 份可用");
    expect(outcome.text).toContain("2 份失败");
    expect(outcome.text).toContain("empty.md");
    expect(outcome.text).toContain("bad.xyz");
  });

  it("reports all rejected material uploads as an error summary", () => {
    const outcome = summarizeMaterialUploadOutcome(
      2,
      [],
      [
        { fileName: "bad-1.xyz", error: new Error("材料上传失败：不支持的文件类型。") },
        { fileName: "bad-2.md", error: new Error("材料上传失败：文件为空或没有可解析文本。") },
      ],
    );

    expect(outcome.level).toBe("error");
    expect(outcome.text).toContain("2 份材料均上传失败");
    expect(outcome.text).toContain("bad-1.xyz");
    expect(outcome.text).toContain("bad-2.md");
  });
});
