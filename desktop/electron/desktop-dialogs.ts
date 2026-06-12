/**
 * Desktop file dialog IPC for the Electron main process (PR7, issue #21).
 *
 * Native open / save dialogs for the official patent export flow. The renderer
 * never receives a raw filesystem path it did not choose: every path returned
 * here was either the user-selected source (openDraft) or the user-selected
 * destination (saveOfficial). ``openFolder`` reveals a previously written file
 * in the OS file manager.
 *
 * The file bytes themselves flow from the supervised FastAPI backend over
 * HTTP, never through Electron IPC. This module only:
 *   1. Asks the user where the file lives / should go (native dialog).
 *   2. Streams the bytes from ``backendBaseUrl/<downloadUrl>`` to disk.
 *   3. Returns a redacted result (``filePath``, ``byteCount``) to the renderer.
 *
 * If the user cancels, ``{cancelled: true}`` is returned so the renderer can
 * stay on the same step without surfacing an error.
 */
import { dialog, ipcMain, shell } from "electron";
import { createWriteStream } from "fs";
import { mkdir, readFile } from "fs/promises";
import { basename, dirname, extname } from "path";
import * as http from "http";
import { URL } from "url";

export type OpenDraftKind = "docx" | "markdown";

export interface OpenDraftFilters {
  docx: { name: string; extensions: string[] };
  markdown: { name: string; extensions: string[] };
}

export const OPEN_DRAFT_FILTERS: OpenDraftFilters = {
  docx: { name: "Word 文档", extensions: ["docx"] },
  markdown: { name: "Markdown 文本", extensions: ["md", "markdown"] },
};

export interface OpenDraftResult {
  cancelled: boolean;
  filePath: string;
  fileName: string;
  mimeType: string;
  contentBase64: string;
  byteCount: number;
}

export type OfficialExportFormat = "docx" | "md" | "sidecar";

export interface OfficialExportOption {
  /** Friendly format label, e.g. "官方 DOCX" or "侧车报告" */
  label: string;
  /** Backend endpoint to stream (relative path; must start with /api/...). */
  downloadPath: string;
  /** Filter shown in the save dialog. */
  filter: { name: string; extensions: string[] };
  /** Default filename presented in the save dialog. */
  defaultFileName: string;
}

export interface SaveOfficialResult {
  cancelled: boolean;
  filePath: string;
  byteCount: number;
  format: OfficialExportFormat;
}

export interface OpenFolderResult {
  revealed: boolean;
  filePath: string;
}

export interface DesktopDialogsClientOptions {
  baseUrl: string;
  timeoutMs?: number;
  parentWindow?: Electron.BrowserWindow;
}

export class DesktopDialogsError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "DesktopDialogsError";
    this.status = status;
  }
}

function sanitiseError(err: unknown): string {
  if (err instanceof Error) return err.message.slice(0, 512);
  return String(err).slice(0, 512);
}

function isHttpOk(status: number): boolean {
  return status >= 200 && status < 300;
}

function ensureApiPath(downloadPath: string): string {
  if (!downloadPath.startsWith("/api/")) {
    throw new DesktopDialogsError(
      `download path must start with /api/ (got: ${downloadPath})`,
      400,
    );
  }
  return downloadPath;
}

function mimeTypeForDraft(kind: OpenDraftKind): string {
  return kind === "docx"
    ? "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    : "text/markdown";
}

function extensionMatchesKind(filePath: string, kind: OpenDraftKind): boolean {
  const ext = extname(filePath).toLowerCase();
  if (kind === "docx") return ext === ".docx";
  return ext === ".md" || ext === ".markdown";
}

/**
 * Stream a backend response body to disk at ``outputPath``. Returns the number
 * of bytes written. Throws ``DesktopDialogsError`` on HTTP or I/O failure.
 */
