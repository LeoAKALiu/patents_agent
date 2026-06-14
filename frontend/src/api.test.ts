import { afterEach, describe, expect, it, vi } from "vitest";

import {
  cancelFormulaRun,
  cancelPostDraftReview,
  cancelProjectDeliberation,
  cancelProjectDisclosure,
  retryFormulaRun,
  retryPostDraftReview,
  retryProjectDeliberation,
  retryProjectDisclosure,
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
});
