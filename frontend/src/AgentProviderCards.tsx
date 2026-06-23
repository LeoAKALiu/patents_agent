import { AlertTriangle, CheckCircle2, CircleSlash, Clock, HelpCircle, LockKeyhole, XCircle } from "lucide-react";

import { Badge } from "@/components/primitives/Badge";
import type { AgentDoctorReport, AgentProviderStatus } from "./api";

export type AgentProviderRole = "deliberation" | "formula" | "post_review";

export const requiredAgentProviderIds = ["codex", "deepseek", "claude"];
export const deliberationChairProviderId = "codex";
export const deliberationExpertSeatCount = 3;

type DeliberationExpertSelectionOptions = {
  autoFillMissing?: boolean;
};

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

function compactDiagnostic(value: string, limit = 130): string {
  const compact = value.replace(/\s+/g, " ").trim();
  return compact.length > limit ? `${compact.slice(0, limit)}...` : compact;
}

function isDeliberationCandidate(provider: AgentProviderStatus): boolean {
  return provider.id === deliberationChairProviderId || provider.roles.includes("deliberation");
}

function deliberationProviderList(doctor: AgentDoctorReport | null): AgentProviderStatus[] {
  return Object.values(doctor?.commands ?? {})
    .filter((provider) => provider.installed && isDeliberationCandidate(provider))
    .sort((a, b) => {
      if (a.id === deliberationChairProviderId) return -1;
      if (b.id === deliberationChairProviderId) return 1;
      const requiredIndexA = requiredAgentProviderIds.indexOf(a.id);
      const requiredIndexB = requiredAgentProviderIds.indexOf(b.id);
      if (requiredIndexA >= 0 || requiredIndexB >= 0) {
        return (requiredIndexA >= 0 ? requiredIndexA : 99) - (requiredIndexB >= 0 ? requiredIndexB : 99);
      }
      if (a.available !== b.available) return a.available ? -1 : 1;
      return a.label.localeCompare(b.label);
    });
}

export function normalizeDeliberationExpertSelection(
  doctor: AgentDoctorReport | null,
  selectedProviders: string[],
  options: DeliberationExpertSelectionOptions = {},
): string[] {
  const providers = deliberationProviderList(doctor);
  const selectableIds = new Set(providers.filter((provider) => provider.selectable).map((provider) => provider.id));
  const normalized: string[] = [];
  const autoFillMissing = options.autoFillMissing ?? true;

  if (selectableIds.has(deliberationChairProviderId) || doctor === null) {
    normalized.push(deliberationChairProviderId);
  }

  for (const providerId of selectedProviders) {
    if (providerId === deliberationChairProviderId || normalized.includes(providerId) || !selectableIds.has(providerId)) {
      continue;
    }
    normalized.push(providerId);
    if (normalized.length >= deliberationExpertSeatCount) return normalized;
  }

  if (!autoFillMissing) return normalized;

  for (const provider of providers) {
    if (provider.id === deliberationChairProviderId || normalized.includes(provider.id) || !provider.selectable) {
      continue;
    }
    normalized.push(provider.id);
    if (normalized.length >= deliberationExpertSeatCount) break;
  }

  return normalized;
}

export function normalizeDeliberationParticipantSelection(
  doctor: AgentDoctorReport | null,
  expertProviders: string[],
  selectedParticipants: string[],
): string[] {
  const expertSet = new Set(expertProviders);
  const selectableIds = new Set(
    deliberationProviderList(doctor)
      .filter((provider) => provider.selectable && !expertSet.has(provider.id))
      .map((provider) => provider.id),
  );
  return deliberationProviderList(doctor)
    .filter((provider) => selectedParticipants.includes(provider.id) && selectableIds.has(provider.id))
    .map((provider) => provider.id);
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
    <>
      <div className="agent-provider-grid">
        {providers.map((provider) => {
          const enabled = provider.required ? provider.selectable : selectedProviders.includes(provider.id);
          const canToggle = !provider.required && provider.selectable && !disabled;
          const authDisplay = getAuthStatusDisplay(provider);
          const membershipLabel = provider.required
            ? provider.available
              ? "必选"
              : "必选未就绪"
            : enabled
              ? "本轮启用"
              : "本轮未启用";
          return (
            <ProviderCard
              key={`${role}-${provider.id}`}
              provider={provider}
              enabled={enabled}
              locked={!provider.selectable}
              statusLabel={membershipLabel}
              footer={(
                <label className={`agent-provider-toggle ${canToggle ? "" : "is-disabled"}`}>
                  <input
                    checked={enabled}
                    disabled={!canToggle}
                    onChange={(event) => onToggleProvider(provider.id, event.currentTarget.checked)}
                    type="checkbox"
                    size={14}
                  />
                  <span className="agent-provider-toggle-label">
                    {provider.required ? (provider.selectable ? "必选席不可关闭" : "必选席暂不可用") : provider.selectable ? "加入本轮" : "不可用"}
                  </span>
                  {!provider.selectable && <CircleSlash size={15} aria-hidden="true" />}
                </label>
              )}
              authDisplay={authDisplay}
            />
          );
        })}
      </div>
      <AgentProviderDiagnostics providers={providers} />
    </>
  );
}

