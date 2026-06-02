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
  ShieldCheck,
  UsersRound,
  Wand2,
  type LucideIcon,
} from "lucide-react";

import type {
  ClaimDefenseWorksheet,
  DisclosureRun,
  DraftCompletionRun,
  FilingReadinessReport,
  PatentPointCandidate,
  ProjectMaterial,
  ProjectRecord,
} from "./api";
import { canExportPackage } from "./domain";

export type MainSectionId = "generate" | "projects" | "expert";

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

export type GuidedStepId = "idea" | "invention" | "draft" | "quality" | "export";
export type GuidedStepStatus = "done" | "current" | "ready" | "locked";
export type PatentGoalMode = "stable" | "broad" | "fast" | "moat";

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
  patentPoints: PatentPointCandidate[];
  filingReports: FilingReadinessReport[];
  worksheets: ClaimDefenseWorksheet[];
  completionRuns: DraftCompletionRun[];
};

export type GuidedFlowState = {
  currentStepId: GuidedStepId;
  steps: GuidedStepState[];
  processedMaterialCount: number;
  hasIdea: boolean;
  hasCompletedDisclosure: boolean;
  hasInventionCandidates: boolean;
  hasConfirmedInventionPoint: boolean;
  draftReady: boolean;
  qualityChecked: boolean;
  exportReady: boolean;
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

export const mainSections: Array<NavEntry<MainSectionId>> = [
  { id: "generate", label: "专利生成", description: "从一句想法到可导出文件", icon: Wand2 },
  { id: "projects", label: "项目", description: "查看历史项目和运行记录", icon: FolderKanban },
  { id: "expert", label: "专家工具", description: "进入旧工作台和高级检查", icon: Gauge },
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
      { id: "deliberate", label: "多 Agent 会审", description: "生成撰写策略", icon: UsersRound },
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
  { id: "draft", label: "生成初稿", description: "生成摘要、权利要求书和说明书。" },
  { id: "quality", label: "质量检查", description: "运行提交成熟度、权利要求防线和初稿完善。" },
  { id: "export", label: "导出", description: "确认风险并导出正式稿和内部报告。" },
];

export const guidedStepLabels = guidedStepDefinitions.map((step) => step.label);

export function deriveGuidedFlowState(input: GuidedFlowInput): GuidedFlowState {
  const processedMaterialCount = input.materials.filter((material) => material.status === "processed").length;
  const hasIdea = Boolean(input.project?.draft_text.trim());
  const hasCompletedDisclosure = input.disclosures.some((run) => run.status === "completed" && run.package);
  const draftReady = canExportPackage(input.project?.package);
  const hasInventionCandidates = hasCompletedDisclosure || input.patentPoints.length > 0;
  const hasConfirmedInventionPoint = draftReady || input.patentPoints.some((point) => point.selected);
  const qualityChecked = Boolean(
    input.filingReports.length
      && input.worksheets.length
      && input.completionRuns.some((run) => run.status === "completed"),
  );
  const exportReady = draftReady && qualityChecked;

  let currentStepId: GuidedStepId = "idea";
  if (!hasIdea) {
    currentStepId = "idea";
  } else if (!hasConfirmedInventionPoint && !draftReady) {
    currentStepId = "invention";
  } else if (!draftReady) {
    currentStepId = "draft";
  } else if (!qualityChecked) {
    currentStepId = "quality";
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
    draftReady,
    qualityChecked,
    exportReady,
  };
}

function stepStatusForIndex(index: number, currentIndex: number, hasIdea: boolean): GuidedStepStatus {
  if (!hasIdea && index > 0) return "locked";
  if (index < currentIndex) return "done";
  if (index === currentIndex) return "current";
  return "ready";
}

export function qualitySummaryFromRuns(input: {
  filingReport: FilingReadinessReport | null;
  worksheet: ClaimDefenseWorksheet | null;
  completionRun: DraftCompletionRun | null;
}): QualitySummary {
  const completion = input.completionRun?.scorecard ?? null;
  const statusLabel =
    input.filingReport?.status === "high_risk"
      ? "高风险但可导出"
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
    officialExportAllowed: explicitOfficialAllowed ?? true,
  };
}
