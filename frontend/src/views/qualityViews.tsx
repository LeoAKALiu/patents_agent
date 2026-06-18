/**
 * Quality-check expert views — extracted from App.tsx (M3-B').
 * ClaimDefenseView (权利要求防线) + ReviewView (审查意见).
 */
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Info,
  Scale,
  Search,
  ShieldCheck,
} from "@/lib/icons";
import type {
  ClaimDefenseWorksheet,
  ProjectRecord,
  ReviewFinding,
} from "@/api";
import {
  featureClassificationLabel,
  severityLabel,
  worksheetSourceLabel,
  worksheetStatusLabel,
} from "@/domain";
import {
  ActionDock,
  InfoCard,
  SectionHead,
  SettingsGroup,
  StatusStrip,
} from "@/ui/EnterpriseSurface";

function severityTone(severity: string): "danger" | "warn" | "info" {
  if (severity === "high") return "danger";
  if (severity === "medium") return "warn";
  return "info";
}

function severityTagClass(severity: string): string {
  if (severity === "high") return "tag tag-danger";
  if (severity === "medium") return "tag tag-warn";
  return "tag tag-info";
}

function EmptyMessage({ children }: { children: string }) {
  return <p className="empty">{children}</p>;
}

export function ClaimDefenseView({
  project,
  worksheet,
  worksheets,
  busy,
  onGenerate,
}: {
  project: ProjectRecord | null;
  worksheet: ClaimDefenseWorksheet | null;
  worksheets: ClaimDefenseWorksheet[];
  busy: string;
  onGenerate: () => void;
}) {
  const featureCount = worksheet?.feature_records.length ?? 0;
  const differentiatorCount = worksheet?.feature_records.filter((record) => (
    record.classification === "differentiator" || record.classification === "core_combo"
  )).length ?? 0;
  const supportGapCount = worksheet?.support_gaps.length ?? 0;
  const riskTagCount = worksheet
    ? new Set(worksheet.feature_records.flatMap((record) => record.risk_tags)).size
    : 0;

  return (
    <div className="grid gap-4">
      <StatusStrip
        aria-label="权利要求防线状态"
        items={[
          { label: "当前项目", value: project ? project.name : "未选择项目" },
          { label: "特征记录", value: `${featureCount} 项` },
          { label: "区别/核心特征", value: `${differentiatorCount} 项` },
          { label: "支撑缺口", value: `${supportGapCount} 项` },
        ]}
      />

      <SectionHead
        title="权利要求防线"
        description={project ? "从当前草稿、交底书和已生成文本提取特征记录，标记区别特征、支撑缺口与从属兜底建议。" : "先创建项目后再生成防线工作表。"}
        actions={(
          <button
            className="btn btn-primary"
            disabled={!project || busy === "claim-defense"}
            onClick={onGenerate}
            type="button"
          >
            <ShieldCheck size={18} />
            <span>生成工作表</span>
          </button>
        )}
      />

      <SettingsGroup>
        <div className="boundary-grid">
          <InfoCard
            icon={<Scale size={18} />}
            title="权利要求边界"
            description="区别特征、核心组合和从属兜底统一沉淀到工作表，避免保护范围只停留在自由文本。"
            tone={differentiatorCount > 0 ? "success" : "info"}
            meta={<span className={differentiatorCount > 0 ? "tag tag-success" : "tag tag-info"}>{differentiatorCount > 0 ? "已有可用防线" : "等待提取"}</span>}
          />
          <InfoCard
            icon={<AlertTriangle size={18} />}
            title="支撑与风险"
            description="支撑缺口、风险标签和未映射权利要求会在导出前继续参与质量门禁。"
            tone={supportGapCount > 0 ? "warn" : "success"}
            meta={(
              <>
                <span className={supportGapCount > 0 ? "tag tag-warn" : "tag tag-success"}>{supportGapCount} 个缺口</span>
                <span className={riskTagCount > 0 ? "tag tag-warn" : "tag"}>{riskTagCount} 个风险标签</span>
              </>
            )}
          />
        </div>
      </SettingsGroup>

      <div className="quality-split-grid">
        <SettingsGroup
          title="防线建议"
          description="按人工可执行的兜底、补强和收敛动作展示。"
        >
          <div className="dense-list">
            {worksheet?.defense_recommendations.map((item, index) => (
              <InfoCard
                icon={<ShieldCheck size={18} />}
                title={`建议 ${index + 1}`}
                description={item}
                tone="success"
                key={`${item}-${index}`}
              />
            ))}
            {!worksheet && <EmptyMessage>生成工作表后显示防线建议。</EmptyMessage>}
            {worksheet && worksheet.defense_recommendations.length === 0 && <EmptyMessage>暂无防线建议。</EmptyMessage>}
          </div>
        </SettingsGroup>

        <SettingsGroup
          title="历史版本"
          description="保留不同来源与状态，便于回看防线演进。"
        >
          <div className="dense-list">
            {worksheets.map((item) => (
              <InfoCard
                title={item.created_at}
                description={`${item.feature_records.length} 个特征`}
                meta={(
                  <>
                    <span className="tag">{worksheetStatusLabel(item.status)}</span>
                    <span className="tag tag-info">{worksheetSourceLabel(item.source)}</span>
                  </>
                )}
                key={item.id}
              />
            ))}
            {worksheets.length === 0 && <EmptyMessage>暂无工作表历史版本。</EmptyMessage>}
          </div>
        </SettingsGroup>
      </div>

      <SettingsGroup
        title="特征记录"
        description="每个特征保留分类、权利要求映射和风险标签。长文本会在行内换行，不横向撑开页面。"
      >
        <div className="dense-list">
          {worksheet?.feature_records.map((record) => (
            <InfoCard
              icon={<ClipboardCheck size={18} />}
              title={record.text}
              description={record.risk_tags.length > 0 ? `风险标签：${record.risk_tags.join("；")}` : "暂无风险标签"}
              tone={record.risk_tags.length > 0 ? "warn" : "info"}
              meta={(
                <>
                  <span className={record.classification === "support_needed" ? "tag tag-warn" : "tag tag-info"}>
                    {featureClassificationLabel(record.classification)}
                  </span>
                  <span className="tag">{record.claim_refs.length > 0 ? record.claim_refs.join(" / ") : "未映射权利要求"}</span>
                </>
              )}
              key={record.feature_id}
            />
          ))}
          {!worksheet && <EmptyMessage>生成工作表后显示特征记录。</EmptyMessage>}
          {worksheet && worksheet.feature_records.length === 0 && <EmptyMessage>暂无特征记录。</EmptyMessage>}
        </div>
      </SettingsGroup>

      <SettingsGroup
        title="支撑缺口"
        description="正式导出前需要重点复核的说明书、实施例或证据缺口。"
      >
        <div className="dense-list">
          {worksheet?.support_gaps.map((gap, index) => (
            <InfoCard
              icon={<AlertTriangle size={18} />}
              title={`缺口 ${index + 1}`}
              description={gap}
              tone="warn"
              meta={<span className="tag tag-warn">需补强</span>}
              key={`${gap}-${index}`}
            />
          ))}
          {!worksheet && <EmptyMessage>生成工作表后显示支撑缺口。</EmptyMessage>}
          {worksheet && worksheet.support_gaps.length === 0 && <EmptyMessage>暂无支撑缺口。</EmptyMessage>}
        </div>
      </SettingsGroup>

      <ActionDock meta={worksheet ? `最新工作表包含 ${featureCount} 个特征和 ${supportGapCount} 个支撑缺口。` : "生成后将同步更新质量门禁摘要。"}>
        <button
          className="btn btn-primary"
          disabled={!project || busy === "claim-defense"}
          onClick={onGenerate}
          type="button"
        >
          <ShieldCheck size={18} />
          <span>生成工作表</span>
        </button>
      </ActionDock>
    </div>
  );
}

