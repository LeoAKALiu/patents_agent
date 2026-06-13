/**
 * Preload script for PatentAgent desktop. Runs in a sandboxed, isolated world
 * with contextBridge to expose a small, typed API to the renderer.
 *
 * PR6 (issue #20) adds ``window.desktop.config`` for LLM settings. The raw
 * API key never crosses the bridge — the renderer can only call
 * ``get / update / clearKey / health`` and the responses are redacted by the
 * main process and the backend.
 *
 * PR7 (issue #21) adds ``window.desktop.dialogs`` for native open / save
 * dialogs. File bytes still flow from the supervised FastAPI backend over
 * HTTP; the bridge only chooses the path, streams the response, and returns
 * the chosen file path + byte count. The renderer never receives a path it
 * did not select.
 */
import { contextBridge, ipcRenderer, IpcRendererEvent } from "electron";

export type DesktopMenuAction =
  | "open-settings"
  | "open-export-folder"
  | "about"
  | "import-draft-docx"
  | "import-draft-markdown"
  | "export-official-docx"
  | "export-official-md"
  | "export-official-sidecar";

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

export interface DesktopConfigUpdatePayload {
  provider?: string;
  base_url?: string;
  model?: string;
  api_key?: string;
  clear_api_key?: boolean;
}

export interface DesktopConfigApi {
  /** Fetch the redacted desktop LLM configuration. */
  get(): Promise<DesktopConfigView>;
  /**
   * Persist a desktop LLM configuration update. Pass ``api_key`` to set the
   * key, or ``clear_api_key: true`` to remove it. The renderer never receives
   * the raw key in the response.
   */
  update(payload: DesktopConfigUpdatePayload): Promise<DesktopConfigView>;
  /** Remove the locally stored API key. */
  clearKey(): Promise<DesktopConfigView>;
  /**
   * Probe the configured LLM with a tiny request. Returns latency, status, and
   * any error string — never the key itself.
   */
  health(): Promise<DesktopConfigHealthResult>;
}

export type OpenDraftKind = "docx" | "markdown";

export interface OpenDraftResult {
  cancelled: boolean;
  filePath: string;
  fileName: string;
  mimeType: string;
  contentBase64: string;
  byteCount: number;
}

export type OfficialExportFormat = "docx" | "md" | "sidecar";

export interface SaveOfficialPayload {
  format: OfficialExportFormat;
  /** Friendly format label, e.g. "官方 DOCX". */
  label: string;
  /** Backend endpoint to stream (relative path; must start with /api/...). */
  downloadPath: string;
  /** File filter shown in the save dialog. */
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

export interface DesktopDialogsApi {
  /**
   * Show a native open-file dialog for importing a draft. Returns
   * ``{cancelled: true}`` if the user dismisses the dialog. The renderer is
   * expected to upload the chosen file via the existing
   * ``/api/projects/{id}/external-drafts/upload`` endpoint.
   */
  openDraft(kind: OpenDraftKind): Promise<OpenDraftResult>;
  /**
   * Show a native save dialog, then stream the chosen backend endpoint to
   * the user-selected file. Returns ``{cancelled: true}`` if the user
   * dismisses the dialog. ``downloadPath`` must start with ``/api/``.
   */
  saveOfficial(payload: SaveOfficialPayload): Promise<SaveOfficialResult>;
  /**
   * Reveal a previously written file in the OS file manager
   * (Finder / Explorer / xdg-open). Does not open the file itself.
   */
  openFolder(filePath: string): Promise<OpenFolderResult>;
}

export interface DesktopApi {
  platform: NodeJS.Platform;
  versions: {
    electron: string;
    node: string;
    chrome: string;
  };
  isDev: boolean;
  /** Subscribe to native menu events. Returns an unsubscribe function. */
  onMenuAction(handler: (action: DesktopMenuAction) => void): () => void;
  /** Desktop LLM configuration IPC (PR6, issue #20). */
  config: DesktopConfigApi;
  /** Native file dialogs (PR7, issue #21). */
  dialogs: DesktopDialogsApi;
}

const configApi: DesktopConfigApi = {
  get: () => ipcRenderer.invoke("desktop:config:get") as Promise<DesktopConfigView>,
  update: (payload) =>
    ipcRenderer.invoke("desktop:config:update", payload) as Promise<DesktopConfigView>,
  clearKey: () =>
    ipcRenderer.invoke("desktop:config:clear-key") as Promise<DesktopConfigView>,
  health: () =>
    ipcRenderer.invoke("desktop:config:health") as Promise<DesktopConfigHealthResult>,
};

const dialogsApi: DesktopDialogsApi = {
  openDraft: (kind) =>
    ipcRenderer.invoke("desktop:dialogs:open-draft", { kind }) as Promise<OpenDraftResult>,
  saveOfficial: (payload) =>
    ipcRenderer.invoke("desktop:dialogs:save-official", payload) as Promise<SaveOfficialResult>,
  openFolder: (filePath) =>
    ipcRenderer.invoke("desktop:dialogs:open-folder", { filePath }) as Promise<OpenFolderResult>,
};

const api: DesktopApi = {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    node: process.versions.node,
    chrome: process.versions.chrome,
  },
  isDev: process.env.PATENTAGENT_ELECTRON_DEV === "1",
  config: configApi,
  dialogs: dialogsApi,
  onMenuAction(handler) {
    const listener = (
      _event: IpcRendererEvent,
      payload: { action: DesktopMenuAction },
    ) => {
      handler(payload.action);
    };
    ipcRenderer.on("desktop:menu", listener);
    return () => {
      ipcRenderer.removeListener("desktop:menu", listener);
    };
  },
};

contextBridge.exposeInMainWorld("desktop", api);
