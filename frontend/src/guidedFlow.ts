import {
  BookOpen,
  ClipboardCheck,
  ClipboardList,
  Database,
  Download,
  FolderKanban,
  Gauge,
  PenLine,
  Scale,
  SearchCheck,
  Settings as SettingsIcon,
  ShieldCheck,
  UsersRound,
  Wand2,
  type LucideIcon,
} from "lucide-react";

import type {
  ClaimDefenseWorksheet,
  DeliberationRun,
  DisclosureRun,
  DraftCompletionRun,
  ExternalDraftIntakeRun,
  ExternalDraftSource,
  FilingReadinessReport,
  FormulaNeedAssessment,
  FormulaRun,
  OfficialCompileRun,
  PatentPointCandidate,
  PatentPointCreatePayload,
  PatentType,
  PostDraftReviewRun,
  ProjectMaterial,
  ProjectRecord,
} from "./api";

export type { PatentType };
import { canExportPackage, latestCompletedDeliberation } from "./domain";

export type MainSectionId = "generate" | "utility" | "projects" | "expert" | "settings";

export type ExpertToolId =
  | "build"
  | "corpus"
  | "moat"
  | "materials"
  | "deliberate"
  | "write"
  | "readiness"
  | "claimDefense"
  | "completion"
  | "review"
  | "export";

export type GuidedStepId =
  | "idea"
  | "invention"
  | "deliberation"
  | "formula"
  | "draft"
  | "quality"
  | "officialCompile"
  | "postReview"
  | "export";
export type GuidedStepStatus = "done" | "current" | "ready" | "locked";
export type PatentGoalMode = "stable" | "broad" | "fast" | "utility" | "moat";
export type StartChoiceId = "invention" | "utility" | "external";

export type NavEntry<T extends string> = {
  id: T;
  label: string;
  description: string;
  icon: LucideIcon;
};

export type ExpertToolGroup = {
  id: string;
  label: string;
  tools: Array<NavEntry<ExpertToolId>>;
};

export type GuidedStepState = {
  id: GuidedStepId;
  label: string;
  description: string;
  status: GuidedStepStatus;
};

export type GuidedFlowInput = {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  disclosures: DisclosureRun[];
  deliberations: DeliberationRun[];
  patentPoints: PatentPointCandidate[];
  formulaRequirement?: FormulaNeedAssessment | null;
  formulaRuns?: FormulaRun[];
  filingReports: FilingReadinessReport[];
  worksheets: ClaimDefenseWorksheet[];
  completionRuns: DraftCompletionRun[];
  externalDraftSources?: ExternalDraftSource[];
  externalDraftIntakeRuns?: ExternalDraftIntakeRun[];
  officialCompileRuns?: OfficialCompileRun[];
  currentSourceDraftHash?: string;
  postDraftReviews?: PostDraftReviewRun[];
};

export type GuidedFlowState = {
  currentStepId: GuidedStepId;
  steps: GuidedStepState[];
  processedMaterialCount: number;
  hasIdea: boolean;
  hasCompletedDisclosure: boolean;
  hasInventionCandidates: boolean;
  hasConfirmedInventionPoint: boolean;
  hasCompletedDeliberation: boolean;
  formulaRequired: boolean;
  hasCompletedFormula: boolean;
  hasExternalDraftSource: boolean;
  hasCompletedExternalDraftIntake: boolean;
  hasExternalDraftIntakeNeedsReview: boolean;
  draftReady: boolean;
  qualityChecked: boolean;
  hasCompletedOfficialCompile: boolean;
  hasPassedPostDraftReview: boolean;
  exportReady: boolean;
  utilityModelLite: boolean;
};

export type QualitySummary = {
  statusLabel: string;
  authorizationStability: number | null;
  protectionScope: number | null;
  filingMaturity: number | null;
  issueCount: number;
  supportGapCount: number;
  taskCount: number;
  officialExportAllowed: boolean;
};

export type GuidedOperationLog = {
  label: string;
  elapsedSeconds: number;
  lines: string[];
};

export type PatentPointSelectionPayload = {
  candidateId: string;
  payload: PatentPointCreatePayload;
};

