import { useState } from "react";
import { CheckCircle2, FileText, Upload } from "@/lib/icons";
import type {
  ExternalDraftIntakeRun,
  ExternalDraftSource,
  ProjectRecord,
} from "@/api";
import { sourceTypeLabel } from "@/domain";
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
      {!project && <p className="workflow-hint">请先创建或选择一个项目，再导入外部初稿。</p>}
      <form className="guided-upload" onSubmit={handleUpload}>
        <label>
          <span>文件名</span>
          <input
            id="external-draft-file"
            name="external-draft-file"
            type="file"
            accept=".docx,.txt,.md,.markdown"
            onChange={(event) => setSelectedUploadFileName(event.target.files?.[0]?.name ?? "")}
          />
        </label>
        <button className="primary" disabled={!project || !selectedUploadFileName || busy === "external-draft-upload"} type="submit">
          <Upload size={17} />
          <span>上传外部初稿</span>
        </button>
      </form>
      <form className="guided-intake" onSubmit={handleCreate}>
        <label>
          <span>粘贴稿文件名</span>
          <input value={fileName} onChange={(event) => setFileName(event.target.value)} disabled={!project} />
        </label>
        <label>
          <span>粘贴外部专利初稿</span>
          <textarea
            className="idea-input"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="粘贴发明名称、摘要、权利要求书、说明书和附图说明。"
          />
        </label>
        <button className="primary" disabled={!project || !text.trim() || busy === "external-draft-create"} type="submit">
          <FileText size={17} />
          <span>保存原始外部稿</span>
        </button>
      </form>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy.startsWith("external-draft")} />
      <div className="guided-summary-list">
        {sources.map((source) => (
          <article className="guided-summary-row external-draft-source-row" key={source.id}>
            <FileText size={18} />
            <div>
              <strong>{source.file_name}</strong>
              <span>
                {sourceTypeLabel(source.source_type)} · {source.content_hash.slice(0, 12)}
              </span>
            </div>
            <button
              className="icon-button"
              disabled={busy === "external-draft-intake"}
              onClick={() => onStartExternalDraftIntake(source.id)}
              type="button"
            >
              解析章节
            </button>
          </article>
        ))}
        {sources.length === 0 && <p className="empty">保存外部稿后，系统会解析章节并生成内部工作稿。</p>}
      </div>
      {latestRun && (
        <article className="guided-choice selected external-draft-result">
          <div className="result-meta">
            <span className={latestRun.status === "needs_review" ? "status-badge warn" : "status-badge"}>
              {latestRun.status === "completed" ? "解析完成" : latestRun.status === "needs_review" ? "需要确认" : "解析失败"}
            </span>
            <span>工作稿：{latestRun.working_draft_hash.slice(0, 12) || "尚未生成"}</span>
          </div>
          <h4>{draft?.title || "外部初稿解析结果"}</h4>
          <p>{latestRun.intake_issues.map((issue) => issue.message).join("；") || "导入阶段未发现阻断问题。"}</p>
          {draft && (
            <div className="external-draft-section-preview">
              <span>权利要求：{draft.claims.trim() ? "已识别" : "缺失"}</span>
              <span>说明书：{draft.description.trim() ? "已识别" : "缺失"}</span>
            </div>
          )}
          {draft && (
            <button
              className="primary"
              disabled={!confirmable || busy === "external-draft-confirm"}
              onClick={handleConfirm}
              type="button"
            >
              <CheckCircle2 size={17} />
              <span>确认为内部工作稿</span>
            </button>
          )}
          {draft && !confirmable && <p className="workflow-hint">请补齐权利要求书和说明书后重新保存并解析。</p>}
        </article>
      )}
    </section>
  );
}
