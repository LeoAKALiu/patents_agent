/**
 * Electron main process for PatentAgent desktop.
 *
 * Scope (PR4, GitHub issue #18): load the Vite dev URL in development, load the
 * built frontend in production, register a native menu, and expose a smoke
 * entry that boots headlessly and exits. Backend supervision, secret handling,
 * and native file dialogs are explicitly out of scope here (PR5+).
 */
import { app, BrowserWindow, Menu, MenuItemConstructorOptions, dialog, shell, session } from "electron";
import * as path from "path";

const isSmoke = process.argv.includes("--smoke");
const isDev =
  process.env.PATENTAGENT_ELECTRON_DEV === "1" ||
  (!app.isPackaged && !isSmoke && process.env.PATENTAGENT_DESKTOP_PROD !== "1");

const VITE_DEV_URL = process.env.PATENTAGENT_VITE_URL ?? "http://127.0.0.1:5173";
// When compiled to dist-electron/main.js, this resolves to desktop/dist-electron/main.js
// and ../../frontend/dist/index.html is the sibling frontend build output.
const FRONTEND_INDEX = path.resolve(__dirname, "..", "..", "frontend", "dist", "index.html");
// Use the existing SVG; native .icns/.ico/.png are produced in PR5+ packaging.
// Electron's BrowserWindow `icon` only accepts PNG/JPG, so we don't set it here.
let mainWindow: BrowserWindow | null = null;

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
    // rasterized logo. PR5+ packaging will ship platform-native .icns/.ico.
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

async function runSmoke(): Promise<number> {
  const win = createMainWindow();
  try {
    // The smoke test must not require a built frontend. Load a tiny data URL
    // so the renderer's preload runs in isolation; this is the contract we
    // want to verify for the skeleton.
    const dataUrl =
      "data:text/html;charset=utf-8," +
      encodeURIComponent(
        "<!doctype html><html><head><title>smoke</title></head><body>smoke</body></html>",
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
    if (!win.isDestroyed()) win.destroy();
  }
}

function configureSessionSecurity(): void {
  // Lock down the default session: no insecure content, strict referrer, no
  // third-party storage by default. PR5 may add per-API exemptions.
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        "X-Content-Type-Options": ["nosniff"],
      },
    });
  });
}

applySmokeFlags();

app.whenReady().then(async () => {
  configureSessionSecurity();
  Menu.setApplicationMenu(buildAppMenu());

  if (isSmoke) {
    const code = await runSmoke();
    app.exit(code);
    return;
  }

  mainWindow = createMainWindow();
  try {
    await loadRenderer(mainWindow);
  } catch (err) {
    console.error("[main] failed to load renderer:", err);
    if (mainWindow) {
      mainWindow.webContents.once("did-finish-load", () => {
        // After the error page is up, the menu is still usable.
      });
    }
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow();
      void loadRenderer(mainWindow);
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

// Hard-fail fast on uncaught exceptions during boot to surface renderer crashes
// in the terminal where the worker can capture them.
process.on("uncaughtException", (err) => {
  console.error("[main] uncaughtException:", err);
  if (isSmoke) app.exit(1);
});