export const v1StartChoices: Array<{
  id: StartChoiceId;
  label: string;
  description: string;
}> = [
  {
    id: "invention",
    label: "从技术想法撰写发明专利",
    description: "输入技术问题、方案和效果，进入发明点确认、会审、初稿和正式导出。",
  },
  {
    id: "utility",
    label: "从结构方案撰写实用新型",
    description: "聚焦产品结构、部件连接关系、安装位置和附图说明，跳过发明专属重步骤。",
  },
  {
    id: "external",
    label: "导入已有稿件进行润色提升",
    description: "上传或粘贴已有 Markdown/DOCX 初稿，解析章节后进入质量检查和正式稿清理。",
  },
];

export const defaultMainSectionId: MainSectionId = "generate";
export const defaultExpertToolId: ExpertToolId = "build";
export const utilityModelModePrefix = "目标模式：实用新型轻量版。";

export const patentTypeOptions: Array<{ id: PatentType; label: string; description: string }> = [
  {
    id: "invention",
    label: "发明专利",
    description: "覆盖方法、算法、系统或产品的技术方案，需要会审、公式和权利要求完整论证。",
  },
  {
    id: "utility_model",
    label: "实用新型专利",
    description: "聚焦产品结构、部件连接关系、安装位置与附图，强调结构效果，跳过会审等发明专属步骤。",
  },
];

export const patentGoalModes: Array<{ id: PatentGoalMode; label: string; description: string }> = [
  { id: "stable", label: "授权稳健", description: "收紧独权，强调组合闭环和说明书支撑。" },
  { id: "broad", label: "保护范围优先", description: "先上位覆盖，再用从权兜底替代实现。" },
  { id: "fast", label: "快速初稿", description: "优先生成可审阅的完整初稿。" },
  { id: "utility", label: "实用新型轻量版", description: "结构与附图优先，跳过会审和公式重步骤。" },
  { id: "moat", label: "专利护城河", description: "允许可行未验证方案进入内部策略和分案布局。" },
];

export const ideaPatentGoalModes = patentGoalModes.filter((mode) => mode.id !== "utility");

export function projectGoalPrefix(mode: PatentGoalMode): string {
  if (mode === "stable") return "目标模式：授权稳健。";
  if (mode === "broad") return "目标模式：保护范围优先。";
  if (mode === "fast") return "目标模式：快速初稿。";
  if (mode === "utility") {
    return `${utilityModelModePrefix}专利类型：实用新型；请优先提炼产品结构、部件连接关系、安装位置、附图编号和结构效果，避免把纯方法、算法或业务规则作为独立保护主题。`;
  }
  return "目标模式：专利护城河，允许可行未验证方案进入内部策略。";
}

export function isUtilityModelProject(project: ProjectRecord | null | undefined): boolean {
  if (!project) return false;
  // Explicit utility_model always wins.
  if (project.patent_type === "utility_model") return true;
  // Fallback: legacy text-based detection (catches pre-PR3 projects
  // and projects created without an explicit patent_type).
  const draftText = project.draft_text ?? "";
  return draftText.includes(utilityModelModePrefix) || draftText.includes("专利类型：实用新型");
}

export const mainSections: Array<NavEntry<MainSectionId>> = [
  { id: "generate", label: "开始", description: "选择一种默认路径进入 v1.1.0 向导", icon: Wand2 },
  { id: "projects", label: "项目", description: "查看历史项目和运行记录", icon: FolderKanban },
  { id: "settings", label: "设置", description: "本机 LLM 服务参数与 API Key", icon: SettingsIcon },
];

