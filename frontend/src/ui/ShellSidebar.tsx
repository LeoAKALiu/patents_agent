import { type ReactNode } from "react";
import { Button } from "@/components/ui/button";

export interface ShellNavSection {
  id: string;
  label: string;
  icon?: ReactNode;
  description?: string;
}

export interface ShellSidebarProps {
  brandName?: string;
  brandSubtitle?: string;
  brandMark?: ReactNode;
  brandLogoSrc?: string | null;
  brandLogoAlt?: string;
  mainSections: ShellNavSection[];
  activeSectionId: string;
  onSelectSection: (id: string) => void;
  /** Slot for the footer area (health, project info, etc.) */
  footer?: ReactNode;
}

export function ShellSidebar({
  brandName = "权衡 GrantAtlas",
  brandSubtitle,
  brandMark,
  brandLogoSrc = "/logo.svg",
  brandLogoAlt = "权衡 GrantAtlas logo",
  mainSections,
  activeSectionId,
  onSelectSection,
  footer,
}: ShellSidebarProps) {
  return (
    <aside className="sidebar" aria-label="主导航">
      <div className="brand" aria-label={`${brandName} home`}>
        <span className="brand-mark">
          {brandMark ?? (brandLogoSrc ? <img className="brand-logo" src={brandLogoSrc} alt={brandLogoAlt} /> : null)}
        </span>
        <span>
          <strong>{brandName}</strong>
          {brandSubtitle && <span>{brandSubtitle}</span>}
        </span>
      </div>

      <nav className="nav-group" aria-label="主导航">
        {mainSections.map((section) => (
          <Button
            key={section.id}
            variant="ghost"
            size="default"
            className={`nav-link ${activeSectionId === section.id ? "is-active" : ""}`}
            onClick={() => onSelectSection(section.id)}
            title={section.description}
          >
            {section.icon}
            <span>{section.label}</span>
          </Button>
        ))}
      </nav>

      {footer && <div className="sidebar-footer">{footer}</div>}
    </aside>
  );
}
