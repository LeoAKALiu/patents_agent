import type { ReactNode } from "react";

import { ShellSidebar, type ShellNavSection } from "@/ui/ShellSidebar";
import { ShellTopbar, type ShellTopbarProps } from "@/ui/ShellTopbar";

/**
 * ShellLayout composes the production desktop shell — destination sidebar,
 * topbar, and the active workspace content. It owns no state of its own:
 * navigation state lives in AppRoot, workspace state lives in the feature
 * workspace components.
 */
export interface ShellLayoutProps {
  /** Active main section id used to highlight the sidebar entry. */
  activeSectionId: string;
  /** Sections rendered in the main navigation group. */
  mainSections: ShellNavSection[];
  /** Called when the user picks a main section entry. */
  onSelectSection: (id: string) => void;
  /** Slot for the sidebar footer (health, agent doctor, etc.). */
  sidebarFooter?: ReactNode;
  /** Topbar configuration. Title/subtitle are filled in by AppRoot. */
  topbar: Omit<ShellTopbarProps, "title" | "subtitle">;
  /** Title + subtitle shown in the page-title area of the topbar. */
  pageTitle?: ReactNode;
  pageSubtitle?: ReactNode;
  /** Workspace content rendered between the topbar and the bottom notice. */
  children: ReactNode;
}

export function ShellLayout({
  activeSectionId,
  mainSections,
  onSelectSection,
  sidebarFooter,
  topbar,
  pageTitle,
  pageSubtitle,
  children,
}: ShellLayoutProps) {
  return (
    <div className="app-shell">
      <ShellSidebar
        mainSections={mainSections}
        activeSectionId={activeSectionId}
        onSelectSection={onSelectSection}
        footer={sidebarFooter}
      />
      <main className="main-area">
        <ShellTopbar {...topbar} title={pageTitle} subtitle={pageSubtitle} />
        {children}
      </main>
    </div>
  );
}