export const expertToolGroups: ExpertToolGroup[] = [
  {
    id: "knowledge",
    label: "知识库",
    tools: [
      { id: "build", label: "语料库建设", description: "导入官方导出物", icon: Database },
      { id: "corpus", label: "知识库检索", description: "检索授权专利片段", icon: BookOpen },
    ],
  },
  {
    id: "invention",
    label: "发明点",
    tools: [{ id: "moat", label: "护城河地图", description: "管理发明点和证据状态", icon: ShieldCheck }],
  },
  {
    id: "strategy",
    label: "交底与策略",
    tools: [
      { id: "materials", label: "前置材料", description: "生成交底书和候选发明点", icon: ClipboardList },
      { id: "deliberate", label: "多智能体会审", description: "生成撰写策略", icon: UsersRound },
      { id: "write", label: "分步撰写", description: "手动生成申请文本", icon: PenLine },
    ],
  },
  {
    id: "quality",
    label: "质检",
    tools: [
      { id: "readiness", label: "提交成熟度", description: "检查正式稿清洁度", icon: ClipboardCheck },
      { id: "claimDefense", label: "权利要求防线", description: "分析区别特征和支撑缺口", icon: Scale },
      { id: "completion", label: "初稿完善", description: "生成补强任务和候选补丁", icon: Gauge },
      { id: "review", label: "审查修改", description: "生成审查意见", icon: SearchCheck },
    ],
  },
  {
    id: "export",
    label: "导出",
    tools: [{ id: "export", label: "导出文件", description: "导出正式稿和内部稿", icon: Download }],
  },
];

export const guidedStepDefinitions: Array<Omit<GuidedStepState, "status">> = [
  { id: "idea", label: "想法与材料", description: "输入一句想法，上传可选材料。" },
  { id: "invention", label: "发明点", description: "确认主发明点、证据状态和护城河方向。" },
  { id: "deliberation", label: "多智能体会审", description: "会审权利要求边界、说明书支撑和规避风险。" },
  { id: "formula", label: "核心公式", description: "凝练算法公式、变量定义和权利要求落点。" },
  { id: "draft", label: "生成初稿", description: "生成摘要、权利要求书和说明书。" },
  { id: "quality", label: "质量检查", description: "运行提交成熟度、权利要求防线和初稿完善。" },
  { id: "officialCompile", label: "正式稿编译", description: "清除内部痕迹，生成可提交正式稿包。" },
  { id: "postReview", label: "成稿会审", description: "提交前强制审查权利要求、说明书支撑、清污和技术硬度。" },
  { id: "export", label: "导出", description: "确认风险并导出正式稿和内部报告。" },
];

export const guidedStepLabels = guidedStepDefinitions.map((step) => step.label);

export type GuidedActionGate = {
  allowed: boolean;
  reason: string;
};

/** Whether the user may open this step in the guided navigator (view-only; does not advance workflow). */
export function canNavigateToGuidedStep(step: Pick<GuidedStepState, "status">): boolean {
  return step.status === "done" || step.status === "current";
}

/** Block panel actions when the user is browsing a non-current step. */
export function currentStepActionGate(
  workflowStepId: GuidedStepId,
  displayedStepId: GuidedStepId,
): GuidedActionGate {
  if (displayedStepId !== workflowStepId) {
    return { allowed: false, reason: "请先在流程导航中回到当前步骤再继续操作。" };
  }
  return { allowed: true, reason: "" };
}

export function qualityActionGate(
  state: GuidedFlowState,
  workflowStepId: GuidedStepId,
  displayedStepId: GuidedStepId,
): GuidedActionGate {
  const stepGate = currentStepActionGate(workflowStepId, displayedStepId);
  if (!stepGate.allowed) {
    return stepGate;
  }
  if (!state.draftReady) {
    return { allowed: false, reason: "请先生成专利初稿后再运行质量检查。" };
  }
  return { allowed: true, reason: "" };
}

export function officialCompileActionGate(
  state: GuidedFlowState,
  workflowStepId: GuidedStepId,
  displayedStepId: GuidedStepId,
): GuidedActionGate {
  const stepGate = currentStepActionGate(workflowStepId, displayedStepId);
  if (!stepGate.allowed) {
    return stepGate;
  }
  if (!state.draftReady) {
    return { allowed: false, reason: "请先生成专利初稿。" };
  }
  if (!state.qualityChecked) {
    return { allowed: false, reason: "请先完成质量检查后再编译正式稿。" };
  }
  return { allowed: true, reason: "" };
}

