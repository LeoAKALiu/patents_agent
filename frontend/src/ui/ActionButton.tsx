import { cn } from "./cn";

type ActionButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  loading?: boolean;
  icon?: React.ReactNode;
};

const variantStyles: Record<string, string> = {
  primary:
    "bg-teal-600 hover:bg-teal-500 text-white border-transparent shadow-sm",
  secondary:
    "bg-slate-700 hover:bg-slate-600 text-slate-200 border-slate-700/50 hover:border-slate-600",
  danger:
    "bg-red-600/20 hover:bg-red-600/30 text-red-400 border-red-500/20",
  ghost:
    "bg-transparent hover:bg-slate-800 text-slate-400 border-transparent",
};

export function ActionButton({
  variant = "primary",
  loading,
  icon,
  children,
  className,
  disabled,
  ...rest
}: ActionButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-w-0 max-w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-center text-sm font-medium whitespace-normal break-words",
        "border transition-colors duration-150",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        variantStyles[variant],
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon ? (
        icon
      ) : null}
      {children}
    </button>
  );
}
