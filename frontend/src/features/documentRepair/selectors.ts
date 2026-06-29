import type {
  DraftPackage,
  DraftPackageManualUpdate,
  ExportReadiness,
  FilingReadinessReport,
  FilingReadinessIssue,
  OfficialCompileRun,
  PostDraftReviewRun,
} from "@/api";
import type { ProjectWorkspaceState } from "@/features/projects/ProjectWorkspace";
import type { MainSectionId } from "@/guidedFlow";

export const APPROVED_GATE_STATES = [
  "可编辑",
  "当前有效",
  "已失效",
  "需要修复",
  "待重新验证",
  "导出锁定",
  "可导出",
  "运行中",
  "等待生成",
  "运行失败",
] as const;

export type GateState = (typeof APPROVED_GATE_STATES)[number];
export type DocumentRepairTabId = "overview" | "edit" | "issues" | "annotated" | "versions";
export type DocumentDraftFields = DraftPackageManualUpdate;
export type DocumentIssueKind = "阻断" | "风险" | "建议";
export type DocumentIssueSeverity = "严重" | "高" | "中" | "低";
export type DocumentIssueState =
  | "open"
  | "applied"
  | "pending_revalidation"
  | "resolved_by_new_review"
  | "dismissed";
export type DocumentVersionState = "当前有效" | "已失效" | "等待生成";

export interface GateNode {
  id: "internalDraft" | "quality" | "officialCompile" | "postDraftReview" | "export";
  label: string;
  state: GateState;
  detail: string;
}

export interface DraftStatusMetric {
  label: string;
  value: string;
}

export interface DraftStatusCardState {
  title: string;
  subtitle: string;
  state: GateState;
  actionLabel: string;
  tone: "internal" | "official";
  metrics: DraftStatusMetric[];
  notes: string[];
}

export interface IssueSummaryRow {
  id: string;
  level: "阻断" | "风险" | "建议" | "已处理";
  section: string;
  title: string;
}

export interface IssueSummaryState {
  blocking: number;
  risk: number;
  suggestion: number;
  resolved: number;
  topIssues: IssueSummaryRow[];
  explanation: string;
}

export interface DocumentIssueInboxRow {
  id: string;
  kind: DocumentIssueKind;
  severity: DocumentIssueSeverity;
  source: string;
  section: string;
  message: string;
  state: DocumentIssueState;
}

export interface DocumentIssueInboxState {
  rows: DocumentIssueInboxRow[];
  blockingCount: number;
  riskCount: number;
  suggestionCount: number;
}

export interface RecentRecordState {
  label: string;
  value: string;
  detail: string;
}

export interface DocumentVersionNode {
  id: GateNode["id"];
  label: string;
  state: DocumentVersionState;
  detail: string;
  timeLabel: string;
  shortHash?: string;
  fullHashes: Array<{ label: string; value: string }>;
}

export interface DocumentVersionChainState {
  conclusion: string;
  nodes: DocumentVersionNode[];
}

export interface DocumentRepairState {
  activeTab: DocumentRepairTabId;
  editableDraft: DocumentDraftFields | null;
  topConclusion: string;
  primaryAction: {
    label: string;
    targetTab?: DocumentRepairTabId;
    targetSection?: MainSectionId;
  };
  gates: {
    internalDraft: GateNode;
    quality: GateNode;
    officialCompile: GateNode;
    postDraftReview: GateNode;
    export: GateNode;
  };
  internalDraft: DraftStatusCardState;
  officialDraft: DraftStatusCardState;
  issueSummary: IssueSummaryState;
  issueInbox: DocumentIssueInboxState;
  versionChain: DocumentVersionChainState;
  recentRecords: RecentRecordState[];
}

export interface DocumentRepairStateInput {
  projectState: ProjectWorkspaceState;
  exportReadiness?: ExportReadiness | null;
  activeTab?: DocumentRepairTabId;
}

interface DocumentRepairFacts {
  draftPackage: DraftPackage | null;
  currentDraftHash: string;
  latestFilingReport: FilingReadinessReport | null;
  latestOfficialCompile: OfficialCompileRun | null;
  latestPostDraftReview: PostDraftReviewRun | null;
  hasInternalDraft: boolean;
  officialStale: boolean;
  reviewStale: boolean;
  exportReady: boolean;
  exportLocked: boolean;
  blockingIssues: string[];
  contaminationIssues: string[];
  compileBlockedItems: string[];
  suggestions: string[];
  resolvedCount: number;
}

