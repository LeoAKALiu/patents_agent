import { AlertTriangle, CheckCircle2, CircleSlash, LockKeyhole } from "lucide-react";

import type { AgentDoctorReport, AgentProviderStatus } from "./api";

export type AgentProviderRole = "deliberation" | "formula";

export const requiredAgentProviderIds = ["codex", "gemini", "claude"];

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
    if (!provider.required && !provider.available) {
      selected.delete(provider.id);
    }
  }
  return providers.filter((provider) => selected.has(provider.id)).map((provider) => provider.id);
}

export function providerListForRole(doctor: AgentDoctorReport | null, role: AgentProviderRole): AgentProviderStatus[] {
  const providers = Object.values(doctor?.commands ?? {});
  return providers
    .filter((provider) => provider.required || provider.roles.includes(role))
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
        const canToggle = !provider.required && provider.available && !disabled;
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
              <span className={provider.available ? "status-badge" : "status-badge warn"}>
                {provider.available ? "可用" : "不可用"}
              </span>
              <span className={enabled ? "status-badge" : "status-badge muted"}>
                {provider.required ? "必选" : enabled ? "本轮启用" : "本轮未启用"}
              </span>
            </div>
            <p>{provider.available ? provider.path : `未找到命令：${provider.command}`}</p>
            <label className={canToggle ? "agent-toggle" : "agent-toggle disabled"}>
              <input
                checked={enabled}
                disabled={!canToggle}
                onChange={(event) => onToggleProvider(provider.id, event.currentTarget.checked)}
                type="checkbox"
              />
              <span>{provider.required ? "必选席不可关闭" : provider.available ? "加入本轮" : "不可用"}</span>
              {!provider.available && <CircleSlash size={15} />}
            </label>
          </article>
        );
      })}
      {providers.length === 0 && <p className="workflow-hint">暂无可用于该环节的 agent。</p>}
    </div>
  );
}
