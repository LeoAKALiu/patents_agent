import { Fragment } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ProjectRecord, Health, AgentDoctorReport, RuntimeDiagnostics } from "@/api";

export interface SystemStatusPanelProps {
  selectedProject?: ProjectRecord | null;
  health?: Health | null;
  agentDoctor?: AgentDoctorReport | null;
  agentRunModeLabel?: (mode: string) => string;
  /**
   * Optional diagnostics block from the Tauri sidecar.  When the page is
   * running outside Tauri (web dev / tests) the panel falls back to the
   * fields carried by the backend `/api/health` payload.
   */
  runtimeDiagnostics?: RuntimeDiagnostics | null;
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

function dataDirSourceLabel(source: string | undefined): string {
  switch (source) {
    case "explicit":
      return "显式传参";
    case "default":
      return "Pydantic 默认";
    case "app_data_dir":
      return "Tauri 应用目录";
    case "PATENTAGENT_BACKEND_DATA_DIR":
      return "覆盖变量";
    case "DATA_DIR":
      return "DATA_DIR";
    default:
      return source ?? "—";
  }
}

export function SystemStatusPanel({
  selectedProject,
  health,
  agentDoctor,
  agentRunModeLabel = (mode) => mode,
  runtimeDiagnostics = null,
  onRefresh,
}: SystemStatusPanelProps) {
  // Prefer the Rust-side diagnostics when running inside Tauri: it
  // carries the resolved `app_path` and `instance_id` that the
  // Python `/api/health` does not.  Fall back to the backend payload
  // for the browser dev server and tests.
  const dataDir = runtimeDiagnostics?.data_dir ?? health?.data_dir ?? "";
  const dataDirSource = runtimeDiagnostics?.data_dir_source ?? health?.data_dir_source ?? "";
  const qaProfile = runtimeDiagnostics?.qa_profile ?? health?.qa_profile ?? false;
  const instanceId = runtimeDiagnostics?.instance_id ?? health?.instance_id ?? null;
  const backendPort =
    runtimeDiagnostics?.backend_port ?? health?.backend_port ?? null;
  const appPath = runtimeDiagnostics?.app_path ?? health?.app_path ?? null;
  const backendHealthUrl = runtimeDiagnostics?.backend_health_url ?? null;

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

      <div className="p-3 rounded-lg border border-app-border bg-app-surface">
        <h3 className="text-xs font-semibold text-app-muted mb-1">数据目录与实例</h3>
        <div className="grid">
          <StatusRow label="数据目录来源">
            <Badge
              variant={qaProfile ? "warning" : "secondary"}
              className="min-w-[4.5em] justify-center"
              title={dataDir || ""}
            >
              {dataDirSourceLabel(dataDirSource)}
            </Badge>
          </StatusRow>
          <StatusRow label="QA 模式">
            <Badge
              variant={qaProfile ? "warning" : "secondary"}
              className="min-w-[4.5em] justify-center"
            >
              {qaProfile ? "开启" : "关闭"}
            </Badge>
          </StatusRow>
          <StatusRow label="后端端口">
            <span className="text-xs text-app-muted font-mono">
              {backendPort != null ? backendPort : "—"}
            </span>
          </StatusRow>
          {instanceId ? (
            <StatusRow label="实例 ID">
              <span
                className="text-[10px] text-app-muted font-mono truncate max-w-[12rem]"
                title={instanceId}
              >
                {instanceId}
              </span>
            </StatusRow>
          ) : null}
          {dataDir ? (
            <StatusRow label="数据目录">
              <span
                className="text-[10px] text-app-muted font-mono truncate max-w-[14rem]"
                title={dataDir}
              >
                {dataDir}
              </span>
            </StatusRow>
          ) : null}
          {appPath ? (
            <StatusRow label="Tauri 应用目录">
              <span
                className="text-[10px] text-app-muted font-mono truncate max-w-[14rem]"
                title={appPath}
              >
                {appPath}
              </span>
            </StatusRow>
          ) : null}
          {backendHealthUrl ? (
            <StatusRow label="健康检查">
              <span
                className="text-[10px] text-app-muted font-mono truncate max-w-[14rem]"
                title={backendHealthUrl}
              >
                {backendHealthUrl}
              </span>
            </StatusRow>
          ) : null}
        </div>
        {/* Hidden helper that explicitly marks when only the backend
            payload is available so QA logs make the source clear. */}
        {!runtimeDiagnostics && health?.data_dir_source ? (
          <p className="mt-2 text-[10px] text-app-muted">
            数据来源：后端 /api/health · 标签 {health.data_dir_source}
            {health.instance_id ? ` · 实例 ${health.instance_id}` : ""}
          </p>
        ) : null}
        {runtimeDiagnostics ? <Fragment /> : null}
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