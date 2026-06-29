/**
 * Quality-check expert views — extracted from App.tsx (M3-B').
 * ClaimDefenseView (权利要求防线) + ReviewView (审查意见).
 */
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileText,
  Info,
  Scale,
  Search,
  ShieldCheck,
} from "@/lib/icons";
import {
  grantabilityReportUrl,
  type GrantabilityReport,
  type ClaimDefenseWorksheet,
  type ProjectKnowledgeOverview,
  type ProjectRecord,
  type ReviewFinding,
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

function grantabilityStatusLabel(status: string): string {
  if (status === "high") return "授权前景较强";
  if (status === "medium") return "授权前景中等";
  if (status === "uncertain") return "证据不足";
  return "授权风险较高";
}

function grantabilityTone(status: string, failClosed: boolean): "danger" | "warn" | "success" | "info" {
  if (failClosed || status === "low") return "danger";
  if (status === "uncertain" || status === "medium") return "warn";
  if (status === "high") return "success";
  return "info";
}

const blockingKnowledgeFlags = new Set([
  "synthetic_evidence",
  "empty_corpus",
  "needs_search",
  "failed",
  "insufficient_corpus",
  "candidates_need_confirmation",
  "stale_project_snapshot",
]);

function isGrantabilityKnowledgeReady(projectKnowledge: ProjectKnowledgeOverview | null): boolean {
  const state = projectKnowledge?.state;
  if (!state) return false;
  if (state.status !== "ready") return false;
  if (state.document_count < 2) return false;
  return !state.quality_flags.some((flag) => (
    blockingKnowledgeFlags.has(flag)
    || flag.includes("synthetic")
    || flag.includes("empty")
    || flag.includes("needs_search")
    || flag.includes("failed")
    || flag.includes("insufficient")
  ));
}

function knowledgeGateCopy(projectKnowledge: ProjectKnowledgeOverview | null): string {
  const state = projectKnowledge?.state;
  if (isGrantabilityKnowledgeReady(projectKnowledge) && state) {
    return `项目语料库已就绪：已入库 ${state.document_count} 件文献，可用于授权前景分析。`;
  }
  if (!state) {
    return "项目语料库未就绪：可以生成草案，但授权前景和权利要求防线只能输出证据不足结论。";
  }
  const reasons: string[] = [];
  if (state.status !== "ready") {
    reasons.push(`当前状态为 ${state.status}`);
  }
  if (state.document_count < 2) {
    reasons.push(`入库文献仅 ${state.document_count} 件`);
  }
  const blockingFlags = state.quality_flags.filter((flag) => (
    blockingKnowledgeFlags.has(flag)
    || flag.includes("synthetic")
    || flag.includes("empty")
    || flag.includes("needs_search")
    || flag.includes("failed")
    || flag.includes("insufficient")
  ));
  if (blockingFlags.length) {
    reasons.push(`质量标记：${blockingFlags.join("、")}`);
  }
  return `项目语料库仍受证据门控：${reasons.join("；")}。可以生成草案，但授权前景和权利要求防线只能输出证据不足或 gated 结论。`;
}

export function GrantabilityView({
  project,
  projectKnowledge,
  report,
  reports,
  busy,
  onGenerate,
}: {
  project: ProjectRecord | null;
  projectKnowledge: ProjectKnowledgeOverview | null;
  report: GrantabilityReport | null;
  reports: GrantabilityReport[];
  busy: string;
  onGenerate: () => void;
}) {
  const chartCount = report?.claim_chart.length ?? 0;
  const noveltyStrong = report?.novelty_attacks.filter((attack) => attack.attack_strength === "strong").length ?? 0;
  const inventiveStrong = report?.inventive_step_attacks.filter((attack) => attack.attack_strength === "strong").length ?? 0;
  const lowEvidenceCount = report?.low_evidence_flags.length ?? 0;
  const tone = report ? grantabilityTone(report.status, report.fail_closed) : "info";

  return (
    <div className="grid gap-4">
      <StatusStrip
        aria-label="授权前景状态"
        items={[
          { label: "当前状态", value: report ? grantabilityStatusLabel(report.status) : "未生成" },
          { label: "Claim Chart", value: `${chartCount} 项` },
          { label: "强攻击", value: `${noveltyStrong + inventiveStrong} 项` },
          { label: "证据标记", value: `${lowEvidenceCount} 项` },
        ]}
      />

      <SectionHead
        title="授权前景"
        description={project?.package ? "基于当前申请文本、交底查新、发明点和 Deep Research 结果生成新颖性与创造性攻击分析。" : "生成申请文本后可运行授权前景分析。"}
        actions={(
          <button
            className="btn btn-primary"
            disabled={!project?.package || busy === "grantability"}
            onClick={onGenerate}
            type="button"
          >
            <Search size={18} />
            <span>生成报告</span>
          </button>
        )}
      />

      <p className="text-sm text-[var(--text-primary)]/65">{knowledgeGateCopy(projectKnowledge)}</p>

      <SettingsGroup title="结论摘要" description="低证据场景默认 fail closed，不把少量或重复文献包装成高可授权性。">
        <div className="boundary-grid">
          <InfoCard
            icon={report?.fail_closed ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
            title={report ? grantabilityStatusLabel(report.status) : "等待生成"}
            description={report?.overall_assessment || "运行后显示整体授权前景、主要风险和建议收敛方向。"}
            tone={tone}
            meta={report ? <span className={`tag tag-${tone}`}>{report.fail_closed ? "Fail closed" : "可复核"}</span> : <span className="tag">无报告</span>}
          />
          <InfoCard
            icon={<FileText size={18} />}
            title="最接近现有技术"
            description={report?.closest_prior_art_summary || "报告会汇总最接近文献和引用来源。"}
            tone={report?.closest_prior_art_summary ? "info" : "warn"}
            meta={<span className="tag">{report?.source_ledger_citations.length ?? 0} 条引用</span>}
          />
        </div>
      </SettingsGroup>

      <div className="quality-split-grid">
        <SettingsGroup title="Claim Chart" description="逐项映射权利要求特征、现有技术覆盖和建议收窄方向。">
          <div className="dense-list">
            {report?.claim_chart.map((row, index) => (
              <InfoCard
                icon={<Scale size={18} />}
                title={row.claim_ref || `特征 ${index + 1}`}
                description={row.feature_text}
                tone={row.overbreadth_risk ? "warn" : "info"}
                meta={(
                  <>
                    <span className={row.overbreadth_risk ? "tag tag-warn" : "tag tag-info"}>{row.support_status}</span>
                    <span className="tag">{row.closest_prior_art_refs.length} 个现有技术引用</span>
                  </>
                )}
                key={`${row.claim_ref}-${index}`}
              >
                {row.novelty_distinction && <p>{row.novelty_distinction}</p>}
                {row.recommended_scope_adjustment && <p>{row.recommended_scope_adjustment}</p>}
              </InfoCard>
            ))}
            {!report && <EmptyMessage>生成报告后显示 Claim Chart。</EmptyMessage>}
            {report && report.claim_chart.length === 0 && <EmptyMessage>暂无可映射特征。</EmptyMessage>}
          </div>
        </SettingsGroup>

        <SettingsGroup title="风险与历史" description="新颖性、创造性攻击和历史报告分开留痕。">
          <div className="dense-list">
            {report?.novelty_attacks.map((attack, index) => (
              <InfoCard
                icon={<AlertTriangle size={18} />}
                title={`新颖性攻击 ${index + 1}`}
                description={attack.overlap_analysis || attack.feature_text}
                tone={severityTone(attack.attack_strength === "strong" ? "high" : attack.attack_strength === "moderate" ? "medium" : "low")}
                meta={<span className={severityTagClass(attack.attack_strength === "strong" ? "high" : attack.attack_strength === "moderate" ? "medium" : "low")}>{attack.attack_strength}</span>}
                key={`${attack.feature_text}-${index}`}
              />
            ))}
            {report?.inventive_step_attacks.map((attack, index) => (
              <InfoCard
                icon={<ShieldCheck size={18} />}
                title={`创造性组合 ${index + 1}`}
                description={attack.combination_rationale || attack.defense_suggestion}
                tone={severityTone(attack.attack_strength === "strong" ? "high" : attack.attack_strength === "moderate" ? "medium" : "low")}
                meta={<span className={severityTagClass(attack.attack_strength === "strong" ? "high" : attack.attack_strength === "moderate" ? "medium" : "low")}>{attack.attack_strength}</span>}
                key={`${attack.title}-${index}`}
              />
            ))}
            {report?.low_evidence_flags.map((flag, index) => (
              <InfoCard
                icon={<Info size={18} />}
                title={`证据标记 ${index + 1}`}
                description={flag}
                tone="warn"
                key={`${flag}-${index}`}
              />
            ))}
            {!report && <EmptyMessage>生成报告后显示风险条目。</EmptyMessage>}
            {report && !report.novelty_attacks.length && !report.inventive_step_attacks.length && !report.low_evidence_flags.length && (
              <EmptyMessage>暂无额外风险条目。</EmptyMessage>
            )}
            {reports.map((item) => (
              <InfoCard
                title={item.created_at}
                description={`${item.claim_chart.length} 个特征，${item.source_ledger_citations.length} 条引用`}
                meta={<span className="tag">{grantabilityStatusLabel(item.status)}</span>}
                key={item.id}
              />
            ))}
          </div>
        </SettingsGroup>
      </div>

      <ActionDock meta={report ? `最新报告：${grantabilityStatusLabel(report.status)}，${chartCount} 个特征映射。` : "生成后可导出 Markdown 报告供代理师复核。"}>
        <button
          className="btn btn-primary"
          disabled={!project?.package || busy === "grantability"}
          onClick={onGenerate}
          type="button"
        >
          <Search size={18} />
          <span>生成报告</span>
        </button>
        {project && report && (
          <a className="btn btn-secondary" href={grantabilityReportUrl(project.id, report.id)}>
            <Download size={18} />
            <span>导出报告</span>
          </a>
        )}
      </ActionDock>
    </div>
  );
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