export function deriveDocumentRepairState(input: DocumentRepairStateInput): DocumentRepairState {
  const activeTab = input.activeTab ?? "overview";
  const facts = deriveFacts(input.projectState, input.exportReadiness);
  const gates = deriveGates(input.projectState, input.exportReadiness, facts);
  const issueInbox = deriveIssueInbox(input.exportReadiness, facts);
  return {
    activeTab,
    editableDraft: facts.draftPackage ? editableDraftFields(facts.draftPackage) : null,
    topConclusion: deriveTopConclusion(input.exportReadiness, facts, gates),
    primaryAction: derivePrimaryAction(input.exportReadiness, facts, gates),
    gates,
    internalDraft: deriveInternalDraftCard(input.projectState, facts),
    officialDraft: deriveOfficialDraftCard(facts, gates.officialCompile),
    issueSummary: deriveIssueSummary(facts, issueInbox),
    issueInbox,
    versionChain: deriveVersionChain(input.exportReadiness, facts, gates),
    recentRecords: deriveRecentRecords(input.exportReadiness, facts, gates),
  };
}

function deriveFacts(
  projectState: ProjectWorkspaceState,
  exportReadiness: ExportReadiness | null | undefined,
): DocumentRepairFacts {
  const draftPackage = projectState.currentPackage ?? projectState.selectedProject?.package ?? null;
  const currentDraftHash = projectState.currentSourceDraftHash || projectState.currentDraftHash || "";
  const latestFilingReport = latestByTime(projectState.filingReports);
  const latestOfficialCompile = latestByTime(projectState.officialCompileRuns);
  const latestPostDraftReview = latestByTime(projectState.postDraftReviews);
  const hasInternalDraft = Boolean(draftPackage);
  const officialStale = Boolean(
    latestOfficialCompile
      && latestOfficialCompile.status === "completed"
      && currentDraftHash
      && latestOfficialCompile.source_draft_hash !== currentDraftHash,
  );
  const reviewStale = Boolean(
    latestPostDraftReview
      && latestOfficialCompile
      && latestPostDraftReview.status === "completed"
      && (
        (currentDraftHash && latestPostDraftReview.draft_package_hash !== currentDraftHash)
        || latestPostDraftReview.official_compile_run_id !== latestOfficialCompile.id
        || latestPostDraftReview.official_package_hash !== latestOfficialCompile.official_package_hash
      ),
  );
  const blockingIssues = uniqueStrings([
    ...(exportReadiness?.review_blocking_issues ?? []),
    ...collectReviewBlockingIssues(latestPostDraftReview),
  ]);
  const contaminationIssues = uniqueStrings(collectReviewContaminationHits(latestPostDraftReview));
  const compileBlockedItems = uniqueStrings([
    ...(exportReadiness?.compile_blocked_items ?? []).map(recordIssueText),
    ...(latestOfficialCompile?.blocked_items ?? []).map(recordIssueText),
  ]);
  const suggestions = uniqueStrings([
    ...(exportReadiness?.missing_quality_checks ?? []).map((item) => `${item} 待检查`),
    ...(exportReadiness?.stale_quality_checks ?? []).map((item) => `${item} 已失效`),
    ...(latestPostDraftReview?.role_results.flatMap((result) => result.rewrite_suggestions) ?? []),
    ...(latestPostDraftReview?.chair_result?.next_actions ?? []),
  ]);
  const resolvedCount = (
    latestOfficialCompile?.contamination_removed.length ?? 0
  ) + (
    latestPostDraftReview?.role_results.reduce(
      (count, result) => count + result.official_safe_patches.length,
      latestPostDraftReview.chair_result?.official_safe_patches.length ?? 0,
    ) ?? 0
  );
  const exportReady = Boolean(
    exportReadiness?.export_allowed
      || exportReadiness?.next_action === "export_ready"
      || (latestPostDraftReview?.status === "completed" && latestPostDraftReview.export_allowed && !reviewStale),
  );
  const exportLocked = Boolean(
    !exportReady
      && (
        exportReadiness?.review_gate_status === "blocked"
        || exportReadiness?.review_gate_status === "needs_revision"
        || exportReadiness?.compile_status === "blocked"
        || blockingIssues.length > 0
        || compileBlockedItems.length > 0
      ),
  );
  return {
    draftPackage,
    currentDraftHash,
    latestFilingReport,
    latestOfficialCompile,
    latestPostDraftReview,
    hasInternalDraft,
    officialStale,
    reviewStale,
    exportReady,
    exportLocked,
    blockingIssues,
    contaminationIssues,
    compileBlockedItems,
    suggestions,
    resolvedCount,
  };
}

