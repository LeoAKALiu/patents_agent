import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Download,
  FileArchive,
  FileText,
  Gauge,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Upload,
  UsersRound,
  Wand2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { AppRoot } from "@/app/AppRoot";
import {
  AgentProviderCards,
  normalizeAgentSelection,
  normalizeDeliberationExpertSelection,
  normalizeDeliberationParticipantSelection,
  requiredAgentProviderIds,
} from "./AgentProviderCards";
import { ShellSidebar } from "./ui/ShellSidebar";
import { ShellTopbar } from "./ui/ShellTopbar";
import { SystemStatusPanel } from "./ui/SystemStatusPanel";
import { useTheme } from "./ui/useTheme";
import {
  AgentDoctorReport,
  ClaimDefenseWorksheet,
  CorpusImportJob,
  CorpusStats,
  CorpusVersion,
  DeliberationRun,
  DisclosurePackage,
  DisclosureRun,
  DraftPackage,
  EvidenceStatus,
  FilingReadinessReport,
  FormulaNeedAssessment,
  FormulaRun,
  GrantabilityReport,
  Health,
  OfficialCompileRun,
  type CnipaQueryPack,
  type ExportReadiness,
  type OfficialDraftPackage,
  PatentPointCandidate,
  PatentPointCreatePayload,
  PatentDocument,
  PostDraftReviewRun,
  PriorArtCandidate,
  ProjectMaterial,
  ProjectKnowledgeImportLedger,
  ProjectKnowledgeOverview,
  PatentStrategyBrief,
  ProjectRecord,
  ProjectUpdate,
  RuntimeFailure,
  RuntimeStageState,
  SearchResult,
  SectionType,
  type DraftCompletionRun,
  type ExternalDraftIntakeRun,
  type ExternalDraftSource,
  type QualityCheckStates,
  acceptAllCompletionPatches,
  acceptCompletionPatch,
  applyOfficialCompileCleanup,
  applyPostDraftSafePatches,
  buildProjectCorpusVersion,
  cancelFormulaRun,
  cancelPostDraftReview,
  cancelProjectDeliberation,
  cancelProjectDisclosure,
  confirmExternalDraftIntakeRun,
  createClaimDefenseWorksheet,
  createCorpusJob,
  createDraftCompletionRun,
  createExternalDraftSource,
  createFilingReadinessReport,
  createProjectSearchIntent,
  createGrantabilityReport,
  createProject,
  createProjectPatentPoint,
  deleteProject,
  deleteProjectPatentPoint,
  disclosureExportUrl,
  evaluateProjectPatentPointMoat,
  draftCompletionReportUrl,
  exportUrl,
  filingReadinessReportUrl,
  generateProject,
  getFormulaRequirement,
  getAgentDoctor,
  getCorpusStats,
  getExportReadiness,
  getHealth,
  getProjectCnipaQueryPack,
  getProjectKnowledge,
  improveProjectScore,
  importPatent,
  listClaimDefenseWorksheets,
  listCorpus,
  listCorpusVersions,
  listDraftCompletionRuns,
  listExternalDraftIntakeRuns,
  listExternalDraftSources,
  listFilingReadinessReports,
  listGrantabilityReports,
  listProjectDisclosures,
  listProjectDeliberations,
  listFormulaRuns,
  listOfficialCompileRuns,
  listPostDraftReviews,
  listProjectKnowledgeImportLedgers,
  listProjectMaterials,
  listProjectPatentPoints,
  listProjects,
  officialExportUrl,
  rejectCompletionPatch,
  reviewProject,
  retryFormulaRun,
  retryPostDraftReview,
  retryProjectDeliberation,
  retryProjectDisclosure,
  runCorpusJob,
  runProjectSearchPlan,
  searchCorpus,
  startKimiOfficialLanguagePolish,
  startProjectDisclosure,
  startProjectDeliberation,
  startExternalDraftIntakeRun,
  startFormulaRun,
  startOfficialCompileRun,
  startPostDraftReview,
  updateProjectKnowledgeCandidate,
  updateProjectDraftPackage,
  updateProjectPatentPoint,
  uploadCorpusJobFile,
  uploadProjectCnipaExport,
  uploadExternalDraftSource,
  uploadProjectMaterial,
} from "./api";
import { GuidedPatentFlowView } from "./GuidedPatentFlow";
import {
  runtimeDisplayElapsedMs,
  runtimeDisplayElapsedSeconds,
  useRuntimeNow,
  userFacingAppErrorMessage,
} from "./runtimeDisplay";
import { uploadProjectMaterialBatch, type MaterialUploadFailure } from "./materialUploadBatch";
import {
  loadPatentPoints as projectDataLoadPatentPoints,
  loadDeliberations as projectDataLoadDeliberations,
  loadMaterials as projectDataLoadMaterials,
  loadDisclosures as projectDataLoadDisclosures,
  loadFormulaState as projectDataLoadFormulaState,
  loadPostDraftReviews as projectDataLoadPostDraftReviews,
  loadOfficialCompileRuns as projectDataLoadOfficialCompileRuns,
  refreshDisclosureRunUntilSettled as projectDataRefresh,
  type ProjectDataDeps,
} from "./store/projectData";
import { SettingsPanel } from "./SettingsPanel";
import { StatusPill, QualityReportView, Distribution, PreviewBlock } from "./views/widgets";
import {
  BusyOperationConsole,
  RuntimeRunActions,
  RuntimeRunConsole,
  RuntimeFailurePanel,
  isActiveRun,
  latestActiveRun,
  isRetryableRun,
  runtimeStageLabel,
  formatRuntimeMs,
  type RuntimeAwareRun,
} from "./views/runtimePanel";
import { ExportView } from "./views/exportView";
import { CorpusBuildView } from "./views/corpusBuildView";
import { MoatView, DeliberationView, DisclosureView } from "./views/pipelineViews";
import {
  DisclosurePreview,
  DisclosureSourceStatus,
  DisclosureSummaryView,
  StrategyBriefView,
  PackagePreview,
} from "./views/disclosureViews";
import { ExpertToolChooser, WriteView } from "./views/expertViews";
import {
  StartChoiceScreen,
  ProjectSelect,
  ProjectsOverview,
  CorpusView,
} from "./views/projectViews";
import { ClaimDefenseView, GrantabilityView, ReviewView } from "./views/qualityViews";
import { FilingReadinessView, DraftCompletionView } from "./views/filingViews";
import {
  canExportPackage,
  completionCategoryLabel,
  completionTargetLabel,
  evidenceStatusLabel,
  featureClassificationLabel,
  latestCompletedDeliberation,
  moatScoreTotal,
  agentDoctorStatusLabel,
  agentRunModeLabel,
  completionPatchKindLabel,
  completionPatchStatusLabel,
  completionTaskStatusLabel,
  deliberationRunModeLabel,
  draftSectionLabel,
  logLevelLabel,
  pipelineRunStatusLabel,
  readinessStatusLabel,
  severityLabel,
  sourceTypeLabel,
  worksheetSourceLabel,
  worksheetStatusLabel,
} from "./domain";
import {
  defaultExpertToolId,
  defaultMainSectionId,
  buildPatentPointSelectionPayloads,
  expertToolGroups,
  guidedBusyLabel,
  guidedOperationLog,
  mainSections,
  normalizeMainSectionId,
  projectGoalPrefix,
  selectCurrentOfficialCompileRun,
  selectLatestMatchingPostDraftReview,
  v1StartChoices,
  type ExpertToolId,
  type MainSectionId,
  type PatentGoalMode,
  type PatentType,
  type StartChoiceId,
} from "./guidedFlow";
import { OperationConsole } from "./ui/OperationConsole";

type DesktopMenuBridge = {
  desktop?: {
    onMenuAction?: (
      handler: (
        action:
          | "open-settings"
          | "open-export-folder"
          | "about"
          | "import-draft-docx"
          | "import-draft-markdown"
          | "export-official-docx"
          | "export-official-md"
          | "export-official-sidecar",
      ) => void,
    ) => () => void;
    dialogs?: {
      openDraft?: (kind: "docx" | "markdown") => Promise<{
        cancelled: boolean;
        filePath: string;
        fileName: string;
        mimeType: string;
        contentBase64: string;
        byteCount: number;
      }>;
      saveOfficial?: (payload: {
        format: "docx" | "md" | "sidecar";
        label: string;
        downloadPath: string;
        filter: { name: string; extensions: string[] };
        defaultFileName: string;
      }) => Promise<{
        cancelled: boolean;
        filePath: string;
        byteCount: number;
        format: "docx" | "md" | "sidecar";
      }>;
      openFolder?: (filePath: string) => Promise<{
        revealed: boolean;
        filePath: string;
      }>;
    };
  };
};


type CorpusJobForm = {
  source_type: string;
  source_name: string;
  query: string;
  domain: string;
  version_name: string;
};

type BusyTimer = {
  elapsedSeconds: number;
  startedAt: number | null;
};

export type BackendStatus = "unknown" | "online" | "offline";
export type ProjectListStatus = "idle" | "loading" | "ready" | "failed";
export type MaterialUploadOutcome = { level: "message" | "error"; text: string };

export type PersistedAppState = {
  selectedProjectId: string;
  activeSection: MainSectionId;
  activeExpertTool: ExpertToolId;
  startChoice: StartChoiceId | null;
  disclosureResearchMode: "standard" | "free_deep_research";
};

const APP_STATE_STORAGE_KEY = "patentagent.appState.v1";
const APP_HISTORY_MARKER = "__patentAgentApp";

const defaultPersistedAppState: PersistedAppState = {
  selectedProjectId: "",
  activeSection: defaultMainSectionId,
  activeExpertTool: defaultExpertToolId,
  startChoice: null,
  disclosureResearchMode: "standard",
};

const validExpertToolIds = new Set<ExpertToolId>(
  expertToolGroups.flatMap((group) => group.tools.map((tool) => tool.id)),
);
const validStartChoiceIds = new Set<StartChoiceId>(v1StartChoices.map((choice) => choice.id));

function materialUploadFailureText(error: unknown): string {
  if (error == null) return "未知错误";
  const raw = error instanceof Error ? error.message : typeof error === "string" ? error : String(error);
  return raw.replace(/^材料上传失败：/, "").trim() || "未知错误";
}

