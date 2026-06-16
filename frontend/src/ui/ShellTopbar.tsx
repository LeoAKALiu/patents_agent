import { type ReactNode } from "react";
import { Monitor, Moon, Sun } from "lucide-react";

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

function statusClass(variant: "idle" | "busy" | "error"): string {
  if (variant === "busy") return "tag tag-warn";
  if (variant === "error") return "tag tag-danger";
  return "tag tag-success";
}

export function ShellTopbar({
  title,
  subtitle,
  children,
  actions,
  projectSelector,
  statusLabel,
  statusVariant = "idle",
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
            <span className={statusClass(statusVariant)}>{statusLabel}</span>
          )}

          {actions}

          {onRefresh && (
            <button
              className="btn btn-secondary btn-icon"
              onClick={onRefresh}
              type="button"
              title="刷新运行状态"
              aria-label="刷新运行状态"
            >
              <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 6v5h-5" />
                <path d="M4 18v-5h5" />
                <path d="M18 11a6 6 0 0 0-10-4l-4 4" />
                <path d="M6 13a6 6 0 0 0 10 4l4-4" />
              </svg>
            </button>
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
