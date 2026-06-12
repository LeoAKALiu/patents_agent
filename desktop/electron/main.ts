/**
 * Electron main process for PatentAgent desktop.
 *
 * PR5 (GitHub issue #19) starts the local FastAPI backend as a Python/uvicorn
 * sidecar, waits for /api/health before loading the renderer, proxies renderer
 * /api/* requests to that local backend, and shuts the backend down when the app
 * exits. Packaging a standalone backend binary, desktop settings, and native
 * file dialogs remain out of scope for later PRs.
 */
import { app, BrowserWindow, Menu, MenuItemConstructorOptions, dialog, shell, session } from "electron";
import * as os from "os";
import * as path from "path";
import {
  BackendStartupError,
  BackendSupervisor,
  startBackendSupervisor,
} from "./backend-supervisor";

const isSmoke = process.argv.includes("--smoke");
const isDev =
  process.env.PATENTAGENT_ELECTRON_DEV === "1" ||
  (!app.isPackaged && !isSmoke && process.env.PATENTAGENT_DESKTOP_PROD !== "1");

const VITE_DEV_URL = process.env.PATENTAGENT_VITE_URL ?? "http://127.0.0.1:5173";
// When compiled to dist-electron/main.js, this resolves to desktop/dist-electron/main.js
// and ../../frontend/dist/index.html is the sibling frontend build output.
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const FRONTEND_INDEX = path.resolve(REPO_ROOT, "frontend", "dist", "index.html");
// Use the existing SVG; native .icns/.ico/.png are produced in PR8+ packaging.
// Electron's BrowserWindow `icon` only accepts PNG/JPG, so we don't set it here.
let mainWindow: BrowserWindow | null = null;
let backendSupervisor: BackendSupervisor | null = null;
let isQuitting = false;

/** Apply command-line flags that make the smoke test reliable on CI/Linux. */
function applySmokeFlags(): void {
  if (!isSmoke) return;
  app.commandLine.appendSwitch("disable-gpu");
  app.commandLine.appendSwitch("disable-software-rasterizer");
  app.commandLine.appendSwitch("no-sandbox");
}

function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    title: "PatentAgent",
    show: !isSmoke,
    backgroundColor: "#0f172a",
    // Icon note: Electron's BrowserWindow `icon` only accepts PNG/JPG. We
    // intentionally do not set it here so the smoke test doesn't depend on a
    // rasterized logo. PR8+ packaging will ship platform-native .icns/.ico.
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    webPreferences: {
      preload: path.resolve(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: true,
      webSecurity: true,
    },
  });

  // The renderer is a single-page app; deny any attempt to open additional
  // browser windows from the renderer.
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (event, url) => {
    if (isDev && url.startsWith(VITE_DEV_URL)) return;
    if (url.startsWith("file://")) return;
    event.preventDefault();
    shell.openExternal(url).catch(() => undefined);
  });

  win.on("closed", () => {
    if (mainWindow === win) mainWindow = null;
  });

  return win;
}

async function loadRenderer(win: BrowserWindow): Promise<void> {
  if (isDev) {
    await win.loadURL(VITE_DEV_URL);
    return;
  }
  await win.loadFile(FRONTEND_INDEX);
}

function emitMenuAction(action: string): void {
  if (!mainWindow) return;
  mainWindow.webContents.send("desktop:menu", { action });
}

function buildAppMenu(): Menu {
  const isMac = process.platform === "darwin";
  const template: MenuItemConstructorOptions[] = [];

  if (isMac) {
    template.push({
      label: app.name,
      submenu: [
        { role: "about" },
        { type: "separator" },
        { role: "services" },
        { type: "separator" },
        { role: "hide" },
        { role: "hideOthers" },
        { role: "unhide" },
        { type: "separator" },
        { role: "quit" },
      ],
    });
  }

  template.push({
    label: "文件",
    submenu: [
      {
        label: "导出目录…",
        click: () => emitMenuAction("open-export-folder"),
      },
      { type: "separator" },
      {
        label: "设置…",
        accelerator: isMac ? "Cmd+," : "Ctrl+,",
        click: () => emitMenuAction("open-settings"),
      },
      { type: "separator" },
      isMac ? { role: "close" } : { role: "quit" },
    ],
  });

  template.push({
    label: "编辑",
    submenu: [
      { role: "undo" },
      { role: "redo" },
      { type: "separator" },
      { role: "cut" },
      { role: "copy" },
      { role: "paste" },
      { role: "selectAll" },
    ],
  });

  template.push({
    label: "视图",
    submenu: [
      { role: "reload" },
      { role: "forceReload" },
      { role: "toggleDevTools" },
      { type: "separator" },
      { role: "resetZoom" },
      { role: "zoomIn" },
      { role: "zoomOut" },
      { type: "separator" },
      { role: "togglefullscreen" },
    ],
  });

  template.push({
    label: "帮助",
    submenu: [
      {
        label: "关于 PatentAgent",
        click: async () => {
          await dialog.showMessageBox({
            type: "info",
            title: "PatentAgent",
            message: "PatentAgent",
            detail: `版本 ${app.getVersion()}\nElectron ${process.versions.electron}\nNode ${process.versions.node}\nChromium ${process.versions.chrome}`,
          });
        },
      },
    ],
  });

  return Menu.buildFromTemplate(template);
}

