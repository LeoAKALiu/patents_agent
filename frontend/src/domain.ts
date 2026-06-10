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
  type LucideIcon,
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
  { id: "deliberate", label: "多智能体会审", icon: UsersRound },
  { id: "write", label: "分步撰写", icon: PenLine },
  { id: "readiness", label: "提交成熟度", icon: ClipboardCheck },
  { id: "claimDefense", label: "权利要求防线", icon: Scale },
  { id: "completion", label: "初稿完善", icon: Gauge },
  { id: "review", label: "审查修改", icon: SearchCheck },
  { id: "export", label: "导出", icon: Download },
] satisfies Array<{ id: WorkspaceTabId; label: string; icon: LucideIcon }>;

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

export function pipelineRunStatusLabel(status: string): string {
  if (status === "completed") return "已完成";
  if (status === "blocked") return "已阻断";
  if (status === "failed") return "失败";
  if (status === "running" || status === "in_progress") return "运行中";
  if (status === "queued") return "排队中";
  if (status === "interrupted") return "已中断";
  if (status === "pending") return "等待中";
  return status || "未知";
}

export function worksheetStatusLabel(status: string): string {
  if (status === "draft") return "草稿";
  if (status === "reviewed") return "已审阅";
  if (status === "superseded") return "已替代";
  return status || "未知";
}

export function worksheetSourceLabel(source: string): string {
  if (source === "generated_package") return "生成稿";
  if (source === "manual") return "手工编辑";
  if (source === "imported") return "外部导入";
  return source || "未知";
}

export function completionPatchStatusLabel(status: string): string {
  if (status === "proposed") return "待确认";
  if (status === "accepted") return "已接受";
  if (status === "rejected") return "已拒绝";
  if (status === "superseded") return "已替代";
  return status || "未知";
}

export function completionTaskStatusLabel(status: string): string {
  if (status === "open") return "待处理";
  if (status === "proposed") return "已提议";
  if (status === "accepted") return "已接受";
  if (status === "rejected") return "已拒绝";
  if (status === "superseded") return "已替代";
  return status || "未知";
}

export function completionPatchKindLabel(kind: string): string {
  if (kind === "insert") return "插入";
  if (kind === "replace") return "替换";
  if (kind === "delete") return "删除";
  if (kind === "rewrite") return "改写";
  if (kind === "sidecar_only") return "仅侧车记录";
  return kind || "未知";
}

export function draftSectionLabel(section: string): string {
  if (section === "claims") return "权利要求书";
  if (section === "abstract") return "摘要";
  if (section === "summary") return "发明内容";
  if (section === "description") return "说明书";
  if (section === "drawing_description" || section === "drawings") return "附图说明";
  if (section === "embodiments") return "具体实施方式";
  return section || "未知";
}

export function agentDoctorStatusLabel(status: string): string {
  if (status === "ready") return "就绪";
  if (status === "blocked") return "已阻断";
  if (status === "degraded") return "降级可用";
  if (status === "partial") return "部分可用";
  return status === "unknown" || !status ? "未知" : status;
}

export function agentRunModeLabel(mode: string): string {
  if (mode === "full") return "完整会审";
  if (mode === "fast") return "快速会审";
  if (mode === "minimal") return "精简会审";
  if (mode === "partial") return "部分可用";
  if (mode === "blocked") return "已阻断";
  if (mode === "ready") return "就绪";
  return mode === "unknown" || !mode ? "未知" : mode;
}

export function deliberationRunModeLabel(mode: string): string {
  if (mode === "full") return "完整会审";
  if (mode === "fast") return "快速会审";
  if (mode === "minimal") return "精简会审";
  if (mode === "partial") return "部分会审";
  if (mode === "blocked") return "已阻断";
  return mode || "未知";
}

export function logLevelLabel(level: string): string {
  if (level === "error") return "错误";
  if (level === "warn" || level === "warning") return "警告";
  if (level === "info") return "信息";
  return level || "日志";
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

export function latestCompletedDeliberation<T extends {
  status: string;
  providers?: string[];
  failures?: unknown[];
  strategy_brief?: unknown;
  stage_results?: Array<{ phase?: string; label?: string; status?: string }>;
}>(
  runs: T[],
): T | null {
  return runs.find(isStrictCompletedDeliberation) ?? null;
}

export function isStrictCompletedDeliberation(run: {
  status: string;
  providers?: string[];
  failures?: unknown[];
  strategy_brief?: unknown;
  stage_results?: Array<{ phase?: string; label?: string; status?: string }>;
}): boolean {
  if (run.status !== "completed" || !run.strategy_brief || (run.failures?.length ?? 0) > 0) return false;
  const providers = new Set(run.providers ?? []);
  if (!["codex", "gemini", "claude"].every((provider) => providers.has(provider))) return false;
  const completed = (run.stage_results ?? []).filter((stage) => stage.status === "completed");
  const labels = new Set(completed.map((stage) => stage.label ?? ""));
  if (!["opening codex", "opening gemini", "opening claude"].every((label) => labels.has(label))) return false;
  if (!["pair codex-vs-gemini", "pair codex-vs-claude", "pair gemini-vs-claude"].every((label) => labels.has(label))) return false;
  return completed.some((stage) => stage.phase === "chair" && stage.label === "chair synthesis");
}
