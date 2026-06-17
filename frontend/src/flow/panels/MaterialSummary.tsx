import { AlertTriangle, CheckCircle2 } from "@/lib/icons";
import type { ProjectMaterial } from "@/api";

/** Inline list of uploaded project materials with status. */
export function MaterialSummary({ materials }: { materials: ProjectMaterial[] }) {
  return (
    <div className="guided-summary-list">
      {materials.map((material) => (
        <article className="guided-summary-row" key={material.id}>
          {material.status === "processed" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          <div>
            <strong>{material.file_name}</strong>
            <span>
              {material.status === "processed"
                ? `${material.file_type} / ${material.text.length} 字`
                : material.warnings.join("；")}
            </span>
          </div>
        </article>
      ))}
      {materials.length === 0 && <p className="empty">可先不上传材料，系统会基于想法生成第一版。</p>}
    </div>
  );
}
