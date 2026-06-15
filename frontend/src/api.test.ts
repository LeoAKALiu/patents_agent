import { afterEach, describe, expect, it, vi } from "vitest";

import {
  cancelFormulaRun,
  cancelPostDraftReview,
  cancelProjectDeliberation,
  cancelProjectDisclosure,
  importPatent,
  retryFormulaRun,
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