export function summarizeMaterialUploadOutcome(
  totalFileCount: number,
  uploadedMaterials: ProjectMaterial[],
  rejectedUploads: MaterialUploadFailure[],
): MaterialUploadOutcome {
  const processed = uploadedMaterials.filter((material) => material.status === "processed");
  const parsedFailed = uploadedMaterials.filter((material) => material.status !== "processed");
  const failedLabels = [
    ...parsedFailed.map((material) => `${material.file_name}（${material.warnings[0] ?? "解析失败"}）`),
    ...rejectedUploads.map((failure) => `${failure.fileName}（${materialUploadFailureText(failure.error)}）`),
  ];
  const failureCount = failedLabels.length;

  if (totalFileCount === 1) {
    const material = uploadedMaterials[0];
    if (material) {
      return {
        level: material.status === "processed" ? "message" : "error",
        text: material.status === "processed" ? `已上传材料：${material.file_name}` : `材料解析失败：${material.warnings[0] ?? "解析失败"}`,
      };
    }
    const failure = rejectedUploads[0];
    return {
      level: "error",
      text: `材料上传失败：${failure?.fileName ?? "所选文件"}：${materialUploadFailureText(failure?.error)}`,
    };
  }

  if (failureCount > 0) {
    const text = processed.length > 0
      ? `已处理 ${totalFileCount} 份材料：${processed.length} 份可用，${failureCount} 份失败：${failedLabels.join("、")}`
      : `${totalFileCount} 份材料均上传失败：${failedLabels.join("、")}`;
    return { level: processed.length > 0 ? "message" : "error", text };
  }

  return {
    level: "message",
    text: `已上传 ${uploadedMaterials.length} 份材料：${uploadedMaterials.map((material) => material.file_name).join("、")}`,
  };
}

export function sanitizePersistedAppState(value: unknown): PersistedAppState {
  const record = value && typeof value === "object" ? value as Record<string, unknown> : {};
  const selectedProjectId = typeof record.selectedProjectId === "string" ? record.selectedProjectId : "";
  const rawActiveExpertTool = record.activeExpertTool;
  const hasValidActiveExpertTool = validExpertToolIds.has(rawActiveExpertTool as ExpertToolId);
  const activeExpertTool = hasValidActiveExpertTool
    ? rawActiveExpertTool as ExpertToolId
    : defaultExpertToolId;
  // Stale tool ids should not be allowed to trigger legacy build/corpus/export section remaps.
  const sectionMigrationExpertTool: ExpertToolId = hasValidActiveExpertTool
    ? activeExpertTool
    : "materials";
  const activeSection = normalizeMainSectionId(record.activeSection, sectionMigrationExpertTool);
  const startChoice = validStartChoiceIds.has(record.startChoice as StartChoiceId)
    ? record.startChoice as StartChoiceId
    : null;
  const disclosureResearchMode = record.disclosureResearchMode === "free_deep_research"
    ? "free_deep_research"
    : "standard";
  return {
    selectedProjectId,
    activeSection,
    activeExpertTool,
    startChoice,
    disclosureResearchMode,
  };
}

function loadPersistedAppState(): PersistedAppState {
  if (typeof window === "undefined") return defaultPersistedAppState;
  try {
    const raw = window.localStorage.getItem(APP_STATE_STORAGE_KEY);
    return raw ? sanitizePersistedAppState(JSON.parse(raw)) : defaultPersistedAppState;
  } catch {
    return defaultPersistedAppState;
  }
}

function savePersistedAppState(state: PersistedAppState): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(APP_STATE_STORAGE_KEY, JSON.stringify(sanitizePersistedAppState(state)));
  } catch {
    // localStorage can be unavailable in restricted browser contexts.
  }
}

export function resolveRecoveredProjectSelection(
  projects: ProjectRecord[],
  preferredProjectId: string,
): { selectedProjectId: string; clearedMissingProject: boolean } {
  if (!preferredProjectId) {
    return { selectedProjectId: "", clearedMissingProject: false };
  }
  if (projects.some((project) => project.id === preferredProjectId)) {
    return { selectedProjectId: preferredProjectId, clearedMissingProject: false };
  }
  return { selectedProjectId: "", clearedMissingProject: true };
}

export function installAppHistoryGuard(win: Window = window, onRecover?: () => void): () => void {
  const markState = (state: unknown) => ({
    ...(state && typeof state === "object" ? state as Record<string, unknown> : {}),
    [APP_HISTORY_MARKER]: true,
  });
  const ensureGuardEntry = () => {
    if (!win.history.state?.[APP_HISTORY_MARKER]) {
      win.history.replaceState(markState(win.history.state), "", win.location.href);
    }
    win.history.pushState(markState(win.history.state), "", win.location.href);
  };
  const handlePopState = () => {
    ensureGuardEntry();
    onRecover?.();
  };
  const handlePageShow = () => {
    onRecover?.();
  };

  ensureGuardEntry();
  win.addEventListener("popstate", handlePopState);
  win.addEventListener("pageshow", handlePageShow);
  return () => {
    win.removeEventListener("popstate", handlePopState);
    win.removeEventListener("pageshow", handlePageShow);
  };
}

/**
 * PR7 (issue #21): contamination patterns the official compiler is supposed
 * to strip. Mirrors `RESIDUAL_INTERNAL_PATTERNS` and the explicit
 * `INTERNAL_FIELD_RE` patterns in ``backend/app/official_compile.py``. If
 * any of these still appear in the cleaned official package, the compile
 * gate would normally refuse to unlock the export — this scan is a
 * defence-in-depth client-side check that surfaces the warning in the
 * export UI without having to round-trip to the backend.
 */
const OFFICIAL_CONTAMINATION_PATTERNS: ReadonlyArray<{
  pattern: string;
  label: string;
}> = [
  { pattern: "support_gap", label: "support_gap" },
  { pattern: "support_gaps", label: "support_gaps" },
  { pattern: "支撑不足", label: "支撑不足" },
  { pattern: "撰写说明", label: "撰写说明" },
  { pattern: "generation_logs", label: "generation_logs" },
  { pattern: "image_prompt", label: "image_prompt" },
  { pattern: "attorney_memo", label: "attorney_memo" },
  { pattern: "system_trace", label: "system_trace" },
  { pattern: "official_safe_patches", label: "official_safe_patches" },
  { pattern: "根据会审策略", label: "根据会审策略" },
  { pattern: "多 Agent 会审", label: "多 Agent 会审" },
  { pattern: "多Agent会审", label: "多Agent会审" },
  { pattern: "主席汇总", label: "主席汇总" },
  { pattern: "可能不具备创造性", label: "可能不具备创造性" },
  { pattern: "禁止直接提交", label: "禁止直接提交" },
  { pattern: "存在充分公开风险", label: "存在充分公开风险" },
];

