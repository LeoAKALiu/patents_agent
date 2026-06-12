#!/usr/bin/env node
/**
 * Smoke test for the Electron desktop runtime.
 *
 * Compiles main + preload (via `npm run build`), then launches the Electron
 * binary with `--smoke`. The main process starts the local FastAPI backend,
 * waits for `/api/health`, boots a hidden BrowserWindow, validates preload,
 * then exits 0 (or 1 on failure). On Linux CI without a display, wrap this with
 * `xvfb-run -a` if you want a real launch.
 *
 * Exit codes:
 *   0  smoke passed
 *   1  smoke failed (window did not load)
 *   2  missing compiled entry — `npm run build` first
 * 124  smoke timed out
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const require = createRequire(import.meta.url);

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = resolve(__dirname, "..");
const mainEntry = resolve(projectRoot, "dist-electron", "main.js");

if (!existsSync(mainEntry)) {
  console.error(`smoke: missing compiled entry ${mainEntry} — run 'npm run build' first.`);
  process.exit(2);
}

const electronBin = process.env.PATENTAGENT_ELECTRON_BIN
  ? process.env.PATENTAGENT_ELECTRON_BIN
  : require("electron");

if (typeof electronBin !== "string" || !existsSync(electronBin)) {
  console.error(`smoke: electron binary not found at ${electronBin}`);
  process.exit(2);
}

const child = spawn(electronBin, [projectRoot, "--smoke"], {
  stdio: "inherit",
  env: { ...process.env, ELECTRON_ENABLE_LOGGING: "1" },
});

const timeoutMs = Number(process.env.PATENTAGENT_SMOKE_TIMEOUT_MS ?? 30_000);
const timeout = setTimeout(() => {
  console.error(`smoke: timeout after ${timeoutMs}ms, killing.`);
  child.kill("SIGTERM");
  // Give it a moment to actually exit before forcing a non-zero code.
  setTimeout(() => process.exit(124), 1500);
}, timeoutMs);

child.on("exit", (code, signal) => {
  clearTimeout(timeout);
  if (code === 0) {
    console.log("smoke: passed");
    process.exit(0);
  }
  if (signal) {
    console.error(`smoke: terminated by signal ${signal}`);
    process.exit(1);
  }
  console.error(`smoke: failed with exit code ${code}`);
  process.exit(code ?? 1);
});
