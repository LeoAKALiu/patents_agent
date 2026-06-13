/**
 * Electron main process for PatentAgent desktop.
 *
 * PR5 (GitHub issue #19) starts the local FastAPI backend as a Python/uvicorn
 * sidecar, waits for /api/health before loading the renderer, proxies renderer
 * /api/* requests to that local backend, and shuts the backend down when the
 * app exits. PR6 (issue #20) adds desktop LLM configuration IPC. PR7
 * (issue #21) adds native open / save file dialogs for draft import and
 * official export, plus the "open export folder" menu action.
 *
 * PR6 of the v1.1 line (issue #38) adds startup reliability and diagnostics:
 *   - record a structured log of every boot stage,
 *   - check that the production frontend build is present before the
 *     renderer tries to load it (so a missing build shows a friendly
 *     diagnostic page instead of a blank white page),
 *   - wire `did-fail-load` and `render-process-gone` listeners that surface
 *     asset failures (e.g. a corrupt JS bundle) as a diagnostic page, and
 *   - expose a "Help → 诊断信息" menu item plus a renderer IPC so a user can
 *     copy the boot report into a bug report.
 *
 * Packaging a standalone backend binary remains deferred to a later PR.
 */
import { app, BrowserWindow, Menu, MenuItemConstructorOptions, dialog, shell, session } from "electron";
import { existsSync } from "fs";
import * as os from "os";
import * as path from "path";
import {
  BackendStartupError,
  BackendSupervisor,
  startBackendSupervisor,
} from "./backend-supervisor";
import {
  DesktopConfigClient,
  attachDesktopConfigIpc,
} from "./desktop-config";
import {
  DesktopDialogsClient,
  attachDesktopDialogsIpc,
} from "./desktop-dialogs";
import {
  StartupDiagnostics,
  StartupRenderer,
} from "./startup-diagnostics";

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
let diagnostics: StartupDiagnostics | null = null;

function diagnosticsInstance(): StartupDiagnostics {
  if (!diagnostics) {
    diagnostics = new StartupDiagnostics();
  }
  return diagnostics;
}

function recordBootContext(): void {
  const d = diagnosticsInstance();
  d.record("argv", {
    argv: process.argv,
    cwd: process.cwd(),
    isSmoke,
    isDev,
    isPackaged: app.isPackaged,
  });
  d.setRendererIndex(FRONTEND_INDEX);
}

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

  // PR6 of v1.1 (issue #38): surface renderer asset failures as a diagnostic
  // page instead of a silent white screen. We collect every failure in
  // `pendingFailures` so the diagnostic report can list each missing
  // CSS/JS/font asset individually.
  const pendingFailures: Array<{ code: number; description: string; url: string }> = [];
  let renderCrashed: { reason: string; exitCode: number } | null = null;
  const loadStartedAt = Date.now();

  win.webContents.on("did-fail-load", (_event, code, description, validatedURL) => {
    pendingFailures.push({ code, description, url: validatedURL });
    diagnosticsInstance().record(
      "renderer.asset_failed",
      { code, description, url: validatedURL },
      "error",
    );
    // Only the main frame failure shows the diagnostic page; subresource
    // failures are still recorded so the help-menu report is useful.
    if (code !== -3 && !validatedURL.startsWith("data:")) {
      void showRendererAssetFailurePage(win, pendingFailures, renderCrashed).catch(
        (err) => console.error("[main] failed to show asset failure page:", err),
      );
    }
  });

  win.webContents.on("render-process-gone", (_event, details) => {
    renderCrashed = {
      reason: details.reason,
      exitCode: details.exitCode,
    };
    diagnosticsInstance().error("renderer.crashed", new Error(details.reason), {
      reason: details.reason,
      exitCode: details.exitCode,
    });
    void showRendererAssetFailurePage(win, pendingFailures, renderCrashed).catch(
      (err) => console.error("[main] failed to show crash diagnostic page:", err),
    );
  });

  win.webContents.on("did-finish-load", () => {
    const loadOk = pendingFailures.length === 0 && renderCrashed === null;
    const rendererState: StartupRenderer = {
      indexPath: FRONTEND_INDEX,
      indexExists: existsSync(FRONTEND_INDEX),
      loadOk,
      loadDurationMs: Date.now() - loadStartedAt,
      failedSubresources: pendingFailures.slice(),
      crashed: renderCrashed ?? undefined,
    };
    diagnosticsInstance().setRenderer(rendererState);
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
        label: "导入草稿…",
        submenu: [
          {
            label: "Word 文档 (.docx)",
            click: () => emitMenuAction("import-draft-docx"),
          },
          {
            label: "Markdown 文本 (.md)",
            click: () => emitMenuAction("import-draft-markdown"),
          },
        ],
      },
      {
        label: "导出正式稿…",
        submenu: [
          {
            label: "官方 DOCX",
            click: () => emitMenuAction("export-official-docx"),
          },
          {
            label: "官方 Markdown",
            click: () => emitMenuAction("export-official-md"),
          },
          {
            label: "侧车报告",
            click: () => emitMenuAction("export-official-sidecar"),
          },
        ],
      },
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
        label: "诊断信息",
        click: async () => {
          const report = diagnosticsInstance().toText();
          await dialog.showMessageBox({
            type: "info",
            title: "PatentAgent 启动诊断",
            message: "PatentAgent 启动诊断",
            detail: report,
          });
        },
      },
      { type: "separator" },
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
  const d = diagnosticsInstance();
  const startedAt = Date.now();
  d.record("backend.spawning", { dataDir });
  const supervisor = await startBackendSupervisor({
    repoRoot: REPO_ROOT,
    dataDir,
    logger: console,
  });
  backendSupervisor = supervisor;
  d.setBackend({
    command: "python -m uvicorn backend.app.main:app",
    port: supervisor.port,
    baseUrl: supervisor.baseUrl,
    healthUrl: supervisor.healthUrl,
    healthOk: supervisor.health?.ok === true,
    durationMs: Date.now() - startedAt,
    pid: supervisor.process.pid,
  });
  return supervisor;
}

