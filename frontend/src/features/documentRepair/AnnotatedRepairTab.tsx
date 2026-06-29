import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getPostDraftRepairSession,
  type DraftPackageManualUpdate,
  type PostDraftRepairSession,
  type PostDraftReviewRun,
  type ProjectRecord,
} from "@/api";
import { Loader2, PenLine } from "@/lib/icons";
import { selectLatestRepairablePostDraftReview } from "@/guidedFlow";

import { PostDraftRepairEditor } from "@/flow/panels/PostDraftRepairEditor";

export interface AnnotatedRepairTabProps {
  project: ProjectRecord | null;
  reviews: PostDraftReviewRun[];
  currentSourceDraftHash: string;
  saving: boolean;
  onSaveDraftPackage: (fields: DraftPackageManualUpdate) => Promise<void> | void;
}

export function AnnotatedRepairTab({
  project,
  reviews,
  currentSourceDraftHash,
  saving,
  onSaveDraftPackage,
}: AnnotatedRepairTabProps) {
  const repairReview = useMemo(
    () => selectLatestRepairablePostDraftReview(reviews, currentSourceDraftHash),
    [currentSourceDraftHash, reviews],
  );
  const [session, setSession] = useState<PostDraftRepairSession | null>(null);
  const [pendingRevalidationIssueIds, setPendingRevalidationIssueIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadSession = useCallback(async () => {
    if (!project || !repairReview) {
      setSession(null);
      setPendingRevalidationIssueIds([]);
      setLoading(false);
      setError("");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const nextSession = await getPostDraftRepairSession(project.id, repairReview.id);
      setSession(nextSession);
      setPendingRevalidationIssueIds([]);
    } catch {
      setSession(null);
      setError("无法加载标注修复会话，请刷新运行状态后重试。");
    } finally {
      setLoading(false);
    }
  }, [project, repairReview]);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  if (!project) {
    return (
      <section className="document-placeholder-panel">
        <div>
          <p className="section-eyebrow">标注修复</p>
          <h3>请先选择项目</h3>
          <p>选中一个项目后，这里会显示可修复的问题队列、正文定位和修复面板。</p>
        </div>
      </section>
    );
  }

  if (!repairReview) {
    return (
      <section className="document-placeholder-panel">
        <div>
          <p className="section-eyebrow">标注修复</p>
          <h3>暂无可修复会审</h3>
          <p>当前项目还没有可进入标注修复的问题会审。先完成成稿会审，或重新生成阻断会审结果。</p>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="document-placeholder-panel document-repair-status-panel" aria-live="polite">
        <div className="document-repair-status">
          <Loader2 className="spin" size={18} />
          <div>
            <p className="section-eyebrow">标注修复</p>
            <h3>正在加载修复会话</h3>
            <p>正在准备问题队列、正文定位和修复面板。</p>
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="document-placeholder-panel document-repair-status-panel" role="alert">
        <div className="document-repair-status">
          <div>
            <p className="section-eyebrow">标注修复</p>
            <h3>修复会话加载失败</h3>
            <p>{error}</p>
          </div>
          <button className="document-secondary-action" onClick={() => void loadSession()} type="button">
            重新加载
          </button>
        </div>
      </section>
    );
  }

  if (!session || session.issues.length === 0 || Object.keys(session.sections).length === 0) {
    return (
      <section className="document-placeholder-panel">
        <div>
          <p className="section-eyebrow">标注修复</p>
          <h3>暂无可展示的修复内容</h3>
          <p>当前修复会话没有可用的问题项或正文段落，请重新运行成稿会审后再试。</p>
        </div>
      </section>
    );
  }

  return (
    <PostDraftRepairEditor
      open
      mode="embedded"
      session={session}
      saving={saving}
      pendingRevalidationIssueIds={pendingRevalidationIssueIds}
      onClose={() => {}}
      onSave={onSaveDraftPackage}
      onPatchApplied={async (fields, issueId) => {
        await onSaveDraftPackage(fields);
        if (issueId) {
          setPendingRevalidationIssueIds((current) =>
            current.includes(issueId) ? current : [...current, issueId],
          );
        }
      }}
    />
  );
}
