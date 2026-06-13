/**
 * Desktop config IPC for the Electron main process (PR6, issue #20).
 *
 * The renderer never receives the raw API key. The preload bridge only exposes
 * a redacted view + update/clear/health methods. All requests are proxied to
 * the locally-supervised FastAPI backend over HTTP, which performs the actual
 * redaction and persistence on disk.
 */
import { ipcMain } from "electron";
import * as http from "http";
import { URL } from "url";

export interface DesktopConfigView {
  provider: string;
  base_url: string;
  model: string;
  api_key_present: boolean;
  api_key_fingerprint: string;
  updated_at: string;
  version: number;
  api_key_source: "env" | "desktop_config" | "none";
}

export interface DesktopConfigHealthResult {
  ok: boolean;
  model: string;
  api_key_source: "env" | "desktop_config" | "none";
  latency_ms: number;
  status_code: number;
  error: string;
}

export interface DesktopConfigClientOptions {
  baseUrl: string;
  timeoutMs?: number;
}

export interface DesktopConfigUpdatePayload {
  provider?: string;
  base_url?: string;
  model?: string;
  api_key?: string;
  clear_api_key?: boolean;
}

export class DesktopConfigError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "DesktopConfigError";
    this.status = status;
  }
}

const RAW_KEY_PATTERN = /sk-[A-Za-z0-9_-]{6,}/g;

function sanitiseError(err: unknown): string {
  if (err instanceof Error) {
    // Defence in depth: never let a raw key reach the renderer.
    return err.message.replace(RAW_KEY_PATTERN, "sk-…").slice(0, 512);
  }
  return String(err).slice(0, 512);
}

function requestJson<T>(
  baseUrl: string,
  method: "GET" | "PATCH" | "POST",
  pathname: string,
  body: DesktopConfigUpdatePayload | Record<string, never> | undefined,
  timeoutMs: number,
): Promise<T> {
  const url = new URL(pathname.replace(/^\/+/, ""), baseUrl.endsWith("/") ? baseUrl : baseUrl + "/");
  const data = body === undefined ? null : Buffer.from(JSON.stringify(body), "utf8");
  const headers: Record<string, string> = {
    "content-type": "application/json",
    accept: "application/json",
  };
  if (data) headers["content-length"] = String(data.length);

  return new Promise<T>((resolve, reject) => {
    const request = http.request(
      {
        method,
        hostname: url.hostname,
        port: url.port || 80,
        path: url.pathname + url.search,
        headers,
      },
      (response: http.IncomingMessage) => {
        const chunks: Buffer[] = [];
        response.on("data", (chunk: Buffer) => chunks.push(chunk));
        response.on("end", () => {
          const text = Buffer.concat(chunks).toString("utf8");
          const status = response.statusCode ?? 502;
          if (status >= 200 && status < 300) {
            if (!text) {
              resolve({} as T);
              return;
            }
            try {
              resolve(JSON.parse(text) as T);
            } catch (err) {
              reject(new DesktopConfigError(`invalid JSON from ${pathname}: ${sanitiseError(err)}`, 502));
            }
            return;
          }
          reject(new DesktopConfigError(`HTTP ${status} from ${pathname}: ${text.slice(0, 256)}`, status));
        });
      },
    );
    request.on("error", (err: Error) => reject(new DesktopConfigError(sanitiseError(err), 502)));
    request.setTimeout(timeoutMs, () => {
      request.destroy();
      reject(new DesktopConfigError(`request to ${pathname} timed out after ${timeoutMs}ms`, 504));
    });
    if (data) request.write(data);
    request.end();
  });
}

export class DesktopConfigClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(options: DesktopConfigClientOptions) {
    this.baseUrl = options.baseUrl;
    this.timeoutMs = options.timeoutMs ?? 8_000;
  }

  async get(): Promise<DesktopConfigView> {
    try {
      return await requestJson<DesktopConfigView>(
        this.baseUrl,
        "GET",
        "/api/desktop-config",
        undefined,
        this.timeoutMs,
      );
    } catch (err) {
      if (err instanceof DesktopConfigError) throw err;
      throw new DesktopConfigError(sanitiseError(err), 502);
    }
  }

  async update(payload: DesktopConfigUpdatePayload): Promise<DesktopConfigView> {
    try {
      return await requestJson<DesktopConfigView>(
        this.baseUrl,
        "PATCH",
        "/api/desktop-config",
        payload,
        this.timeoutMs,
      );
    } catch (err) {
      if (err instanceof DesktopConfigError) throw err;
      throw new DesktopConfigError(sanitiseError(err), 502);
    }
  }

  async health(): Promise<DesktopConfigHealthResult> {
    try {
      return await requestJson<DesktopConfigHealthResult>(
        this.baseUrl,
        "POST",
        "/api/desktop-config/health",
        {},
        this.timeoutMs,
      );
    } catch (err) {
      if (err instanceof DesktopConfigError) throw err;
      throw new DesktopConfigError(sanitiseError(err), 502);
    }
  }
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export function attachDesktopConfigIpc(client: DesktopConfigClient): void {
  ipcMain.handle("desktop:config:get", async () => client.get());
  ipcMain.handle("desktop:config:update", async (_event: unknown, payload: unknown) => {
    if (!payload || typeof payload !== "object") {
      throw new DesktopConfigError("config update payload must be an object", 400);
    }
    const update = payload as Record<string, unknown>;
    return client.update({
      provider: asString(update.provider),
      base_url: asString(update.base_url),
      model: asString(update.model),
      api_key: asString(update.api_key),
      clear_api_key: update.clear_api_key === true,
    });
  });
  ipcMain.handle("desktop:config:clear-key", async () =>
    client.update({ clear_api_key: true }),
  );
  ipcMain.handle("desktop:config:health", async () => client.health());
}