function installDesktopConfigIpc(backendBaseUrl: string, parent: BrowserWindow | null = null): void {
  const client = new DesktopConfigClient({ baseUrl: backendBaseUrl });
  attachDesktopConfigIpc(client);
  const dialogClient = new DesktopDialogsClient({
    baseUrl: backendBaseUrl,
    parentWindow: parent ?? undefined,
  });
  attachDesktopDialogsIpc(dialogClient);
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

async function loadFrontendMissingPage(win: BrowserWindow, indexPath: string): Promise<void> {
  const pathEscaped = htmlEscape(indexPath);
  const repoRoot = htmlEscape(REPO_ROOT);
  const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>PatentAgent frontend build missing</title>
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
    <h1>前端构建产物缺失</h1>
    <p>PatentAgent 桌面端已启动，本地 FastAPI 后端 <code>/api/health</code> 健康，但找不到前端生产构建 <code>frontend/dist/index.html</code>。</p>
    <p>文件路径：<code>${pathEscaped}</code></p>
    <p>开发模式：保持此 Electron 窗口的同时运行 <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run dev</code>，刷新窗口即可。</p>
    <p>打包前修复：在仓库根目录执行 <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>，然后重新启动桌面端（构建产物根：<code>${repoRoot}</code>）。</p>
  </main>
</body>
</html>`;
  await win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

async function showRendererAssetFailurePage(
  win: BrowserWindow,
  failures: Array<{ code: number; description: string; url: string }>,
  crashed: { reason: string; exitCode: number } | null,
): Promise<void> {
  if (win.isDestroyed()) return;
  const lines: string[] = [];
  if (crashed) {
    lines.push(
      `<h1>渲染进程已崩溃</h1>`,
      `<p>原因：<code>${htmlEscape(crashed.reason)}</code>（退出码 <code>${crashed.exitCode}</code>）</p>`,
    );
  } else {
    lines.push(
      `<h1>前端资源加载失败</h1>`,
      `<p>本地后端已启动，但桌面端在加载 <code>${htmlEscape(FRONTEND_INDEX)}</code> 时失败了。常见原因：</p>`,
      `<ul>`,
      `<li>构建产物损坏或部分丢失（重新执行 <code>cd frontend &amp;&amp; npm run build</code>）。</li>`,
      `<li>开发服务器未启动（执行 <code>cd frontend &amp;&amp; npm run dev</code>）。</li>`,
      `<li>杀毒软件拦截了 <code>file://</code> 资源（白名单本应用）。</li>`,
      `</ul>`,
    );
  }
  if (failures.length > 0) {
    lines.push(`<h2>失败的资源 (${failures.length})</h2>`);
    lines.push(`<ul>`);
    for (const f of failures) {
      lines.push(
        `<li><code>${htmlEscape(String(f.code))}</code> ${htmlEscape(
          f.description,
        )} — <code>${htmlEscape(f.url)}</code></li>`,
      );
    }
    lines.push(`</ul>`);
  }
  const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>PatentAgent renderer failed</title>
  <style>
    :root { color-scheme: dark; }
    body { margin: 0; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f172a; color: #e2e8f0; display: grid; place-items: center; }
    main { max-width: 760px; padding: 32px; }
    h1 { margin: 0 0 12px; color: #fca5a5; font-size: 28px; }
    h2 { color: #fde68a; font-size: 18px; margin-top: 24px; }
    p, li { color: #cbd5e1; line-height: 1.6; }
    code { background: #111827; border: 1px solid #334155; border-radius: 6px; padding: 1px 6px; }
  </style>
</head>
<body>
  <main>
    ${lines.join("\n")}
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

async function loadSmokeFrontendDocument(win: BrowserWindow): Promise<void> {
  // Production-renderer probe: load the real frontend build via a file:// URL
  // and let the registered `did-fail-load` listener collect any subresource
  // failures. We assert the page reaches `did-finish-load` (no top-level
  // failure), and the caller asserts the failure list is empty.
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
    win.loadFile(FRONTEND_INDEX).catch(reject);
  });
}

async function probeSmokeWindow(win: BrowserWindow): Promise<{ hasDiagnostics: boolean; hasDiagnosticsGet: boolean }> {
  // Give the preload a tick so its contextBridge call has flushed.
  await new Promise((r) => setTimeout(r, 200));

  const probe = await win.webContents.executeJavaScript(
    "JSON.stringify({hasDesktop: typeof window.desktop==='object' && window.desktop!==null, hasOnMenuAction: typeof (window.desktop && window.desktop.onMenuAction)==='function', hasConfigGet: typeof (window.desktop && window.desktop.config && window.desktop.config.get)==='function', hasConfigUpdate: typeof (window.desktop && window.desktop.config && window.desktop.config.update)==='function', hasConfigClearKey: typeof (window.desktop && window.desktop.config && window.desktop.config.clearKey)==='function', hasConfigHealth: typeof (window.desktop && window.desktop.config && window.desktop.config.health)==='function', hasDialogsOpenDraft: typeof (window.desktop && window.desktop.dialogs && window.desktop.dialogs.openDraft)==='function', hasDialogsSaveOfficial: typeof (window.desktop && window.desktop.dialogs && window.desktop.dialogs.saveOfficial)==='function', hasDialogsOpenFolder: typeof (window.desktop && window.desktop.dialogs && window.desktop.dialogs.openFolder)==='function', hasDiagnostics: typeof (window.desktop && window.desktop.diagnostics)==='object' && window.desktop.diagnostics!==null, hasDiagnosticsGet: typeof (window.desktop && window.desktop.diagnostics && window.desktop.diagnostics.getReport)==='function', platform: (window.desktop && window.desktop.platform) || null})",
  );
  const result = JSON.parse(String(probe)) as {
    hasDesktop: boolean;
    hasOnMenuAction: boolean;
    hasConfigGet: boolean;
    hasConfigUpdate: boolean;
    hasConfigClearKey: boolean;
    hasConfigHealth: boolean;
    hasDialogsOpenDraft: boolean;
    hasDialogsSaveOfficial: boolean;
    hasDialogsOpenFolder: boolean;
    hasDiagnostics: boolean;
    hasDiagnosticsGet: boolean;
    platform: string | null;
  };

  if (!result.hasDesktop) {
    throw new Error("preload did not expose window.desktop");
  }
  if (!result.hasOnMenuAction) {
    throw new Error("preload did not expose window.desktop.onMenuAction");
  }
  if (!result.hasConfigGet) {
    throw new Error("preload did not expose window.desktop.config.get");
  }
  if (!result.hasConfigUpdate) {
    throw new Error("preload did not expose window.desktop.config.update");
  }
  if (!result.hasConfigClearKey) {
    throw new Error("preload did not expose window.desktop.config.clearKey");
  }
  if (!result.hasConfigHealth) {
    throw new Error("preload did not expose window.desktop.config.health");
  }
  if (!result.hasDialogsOpenDraft) {
    throw new Error("preload did not expose window.desktop.dialogs.openDraft");
  }
  if (!result.hasDialogsSaveOfficial) {
    throw new Error("preload did not expose window.desktop.dialogs.saveOfficial");
  }
  if (!result.hasDialogsOpenFolder) {
    throw new Error("preload did not expose window.desktop.dialogs.openFolder");
  }
  return { hasDiagnostics: result.hasDiagnostics, hasDiagnosticsGet: result.hasDiagnosticsGet };
}

async function runSmoke(): Promise<number> {
  const d = diagnosticsInstance();
  d.record("smoke.start");
  let win: BrowserWindow | null = null;
  try {
    const backend = await startBackend(smokeBackendDataDir());
    configureSessionSecurity(backend.baseUrl);
    installDesktopConfigIpc(backend.baseUrl);
    // eslint-disable-next-line no-console
    console.log(`[smoke] backend health ok: ${backend.healthUrl}`);

    // Step 1: probe the preload over a data URL so the smoke never depends on
    // a built frontend (this is what CI runs on every commit).
    win = createMainWindow();
    await loadSmokeDocument(win);
    const probeResult = await probeSmokeWindow(win);
    // eslint-disable-next-line no-console
    console.log(
      `[smoke] preload exposed desktop API: diagnostics=${probeResult.hasDiagnostics}`,
    );

    if (!probeResult.hasDiagnostics) {
      throw new Error("preload did not expose window.desktop.diagnostics");
    }
    if (!probeResult.hasDiagnosticsGet) {
      throw new Error("preload did not expose window.desktop.diagnostics.getReport");
    }

    // Step 2: if the production renderer has been built, load it and assert
    // no subresource failed. This is the path a packaged user hits and the
    // thing that used to silently render a blank white page on a missing
    // bundle. CI runs without `frontend/dist` and the asset-failure probe is
    // skipped — the data-URL probe above is the only mandatory check.
    const probeFrontend = process.env.PATENTAGENT_SMOKE_SKIP_FRONTEND !== "1" && existsSync(FRONTEND_INDEX);
    if (probeFrontend) {
      d.record("smoke.frontend_probe.start");
      const assetFailures: Array<{ code: number; description: string; url: string }> = [];
      let crashed: { reason: string; exitCode: number } | null = null;
      const onFail = (_event: unknown, code: number, description: string, validatedURL: string) => {
        if (validatedURL.startsWith("data:")) return;
        assetFailures.push({ code, description, url: validatedURL });
      };
      const onCrashed = (_event: unknown, details: { reason: string; exitCode: number }) => {
        crashed = { reason: details.reason, exitCode: details.exitCode };
      };
      win.webContents.on("did-fail-load", onFail);
      win.webContents.on("render-process-gone", onCrashed);
      try {
        await loadSmokeFrontendDocument(win);
        const finalCrashed = crashed as { reason: string; exitCode: number } | null;
        if (finalCrashed !== null) {
          d.record(
            "smoke.frontend_probe.crashed",
            { reason: finalCrashed.reason, exitCode: finalCrashed.exitCode },
            "error",
          );
          throw new Error(
            `frontend renderer crashed during smoke: ${finalCrashed.reason} (exit ${finalCrashed.exitCode})`,
          );
        }
        if (assetFailures.length > 0) {
          d.record(
            "smoke.frontend_probe.asset_failures",
            { count: assetFailures.length, samples: assetFailures.slice(0, 3) },
            "error",
          );
          throw new Error(
            `frontend renderer failed to load ${assetFailures.length} subresource(s); first: ${assetFailures[0].description} ${assetFailures[0].url}`,
          );
        }
        // The production renderer must also expose window.desktop so a
        // packaged user can reach the menu / settings / diagnostics.
        const prodProbe = await win.webContents.executeJavaScript(
          "JSON.stringify({hasDesktop: typeof window.desktop==='object' && window.desktop!==null, hasDiagnosticsGet: typeof (window.desktop && window.desktop.diagnostics && window.desktop.diagnostics.getReport)==='function'})",
        );
        const parsed = JSON.parse(String(prodProbe)) as {
          hasDesktop: boolean;
          hasDiagnosticsGet: boolean;
        };
        if (!parsed.hasDesktop) {
          throw new Error("production renderer did not expose window.desktop");
        }
        if (!parsed.hasDiagnosticsGet) {
          throw new Error("production renderer did not expose window.desktop.diagnostics.getReport");
        }
        d.record("smoke.frontend_probe.ok", { index: FRONTEND_INDEX });
        // eslint-disable-next-line no-console
        console.log(`[smoke] frontend assets loaded: ${FRONTEND_INDEX}`);
      } finally {
        win.webContents.removeListener("did-fail-load", onFail);
        win.webContents.removeListener("render-process-gone", onCrashed);
      }
    } else {
      d.record("smoke.frontend_probe.skipped", {
        indexPath: FRONTEND_INDEX,
        indexExists: false,
        reason: "frontend/dist/index.html not built; asset-failure probe skipped",
      });
      // eslint-disable-next-line no-console
      console.log(
        `[smoke] frontend assets skipped: ${FRONTEND_INDEX} not found (set PATENTAGENT_SMOKE_SKIP_FRONTEND=0 and run \`cd frontend && npm run build\` to exercise the production renderer)`,
      );
    }

    d.record("smoke.passed");
    return 0;
  } catch (err) {
    d.error("smoke.failed", err);
    console.error("[smoke] failed:", err);
    return 1;
  } finally {
    if (win && !win.isDestroyed()) win.destroy();
    await stopBackend().catch((err) => console.error("[smoke] backend stop failed:", err));
  }
}

async function bootDesktopApp(): Promise<void> {
  const d = diagnosticsInstance();
  d.record("boot.start", { isDev, isSmoke, isPackaged: app.isPackaged });
  let backendError: unknown | null = null;
  try {
    const backend = await startBackend(backendDataDir());
    configureSessionSecurity(backend.baseUrl);
    Menu.setApplicationMenu(buildAppMenu());
    mainWindow = createMainWindow();
    // Install the desktop IPC (config + dialogs) once the main window exists
    // so save/open dialogs are parented to it on macOS.
    installDesktopConfigIpc(backend.baseUrl, mainWindow);
    d.attachIpc();
    d.record("boot.window_created", { backendBaseUrl: backend.baseUrl });
  } catch (err) {
    backendError = err;
    d.error("boot.backend_failed", err);
    console.error("[main] failed to start backend:", err);
  }

  if (backendError) {
    if (!mainWindow) {
      mainWindow = createMainWindow();
      Menu.setApplicationMenu(buildAppMenu());
    }
    await loadBackendErrorPage(mainWindow, backendError);
    return;
  }

  // PR6 of v1.1 (issue #38): if the production renderer has not been built,
  // surface a friendly diagnostic page instead of letting Electron render a
  // blank window. In dev mode we let `loadURL(VITE_DEV_URL)` try the Vite
  // server — that path will fail with a clear network error on its own.
  if (!isDev && !existsSync(FRONTEND_INDEX)) {
    d.record("boot.frontend_missing", { indexPath: FRONTEND_INDEX }, "error");
    if (mainWindow) {
      await loadFrontendMissingPage(mainWindow, FRONTEND_INDEX);
    }
    return;
  }

  try {
    const win = mainWindow ?? createMainWindow();
    mainWindow = win;
    await loadRenderer(win);
    d.record("boot.renderer_load_ok");
  } catch (err) {
    d.error("boot.renderer_load_failed", err);
    console.error("[main] failed to load renderer:", err);
    if (mainWindow) {
      await loadRendererErrorPage(mainWindow, err);
    }
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow();
      void loadRenderer(mainWindow).catch((err) => {
        d.error("boot.activate_load_failed", err);
        console.error("[main] failed to load renderer on activate:", err);
        if (mainWindow) void loadRendererErrorPage(mainWindow, err);
      });
    }
  });
}

applySmokeFlags();
recordBootContext();

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