function editableDraftFields(packageValue: DraftPackage): DocumentDraftFields {
  return {
    title: packageValue.title,
    abstract: packageValue.abstract,
    claims: packageValue.claims,
    description: packageValue.description,
    drawing_description: packageValue.drawing_description,
  };
}

function deriveGates(
  projectState: ProjectWorkspaceState,
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
): DocumentRepairState["gates"] {
  const internalDraftState: GateState = facts.hasInternalDraft
    ? projectState.busy === "generate" ? "运行中" : "可编辑"
    : "等待生成";
  const qualityState = deriveQualityGateState(projectState, exportReadiness, facts);
  const officialCompileState = deriveOfficialCompileGateState(exportReadiness, facts);
  const postDraftReviewState = derivePostDraftReviewGateState(exportReadiness, facts, officialCompileState);
  const exportState = deriveExportGateState(facts, officialCompileState, postDraftReviewState);
  return {
    internalDraft: {
      id: "internalDraft",
      label: "内部初稿",
      state: internalDraftState,
      detail: facts.hasInternalDraft ? "可继续编辑的内部工作稿。" : "生成内部初稿后才能进入后续门禁。",
    },
    quality: {
      id: "quality",
      label: "质量检查",
      state: qualityState,
      detail: qualityGateDetail(qualityState),
    },
    officialCompile: {
      id: "officialCompile",
      label: "正式稿编译",
      state: officialCompileState,
      detail: officialCompileGateDetail(officialCompileState),
    },
    postDraftReview: {
      id: "postDraftReview",
      label: "成稿会审",
      state: postDraftReviewState,
      detail: postDraftReviewGateDetail(postDraftReviewState),
    },
    export: {
      id: "export",
      label: "导出",
      state: exportState,
      detail: exportGateDetail(exportState),
    },
  };
}

function deriveQualityGateState(
  projectState: ProjectWorkspaceState,
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
): GateState {
  if (!facts.hasInternalDraft) return "等待生成";
  if (projectState.busy === "quality") return "运行中";
  if ((exportReadiness?.failed_quality_checks?.length ?? 0) > 0) return "运行失败";
  if (facts.latestFilingReport?.draft_package_hash === facts.currentDraftHash || exportReadiness?.quality_done) {
    return "当前有效";
  }
  if (
    exportReadiness?.quality_required
    || (exportReadiness?.missing_quality_checks?.length ?? 0) > 0
    || (exportReadiness?.stale_quality_checks?.length ?? 0) > 0
    || (exportReadiness?.unknown_quality_checks?.length ?? 0) > 0
  ) {
    return "待重新验证";
  }
  return "待重新验证";
}

function deriveOfficialCompileGateState(
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
): GateState {
  if (!facts.hasInternalDraft) return "等待生成";
  const compileStatus = exportReadiness?.compile_status ?? facts.latestOfficialCompile?.status;
  if (compileStatus === "queued" || compileStatus === "running") return "运行中";
  if (compileStatus === "failed") return "运行失败";
  if (compileStatus === "blocked" || facts.compileBlockedItems.length > 0) return "需要修复";
  if (!facts.latestOfficialCompile) return "等待生成";
  if (facts.officialStale || exportReadiness?.official_compile_required) return "已失效";
  if (facts.latestOfficialCompile.status === "completed") return "当前有效";
  return "等待生成";
}

function derivePostDraftReviewGateState(
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
  officialCompileState: GateState,
): GateState {
  const reviewStatus = exportReadiness?.review_gate_status ?? exportReadiness?.review_status ?? facts.latestPostDraftReview?.status;
  if (reviewStatus === "queued" || reviewStatus === "running") return "运行中";
  if (reviewStatus === "failed" || reviewStatus === "interrupted") return "运行失败";
  if (reviewStatus === "blocked" || reviewStatus === "needs_revision" || facts.blockingIssues.length > 0) {
    return "需要修复";
  }
  if (facts.latestPostDraftReview?.status === "completed" && facts.reviewStale) return "已失效";
  if (facts.exportReady) return "当前有效";
  if (officialCompileState === "当前有效") return "待重新验证";
  return "等待生成";
}

function deriveExportGateState(
  facts: DocumentRepairFacts,
  officialCompileState: GateState,
  postDraftReviewState: GateState,
): GateState {
  if (facts.exportReady) return "可导出";
  if (facts.exportLocked) return "导出锁定";
  if (!facts.hasInternalDraft) return "等待生成";
  if (officialCompileState === "运行失败" || postDraftReviewState === "运行失败") return "运行失败";
  if (postDraftReviewState === "运行中") return "运行中";
  return "等待生成";
}

