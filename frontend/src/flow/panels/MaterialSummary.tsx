import { AlertTriangle, CheckCircle2, FileText } from "@/lib/icons";
import type { ProjectMaterial } from "@/api";

/** Inline list of uploaded project materials with status. */
export function MaterialSummary({ materials }: { materials: ProjectMaterial[] }) {
  return (
    <section className="settings-group material-summary">
      <div className="settings-group-header">
        <h3>材料摘要</h3>
        <p>补充材料会作为发明点提炼、说明书支撑和质量检查的参考输入。</p>
      </div>
      <div className="guided-summary-list">
        {materials.map((material) => (
          <article className="info-card material-summary-row" key={material.id}>
            <div className={material.status === "processed" ? "info-card-icon success" : "info-card-icon warn"}>
              {material.status === "processed" ? <CheckCircle2 size={18} aria-hidden="true" /> : <AlertTriangle size={18} aria-hidden="true" />}
            </div>
            <div className="info-card-body">
              <strong>{material.file_name}</strong>
              <p>
                {material.status === "processed"
                  ? `${material.file_type} / ${material.text.length} 字`
                  : material.warnings.join("；")}
              </p>
            </div>
          </article>
        ))}
        {materials.length === 0 && (
          <div className="callout material-summary-empty">
            <FileText size={18} aria-hidden="true" />
            <div>
              <strong>暂无补充材料</strong>
              <p className="empty">可先不上传材料，系统会基于想法生成第一版。</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
