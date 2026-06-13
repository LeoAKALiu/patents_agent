/**
 * Startup diagnostics for the Electron main process (PR6, issue #38).
 *
 * The desktop MVP must surface boot-time failures in a way the user (and the
 * release smoke) can read. The previous flow either swallowed renderer asset
 * failures into a blank white page, or printed uvicorn output to stdout where
 * a packaged user would never see it. This module gives the main process a
 * tiny, append-only structured log it can:
 *
 *   - write one JSON line per stage to stdout (greppable from CI),
 *   - render as a human-readable report behind a "Help → Diagnostic info"
 *     menu item, and
 *   - surface to the renderer via `desktop:startup-diagnostics:get` so a
 *     future "Copy diagnostics" button can paste it into a bug report.
 *
 * The module deliberately does not touch `app.getPath` or any user data — it
 * is read-only over the boot context we already collected.
 */
import { app, ipcMain } from "electron";
import { existsSync } from "fs";

export type StartupLevel = "info" | "warn" | "error";

export interface StartupStage {
  stage: string;
  ts: number;
  level: StartupLevel;
  data?: Record<string, unknown>;
}

export interface StartupPython {
  executable: string;
  version?: string;
}

export interface StartupBackend {
  command: string;
  port: number;
  baseUrl: string;
  healthUrl: string;
  healthOk: boolean;
  durationMs: number;
  pid?: number;
}

export interface StartupRenderer {
  indexPath: string;
  indexExists: boolean;
  loadOk: boolean;
  loadDurationMs: number;
  failedSubresources: Array<{ code: number; description: string; url: string }>;
  crashed?: { reason: string; exitCode: number };
}

export interface StartupReport {
  schema: 1;
  app: { name: string; version: string };
  runtime: { electron: string; node: string; chrome: string };
  platform: NodeJS.Platform;
  argv: string[];
  env: {
    isDev: boolean;
    isSmoke: boolean;
    isPackaged: boolean;
  };
  startedAt: string;
  uptimeMs: number;
  stages: StartupStage[];
  python?: StartupPython;
  backend?: StartupBackend;
  renderer?: StartupRenderer;
  errors: string[];
}

export interface StartupDiagnosticsOptions {
  /** IPC channel the renderer uses to fetch the report. */
  ipcChannel?: string;
  /** Override the boot timestamp (mostly for tests). */
  now?: () => Date;
  /** Override monotonic clock (mostly for tests). */
  monotonicMs?: () => number;
  /** Console to use for the per-stage JSON log line. */
  logger?: Pick<Console, "log" | "warn" | "error">;
}

const DEFAULT_IPC_CHANNEL = "desktop:startup-diagnostics:get";
const MAX_CAPTURED_ERROR_CHARS = 4_000;

function truncate(value: string, max: number): string {
  if (value.length <= max) return value;
  return value.slice(value.length - max);
}

function safeStringify(value: unknown, max = 2_000): string {
  try {
    const text = JSON.stringify(value);
    if (text === undefined) return "<undefined>";
    return truncate(text, max);
  } catch (_err) {
    return "<unserialisable>";
  }
}

function errToString(err: unknown): string {
  if (err instanceof Error) {
    return err.stack ?? err.message;
  }
  return String(err);
}

export class StartupDiagnostics {
  private readonly stages: StartupStage[] = [];
  private readonly startWallClock: Date;
  private readonly startMonotonic: number;
  private readonly monotonicMs: () => number;
  private readonly now: () => Date;
  private readonly logger: Pick<Console, "log" | "warn" | "error">;
  private readonly errors: string[] = [];
  private readonly ipcChannel: string;
  private python?: StartupPython;
  private backend?: StartupBackend;
  private renderer?: StartupRenderer;
  private ipcAttached = false;

  constructor(options: StartupDiagnosticsOptions = {}) {
    this.startWallClock = options.now ? options.now() : new Date();
    this.startMonotonic = options.monotonicMs ? options.monotonicMs() : Date.now();
    this.now = options.now ?? ((): Date => new Date());
    this.monotonicMs = options.monotonicMs ?? ((): number => Date.now());
    this.logger = options.logger ?? console;
    this.ipcChannel = options.ipcChannel ?? DEFAULT_IPC_CHANNEL;
  }