function deriveTopConclusion(
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
  gates: DocumentRepairState["gates"],
): string {
  if (!facts.hasInternalDraft) return "当前项目尚未生成内部初稿。";
  const blockingCount = facts.blockingIssues.length + facts.compileBlockedItems.length;
  if (facts.exportReady) return "正式稿已通过导出门禁，可以导出正式稿。";
  if (facts.exportLocked) {
    return `当前文稿阻断导出，需先处理 ${Math.max(blockingCount, 1)} 个阻断项。`;
  }
  if (gates.officialCompile.state === "已失效" || exportReadiness?.official_compile_required) {
    return "当前正式稿已失效，需要重新编译正式稿。";
  }
  if (gates.quality.state === "待重新验证") {
    return "当前内部初稿需要重新质量检查。";
  }
  if (gates.postDraftReview.state === "待重新验证" || exportReadiness?.post_draft_review_required) {
    return "正式稿需要重新成稿会审后才能放行导出。";
  }
  return "当前文稿链路等待下一步处理。";
}

function derivePrimaryAction(
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
  gates: DocumentRepairState["gates"],
): DocumentRepairState["primaryAction"] {
  if (!facts.hasInternalDraft) return { label: "生成内部初稿", targetSection: "workbench" };
  if (facts.exportReady) return { label: "导出正式稿", targetSection: "export" };
  if (facts.exportLocked && facts.blockingIssues.length > 0) {
    return { label: "进入标注修复", targetTab: "annotated" };
  }
  if (facts.exportLocked) return { label: "查看问题", targetTab: "issues" };
  if (gates.quality.state === "待重新验证" || gates.quality.state === "运行失败") {
    return { label: "重新质量检查", targetSection: "workbench" };
  }
  if (gates.officialCompile.state === "已失效" || exportReadiness?.official_compile_required) {
    return { label: "重新编译正式稿", targetSection: "workbench" };
  }
  if (gates.postDraftReview.state === "待重新验证" || exportReadiness?.post_draft_review_required) {
    return { label: "重新成稿会审", targetSection: "workbench" };
  }
  return { label: "编辑文稿", targetTab: "edit" };
}

function deriveInternalDraftCard(
  projectState: ProjectWorkspaceState,
  facts: DocumentRepairFacts,
): DraftStatusCardState {
  const draft = facts.draftPackage;
  return {
    title: draft?.title || projectState.selectedProject?.name || "内部初稿",
    subtitle: "内部复核材料，可编辑工作稿",
    state: facts.hasInternalDraft ? "可编辑" : "等待生成",
    actionLabel: facts.hasInternalDraft ? "编辑文稿" : "生成初稿",
    tone: "internal",
    metrics: facts.hasInternalDraft
      ? [
          { label: "权利要求书", value: sectionLengthLabel(draft?.claims) },
          { label: "说明书", value: sectionLengthLabel(draft?.description) },
          { label: "摘要", value: sectionLengthLabel(draft?.abstract) },
        ]
      : [
          { label: "章节", value: "待生成" },
          { label: "保存状态", value: "等待生成" },
        ],
    notes: facts.hasInternalDraft
      ? ["编辑内部初稿后，旧正式稿与旧成稿会审需要重新验证。"]
      : ["生成内部初稿后才能进入质量检查、正式稿编译和成稿会审。"],
  };
}

function deriveOfficialDraftCard(
  facts: DocumentRepairFacts,
  gate: GateNode,
): DraftStatusCardState {
  const official = facts.latestOfficialCompile?.official_package;
  const exists = Boolean(official);
  return {
    title: official?.title || "尚未生成正式稿",
    subtitle: "正式提交稿，由内部初稿编译生成",
    state: gate.state,
    actionLabel: exists && gate.state !== "已失效" ? "查看正式稿" : "重新编译",
    tone: "official",
    metrics: exists
      ? [
          { label: "来源状态", value: facts.officialStale ? "来源已变更" : "来源当前" },
          { label: "清理状态", value: `${facts.latestOfficialCompile?.contamination_removed.length ?? 0} 项已清理` },
          { label: "导出状态", value: facts.exportReady ? "可导出" : "未放行" },
        ]
      : [
          { label: "生成状态", value: "等待生成" },
          { label: "导出状态", value: "未放行" },
        ],
    notes: exists
      ? ["正式稿是提交候选稿，不作为内部策略材料编辑。"]
      : ["需要先完成内部初稿，再编译正式稿。"],
  };
}

