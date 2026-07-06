import { useState, useCallback, useEffect, useMemo } from "react";

import {
  type DraftPackageManualUpdate,
  type DraftReviewIssue,
  type PostDraftRepairSession,
  type DraftRepairPatch,
  createDraftRepairPatch,
  applyDraftRepairPatch,
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

type PatchActivity = {
  issueId: string;
  section: DraftRepairPatch["target_section"];
  status: "applying" | "applied";
};

export interface PostDraftRepairEditorProps {
  open: boolean;
  session: PostDraftRepairSession | null;
  saving: boolean;
  mode?: "modal" | "embedded";
  pendingRevalidationIssueIds?: string[];
  onClose: () => void;
  onSave: (fields: DraftPackageManualUpdate) => Promise<void> | void;
  onPatchApplied?: (
    fields: DraftPackageManualUpdate,
    issueId?: string,
  ) => Promise<void> | void;
}

export function PostDraftRepairEditor({
  open,
  session,
  saving,
  mode = "modal",
  pendingRevalidationIssueIds = [],
  onClose,
  onSave,
  onPatchApplied,
}: PostDraftRepairEditorProps) {
  const [selectedIssue, setSelectedIssue] = useState<DraftReviewIssue | null>(
    () => session?.issues[0] ?? null,
  );
  const [sectionValues, setSectionValues] = useState<Record<string, string>>(
    {},
  );

  // Patch workflow state
  const [patch, setPatch] = useState<DraftRepairPatch | null>(null);
  const [generating, setGenerating] = useState(false);
  const [applying, setApplying] = useState(false);
  const [patchError, setPatchError] = useState<string | null>(null);
  const [resolvedIssueIds, setResolvedIssueIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [patchActivity, setPatchActivity] = useState<PatchActivity | null>(null);

  // Reset local state when session changes
  useEffect(() => {
    if (session) {
      setSectionValues({ ...session.sections });
      setSelectedIssue(session.issues[0] ?? null);
      setPatch(null);
      setGenerating(false);
      setApplying(false);
      setPatchError(null);
      setResolvedIssueIds(new Set());
      setPatchActivity(null);
    }
  }, [session]);

  const visibleIssues = useMemo(
    () =>
      (session?.issues ?? []).filter(
        (issue) =>
          pendingRevalidationIssueIds.includes(issue.id) ||
          (!resolvedIssueIds.has(issue.id) &&
            !isIssueResolvedInCurrentDraft(issue, sectionValues)),
      ),
    [session, resolvedIssueIds, sectionValues, pendingRevalidationIssueIds],
  );

  useEffect(() => {
    if (!session) return;
    if (selectedIssue && visibleIssues.some((issue) => issue.id === selectedIssue.id)) {
      return;
    }
    setSelectedIssue(visibleIssues[0] ?? null);
    setPatch(null);
    setPatchError(null);
  }, [session, selectedIssue, visibleIssues]);

  const handleSelectIssue = useCallback((issue: DraftReviewIssue) => {
    setSelectedIssue(issue);
    setPatch(null);
    setPatchError(null);
    setPatchActivity(null);
  }, []);

  const handleUpdateSection = useCallback(
    (sectionKey: string, value: string) => {
      setSectionValues((prev) => ({ ...prev, [sectionKey]: value }));
    },
    [],
  );

  const findAnchorIssue = useCallback(
    (sectionKey: string): DraftReviewIssue | null => {
      if (selectedIssue && selectedIssue.target_section === sectionKey)
        return selectedIssue;
      // Fallback: find first issue anchored to this section
      const anchored = visibleIssues.find(
        (i) => i.target_section === sectionKey && i.anchor.type !== "missing",
      );
      return anchored ?? null;
    },
    [selectedIssue, visibleIssues],
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

  const handleGeneratePatch = useCallback(async () => {
    if (!session || !selectedIssue) return;
    setPatchError(null);
    if (!isPatchTargetSection(selectedIssue.target_section)) {
      setPatchError("该问题未定位到可修正段落，请人工修正。");
      return;
    }
    setGenerating(true);
    try {
      const sectionText =
        sectionValues[selectedIssue.target_section] ?? "";
      const selectedText = selectedTextForIssue(selectedIssue, sectionText);
      const result = await createDraftRepairPatch(
        session.project_id,
        session.review_run_id,
        {
          issue_id: selectedIssue.id,
          draft_package_hash: session.current_draft_hash ?? "",
          target_section: selectedIssue.target_section,
          selected_text: selectedText,
          nearby_context: sectionText.length > 0 ? sectionText : null,
        },
      );
      setPatch(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setPatchError(message);
    } finally {
      setGenerating(false);
    }
  }, [session, selectedIssue, sectionValues]);

  const handleApplyPatch = useCallback(async () => {
    if (!session || !patch) return;
    setApplying(true);
    setPatchError(null);
    setPatchActivity({
      issueId: patch.issue_id,
      section: patch.target_section,
      status: "applying",
    });
    try {
      const result = await applyDraftRepairPatch(
        session.project_id,
        session.review_run_id,
        patch.id,
      );
      // Update local section content with the patched version
      const updatedSection =
        result.package[patch.target_section as keyof typeof result.package];
      if (typeof updatedSection === "string") {
        setSectionValues((prev) => ({
          ...prev,
          [patch.target_section]: updatedSection,
        }));
      }
      await onPatchApplied?.(editableFieldsFromPackage(result.package), patch.issue_id);
      setResolvedIssueIds((prev) => {
        const next = new Set(prev);
        next.add(patch.issue_id);
        return next;
      });
      setPatchActivity({
        issueId: patch.issue_id,
        section: patch.target_section,
        status: "applied",
      });
      setPatch(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setPatchError(message);
      setPatchActivity(null);
    } finally {
      setApplying(false);
    }
  }, [session, patch, onPatchApplied]);

  const handleDismissPatch = useCallback(() => {
    setPatch(null);
    setPatchError(null);
  }, []);

  if (!open || !session) return null;

  const embedded = mode === "embedded";
  const selectedPendingRevalidation = selectedIssue
    ? pendingRevalidationIssueIds.includes(selectedIssue.id)
    : false;

  return (
    <div
      className={embedded ? "draft-editor-embedded" : "draft-editor-overlay"}
      role={embedded ? undefined : "dialog"}
      aria-modal={embedded ? undefined : "true"}
      aria-label="标注式修复编辑器"
    >
      <div className={`repair-editor-shell${embedded ? " is-embedded" : ""}`}>
        <header className="draft-editor-header">
          <div>
            <h3>标注式修复编辑器</h3>
            <p>
              {session.stale
                ? "当前初稿已变更，AI 修正不可用。请使用人工修正。"
                : "手动修订各段落，保存后请重新编译正式稿并重新成稿会审。"}
            </p>
          </div>
          {!embedded && (
            <button
              className="icon-button"
              onClick={onClose}
              type="button"
              aria-label="关闭标注式修复编辑器"
            >
              <XCircle size={18} />
            </button>
          )}
        </header>

        <div className="repair-editor-grid">
          <PostDraftIssueRail
            issues={visibleIssues}
            selectedIssueId={selectedIssue?.id ?? null}
            pendingRevalidationIssueIds={pendingRevalidationIssueIds}
            onSelectIssue={handleSelectIssue}
          />

          <div className="repair-document-pane">
            <div className="repair-pane-header">
              <h4>正文定位</h4>
              <p>按问题定位段落并直接修改当前初稿内容。</p>
            </div>
            {DRAFT_SECTION_KEYS.map((sectionKey) => (
              <AnnotatedDraftSection
                key={sectionKey}
                sectionKey={sectionKey}
                label={SECTION_LABELS[sectionKey] ?? sectionKey}
                value={sectionValues[sectionKey] ?? ""}
                selected={selectedIssue?.target_section === sectionKey}
                anchorIssue={findAnchorIssue(sectionKey)}
                patchActivity={
                  patchActivity?.section === sectionKey ? patchActivity.status : null
                }
                onChange={(value) => handleUpdateSection(sectionKey, value)}
              />
            ))}
          </div>

          <DraftRepairInspector
            issue={selectedIssue}
            sectionText={
              selectedIssue && selectedIssue.target_section !== "unknown"
                ? sectionValues[selectedIssue.target_section] ?? ""
                : ""
            }
            stale={session.stale}
            patch={patch}
            pendingRevalidation={selectedPendingRevalidation}
            generating={generating}
            applying={applying}
            patchError={patchError}
            patchActivity={patchActivity}
            onGeneratePatch={handleGeneratePatch}
            onApplyPatch={handleApplyPatch}
            onDismissPatch={handleDismissPatch}
          />
        </div>

        <footer className="draft-editor-footer">
          <span>保存后请重新编译正式稿并重新成稿会审。</span>
          <button
            className="btn btn-primary"
            disabled={saving}
            onClick={() => void handleSave()}
            type="button"
          >
            {saving ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
            <span>{saving ? "正在保存" : "保存当前初稿"}</span>
          </button>
        </footer>
      </div>
    </div>
  );
}

function isPatchTargetSection(section: string): section is DraftRepairPatch["target_section"] {
  return DRAFT_SECTION_KEYS.includes(section as DraftRepairPatch["target_section"]);
}

function editableFieldsFromPackage(packageValue: DraftPackageManualUpdate): DraftPackageManualUpdate {
  return {
    title: packageValue.title,
    abstract: packageValue.abstract,
    claims: packageValue.claims,
    description: packageValue.description,
    drawing_description: packageValue.drawing_description,
  };
}

function selectedTextForIssue(issue: DraftReviewIssue, sectionText: string): string | null {
  const anchorSnippet = issue.anchor.snippet?.trim();
  if (anchorSnippet && sectionText.includes(anchorSnippet)) {
    return anchorSnippet;
  }

  const issueSnippet = issue.snippet?.trim();
  if (issueSnippet && sectionText.includes(issueSnippet)) {
    return issueSnippet;
  }

  const { start, end } = issue.anchor;
  if (
    issue.anchor.type === "text" &&
    typeof start === "number" &&
    typeof end === "number" &&
    start >= 0 &&
    end > start &&
    end <= sectionText.length
  ) {
    const anchoredText = sectionText.slice(start, end).trim();
    return anchoredText || null;
  }

  return null;
}

function isIssueResolvedInCurrentDraft(
  issue: DraftReviewIssue,
  sectionValues: Record<string, string>,
): boolean {
  if (issue.status === "fixed" || issue.status === "skipped") return true;
  if (issue.anchor.type !== "text") return false;
  if (!(issue.target_section in sectionValues)) return false;

  const sectionText = sectionValues[issue.target_section] ?? "";
  const snippet = issue.anchor.snippet?.trim() || issue.snippet?.trim();
  return Boolean(snippet && !sectionText.includes(snippet));
}
