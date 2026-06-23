import createClient from "openapi-fetch";
import type { paths } from "@/generated/api/schema";

type TauriInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>;

declare global {
  interface Window {
    __TAURI__?: {
      core?: {
        invoke?: TauriInvoke;
      };
    };
  }
}

let backendBaseUrlPromise: Promise<string | null> | null = null;

async function resolveBackendBaseUrl(): Promise<string | null> {
  const invoke = typeof window !== "undefined" ? window.__TAURI__?.core?.invoke : undefined;
  if (!invoke) return null;
  if (!backendBaseUrlPromise) {
    backendBaseUrlPromise = invoke<string>("get_backend_base_url")
      .then((baseUrl) => baseUrl.replace(/\/+$/, ""))
      .catch(() => null);
  }
  return backendBaseUrlPromise;
}

/**
 * Returns the absolute origin openapi-fetch should resolve relative paths
 * against. In a real browser this is `window.location.origin`. In non-browser
 * environments (Vitest/jsdom) we fall back to a stable dummy origin so
 * `new Request("/api/health")` does not throw on relative URLs.
 */
function resolveOriginForOpenApi(): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  return "http://localhost";
}

function isApiPath(pathname: string): boolean {
  return pathname === "/api" || pathname.startsWith("/api/");
}

function resolveRequestUrl(raw: string, backendBaseUrl: string | null): string {
  if (!backendBaseUrl) return raw;
  const origin = resolveOriginForOpenApi();
  const url = new URL(raw, origin);
  if (!isApiPath(url.pathname)) return raw;
  return `${backendBaseUrl}${url.pathname}${url.search}`;
}

export const apiClient = createClient<paths>({
  baseUrl: resolveOriginForOpenApi(),
  fetch: async (input: Request | string, init?: RequestInit) => {
    const raw = typeof input === "string" ? input : input.url;
    const backendBaseUrl = await resolveBackendBaseUrl();
    const target = resolveRequestUrl(raw, backendBaseUrl);
    if (typeof input === "string") {
      return fetch(target, init);
    }
    const request = target === input.url ? input : new Request(target, input);
    return fetch(request, init);
  },
});
