/**
 * Preload script for PatentAgent desktop. Runs in a sandboxed, isolated world
 * with contextBridge to expose a small, typed API to the renderer.
 *
 * PR6 (issue #20) adds ``window.desktop.config`` for LLM settings. The raw
 * API key never crosses the bridge — the renderer can only call
 * ``get / update / clearKey / health`` and the responses are redacted by the
 * main process and the backend.
 */
import { contextBridge, ipcRenderer, IpcRendererEvent } from "electron";

export type DesktopMenuAction = "open-settings" | "open-export-folder" | "about";

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

const api: DesktopApi = {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    node: process.versions.node,
    chrome: process.versions.chrome,
  },
  isDev: process.env.PATENTAGENT_ELECTRON_DEV === "1",
  config: configApi,
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
