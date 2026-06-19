import { type ReactNode } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

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
  statusVariant?: "idle" | "busy" | "error";
  /** Refresh handler */
  onRefresh?: () => void;
  /** Extra elements after the main action row */
  extraActions?: ReactNode;
}

function statusChipClass(variant: "idle" | "busy" | "error"): string {
  if (variant === "busy") return "tag tag-warn";
  if (variant === "error") return "tag tag-danger";
  return "tag tag-info";
}

export function ShellTopbar({
  title,
  subtitle,
  actions,
  projectSelector,
  statusLabel,
  statusVariant: statusV = "idle",
  onRefresh,
  extraActions,
}: ShellTopbarProps) {
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

          {statusLabel && (
            <span className={`${statusChipClass(statusV)} topbar-status-chip`}>
              {statusLabel}
            </span>
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