function deriveIssueSummary(
  facts: DocumentRepairFacts,
  issueInbox: DocumentIssueInboxState,
): IssueSummaryState {
  const rows: IssueSummaryRow[] = issueInbox.rows.map((row) => ({
    id: row.id,
    level: row.kind,
    section: row.section,
    title: truncate(row.message, 88),
  }));
  return {
    blocking: issueInbox.blockingCount,
    risk: issueInbox.riskCount,
    suggestion: issueInbox.suggestionCount,
    resolved: facts.resolvedCount,
    topIssues: rows.slice(0, 5),
    explanation: facts.exportLocked
      ? "先处理阻断项。保存初稿后，当前正式稿和旧成稿会审会失效，需要重新编译正式稿并重新成稿会审。"
      : "保持内部初稿、正式稿和成稿会审在同一版本链路上，再进入导出。",
  };
}

function deriveIssueInbox(
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
): DocumentIssueInboxState {
  const rows: DocumentIssueInboxRow[] = [];
  const seen = new Set<string>();
  const reviewState: DocumentIssueState = facts.reviewStale ? "pending_revalidation" : "open";
  const qualityState: DocumentIssueState = isFilingReportCurrent(facts.latestFilingReport, facts.currentDraftHash)
    ? "open"
    : "pending_revalidation";

  function addIssue(issue: Omit<DocumentIssueInboxRow, "id">): void {
    const message = truncate(sanitizeInlineText(issue.message), 118);
    if (!message) return;
    const key = `${issue.kind}:${message}`;
    if (seen.has(key)) return;
    seen.add(key);
    rows.push({
      ...issue,
      id: `issue-${rows.length + 1}`,
      message,
    });
  }

  for (const issue of exportReadiness?.review_blocking_issues ?? []) {
    addIssue({
      kind: "阻断",
      severity: "严重",
      source: "导出门禁",
      section: inferSectionLabel(issue),
      message: issue,
      state: "open",
    });
  }

  for (const issue of facts.latestPostDraftReview?.blocking_issues ?? []) {
    addIssue({
      kind: "阻断",
      severity: "严重",
      source: "成稿会审",
      section: inferSectionLabel(issue),
      message: issue,
      state: reviewState,
    });
  }

  for (const issue of facts.latestPostDraftReview?.chair_result?.blocking_issues ?? []) {
    addIssue({
      kind: "阻断",
      severity: "严重",
      source: "主席结论",
      section: inferSectionLabel(issue),
      message: issue,
      state: reviewState,
    });
  }

  for (const result of facts.latestPostDraftReview?.role_results ?? []) {
    for (const issue of result.blocking_issues) {
      addIssue({
        kind: "阻断",
        severity: "严重",
        source: roleSourceLabel(result.role),
        section: inferSectionLabel(issue),
        message: issue,
        state: reviewState,
      });
    }
    for (const hit of result.contamination_hits) {
      addIssue({
        kind: "风险",
        severity: "高",
        source: roleSourceLabel(result.role),
        section: inferSectionLabel(hit),
        message: hit,
        state: reviewState,
      });
    }
    for (const suggestion of result.rewrite_suggestions) {
      addIssue({
        kind: "建议",
        severity: "中",
        source: roleSourceLabel(result.role),
        section: inferSectionLabel(suggestion),
        message: suggestion,
        state: reviewState,
      });
    }
  }

  for (const hit of facts.latestPostDraftReview?.contamination_hits ?? []) {
    addIssue({
      kind: "风险",
      severity: "高",
      source: "污染扫描",
      section: inferSectionLabel(hit),
      message: hit,
      state: reviewState,
    });
  }

  for (const hit of facts.latestPostDraftReview?.chair_result?.contamination_hits ?? []) {
    addIssue({
      kind: "风险",
      severity: "高",
      source: "主席结论",
      section: inferSectionLabel(hit),
      message: hit,
      state: reviewState,
    });
  }

  for (const task of facts.latestPostDraftReview?.chair_result?.description_rewrite_tasks ?? []) {
    addIssue({
      kind: "建议",
      severity: "中",
      source: "主席说明书任务",
      section: "说明书",
      message: task,
      state: reviewState,
    });
  }

  for (const action of facts.latestPostDraftReview?.chair_result?.next_actions ?? []) {
    addIssue({
      kind: "建议",
      severity: "中",
      source: "主席下一步",
      section: inferSectionLabel(action),
      message: action,
      state: reviewState,
    });
  }

  for (const item of exportReadiness?.compile_blocked_items ?? []) {
    addIssue({
      kind: "阻断",
      severity: "严重",
      source: "正式稿编译",
      section: inferSectionLabel(recordIssueText(item)),
      message: recordIssueText(item) || "正式稿编译存在阻断项",
      state: "open",
    });
  }

  for (const item of facts.latestOfficialCompile?.blocked_items ?? []) {
    addIssue({
      kind: "阻断",
      severity: "严重",
      source: "正式稿编译",
      section: inferSectionLabel(recordIssueText(item)),
      message: recordIssueText(item) || "正式稿编译存在阻断项",
      state: facts.officialStale ? "pending_revalidation" : "open",
    });
  }

  for (const issue of facts.latestFilingReport?.issues ?? []) {
    addIssue({
      kind: filingIssueKind(issue),
      severity: filingIssueSeverity(issue),
      source: "质量检查",
      section: filingIssueSection(issue),
      message: issue.message || issue.suggestion || issue.category,
      state: qualityState,
    });
  }

  addQualityTaskRows(addIssue, exportReadiness);

  const blockingCount = rows.filter((row) => row.kind === "阻断").length;
  const riskCount = rows.filter((row) => row.kind === "风险").length;
  const suggestionCount = rows.filter((row) => row.kind === "建议").length;
  return { rows, blockingCount, riskCount, suggestionCount };
}

