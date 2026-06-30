import { type ReactNode } from "react";
import {
  Activity,
  CheckCircle2,
  CircleAlert,
  CircleHelp,
  Download,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, type BadgeProps } from "@/components/ui/badge";

type StatusVariant = "idle" | "busy" | "error" | "success" | "warning";

export interface ShellTopbarProps {
  /** Page title shown on the left side of the enterprise shell */
  title?: ReactNode;
  /** Secondary page copy shown under the title */
  subtitle?: ReactNode;
  /** Slot for the right side (actions, status, etc.) */
  actions?: ReactNode;
  /** Project selector (optional select element) */
  projectSelector?: ReactNode;
  /** Status indicator */
  statusLabel?: string;
  statusVariant?: StatusVariant;
  /** Export readiness indicator */
  exportStatusLabel?: string;
  exportStatusVariant?: StatusVariant;
  /** Backend connectivity indicator */
  backendStatus?: "unknown" | "online" | "offline";
  /** Optional detailed diagnostics trigger for the backend chip. */
  onOpenDiagnostics?: () => void;
  /** Refresh handler */
  onRefresh?: () => void;
  /** Extra elements after the main action row */
  extraActions?: ReactNode;
}

function badgeVariantFor(variant: StatusVariant): BadgeProps["variant"] {
  if (variant === "success") return "success";
  if (variant === "busy" || variant === "warning") return "warning";
  if (variant === "error") return "destructive";
  return "info";
}

function backendStatusMeta(status: "unknown" | "online" | "offline") {
  if (status === "online") {
    return { label: "后端在线", variant: "success" as const, icon: CheckCircle2 };
  }
  if (status === "offline") {
    return { label: "后端离线", variant: "error" as const, icon: CircleAlert };
  }
  return { label: "后端检测中", variant: "idle" as const, icon: CircleHelp };
}

export function ShellTopbar({
  title,
  subtitle,
  actions,
  projectSelector,
  statusLabel,
  statusVariant: statusV = "idle",
  exportStatusLabel,
  exportStatusVariant = "idle",
  backendStatus = "unknown",
  onOpenDiagnostics,
  onRefresh,
  extraActions,
}: ShellTopbarProps) {
  const backendMeta = backendStatusMeta(backendStatus);
  const BackendIcon = backendMeta.icon;
  const RunIcon = statusV === "busy" ? Loader2 : Activity;
  return (
    <header className="topbar">
      {(title || subtitle) && (
        <div className="topbar-main page-title">
          {title && <h1>{title}</h1>}
          {subtitle && <p>{subtitle}</p>}
        </div>
      )}

      <div className="top-actions">
        <div className="topbar-actions-group">
          {projectSelector}

          {exportStatusLabel && (
            <Badge
              variant={badgeVariantFor(exportStatusVariant)}
              className="topbar-status-chip"
            >
              <Download size={14} aria-hidden="true" />
              <span>{exportStatusLabel}</span>
            </Badge>
          )}

          {statusLabel && (
            <Badge variant={badgeVariantFor(statusV)} className="topbar-status-chip">
              <RunIcon
                size={14}
                aria-hidden="true"
                className={statusV === "busy" ? "animate-spin" : undefined}
              />
              <span>{statusLabel}</span>
            </Badge>
          )}

          {onOpenDiagnostics ? (
            <Button
              variant="outline"
              className="topbar-status-chip topbar-backend-button"
              onClick={onOpenDiagnostics}
              title="查看后端诊断"
              type="button"
            >
              <BackendIcon size={14} aria-hidden="true" />
              <span>{backendMeta.label}</span>
            </Button>
          ) : (
            <Badge
              variant={badgeVariantFor(backendMeta.variant)}
              className="topbar-status-chip"
              title={backendMeta.label}
            >
              <BackendIcon size={14} aria-hidden="true" />
              <span>{backendMeta.label}</span>
            </Badge>
          )}

          {actions}

          {onRefresh && (
            <Button
              variant="outline"
              size="icon"
              className="topbar-refresh-button"
              onClick={onRefresh}
              title="刷新运行状态"
              aria-label="刷新运行状态"
            >
              <RefreshCw size={16} aria-hidden="true" />
            </Button>
          )}
        </div>

        {extraActions}
      </div>
    </header>
  );
}