function streamBackendToFile(
  baseUrl: string,
  downloadPath: string,
  outputPath: string,
  timeoutMs: number,
): Promise<number> {
  ensureApiPath(downloadPath);
  const url = new URL(
    downloadPath.replace(/^\/+/, ""),
    baseUrl.endsWith("/") ? baseUrl : baseUrl + "/",
  );

  return new Promise<number>((resolve, reject) => {
    const request = http.request(
      {
        method: "GET",
        hostname: url.hostname,
        port: url.port || 80,
        path: url.pathname + url.search,
        headers: { accept: "*/*" },
      },
      (response: http.IncomingMessage) => {
        const status = response.statusCode ?? 502;
        if (!isHttpOk(status)) {
          // Drain so the socket can be reused.
          response.resume();
          reject(
            new DesktopDialogsError(
              `HTTP ${status} from ${downloadPath} while preparing export`,
              status,
            ),
          );
          return;
        }
        mkdir(dirname(outputPath), { recursive: true })
          .then(() => {
            const out = createWriteStream(outputPath);
            let byteCount = 0;
            response.on("data", (chunk: Buffer) => {
              byteCount += chunk.length;
            });
            response.on("error", (err: Error) => {
              out.destroy();
              reject(new DesktopDialogsError(sanitiseError(err), 502));
            });
            out.on("error", (err: Error) => {
              response.destroy();
              reject(new DesktopDialogsError(sanitiseError(err), 502));
            });
            out.on("finish", () => {
              if (byteCount === 0) {
                reject(
                  new DesktopDialogsError(
                    `backend returned an empty body for ${downloadPath}`,
                    502,
                  ),
                );
                return;
              }
              resolve(byteCount);
            });
            response.pipe(out);
          })
          .catch((err: Error) => {
            response.destroy();
            reject(new DesktopDialogsError(sanitiseError(err), 502));
          });
      },
    );
    request.on("error", (err: Error) =>
      reject(new DesktopDialogsError(sanitiseError(err), 502)),
    );
    request.setTimeout(timeoutMs, () => {
      request.destroy();
      reject(
        new DesktopDialogsError(
          `request to ${downloadPath} timed out after ${timeoutMs}ms`,
          504,
        ),
      );
    });
    request.end();
  });
}

export function extensionFor(format: OfficialExportFormat): string {
  if (format === "docx") return ".docx";
  if (format === "md") return ".md";
  return ".md";
}

export class DesktopDialogsClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly parentWindow: Electron.BrowserWindow | undefined;

  constructor(options: DesktopDialogsClientOptions) {
    this.baseUrl = options.baseUrl;
    this.timeoutMs = options.timeoutMs ?? 60_000;
    this.parentWindow = options.parentWindow;
  }

  /**
   * Show a native open-file dialog. Returns ``{cancelled: true}`` if the user
   * dismisses the dialog. The chosen file is read only after the user selects
   * it, and the bytes are returned to the renderer so it can reuse the
   * existing /api/projects/{id}/external-drafts/upload endpoint.
   */
  async openDraft(kind: OpenDraftKind): Promise<OpenDraftResult> {
    const filter = OPEN_DRAFT_FILTERS[kind];
    const dialogOptions: Electron.OpenDialogOptions = {
      title:
        kind === "docx" ? "选择要导入的 Word 草稿" : "选择要导入的 Markdown 草稿",
      properties: ["openFile"],
      filters: [
        { name: filter.name, extensions: filter.extensions },
        { name: "全部文件", extensions: ["*"] },
      ],
    };
    const result = this.parentWindow
      ? await dialog.showOpenDialog(this.parentWindow, dialogOptions)
      : await dialog.showOpenDialog(dialogOptions);
    if (result.canceled || result.filePaths.length === 0) {
      return {
        cancelled: true,
        filePath: "",
        fileName: "",
        mimeType: mimeTypeForDraft(kind),
        contentBase64: "",
        byteCount: 0,
      };
    }
    const filePath = result.filePaths[0];
    if (!extensionMatchesKind(filePath, kind)) {
      throw new DesktopDialogsError(
        kind === "docx"
          ? "selected draft must be a .docx file"
          : "selected draft must be a .md or .markdown file",
        400,
      );
    }
    const content = await readFile(filePath);
    return {
      cancelled: false,
      filePath,
      fileName: basename(filePath),
      mimeType: mimeTypeForDraft(kind),
      contentBase64: content.toString("base64"),
      byteCount: content.length,
    };
  }

  /**
   * Show a native save dialog, then stream the chosen backend endpoint to the
   * user-selected file. Returns ``{cancelled: true}`` if the user dismisses
   * the dialog. Overwrite is permitted by default for save dialogs.
   */
  async saveOfficial(
    format: OfficialExportFormat,
    option: OfficialExportOption,
  ): Promise<SaveOfficialResult> {
    const dialogOptions: Electron.SaveDialogOptions = {
      title: "保存正式稿",
      defaultPath: option.defaultFileName,
      filters: [
        option.filter,
        { name: "全部文件", extensions: ["*"] },
      ],
    };
    const result = this.parentWindow
      ? await dialog.showSaveDialog(this.parentWindow, dialogOptions)
      : await dialog.showSaveDialog(dialogOptions);
    if (result.canceled || !result.filePath) {
      return { cancelled: true, filePath: "", byteCount: 0, format };
    }
    // If the user typed a name without an extension, append the canonical one.
    let outputPath = result.filePath;
    if (!extname(outputPath)) {
      outputPath += extensionFor(format);
    }
    try {
      const byteCount = await streamBackendToFile(
        this.baseUrl,
        option.downloadPath,
        outputPath,
        this.timeoutMs,
      );
      return { cancelled: false, filePath: outputPath, byteCount, format };
    } catch (err) {
      throw err instanceof DesktopDialogsError
        ? err
        : new DesktopDialogsError(sanitiseError(err), 502);
    }
  }

  /**
   * Reveal an already-written file in the OS file manager (Finder / Explorer
   * / xdg-open). Does not open the file itself.
   */
  async openFolder(filePath: string): Promise<OpenFolderResult> {
    if (!filePath) {
      throw new DesktopDialogsError("filePath is required", 400);
    }
    shell.showItemInFolder(filePath);
    return { revealed: true, filePath };
  }
}

