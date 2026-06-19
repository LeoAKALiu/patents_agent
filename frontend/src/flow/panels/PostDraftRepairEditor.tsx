import { useState, useCallback, useEffect, useMemo } from "react";

import {
  type DraftPackageManualUpdate,
  type DraftReviewIssue,
  type PostDraftRepairSession,
} from "@/api";
import { Loader2, Save, XCircle } from "@/lib/icons";
import { PostDraftIssueRail } from "./PostDraftIssueRail";
import { AnnotatedDraftSection, SECTION_LABELS } from "./AnnotatedDraftSection";
import { DraftRepairInspector } from "./DraftRepairInspector";

const DRAFT_SECTION_KEYS = [
  "title",
  "abstract",
  "claims",
  "description",
  "drawing_description",
] as const;

export interface PostDraftRepairEditorProps {
  open: boolean;
  session: PostDraftRepairSession | null;
  saving: boolean;
  onClose: () => void;
  onSave: (fields: DraftPackageManualUpdate) => Promise<void> | void;
}

export function PostDraftRepairEditor({
  open,
  session,
  saving,
  onClose,
  onSave,
}: PostDraftRepairEditorProps) {
  const [selectedIssue, setSelectedIssue] = useState<DraftReviewIssue | null>(null);
  const [sectionValues, setSectionValues] = useState<Record<string, string>>({});

  // Reset local state when session changes
  useEffect(() => {
    if (session) {
      setSectionValues({ ...session.sections });
      setSelectedIssue(null);
    }
  }, [session]);

  const handleSelectIssue = useCallback((issue: DraftReviewIssue) => {
    setSelectedIssue(issue);
  }, []);

  const handleUpdateSection = useCallback((sectionKey: string, value: string) => {
    setSectionValues((prev) => ({ ...prev, [sectionKey]: value }));
  }, []);

  const findAnchorIssue = useCallback(
    (sectionKey: string): DraftReviewIssue | null => {
      if (selectedIssue && selectedIssue.target_section === sectionKey) return selectedIssue;
      // Fallback: find first issue anchored to this section
      const anchored = session?.issues.find(
        (i) => i.target_section === sectionKey && i.anchor.type !== "missing",
      );
      return anchored ?? null;
    },
    [selectedIssue, session],
  );

  const handleSave = useCallback(async () => {
    const fields: DraftPackageManualUpdate = {
      title: sectionValues.title ?? "",
      abstract: sectionValues.abstract ?? "",
      claims: sectionValues.claims ?? "",
      description: sectionValues.description ?? "",
      drawing_description: sectionValues.drawing_description ?? "",
    };
    await onSave(fields);
  }, [sectionValues, onSave]);

  if (!open || !session) return null;

  return (
    <div className="draft-editor-overlay" role="dialog" aria-modal="true" aria-label="标注式修复编辑器">
      <div className="repair-editor-shell">
        <header className="draft-editor-header">
          <div>
            <h3>标注式修复编辑器</h3>
            <p>
              {session.stale
                ? "当前初稿已变更，AI 修正不可用。请使用人工修正。"
                : "手动修订各段落，保存后请重新编译正式稿并重新成稿会审。"}
            </p>
          </div>
          <button className="icon-button" onClick={onClose} type="button" aria-label="关闭标注式修复编辑器">
            <XCircle size={18} />
          </button>
        </header>

        <div className="repair-editor-grid">
          <PostDraftIssueRail
            issues={session.issues}
            selectedIssueId={selectedIssue?.id ?? null}
            onSelectIssue={handleSelectIssue}
          />

          <div className="repair-document-pane">
            {DRAFT_SECTION_KEYS.map((sectionKey) => (
              <AnnotatedDraftSection
                key={sectionKey}
                sectionKey={sectionKey}
                label={SECTION_LABELS[sectionKey] ?? sectionKey}
                value={sectionValues[sectionKey] ?? ""}
                selected={selectedIssue?.target_section === sectionKey}
                anchorIssue={findAnchorIssue(sectionKey)}
                onChange={(value) => handleUpdateSection(sectionKey, value)}
              />
            ))}
          </div>

          <DraftRepairInspector
            issue={selectedIssue}
            stale={session.stale}
          />
        </div>

        <footer className="draft-editor-footer">
          <span>保存后请重新编译正式稿并重新成稿会审。</span>
          <button className="btn btn-primary" disabled={saving} onClick={() => void handleSave()} type="button">
            {saving ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
            <span>{saving ? "正在保存" : "保存当前初稿"}</span>
          </button>
        </footer>
      </div>
    </div>
  );
}