export function postDraftReviewActionGate(
  state: GuidedFlowState,
  workflowStepId: GuidedStepId,
  displayedStepId: GuidedStepId,
): GuidedActionGate {
  const stepGate = currentStepActionGate(workflowStepId, displayedStepId);
  if (!stepGate.allowed) {
    return stepGate;
  }
  if (!state.draftReady) {
    return { allowed: false, reason: "请先生成专利初稿。" };
  }
  if (!state.hasCompletedOfficialCompile) {
    return { allowed: false, reason: "请先完成正式稿编译后再启动成稿会审。" };
  }
  return { allowed: true, reason: "" };
}

/** Resolve which step panel to show while preserving workflow gates. */
export function resolveGuidedViewStep(
  workflowStepId: GuidedStepId,
  manualViewStepId: GuidedStepId | null,
  steps: GuidedStepState[],
): GuidedStepId {
  if (!manualViewStepId) {
    return workflowStepId;
  }
  const manualStep = steps.find((step) => step.id === manualViewStepId);
  if (!manualStep || !canNavigateToGuidedStep(manualStep)) {
    return workflowStepId;
  }
  return manualViewStepId;
}

export function guidedStepStatusLabel(status: GuidedStepStatus): string {
  if (status === "done") return "已完成";
  if (status === "current") return "当前步骤";
  if (status === "ready") return "可查看";
  return "未解锁";
}

export function guidedNextActionLabel(stepId: GuidedStepId): string {
  if (stepId === "idea") return "填写并创建项目";
  if (stepId === "invention") return "提炼发明点";
  if (stepId === "deliberation") return "启动多智能体会审";
  if (stepId === "formula") return "凝练核心公式";
  if (stepId === "draft") return "生成专利初稿";
  if (stepId === "quality") return "运行质量检查";
  if (stepId === "officialCompile") return "编译正式稿";
  if (stepId === "postReview") return "启动成稿会审";
  return "打开导出工具";
}

export function guidedNextActionDescription(stepId: GuidedStepId): string {
  if (stepId === "idea") return "先创建项目；已有稿件可从第三个入口导入。";
  if (stepId === "invention") return "生成候选发明点和护城河方向，然后人工确认主线。";
  if (stepId === "deliberation") return "收敛权利要求边界、说明书支撑和规避路径。";
  if (stepId === "formula") return "当项目包含算法/指标信号时，先生成公式包再写入初稿。";
  if (stepId === "draft") return "基于已确认材料生成摘要、权利要求书、说明书和附图说明。";
  if (stepId === "quality") return "串行运行提交成熟度、权利要求防线和初稿完善。";
  if (stepId === "officialCompile") return "清除内部痕迹，生成只包含正式申请内容的提交包。";
  if (stepId === "postReview") return "正式导出前复核成稿哈希、权利要求质量和清污结果。";
  return "正式稿、内部稿和侧车报告分离导出；提交前仍需专业人员复核。";
}

