type TauriInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>;

type TauriRuntime = {
  __TAURI__?: {
    core?: {
      invoke?: TauriInvoke;
    };
  };
};

type DesktopConfigUpdatePayload = {
  provider?: string;
  base_url?: string;
  model?: string;
  api_key?: string;
  clear_api_key?: boolean;
};

type SaveOfficialPayload = {
  format: "docx" | "md" | "sidecar";
  label: string;
  downloadPath: string;
  filter: { name: string; extensions: string[] };
  defaultFileName: string;
};

type OpenDraftResult = {
  cancelled: boolean;
  filePath: string;
  fileName: string;
  mimeType: string;
  contentBase64: string;
  byteCount: number;
};

type SaveOfficialResult = {
  cancelled: boolean;
  filePath: string;
  byteCount: number;
  format: "docx" | "md" | "sidecar";
};

type OpenFolderResult = {
  revealed: boolean;
  filePath: string;
};

type DesktopBridge = {
  platform?: string;
  versions?: Record<string, string>;
  isDev?: boolean;
  onMenuAction?: (handler: (action: string) => void) => () => void;
  config?: {
    get: () => Promise<unknown>;
    update: (payload: DesktopConfigUpdatePayload) => Promise<unknown>;
    clearKey: () => Promise<unknown>;
    health: () => Promise<unknown>;
  };
  dialogs?: {
    openDraft: (kind: "docx" | "markdown") => Promise<OpenDraftResult>;
    saveOfficial: (payload: SaveOfficialPayload) => Promise<SaveOfficialResult>;
    openFolder: (filePath: string) => Promise<OpenFolderResult>;
  };
};

type TauriDesktopWindow = Window & TauriRuntime & { desktop?: DesktopBridge };

function tauriInvoke(): TauriInvoke | null {
  const runtime = window as TauriDesktopWindow;
  return runtime.__TAURI__?.core?.invoke ?? null;
}

export function installTauriDesktopBridge(): void {
  if (typeof window === "undefined") return;
  const desktopWindow = window as TauriDesktopWindow;
  if (desktopWindow.desktop) return;
  const invoke = tauriInvoke();
  if (!invoke) return;

  desktopWindow.desktop = {
    platform: navigator.platform,
    versions: {},
    isDev: Boolean((import.meta as ImportMeta & { env?: { DEV?: boolean } }).env?.DEV),
    onMenuAction: () => () => undefined,
    config: {
      get: () => invoke("desktop_config_get"),
      update: (payload) => invoke("desktop_config_update", { payload }),
      clearKey: () => invoke("desktop_config_clear_key"),
      health: () => invoke("desktop_config_health"),
    },
    dialogs: {
      openDraft: (kind) => invoke("open_draft", { payload: { kind } }),
      saveOfficial: (payload) => invoke("save_official", { payload }),
      openFolder: (filePath) => invoke("open_folder", { payload: { filePath } }),
    },
  };
}
