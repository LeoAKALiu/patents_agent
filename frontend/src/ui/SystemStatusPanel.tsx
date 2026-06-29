import { Badge } from "@/components/ui/badge";
import type { ProjectRecord, Health, AgentDoctorReport } from "@/api";

export interface SystemStatusPanelProps {
  selectedProject?: ProjectRecord | null;
  health?: Health | null;
  agentDoctor?: AgentDoctorReport | null;
  backendStatus?: "unknown" | "online" | "offline";
  projectListStatus?: "idle" | "loading" | "ready" | "failed";
  agentRunModeLabel?: (mode: string) => string;
  onRefresh?: () => void;
}

function StatusRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="system-status-row">
      <span>{label}</span>
      <div>
        {children}
      </div>
    </div>
  );
}

function modelStatus(
  health: Health | null | undefined,
  backendStatus: "unknown" | "online" | "offline",
): { label: string; variant: "success" | "secondary" | "destructive" } {
  if (backendStatus === "offline") return { label: "离线", variant: "destructive" };
  if (!health) return { label: "检测中", variant: "secondary" };
  if (health.llm_configured) return { label: "可用", variant: "success" };
  return { label: "未配置", variant: "destructive" };
}

function agentStatus(
  agentDoctor: AgentDoctorReport | null | undefined,
  backendStatus: "unknown" | "online" | "offline",
  agentRunModeLabel: (mode: string) => string,
): { label: string; variant: "success" | "warning" | "secondary" | "destructive" } {
  if (backendStatus === "offline") return { label: "离线", variant: "destructive" };
  if (!agentDoctor) return { label: "检测中", variant: "secondary" };
  if (agentDoctor.status === "ready") return { label: "可用", variant: "success" };
  if (agentDoctor.status === "degraded") {
    return { label: agentRunModeLabel(agentDoctor.run_mode), variant: "warning" };
  }
  return { label: "离线", variant: "destructive" };
}

function backendLabel(
  backendStatus: "unknown" | "online" | "offline",
): { label: string; variant: "success" | "secondary" | "destructive" } {
  if (backendStatus === "online") return { label: "在线", variant: "success" };
  if (backendStatus === "offline") return { label: "离线", variant: "destructive" };
  return { label: "检测中", variant: "secondary" };
}

export function SystemStatusPanel({
  health,
  agentDoctor,
  backendStatus = "unknown",
  projectListStatus = "idle",
  agentRunModeLabel = (mode) => mode,
}: SystemStatusPanelProps) {
  const model = modelStatus(health, backendStatus);
  const agents = agentStatus(agentDoctor, backendStatus, agentRunModeLabel);
  const backend = backendLabel(backendStatus);
  return (
    <div className="system-status-compact">
      <StatusRow label="模型">
        <Badge variant={model.variant}>{model.label}</Badge>
      </StatusRow>
      <StatusRow label="智能体">
        <Badge variant={agents.variant}>{agents.label}</Badge>
      </StatusRow>
      <StatusRow label="后端">
        <Badge variant={backend.variant} aria-label={`后端${backend.label}`}>
          {backend.label}
        </Badge>
      </StatusRow>

      <details className="system-status-diagnostics">
        <summary>查看诊断</summary>
        <dl>
          <div>
            <dt>模型名称</dt>
            <dd>{health?.model || "未检测"}</dd>
          </div>
          <div>
            <dt>向量模型</dt>
            <dd>{health?.embedding_model || "未检测"}</dd>
          </div>
          <div>
            <dt>数据目录</dt>
            <dd>{health?.data_dir || "未检测"}</dd>
          </div>
          <div>
            <dt>项目列表</dt>
            <dd>{projectListStatus === "failed" ? "加载失败" : "正常"}</dd>
          </div>
        </dl>
      </details>
    </div>
  );
}
