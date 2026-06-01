import {
  BookOpen,
  ClipboardCheck,
  ClipboardList,
  Database,
  Download,
  FilePlus2,
  Gauge,
  PenLine,
  Scale,
  SearchCheck,
  ShieldCheck,
  UsersRound,
} from "lucide-react";

export type WorkspaceTabId =
  | "build"
  | "corpus"
  | "create"
  | "moat"
  | "materials"
  | "deliberate"
  | "write"
  | "readiness"
  | "claimDefense"
  | "completion"
  | "review"
  | "export";

export const workspaceTabs = [
  { id: "build", label: "语料库建设", icon: Database },
  { id: "corpus", label: "知识库", icon: BookOpen },
  { id: "create", label: "创建专利项目", icon: FilePlus2 },
  { id: "moat", label: "护城河地图", icon: ShieldCheck },
  { id: "materials", label: "前置材料", icon: ClipboardList },
  { id: "deliberate", label: "多 Agent 会审", icon: UsersRound },
  { id: "write", label: "分步撰写", icon: PenLine },
  { id: "readiness", label: "提交成熟度", icon: ClipboardCheck },
  { id: "claimDefense", label: "权利要求防线", icon: Scale },
  { id: "completion", label: "初稿完善", icon: Gauge },
  { id: "review", label: "审查修改", icon: SearchCheck },
  { id: "export", label: "导出", icon: Download },
] satisfies Array<{ id: WorkspaceTabId; label: string; icon: typeof BookOpen }>;

export function canExportPackage(
  value: { title?: string; claims?: string } | null | undefined,
): boolean {
  return Boolean(value?.title?.trim() && value?.claims?.trim());
}

export function severityLabel(severity: string): string {
  if (severity === "high") return "高";
  if (severity === "medium") return "中";
  return "低";
}

export function evidenceStatusLabel(status: string): string {
  if (status === "verified") return "已验证";
  if (status === "feasible_unverified") return "可行未验证";
  if (status === "needs_experiment") return "需实验";
  return "模型生成";
}

export function sourceTypeLabel(source: string): string {
  if (source === "user") return "用户输入";
  if (source === "imported") return "材料导入";
  return "模型生成";
}

export function readinessStatusLabel(status: string): string {
  if (status === "clean") return "干净";
  if (status === "warning") return "有警告";
  return "高风险";
}

export function featureClassificationLabel(value: string): string {
  if (value === "known_base") return "已知基础";
  if (value === "differentiator") return "区别特征";
  if (value === "core_combo") return "核心组合";
  if (value === "dependent_fallback") return "从属兜底";
  return "需支撑";
}

export function completionCategoryLabel(category: string): string {
  if (category === "claim_support_gap") return "权利要求支撑缺口";
  if (category === "specification_sufficiency_gap") return "说明书充分公开缺口";
  if (category === "figure_consistency_gap") return "附图一致性缺口";
  if (category === "term_definition_gap") return "术语定义缺口";
  if (category === "prior_art_distinction_gap") return "现有技术差异缺口";
  if (category === "unverified_scheme_gap") return "未验证方案风险";
  if (category === "format_pollution") return "格式污染";
  if (category === "subject_matter_risk") return "客体风险";
  if (category === "claim_scope_risk") return "保护范围风险";
  return "不利表述";
}

export function completionTargetLabel(target: string): string {
  if (target === "claim") return "权利要求";
  if (target === "description") return "说明书";
  if (target === "drawing") return "附图";
  if (target === "embodiment") return "实施例";
  if (target === "term") return "术语";
  if (target === "evidence") return "证据";
  if (target === "prior_art") return "现有技术";
  return "导出";
}

export function completionScoreAverage<T extends { overall: number }>(scorecard: T): number {
  return scorecard.overall;
}

export function moatScoreTotal(scores: {
  scope_width: number;
  designaround_difficulty: number;
  feasibility: number;
  support_strength: number;
  prior_art_distance: number;
  strategic_value: number;
}): number {
  return Number(
    (
      scores.scope_width * 0.18
      + scores.designaround_difficulty * 0.18
      + scores.feasibility * 0.16
      + scores.support_strength * 0.16
      + scores.prior_art_distance * 0.16
      + scores.strategic_value * 0.16
    ).toFixed(3),
  );
}

export function splitLines(value: string): string[] {
  return value
    .split(/[\n,，;；]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function latestCompletedDeliberation<T extends { status: string }>(
  runs: T[],
): T | null {
  return runs.find((run) => run.status === "completed") ?? null;
}