export function deriveGuidedFlowState(input: GuidedFlowInput): GuidedFlowState {
  const processedMaterialCount = input.materials.filter((material) => material.status === "processed").length;
  const hasIdea = Boolean(input.project?.draft_text.trim());
  const utilityModelLite = isUtilityModelProject(input.project);
  const hasCompletedDisclosure = input.disclosures.some((run) => run.status === "completed" && run.package);
  const draftReady = canExportPackage(input.project?.package);
  const externalDraftSources = input.externalDraftSources ?? [];
  const externalDraftIntakeRuns = input.externalDraftIntakeRuns ?? [];
  const hasExternalDraftSource = externalDraftSources.length > 0;
  const hasCompletedExternalDraftIntake = externalDraftIntakeRuns.some((run) => run.status === "completed");
  const hasExternalDraftIntakeNeedsReview = externalDraftIntakeRuns.some((run) => run.status === "needs_review");
  const hasInventionCandidates = hasCompletedDisclosure || input.patentPoints.length > 0;
  const hasConfirmedInventionPoint = draftReady || input.patentPoints.some((point) => point.selected);
  const hasCompletedDeliberation = draftReady || utilityModelLite || Boolean(latestCompletedDeliberation(input.deliberations));
  const formulaRequired = !utilityModelLite && Boolean(input.formulaRequirement?.required);
  const hasCompletedFormula = draftReady || !formulaRequired || Boolean(input.formulaRuns?.some((run) => run.status === "completed" && run.package));
  const qualityChecked = Boolean(
    input.filingReports.length
      && input.worksheets.length
      && input.completionRuns.some((run) => run.status === "completed"),
  );
  const currentOfficialCompileRun = selectCurrentOfficialCompileRun(
    input.officialCompileRuns ?? [],
    input.currentSourceDraftHash,
  );
  const hasCompletedOfficialCompile = Boolean(currentOfficialCompileRun);
  const latestMatchingPostDraftReview = selectLatestMatchingPostDraftReview(
    input.postDraftReviews ?? [],
    currentOfficialCompileRun,
  );
  const hasPassedPostDraftReview = Boolean(
    latestMatchingPostDraftReview?.export_allowed,
  );
  const exportReady = draftReady && qualityChecked && hasCompletedOfficialCompile && hasPassedPostDraftReview;

  let currentStepId: GuidedStepId = "idea";
  if (!hasIdea) {
    currentStepId = "idea";
  } else if (!hasConfirmedInventionPoint && !draftReady) {
    currentStepId = "invention";
  } else if (!hasCompletedDeliberation && !draftReady) {
    currentStepId = "deliberation";
  } else if (!hasCompletedFormula && !draftReady) {
    currentStepId = "formula";
  } else if (!draftReady) {
    currentStepId = "draft";
  } else if (!qualityChecked) {
    currentStepId = "quality";
  } else if (!hasCompletedOfficialCompile) {
    currentStepId = "officialCompile";
  } else if (!hasPassedPostDraftReview) {
    currentStepId = "postReview";
  } else {
    currentStepId = "export";
  }

  const currentIndex = guidedStepDefinitions.findIndex((step) => step.id === currentStepId);
  const steps = guidedStepDefinitions.map((step, index) => ({
    ...step,
    status: stepStatusForIndex(index, currentIndex, hasIdea),
  }));

  return {
    currentStepId,
    steps,
    processedMaterialCount,
    hasIdea,
    hasCompletedDisclosure,
    hasInventionCandidates,
    hasConfirmedInventionPoint,
    hasCompletedDeliberation,
    formulaRequired,
    hasCompletedFormula,
    hasExternalDraftSource,
    hasCompletedExternalDraftIntake,
    hasExternalDraftIntakeNeedsReview,
    draftReady,
    qualityChecked,
    hasCompletedOfficialCompile,
    hasPassedPostDraftReview,
    exportReady,
    utilityModelLite,
  };
}

function isMatchingPostDraftReview(review: PostDraftReviewRun, compile: OfficialCompileRun): boolean {
  return Boolean(
    review.status === "completed"
      && compile.official_package_hash
      && compile.source_draft_hash
      && review.official_compile_run_id === compile.id
      && review.official_package_hash === compile.official_package_hash
      && review.draft_package_hash === compile.source_draft_hash,
  );
}

export function selectLatestMatchingPostDraftReview(
  reviews: PostDraftReviewRun[],
  compile: OfficialCompileRun | null,
): PostDraftReviewRun | null {
  if (!compile) {
    return null;
  }
  return reviews.reduce<PostDraftReviewRun | null>((latest, review) => {
    if (!isMatchingPostDraftReview(review, compile)) {
      return latest;
    }
    if (!latest) {
      return review;
    }
    return postDraftReviewTime(review) > postDraftReviewTime(latest) ? review : latest;
  }, null);
}

function postDraftReviewTime(review: PostDraftReviewRun): number {
  return Date.parse(review.updated_at || review.created_at || "") || 0;
}

export function selectCurrentOfficialCompileRun(
  runs: OfficialCompileRun[],
  currentSourceDraftHash?: string,
): OfficialCompileRun | null {
  return runs.find((run) =>
    run.status === "completed"
      && run.official_package
      && run.official_package_hash
      && (!currentSourceDraftHash || run.source_draft_hash === currentSourceDraftHash),
  ) ?? null;
}

