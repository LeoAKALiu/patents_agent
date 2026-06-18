import { afterEach, describe, expect, it, vi } from "vitest";

import {
  cancelFormulaRun,
  cancelGenerateRun,
  cancelPostDraftReview,
  cancelProjectDeliberation,
  cancelProjectDisclosure,
  createGenerateRun,
  getGenerateRun,
  getHealth,
  importPatent,
  listGenerateRuns,
  retryFormulaRun,
  retryGenerateRun,
  retryPostDraftReview,
  retryProjectDeliberation,
  retryProjectDisclosure,
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
});

describe("generate run API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const generateRunResp = (id: string, status: string) => ({
    id,
    project_id: "project-1",
    status,
    providers: ["deepseek"],
    failures: [],
    failure_details: [],
    events: [],
    created_at: "2026-06-18T12:00:00Z",
    updated_at: "2026-06-18T12:00:00Z",
  });

  it("POSTs create and returns a queued run", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (typeof url === "string" && url.includes("/generate-runs") && init?.method === "POST") {
        return new Response(JSON.stringify(generateRunResp("gr-1", "queued")), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response("not found", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const run = await createGenerateRun("project-1", "d-1", "f-1");
    expect(run.id).toBe("gr-1");
    expect(run.status).toBe("queued");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/projects/project-1/generate-runs"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("GETs a single generate run by id", async () => {
    const fetchMock = vi.fn(async () => (
      new Response(JSON.stringify(generateRunResp("gr-2", "running")), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    ));
    vi.stubGlobal("fetch", fetchMock);

    const run = await getGenerateRun("project-1", "gr-2");
    expect(run.status).toBe("running");
    // GET requests pass no init options; fetch receives undefined.
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/projects/project-1/generate-runs/gr-2"),
      undefined,
    );
  });

  it("lists generate runs", async () => {
    const runs = [generateRunResp("gr-1", "completed"), generateRunResp("gr-2", "queued")];
    const fetchMock = vi.fn(async () => (
      new Response(JSON.stringify({ runs }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await listGenerateRuns("project-1");
    expect(result).toHaveLength(2);
    expect(result[0].status).toBe("completed");
  });

  it("POSTs cancel for a running generate run", async () => {
    const fetchMock = vi.fn(async () => (
      new Response(JSON.stringify(generateRunResp("gr-3", "failed")), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    ));
    vi.stubGlobal("fetch", fetchMock);

    const run = await cancelGenerateRun("project-1", "gr-3");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/projects/project-1/generate-runs/gr-3/cancel"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(run.status).toBe("failed");
  });

  it("POSTs retry for a failed generate run", async () => {
    const fetchMock = vi.fn(async () => (
      new Response(JSON.stringify(generateRunResp("gr-4", "queued")), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    ));
    vi.stubGlobal("fetch", fetchMock);

    const run = await retryGenerateRun("project-1", "gr-4");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/projects/project-1/generate-runs/gr-4/retry"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(run.status).toBe("queued");
  });
});