function deriveVersionChain(
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
  gates: DocumentRepairState["gates"],
): DocumentVersionChainState {
  const nodes: DocumentVersionNode[] = [
    {
      id: "internalDraft",
      label: "内部初稿",
      state: facts.hasInternalDraft ? "当前有效" : "等待生成",
      detail: facts.hasInternalDraft ? "当前可编辑工作稿。" : "需要先生成内部初稿。",
      timeLabel: facts.draftPackage ? "当前工作稿" : "暂无记录",
      shortHash: shortHash(facts.currentDraftHash),
      fullHashes: hashDetails([{ label: "内部初稿哈希", value: facts.currentDraftHash }]),
    },
    {
      id: "quality",
      label: "质量检查",
      state: qualityVersionState(gates.quality.state),
      detail: qualityVersionDetail(gates.quality.state),
      timeLabel: facts.latestFilingReport ? formatRecordTime(facts.latestFilingReport.created_at) : "暂无记录",
      shortHash: shortHash(facts.latestFilingReport?.draft_package_hash),
      fullHashes: hashDetails([{ label: "检查初稿哈希", value: facts.latestFilingReport?.draft_package_hash ?? "" }]),
    },
    {
      id: "officialCompile",
      label: "正式稿",
      state: artifactVersionState(gates.officialCompile.state),
      detail: facts.officialStale ? "正式稿来源不是当前内部初稿。" : gates.officialCompile.detail,
      timeLabel: facts.latestOfficialCompile ? formatRecordTime(facts.latestOfficialCompile.updated_at) : "暂无记录",
      shortHash: shortHash(facts.latestOfficialCompile?.official_package_hash),
      fullHashes: hashDetails([
        { label: "来源初稿哈希", value: facts.latestOfficialCompile?.source_draft_hash ?? "" },
        { label: "正式稿哈希", value: facts.latestOfficialCompile?.official_package_hash ?? "" },
      ]),
    },
    {
      id: "postDraftReview",
      label: "成稿会审",
      state: artifactVersionState(gates.postDraftReview.state),
      detail: facts.reviewStale ? "成稿会审不再匹配当前正式稿。" : gates.postDraftReview.detail,
      timeLabel: facts.latestPostDraftReview ? formatRecordTime(facts.latestPostDraftReview.updated_at) : "暂无记录",
      shortHash: shortHash(facts.latestPostDraftReview?.official_package_hash),
      fullHashes: hashDetails([
        { label: "会审初稿哈希", value: facts.latestPostDraftReview?.draft_package_hash ?? "" },
        { label: "会审正式稿哈希", value: facts.latestPostDraftReview?.official_package_hash ?? "" },
      ]),
    },
    {
      id: "export",
      label: "导出",
      state: exportVersionState(gates.export.state),
      detail: gates.export.detail,
      timeLabel: exportReadiness?.export_allowed ? "导出门禁已放行" : "等待导出门禁",
      shortHash: shortHash(exportReadiness?.official_package_hash),
      fullHashes: hashDetails([{ label: "导出正式稿哈希", value: exportReadiness?.official_package_hash ?? "" }]),
    },
  ];
  return {
    conclusion: versionConclusion(facts, gates),
    nodes,
  };
}

