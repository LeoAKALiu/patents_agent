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
    <div className="flex h-10 min-w-0 items-center justify-between gap-3">
      <span className="min-w-0 flex-1 truncate text-xs text-app-muted">{label}</span>
      <div className="flex min-w-0 max-w-[7.25rem] shrink-0 justify-end overflow-hidden [&>*]:min-w-0 [&>*]:max-w-full [&>*]:truncate">
        {children}
      </div>
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
    <div className="grid min-w-0 max-w-full gap-2.5 overflow-hidden">
      <div className="min-w-0 max-w-full overflow-hidden rounded-lg border border-app-border bg-app-surface p-3">
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

      <div className="min-w-0 max-w-full overflow-hidden rounded-lg border border-app-border bg-app-surface p-3">
        <h3 className="text-xs font-semibold text-app-muted mb-1">模型与智能体</h3>
        <div className="grid min-w-0">
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
