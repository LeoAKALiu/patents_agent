import { AlertTriangle, CheckCircle2, FileText } from "@/lib/icons";
import type { ProjectMaterial } from "@/api";

/** Inline list of uploaded project materials with status. */
export function MaterialSummary({ materials }: { materials: ProjectMaterial[] }) {
  const processedMaterials = materials.filter((material) => material.status === "processed");
  const failedMaterials = materials.filter((material) => material.status !== "processed");
  return (
    <section className="settings-group material-summary">
      <div className="settings-group-header">
        <h3>材料摘要</h3>
        <p>补充材料会作为发明点提炼、说明书支撑和质量检查的参考输入。</p>
      </div>
      <div className="guided-summary-list">
        {processedMaterials.length > 0 && (
          <div className="material-summary-group">
            <h4>可用材料</h4>
            {processedMaterials.map((material) => (
              <article className="info-card material-summary-row" key={material.id}>
                <div className="info-card-icon success">
                  <CheckCircle2 size={18} aria-hidden="true" />
                </div>
                <div className="info-card-body">
                  <strong>{material.file_name}</strong>
                  <p>
                    <span>类型：{material.file_type || "未知"}</span>
                    {" · "}
                    <span>{material.text.length} 字</span>
                  </p>
                </div>
              </article>
            ))}
          </div>
        )}
        {failedMaterials.length > 0 && (
          <div className="material-summary-group">
            <h4>失败上传</h4>
            <p>以下文件不参与后续发明点提炼，请重新选择可读且支持的文件。</p>
            {failedMaterials.map((material) => (
              <article className="info-card material-summary-row" key={material.id}>
                <div className="info-card-icon warn">
                  <AlertTriangle size={18} aria-hidden="true" />
                </div>
                <div className="info-card-body">
                  <strong>{material.file_name}</strong>
                  <p>{material.warnings.join("；") || "材料解析失败。"}</p>
                </div>
              </article>
            ))}
          </div>
        )}
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
