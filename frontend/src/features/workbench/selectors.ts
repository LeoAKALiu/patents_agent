import type { ExportReadiness, PostDraftReviewRun } from "@/api";
import type { ProjectWorkspaceState } from "@/features/projects/ProjectWorkspace";
import {
  deriveGuidedFlowState,
  guidedBusyLabel,
  guidedNextActionDescription,
  guidedNextActionLabel,
  guidedProgressActionBlockReason,
  type GuidedStepId,
  type GuidedStepState,
} from "@/guidedFlow";

export type WorkbenchPrimaryTarget =
  | "workbench-start"
  | "documents"
  | "knowledge"
  | "expert"
  | "export";

export interface WorkbenchState {
  hasProject: boolean;
  projectName: string;
  currentStepId: GuidedStepId;
  phaseGroups: WorkbenchPhase[];
  stepGroups: Array<{ label: string; steps: GuidedStepState[] }>;
  nextAction: { label: string; description: string };
  primaryTarget: WorkbenchPrimaryTarget;
  primaryActionBlockReason: string;
  riskSummary: {
    blockingCount: number;
    issueCount: number;
    exportLocked: boolean;
    exportReady: boolean;
  };
  runSummary: { label: string; busy: boolean };
}

export interface WorkbenchPhase {
  label: "输入" | "提炼" | "成稿" | "质检修复" | "导出";
  status: "done" | "current" | "locked";
  stepIds: GuidedStepId[];
}

export interface WorkbenchStateInput {
  projectState: ProjectWorkspaceState;
  exportReadiness?: ExportReadiness | null;
}

export function deriveWorkbenchState(input: WorkbenchStateInput): WorkbenchState {
  const guidedState = deriveGuidedFlowState({
    project: input.projectState.selectedProject,
    materials: input.projectState.projectMaterials,
    disclosures: input.projectState.disclosureRuns,
    deliberations: input.projectState.deliberationRuns,
    patentPoints: input.projectState.visiblePatentPoints,
    formulaRequirement: input.projectState.formulaRequirement,
    formulaRuns: input.projectState.formulaRuns,
    filingReports: input.projectState.filingReports,
    worksheets: input.projectState.worksheets,
    completionRuns: input.projectState.completionRuns,
    externalDraftSources: input.projectState.externalDraftSources,
    externalDraftIntakeRuns: input.projectState.externalDraftIntakeRuns,
    officialCompileRuns: input.projectState.officialCompileRuns,
    currentSourceDraftHash: input.projectState.currentSourceDraftHash,
    postDraftReviews: input.projectState.postDraftReviews,
  });
  const hasProject = Boolean(input.projectState.selectedProject);
  const latestReview = latestPostDraftReview(input.projectState.postDraftReviews);
  const riskSummary = deriveRiskSummary(input.exportReadiness, latestReview, guidedState.exportReady);
  const nextAction = deriveNextAction({
    hasProject,
    currentStepId: guidedState.currentStepId,
    exportReady: riskSummary.exportReady,
    exportBlocked: riskSummary.exportLocked && riskSummary.blockingCount > 0,
  });

  return {
    hasProject,
    projectName: input.projectState.selectedProject?.name || "未选择项目",
    currentStepId: guidedState.currentStepId,
    phaseGroups: groupUserPhases(guidedState.steps),
    stepGroups: groupGuidedSteps(guidedState.steps),
    nextAction: {
      label: nextAction.label,
      description: nextAction.description,
    },
    primaryTarget: nextAction.target,
    primaryActionBlockReason: nextAction.target === "workbench-start"
      ? guidedProgressActionBlockReason({
        currentStepId: guidedState.currentStepId,
        selectedDeliberationProviders: input.projectState.selectedDeliberationProviders,
      })
      : "",
    riskSummary,
    runSummary: deriveRunSummary(input.projectState.busy),
  };
}

function groupGuidedSteps(steps: GuidedStepState[]): WorkbenchState["stepGroups"] {
  return [
    { label: "构思输入", steps: steps.slice(0, 2) },
    { label: "生成成稿", steps: steps.slice(2, 6) },
    { label: "提交放行", steps: steps.slice(6, 9) },
  ];
}