  /**
   * Record a startup stage. Each call appends a structured entry and emits a
   * single JSON line on stdout (the same channel CI / a desktop log collector
   * already greps).
   */
  record(
    stage: string,
    data?: Record<string, unknown>,
    level: StartupLevel = "info",
  ): void {
    const entry: StartupStage = {
      stage,
      ts: this.monotonicMs() - this.startMonotonic,
      level,
      data: data ? redact(data) : undefined,
    };
    this.stages.push(entry);
    const line = `[startup] ${safeStringify(entry)}`;
    if (level === "error") this.logger.error(line);
    else if (level === "warn") this.logger.warn(line);
    else this.logger.log(line);
  }

  /** Convenience wrapper — record(stage) with level=error and the message. */
  error(stage: string, err: unknown, data?: Record<string, unknown>): void {
    const text = errToString(err);
    this.errors.push(truncate(`${stage}: ${text}`, MAX_CAPTURED_ERROR_CHARS));
    this.record(
      stage,
      { ...(data ?? {}), error: truncate(text, 2_000) },
      "error",
    );
  }

  setPython(python: StartupPython): void {
    this.python = python;
    this.record("python.resolved", {
      executable: python.executable,
      version: python.version,
    });
  }

  setBackend(backend: StartupBackend): void {
    this.backend = backend;
    this.record("backend.healthy", {
      command: backend.command,
      port: backend.port,
      baseUrl: backend.baseUrl,
      healthUrl: backend.healthUrl,
      healthOk: backend.healthOk,
      durationMs: backend.durationMs,
      pid: backend.pid,
    });
  }

  setRenderer(renderer: StartupRenderer): void {
    this.renderer = renderer;
    this.record("renderer.load", {
      indexPath: renderer.indexPath,
      indexExists: renderer.indexExists,
      loadOk: renderer.loadOk,
      loadDurationMs: renderer.loadDurationMs,
      failedSubresourceCount: renderer.failedSubresources.length,
      crashed: renderer.crashed,
    }, renderer.loadOk ? "info" : "error");
  }

  /**
   * Read the renderer asset check from disk. We do this once at boot so the
   * help-menu report can tell the user exactly what build artefact is missing.
   */
  setRendererIndex(indexPath: string): void {
    const exists = existsSync(indexPath);
    this.renderer = {
      ...(this.renderer ?? {
        indexPath,
        indexExists: exists,
        loadOk: false,
        loadDurationMs: 0,
        failedSubresources: [],
      }),
      indexPath,
      indexExists: exists,
    };
    this.record("renderer.index_check", {
      indexPath,
      indexExists: exists,
    }, exists ? "info" : "error");
  }

  /**
   * Register the IPC handler that returns the report to the renderer. Safe to
   * call multiple times — repeated calls are no-ops. We avoid registering the
   * handler in environments that do not have an IPC bus (e.g. plain Node tests
   * that import this module without booting Electron).
   */
  attachIpc(channel: string = this.ipcChannel): void {
    if (this.ipcAttached) return;
    this.ipcAttached = true;
    this.ipcChannelRef = channel;
    try {
      if (typeof ipcMain?.handle === "function") {
        ipcMain.handle(channel, () => this.getReport());
        this.record("ipc.registered", { channel });
      } else {
        this.record("ipc.skipped", {
          channel,
          reason: "ipcMain.handle is not available",
        });
      }
    } catch (err) {
      this.record("ipc.register_failed", {
        channel,
        error: err instanceof Error ? err.message : String(err),
      }, "error");
    }
  }

  private ipcChannelRef: string = DEFAULT_IPC_CHANNEL;
  get ipcChannelName(): string {
    return this.ipcChannelRef;
  }

