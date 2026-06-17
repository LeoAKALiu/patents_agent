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
    <aside
      className="sidebar sticky top-0 flex flex-col h-screen py-[18px] px-[14px] border-r border-app-border bg-app-surface overflow-y-auto"
      aria-label="主导航"
    >
      <div className="brand flex items-center gap-2.5 px-2 pb-[18px] pt-1" aria-label={`${brandName} home`}>
        <span className="brand-mark grid place-items-center w-[34px] h-[34px] rounded-[10px] bg-action-primary/10 border border-action-primary/50 text-app-fg font-mono font-extrabold">
          {brandMark}
        </span>
        <span>
          <strong className="block text-[15px] font-semibold tracking-[-0.01em]">{brandName}</strong>
          <span className="block text-app-soft text-xs">{brandSubtitle}</span>
        </span>
      </div>

      <nav className="nav-group grid gap-1 mb-[18px]" aria-label="主导航">
        <div className="nav-label pt-3 pb-1.5 px-2.5 text-app-soft text-[11px] font-bold">Main</div>
        {mainSections.map((section) => (
          <Button
            key={section.id}
            variant="ghost"
            size="default"
            className={`nav-link flex items-center gap-2.5 min-h-[44px] px-2.5 py-2 w-full justify-start rounded-md text-[13px] font-normal transition-colors ${
              activeSectionId === section.id
                ? "is-active text-app-fg bg-action-primary/10 border border-action-primary/50"
                : "text-app-muted border-transparent hover:bg-app-subtle hover:text-app-fg"
            }`}
            onClick={() => onSelectSection(section.id)}
            title={section.description}
          >
            {section.icon}
            <span>{section.label}</span>
          </Button>
        ))}
      </nav>

      {keySections && keySections.length > 0 && (
        <nav className="nav-group grid gap-1 mb-[18px]" aria-label="关键节点">
          <div className="nav-label pt-3 pb-1.5 px-2.5 text-app-soft text-[11px] font-bold">关键节点</div>
          {keySections.map((section) => (
            <Button
              key={section.id}
              variant="ghost"
              size="default"
              className={`flex items-center gap-2.5 min-h-[44px] px-2.5 py-2 w-full justify-start rounded-md text-[13px] font-normal transition-colors ${
                activeSectionId === section.id
                  ? "text-app-fg bg-action-primary/10 border border-action-primary/50"
                  : "text-app-muted border-transparent hover:bg-app-subtle hover:text-app-fg"
              }`}
              onClick={() => onSelectKeySection?.(section.id)}
              title={section.description}
            >
              {section.icon}
              <span>{section.label}</span>
            </Button>
          ))}
        </nav>
      )}

      {footer && <div className="sidebar-footer grid gap-2.5 mt-auto">{footer}</div>}
    </aside>
  );
}