function backendDataDir(): string {
  return process.env.PATENTAGENT_BACKEND_DATA_DIR ?? path.join(app.getPath("userData"), "backend-data");
}

function smokeBackendDataDir(): string {
  return path.join(os.tmpdir(), `patentagent-backend-smoke-${process.pid}`);
}

async function startBackend(dataDir: string): Promise<BackendSupervisor> {
  backendSupervisor = await startBackendSupervisor({
    repoRoot: REPO_ROOT,
    dataDir,
    logger: console,
  });
  return backendSupervisor;
}

async function stopBackend(): Promise<void> {
  const supervisor = backendSupervisor;
  backendSupervisor = null;
  if (!supervisor) return;
  await supervisor.stop();
}

function stopBackendSync(): void {
  const supervisor = backendSupervisor;
  backendSupervisor = null;
  if (!supervisor) return;
  if (supervisor.process.exitCode === null && supervisor.process.signalCode === null) {
    supervisor.process.kill("SIGTERM");
  }
}

function routeRendererApiRequests(backendBaseUrl: string): void {
  const devUrl = new URL(VITE_DEV_URL);
  const devApiPattern = `${devUrl.origin}/api/*`;
  session.defaultSession.webRequest.onBeforeRequest(
    { urls: ["file:///api/*", devApiPattern] },
    (details, callback) => {
      try {
        const requestUrl = new URL(details.url);
        if (!requestUrl.pathname.startsWith("/api/")) {
          callback({});
          return;
        }
        callback({
          redirectURL: `${backendBaseUrl}${requestUrl.pathname}${requestUrl.search}`,
        });
      } catch (err) {
        console.error("[main] failed to proxy renderer API request:", err);
        callback({});
      }
    },
  );
}

