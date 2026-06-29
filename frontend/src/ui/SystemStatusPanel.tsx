import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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

function projectListLabel(projectListStatus: "idle" | "loading" | "ready" | "failed"): string {
  if (projectListStatus === "failed") return "加载失败";
  if (projectListStatus === "loading") return "加载中";
  if (projectListStatus === "idle") return "未加载";
  return "正常";
}

export function SystemStatusPanel({
  health,
  agentDoctor,
  backendStatus = "unknown",
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
    </div>
  );
}

export interface SystemDiagnosticsDialogProps extends SystemStatusPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SystemDiagnosticsDialog({
  open,
  onOpenChange,
  health,
  agentDoctor,
  backendStatus = "unknown",
  projectListStatus = "idle",
  agentRunModeLabel = (mode) => mode,
}: SystemDiagnosticsDialogProps) {
  const backend = backendLabel(backendStatus);
  const agents = agentStatus(agentDoctor, backendStatus, agentRunModeLabel);
  const agentMode = agentDoctor ? agentRunModeLabel(agentDoctor.run_mode) : "未检测";
  const rows = [
    ["后端状态", backend.label],
    ["项目列表", projectListLabel(projectListStatus)],
    ["模型名称", health?.model || "未检测"],
    ["向量模型", health?.embedding_model || "未检测"],
    ["数据目录", health?.data_dir || "未检测"],
    ["智能体状态", agents.label],
  ];

  if (agentMode !== agents.label) {
    rows.push(["智能体模式", agentMode]);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="system-diagnostics-dialog">
        <DialogHeader>
          <DialogTitle>后端诊断</DialogTitle>
          <DialogDescription>当前后端连接、模型配置与智能体运行摘要。</DialogDescription>
        </DialogHeader>
        <dl className="system-diagnostics-list">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </DialogContent>
    </Dialog>
  );
}