function stepStatusForIndex(index: number, currentIndex: number, hasIdea: boolean): GuidedStepStatus {
  if (!hasIdea && index > 0) return "locked";
  if (index < currentIndex) return "done";
  if (index === currentIndex) return "current";
  return "locked";
}

export function qualitySummaryFromRuns(input: {
  filingReport: FilingReadinessReport | null;
  worksheet: ClaimDefenseWorksheet | null;
  completionRun: DraftCompletionRun | null;
}): QualitySummary {
  const completion = input.completionRun?.scorecard ?? null;
  const statusLabel =
    input.filingReport?.status === "high_risk"
      ? "高风险，等待成稿会审"
      : input.filingReport?.status === "warning"
        ? "建议补强"
        : input.filingReport
          ? "可导出"
          : "尚未检查";
  const explicitOfficialAllowed = (
    input.filingReport as (FilingReadinessReport & { official_export_allowed?: boolean }) | null
  )?.official_export_allowed;

  return {
    statusLabel,
    authorizationStability: completion?.authorization_stability ?? null,
    protectionScope: completion?.protection_scope ?? null,
    filingMaturity: completion?.filing_maturity ?? null,
    issueCount: input.filingReport?.issues.length ?? 0,
    supportGapCount: input.worksheet?.support_gaps.length ?? 0,
    taskCount: input.completionRun?.tasks.length ?? 0,
    officialExportAllowed: explicitOfficialAllowed ?? false,
  };
}

export function guidedBusyLabel(value: string): string {
  if (value === "guided-quality") return "正在运行质量检查";
  if (value === "official-compile") return "正在编译正式稿";
  if (value === "post-draft-review") return "正在运行成稿会审";
  if (value === "score-improve") return "正在一键提升分数";
  if (value === "disclosure") return "正在提炼发明点";
  if (value === "generate") return "正在生成专利初稿";
  if (value === "formula") return "正在凝练核心公式";
  if (value === "guided-create") return "正在创建专利项目";
  if (value === "material-upload") return "正在上传材料";
  if (value === "external-draft-upload") return "正在上传外部初稿";
  if (value === "patent-point-select") return "正在保存主路线和后备路线";
  if (value === "project-delete") return "正在删除项目";
  if (value === "claim-defense") return "正在生成权利要求防线";
  if (value === "filing-readiness") return "正在检查提交成熟度";
  if (value === "completion") return "正在运行初稿完善";
  if (value === "review") return "正在生成审查意见";
  if (value === "deliberate") return "正在启动多智能体会审";
  if (value === "corpus-run") return "正在运行语料导入";
  if (value === "corpus-upload") return "正在上传语料文件";
  if (value === "corpus-job") return "正在创建语料任务";
  if (value === "import") return "正在导入专利文件";
  if (value === "search") return "正在检索知识库";
  if (value === "refresh") return "正在刷新工作台";
  if (value.startsWith("completion-")) return "正在处理补强建议";
  return value ? "正在处理" : "";
}

export function guidedOperationLog(value: string, elapsedSeconds = 0): GuidedOperationLog | null {
  if (!value) return null;
  const safeElapsed = Math.max(0, Math.floor(elapsedSeconds));
  const lines = operationLogSteps(value)
    .filter((step) => step.at <= safeElapsed)
    .map((step) => `[${formatElapsed(step.at)}] ${step.text}`);
  return {
    label: guidedBusyLabel(value),
    elapsedSeconds: safeElapsed,
    lines: lines.length ? lines : [`[00:00] ${guidedBusyLabel(value) || "操作已启动"}`],
  };
}