function deriveRecentRecords(
  exportReadiness: ExportReadiness | null | undefined,
  facts: DocumentRepairFacts,
  gates: DocumentRepairState["gates"],
): RecentRecordState[] {
  return [
    {
      label: "质量检查",
      value: gates.quality.state,
      detail: facts.latestFilingReport ? formatRecordTime(facts.latestFilingReport.created_at) : "暂无记录",
    },
    {
      label: "正式稿编译",
      value: gates.officialCompile.state,
      detail: facts.latestOfficialCompile ? formatRecordTime(facts.latestOfficialCompile.updated_at) : "暂无记录",
    },
    {
      label: "成稿会审",
      value: gates.postDraftReview.state,
      detail: facts.latestPostDraftReview ? formatRecordTime(facts.latestPostDraftReview.updated_at) : "暂无记录",
    },
    {
      label: "修复记录",
      value: `${facts.resolvedCount} 项已处理`,
      detail: facts.resolvedCount > 0 ? "包含清理与安全修复" : "暂无记录",
    },
    {
      label: "导出",
      value: exportReadiness?.export_allowed ? "可导出" : gates.export.state,
      detail: exportReadiness?.reason || "等待导出门禁",
    },
  ];
}

function addQualityTaskRows(
  addIssue: (issue: Omit<DocumentIssueInboxRow, "id">) => void,
  exportReadiness: ExportReadiness | null | undefined,
): void {
  for (const name of exportReadiness?.failed_quality_checks ?? []) {
    addIssue({
      kind: "阻断",
      severity: "严重",
      source: "质量检查",
      section: "全文",
      message: `${name} 失败，需要处理后重新检查`,
      state: "open",
    });
  }
  for (const name of exportReadiness?.stale_quality_checks ?? []) {
    addIssue({
      kind: "风险",
      severity: "中",
      source: "质量检查",
      section: "全文",
      message: `${name} 已失效，需要重新验证`,
      state: "pending_revalidation",
    });
  }
  for (const name of exportReadiness?.missing_quality_checks ?? []) {
    addIssue({
      kind: "风险",
      severity: "中",
      source: "质量检查",
      section: "全文",
      message: `${name} 尚未完成`,
      state: "open",
    });
  }
  for (const name of exportReadiness?.unknown_quality_checks ?? []) {
    addIssue({
      kind: "风险",
      severity: "低",
      source: "质量检查",
      section: "全文",
      message: `${name} 状态未知`,
      state: "open",
    });
  }
  for (const [name, state] of Object.entries(exportReadiness?.quality_check_states ?? {})) {
    if (state === "current") continue;
    addIssue({
      kind: state === "failed" ? "阻断" : "风险",
      severity: state === "failed" ? "严重" : "中",
      source: "质量检查",
      section: "全文",
      message: `${name} ${qualityTaskStateLabel(state)}`,
      state: state === "stale" ? "pending_revalidation" : "open",
    });
  }
}

function roleSourceLabel(role: PostDraftReviewRun["role_results"][number]["role"]): string {
  if (role === "claims_reviewer") return "成稿会审/权利要求";
  if (role === "spec_cleaner") return "成稿会审/说明书";
  return "成稿会审/技术稳健性";
}

function filingIssueKind(issue: FilingReadinessIssue): DocumentIssueKind {
  if (issue.severity === "high") return "阻断";
  if (issue.severity === "medium") return "风险";
  return "建议";
}

function filingIssueSeverity(issue: FilingReadinessIssue): DocumentIssueSeverity {
  if (issue.severity === "high") return "高";
  if (issue.severity === "medium") return "中";
  return "低";
}

function filingIssueSection(issue: FilingReadinessIssue): string {
  if (issue.target === "claims") return "权利要求书";
  if (issue.target === "abstract") return "摘要";
  if (issue.target === "drawings") return "附图说明";
  if (issue.target === "description") return "说明书";
  return "全文";
}

function isFilingReportCurrent(report: FilingReadinessReport | null, currentDraftHash: string): boolean {
  if (!report || !report.draft_package_hash || !currentDraftHash) return true;
  return report.draft_package_hash === currentDraftHash;
}

function qualityTaskStateLabel(state: string): string {
  if (state === "missing") return "尚未完成";
  if (state === "stale") return "已失效，需要重新验证";
  if (state === "failed") return "失败，需要处理";
  return "状态未知";
}

function qualityVersionState(state: GateState): DocumentVersionState {
  if (state === "当前有效") return "当前有效";
  if (state === "等待生成" || state === "运行中") return "等待生成";
  return "已失效";
}

function artifactVersionState(state: GateState): DocumentVersionState {
  if (state === "当前有效" || state === "可导出" || state === "可编辑") return "当前有效";
  if (state === "等待生成" || state === "运行中") return "等待生成";
  return "已失效";
}

function exportVersionState(state: GateState): DocumentVersionState {
  if (state === "可导出") return "当前有效";
  if (state === "等待生成" || state === "运行中") return "等待生成";
  return "已失效";
}

