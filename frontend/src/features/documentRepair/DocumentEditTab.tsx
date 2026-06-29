import { useEffect, useMemo, useState } from "react";

import type { DocumentDraftFields } from "./selectors";

const INVALIDATION_COPY = "保存后旧正式稿、旧成稿会审和旧导出状态将失效，需要重新编译正式稿并重新成稿会审。";

const fieldConfig: Array<{
  key: keyof DocumentDraftFields;
  label: string;
  multiline: boolean;
}> = [
  { key: "title", label: "标题", multiline: false },
  { key: "abstract", label: "摘要", multiline: true },
  { key: "claims", label: "权利要求书", multiline: true },
  { key: "description", label: "说明书", multiline: true },
  { key: "drawing_description", label: "附图说明", multiline: true },
];

export interface DocumentEditTabProps {
  draft: DocumentDraftFields | null;
  draftLabel?: string;
  onSaveDraftPackage: (payload: DocumentDraftFields) => void;
}

export function DocumentEditTab({
  draft,
  draftLabel,
  onSaveDraftPackage,
}: DocumentEditTabProps) {
  const initialFields = useMemo<DocumentDraftFields>(() => ({
    title: draft?.title ?? "",
    abstract: draft?.abstract ?? "",
    claims: draft?.claims ?? "",
    description: draft?.description ?? "",
    drawing_description: draft?.drawing_description ?? "",
  }), [
    draft?.title,
    draft?.abstract,
    draft?.claims,
    draft?.description,
    draft?.drawing_description,
  ]);
  const [fields, setFields] = useState<DocumentDraftFields>(initialFields);

  useEffect(() => {
    setFields(initialFields);
  }, [initialFields]);

  const hasDraft = Boolean(draft);
  const isDirty = hasDraft && !sameDraftFields(fields, initialFields);

  function updateField(field: keyof DocumentDraftFields, value: string): void {
    setFields((current) => ({ ...current, [field]: value }));
  }

  function saveDraft(): void {
    if (!hasDraft) return;
    onSaveDraftPackage(fields);
  }

  return (
    <section className="document-edit" aria-labelledby="document-edit-title">
      <div className="document-panel document-edit-status">
        <div>
          <p className="section-eyebrow">内部初稿 - 可编辑</p>
          <h3 id="document-edit-title">编辑内部初稿</h3>
          <p>{draftLabel ? `当前版本 ${draftLabel}` : "当前版本等待生成"}</p>
        </div>
        <span className="document-state-pill">{isDirty ? "有未保存修改" : "未修改"}</span>
      </div>

      <p className="document-invalidation-note">{INVALIDATION_COPY}</p>

      <form className="document-edit-form" onSubmit={(event) => event.preventDefault()}>
        {fieldConfig.map((field) => (
          <label className="document-edit-field" key={field.key}>
            <span>
              {field.label}
              <small aria-hidden="true">{sectionLengthLabel(fields[field.key])}</small>
            </span>
            {field.multiline ? (
              <textarea
                aria-label={field.label}
                value={fields[field.key]}
                onChange={(event) => updateField(field.key, event.target.value)}
                disabled={!hasDraft}
                rows={field.key === "abstract" || field.key === "drawing_description" ? 5 : 12}
              />
            ) : (
              <input
                aria-label={field.label}
                value={fields[field.key]}
                onChange={(event) => updateField(field.key, event.target.value)}
                disabled={!hasDraft}
                type="text"
              />
            )}
          </label>
        ))}
        <div className="document-edit-actions">
          <button
            type="button"
            className="document-secondary-action"
            disabled={!hasDraft || !isDirty}
            onClick={saveDraft}
          >
            保存当前初稿
          </button>
        </div>
      </form>
    </section>
  );
}

function sameDraftFields(left: DocumentDraftFields, right: DocumentDraftFields): boolean {
  return fieldConfig.every((field) => left[field.key] === right[field.key]);
}

function sectionLengthLabel(value: string): string {
  const length = value.replace(/\s+/g, "").length;
  return length > 0 ? `${length} 字` : "待补充";
}
