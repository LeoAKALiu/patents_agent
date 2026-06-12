/**
 * FastAPI backend process supervision for the Electron main process.
 *
 * The v1 desktop MVP runs the existing Python backend as a local uvicorn
 * sidecar. Packaging a standalone backend binary is intentionally deferred to a
 * later PR; this launcher only uses the local Python interpreter.
 */
import { ChildProcess, spawn } from "child_process";
import { existsSync } from "fs";
import * as net from "net";
import * as path from "path";

export interface BackendHealth {
  ok: boolean;
  [key: string]: unknown;
}

export interface BackendSupervisorOptions {
  repoRoot: string;
  dataDir: string;
  env?: NodeJS.ProcessEnv;
  healthPath?: string;
  logger?: Pick<Console, "log" | "warn" | "error">;
  pythonExecutable?: string;
  requestedPort?: number;
  startupTimeoutMs?: number;
}

export interface BackendSupervisor {
  baseUrl: string;
  health: BackendHealth;
  healthUrl: string;
  port: number;
  process: ChildProcess;
  stop(graceMs?: number): Promise<void>;
}

export interface BackendStartupDetails {
  command: string;
  healthUrl: string;
  output: string;
  port: number;
}

export class BackendStartupError extends Error {
  details: BackendStartupDetails;

  constructor(message: string, details: BackendStartupDetails) {
    super(message);
    this.name = "BackendStartupError";
    this.details = details;
  }
}

const DEFAULT_HEALTH_PATH = "/api/health";
const DEFAULT_STARTUP_TIMEOUT_MS = 20_000;
const HEALTH_POLL_INTERVAL_MS = 250;
const HEALTH_FETCH_TIMEOUT_MS = 1_000;
const MAX_CAPTURED_OUTPUT_CHARS = 8_000;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeHealthPath(healthPath: string): string {
  return healthPath.startsWith("/") ? healthPath : `/${healthPath}`;
}

function appendPythonPath(repoRoot: string, existing: string | undefined): string {
  if (!existing) return repoRoot;
  return [repoRoot, existing].join(path.delimiter);
}

function appendCapturedOutput(current: string, chunk: string): string {
  const next = current + chunk;
  if (next.length <= MAX_CAPTURED_OUTPUT_CHARS) return next;
  return next.slice(next.length - MAX_CAPTURED_OUTPUT_CHARS);
}

function formatCommand(binary: string, args: string[]): string {
  return [binary, ...args].join(" ");
}

function defaultPythonExecutable(env: NodeJS.ProcessEnv): string {
  if (env.PATENTAGENT_PYTHON) return env.PATENTAGENT_PYTHON;

  const candidates =
    process.platform === "darwin"
      ? [
          "/opt/homebrew/anaconda3/bin/python3",
          "/opt/homebrew/bin/python3",
          "/usr/local/bin/python3",
          "/usr/bin/python3",
        ]
      : [];
  const absoluteCandidate = candidates.find((candidate) => existsSync(candidate));
  if (absoluteCandidate) return absoluteCandidate;

  return process.platform === "win32" ? "python" : "python3";
}

export function parsePort(value: string | number | undefined): number | undefined {
  if (value === undefined || value === "") return undefined;
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65_535) {
    throw new Error(`Invalid backend port: ${value}`);
  }
  return parsed;
}

function parsePositiveInteger(value: string | number | undefined): number | undefined {
  if (value === undefined || value === "") return undefined;
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) {
    throw new Error(`Invalid positive integer: ${value}`);
  }
  return parsed;
}

export async function findAvailablePort(host = "127.0.0.1"): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once("error", reject);
    server.listen(0, host, () => {
      const address = server.address();
      server.close(() => {
        if (address && typeof address === "object") {
          resolve(address.port);
          return;
        }
        reject(new Error("Unable to allocate a backend port"));
      });
    });
  });
}

async function fetchJsonWithTimeout(url: string, timeoutMs: number): Promise<BackendHealth> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`health returned HTTP ${response.status}`);
    }
    const payload = (await response.json()) as BackendHealth;
    if (!payload || payload.ok !== true) {
      throw new Error("health response did not include ok=true");
    }
    return payload;
  } finally {
    clearTimeout(timeout);
  }
}

