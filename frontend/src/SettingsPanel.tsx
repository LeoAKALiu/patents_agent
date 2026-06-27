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
  Monitor,
  Moon,
  RefreshCw,
  Save,
  Sun,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { DARK_MODE_ENABLED, type ThemeMode } from "./ui/useTheme";
import {
  DesktopConfigHealthResult,
  DesktopConfigView,
  checkDesktopConfigHealth,
  clearDesktopConfigKey,
  getDesktopConfig,
  updateDesktopConfig,
} from "./api";
import { userFacingAppErrorMessage, userFacingErrorCopy } from "./runtimeDisplay";

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

const THEME_OPTIONS: { value: ThemeMode; label: string; icon: typeof Sun }[] = [
  { value: "auto", label: "自动", icon: Monitor },
  { value: "light", label: "浅色", icon: Sun },
  { value: "dark", label: "深色", icon: Moon },
];

export interface SettingsPanelProps {
  theme: ThemeMode;
  onThemeChange: (theme: ThemeMode) => void;
}

export function SettingsPanel({ theme, onThemeChange }: SettingsPanelProps) {
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
      setLoadError(userFacingAppErrorMessage(err, { fallbackTitle: "设置加载失败" }));
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
        message: userFacingAppErrorMessage(err, { fallbackTitle: "设置保存失败" }),
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
        message: userFacingAppErrorMessage(err, { fallbackTitle: "密钥清除失败" }),
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
        <Button
          variant="outline"
          onClick={() => void load()}
          type="button"
        >
          <RefreshCw size={16} /> 重试
        </Button>
      </section>
    );
  }

  const present = view?.api_key_present ?? false;
  const fingerprint = view?.api_key_fingerprint ?? "";
  const healthErrorCopy = healthStatus.kind === "error"
    ? userFacingErrorCopy(healthStatus.result.error, { statusCode: healthStatus.result.status_code })
    : null;

  return (
    <section className="p-5 rounded-lg border border-app-border bg-app-surface max-w-[1120px]" data-testid="settings-panel">
      <h3>设置 · LLM 服务</h3>
      <p className="section-copy">
        在本机保存 LLM 服务参数。密钥仅写在本机配置文件中，权限受限；
        界面只会显示是否已配置和指纹，不会回显明文。
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div className="flex flex-col gap-1 p-3 rounded-lg border border-app-border bg-app-surface min-h-[88px]">
          <span className="text-xs font-semibold text-app-muted">状态</span>
          <strong
            className={`text-sm font-medium truncate ${
              present || view?.api_key_source === "env"
                ? "text-app-success"
                : "text-app-warn"
            }`}
            title={apiKeySourceLabel(view?.api_key_source ?? "none")}
          >
            {apiKeySourceLabel(view?.api_key_source ?? "none")}
          </strong>
        </div>
        <div className="flex flex-col gap-1 p-3 rounded-lg border border-app-border bg-app-surface min-h-[88px]">
          <span className="text-xs font-semibold text-app-muted">密钥指纹</span>
          <code
            className="text-sm text-app-fg truncate font-mono"
            data-testid="api-key-fingerprint"
            title={present ? fingerprint : undefined}
          >
            {present ? fingerprint : "（未配置）"}
          </code>
        </div>
        <div className="flex flex-col gap-1 p-3 rounded-lg border border-app-border bg-app-surface min-h-[88px]">
          <span className="text-xs font-semibold text-app-muted">模型</span>
          <code className="text-sm text-app-fg truncate font-mono" title={view?.model ?? undefined}>
            {view?.model ?? "—"}
          </code>
        </div>
        <div className="flex flex-col gap-1 p-3 rounded-lg border border-app-border bg-app-surface min-h-[88px]">
          <span className="text-xs font-semibold text-app-muted">Base URL</span>
          <code
            className="text-sm text-app-fg truncate font-mono"
            title={view?.base_url ?? undefined}
          >
            {view?.base_url ?? "—"}
          </code>
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
            <Button
              variant="ghost"
              size="icon"
              aria-label={showKey ? "隐藏密钥" : "显示密钥"}
              onClick={() => setShowKey((prev) => !prev)}
              type="button"
            >
              {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
            </Button>
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
          <Button
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
          </Button>
          <Button
            variant="outline"
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
          </Button>
          <Button
            variant="destructive"
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
          </Button>
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
        <div className="settings-feedback err" data-testid="settings-health-status">
          <AlertTriangle size={14} />
          <span>{healthErrorCopy?.title ?? "连通失败"}：{healthErrorCopy?.message ?? "请检查配置后重试。"}</span>
          {healthErrorCopy?.detail && (
            <details>
              <summary>诊断详情</summary>
              <code>{healthErrorCopy.detail}</code>
            </details>
          )}
        </div>
      )}

      <div className="mt-6 pt-6 border-t border-app-border">
        <h4 className="text-sm font-semibold text-app-fg mb-3">外观</h4>
        <div className="theme-set" aria-label="主题" role="radiogroup">
          {THEME_OPTIONS.map(({ value, label, icon: Icon }) => {
            const disabled = !DARK_MODE_ENABLED && value !== "light";
            return (
              <button
                className={`theme-segment${theme === value ? " is-active" : ""}`}
                key={value}
                onClick={() => {
                  if (!disabled) onThemeChange(value);
                }}
                type="button"
                role="radio"
                aria-checked={theme === value}
                aria-disabled={disabled || undefined}
                disabled={disabled}
                title={disabled ? `${label}主题（暗色模式即将推出）` : `${label}主题`}
              >
                <Icon size={16} aria-hidden="true" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            );
          })}
        </div>
        <p className="text-xs text-app-soft mt-2">
          暗色模式正在开发中，当前仅浅色模式可用。
        </p>
      </div>
    </section>
  );
}
