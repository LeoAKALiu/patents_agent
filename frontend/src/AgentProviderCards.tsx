import { AlertTriangle, CheckCircle2, CircleSlash, Clock, HelpCircle, LockKeyhole, XCircle } from "lucide-react";

import { Badge } from "@/components/primitives/Badge";
import type { AgentDoctorReport, AgentProviderStatus } from "./api";

export type AgentProviderRole = "deliberation" | "formula" | "post_review";

export const requiredAgentProviderIds = ["codex", "deepseek", "claude"];

function getAuthStatusDisplay(provider: AgentProviderStatus): { label: string; icon: React.ReactNode; variant: "success" | "warn" | "neutral" } {
  if (!provider.installed) {
    return { label: "未安装", icon: <XCircle size={14} />, variant: "warn" };
  }
  switch (provider.auth_status) {
    case "ready":
      return { label: "可用", icon: <CheckCircle2 size={14} />, variant: "success" };
    case "not_authenticated":
      return { label: "未登录/需认证", icon: <AlertTriangle size={14} />, variant: "warn" };
    case "timeout":
      return { label: "探测超时", icon: <Clock size={14} />, variant: "warn" };
    case "unavailable":
      return { label: "不可用", icon: <XCircle size={14} />, variant: "warn" };
    case "unknown":
    default:
      return { label: "状态未知", icon: <HelpCircle size={14} />, variant: "neutral" };
  }
}

function providerHint(provider: AgentProviderStatus): string {
  if (!provider.installed) return "未检测到 CLI，安装后可重新扫描。";
  if (provider.available) return "已就绪，可参与本轮任务。";
  if (provider.selectable) return "已检测到 CLI，调用状态将在运行时验证。";
  if (provider.auth_status === "not_authenticated") return "需要完成登录或凭据配置。";
  if (provider.auth_status === "timeout") return "状态探测超时，可稍后重试。";
  return "暂不可用于本轮任务。";
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
  if (providers.length === 0) {
    return <p className="workflow-hint">智能体诊断尚未刷新，请稍候或点击刷新。</p>;
  }
  return (
    <div className="agent-provider-grid my-3">
      {providers.map((provider) => {
        const enabled = provider.required || selectedProviders.includes(provider.id);
        const canToggle = !provider.required && provider.selectable && !disabled;
        const authDisplay = getAuthStatusDisplay(provider);
        return (
          <article
            className={[
              "agent-card grid gap-2 p-3 rounded-lg border bg-app-subtle",
              enabled
                ? "border-app-accent/40 shadow-[inset_3px_0_0_var(--action-primary)]"
                : "border-app-border",
            ].filter(Boolean).join(" ")}
            key={`${role}-${provider.id}`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <strong className="block text-app-fg text-sm truncate">{provider.label}</strong>
                <span className="block text-app-muted text-[11px] truncate">{provider.model_version || "模型版本未声明"}</span>
              </div>
              {provider.required ? (
                <LockKeyhole size={18} className="shrink-0" />
              ) : provider.available ? (
                <CheckCircle2 size={18} className="shrink-0" />
              ) : (
                <AlertTriangle size={18} className="shrink-0" />
              )}
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge variant={authDisplay.variant}>
                {authDisplay.icon}
                {authDisplay.label}
              </Badge>
              <Badge variant={enabled ? "success" : "neutral"}>
                {provider.required ? "必选" : enabled ? "本轮启用" : "本轮未启用"}
              </Badge>
            </div>
            <p className="text-app-muted text-[11px] leading-snug m-0">{providerHint(provider)}</p>
            {provider.diagnostic && !provider.selectable && (
              <p className="text-app-muted text-[11px] m-0">{provider.diagnostic}</p>
            )}
            {provider.repair_suggestion && !provider.selectable && (
              <p className="text-app-muted text-[11px] m-0">{provider.repair_suggestion}</p>
            )}
            <label className={`flex items-center gap-2 font-semibold text-xs ${canToggle ? "" : "opacity-50 cursor-not-allowed"}`}>
              <input
                checked={enabled}
                disabled={!canToggle}
                onChange={(event) => onToggleProvider(provider.id, event.currentTarget.checked)}
                type="checkbox"
                size={14}
              />
              <span>{provider.required ? "必选席不可关闭" : provider.selectable ? "加入本轮" : "不可用"}</span>
              {!provider.selectable && <CircleSlash size={15} />}
            </label>
          </article>
        );
      })}
    </div>
  );
}
