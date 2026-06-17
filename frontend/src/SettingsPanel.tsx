/**
 * Settings panel for desktop LLM configuration (PR6, issue #20).
 *
 * The renderer NEVER holds the raw API key. The backend returns a redacted
 * view (fingerprint + present flag only), and the panel only sends the key
 * up when the user explicitly types a new value. Nothing is stored in
 * localStorage — the source of truth is the local ``desktop-config.json``
 * file managed by the backend.
 */
import { FormEvent, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  RefreshCw,
  Save,
  Trash2,
} from "lucide-react";

import {
  DesktopConfigHealthResult,
  DesktopConfigView,
  checkDesktopConfigHealth,
  clearDesktopConfigKey,
  getDesktopConfig,
  updateDesktopConfig,
} from "./api";

type SaveStatus =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; updatedAt: string }
  | { kind: "error"; message: string };

type HealthStatus =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "ok"; result: DesktopConfigHealthResult }
  | { kind: "no-key" }
  | { kind: "error"; result: DesktopConfigHealthResult };

function apiKeySourceLabel(source: DesktopConfigView["api_key_source"]): string {
  if (source === "env") return "环境变量";
  if (source === "desktop_config") return "本机配置";
  return "未配置";
}

export function SettingsPanel() {
  const [view, setView] = useState<DesktopConfigView | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [provider, setProvider] = useState("deepseek");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [clearRequested, setClearRequested] = useState(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>({ kind: "idle" });
  const [healthStatus, setHealthStatus] = useState<HealthStatus>({ kind: "idle" });

  const load = async () => {
    setLoading(true);
    setLoadError("");
    try {
      const data = await getDesktopConfig();
      setView(data);
      setProvider(data.provider);
      setBaseUrl(data.base_url);
      setModel(data.model);
      setApiKeyInput("");
      setClearRequested(false);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const runHealth = async () => {
    setHealthStatus({ kind: "checking" });
    try {
      const result = await checkDesktopConfigHealth();
      if (result.api_key_source === "none") {
        setHealthStatus({ kind: "no-key" });
      } else if (result.ok) {
        setHealthStatus({ kind: "ok", result });
      } else {
        setHealthStatus({ kind: "error", result });
      }
    } catch (err) {
      setHealthStatus({
        kind: "error",
        result: {
          ok: false,
          model: model,
          api_key_source: view?.api_key_source ?? "none",
          latency_ms: 0,
          status_code: 0,
          error: err instanceof Error ? err.message : String(err),
        },
      });
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaveStatus({ kind: "saving" });
    setHealthStatus({ kind: "idle" });
    try {
      const payload: Parameters<typeof updateDesktopConfig>[0] = {
        provider: provider.trim(),
        base_url: baseUrl.trim(),
        model: model.trim(),
      };
      if (clearRequested) {
        payload.clear_api_key = true;
      } else if (apiKeyInput.trim().length > 0) {
        payload.api_key = apiKeyInput.trim();
      }
      const next = await updateDesktopConfig(payload);
      setView(next);
      setApiKeyInput("");
      setClearRequested(false);
      setSaveStatus({ kind: "saved", updatedAt: next.updated_at });
    } catch (err) {
      setSaveStatus({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  const handleClearKey = async () => {
    setSaveStatus({ kind: "saving" });
    try {
      const next = await clearDesktopConfigKey();
      setView(next);
      setApiKeyInput("");
      setClearRequested(false);
      setSaveStatus({ kind: "saved", updatedAt: next.updated_at });
      setHealthStatus({ kind: "no-key" });
    } catch (err) {
      setSaveStatus({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  if (loading) {
    return (
      <section className="p-5 rounded-lg border border-app-border bg-app-surface max-w-[1120px]">
        <h3>设置</h3>
        <p className="section-copy">正在加载当前 LLM 配置…</p>
        <Loader2 className="animate-spin" size={18} />
      </section>
    );
  }

  if (loadError) {
    return (
      <section className="p-5 rounded-lg border border-app-border bg-app-surface max-w-[1120px]">
        <h3>设置</h3>
        <p className="section-copy">加载失败：{loadError}</p>
        <button
          className="btn-secondary"
          onClick={() => void load()}
          type="button"
        >
          <RefreshCw size={16} /> 重试
        </button>
      </section>
    );
  }

  const present = view?.api_key_present ?? false;
  const fingerprint = view?.api_key_fingerprint ?? "";

  return (
    <section className="p-5 rounded-lg border border-app-border bg-app-surface max-w-[1120px]" data-testid="settings-panel">
      <h3>设置 · LLM 服务</h3>
      <p className="section-copy">
        在本机保存 LLM 服务参数。密钥仅写在本机配置文件中，权限受限；
        界面只会显示是否已配置和指纹，不会回显明文。
      </p>

      <div className="settings-status-grid">
        <div className="settings-status-tile">
          <span>状态</span>
          <strong
            className={
              present || view?.api_key_source === "env"
                ? "text-emerald-400"
                : "text-amber-400"
            }
          >
            {apiKeySourceLabel(view?.api_key_source ?? "none")}
          </strong>
        </div>
        <div className="settings-status-tile">
          <span>密钥指纹</span>
          <code data-testid="api-key-fingerprint">
            {present ? fingerprint : "（未配置）"}
          </code>
        </div>
        <div className="settings-status-tile">
          <span>模型</span>
          <code>{view?.model ?? "—"}</code>
        </div>
        <div className="settings-status-tile">
          <span>Base URL</span>
          <code className="break-all">{view?.base_url ?? "—"}</code>
        </div>
      </div>

      <form className="settings-form" onSubmit={handleSubmit}>
        <label className="settings-field">
          <span>Provider</span>
          <input
            data-testid="settings-provider"
            onChange={(e) => setProvider(e.target.value)}
            placeholder="deepseek"
            required
            type="text"
            value={provider}
          />
        </label>
        <label className="settings-field">
          <span>Base URL</span>
          <input
            data-testid="settings-base-url"
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.deepseek.com"
            required
            type="url"
            value={baseUrl}
          />
        </label>
        <label className="settings-field">
          <span>Model</span>
          <input
            data-testid="settings-model"
            onChange={(e) => setModel(e.target.value)}
            placeholder="deepseek-v4-pro"
            required
            type="text"
            value={model}
          />
        </label>

        <label className="settings-field">
          <span>
            <KeyRound size={14} /> API Key
          </span>
          <div className="settings-key-row">
            <input
              autoComplete="off"
              data-testid="settings-api-key"
              onChange={(e) => {
                setApiKeyInput(e.target.value);
                setClearRequested(false);
              }}
              placeholder={present ? "（已配置）输入新值以替换" : "输入 API Key"}
              spellCheck={false}
              type={showKey ? "text" : "password"}
              value={apiKeyInput}
            />
            <button
              aria-label={showKey ? "隐藏密钥" : "显示密钥"}
              className="btn-ghost"
              onClick={() => setShowKey((prev) => !prev)}
              type="button"
            >
              {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {clearRequested ? (
            <small className="settings-hint warn">
              <AlertTriangle size={12} /> 点击"保存"后会清除已存储的密钥
            </small>
          ) : (
            <small className="settings-hint">
              密钥只发往本机后端，界面不会回显明文
            </small>
          )}
        </label>

        <div className="settings-actions">
          <button
            className="btn-primary"
            data-testid="settings-save"
            disabled={saveStatus.kind === "saving"}
            type="submit"
          >
            {saveStatus.kind === "saving" ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <Save size={16} />
            )}
            保存
          </button>
          <button
            className="btn-secondary"
            data-testid="settings-health"
            disabled={healthStatus.kind === "checking"}
            onClick={() => void runHealth()}
            type="button"
          >
            {healthStatus.kind === "checking" ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <RefreshCw size={16} />
            )}
            测试连通
          </button>
          <button
            className="btn-danger"
            data-testid="settings-clear"
            disabled={!present || saveStatus.kind === "saving"}
            onClick={() => {
              setClearRequested(true);
              setApiKeyInput("");
              void handleClearKey();
            }}
            type="button"
          >
            <Trash2 size={16} /> 清除密钥
          </button>
        </div>
      </form>

      {saveStatus.kind === "saved" && (
        <p className="settings-feedback ok" data-testid="settings-save-status">
          <CheckCircle2 size={14} /> 已保存（{saveStatus.updatedAt || "刚刚"}）
        </p>
      )}
      {saveStatus.kind === "error" && (
        <p className="settings-feedback err" data-testid="settings-save-status">
          <AlertTriangle size={14} /> {saveStatus.message}
        </p>
      )}

      {healthStatus.kind === "ok" && (
        <p className="settings-feedback ok" data-testid="settings-health-status">
          <CheckCircle2 size={14} /> {healthStatus.result.model} ·
          {" "}
          {healthStatus.result.latency_ms} ms
        </p>
      )}
      {healthStatus.kind === "no-key" && (
        <p className="settings-feedback warn" data-testid="settings-health-status">
          <AlertTriangle size={14} /> 尚未配置 API Key
        </p>
      )}
      {healthStatus.kind === "error" && (
        <p className="settings-feedback err" data-testid="settings-health-status">
          <AlertTriangle size={14} /> {healthStatus.result.error || "连通失败"}
        </p>
      )}
    </section>
  );
}