async function waitForBackendHealth(
  child: ChildProcess,
  healthUrl: string,
  timeoutMs: number,
  startupDetails: () => BackendStartupDetails,
): Promise<BackendHealth> {
  const deadline = Date.now() + timeoutMs;
  let lastError: Error | null = null;

  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new BackendStartupError(
        `Backend exited before becoming healthy${child.signalCode ? ` (${child.signalCode})` : ""}`,
        startupDetails(),
      );
    }

    try {
      return await fetchJsonWithTimeout(healthUrl, HEALTH_FETCH_TIMEOUT_MS);
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
      await delay(HEALTH_POLL_INTERVAL_MS);
    }
  }

  throw new BackendStartupError(
    `Backend did not become healthy within ${timeoutMs}ms${lastError ? `: ${lastError.message}` : ""}`,
    startupDetails(),
  );
}

export async function stopBackendProcess(child: ChildProcess, graceMs = 2_000): Promise<void> {
  if (child.exitCode !== null || child.signalCode !== null) return;

  await new Promise<void>((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      child.removeListener("exit", finish);
      resolve();
    };
    const timer = setTimeout(() => {
      if (child.exitCode === null && child.signalCode === null) {
        child.kill("SIGKILL");
      }
      finish();
    }, graceMs);

    child.once("exit", finish);
    child.kill("SIGTERM");
  });
}

export async function startBackendSupervisor(
  options: BackendSupervisorOptions,
): Promise<BackendSupervisor> {
  const env = options.env ?? process.env;
  const port =
    options.requestedPort ??
    parsePort(env.PATENTAGENT_BACKEND_PORT) ??
    (await findAvailablePort());
  const healthPath = normalizeHealthPath(options.healthPath ?? DEFAULT_HEALTH_PATH);
  const baseUrl = `http://127.0.0.1:${port}`;
  const healthUrl = `${baseUrl}${healthPath}`;
  const pythonExecutable =
    options.pythonExecutable ?? defaultPythonExecutable(env);
  const args = [
    "-m",
    "uvicorn",
    "backend.app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    String(port),
    "--log-level",
    env.PATENTAGENT_BACKEND_LOG_LEVEL ?? "warning",
  ];
  const command = formatCommand(pythonExecutable, args);
  let output = "";

  const childEnv: NodeJS.ProcessEnv = {
    ...process.env,
    ...env,
    DATA_DIR: options.dataDir,
    PYTHONPATH: appendPythonPath(options.repoRoot, env.PYTHONPATH),
    PYTHONUNBUFFERED: "1",
  };

  const child = spawn(pythonExecutable, args, {
    cwd: options.repoRoot,
    env: childEnv,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  const capture = (streamName: "stdout" | "stderr", chunk: Buffer | string) => {
    const text = chunk.toString();
    output = appendCapturedOutput(output, text);
    const trimmed = text.trim();
    if (!trimmed) return;
    const logger = options.logger;
    if (streamName === "stderr") {
      logger?.warn(`[backend] ${trimmed}`);
    } else {
      logger?.log(`[backend] ${trimmed}`);
    }
  };

  child.stdout?.setEncoding("utf8");
  child.stderr?.setEncoding("utf8");
  child.stdout?.on("data", (chunk: Buffer | string) => capture("stdout", chunk));
  child.stderr?.on("data", (chunk: Buffer | string) => capture("stderr", chunk));

  const startupDetails = (): BackendStartupDetails => ({
    command,
    healthUrl,
    output,
    port,
  });

  const spawnError = new Promise<never>((_resolve, reject) => {
    child.once("error", (err) => {
      reject(
        new BackendStartupError(`Unable to launch backend: ${err.message}`, startupDetails()),
      );
    });
  });

  try {
    const health = await Promise.race([
      waitForBackendHealth(
        child,
        healthUrl,
        options.startupTimeoutMs ?? parsePositiveInteger(env.PATENTAGENT_BACKEND_TIMEOUT_MS) ?? DEFAULT_STARTUP_TIMEOUT_MS,
        startupDetails,
      ),
      spawnError,
    ]);
    options.logger?.log(`[backend] healthy at ${healthUrl}`);
    return {
      baseUrl,
      health,
      healthUrl,
      port,
      process: child,
      stop: (graceMs?: number) => stopBackendProcess(child, graceMs),
    };
  } catch (err) {
    await stopBackendProcess(child).catch(() => undefined);
    throw err;
  }
}