function qualityVersionDetail(state: GateState): string {
  if (state === "当前有效") return "质量检查匹配当前内部初稿。";
  if (state === "等待生成") return "等待内部初稿生成后检查。";
  if (state === "运行中") return "质量检查正在运行。";
  return "质量检查需要重新验证。";
}

function versionConclusion(
  facts: DocumentRepairFacts,
  gates: DocumentRepairState["gates"],
): string {
  if (!facts.hasInternalDraft) return "尚未生成内部初稿，版本链路等待开始。";
  if (
    facts.officialStale
    || facts.reviewStale
    || gates.officialCompile.state === "已失效"
    || gates.postDraftReview.state === "已失效"
  ) {
    return "当前内部初稿已修改，正式稿和成稿会审已失效，需重新编译正式稿。";
  }
  if (facts.exportReady) return "当前版本链路有效，可以导出正式稿。";
  if (gates.postDraftReview.state === "需要修复") return "成稿会审存在阻断项，导出仍被锁定。";
  return "保持内部初稿、质量检查、正式稿和成稿会审在同一版本链路上。";
}

function shortHash(value: string | undefined): string | undefined {
  if (!value) return undefined;
  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}

function hashDetails(values: Array<{ label: string; value: string }>): Array<{ label: string; value: string }> {
  return values.filter((item) => item.value.trim().length > 0);
}

function recordIssueText(record: Record<string, string>): string {
  const visibleValues = Object.entries(record)
    .filter(([key]) => !/(^|_)(id|run_id)$|hash|log|patch/i.test(key))
    .map(([, value]) => value)
    .filter(Boolean);
  return sanitizeInlineText(visibleValues.join(" "));
}

function sanitizeInlineText(value: string): string {
  return value
    .replace(/\b[a-f0-9]{16,}\b/gi, "哈希已隐藏")
    .replace(/\b(?:run|compile|review)-[A-Za-z0-9-]{8,}\b/g, "记录已隐藏")
    .replace(/\s+/g, " ")
    .trim();
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

function latestByTime<T extends { created_at: string; updated_at?: string }>(items: T[]): T | null {
  return items.reduce<T | null>((latest, item) => {
    if (!latest) return item;
    return recordTime(item) > recordTime(latest) ? item : latest;
  }, null);
}

function recordTime(item: { created_at: string; updated_at?: string }): number {
  return Date.parse(item.updated_at || item.created_at || "") || 0;
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}

function inferSectionLabel(issue: string): string {
  if (/权利要求|claim/i.test(issue)) return "权利要求书";
  if (/摘要|abstract/i.test(issue)) return "摘要";
  if (/附图|drawing|figure/i.test(issue)) return "附图说明";
  if (/说明书|description|实施例/i.test(issue)) return "说明书";
  return "全文";
}

function sectionLengthLabel(value: string | undefined): string {
  const length = value?.trim().length ?? 0;
  return length > 0 ? `${length} 字` : "待补充";
}

function truncate(value: string, maxLength: number): string {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function formatRecordTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间未知";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function qualityGateDetail(state: GateState): string {
  if (state === "当前有效") return "质量检查绑定当前内部初稿。";
  if (state === "运行失败") return "质量检查失败，需要重新运行。";
  if (state === "运行中") return "质量检查正在运行。";
  if (state === "等待生成") return "等待内部初稿生成。";
  return "需要重新验证当前内部初稿。";
}

function officialCompileGateDetail(state: GateState): string {
  if (state === "当前有效") return "正式稿已由当前内部初稿编译。";
  if (state === "已失效") return "内部初稿已变更，正式稿需要重编。";
  if (state === "需要修复") return "正式稿编译发现需要修复的问题。";
  if (state === "运行失败") return "正式稿编译失败。";
  if (state === "运行中") return "正式稿编译正在运行。";
  return "等待正式稿编译。";
}

function postDraftReviewGateDetail(state: GateState): string {
  if (state === "当前有效") return "成稿会审已通过当前正式稿。";
  if (state === "已失效") return "版本链路已变更，需要重新会审。";
  if (state === "需要修复") return "成稿会审发现阻断项。";
  if (state === "运行失败") return "成稿会审运行失败。";
  if (state === "运行中") return "成稿会审正在运行。";
  return "等待成稿会审。";
}

function exportGateDetail(state: GateState): string {
  if (state === "可导出") return "正式稿已满足导出条件。";
  if (state === "导出锁定") return "导出被阻断，需要先修复问题。";
  if (state === "运行中") return "导出门禁正在检查。";
  if (state === "运行失败") return "导出门禁检查失败。";
  return "等待前置门禁完成。";
}