export function DeliberationAgentSelector({
  doctor,
  expertProviders,
  participantProviders,
  disabled = false,
  onToggleExpert,
  onToggleParticipant,
}: {
  doctor: AgentDoctorReport | null;
  expertProviders: string[];
  participantProviders: string[];
  disabled?: boolean;
  onToggleExpert: (providerId: string, enabled: boolean) => void;
  onToggleParticipant: (providerId: string, enabled: boolean) => void;
}) {
  const providers = deliberationProviderList(doctor);
  if (providers.length === 0) {
    return <p className="workflow-hint">正在扫描本机 agent CLI。刷新运行状态后，已安装的 agent 会出现在这里。</p>;
  }
  const expertSet = new Set(expertProviders);
  const participantSet = new Set(participantProviders);
  const expertFull = expertProviders.length >= deliberationExpertSeatCount;

  return (
    <section className="deliberation-agent-selector" aria-label="会审专家席位">
      <div className="agent-seat-summary">
        <Badge variant={expertProviders.length >= deliberationExpertSeatCount ? "success" : "warn"}>
          决策专家 {expertProviders.length}/{deliberationExpertSeatCount}
        </Badge>
        <span>主席 Codex 固定；另外 2 席由用户选择，参会专家仅供主席参考。</span>
      </div>
      <div className="agent-provider-grid">
        {providers.map((provider) => {
          const isChair = provider.id === deliberationChairProviderId;
          const isExpert = expertSet.has(provider.id);
          const isParticipant = participantSet.has(provider.id);
          const authDisplay = getAuthStatusDisplay(provider);
          const canSelectExpert = !disabled && !isChair && provider.selectable && (isExpert || !expertFull);
          const canSelectParticipant = !disabled && !isChair && provider.selectable && !isExpert;
          const statusLabel = isChair
            ? provider.selectable
              ? "主席固定"
              : "主席未就绪"
            : isExpert
              ? "决策专家"
              : isParticipant
                ? "参会专家"
                : provider.selectable
                  ? "可选择"
                  : "必选未就绪";
          return (
            <ProviderCard
              key={`deliberation-${provider.id}`}
              provider={provider}
              enabled={isChair || isExpert || isParticipant}
              locked={!provider.selectable}
              statusLabel={statusLabel}
              authDisplay={authDisplay}
              footer={(
                <div className="agent-seat-actions">
                  {isChair ? (
                    <span className="agent-provider-toggle-label">主席固定</span>
                  ) : (
                    <>
                      <label className={`agent-provider-toggle ${canSelectExpert ? "" : "is-disabled"}`}>
                        <input
                          checked={isExpert}
                          disabled={!canSelectExpert}
                          onChange={(event) => onToggleExpert(provider.id, event.currentTarget.checked)}
                          type="checkbox"
                          size={14}
                        />
                        <span className="agent-provider-toggle-label">{isExpert ? "决策专家" : "设为专家"}</span>
                      </label>
                      <label className={`agent-provider-toggle ${canSelectParticipant ? "" : "is-disabled"}`}>
                        <input
                          checked={isParticipant}
                          disabled={!canSelectParticipant}
                          onChange={(event) => onToggleParticipant(provider.id, event.currentTarget.checked)}
                          type="checkbox"
                          size={14}
                        />
                        <span className="agent-provider-toggle-label">参会</span>
                      </label>
                    </>
                  )}
                  {!provider.selectable && <CircleSlash size={15} aria-hidden="true" />}
                </div>
              )}
            />
          );
        })}
      </div>
      <AgentProviderDiagnostics providers={providers} />
    </section>
  );
}

function ProviderCard({
  provider,
  enabled,
  locked,
  statusLabel,
  authDisplay,
  footer,
}: {
  provider: AgentProviderStatus;
  enabled: boolean;
  locked: boolean;
  statusLabel: string;
  authDisplay: { label: string; icon: React.ReactNode; variant: "success" | "warn" | "neutral" };
  footer: React.ReactNode;
}) {
  return (
    <article
      className={[
        "agent-provider-card",
        enabled ? "is-enabled" : "",
        locked ? "is-locked" : "",
      ].filter(Boolean).join(" ")}
    >
      <div className="agent-provider-head">
        <div className="agent-provider-title">
          <strong>{provider.label}</strong>
          <span>{provider.model_version || provider.command || "模型版本未声明"}</span>
        </div>
        {provider.id === deliberationChairProviderId || provider.required ? (
          <LockKeyhole size={18} aria-hidden="true" />
        ) : provider.available ? (
          <CheckCircle2 size={18} aria-hidden="true" />
        ) : (
          <AlertTriangle size={18} aria-hidden="true" />
        )}
      </div>
      <div className="agent-provider-status">
        <Badge variant={authDisplay.variant}>
          {authDisplay.icon}
          {authDisplay.label}
        </Badge>
        <Badge variant={enabled ? "success" : "neutral"}>
          <span>{statusLabel}</span>
        </Badge>
      </div>
      <p className="agent-provider-copy">{providerHint(provider)}</p>
      {footer}
    </article>
  );
}

function AgentProviderDiagnostics({ providers }: { providers: AgentProviderStatus[] }) {
  const diagnostics = providers.filter((provider) => !provider.selectable && (provider.diagnostic || provider.repair_suggestion));
  if (diagnostics.length === 0) return null;
  return (
    <div className="agent-provider-diagnostics" aria-label="agent 诊断">
      {diagnostics.slice(0, 4).map((provider) => (
        <p key={`diagnostic-${provider.id}`}>
          <strong>{provider.label}</strong>
          {provider.diagnostic ? `：${compactDiagnostic(provider.diagnostic)}` : ""}
          {provider.repair_suggestion ? ` 建议：${compactDiagnostic(provider.repair_suggestion, 90)}` : ""}
        </p>
      ))}
    </div>
  );
}
