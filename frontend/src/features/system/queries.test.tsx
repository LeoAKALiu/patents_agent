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
    Reflect.deleteProperty(window, "__TAURI__");
  });

  it("loads backend health through the typed client", async () => {
    const { result } = renderHook(() => useHealthQuery(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.ok).toBe(true);
    expect(result.current.data?.model).toBe("test-model");
  });

  it("routes Tauri requests through the backend base URL", async () => {
    const invoke = vi.fn(async () => "http://127.0.0.1:8123/");
    Object.defineProperty(window, "__TAURI__", {
      configurable: true,
      value: { core: { invoke } },
    });
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
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
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useHealthQuery(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const calls = fetchMock.mock.calls as Array<[RequestInfo | URL, RequestInit?]>;
    const request = calls[0]?.[0];
    expect(request).toBeDefined();
    const requestedUrl = request instanceof Request ? request.url : String(request);
    expect(requestedUrl).toBe("http://127.0.0.1:8123/api/health");
    expect(invoke).toHaveBeenCalledWith("get_backend_base_url");
  });
});
