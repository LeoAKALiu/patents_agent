import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ProjectRecord, Health, AgentDoctorReport } from "@/api";

export interface SystemStatusPanelProps {
  selectedProject?: ProjectRecord | null;
  health?: Health | null;
  agentDoctor?: AgentDoctorReport | null;
  agentRunModeLabel?: (mode: string) => string;
  onRefresh?: () => void;
}

function StatusRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 h-10 min-w-0">
      <span className="text-xs text-app-muted truncate">{label}</span>
      {children}
    </div>
  );
}

export function SystemStatusPanel({
  selectedProject,
  health,
  agentDoctor,
  agentRunModeLabel = (mode) => mode,
  onRefresh,
}: SystemStatusPanelProps) {
  return (
    <div className="grid gap-2.5">
      <div className="p-3 rounded-lg border border-app-border bg-app-surface">
        <h3 className="text-xs font-semibold text-app-muted mb-1">当前项目</h3>
        <StatusRow label={selectedProject?.name ?? "未选择"}>
          {selectedProject?.package ? (
            <Badge variant="info" className="min-w-[4.5em] justify-center">
              已有初稿
            </Badge>
          ) : (
            <Badge variant="secondary" className="min-w-[4.5em] justify-center">
              新建中
            </Badge>
          )}
        </StatusRow>
      </div>

      <div className="p-3 rounded-lg border border-app-border bg-app-surface">
        <h3 className="text-xs font-semibold text-app-muted mb-1">模型与智能体</h3>
        <div className="grid">
          <StatusRow label="基础模型">
            {health?.llm_configured ? (
              <Badge variant="success" className="min-w-[4.5em] justify-center">
                可用
              </Badge>
            ) : (
              <Badge variant="destructive" className="min-w-[4.5em] justify-center">
                未配置
              </Badge>
            )}
          </StatusRow>
          <StatusRow label="智能体">
            {agentDoctor?.status === "blocked" ? (
              <Badge variant="warning" className="min-w-[4.5em] justify-center">
                {agentRunModeLabel(agentDoctor?.run_mode ?? "unknown")}
              </Badge>
            ) : (
              <Badge variant="success" className="min-w-[4.5em] justify-center">
                {agentRunModeLabel(agentDoctor?.run_mode ?? "unknown")}
              </Badge>
            )}
          </StatusRow>
          <StatusRow label="内部痕迹检查">
            <Badge variant="success" className="min-w-[4.5em] justify-center">
              可用
            </Badge>
          </StatusRow>
        </div>
      </div>

      {onRefresh && (
        <Button variant="outline" onClick={onRefresh} type="button" className="w-full">
          <RefreshCw size={14} />
          <span>刷新运行状态</span>
        </Button>
      )}
    </div>
  );
}
