import { AlertTriangle, Lock } from "lucide-react";
import { cn } from "./cn";

type RiskBannerProps = {
  message: string;
  variant?: "warning" | "error" | "info";
  className?: string;
};

const styles: Record<string, string> = {
  warning: "border-yellow-500/30 bg-yellow-500/5 text-yellow-300",
  error: "border-red-500/30 bg-red-500/5 text-red-300",
  info: "border-teal-500/30 bg-teal-500/5 text-teal-300",
};

export function RiskBanner({ message, variant = "warning", className }: RiskBannerProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 px-3 py-2 rounded-md border text-xs",
        styles[variant],
        className,
      )}
    >
      {variant === "error" ? (
        <Lock size={14} className="mt-0.5 flex-shrink-0" />
      ) : (
        <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
      )}
      <span>{message}</span>
    </div>
  );
}
