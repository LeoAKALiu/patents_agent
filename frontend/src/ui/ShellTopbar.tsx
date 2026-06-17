import { type ReactNode } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export interface ShellTopbarProps {
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

function statusChipVariant(variant: "idle" | "busy" | "error"): "default" | "warning" | "destructive" {
  if (variant === "busy") return "warning";
  if (variant === "error") return "destructive";
  return "default";
}

export function ShellTopbar({
  actions,
  projectSelector,
  statusLabel,
  statusVariant: statusV = "idle",
  onRefresh,
  extraActions,
}: ShellTopbarProps) {
  return (
    <header className="topbar">
      <div className="top-actions">
        <div className="topbar-actions-group">
          {projectSelector}

          {statusLabel && (
            <Badge
              variant={statusChipVariant(statusV)}
              className="h-10 px-3 text-xs flex items-center"
            >
              {statusLabel}
            </Badge>
          )}

          {actions}

          {onRefresh && (
            <Button
              variant="outline"
              size="icon"
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
