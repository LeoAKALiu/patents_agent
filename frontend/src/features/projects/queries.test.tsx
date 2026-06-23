import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createPatentAgentQueryClient } from "@/lib/queryClient";
import { useProjectsQuery } from "./queries";

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={createPatentAgentQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

describe("useProjectsQuery", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            projects: [
              {
                id: "project-1",
                name: "Demo Project",
                draft_text: "Draft",
                patent_type: "invention",
                package: null,
                created_at: "2026-06-23T00:00:00Z",
                updated_at: "2026-06-23T00:00:00Z",
                applicant: "",
                inventors: "",
                technical_field: "",
                background: "",
                pain_point: "",
                technical_solution: "",
                innovation: "",
                embodiments: "",
                beneficial_effects: "",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the project list from the backend response wrapper", async () => {
    const { result } = renderHook(() => useProjectsQuery(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0]?.id).toBe("project-1");
  });
});