export function ReviewView({
  project,
  busy,
  onReview,
}: {
  project: ProjectRecord | null;
  busy: string;
  onReview: () => void;
}) {
  const findings = project?.package?.review_findings ?? [];
  const highCount = findings.filter((finding) => finding.severity === "high").length;
  const mediumCount = findings.filter((finding) => finding.severity === "medium").length;
  const lowCount = findings.filter((finding) => finding.severity === "low").length;

  return (
    <div className="grid gap-4">
      <StatusStrip
        aria-label="审查意见状态"
        items={[
          { label: "审查项目", value: project?.package ? project.name : "待生成申请文本" },
          { label: "高风险", value: `${highCount} 项` },
          { label: "中风险", value: `${mediumCount} 项` },
          { label: "低风险", value: `${lowCount} 项` },
        ]}
      />

      <SectionHead
        title="审查意见"
        description={project?.package ? "围绕可授权性、清楚性、支撑性和导出前风险生成审查意见。" : "生成申请文本后可审查。"}
        actions={(
          <button className="btn btn-primary" disabled={!project?.package || busy === "review"} onClick={onReview} type="button">
            <Search size={18} />
            <span>审查</span>
          </button>
        )}
      />

      <SettingsGroup
        title="审查发现"
        description="按严重程度展示风险、建议和证据，避免正式稿风险被埋在长段落里。"
      >
        <div className="dense-list">
          {findings.map((finding: ReviewFinding, index) => (
            <InfoCard
              icon={finding.severity === "high" ? <AlertTriangle size={18} /> : finding.severity === "medium" ? <Info size={18} /> : <CheckCircle2 size={18} />}
              title={finding.category}
              description={finding.message}
              tone={severityTone(finding.severity)}
              meta={(
                <>
                  <span className={severityTagClass(finding.severity)}>{severityLabel(finding.severity)}</span>
                  <span className="tag">建议：{finding.suggestion}</span>
                  {finding.evidence && <span className="tag tag-info">证据：{finding.evidence}</span>}
                </>
              )}
              key={`${finding.category}-${index}`}
            />
          ))}
          {findings.length === 0 && <EmptyMessage>暂无审查意见。</EmptyMessage>}
        </div>
      </SettingsGroup>

      <ActionDock meta={findings.length > 0 ? `共 ${findings.length} 条审查意见，高风险 ${highCount} 条。` : "审查后会在这里汇总风险级别。"}>
        <button className="btn btn-primary" disabled={!project?.package || busy === "review"} onClick={onReview} type="button">
          <Search size={18} />
          <span>审查</span>
        </button>
      </ActionDock>
    </div>
  );
}