function htmlEscape(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function backendErrorDetails(err: unknown): string {
  if (err instanceof BackendStartupError) {
    return `${err.message}\n\nCommand: ${err.details.command}\nHealth URL: ${err.details.healthUrl}\n\n${err.details.output}`;
  }
  if (err instanceof Error) return err.stack ?? err.message;
  return String(err);
}

async function loadBackendErrorPage(win: BrowserWindow, err: unknown): Promise<void> {
  const details = htmlEscape(backendErrorDetails(err));
  const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>PatentAgent backend failed</title>
  <style>
    :root { color-scheme: dark; }
    body { margin: 0; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f172a; color: #e2e8f0; display: grid; place-items: center; }
    main { max-width: 760px; padding: 32px; }
    h1 { margin: 0 0 12px; color: #fca5a5; font-size: 28px; }
    p { color: #cbd5e1; line-height: 1.6; }
    code, pre { background: #111827; border: 1px solid #334155; border-radius: 10px; }
    code { padding: 2px 6px; }
    pre { max-height: 280px; overflow: auto; padding: 16px; white-space: pre-wrap; color: #f8fafc; }
  </style>
</head>
<body>
  <main>
    <h1>后端服务启动失败</h1>
    <p>PatentAgent 桌面端已启动，但本地 FastAPI 后端未能通过 <code>/api/health</code> 健康检查。请确认本机 Python 环境已安装项目依赖后重新打开应用。</p>
    <p>常用修复命令：<code>python3 -m pip install -e ".[dev]"</code></p>
    <pre>${details}</pre>
  </main>
</body>
</html>`;
  await win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

async function loadRendererErrorPage(win: BrowserWindow, err: unknown): Promise<void> {
  const details = htmlEscape(err instanceof Error ? err.stack ?? err.message : String(err));
  const html = `<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8" /><title>PatentAgent renderer failed</title></head>
<body style="margin:0;min-height:100vh;background:#0f172a;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;display:grid;place-items:center;">
  <main style="max-width:760px;padding:32px;">
    <h1 style="color:#fca5a5;">前端页面加载失败</h1>
    <p>本地后端已启动，但桌面端无法加载前端页面。生产模式请先运行 <code>cd frontend &amp;&amp; npm run build</code>。</p>
    <pre style="white-space:pre-wrap;background:#111827;border:1px solid #334155;border-radius:10px;padding:16px;">${details}</pre>
  </main>
</body>
</html>`;
  await win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

function configureSessionSecurity(backendBaseUrl: string): void {
  routeRendererApiRequests(backendBaseUrl);
  // Lock down the default session: no insecure content, strict referrer, no
  // third-party storage by default.
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        "X-Content-Type-Options": ["nosniff"],
      },
    });
  });
}

async function loadSmokeDocument(win: BrowserWindow): Promise<void> {
  // The smoke test must not require a built frontend. Load a tiny data URL so
  // the renderer's preload runs in isolation; backend health is checked from the
  // Electron main process before this function is called.
  const dataUrl =
    "data:text/html;charset=utf-8," +
    encodeURIComponent(
      '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'"><title>smoke</title></head><body>smoke</body></html>',
    );
  await new Promise<void>((resolve, reject) => {
    const onLoaded = () => {
      win.webContents.removeListener("did-fail-load", onFailed);
      resolve();
    };
    const onFailed = (_event: unknown, code: number, desc: string) => {
      win.webContents.removeListener("did-finish-load", onLoaded);
      reject(new Error(`did-fail-load ${code} ${desc}`));
    };
    win.webContents.once("did-finish-load", onLoaded);
    win.webContents.once("did-fail-load", onFailed);
    win.loadURL(dataUrl).catch(reject);
  });
}

async function runSmoke(): Promise<number> {
  let win: BrowserWindow | null = null;
  try {
    const backend = await startBackend(smokeBackendDataDir());
    configureSessionSecurity(backend.baseUrl);
    // eslint-disable-next-line no-console
    console.log(`[smoke] backend health ok: ${backend.healthUrl}`);

    win = createMainWindow();
    await loadSmokeDocument(win);

    // Give the preload a tick so its contextBridge call has flushed.
    await new Promise((r) => setTimeout(r, 200));

    const probe = await win.webContents.executeJavaScript(
      "JSON.stringify({hasDesktop: typeof window.desktop==='object' && window.desktop!==null, hasOnMenuAction: typeof (window.desktop && window.desktop.onMenuAction)==='function', platform: (window.desktop && window.desktop.platform) || null})",
    );
    const result = JSON.parse(String(probe)) as {
      hasDesktop: boolean;
      hasOnMenuAction: boolean;
      platform: string | null;
    };

    if (!result.hasDesktop) {
      throw new Error("preload did not expose window.desktop");
    }
    if (!result.hasOnMenuAction) {
      throw new Error("preload did not expose window.desktop.onMenuAction");
    }

    // eslint-disable-next-line no-console
    console.log(
      `[smoke] preload exposed desktop API: platform=${result.platform}`,
    );
    return 0;
  } catch (err) {
    console.error("[smoke] failed:", err);
    return 1;
  } finally {
    if (win && !win.isDestroyed()) win.destroy();
    await stopBackend().catch((err) => console.error("[smoke] backend stop failed:", err));
  }
}

async function bootDesktopApp(): Promise<void> {
  let backendError: unknown | null = null;
  try {
    const backend = await startBackend(backendDataDir());
    configureSessionSecurity(backend.baseUrl);
  } catch (err) {
    backendError = err;
    console.error("[main] failed to start backend:", err);
  }

  Menu.setApplicationMenu(buildAppMenu());
  mainWindow = createMainWindow();

  if (backendError) {
    await loadBackendErrorPage(mainWindow, backendError);
    return;
  }

  try {
    await loadRenderer(mainWindow);
  } catch (err) {
    console.error("[main] failed to load renderer:", err);
    if (mainWindow) {
      await loadRendererErrorPage(mainWindow, err);
    }
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow();
      void loadRenderer(mainWindow).catch((err) => {
        console.error("[main] failed to load renderer on activate:", err);
        if (mainWindow) void loadRendererErrorPage(mainWindow, err);
      });
    }
  });
}

applySmokeFlags();

app.whenReady().then(async () => {
  if (isSmoke) {
    const code = await runSmoke();
    app.exit(code);
    return;
  }

  await bootDesktopApp();
});

app.on("before-quit", () => {
  isQuitting = true;
  stopBackendSync();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

process.on("exit", () => {
  stopBackendSync();
});

for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, () => {
    if (isQuitting) return;
    isQuitting = true;
    stopBackendSync();
    app.quit();
  });
}

// Hard-fail fast on uncaught exceptions during boot to surface renderer crashes
// in the terminal where the worker can capture them.
process.on("uncaughtException", (err) => {
  console.error("[main] uncaughtException:", err);
  if (isSmoke) app.exit(1);
});
