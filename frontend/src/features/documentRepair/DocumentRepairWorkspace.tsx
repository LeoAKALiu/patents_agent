import { useEffect, useMemo, useState } from "react";

import type { ExportReadiness } from "@/api";
import type {
  ProjectWorkspaceHandlers,
  ProjectWorkspaceState,
} from "@/features/projects/ProjectWorkspace";
import type { MainSectionId } from "@/guidedFlow";
import { Info, X } from "@/lib/icons";

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
  const [showGuidance, setShowGuidance] = useState<boolean>(false);
  const [guidanceType, setGuidanceType] = useState<"navigation" | "locked" | null>(null);
  const [dismissedLockGuidanceKey, setDismissedLockGuidanceKey] = useState<string | null>(null);

  const lockGuidanceKey = useMemo(() => {
    if (!exportReadiness || exportReadiness.export_allowed) return null;
    const reviewBlockingCount = exportReadiness.review_blocking_issues?.length ?? 0;
    const compileBlockingCount = exportReadiness.compile_blocked_items?.length ?? 0;
    const hasDocumentRepairBlocker = Boolean(
      reviewBlockingCount > 0
        || compileBlockingCount > 0
        || exportReadiness.post_draft_review_required
        || exportReadiness.review_gate_status === "needs_revision"
        || exportReadiness.review_gate_status === "blocked"
        || exportReadiness.compile_status === "blocked",
    );
    if (!hasDocumentRepairBlocker) return null;
    return [
      exportReadiness.next_action,
      exportReadiness.reason,
      exportReadiness.review_gate_status ?? "",
      exportReadiness.compile_status ?? "",
      String(reviewBlockingCount),
      String(compileBlockingCount),
    ].join("|");
  }, [exportReadiness]);

  function clearGuidance(): void {
    if (lockGuidanceKey) {
      setDismissedLockGuidanceKey(lockGuidanceKey);
    }
    setShowGuidance(false);
    setGuidanceType(null);
  }

  useEffect(() => {
    if (
      !requestedTab
      && lockGuidanceKey
      && dismissedLockGuidanceKey !== lockGuidanceKey
      && guidanceType !== "navigation"
    ) {
      setShowGuidance(true);
      setGuidanceType("locked");
    }
  }, [requestedTab, lockGuidanceKey, dismissedLockGuidanceKey, guidanceType]);

  useEffect(() => {
    if (!requestedTab) return;
    setActiveTab(requestedTab);
    setShowGuidance(true);
    setGuidanceType("navigation");
    if (lockGuidanceKey) {
      setDismissedLockGuidanceKey(lockGuidanceKey);
    }
    onRequestedTabHandled?.();
  }, [requestedTab, onRequestedTabHandled, lockGuidanceKey]);

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
      clearGuidance();
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

      {showGuidance && (
        <div className="document-guidance-band" role="status">
          <div className="document-guidance-content">
            <Info size={16} className="document-guidance-icon" aria-hidden="true" />
            <p className="document-guidance-text">
              {guidanceType === "navigation"
                ? "由于导出门禁或工作台指引，已引导您至标注修复页面处理相关问题。"
                : "当前项目存在待修复的文稿或会审问题，正式稿已被锁定导出。建议前往标注修复处理。"}
            </p>
          </div>
          <div className="document-guidance-actions">
            {guidanceType === "navigation" ? (
              <>
                <button
                  type="button"
                  className="document-guidance-btn-secondary"
                  onClick={() => {
                    setActiveTab("overview");
                    clearGuidance();
                  }}
                >
                  返回总览
                </button>
                <button
                  type="button"
                  className="document-guidance-btn-primary"
                  onClick={clearGuidance}
                >
                  留在标注修复
                </button>
              </>
            ) : (
              <>
                {activeTab !== "annotated" && (
                  <button
                    type="button"
                    className="document-guidance-btn-primary"
                    onClick={() => {
                      setActiveTab("annotated");
                      clearGuidance();
                    }}
                  >
                    前往标注修复
                  </button>
                )}
                {activeTab === "annotated" && (
                  <button
                    type="button"
                    className="document-guidance-btn-secondary"
                    onClick={() => {
                      setActiveTab("overview");
                      clearGuidance();
                    }}
                  >
                    返回总览
                  </button>
                )}
                <button
                  type="button"
                  className="document-guidance-btn-secondary"
                  onClick={clearGuidance}
                >
                  我知道了
                </button>
              </>
            )}
            <button
              type="button"
              className="document-guidance-close"
              aria-label="关闭提示"
              onClick={clearGuidance}
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      <div className="document-tabs" role="tablist" aria-label="文稿与修复标签">
        {tabs.map((tab) => (
          <button
            aria-controls={`document-tabpanel-${tab.id}`}
            aria-selected={activeTab === tab.id}
            className={activeTab === tab.id ? "is-active" : ""}
            id={`document-tab-${tab.id}`}
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id);
              clearGuidance();
            }}
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
            onOpenTab={(tabId) => {
              setActiveTab(tabId);
              clearGuidance();
            }}
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
            onOpenAnnotated={() => {
              setActiveTab("annotated");
              clearGuidance();
            }}
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
            onBack={() => {
              setActiveTab("overview");
              clearGuidance();
            }}
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