export function buildPatentPointSelectionPayloads(
  selectedPoint: PatentPointCandidate,
  candidatePool: PatentPointCandidate[],
): PatentPointSelectionPayload[] {
  const seen = new Set<string>();
  const orderedCandidates = [selectedPoint, ...candidatePool].filter((candidate) => {
    if (seen.has(candidate.id)) return false;
    seen.add(candidate.id);
    return true;
  });
  return orderedCandidates.map((candidate) => ({
    candidateId: candidate.id,
    payload: {
      source_candidate_id: candidate.id,
      title: candidate.title,
      technical_problem: candidate.technical_problem,
      innovation: candidate.innovation,
      technical_solution: candidate.technical_solution,
      beneficial_effects: candidate.beneficial_effects,
      protection_focus: candidate.protection_focus,
      evidence_status: candidate.evidence_status,
      source_type: candidate.source_type,
      feasibility_basis: candidate.feasibility_basis,
      support_gaps: candidate.support_gaps,
      experiment_needed: candidate.experiment_needed,
      moat_scores: candidate.moat_scores,
      claim_chart: candidate.claim_chart,
      selected: candidate.id === selectedPoint.id,
      rationale: candidate.id === selectedPoint.id ? candidate.rationale : candidate.rationale || "未选中的候选后备路线",
    },
  }));
}

function operationLogSteps(value: string): Array<{ at: number; text: string }> {
  const commonModelSteps = [
    { at: 0, text: "启动任务，锁定当前项目快照" },
    { at: 3, text: "读取项目、材料、候选路线和历史运行记录" },
    { at: 8, text: "组装专利审查上下文与提示词" },
    { at: 15, text: "调用模型或外部 agent 服务" },
    { at: 25, text: "等待模型或服务返回" },
    { at: 45, text: "解析结构化结果并准备写入项目" },
  ];
  if (value === "deliberate") {
    return [
      { at: 0, text: "启动多智能体会审，锁定项目和发明点" },
      { at: 4, text: "分发会审任务到可用 agent" },
      { at: 12, text: "收集权利要求边界、说明书支撑和风险控制意见" },
      { at: 25, text: "等待模型或服务返回" },
      { at: 50, text: "合并冲突意见并生成会审策略" },
    ];
  }
  if (value === "formula") {
    return [
      { at: 0, text: "读取项目、发明点、会审策略和交底书" },
      { at: 4, text: "识别公式型信号和变量关系" },
      { at: 10, text: "凝练核心公式、变量定义和权利要求落点" },
      { at: 25, text: "等待模型或服务返回" },
      { at: 45, text: "生成 LaTeX 公式包并写入项目" },
    ];
  }
  if (value === "post-draft-review") {
    return [
      { at: 0, text: "启动成稿后多智能体会审，锁定当前成稿哈希" },
      { at: 4, text: "分发权利要求、清污和技术硬度审查角色" },
      { at: 12, text: "收集阻断项、污染命中和可提交补丁建议" },
      { at: 25, text: "等待模型或服务返回" },
      { at: 45, text: "主席综合裁决并写入导出门禁" },
    ];
  }
  if (value === "official-compile") {
    return [
      { at: 0, text: "锁定当前初稿快照" },
      { at: 2, text: "移除内部提示、会审痕迹和非正式内容" },
      { at: 5, text: "检查正式稿必备章节和交叉项目污染" },
      { at: 8, text: "生成正式稿包、hash 和编译报告" },
    ];
  }
  if (value === "score-improve") {
    return [
      { at: 0, text: "启动一键提升分数，读取当前初稿" },
      { at: 3, text: "按通用专利审查标准重新评分" },
      { at: 8, text: "生成可进入正式稿的补强补丁" },
      { at: 15, text: "应用安全补丁并保留未验证边界" },
      { at: 25, text: "重新评分并写入项目运行记录" },
      { at: 40, text: "等待模型或服务返回" },
    ];
  }
  if (value === "patent-point-select") {
    return [
      { at: 0, text: "保存选中的主路线" },
      { at: 1, text: "写入未选路线到后备路线池" },
      { at: 2, text: "刷新项目发明点列表" },
    ];
  }
  if (value.includes("upload") || value.includes("delete") || value.includes("create") || value === "search" || value === "refresh") {
    return [
      { at: 0, text: "提交请求到本地服务" },
      { at: 1, text: "写入或读取项目数据" },
      { at: 2, text: "刷新界面状态" },
    ];
  }
  return commonModelSteps;
}

function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}
