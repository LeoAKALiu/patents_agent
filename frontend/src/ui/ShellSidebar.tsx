import { type ReactNode } from "react";

export interface ShellNavSection {
  id: string;
  label: string;
  icon?: ReactNode;
  description?: string;
}

export interface ShellSidebarProps {
  brandName?: string;
  brandSubtitle?: string;
  brandMark?: string;
  mainSections: ShellNavSection[];
  activeSectionId: string;
  onSelectSection: (id: string) => void;
  keySections?: ShellNavSection[];
  onSelectKeySection?: (id: string) => void;
  /** Slot for the footer area (health, project info, etc.) */
  footer?: ReactNode;
}

export function ShellSidebar({
  brandName = "PatentAgent",
  brandSubtitle = "授权导向专利工程系统",
  brandMark = "PA",
  mainSections,
  activeSectionId,
  onSelectSection,
  keySections,
  onSelectKeySection,
  footer,
}: ShellSidebarProps) {
  return (
    <aside className="sidebar" aria-label="主导航">
      <div className="brand" aria-label={`${brandName} home`}>
        <span className="brand-mark">{brandMark}</span>
        <span>
          <strong>{brandName}</strong>
          <span>{brandSubtitle}</span>
        </span>
      </div>

      <nav className="nav-group" aria-label="主导航">
        <div className="nav-label">Main</div>
        {mainSections.map((section) => (
          <button
            className={`nav-link${activeSectionId === section.id ? " is-active" : ""}`}
            key={section.id}
            onClick={() => onSelectSection(section.id)}
            type="button"
            title={section.description}
          >
            {section.icon}
            <span>{section.label}</span>
          </button>
        ))}
      </nav>

      {keySections && keySections.length > 0 && (
        <nav className="nav-group" aria-label="关键节点">
          <div className="nav-label">关键节点</div>
          {keySections.map((section) => (
            <button
              className={`nav-link${activeSectionId === section.id ? " is-active" : ""}`}
              key={section.id}
              onClick={() => onSelectKeySection?.(section.id)}
              type="button"
              title={section.description}
            >
              {section.icon}
              <span>{section.label}</span>
            </button>
          ))}
        </nav>
      )}

      {footer && <div className="sidebar-footer">{footer}</div>}
    </aside>
  );
}
