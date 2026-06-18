import { AlertTriangle, Info, LockKeyhole } from "@/lib/icons";
import { cn } from "./cn";

type RiskBannerProps = {
  message: string;
  variant?: "warning" | "error" | "info";
  className?: string;
};

const styles: Record<string, string> = {
  warning: "callout-warn",
  error: "callout-danger",
  info: "callout-info",
};

export function RiskBanner({ message, variant = "warning", className }: RiskBannerProps) {
  const Icon = variant === "error" ? LockKeyhole : variant === "info" ? Info : AlertTriangle;

  return (
    <div
      className={cn(
        "callout risk-banner",
        styles[variant],
        className,
      )}
    >
      <Icon size={16} className="risk-banner-icon" />
      <p>{message}</p>
    </div>
  );
}
