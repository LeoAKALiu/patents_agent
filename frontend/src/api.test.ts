import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildProjectCorpusVersion,
  cancelFormulaRun,
  cancelPostDraftReview,
  cancelProjectDeliberation,
  cancelProjectDisclosure,
  getProjectKnowledge,
  acceptAllCompletionPatches,
  applyOfficialCompileCleanup,
  getHealth,
  importPatent,
  retryFormulaRun,
  retryPostDraftReview,
  retryProjectDeliberation,
  retryProjectDisclosure,
  runProjectSearchPlan,
  startPostDraftReview,
  startKimiOfficialLanguagePolish,
  updateProjectKnowledgeCandidate,
  uploadCorpusJobFile,
  uploadProjectMaterial,
} from "./api";

describe("runtime control API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts to the cancel and retry endpoints for runtime-aware runs", async () => {
    const fetchMock = vi.fn(async () => (
      new Response(JSON.stringify({ id: "run-1", status: "queued" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    ));
    vi.stubGlobal("fetch", fetchMock);

    const calls = [
      {
        action: cancelProjectDisclosure,
        url: "/api/projects/project-1/disclosures/run-1/cancel",
      },
      {
        action: retryProjectDisclosure,
        url: "/api/projects/project-1/disclosures/run-1/retry",
      },
      {
        action: cancelProjectDeliberation,
        url: "/api/projects/project-1/deliberations/run-1/cancel",
      },
      {
        action: retryProjectDeliberation,
        url: "/api/projects/project-1/deliberations/run-1/retry",
      },
      {
        action: cancelFormulaRun,
        url: "/api/projects/project-1/formula-runs/run-1/cancel",
      },
      {
        action: retryFormulaRun,
        url: "/api/projects/project-1/formula-runs/run-1/retry",
      },
      {
        action: cancelPostDraftReview,
        url: "/api/projects/project-1/post-draft-reviews/run-1/cancel",
      },
      {
        action: retryPostDraftReview,
        url: "/api/projects/project-1/post-draft-reviews/run-1/retry",
      },
      {
        action: startKimiOfficialLanguagePolish,
        url: "/api/projects/project-1/official-compile-runs/run-1/kimi-language-polish",
      },
      {
        action: acceptAllCompletionPatches,
        url: "/api/projects/project-1/completion-runs/run-1/patches/accept-all",
      },
      {
        action: applyOfficialCompileCleanup,
        url: "/api/projects/project-1/official-compile-runs/run-1/apply-cleanup",
      },
    ];

    for (const { action } of calls) {
      await action("project-1", "run-1");
    }

    calls.forEach(({ url }, index) => {
      expect(fetchMock).toHaveBeenNthCalledWith(index + 1, url, { method: "POST" });
    });
  });

  it("includes the endpoint when fetch fails before a response", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Load failed");
    }));

    await expect(getHealth()).rejects.toThrow("GET /api/health 请求失败：Load failed");
  });

  it("maps browser file permission upload failures to user guidance", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    const file = new File(["private"], "round30-unreadable-material.md", { type: "text/markdown" });

    await expect(uploadProjectMaterial("project-1", file)).rejects.toThrow(
      "无法读取该文件，请检查文件权限或重新选择可读文件。",
    );
    await expect(uploadProjectMaterial("project-1", file)).rejects.not.toThrow("/api/projects/");
    await expect(uploadProjectMaterial("project-1", file)).rejects.not.toThrow("Failed to fetch");
  });

  it("maps project material validation failures without exposing the upload endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => (
      new Response(JSON.stringify({ detail: "文件为空或没有可解析文本。" }), {
        status: 422,
        statusText: "Unprocessable Entity",
        headers: { "Content-Type": "application/json" },
      })
    )));
    const file = new File([""], "empty.md", { type: "text/markdown" });

    await expect(uploadProjectMaterial("project-1", file)).rejects.toThrow("材料上传失败：文件为空或没有可解析文本。");
    await expect(uploadProjectMaterial("project-1", file)).rejects.not.toThrow("/api/projects/");
  });

  it("routes direct upload fetches through the Tauri backend base URL", async () => {
    const invokeMock = vi.fn(async (command: string) => {
      expect(command).toBe("get_backend_base_url");
      return "http://127.0.0.1:18234";
    });
    vi.stubGlobal("__TAURI__", { core: { invoke: invokeMock } });
    const fetchMock = vi.fn(async () => (
      new Response(JSON.stringify({ job: {}, document: {}, chunks_count: 1, file_count: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    ));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["patent"], "patent.md", { type: "text/markdown" });

    await uploadCorpusJobFile("job-1", file);
    await importPatent(file);
    await uploadProjectMaterial("project-1", file);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:18234/api/corpus/jobs/job-1/files",
      expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://127.0.0.1:18234/api/corpus/import",
      expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://127.0.0.1:18234/api/projects/project-1/materials",
      expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
    );
  });

  it("starts post-draft review with expert and participant provider seats", async () => {
    const fetchMock = vi.fn(async () => (
      new Response(JSON.stringify({ id: "review-1", status: "completed" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    ));
    vi.stubGlobal("fetch", fetchMock);

    await startPostDraftReview("project-1", ["codex", "deepseek", "kimicode"], ["mimo"]);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/post-draft-reviews",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          providers: ["codex", "deepseek", "kimicode"],
          participant_providers: ["mimo"],
        }),
      }),
    );
  });

  it("calls project knowledge endpoints", async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      requests.push({ url, init });
      if (url.endsWith("/knowledge/candidates/c-1")) {
        return new Response(JSON.stringify({ id: "c-1", user_decision: "include" }), { status: 200 });
      }
      return new Response(JSON.stringify({ state: { project_id: "p-1", status: "ready" } }), { status: 200 });
    }));

    await getProjectKnowledge("p-1");
    await runProjectSearchPlan("p-1", "plan-1");
    await updateProjectKnowledgeCandidate("p-1", "c-1", "include");
    await buildProjectCorpusVersion("p-1", "plan-1");

    expect(requests.map((request) => request.url)).toEqual([
      "/api/projects/p-1/knowledge",
      "/api/projects/p-1/knowledge/search-plans/plan-1/run",
      "/api/projects/p-1/knowledge/candidates/c-1",
      "/api/projects/p-1/knowledge/corpus-versions",
    ]);
    expect(requests[2].init?.method).toBe("PATCH");
    expect(requests[3].init?.body).toBe(JSON.stringify({ plan_id: "plan-1" }));
  });
});