/**
 * Register the desktop file dialog IPC handlers on ``ipcMain``. The caller is
 * responsible for passing in a ``DesktopDialogsClient`` that points at the
 * supervised FastAPI backend.
 */
export function attachDesktopDialogsIpc(
  client: DesktopDialogsClient,
): void {
  ipcMain.handle(
    "desktop:dialogs:open-draft",
    async (_event: unknown, payload: unknown) => {
      if (!payload || typeof payload !== "object") {
        throw new DesktopDialogsError(
          "open-draft payload must be an object",
          400,
        );
      }
      const kindRaw = (payload as Record<string, unknown>).kind;
      if (kindRaw !== "docx" && kindRaw !== "markdown") {
        throw new DesktopDialogsError(
          "open-draft kind must be 'docx' or 'markdown'",
          400,
        );
      }
      return client.openDraft(kindRaw);
    },
  );

  ipcMain.handle(
    "desktop:dialogs:save-official",
    async (_event: unknown, payload: unknown) => {
      if (!payload || typeof payload !== "object") {
        throw new DesktopDialogsError(
          "save-official payload must be an object",
          400,
        );
      }
      const update = payload as Record<string, unknown>;
      const format = update.format;
      if (
        format !== "docx" &&
        format !== "md" &&
        format !== "sidecar"
      ) {
        throw new DesktopDialogsError(
          "save-official format must be 'docx' | 'md' | 'sidecar'",
          400,
        );
      }
      const option: OfficialExportOption = {
        label: typeof update.label === "string" ? update.label : "Official",
        downloadPath:
          typeof update.downloadPath === "string"
            ? update.downloadPath
            : "",
        filter:
          update.filter && typeof update.filter === "object"
            ? (update.filter as OfficialExportOption["filter"])
            : { name: "File", extensions: ["*"] },
        defaultFileName:
          typeof update.defaultFileName === "string"
            ? update.defaultFileName
            : "official.bin",
      };
      if (!option.downloadPath.startsWith("/api/")) {
        throw new DesktopDialogsError(
          "save-official downloadPath must start with /api/",
          400,
        );
      }
      return client.saveOfficial(format, option);
    },
  );

  ipcMain.handle(
    "desktop:dialogs:open-folder",
    async (_event: unknown, payload: unknown) => {
      if (!payload || typeof payload !== "object") {
        throw new DesktopDialogsError(
          "open-folder payload must be an object",
          400,
        );
      }
      const filePath = (payload as Record<string, unknown>).filePath;
      if (typeof filePath !== "string" || !filePath) {
        throw new DesktopDialogsError(
          "open-folder filePath must be a non-empty string",
          400,
        );
      }
      return client.openFolder(filePath);
    },
  );
}
