import { type HTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/cn";

type Tone = "default" | "accent" | "info" | "success" | "warn" | "danger";

export function SectionHead({
  title,
  description,
  actions,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className={cn("section-head", className)} {...props}>
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {actions}
    </div>
  );
}

export function SettingsGroup({
  title,
  description,
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  title?: ReactNode;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className={cn("settings-group", className)} {...props}>
      {(title || description) && (
        <div className="settings-group-header">
          {title && <h3>{title}</h3>}
          {description && <p>{description}</p>}
        </div>
      )}
      {children}
    </section>
  );
}

export function InfoCard({
  icon,
  title,
  description,
  meta,
  action,
  tone = "default",
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  meta?: ReactNode;
  action?: ReactNode;
  tone?: Tone;
}) {
  return (
    <article className={cn("info-card", !icon && "info-card-no-icon", className)} {...props}>
      {icon && <div className={cn("info-card-icon", tone !== "default" && tone)}>{icon}</div>}
      <div className="info-card-body">
        <strong>{title}</strong>
        {description && <p>{description}</p>}
        {meta && <div className="meta-row">{meta}</div>}
        {children}
      </div>
      {action}
    </article>
  );
}

export function StatusStrip({
  items,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  items: Array<{ label: ReactNode; value: ReactNode }>;
}) {
  return (
    <section className={cn("status-strip", className)} {...props}>
      {items.map((item, index) => (
        <StatusTile key={index} label={item.label} value={item.value} />
      ))}
    </section>
  );
}

export function StatusTile({
  label,
  value,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  label: ReactNode;
  value: ReactNode;
}) {
  return (
    <div className={cn("status-tile", className)} {...props}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function BoundaryCard({
  title,
  description,
  tone = "default",
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  title: ReactNode;
  description?: ReactNode;
  tone?: "default" | "official" | "internal" | "external";
}) {
  return (
    <article className={cn("boundary-card", tone !== "default" && tone, className)} {...props}>
      <strong>{title}</strong>
      {description && <p>{description}</p>}
    </article>
  );
}

export function ActionDock({
  meta,
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  meta?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={cn("action-dock", className)} {...props}>
      {meta && <div className="meta">{meta}</div>}
      {children}
    </div>
  );
}
