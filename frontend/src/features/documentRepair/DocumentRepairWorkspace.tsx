import { useEffect, useMemo, useState } from "react";

import type { ExportReadiness } from "@/api";
import type {
  ProjectWorkspaceHandlers,
  ProjectWorkspaceState,
} from "@/features/projects/ProjectWorkspace";
import type { MainSectionId } from "@/guidedFlow";

import { DocumentEditTab } from "./DocumentEditTab";
import { DocumentIssuesTab } from "./DocumentIssuesTab";
import { DocumentOverviewTab } from "./DocumentOverviewTab";
import { DocumentVersionsTab } from "./DocumentVersionsTab";
import { AnnotatedRepairTab } from "./AnnotatedRepairTab";
import {
  deriveDocumentRepairState,
  type DocumentRepairTabId,
} from "./selectors";

export interface DocumentRepairWorkspaceProps {
  projectState: ProjectWorkspaceState;
  handlers: ProjectWorkspaceHandlers;
  exportReadiness?: ExportReadiness | null;
  onNavigate: (section: MainSectionId) => void;
  requestedTab?: DocumentRepairTabId | null;
  onRequestedTabHandled?: () => void;
}

const tabs: Array<{ id: DocumentRepairTabId; label: string; description: string }> = [
  { id: "overview", label: "总览", description: "门禁、文稿和问题摘要" },
  { id: "edit", label: "编辑", description: "内部初稿编辑" },
  { id: "issues", label: "问题", description: "问题队列" },
  { id: "annotated", label: "标注修复", description: "问题队列、正文定位与修复面板" },
  { id: "versions", label: "版本", description: "版本链路" },
];

export function DocumentRepairWorkspace({
  projectState,
  handlers,
  exportReadiness = null,
  onNavigate,
  requestedTab = null,
  onRequestedTabHandled,
}: DocumentRepairWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<DocumentRepairTabId>("overview");

  useEffect(() => {
    if (!requestedTab) return;
    setActiveTab(requestedTab);
    onRequestedTabHandled?.();
  }, [requestedTab, onRequestedTabHandled]);

  const state = useMemo(
    () => deriveDocumentRepairState({ projectState, exportReadiness, activeTab }),
    [activeTab, exportReadiness, projectState],
  );

  function runPrimaryAction(): void {
    if (state.primaryAction.targetSection) {
      onNavigate(state.primaryAction.targetSection);
      return;
    }
    if (state.primaryAction.targetTab) {
      setActiveTab(state.primaryAction.targetTab);
    }
  }

  return (
    <section className="document-workspace" aria-labelledby="document-workspace-title">
      <div className="document-workspace-header">
        <div>
          <p className="section-eyebrow">文稿与修复</p>
          <h2 id="document-workspace-title">文稿与修复</h2>
          <p>管理内部初稿、正式稿、问题修复和导出门禁。</p>
        </div>
      </div>

      <div className="document-tabs" role="tablist" aria-label="文稿与修复标签">
        {tabs.map((tab) => (
          <button
            aria-controls={`document-tabpanel-${tab.id}`}
            aria-selected={activeTab === tab.id}
            className={activeTab === tab.id ? "is-active" : ""}
            id={`document-tab-${tab.id}`}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            type="button"
          >
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div
        aria-labelledby={`document-tab-${activeTab}`}
        className="document-tab-panel"
        id={`document-tabpanel-${activeTab}`}
        role="tabpanel"
      >
        {activeTab === "overview" ? (
          <DocumentOverviewTab
            state={state}
            onPrimaryAction={runPrimaryAction}
            onOpenTab={setActiveTab}
          />
        ) : activeTab === "edit" ? (
          <DocumentEditTab
            draft={state.editableDraft}
            draftLabel={state.versionChain.nodes.find((node) => node.id === "internalDraft")?.shortHash}
            onSaveDraftPackage={handlers.onSaveDraftPackage}
          />
        ) : activeTab === "issues" ? (
          <DocumentIssuesTab
            inbox={state.issueInbox}
            onOpenAnnotated={() => setActiveTab("annotated")}
          />
        ) : activeTab === "annotated" ? (
          <AnnotatedRepairTab
            project={projectState.selectedProject}
            reviews={projectState.postDraftReviews}
            currentSourceDraftHash={projectState.currentSourceDraftHash}
            saving={projectState.busy === "save-draft"}
            onSaveDraftPackage={handlers.onSaveDraftPackage}
            onDraftRepairPatchApplied={handlers.onDraftRepairPatchApplied}
          />
        ) : activeTab === "versions" ? (
          <DocumentVersionsTab chain={state.versionChain} />
        ) : (
          <PlaceholderPanel
            tab={tabs.find((tab) => tab.id === activeTab) ?? tabs[0]}
            onBack={() => setActiveTab("overview")}
          />
        )}
      </div>
    </section>
  );
}

function PlaceholderPanel({
  tab,
  onBack,
}: {
  tab: { label: string; description: string };
  onBack: () => void;
}) {
  return (
    <section className="document-placeholder-panel">
      <div>
        <p className="section-eyebrow">占位面板</p>
        <h3>{tab.label}</h3>
        <p>{tab.description}</p>
      </div>
      <button type="button" className="document-secondary-action" onClick={onBack}>
        返回总览
      </button>
    </section>
  );
}
