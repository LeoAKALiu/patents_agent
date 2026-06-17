import { type ReactNode } from "react";
import { Monitor, Moon, Sun, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export type ThemeMode = "auto" | "light" | "dark";

export interface ShellTopbarProps {
  title: string;
  subtitle?: string;
  /** Slot for the left side (page title area) */
  children?: ReactNode;
  /** Slot for the right side (actions, status, etc.) */
  actions?: ReactNode;
  /** Project selector (optional select element) */
  projectSelector?: ReactNode;
  /** Status indicator */
  statusLabel?: string;
  statusVariant?: "idle" | "busy" | "error";
  /** Theme state */
  theme: ThemeMode;
  onThemeChange: (theme: ThemeMode) => void;
  /** Refresh handler */
  onRefresh?: () => void;
  /** Extra elements after theme switch */
  extraActions?: ReactNode;
}

const THEME_OPTIONS: { value: ThemeMode; label: string; icon: typeof Sun }[] = [
  { value: "auto", label: "自动", icon: Monitor },
  { value: "light", label: "浅色", icon: Sun },
  { value: "dark", label: "深色", icon: Moon },
];

function statusVariant(variant: "idle" | "busy" | "error"): "success" | "warning" | "secondary" {
  if (variant === "busy") return "warning";
  if (variant === "error") return "secondary"; // red in legacy; we keep semantic
  return "success";
}

function statusChipVariant(variant: "idle" | "busy" | "error"): "default" | "warning" | "destructive" {
  if (variant === "busy") return "warning";
  if (variant === "error") return "destructive";
  return "default";
}

export function ShellTopbar({
  title,
  subtitle,
  children,
  actions,
  projectSelector,
  statusLabel,
  statusVariant: statusV = "idle",
  theme,
  onThemeChange,
  onRefresh,
  extraActions,
}: ShellTopbarProps) {
  return (
    <header className="topbar">
      <div className="page-title">
        {children || (
          <>
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
          </>
        )}
      </div>

      <div className="top-actions">
        <div className="topbar-actions-group">
          {projectSelector}

          {statusLabel && (
            <Badge variant={statusChipVariant(statusV)} className="text-xs">
              {statusLabel}
            </Badge>
          )}

          {actions}

          {onRefresh && (
            <Button
              variant="glass-soft"
              size="icon"
              onClick={onRefresh}
              title="刷新运行状态"
              aria-label="刷新运行状态"
            >
              <RefreshCw size={16} aria-hidden="true" />
            </Button>
          )}
        </div>

        <div className="theme-set" aria-label="主题" role="radiogroup">
          {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
            <button
              className={`theme-segment${theme === value ? " is-active" : ""}`}
              key={value}
              onClick={() => onThemeChange(value)}
              type="button"
              role="radio"
              aria-checked={theme === value}
              title={`${label}主题`}
            >
              <Icon size={16} aria-hidden="true" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {extraActions}
      </div>
    </header>
  );
}
