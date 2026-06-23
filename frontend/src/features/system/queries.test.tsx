import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createPatentAgentQueryClient } from "@/lib/queryClient";
import { useHealthQuery } from "./queries";

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={createPatentAgentQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

describe("useHealthQuery", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ok: true,
            llm_configured: false,
            data_dir: "/tmp/data",
            model: "test-model",
            embedding_model: "test-embed",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads backend health through the typed client", async () => {
    const { result } = renderHook(() => useHealthQuery(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.ok).toBe(true);
    expect(result.current.data?.model).toBe("test-model");
  });
});
