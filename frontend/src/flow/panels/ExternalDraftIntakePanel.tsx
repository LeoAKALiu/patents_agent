import { useState } from "react";
import { AlertTriangle, CheckCircle2, FileText, Upload } from "@/lib/icons";
import { Badge } from "@/components/ui/badge";
import type {
  ExternalDraftIntakeRun,
  ExternalDraftSource,
  ProjectRecord,
} from "@/api";
import { sourceTypeLabel } from "@/domain";
import { cn } from "@/lib/cn";
import type { FormEvent } from "react";
import { GuidedOperationConsole } from "../runtimeWidgets";

export interface ExternalDraftIntakePanelProps {
  project: ProjectRecord | null;
  sources: ExternalDraftSource[];
  runs: ExternalDraftIntakeRun[];
  busy: string;
  busyElapsedSeconds: number;
  onCreateExternalDraft: (payload: { text: string; fileName: string }) => Promise<void>;
  onUploadExternalDraft: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onStartExternalDraftIntake: (sourceId: string) => Promise<void>;
  onConfirmExternalDraftIntake: (
    runId: string,
    payload: {
      title: string;
      abstract: string;
      claims: string;
      description: string;
      drawing_description: string;
    },
  ) => Promise<void>;
}

export function ExternalDraftIntakePanel({
  project,
  sources,
  runs,
  busy,
  busyElapsedSeconds,
  onCreateExternalDraft,
  onUploadExternalDraft,
  onStartExternalDraftIntake,
  onConfirmExternalDraftIntake,
}: ExternalDraftIntakePanelProps) {
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("external-draft.txt");
  const [selectedUploadFileName, setSelectedUploadFileName] = useState("");
  const latestRun = runs[0] ?? null;
  const draft = latestRun?.parsed_package ?? null;
  const confirmable = Boolean(draft?.claims.trim() && draft?.description.trim());
  const latestRunLabel = latestRun
    ? latestRun.status === "completed"
      ? "已生成工作稿"
      : latestRun.status === "needs_review"
        ? "待人工确认"
        : "解析失败"
    : "尚未解析";

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!project || !text.trim()) return;
    await onCreateExternalDraft({ text: text.trim(), fileName: fileName.trim() || "external-draft.txt" });
    setText("");
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !selectedUploadFileName) return;
    await onUploadExternalDraft(event);
    setSelectedUploadFileName("");
  }

  async function handleConfirm() {
    if (!latestRun || !draft || !confirmable) return;
    await onConfirmExternalDraftIntake(latestRun.id, {
      title: draft.title,
      abstract: draft.abstract,
      claims: draft.claims,
      description: draft.description,
      drawing_description: draft.drawing_description,
    });
  }

  return (
    <section className="external-draft-panel">
      <div className="status-strip" aria-label="外部初稿导入摘要">
        <div className="status-tile">
          <span>当前项目</span>
          <strong title={project?.name ?? "未选择"}>{project?.name ?? "未选择"}</strong>
        </div>
        <div className="status-tile">
          <span>已保存来源</span>
          <strong>{sources.length} 份</strong>
        </div>
        <div className="status-tile">
          <span>最近解析</span>
          <strong>{latestRunLabel}</strong>
        </div>
        <div className="status-tile">
          <span>确认条件</span>
          <strong>{confirmable ? "可确认" : "需权利要求+说明书"}</strong>
        </div>
      </div>

      {!project && (
        <div className="callout callout-warn">
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>请先创建或选择项目</strong>
            <p>外部稿会绑定到当前项目，用于解析章节并生成内部工作稿。</p>
          </div>
        </div>
      )}

      <div className="settings-group">
        <div className="settings-group-header">
          <h3>保存外部初稿</h3>
          <p>可以上传 DOCX/TXT/Markdown，也可以直接粘贴原文。保存后再运行章节解析。</p>
        </div>
        <form className="info-card guided-upload guided-upload-card" onSubmit={handleUpload}>
          <div className="info-card-icon info">
            <Upload size={18} aria-hidden="true" />
          </div>
          <div className="info-card-body">
            <strong>上传文件</strong>
            <p>适合已有 DOCX、TXT 或 Markdown 初稿。</p>
            <label className="field">
              <span>文件名</span>
              <input
                id="external-draft-file"
                name="external-draft-file"
                type="file"
                accept=".docx,.txt,.md,.markdown"
                onChange={(event) => setSelectedUploadFileName(event.target.files?.[0]?.name ?? "")}
              />
            </label>
          </div>
          <button className="btn btn-primary" disabled={!project || !selectedUploadFileName || busy === "external-draft-upload"} type="submit">
            <Upload size={17} />
            <span>上传外部初稿</span>
          </button>
        </form>
        <form className="info-card guided-intake guided-form-card" onSubmit={handleCreate}>
          <div className="info-card-icon accent">
            <FileText size={18} aria-hidden="true" />
          </div>
          <div className="info-card-body">
            <strong>粘贴文本</strong>
            <p>适合从审稿文件、邮件或网页复制已有初稿。</p>
            <div className="guided-field-grid">
              <label className="field">
                <span>粘贴稿文件名</span>
                <input value={fileName} onChange={(event) => setFileName(event.target.value)} disabled={!project} />
              </label>
              <label className="field field-wide">
                <span>粘贴外部专利初稿</span>
                <textarea
                  className="idea-input"
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  placeholder="粘贴发明名称、摘要、权利要求书、说明书和附图说明。"
                />
              </label>
            </div>
          </div>
          <button className="btn btn-primary" disabled={!project || !text.trim() || busy === "external-draft-create"} type="submit">
            <FileText size={17} />
            <span>保存原始外部稿</span>
          </button>
        </form>
      </div>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy.startsWith("external-draft")} />

      <div className="settings-group">
        <div className="settings-group-header">
          <h3>来源队列</h3>
          <p>已保存的外部稿会保留原始哈希，解析结果需要确认后才会覆盖内部工作稿。</p>
        </div>
        <div className="guided-summary-list">
          {sources.map((source) => (
            <article className="info-card external-draft-source-row" key={source.id}>
              <div className="info-card-icon">
                <FileText size={18} aria-hidden="true" />
              </div>
              <div className="info-card-body">
                <strong>{source.file_name}</strong>
                <p>
                  {sourceTypeLabel(source.source_type)} · {source.content_hash.slice(0, 12)}
                </p>
              </div>
              <button
                className="btn btn-secondary"
                disabled={busy === "external-draft-intake"}
                onClick={() => onStartExternalDraftIntake(source.id)}
                type="button"
              >
                解析章节
              </button>
            </article>
          ))}
          {sources.length === 0 && (
            <div className="callout">
              <FileText size={18} aria-hidden="true" />
              <div>
                <strong>暂无外部稿来源</strong>
                <p className="empty">保存外部稿后，系统会解析章节并生成内部工作稿。</p>
              </div>
            </div>
          )}
        </div>
      </div>
      {latestRun && (
        <article className={cn("info-card external-draft-result", latestRun.status === "needs_review" && "selected")}>
          <div className={cn("info-card-icon", latestRun.status === "completed" ? "success" : latestRun.status === "needs_review" ? "warn" : "danger")}>
            {latestRun.status === "completed" ? <CheckCircle2 size={18} aria-hidden="true" /> : <AlertTriangle size={18} aria-hidden="true" />}
          </div>
          <div className="info-card-body">
            <div className="result-meta">
              {latestRun.status === "completed" ? <Badge variant="success" className="text-xs">解析完成</Badge> : latestRun.status === "needs_review" ? <Badge variant="warning" className="text-xs">需要确认</Badge> : <Badge variant="secondary" className="text-xs">解析失败</Badge>}
              <span>工作稿：{latestRun.working_draft_hash.slice(0, 12) || "尚未生成"}</span>
            </div>
            <strong>{draft?.title || "外部初稿解析结果"}</strong>
            <p>{latestRun.intake_issues.map((issue) => issue.message).join("；") || "导入阶段未发现阻断问题。"}</p>
            {draft && (
              <div className="external-draft-section-preview">
                <span>权利要求：{draft.claims.trim() ? "已识别" : "缺失"}</span>
                <span>说明书：{draft.description.trim() ? "已识别" : "缺失"}</span>
              </div>
            )}
          </div>
          {draft && (
            <button
              className="btn btn-primary"
              disabled={!confirmable || busy === "external-draft-confirm"}
              onClick={handleConfirm}
              type="button"
            >
              <CheckCircle2 size={17} />
              <span>确认为内部工作稿</span>
            </button>
          )}
        </article>
      )}
      {draft && !confirmable && (
        <div className="callout callout-warn">
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>确认条件未满足</strong>
            <p>请补齐权利要求书和说明书后重新保存并解析。</p>
          </div>
        </div>
      )}
    </section>
  );
}