const OFFICIAL_INTERNAL_FIELD_RE = /(?:^|\n)\s*(image_prompt|prompt|diagram|generation_logs|attorney_memo|system_trace|official_safe_patches)\s*[:：=]/i;
const OFFICIAL_MERMAID_RE = /^(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt)\b/i;
const OFFICIAL_FENCE_RE = /```/;

interface ContaminationMatch {
  section: string;
  pattern: string;
}

/**
 * Scan every text field of a completed official package for the residual
 * internal markers. Returns one match per (section, pattern) — the UI uses
 * this to populate the contamination warning banner.
 */
function findOfficialContaminationMarkers(
  packageValue: OfficialDraftPackage,
): ContaminationMatch[] {
  const sections: Array<[string, string]> = [
    ["title", packageValue.title],
    ["abstract", packageValue.abstract],
    ["claims", packageValue.claims],
    ["description", packageValue.description],
    ["drawing_description", packageValue.drawing_description],
    ["compile_warnings", packageValue.compile_warnings.join("\n")],
  ];
  const matches: ContaminationMatch[] = [];
  for (const [section, text] of sections) {
    if (!text) continue;
    for (const { pattern } of OFFICIAL_CONTAMINATION_PATTERNS) {
      if (text.includes(pattern)) {
        matches.push({ section, pattern });
      }
    }
    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (OFFICIAL_INTERNAL_FIELD_RE.test(line)) {
        matches.push({ section, pattern: "internal_field" });
      }
      if (OFFICIAL_FENCE_RE.test(trimmed)) {
        matches.push({ section, pattern: "markdown_fence" });
      }
      if (OFFICIAL_MERMAID_RE.test(trimmed)) {
        matches.push({ section, pattern: "mermaid" });
      }
    }
  }
  return matches;
}

function formatBytes(byteCount: number): string {
  if (byteCount < 1024) return `${byteCount} B`;
  if (byteCount < 1024 * 1024) return `${(byteCount / 1024).toFixed(1)} KB`;
  return `${(byteCount / (1024 * 1024)).toFixed(2)} MB`;
}

function fileFromNativeDraft(
  pick: {
    fileName: string;
    mimeType: string;
    contentBase64: string;
  },
  kind: "docx" | "markdown",
): File {
  const binary = window.atob(pick.contentBase64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const fallbackName = kind === "docx" ? "external-draft.docx" : "external-draft.md";
  return new File([bytes], pick.fileName || fallbackName, {
    type: pick.mimeType ||
      (kind === "docx"
        ? "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        : "text/markdown"),
  });
}

function qualityCheckStateForDraftHash(
  artifacts: Array<{ draft_package_hash?: string }>,
  currentSourceDraftHash: string,
): "missing" | "stale" | "current" {
  if (!artifacts.length) return "missing";
  if (!currentSourceDraftHash) return "stale";
  return artifacts.some((artifact) => artifact.draft_package_hash === currentSourceDraftHash)
    ? "current"
    : "stale";
}

function App() {
  const initialAppState = useMemo(() => loadPersistedAppState(), []);
  const [activeSection, setActiveSection] = useState<MainSectionId>(initialAppState.activeSection);
  const [activeExpertTool, setActiveExpertTool] = useState<ExpertToolId>(initialAppState.activeExpertTool);
  const [startChoice, setStartChoice] = useState<StartChoiceId | null>(initialAppState.startChoice);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("unknown");
  const [projectListStatus, setProjectListStatus] = useState<ProjectListStatus>("idle");
  const [health, setHealth] = useState<Health | null>(null);
  const [agentDoctor, setAgentDoctor] = useState<AgentDoctorReport | null>(null);
  const [documents, setDocuments] = useState<PatentDocument[]>([]);
  const [corpusVersions, setCorpusVersions] = useState<CorpusVersion[]>([]);
  const [corpusStats, setCorpusStats] = useState<CorpusStats | null>(null);
  const [corpusJob, setCorpusJob] = useState<CorpusImportJob | null>(null);
  const [projectKnowledge, setProjectKnowledge] = useState<ProjectKnowledgeOverview | null>(null);
  const [cnipaQueryPack, setCnipaQueryPack] = useState<CnipaQueryPack | null>(null);
  const [projectKnowledgeImportLedgers, setProjectKnowledgeImportLedgers] = useState<ProjectKnowledgeImportLedger[]>([]);
  const [corpusJobForm, setCorpusJobForm] = useState({
    source_type: "cnipa_export",
    source_name: "CNIPA",
    query: "G06V 神经网络 图像缺陷",
    domain: "ai_software",
    version_name: "ai-software-v1",
  });
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [deliberationRuns, setDeliberationRuns] = useState<DeliberationRun[]>([]);
  const [projectMaterials, setProjectMaterials] = useState<ProjectMaterial[]>([]);
  const [disclosureRuns, setDisclosureRuns] = useState<DisclosureRun[]>([]);
  const [patentPoints, setPatentPoints] = useState<PatentPointCandidate[]>([]);
  const [formulaRequirement, setFormulaRequirement] = useState<FormulaNeedAssessment | null>(null);
  const [formulaRuns, setFormulaRuns] = useState<FormulaRun[]>([]);
  const [officialCompileRuns, setOfficialCompileRuns] = useState<OfficialCompileRun[]>([]);
  const [currentSourceDraftHash, setCurrentSourceDraftHash] = useState("");
  const [postDraftReviews, setPostDraftReviews] = useState<PostDraftReviewRun[]>([]);
  const [exportReadiness, setExportReadiness] = useState<ExportReadiness | null>(null);
  const [currentDraftHash, setCurrentDraftHash] = useState("");
  const [selectedDeliberationProviders, setSelectedDeliberationProviders] = useState<string[]>(requiredAgentProviderIds);
  const [selectedDeliberationParticipantProviders, setSelectedDeliberationParticipantProviders] = useState<string[]>([]);
  const deliberationExpertsUserEditedRef = useRef(false);
  const [selectedFormulaProviders, setSelectedFormulaProviders] = useState<string[]>(requiredAgentProviderIds);
  const [disclosureResearchMode, setDisclosureResearchMode] =
    useState<"standard" | "free_deep_research">(initialAppState.disclosureResearchMode);
  const [filingReports, setFilingReports] = useState<FilingReadinessReport[]>([]);
  const [grantabilityReports, setGrantabilityReports] = useState<GrantabilityReport[]>([]);
  const [worksheets, setWorksheets] = useState<ClaimDefenseWorksheet[]>([]);
  const [completionRuns, setCompletionRuns] = useState<DraftCompletionRun[]>([]);
  const [externalDraftSources, setExternalDraftSources] = useState<ExternalDraftSource[]>([]);
  const [externalDraftIntakeRuns, setExternalDraftIntakeRuns] = useState<ExternalDraftIntakeRun[]>([]);
  const [patentPointsProjectId, setPatentPointsProjectId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState(initialAppState.selectedProjectId);
  const [searchText, setSearchText] = useState("图像 神经网络 缺陷 方法");
  const [searchSection, setSearchSection] = useState<SectionType | "">("claims");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  // PR7 (issue #21): track the most recent successful native export so the
  // UI can show its absolute path and offer an "open folder" action.
  const [lastExport, setLastExport] = useState<{
    format: "docx" | "md" | "sidecar";
    filePath: string;
    byteCount: number;
    officialPackageHash?: string;
  } | null>(null);
  const selectedProjectIdRef = useRef("");
  const busyTimer = useBusyTimer(busy);
  const { theme, setTheme } = useTheme();

  // Dependency bundle for the extracted project-data loaders (store/projectData,
  // M3-B). Bundling the race-guard + setters here keeps the loader module pure
  // and unit-testable while leaving every call site in App() unchanged.
  const projectDataDeps: ProjectDataDeps = {
    isStillSelected: (projectId) => selectedProjectIdRef.current === projectId,
    setDeliberationRuns,
    setProjectMaterials,
    setDisclosureRuns,
    setPatentPoints,
    setPatentPointsProjectId,
    setFormulaRequirement,
    setFormulaRuns,
    setPostDraftReviews,
    setCurrentDraftHash,
    setOfficialCompileRuns,
    setCurrentSourceDraftHash,
  };

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );
  const currentPackage: DraftPackage | null = selectedProject?.package ?? null;
  const currentDeliberation = latestCompletedDeliberation(deliberationRuns);
  const currentDisclosure = latestCompletedDisclosure(disclosureRuns);
  const currentFormulaRun = formulaRuns.find((run) => run.status === "completed" && run.package) ?? null;
  const visiblePatentPoints = patentPointsProjectId === selectedProject?.id ? patentPoints : [];
  const latestFilingReport = filingReports[0] ?? null;
  const latestGrantabilityReport = grantabilityReports[0] ?? null;
  const latestWorksheet = worksheets[0] ?? null;
  const latestCompletionRun = completionRuns[0] ?? null;
  const latestOfficialCompileRun = selectCurrentOfficialCompileRun(officialCompileRuns, currentSourceDraftHash);
  const latestPostDraftReview = selectLatestMatchingPostDraftReview(postDraftReviews, latestOfficialCompileRun);
  const currentQualityCheckStates = useMemo<QualityCheckStates>(() => ({
    filing_readiness: qualityCheckStateForDraftHash(filingReports, currentSourceDraftHash),
    claim_defense_worksheet: qualityCheckStateForDraftHash(worksheets, currentSourceDraftHash),
    draft_completion: qualityCheckStateForDraftHash(
      completionRuns.filter((run) => run.status === "completed"),
      currentSourceDraftHash,
    ),
  }), [completionRuns, currentSourceDraftHash, filingReports, worksheets]);
  const currentQualityChecked = Object.values(currentQualityCheckStates).every((state) => state === "current");
  const selectedProjectIdForRefresh = selectedProject?.id ?? "";
  const latestOfficialCompileRunId = latestOfficialCompileRun?.id ?? "";
  const latestPostDraftReviewId = latestPostDraftReview?.id ?? "";
  const lastExportRefreshKey = lastExport
    ? [
        lastExport.format,
        lastExport.filePath,
        lastExport.byteCount,
        lastExport.officialPackageHash ?? "",
      ].join(":")
    : "";
  selectedProjectIdRef.current = selectedProjectId;

  useEffect(() => {
    if (selectedProjectIdForRefresh) {
      void loadExportReadiness(selectedProjectIdForRefresh);
    }
    void refreshAll();
  }, [
    selectedProjectIdForRefresh,
    latestOfficialCompileRunId,
    latestPostDraftReviewId,
    currentDraftHash,
    currentSourceDraftHash,
    currentQualityChecked,
    lastExportRefreshKey,
  ]);

  useEffect(() => installAppHistoryGuard(window, () => {
    const recovered = loadPersistedAppState();
    setSelectedProjectId(recovered.selectedProjectId);
    setActiveSection(recovered.activeSection);
    setActiveExpertTool(recovered.activeExpertTool);
    setStartChoice(recovered.startChoice);
    setDisclosureResearchMode(recovered.disclosureResearchMode);
  }), []);

  useEffect(() => {
    savePersistedAppState({
      selectedProjectId,
      activeSection,
      activeExpertTool,
      startChoice,
      disclosureResearchMode,
    });
  }, [activeExpertTool, activeSection, disclosureResearchMode, selectedProjectId, startChoice]);

  useEffect(() => {
    const desktop = (window as Window & DesktopMenuBridge).desktop;
    if (!desktop?.onMenuAction) return undefined;
    return desktop.onMenuAction((action) => {
      if (action === "open-settings") {
        setActiveSection("settings");
        return;
      }
      if (action === "open-export-folder") {
        void triggerOpenExportFolder();
        return;
      }
      if (action === "import-draft-docx") {
        // External-draft intake lives inside the "materials" expert tool.
        setActiveSection("expert");
        setActiveExpertTool("materials");
        void triggerNativeImport("docx");
        return;
      }
      if (action === "import-draft-markdown") {
        setActiveSection("expert");
        setActiveExpertTool("materials");
        void triggerNativeImport("markdown");
        return;
      }
      if (
        action === "export-official-docx" ||
        action === "export-official-md" ||
        action === "export-official-sidecar"
      ) {
        setActiveSection("export");
        setActiveExpertTool("export");
        if (action === "export-official-docx") {
          void triggerNativeExport("docx");
        } else if (action === "export-official-md") {
          void triggerNativeExport("md");
        } else {
          void triggerNativeExport("sidecar");
        }
      }
    });
  }, []);

  useEffect(() => {
    setSelectedDeliberationProviders((providers) => {
      const normalized = normalizeDeliberationExpertSelection(agentDoctor, providers, {
        autoFillMissing: !deliberationExpertsUserEditedRef.current,
      });
      setSelectedDeliberationParticipantProviders((participants) =>
        normalizeDeliberationParticipantSelection(agentDoctor, normalized, participants),
      );
      return normalized;
    });
    setSelectedFormulaProviders((providers) => normalizeAgentSelection(agentDoctor, providers, "formula"));
  }, [agentDoctor]);

  useEffect(() => {
    setProjectKnowledge(null);
    setCnipaQueryPack(null);
    setProjectKnowledgeImportLedgers([]);
    setOfficialCompileRuns([]);
    setCurrentSourceDraftHash("");
    setPostDraftReviews([]);
    setExportReadiness(null);
    setCurrentDraftHash("");
    setExternalDraftSources([]);
    setExternalDraftIntakeRuns([]);
    if (selectedProject?.id) {
      void loadProjectKnowledge(selectedProject.id);
      void loadDeliberations(selectedProject.id);
      void loadMaterials(selectedProject.id);
      void loadDisclosures(selectedProject.id);
      void loadFormulaState(selectedProject.id);
      void loadOfficialCompileRuns(selectedProject.id);
      void loadPostDraftReviews(selectedProject.id);
      void loadExportReadiness(selectedProject.id);
      void refreshExternalDrafts(selectedProject.id);
      setPatentPoints([]);
      setPatentPointsProjectId("");
      setFilingReports([]);
      setGrantabilityReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      void loadPatentPoints(selectedProject.id);
      void loadFilingReports(selectedProject.id);
      void loadGrantabilityReports(selectedProject.id);
      void loadWorksheets(selectedProject.id);
      void loadCompletionRuns(selectedProject.id);
    } else {
      setDeliberationRuns([]);
      setProjectMaterials([]);
      setDisclosureRuns([]);
      setFormulaRequirement(null);
      setFormulaRuns([]);
      setProjectKnowledge(null);
      setCnipaQueryPack(null);
      setProjectKnowledgeImportLedgers([]);
      setExportReadiness(null);
      setPatentPoints([]);
      setFilingReports([]);
      setGrantabilityReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      setExternalDraftSources([]);
      setExternalDraftIntakeRuns([]);
      setPatentPointsProjectId("");
    }
  }, [selectedProject?.id]);

  // Poll run state while any background task is in flight. The effect depends
  // only on a boolean (isAnyRunning) plus the project id, NOT on the run
  // arrays themselves: depending on the arrays would tear down and rebuild the
  // interval on every poll response (each fetch returns a new array reference),
  // causing needless re-renders. With the boolean, the interval is created when
  // a run starts and torn down only when all runs leave the in-flight state.
  const isAnyRunInFlight =
    deliberationRuns.some((run) => run.status === "queued" || run.status === "running")
    || disclosureRuns.some((run) => run.status === "queued" || run.status === "running")
    || formulaRuns.some((run) => run.status === "queued" || run.status === "running")
    || postDraftReviews.some((run) => run.status === "queued" || run.status === "running");

  useEffect(() => {
    const projectId = selectedProject?.id;
    if (!projectId || !isAnyRunInFlight) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadDeliberations(projectId);
      void loadDisclosures(projectId);
      void loadFormulaState(projectId);
      void loadOfficialCompileRuns(projectId);
      void loadPostDraftReviews(projectId);
      void loadExportReadiness(projectId);
    }, 1000);
    return () => window.clearInterval(timer);
    // loadX functions are stable closures over setState only; they are not
    // listed because they do not change identity in a way that should reset
    // the interval. isAnyRunInFlight is the single state-derived signal.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProject?.id, isAnyRunInFlight]);

  async function refreshAll() {
    await withStatus("refresh", async () => {
      setProjectListStatus((current) => current === "ready" ? current : "loading");
      try {
        const [healthData, doctorData, corpusData, projectsData] = await Promise.all([
          getHealth(),
          getAgentDoctor(),
          listCorpus(),
          listProjects(),
        ]);
        const [versionsData, statsData] = await Promise.all([listCorpusVersions(), getCorpusStats()]);
        const recoveredSelection = resolveRecoveredProjectSelection(projectsData, selectedProjectIdRef.current);
        setBackendStatus("online");
        setProjectListStatus("ready");
        setHealth(healthData);
        setAgentDoctor(doctorData);
        setDocuments(corpusData);
        setCorpusVersions(versionsData);
        setCorpusStats(statsData);
        setProjects(projectsData);
        if (recoveredSelection.selectedProjectId === selectedProjectIdRef.current && recoveredSelection.selectedProjectId) {
          await loadProjectKnowledge(recoveredSelection.selectedProjectId);
        } else if (!recoveredSelection.selectedProjectId) {
          setProjectKnowledge(null);
        }
        if (recoveredSelection.selectedProjectId !== selectedProjectIdRef.current) {
          setSelectedProjectId(recoveredSelection.selectedProjectId);
        }
        if (recoveredSelection.clearedMissingProject) {
          setMessage("上次选择的项目已不存在，请重新选择项目。");
        }
      } catch (err) {
        setBackendStatus("offline");
        setProjectListStatus("failed");
        setHealth(null);
        setAgentDoctor(null);
        throw err;
      }
    });
  }

  async function loadDeliberations(projectId: string): Promise<boolean> {
    return projectDataLoadDeliberations(projectId, projectDataDeps);
  }

  async function loadMaterials(projectId: string): Promise<boolean> {
    return projectDataLoadMaterials(projectId, projectDataDeps);
  }

  async function loadDisclosures(projectId: string): Promise<boolean> {
    return projectDataLoadDisclosures(projectId, projectDataDeps);
  }

  async function refreshDisclosureRunUntilSettled(projectId: string, runId: string): Promise<void> {
    // Delegates to store/projectData (M3-B); back-off schedule + race guard
    // live there and are unit-tested. `delay` is passed in to keep the module pure.
    return projectDataRefresh(projectId, runId, projectDataDeps, delay);
  }

  async function loadFormulaState(projectId: string): Promise<boolean> {
    return projectDataLoadFormulaState(projectId, projectDataDeps);
  }

  async function loadPostDraftReviews(projectId: string): Promise<boolean> {
    return projectDataLoadPostDraftReviews(projectId, projectDataDeps);
  }

  async function loadOfficialCompileRuns(projectId: string): Promise<boolean> {
    return projectDataLoadOfficialCompileRuns(projectId, projectDataDeps);
  }

  async function loadExportReadiness(projectId: string): Promise<boolean> {
    try {
      const readiness = await getExportReadiness(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setExportReadiness(readiness);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setExportReadiness(null);
      }
      return false;
    }
  }

  async function loadProjectKnowledge(projectId: string): Promise<boolean> {
    try {
      const overview = await getProjectKnowledge(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setProjectKnowledge(overview);
      try {
        const queryPack = await getProjectCnipaQueryPack(projectId);
        if (selectedProjectIdRef.current !== projectId) {
          return false;
        }
        setCnipaQueryPack(queryPack);
      } catch {
        if (selectedProjectIdRef.current === projectId) {
          setCnipaQueryPack(null);
        }
      }
      if (!overview.latest_plan) {
        setProjectKnowledgeImportLedgers([]);
        return true;
      }
      try {
        const ledgers = await listProjectKnowledgeImportLedgers(projectId, overview.latest_plan.id);
        if (selectedProjectIdRef.current !== projectId) {
          return false;
        }
        setProjectKnowledgeImportLedgers(ledgers);
      } catch {
        if (selectedProjectIdRef.current === projectId) {
          setProjectKnowledgeImportLedgers([]);
        }
      }
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setProjectKnowledge(null);
        setCnipaQueryPack(null);
        setProjectKnowledgeImportLedgers([]);
      }
      return false;
    }
  }

  async function loadPatentPoints(projectId: string): Promise<boolean> {
    // Delegates to store/projectData (M3-B); kept as a thin closure so call
    // sites are unchanged. Race-guard + setters are passed in explicitly.
    return projectDataLoadPatentPoints(projectId, projectDataDeps);
  }

  async function loadFilingReports(projectId: string): Promise<boolean> {
    try {
      const { reports, current_source_draft_hash } = await listFilingReadinessReports(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setFilingReports(reports);
      setCurrentSourceDraftHash(current_source_draft_hash);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setFilingReports([]);
      }
      return false;
    }
  }

  async function loadGrantabilityReports(projectId: string): Promise<boolean> {
    try {
      const { reports, current_source_draft_hash } = await listGrantabilityReports(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setGrantabilityReports(reports);
      setCurrentSourceDraftHash(current_source_draft_hash);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setGrantabilityReports([]);
      }
      return false;
    }
  }

  async function loadWorksheets(projectId: string): Promise<boolean> {
    try {
      const { worksheets: nextWorksheets, current_source_draft_hash } = await listClaimDefenseWorksheets(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setWorksheets(nextWorksheets);
      setCurrentSourceDraftHash(current_source_draft_hash);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setWorksheets([]);
      }
      return false;
    }
  }

  async function loadCompletionRuns(projectId: string): Promise<boolean> {
    try {
      const { runs, current_source_draft_hash } = await listDraftCompletionRuns(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setCompletionRuns(runs);
      setCurrentSourceDraftHash(current_source_draft_hash);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setCompletionRuns([]);
      }
      return false;
    }
  }

  async function refreshExternalDrafts(projectId: string, preferredSourceId?: string): Promise<boolean> {
    try {
      const sources = await listExternalDraftSources(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setExternalDraftSources(sources);
      const sourceId = preferredSourceId ?? sources[0]?.id;
      if (sourceId) {
        const runs = await listExternalDraftIntakeRuns(projectId, sourceId);
        if (selectedProjectIdRef.current !== projectId) {
          return false;
        }
        setExternalDraftIntakeRuns(runs);
      } else {
        setExternalDraftIntakeRuns([]);
      }
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setExternalDraftSources([]);
        setExternalDraftIntakeRuns([]);
      }
      return false;
    }
  }

  async function refreshProjectsPreservingSelection(projectId: string): Promise<boolean> {
    const nextProjects = await listProjects();
    if (selectedProjectIdRef.current !== projectId) {
      return false;
    }
    setProjects(nextProjects);
    if (nextProjects.some((project) => project.id === projectId)) {
      setSelectedProjectId(projectId);
      return true;
    }
    setSelectedProjectId("");
    return false;
  }

  async function withStatus(label: string, task: () => Promise<void>) {
    setBusy(label);
    setError("");
    setMessage("");
    try {
      await task();
    } catch (err) {
      setError(userFacingAppErrorMessage(err));
    } finally {
      setBusy("");
    }
  }

  /**
   * PR7 (issue #21): open a native open-file dialog, then upload the chosen
   * DOCX/Markdown file as an external draft. The renderer's own
   * ``uploadExternalDraftSource`` POSTs the file to the existing FastAPI
   * ``/api/projects/{id}/external-drafts/upload`` endpoint and triggers the
   * normal intake confirmation flow.
   */
  async function triggerNativeImport(kind: "docx" | "markdown"): Promise<void> {
    const desktop = (window as Window & DesktopMenuBridge).desktop;
    if (!desktop?.dialogs?.openDraft) {
      setError("原生导入对话框不可用：请使用页面内的上传按钮。");
      return;
    }
    if (!selectedProject) {
      setError("请先选择项目再导入草稿。");
      return;
    }
    await withStatus("native-import-draft", async () => {
      const pick = await desktop.dialogs!.openDraft!(kind);
      if (pick.cancelled) {
        setMessage("已取消草稿导入。");
        return;
      }
      // The main process reads exactly the file selected in the native dialog.
      // The renderer then POSTs the bytes through the existing upload endpoint
      // so DOCX extraction, content-hash sealing, and intake confirmation stay
      // on the same backend path as the in-page upload.
      const file = fileFromNativeDraft(pick, kind);
      const source = await uploadExternalDraftSource(selectedProject.id, file);
      const stillSelected = await refreshExternalDrafts(selectedProject.id, source.id);
      if (!stillSelected) return;
      setMessage(`已通过原生对话框导入：${source.file_name}`);
    });
  }

  /**
   * PR7 (issue #21): show a native save dialog, then have the main process
   * stream the chosen backend export endpoint to the user-selected file. If
   * the running app does not expose the dialog bridge (web preview), fall
   * back to the existing ``<a download>`` flow so the UI is still usable.
   */
  async function triggerNativeExport(
    format: "docx" | "md" | "sidecar",
  ): Promise<void> {
    const desktop = (window as Window & DesktopMenuBridge).desktop;
    if (!desktop?.dialogs?.saveOfficial) {
      // Web preview / dev fallback: trigger the existing browser download.
      if (!selectedProject) return;
      const href =
        format === "sidecar"
          ? `${window.location.origin}/api/projects/${selectedProject.id}/official-compile-runs/${latestOfficialCompileRun?.id ?? ""}/report.md`
          : officialExportUrl(
              selectedProject.id,
              format === "docx" ? "docx" : "md",
            );
      if (format === "sidecar" && !latestOfficialCompileRun?.id) {
        setError("风险说明需要先生成正式稿。");
        return;
      }
      window.location.href = href;
      return;
    }
    if (!selectedProject) {
      setError("请先选择项目再导出。");
      return;
    }
    if (!latestOfficialCompileRun?.id) {
      setError("请先生成正式稿，再导出官方稿。");
      return;
    }
    if (format === "sidecar") {
      // Sidecar is always allowed; it doesn't depend on the post-draft review gate.
    } else if (format === "docx" || format === "md") {
      const allowed = Boolean(
        latestOfficialCompileRun.status === "completed" &&
        latestOfficialCompileRun.official_package &&
        latestOfficialCompileRun.source_draft_hash === currentSourceDraftHash &&
        currentQualityChecked &&
        latestPostDraftReview?.status === "completed" &&
        latestPostDraftReview.export_allowed &&
        latestPostDraftReview.draft_package_hash === latestOfficialCompileRun.source_draft_hash &&
        latestPostDraftReview.official_compile_run_id === latestOfficialCompileRun.id &&
        latestPostDraftReview.official_package_hash === latestOfficialCompileRun.official_package_hash,
      );
      if (!allowed) {
        setError(
          "正式稿导出已锁定：需先完成当前初稿质量检查，并通过针对当前正式稿的成稿会审。",
        );
        return;
      }
    }
    const projectName = selectedProject.name || "权衡 GrantAtlas";
    const safeName = projectName.replace(/[\\/:*?"<>|]/g, "_");
    const option =
      format === "docx"
        ? {
            format: "docx" as const,
            label: "官方 DOCX",
            downloadPath: officialExportUrl(selectedProject.id, "docx"),
            filter: {
              name: "Word 文档",
              extensions: ["docx"],
            },
            defaultFileName: `${safeName}-正式提交稿.docx`,
          }
        : format === "md"
          ? {
              format: "md" as const,
              label: "官方 Markdown",
              downloadPath: officialExportUrl(selectedProject.id, "md"),
              filter: { name: "Markdown 文本", extensions: ["md"] },
              defaultFileName: `${safeName}-正式提交稿.md`,
            }
          : {
              format: "sidecar" as const,
              label: "正式稿编译报告",
              downloadPath: `/api/projects/${selectedProject.id}/official-compile-runs/${latestOfficialCompileRun.id}/report.md`,
              filter: { name: "Markdown 文本", extensions: ["md"] },
              defaultFileName: `${safeName}-正式稿编译报告.md`,
            };
    await withStatus("native-export", async () => {
      const result = await desktop.dialogs!.saveOfficial!(option);
      if (result.cancelled) {
        setMessage("已取消导出。");
        return;
      }
      setLastExport({
        format: result.format,
        filePath: result.filePath,
        byteCount: result.byteCount,
        officialPackageHash: latestOfficialCompileRun?.official_package_hash ?? undefined,
      });
      setMessage(
        `已保存到 ${result.filePath}（${result.byteCount} 字节，${result.format}）`,
      );
    });
  }

  async function triggerOpenExportFolder(): Promise<void> {
    const desktop = (window as Window & DesktopMenuBridge).desktop;
    if (!lastExport) {
      setError("暂无可打开的导出文件。请先完成一次原生导出。");
      return;
    }
    if (!desktop?.dialogs?.openFolder) {
      setError("原生文件管理器集成不可用。");
      return;
    }
    await withStatus("native-open-folder", async () => {
      await desktop.dialogs!.openFolder!(lastExport.filePath);
      setMessage(`已在系统文件管理器中定位 ${lastExport.filePath}`);
    });
  }

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("patent-file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    await withStatus("import", async () => {
      const result = await importPatent(file);
      setMessage(`已导入 ${result.document.title}，生成 ${result.chunks_count} 个片段`);
      setDocuments(await listCorpus());
      input.value = "";
    });
  }

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    await withStatus("search", async () => {
      setSearchResults(await searchCorpus(searchText, searchSection, corpusVersions[0]?.name));
    });
  }

  async function handleCreateCorpusJob(event: FormEvent) {
    event.preventDefault();
    await withStatus("corpus-job", async () => {
      const job = await createCorpusJob(corpusJobForm);
      setCorpusJob(job);
      setMessage(`已创建语料导入任务：${job.version_name}`);
    });
  }

  async function handleUploadCorpusJobFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("corpus-batch-file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !corpusJob) return;
    await withStatus("corpus-upload", async () => {
      const result = await uploadCorpusJobFile(corpusJob.id, file);
      setCorpusJob(result.job);
      setMessage(`已上传 ${result.file_count} 个批次文件`);
      input.value = "";
    });
  }

  async function handleRunCorpusJob() {
    if (!corpusJob) return;
    await withStatus("corpus-run", async () => {
      const job = await runCorpusJob(corpusJob.id);
      setCorpusJob(job);
      const [nextDocuments, nextVersions, nextStats] = await Promise.all([
        listCorpus(),
        listCorpusVersions(),
        getCorpusStats(job.version_name),
      ]);
      setDocuments(nextDocuments);
      setCorpusVersions(nextVersions);
      setCorpusStats(nextStats);
      setMessage(`导入完成：入库 ${job.imported_documents} 件，去重 ${job.duplicate_documents} 件`);
    });
  }

  async function handleGenerateKnowledgePlan(): Promise<void> {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("knowledge-plan", async () => {
      const overview = await createProjectSearchIntent(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return;
      }
      setProjectKnowledge(overview);
      try {
        const queryPack = await getProjectCnipaQueryPack(projectId);
        if (selectedProjectIdRef.current !== projectId) {
          return;
        }
        setCnipaQueryPack(queryPack);
        if (overview.latest_plan) {
          const ledgers = await listProjectKnowledgeImportLedgers(projectId, overview.latest_plan.id);
          if (selectedProjectIdRef.current !== projectId) {
            return;
          }
          setProjectKnowledgeImportLedgers(ledgers);
        } else {
          setProjectKnowledgeImportLedgers([]);
        }
      } catch {
        if (selectedProjectIdRef.current === projectId) {
          setCnipaQueryPack(null);
          setProjectKnowledgeImportLedgers([]);
        }
      }
      setMessage("已生成 Agent 检索计划。");
    });
  }

  async function handleRunKnowledgeSearch(): Promise<void> {
    const latestPlan = projectKnowledge?.latest_plan;
    if (!selectedProject || !latestPlan) return;
    const projectId = selectedProject.id;
    await withStatus("knowledge-search", async () => {
      const overview = await runProjectSearchPlan(projectId, latestPlan.id);
      if (selectedProjectIdRef.current !== projectId) {
        return;
      }
      setProjectKnowledge(overview);
      setMessage(`已生成 ${overview.candidates.length} 条候选文献。`);
    });
  }

  async function handleCandidateDecision(
    candidateId: string,
    decision: PriorArtCandidate["user_decision"],
  ): Promise<void> {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("knowledge-candidate", async () => {
      await updateProjectKnowledgeCandidate(projectId, candidateId, decision);
      if (selectedProjectIdRef.current !== projectId) {
        return;
      }
      await loadProjectKnowledge(projectId);
    });
  }

  async function handleBuildProjectCorpus(): Promise<void> {
    const latestPlan = projectKnowledge?.latest_plan;
    if (!selectedProject || !latestPlan) return;
    const projectId = selectedProject.id;
    await withStatus("knowledge-build", async () => {
      const overview = await buildProjectCorpusVersion(projectId, latestPlan.id);
      if (selectedProjectIdRef.current !== projectId) {
        return;
      }
      setProjectKnowledge(overview);
      if (overview.state.status === "ready") {
        setMessage(`项目语料库已就绪：${overview.state.document_count} 件文献。`);
        return;
      }
      if (overview.state.quality_flags.includes("synthetic_evidence")) {
        setMessage(`项目证据库建库完成：${overview.state.document_count} 件文献，但当前仅含 synthetic/fake 证据，仍需补充检索。`);
        return;
      }
      if (overview.state.status === "needs_supplemental_search") {
        setMessage(`项目证据库建库完成：${overview.state.document_count} 件文献，但当前仍需补充检索。`);
        return;
      }
      setMessage(`项目证据库建库完成：${overview.state.document_count} 件文献。`);
    });
  }

  async function handleImportCnipaExport(file: File): Promise<void> {
    const latestPlan = projectKnowledge?.latest_plan;
    if (!selectedProject || !latestPlan) return;
    const projectId = selectedProject.id;
    await withStatus("knowledge-cnipa-import", async () => {
      const result = await uploadProjectCnipaExport(projectId, latestPlan.id, file);
      if (selectedProjectIdRef.current !== projectId) {
        return;
      }
      setProjectKnowledge(result.overview);
      setProjectKnowledgeImportLedgers((current) => [result.ledger, ...current]);
      setMessage(`已导入 CNIPA 官方导出物：解析 ${result.ledger.parsed_count} 条候选。`);
    });
  }

  async function handleCreateIdeaProject(payload: {
    name: string;
    idea: string;
    mode: PatentGoalMode;
    patentType: PatentType;
    applicant?: string;
    inventors?: string;
    technical_field?: string;
    background?: string;
    pain_point?: string;
    technical_solution?: string;
    innovation?: string;
    embodiments?: string;
    beneficial_effects?: string;
  }) {
    await withStatus("guided-create", async () => {
      const prefix = projectGoalPrefix(payload.mode);
      const metadata: Partial<ProjectUpdate> = {
        applicant: payload.applicant,
        inventors: payload.inventors,
        technical_field: payload.technical_field,
        background: payload.background,
        pain_point: payload.pain_point,
        technical_solution: payload.technical_solution,
        innovation: payload.innovation,
        embodiments: payload.embodiments,
        beneficial_effects: payload.beneficial_effects,
      };
      const project = await createProject(payload.name, `${prefix}\n${payload.idea}`, payload.patentType, metadata);
      const nextProjects = await listProjects();
      setProjects(nextProjects);
      setSelectedProjectId(project.id);
      setMessage(`已创建项目：${project.name}`);
    });
  }

  async function handleUploadMaterial(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    const input = event.currentTarget.elements.namedItem("project-material-file") as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (files.length === 0) return;
    await withStatus("material-upload", async () => {
      const { uploadedMaterials, rejectedUploads, refreshed } = await uploadProjectMaterialBatch(projectId, files, {
        uploadProjectMaterial,
        loadMaterials,
      });
      if (uploadedMaterials.length > 0 && !refreshed) return;
      const outcome = summarizeMaterialUploadOutcome(files.length, uploadedMaterials, rejectedUploads);
      if (outcome.level === "error") {
        setError(outcome.text);
      } else {
        setMessage(outcome.text);
      }
      input.value = "";
    });
  }

  async function handleCreateExternalDraft(payload: { text: string; fileName: string }) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("external-draft-create", async () => {
      const source = await createExternalDraftSource(projectId, {
        source_type: "pasted_text",
        text: payload.text,
        file_name: payload.fileName,
      });
      const stillSelected = await refreshExternalDrafts(projectId, source.id);
      if (!stillSelected) return;
      setMessage(`已保存外部稿：${source.file_name}`);
    });
  }

  async function handleUploadExternalDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    const input = event.currentTarget.elements.namedItem("external-draft-file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    await withStatus("external-draft-upload", async () => {
      const source = await uploadExternalDraftSource(projectId, file);
      const stillSelected = await refreshExternalDrafts(projectId, source.id);
      if (!stillSelected) return;
      setMessage(`已上传外部稿：${source.file_name}`);
      input.value = "";
    });
  }

  async function handleStartExternalDraftIntake(sourceId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("external-draft-intake", async () => {
      const run = await startExternalDraftIntakeRun(projectId, sourceId);
      if (selectedProjectIdRef.current !== projectId) return;
      setExternalDraftIntakeRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      const draftsStillSelected = await refreshExternalDrafts(projectId, sourceId);
      if (!draftsStillSelected) return;
      if (run.status === "completed" && run.parsed_package) {
        const stillSelected = await refreshProjectsPreservingSelection(projectId);
        if (!stillSelected) return;
        setFilingReports([]);
        setWorksheets([]);
        setCompletionRuns([]);
        await loadOfficialCompileRuns(projectId);
        await loadPostDraftReviews(projectId);
      }
      setMessage(run.status === "needs_review" ? "外部稿解析完成，需确认章节" : `外部稿解析${run.status}`);
    });
  }

  async function handleConfirmExternalDraftIntake(
    runId: string,
    payload: {
      title: string;
      abstract: string;
      claims: string;
      description: string;
      drawing_description: string;
    },
  ) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("external-draft-confirm", async () => {
      const run = await confirmExternalDraftIntakeRun(projectId, runId, payload);
      const stillSelected = await refreshProjectsPreservingSelection(projectId);
      if (!stillSelected) return;
      const draftsStillSelected = await refreshExternalDrafts(projectId, run.source_id);
      if (!draftsStillSelected) return;
      setFilingReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage("外部稿已确认为内部工作稿，请重新运行质量检查");
    });
  }

  async function handleStartDisclosure(trace = false) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("disclosure", async () => {
      const run = await startProjectDisclosure(projectId, trace, disclosureResearchMode);
      const stillSelected = await loadDisclosures(projectId);
      if (!stillSelected) return;
      if (run.status === "queued" || run.status === "running") {
        void refreshDisclosureRunUntilSettled(projectId, run.id);
      } else {
        await loadPatentPoints(projectId);
      }
      const modeLabel =
        disclosureResearchMode === "free_deep_research" ? "（免费 Deep Research 补充）" : "";
      setMessage(
        `前置材料生成已${run.status === "completed" ? "完成" : "启动"}${modeLabel}：${pipelineRunStatusLabel(run.status)}`,
      );
    });
  }

  async function handleStartDeliberation(trace = false) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("deliberate", async () => {
      const run = await startProjectDeliberation(projectId, trace, selectedDeliberationProviders, selectedDeliberationParticipantProviders);
      const stillSelected = await loadDeliberations(projectId);
      if (!stillSelected) return;
      await loadFormulaState(projectId);
      setMessage(`会审已${run.status === "completed" ? "完成" : "启动"}：${deliberationRunModeLabel(run.run_mode)}`);
    });
  }

  async function handleStartFormula() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("formula", async () => {
      const run = await startFormulaRun(projectId, selectedFormulaProviders);
      const stillSelected = await loadFormulaState(projectId);
      if (!stillSelected) return;
      setMessage(`核心公式已${run.status === "completed" ? "完成" : "启动"}：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  async function handleStartPostDraftReview() {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("post-draft-review", async () => {
      const run = await startPostDraftReview(projectId, selectedDeliberationProviders, selectedDeliberationParticipantProviders);
      const stillSelected = await loadPostDraftReviews(projectId);
      if (!stillSelected) return;
      setMessage(
        `成稿会审已${run.status === "completed" ? "完成" : "启动"}：${
          run.export_allowed ? "允许正式导出" : pipelineRunStatusLabel(run.status)
        }`,
      );
    });
  }

  async function handleApplyPostDraftSafePatches(runId: string) {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("post-draft-safe-patch", async () => {
      const result = await applyPostDraftSafePatches(projectId, runId);
      const stillSelected = await refreshProjectsPreservingSelection(projectId);
      if (!stillSelected) return;
      setFilingReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage(
        `已应用 ${result.applied_count} 条会审安全补丁，当前初稿已变更。请重新运行质量检查、正式稿编译和成稿会审。`,
      );
    });
  }

  async function handleApplyOfficialCompileCleanup(runId: string) {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("official-compile-cleanup", async () => {
      const result = await applyOfficialCompileCleanup(projectId, runId);
      const stillSelected = await refreshProjectsPreservingSelection(projectId);
      if (!stillSelected) return;
      setFilingReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage(
        `已清理 ${result.applied_count} 项正式稿阻断痕迹，当前源稿已变更。请重新运行质量检查、正式稿编译和成稿会审。`,
      );
    });
  }

  async function handleSaveDraftPackage(payload: Pick<DraftPackage, "title" | "abstract" | "claims" | "description" | "drawing_description">) {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("draft-save", async () => {
      await updateProjectDraftPackage(projectId, payload);
      const stillSelected = await refreshProjectsPreservingSelection(projectId);
      if (!stillSelected) return;
      setFilingReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage("当前内部初稿已保存。请重新运行质量检查、正式稿编译和成稿会审。");
    });
  }

  async function handleDraftRepairPatchApplied(issueId?: string) {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("draft-repair-patch", async () => {
      const stillSelected = await refreshProjectsPreservingSelection(projectId);
      if (!stillSelected) return;
      setFilingReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      await loadExportReadiness(projectId);
      setMessage(
        issueId
          ? "AI 修正已写回当前初稿。请重新运行质量检查、正式稿编译和成稿会审。"
          : "修复补丁已写回当前初稿。请重新运行质量检查、正式稿编译和成稿会审。",
      );
    });
  }

  async function handleStartOfficialCompile() {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("official-compile", async () => {
      const run = await startOfficialCompileRun(projectId);
      const stillSelected = await loadOfficialCompileRuns(projectId);
      if (!stillSelected) return;
      setMessage(
        run.status === "completed" ? "正式稿编译完成" : `正式稿编译${pipelineRunStatusLabel(run.status)}`,
      );
    });
  }

  async function handleStartKimiLanguagePolish() {
    if (!selectedProject?.package || !latestOfficialCompileRun?.official_package) return;
    const projectId = selectedProject.id;
    const runId = latestOfficialCompileRun.id;
    await withStatus("kimi-language-polish", async () => {
      const run = await startKimiOfficialLanguagePolish(projectId, runId);
      const stillSelected = await loadOfficialCompileRuns(projectId);
      if (!stillSelected) return;
      await loadPostDraftReviews(projectId);
      setMessage(
        run.status === "completed"
          ? "Kimi 成稿语言润色完成。润色稿已生成新的正式稿版本，请重新运行成稿会审。"
          : `Kimi 成稿语言润色${pipelineRunStatusLabel(run.status)}`,
      );
    });
  }

  async function handleCancelDisclosureRun(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("runtime-cancel", async () => {
      const run = await cancelProjectDisclosure(projectId, runId);
      const stillSelected = await loadDisclosures(projectId);
      if (!stillSelected) return;
      setMessage(`已请求取消交底书生成：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  async function handleRetryDisclosureRun(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("runtime-retry", async () => {
      const run = await retryProjectDisclosure(projectId, runId);
      const stillSelected = await loadDisclosures(projectId);
      if (!stillSelected) return;
      setMessage(`已重试交底书生成：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  async function handleCancelDeliberationRun(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("runtime-cancel", async () => {
      const run = await cancelProjectDeliberation(projectId, runId);
      const stillSelected = await loadDeliberations(projectId);
      if (!stillSelected) return;
      await loadFormulaState(projectId);
      setMessage(`已请求取消会审：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  async function handleRetryDeliberationRun(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("runtime-retry", async () => {
      const run = await retryProjectDeliberation(projectId, runId);
      const stillSelected = await loadDeliberations(projectId);
      if (!stillSelected) return;
      await loadFormulaState(projectId);
      setMessage(`已重试会审：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  async function handleCancelFormulaRun(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("runtime-cancel", async () => {
      const run = await cancelFormulaRun(projectId, runId);
      const stillSelected = await loadFormulaState(projectId);
      if (!stillSelected) return;
      setMessage(`已请求取消核心公式：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  async function handleRetryFormulaRun(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("runtime-retry", async () => {
      const run = await retryFormulaRun(projectId, runId);
      const stillSelected = await loadFormulaState(projectId);
      if (!stillSelected) return;
      setMessage(`已重试核心公式：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  async function handleCancelPostDraftReviewRun(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("runtime-cancel", async () => {
      const run = await cancelPostDraftReview(projectId, runId);
      const stillSelected = await loadPostDraftReviews(projectId);
      if (!stillSelected) return;
      setMessage(`已请求取消成稿会审：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  async function handleRetryPostDraftReviewRun(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("runtime-retry", async () => {
      const run = await retryPostDraftReview(projectId, runId);
      const stillSelected = await loadPostDraftReviews(projectId);
      if (!stillSelected) return;
      setMessage(`已重试成稿会审：${pipelineRunStatusLabel(run.status)}`);
    });
  }

  function handleToggleDeliberationProvider(providerId: string, enabled: boolean) {
    deliberationExpertsUserEditedRef.current = true;
    setSelectedDeliberationProviders((providers) => {
      const next = enabled ? [...providers, providerId] : providers.filter((id) => id !== providerId);
      const normalized = normalizeDeliberationExpertSelection(agentDoctor, next, { autoFillMissing: false });
      setSelectedDeliberationParticipantProviders((participants) =>
        normalizeDeliberationParticipantSelection(agentDoctor, normalized, participants.filter((id) => id !== providerId)),
      );
      return normalized;
    });
  }

  function handleToggleDeliberationParticipantProvider(providerId: string, enabled: boolean) {
    setSelectedDeliberationParticipantProviders((providers) => {
      const next = enabled ? [...providers, providerId] : providers.filter((id) => id !== providerId);
      return normalizeDeliberationParticipantSelection(agentDoctor, selectedDeliberationProviders, next);
    });
  }

  function handleToggleFormulaProvider(providerId: string, enabled: boolean) {
    setSelectedFormulaProviders((providers) => {
      const next = enabled ? [...providers, providerId] : providers.filter((id) => id !== providerId);
      return normalizeAgentSelection(agentDoctor, next, "formula");
    });
  }

  async function handleGenerate() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("generate", async () => {
      await generateProject(projectId, currentDeliberation?.id ?? null, currentFormulaRun?.id ?? null);
      const nextProjects = await listProjects();
      if (selectedProjectIdRef.current !== projectId) return;
      setProjects(nextProjects);
      setSelectedProjectId(projectId);
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage("申请文本已生成");
    });
  }

  async function handleReview() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("review", async () => {
      await reviewProject(projectId);
      const nextProjects = await listProjects();
      if (selectedProjectIdRef.current !== projectId) return;
      setProjects(nextProjects);
      setSelectedProjectId(projectId);
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage("审查意见已更新");
    });
  }

  async function handleRunFilingReadiness() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("filing-readiness", async () => {
      const report = await createFilingReadinessReport(projectId);
      const stillSelected = await loadFilingReports(projectId);
      if (!stillSelected) return;
      setMessage(`提交成熟度检查完成：${readinessStatusLabel(report.status)}`);
    });
  }

  async function handleRunGuidedQualityChecks() {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("guided-quality", async () => {
      const report = await createFilingReadinessReport(projectId);
      const grantability = await createGrantabilityReport(projectId);
      const worksheet = await createClaimDefenseWorksheet(projectId);
      const completion = await createDraftCompletionRun(projectId);
      const nextProjects = await listProjects();
      if (selectedProjectIdRef.current !== projectId) return;
      setProjects(nextProjects);
      setSelectedProjectId(projectId);
      setFilingReports((current) => [report, ...current.filter((item) => item.id !== report.id)]);
      setGrantabilityReports((current) => [grantability, ...current.filter((item) => item.id !== grantability.id)]);
      setWorksheets((current) => [worksheet, ...current.filter((item) => item.id !== worksheet.id)]);
      setCompletionRuns((current) => [completion, ...current.filter((item) => item.id !== completion.id)]);
      await Promise.all([
        loadFilingReports(projectId),
        loadGrantabilityReports(projectId),
        loadWorksheets(projectId),
        loadCompletionRuns(projectId),
        loadOfficialCompileRuns(projectId),
        loadPostDraftReviews(projectId),
      ]);
      setMessage(`质量检查完成：整体评分 ${completion.scorecard.overall}/100`);
    });
  }

  async function handleCreateGrantabilityReport() {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("grantability", async () => {
      const report = await createGrantabilityReport(projectId);
      const stillSelected = await loadGrantabilityReports(projectId);
      if (!stillSelected) return;
      setMessage(`授权前景报告已生成：${report.claim_chart.length} 个特征映射`);
    });
  }

  async function handleImproveScore() {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("score-improve", async () => {
      const result = await improveProjectScore(projectId, { max_rounds: 1 });
      const nextProjects = await listProjects();
      if (selectedProjectIdRef.current !== projectId) return;
      setProjects(nextProjects);
      setSelectedProjectId(projectId);
      await Promise.all([
        loadFilingReports(projectId),
        loadGrantabilityReports(projectId),
        loadWorksheets(projectId),
        loadCompletionRuns(projectId),
        loadOfficialCompileRuns(projectId),
        loadPostDraftReviews(projectId),
      ]);
      setMessage(
        `一键提升完成：${result.before_score}/100 -> ${result.after_score}/100，应用 ${result.accepted_patch_ids.length} 条补强`,
      );
    });
  }

  async function handleCreateWorksheet() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("claim-defense", async () => {
      const worksheet = await createClaimDefenseWorksheet(projectId);
      const stillSelected = await loadWorksheets(projectId);
      if (!stillSelected) return;
      setMessage(`权利要求防线工作表已生成：${worksheet.feature_records.length} 个特征`);
    });
  }

  async function handleRunDraftCompletion() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("completion", async () => {
      const run = await createDraftCompletionRun(projectId);
      if (selectedProjectIdRef.current !== projectId) return;
      setCompletionRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      setMessage(`初稿完善完成：整体评分 ${run.scorecard.overall}/100`);
    });
  }

  async function handleCompletionPatch(runId: string, patchId: string, action: "accept" | "reject") {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus(`completion-${action}`, async () => {
      const run =
        action === "accept"
          ? await acceptCompletionPatch(projectId, runId, patchId)
          : await rejectCompletionPatch(projectId, runId, patchId);
      if (selectedProjectIdRef.current !== projectId) return;
      setCompletionRuns((current) => current.map((item) => (item.id === run.id ? run : item)));
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage(action === "accept" ? "已接受完善补丁" : "已拒绝完善补丁");
    });
  }

  async function handleAcceptAllCompletionPatches(runId: string) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    const pendingCount = completionRuns
      .find((run) => run.id === runId)
      ?.patches.filter((patch) => patch.status === "proposed").length ?? 0;
    await withStatus("completion-accept-all", async () => {
      const run = await acceptAllCompletionPatches(projectId, runId);
      if (selectedProjectIdRef.current !== projectId) return;
      setCompletionRuns((current) => current.map((item) => (item.id === run.id ? run : item)));
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage(pendingCount > 0 ? `已一键接受 ${pendingCount} 条补强建议，评分已更新` : "暂无待接受补强建议");
    });
  }

  async function handleCreatePatentPoint(payload: PatentPointCreatePayload): Promise<boolean> {
    if (!selectedProject) return false;
    const projectId = selectedProject.id;
    let succeeded = false;
    await withStatus("patent-point-create", async () => {
      await createProjectPatentPoint(projectId, payload);
      const stillSelected = await loadPatentPoints(projectId);
      if (!stillSelected) return;
      await loadProjectKnowledge(projectId);
      setMessage("已加入护城河专利点");
      succeeded = true;
    });
    return succeeded;
  }

  async function handleSelectPatentPoint(point: PatentPointCandidate, candidatePool: PatentPointCandidate[] = []) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("patent-point-select", async () => {
      const payloads = buildPatentPointSelectionPayloads(point, candidatePool.length ? candidatePool : [point]);
      const existingById = new Map(visiblePatentPoints.map((candidate) => [candidate.id, candidate]));
      for (const entry of payloads) {
        const existing = existingById.get(entry.candidateId);
        if (existing) {
          if (existing.selected !== entry.payload.selected) {
            await updateProjectPatentPoint(projectId, entry.candidateId, { selected: entry.payload.selected });
          }
          continue;
        }
        await createProjectPatentPoint(projectId, entry.payload);
      }
      const stillSelected = await loadPatentPoints(projectId);
      if (!stillSelected) return;
      await loadProjectKnowledge(projectId);
      const backupCount = Math.max(0, payloads.length - 1);
      setMessage(`已选择主路线：${point.title}${backupCount ? `；已保存 ${backupCount} 条后备路线` : ""}`);
    });
  }

  async function handleDeletePatentPoint(point: PatentPointCandidate) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("patent-point-delete", async () => {
      await deleteProjectPatentPoint(projectId, point.id);
      const stillSelected = await loadPatentPoints(projectId);
      if (!stillSelected) return;
      await loadProjectKnowledge(projectId);
      setMessage(`已删除专利点：${point.title}`);
    });
  }

  async function handleEvaluatePatentPointMoat() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    const targets = visiblePatentPoints;
    if (!targets.length) return;
    await withStatus("patent-point-evaluate-moat", async () => {
      for (let i = 0; i < targets.length; i++) {
        setMessage(`正在评测护城河（${i + 1}/${targets.length}）：${targets[i].title}`);
        await evaluateProjectPatentPointMoat(projectId, targets[i].id);
        await loadPatentPoints(projectId);
      }
      setMessage(`已完成 ${targets.length} 个专利点的护城河评测`);
    });
  }

  async function handleDeleteProject(project: ProjectRecord) {
    if (!window.confirm(`确认删除项目“${project.name}”？该项目的运行记录和专利点也会删除。`)) {
      return;
    }
    await withStatus("project-delete", async () => {
      await deleteProject(project.id);
      const nextProjects = await listProjects();
      setProjects(nextProjects);
      if (selectedProjectIdRef.current === project.id) {
        setSelectedProjectId(nextProjects[0]?.id ?? "");
      } else if (!nextProjects.some((item) => item.id === selectedProjectIdRef.current)) {
        setSelectedProjectId("");
      }
      setMessage(`已删除项目：${project.name}`);
    });
  }

  function openExpertTool(tool: ExpertToolId) {
    setActiveExpertTool(tool);
    if (tool === "build" || tool === "corpus") {
      setActiveSection("knowledge");
    } else if (tool === "export") {
      setActiveSection("export");
    } else {
      setActiveSection("expert");
    }
  }

  function handleStartChoice(choice: StartChoiceId) {
    setStartChoice(choice);
    setActiveSection("workbench");
    if (choice === "external") {
      setActiveExpertTool("materials");
    }
  }

  function returnToStartChoices() {
    setStartChoice(null);
    setActiveSection("workbench");
  }

  return (
    <AppRoot
      activeSection={activeSection}
      activeExpertTool={activeExpertTool}
      startChoice={startChoice}
      selectedProject={selectedProject}
      projects={projects}
      busy={busy}
      busyElapsedSeconds={busyTimer.elapsedSeconds}
      message={message}
      error={error}
      health={health}
      agentDoctor={agentDoctor}
      backendStatus={backendStatus}
      projectListStatus={projectListStatus}
      theme={theme}
      onSelectSection={setActiveSection}
      onSelectExpertTool={setActiveExpertTool}
      onSelectProjectId={setSelectedProjectId}
      onReturnToStartChoices={returnToStartChoices}
      onChangeTheme={setTheme}
      onRefresh={refreshAll}
      projectState={{
        startChoice,
        selectedProject,
        projects,
        projectMaterials,
        disclosureRuns,
        deliberationRuns,
        visiblePatentPoints,
        formulaRequirement,
        formulaRuns,
        officialCompileRuns,
        currentSourceDraftHash,
        postDraftReviews,
        currentDraftHash,
        currentPackage,
        agentDoctor,
        selectedDeliberationProviders,
        selectedDeliberationParticipantProviders,
        selectedFormulaProviders,
        filingReports,
        worksheets,
        completionRuns,
        externalDraftSources,
        externalDraftIntakeRuns,
        busy,
        busyElapsedSeconds: busyTimer.elapsedSeconds,
        disclosureResearchMode,
      }}
      projectHandlers={{
        onStartChoice: handleStartChoice,
        onSelectProjectId: setSelectedProjectId,
        onDeleteProject: handleDeleteProject,
        onCreateIdeaProject: handleCreateIdeaProject,
        onCreateExternalDraft: handleCreateExternalDraft,
        onUploadExternalDraft: handleUploadExternalDraft,
        onStartExternalDraftIntake: handleStartExternalDraftIntake,
        onConfirmExternalDraftIntake: handleConfirmExternalDraftIntake,
        onUploadMaterial: handleUploadMaterial,
        onChangeDisclosureResearchMode: setDisclosureResearchMode,
        onStartDisclosure: () => void handleStartDisclosure(false),
        onCancelDisclosureRun: (runId) => void handleCancelDisclosureRun(runId),
        onRetryDisclosureRun: (runId) => void handleRetryDisclosureRun(runId),
        onSelectPatentPoint: (point, candidates) => void handleSelectPatentPoint(point, candidates),
        onStartDeliberation: () => void handleStartDeliberation(false),
        onCancelDeliberationRun: (runId) => void handleCancelDeliberationRun(runId),
        onRetryDeliberationRun: (runId) => void handleRetryDeliberationRun(runId),
        onStartFormula: () => void handleStartFormula(),
        onCancelFormulaRun: (runId) => void handleCancelFormulaRun(runId),
        onRetryFormulaRun: (runId) => void handleRetryFormulaRun(runId),
        onStartOfficialCompile: () => void handleStartOfficialCompile(),
        onStartKimiLanguagePolish: () => void handleStartKimiLanguagePolish(),
        onStartPostDraftReview: () => void handleStartPostDraftReview(),
        onApplyOfficialCompileCleanup: (runId) => void handleApplyOfficialCompileCleanup(runId),
        onApplyPostDraftSafePatches: (runId) => void handleApplyPostDraftSafePatches(runId),
        onSaveDraftPackage: (payload) => void handleSaveDraftPackage(payload),
        onDraftRepairPatchApplied: (issueId) => void handleDraftRepairPatchApplied(issueId),
        onCancelPostDraftReviewRun: (runId) => void handleCancelPostDraftReviewRun(runId),
        onRetryPostDraftReviewRun: (runId) => void handleRetryPostDraftReviewRun(runId),
        onToggleDeliberationProvider: handleToggleDeliberationProvider,
        onToggleDeliberationParticipantProvider: handleToggleDeliberationParticipantProvider,
        onToggleFormulaProvider: handleToggleFormulaProvider,
        onGenerateDraft: () => void handleGenerate(),
        onRunQualityChecks: () => void handleRunGuidedQualityChecks(),
        onImproveScore: () => void handleImproveScore(),
        onAcceptPatch: (runId, patchId) => void handleCompletionPatch(runId, patchId, "accept"),
        onAcceptAllPatches: (runId) => void handleAcceptAllCompletionPatches(runId),
        onOpenExpertTool: (tool) => openExpertTool(tool as ExpertToolId),
      }}
      corpusState={{
        selectedProject,
        projectKnowledge,
        cnipaQueryPack,
        importLedgers: projectKnowledgeImportLedgers,
        corpusJobForm,
        corpusJob,
        corpusVersions,
        corpusStats,
        documents,
        searchText,
        searchSection,
        searchResults,
        busy,
      }}
      corpusHandlers={{
        onCorpusFormChange: (patch) => setCorpusJobForm((current) => ({ ...current, ...patch })),
        onCreateCorpusJob: handleCreateCorpusJob,
        onUploadCorpusJobFile: handleUploadCorpusJobFile,
        onRunCorpusJob: handleRunCorpusJob,
        onGenerateKnowledgePlan: handleGenerateKnowledgePlan,
        onRunKnowledgeSearch: handleRunKnowledgeSearch,
        onCandidateDecision: handleCandidateDecision,
        onBuildProjectCorpus: handleBuildProjectCorpus,
        onImportCnipaExport: handleImportCnipaExport,
        onImport: handleImport,
        onSearch: handleSearch,
        onSearchText: setSearchText,
        onSearchSection: setSearchSection,
      }}
      qualityState={{
        selectedProject,
        projectKnowledge,
        filingReports,
        latestFilingReport,
        grantabilityReports,
        latestGrantabilityReport,
        worksheets,
        latestWorksheet,
        completionRuns,
        latestCompletionRun,
        latestOfficialCompileRun,
        latestPostDraftReview,
        currentDraftHash,
        currentSourceDraftHash,
        busy,
      }}
      qualityHandlers={{
        onRunFilingReadiness: handleRunFilingReadiness,
        onCreateGrantabilityReport: handleCreateGrantabilityReport,
        onCreateWorksheet: handleCreateWorksheet,
        onRunDraftCompletion: handleRunDraftCompletion,
        onImproveScore: handleImproveScore,
        onCompletionPatch: handleCompletionPatch,
        onReview: handleReview,
      }}
      postDraftState={{
        selectedProject,
        agentDoctor,
        visiblePatentPoints,
        projectMaterials,
        disclosureRuns,
        deliberationRuns,
        currentDisclosure,
        currentDeliberation,
        formulaRequirement,
        currentFormulaRun,
        currentPackage,
        latestOfficialCompileRun,
        latestPostDraftReview,
        exportReadiness,
        currentDraftHash,
        currentSourceDraftHash,
        currentQualityChecked,
        qualityCheckStates: currentQualityCheckStates,
        selectedDeliberationProviders,
        lastExport,
        busy,
        desktopDialogsAvailable: Boolean(
          (window as Window & DesktopMenuBridge).desktop?.dialogs?.saveOfficial &&
            (window as Window & DesktopMenuBridge).desktop?.dialogs?.openFolder,
        ),
      }}
      postDraftHandlers={{
        onCreatePatentPoint: handleCreatePatentPoint,
        onSelectPatentPoint: (point) => handleSelectPatentPoint(point),
        onDeletePatentPoint: handleDeletePatentPoint,
        onEvaluatePatentPointMoat: handleEvaluatePatentPointMoat,
        onUploadMaterial: handleUploadMaterial,
        onStartDisclosure: handleStartDisclosure,
        onRefreshDisclosures: async () => {
          if (selectedProject) await loadDisclosures(selectedProject.id);
        },
        onCancelDisclosureRun: handleCancelDisclosureRun,
        onRetryDisclosureRun: handleRetryDisclosureRun,
        onStartDeliberation: handleStartDeliberation,
        onToggleDeliberationProvider: handleToggleDeliberationProvider,
        onRefreshDeliberations: async () => {
          if (selectedProject) await loadDeliberations(selectedProject.id);
        },
        onCancelDeliberationRun: handleCancelDeliberationRun,
        onRetryDeliberationRun: handleRetryDeliberationRun,
        onGenerate: handleGenerate,
        onNativeExport: triggerNativeExport,
        onOpenExportFolder: triggerOpenExportFolder,
      }}
    />
  );
}

function useBusyTimer(busy: string): BusyTimer {
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!busy) {
      setStartedAt(null);
      return;
    }
    const nextStartedAt = Date.now();
    setStartedAt(nextStartedAt);
    setNow(nextStartedAt);
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [busy]);

  return {
    elapsedSeconds: startedAt ? Math.max(0, Math.floor((now - startedAt) / 1000)) : 0,
    startedAt,
  };
}


// QualityReportView + Distribution moved to ./views/widgets (pure leaves).
// percent() stays here — it's used by CorpusView, MoatView, etc. in App scope.
function percent(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function latestCompletedDisclosure(runs: DisclosureRun[]): DisclosureRun | null {
  return runs.find((run) => run.status === "completed" && run.package) ?? null;
}


// StatusPill moved to ./views/widgets (pure leaf, no App state).








// PreviewBlock moved to ./views/widgets (pure leaf, no App state).

export default App;