function groupUserPhases(steps: GuidedStepState[]): WorkbenchPhase[] {
  const phaseDefs: Array<Pick<WorkbenchPhase, "label" | "stepIds">> = [
    { label: "输入", stepIds: ["idea"] },
    { label: "提炼", stepIds: ["invention"] },
    { label: "成稿", stepIds: ["deliberation", "formula", "draft"] },
    { label: "质检修复", stepIds: ["quality", "officialCompile", "postReview"] },
    { label: "导出", stepIds: ["export"] },
  ];

  return phaseDefs.map((phase) => {
    const phaseSteps = steps.filter((step) => phase.stepIds.includes(step.id));
    const status: WorkbenchPhase["status"] = phaseSteps.some((step) => step.status === "current")
      ? "current"
      : phaseSteps.every((step) => step.status === "done")
        ? "done"
        : "locked";
    return { ...phase, status };
  });
}

function deriveNextAction(input: {
  hasProject: boolean;
  currentStepId: GuidedStepId;
  exportReady: boolean;
  exportBlocked: boolean;
}): { label: string; description: string; target: WorkbenchPrimaryTarget } {
  if (!input.hasProject) {
    return {
      label: "创建项目",
      description: "选择一种起步路径，创建或导入当前项目。",
      target: "workbench-start",
    };
  }
  if (input.exportBlocked) {
    return {
      label: "处理成稿会审阻断项",
      description: "先进入文稿与修复处理阻断项，再重新验证导出门禁。",
      target: "documents",
    };
  }
  if (input.exportReady) {
    return {
      label: "导出正式稿",
      description: "正式稿和提交门禁已放行，可以进入导出。",
      target: "export",
    };
  }
  return {
    label: guidedNextActionLabel(input.currentStepId),
    description: guidedNextActionDescription(input.currentStepId),
    target: "workbench-start",
  };
}

function deriveRunSummary(busy: string): WorkbenchState["runSummary"] {
  if (!busy) {
    return { label: "空闲", busy: false };
  }
  return {
    label: guidedBusyLabel(busy),
    busy: true,
  };
}
function deriveRiskSummary(
  exportReadiness: ExportReadiness | null | undefined,
  latestReview: PostDraftReviewRun | null,
  guidedExportReady: boolean,
): WorkbenchState["riskSummary"] {
  const blockingItems = new Set<string>();
  for (const issue of exportReadiness?.review_blocking_issues ?? []) {
    addNonEmpty(blockingItems, issue);
  }
  for (const item of exportReadiness?.compile_blocked_items ?? []) {
    const sortedRecord = Object.fromEntries(
      Object.entries(item).sort(([a], [b]) => a.localeCompare(b))
    );
    addNonEmpty(blockingItems, JSON.stringify(sortedRecord));
  }
  collectReviewBlockingIssues(latestReview).forEach((issue) => addNonEmpty(blockingItems, issue));

  const issueItems = new Set(blockingItems);
  collectReviewContaminationHits(latestReview).forEach((issue) => addNonEmpty(issueItems, issue));

  const exportReady = Boolean(
    exportReadiness?.export_allowed
      || exportReadiness?.next_action === "export_ready"
      || guidedExportReady,
  );
  const readinessBlocked = exportReadiness?.review_gate_status === "blocked"
    || exportReadiness?.review_gate_status === "needs_revision"
    || exportReadiness?.compile_status === "blocked";
  const reviewBlocked = Boolean(
    latestReview
      && latestReview.status === "completed"
      && !latestReview.export_allowed
      && blockingItems.size > 0,
  );

  return {
    blockingCount: blockingItems.size,
    issueCount: issueItems.size,
    exportLocked: Boolean(!exportReady && (readinessBlocked || reviewBlocked || blockingItems.size > 0)),
    exportReady,
  };
}

function latestPostDraftReview(reviews: PostDraftReviewRun[]): PostDraftReviewRun | null {
  return reviews.reduce<PostDraftReviewRun | null>((latest, review) => {
    if (!latest) return review;
    return reviewTime(review) > reviewTime(latest) ? review : latest;
  }, null);
}

function reviewTime(review: PostDraftReviewRun): number {
  return Date.parse(review.updated_at || review.created_at || "") || 0;
}

function collectReviewBlockingIssues(review: PostDraftReviewRun | null): string[] {
  if (!review) return [];
  return [
    ...review.blocking_issues,
    ...(review.chair_result?.blocking_issues ?? []),
    ...review.role_results.flatMap((result) => result.blocking_issues),
  ];
}

function collectReviewContaminationHits(review: PostDraftReviewRun | null): string[] {
  if (!review) return [];
  return [
    ...review.contamination_hits,
    ...(review.chair_result?.contamination_hits ?? []),
    ...review.role_results.flatMap((result) => result.contamination_hits),
  ];
}

function addNonEmpty(items: Set<string>, value: string): void {
  const normalized = value.trim();
  if (normalized) {
    items.add(normalized);
  }
}
