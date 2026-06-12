/**
 * Preload script for PatentAgent desktop. Runs in a sandboxed, isolated world
 * with contextBridge to expose a small, typed API to the renderer.
 */
import { contextBridge, ipcRenderer, IpcRendererEvent } from "electron";

export type DesktopMenuAction = "open-settings" | "open-export-folder" | "about";

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
}

const api: DesktopApi = {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    node: process.versions.node,
    chrome: process.versions.chrome,
  },
  isDev: process.env.PATENTAGENT_ELECTRON_DEV === "1",
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
