import { AlertTriangle, CheckCircle2, CircleSlash, Clock, HelpCircle, LockKeyhole, XCircle } from "lucide-react";

import type { AgentDoctorReport, AgentProviderStatus } from "./api";

export type AgentProviderRole = "deliberation" | "formula" | "post_review";

export const requiredAgentProviderIds = ["codex", "gemini", "claude"];

function getAuthStatusDisplay(provider: AgentProviderStatus): { label: string; icon: React.ReactNode; variant: string } {
  if (!provider.installed) {
    return { label: "未安装", icon: <XCircle size={14} />, variant: "warn" };
  }
  switch (provider.auth_status) {
    case "ready":
      return { label: "可用", icon: <CheckCircle2 size={14} />, variant: "ok" };
    case "not_authenticated":
      return { label: "未登录/需认证", icon: <AlertTriangle size={14} />, variant: "warn" };
    case "timeout":
      return { label: "探测超时", icon: <Clock size={14} />, variant: "warn" };
    case "unavailable":
      return { label: "不可用", icon: <XCircle size={14} />, variant: "warn" };
    case "unknown":
    default:
      return { label: "状态未知", icon: <HelpCircle size={14} />, variant: "muted" };
  }
}

export function normalizeAgentSelection(
  doctor: AgentDoctorReport | null,
  selectedProviders: string[],
  role: AgentProviderRole,
): string[] {
  const providers = providerListForRole(doctor, role);
  const validProviderIds = new Set(providers.map((provider) => provider.id));
  const requiredProviderIds = providers.filter((provider) => provider.required).map((provider) => provider.id);
  const selected = new Set([...requiredProviderIds, ...selectedProviders.filter((providerId) => validProviderIds.has(providerId))]);
  for (const provider of providers) {
    if (!provider.required && !provider.selectable) {
      selected.delete(provider.id);
    }
  }
  return providers.filter((provider) => selected.has(provider.id)).map((provider) => provider.id);
}

export function providerListForRole(doctor: AgentDoctorReport | null, role: AgentProviderRole): AgentProviderStatus[] {
  const providerRole = role === "post_review" ? "deliberation" : role;
  const providers = Object.values(doctor?.commands ?? {});
  return providers
    .filter((provider) => provider.required || provider.roles.includes(providerRole))
    .sort((a, b) => {
      const requiredIndexA = requiredAgentProviderIds.indexOf(a.id);
      const requiredIndexB = requiredAgentProviderIds.indexOf(b.id);
      if (requiredIndexA >= 0 || requiredIndexB >= 0) {
        return (requiredIndexA >= 0 ? requiredIndexA : 99) - (requiredIndexB >= 0 ? requiredIndexB : 99);
      }
      if (a.required !== b.required) return a.required ? -1 : 1;
      if (a.available !== b.available) return a.available ? -1 : 1;
      return a.label.localeCompare(b.label);
    });
}

export function AgentProviderCards({
  doctor,
  selectedProviders,
  role,
  disabled = false,
  onToggleProvider,
}: {
  doctor: AgentDoctorReport | null;
  selectedProviders: string[];
  role: AgentProviderRole;
  disabled?: boolean;
  onToggleProvider: (providerId: string, enabled: boolean) => void;
}) {
  const providers = providerListForRole(doctor, role);
  if (!doctor) {
    return <p className="workflow-hint">Agent doctor 尚未刷新。</p>;
  }
  return (
    <div className="agent-card-grid">
      {providers.map((provider) => {
        const enabled = provider.required || selectedProviders.includes(provider.id);
        const canToggle = !provider.required && provider.selectable && !disabled;
        const authDisplay = getAuthStatusDisplay(provider);
        return (
          <article
            className={[
              "agent-card",
              enabled ? "enabled" : "",
              provider.required ? "required" : "",
              provider.available ? "available" : "missing",
            ].filter(Boolean).join(" ")}
            key={`${role}-${provider.id}`}
          >
            <div className="agent-card-main">
              <div>
                <strong>{provider.label}</strong>
                <span>{provider.model_version || "模型版本未声明"}</span>
              </div>
              {provider.required ? (
                <LockKeyhole size={18} />
              ) : provider.available ? (
                <CheckCircle2 size={18} />
              ) : (
                <AlertTriangle size={18} />
              )}
            </div>
            <div className="agent-card-meta">
              <span className={`status-badge ${authDisplay.variant}`}>
                {authDisplay.icon}
                {authDisplay.label}
              </span>
              <span className={enabled ? "status-badge" : "status-badge muted"}>
                {provider.required ? "必选" : enabled ? "本轮启用" : "本轮未启用"}
              </span>
            </div>
            <p className="agent-card-path">
              {provider.installed ? provider.path : `未找到命令：${provider.command}`}
            </p>
            {provider.diagnostic && (
              <p className="agent-card-diagnostic">{provider.diagnostic}</p>
            )}
            {provider.repair_suggestion && !provider.selectable && (
              <p className="agent-card-repair">{provider.repair_suggestion}</p>
            )}
            <label className={canToggle ? "agent-toggle" : "agent-toggle disabled"}>
              <input
                checked={enabled}
                disabled={!canToggle}
                onChange={(event) => onToggleProvider(provider.id, event.currentTarget.checked)}
                type="checkbox"
              />
              <span>{provider.required ? "必选席不可关闭" : provider.selectable ? "加入本轮" : "不可用"}</span>
              {!provider.selectable && <CircleSlash size={15} />}
            </label>
          </article>
        );
      })}
      {providers.length === 0 && <p className="workflow-hint">暂无可用于该环节的 agent。</p>}
    </div>
  );
}