  getReport(): StartupReport {
    return {
      schema: 1,
      app: {
        name: (() => {
          try {
            return app.getName();
          } catch (_err) {
            return "PatentAgent";
          }
        })(),
        version: (() => {
          try {
            return app.getVersion();
          } catch (_err) {
            return "unknown";
          }
        })(),
      },
      runtime: {
        electron: process.versions.electron ?? "unknown",
        node: process.versions.node ?? "unknown",
        chrome: process.versions.chrome ?? "unknown",
      },
      platform: process.platform,
      argv: process.argv,
      env: {
        isDev:
          process.env.PATENTAGENT_ELECTRON_DEV === "1" ||
          (!isAppPackagedSafe() &&
            !process.argv.includes("--smoke") &&
            process.env.PATENTAGENT_DESKTOP_PROD !== "1"),
        isSmoke: process.argv.includes("--smoke"),
        isPackaged: isAppPackagedSafe(),
      },
      startedAt: this.startWallClock.toISOString(),
      uptimeMs: this.monotonicMs() - this.startMonotonic,
      stages: this.stages.slice(),
      python: this.python,
      backend: this.backend,
      renderer: this.renderer,
      errors: this.errors.slice(),
    };
  }

  /** Render the report as a plain-text block suitable for showMessageBox. */
  toText(): string {
    const report = this.getReport();
    const lines: string[] = [];
    lines.push(`PatentAgent startup diagnostics`);
    lines.push(
      `  app:        ${report.app.name} v${report.app.version}`,
    );
    lines.push(
      `  platform:   ${report.platform} (electron ${report.runtime.electron}, node ${report.runtime.node}, chrome ${report.runtime.chrome})`,
    );
    lines.push(
      `  packaged:   ${report.env.isPackaged}  dev: ${report.env.isDev}  smoke: ${report.env.isSmoke}`,
    );
    lines.push(`  started:    ${report.startedAt}  (uptime ${report.uptimeMs}ms)`);
    if (report.python) {
      lines.push(
        `  python:     ${report.python.executable}${
          report.python.version ? ` (${report.python.version})` : ""
        }`,
      );
    }
    if (report.backend) {
      lines.push(
        `  backend:    ${report.backend.command}`,
      );
      lines.push(
        `              health ${report.backend.healthUrl} → ${
          report.backend.healthOk ? "ok" : "FAIL"
        } in ${report.backend.durationMs}ms (port ${report.backend.port})`,
      );
    }
    if (report.renderer) {
      lines.push(
        `  renderer:   ${report.renderer.indexPath} (exists=${
          report.renderer.indexExists ? "yes" : "NO"
        })`,
      );
      lines.push(
        `              load ${
          report.renderer.loadOk ? "ok" : "FAIL"
        } in ${report.renderer.loadDurationMs}ms; ${
          report.renderer.failedSubresources.length
        } failed subresource(s)`,
      );
      if (report.renderer.crashed) {
        lines.push(
          `              crashed: ${report.renderer.crashed.reason} (exit ${report.renderer.crashed.exitCode})`,
        );
      }
    }
    lines.push(`  stages:     ${report.stages.length} recorded`);
    if (report.errors.length > 0) {
      lines.push(`  errors:`);
      for (const err of report.errors) {
        lines.push(`    - ${err}`);
      }
    }
    return lines.join("\n");
  }
}

function isAppPackagedSafe(): boolean {
  try {
    return app.isPackaged;
  } catch (_err) {
    return false;
  }
}

/**
 * Best-effort redaction of obvious credential-shaped fields before logging.
 * We never want `api_key=...` to leak through the structured log. We replace
 * the value of any key that looks like a credential with `"<redacted>"` and a
 * 6-character suffix (the last 6 chars of the value, when available) so two
 * distinct keys are still distinguishable.
 */
const REDACT_KEYS = new Set([
  "api_key",
  "apikey",
  "api-key",
  "openai_api_key",
  "token",
  "authorization",
  "password",
  "secret",
]);

function redact(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object") return {};
  const out: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
    if (REDACT_KEYS.has(key.toLowerCase())) {
      const text = typeof val === "string" ? val : "";
      const suffix = text.length >= 6 ? text.slice(-6) : "<set>";
      out[key] = `<redacted:${suffix}>`;
      continue;
    }
    if (val && typeof val === "object" && !Array.isArray(val)) {
      out[key] = redact(val);
      continue;
    }
    out[key] = val;
  }
  return out;
}
