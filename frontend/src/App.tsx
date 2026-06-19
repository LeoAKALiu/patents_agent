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
import { AgentProviderCards, normalizeAgentSelection, requiredAgentProviderIds } from "./AgentProviderCards";
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
  type OfficialDraftPackage,
  PatentPointCandidate,
  PatentPointCreatePayload,
  PatentDocument,
  PostDraftReviewRun,
  ProjectMaterial,
  PatentStrategyBrief,
  ProjectRecord,
  RuntimeFailure,
  RuntimeStageState,
  SearchResult,
  SectionType,
  type DraftCompletionRun,
  type ExternalDraftIntakeRun,
  type ExternalDraftSource,
  acceptCompletionPatch,
  applyPostDraftSafePatches,
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
  getHealth,
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
  searchCorpus,
  startKimiOfficialLanguagePolish,
  startProjectDisclosure,
  startProjectDeliberation,
  startExternalDraftIntakeRun,
  startFormulaRun,
  startOfficialCompileRun,
  startPostDraftReview,
  updateProjectDraftPackage,
  updateProjectPatentPoint,
  uploadCorpusJobFile,
  uploadExternalDraftSource,
  uploadProjectMaterial,
} from "./api";
import { GuidedPatentFlowView } from "./GuidedPatentFlow";
import { runtimeDisplayElapsedMs, runtimeDisplayElapsedSeconds, useRuntimeNow } from "./runtimeDisplay";
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
  CreateProjectView,
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

function App() {
  const [activeSection, setActiveSection] = useState<MainSectionId>(defaultMainSectionId);
  const [activeExpertTool, setActiveExpertTool] = useState<ExpertToolId>(defaultExpertToolId);
  const [startChoice, setStartChoice] = useState<StartChoiceId | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [agentDoctor, setAgentDoctor] = useState<AgentDoctorReport | null>(null);
  const [documents, setDocuments] = useState<PatentDocument[]>([]);
  const [corpusVersions, setCorpusVersions] = useState<CorpusVersion[]>([]);
  const [corpusStats, setCorpusStats] = useState<CorpusStats | null>(null);
  const [corpusJob, setCorpusJob] = useState<CorpusImportJob | null>(null);
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
  const [currentDraftHash, setCurrentDraftHash] = useState("");
  const [selectedDeliberationProviders, setSelectedDeliberationProviders] = useState<string[]>(requiredAgentProviderIds);
  const [selectedFormulaProviders, setSelectedFormulaProviders] = useState<string[]>(requiredAgentProviderIds);
  const [disclosureResearchMode, setDisclosureResearchMode] =
    useState<"standard" | "free_deep_research">("standard");
  const [filingReports, setFilingReports] = useState<FilingReadinessReport[]>([]);
  const [grantabilityReports, setGrantabilityReports] = useState<GrantabilityReport[]>([]);
  const [worksheets, setWorksheets] = useState<ClaimDefenseWorksheet[]>([]);
  const [completionRuns, setCompletionRuns] = useState<DraftCompletionRun[]>([]);
  const [externalDraftSources, setExternalDraftSources] = useState<ExternalDraftSource[]>([]);
  const [externalDraftIntakeRuns, setExternalDraftIntakeRuns] = useState<ExternalDraftIntakeRun[]>([]);
  const [patentPointsProjectId, setPatentPointsProjectId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [searchText, setSearchText] = useState("图像 神经网络 缺陷 方法");
  const [searchSection, setSearchSection] = useState<SectionType | "">("claims");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [projectName, setProjectName] = useState("");
  const [draftText, setDraftText] = useState("");
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
  const activeExpertToolEntry = expertToolGroups
    .flatMap((group) => group.tools)
    .find((tool) => tool.id === activeExpertTool);
  const activeShellSection =
    activeSection === "expert"
      ? {
          label: "专家工具",
          description: activeExpertToolEntry
            ? `${activeExpertToolEntry.label}：${activeExpertToolEntry.description}`
            : "高级能力按任务分组，结果可回写主流程或保留为内部材料。",
        }
      : activeSection === "utility"
        ? {
            label: "实用新型",
            description: "从结构方案撰写实用新型，聚焦部件连接关系、安装位置和附图说明。",
          }
        : mainSections.find((section) => section.id === activeSection) ?? mainSections[0];
  selectedProjectIdRef.current = selectedProject?.id ?? "";

  useEffect(() => {
    void refreshAll();
  }, [
    selectedProjectIdForRefresh,
    latestOfficialCompileRunId,
    latestPostDraftReviewId,
    currentDraftHash,
    currentSourceDraftHash,
    lastExportRefreshKey,
  ]);

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
        setActiveSection("expert");
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
    setSelectedDeliberationProviders((providers) => normalizeAgentSelection(agentDoctor, providers, "deliberation"));
    setSelectedFormulaProviders((providers) => normalizeAgentSelection(agentDoctor, providers, "formula"));
  }, [agentDoctor]);

  useEffect(() => {
    setOfficialCompileRuns([]);
    setCurrentSourceDraftHash("");
    setPostDraftReviews([]);
    setCurrentDraftHash("");
    setExternalDraftSources([]);
    setExternalDraftIntakeRuns([]);
    if (selectedProject?.id) {
      void loadDeliberations(selectedProject.id);
      void loadMaterials(selectedProject.id);
      void loadDisclosures(selectedProject.id);
      void loadFormulaState(selectedProject.id);
      void loadOfficialCompileRuns(selectedProject.id);
      void loadPostDraftReviews(selectedProject.id);
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
    }, 1000);
    return () => window.clearInterval(timer);
    // loadX functions are stable closures over setState only; they are not
    // listed because they do not change identity in a way that should reset
    // the interval. isAnyRunInFlight is the single state-derived signal.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProject?.id, isAnyRunInFlight]);

  async function refreshAll() {
    await withStatus("refresh", async () => {
      const [healthData, doctorData, corpusData, projectsData] = await Promise.all([
        getHealth(),
        getAgentDoctor(),
        listCorpus(),
        listProjects(),
      ]);
      const [versionsData, statsData] = await Promise.all([listCorpusVersions(), getCorpusStats()]);
      setHealth(healthData);
      setAgentDoctor(doctorData);
      setDocuments(corpusData);
      setCorpusVersions(versionsData);
      setCorpusStats(statsData);
      setProjects(projectsData);
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
    setSelectedProjectId(nextProjects[0]?.id ?? "");
    return false;
  }

  async function withStatus(label: string, task: () => Promise<void>) {
    setBusy(label);
    setError("");
    setMessage("");
    try {
      await task();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
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
        latestPostDraftReview?.status === "completed" &&
        latestPostDraftReview.export_allowed &&
        latestPostDraftReview.draft_package_hash === latestOfficialCompileRun.source_draft_hash &&
        latestPostDraftReview.official_compile_run_id === latestOfficialCompileRun.id &&
        latestPostDraftReview.official_package_hash === latestOfficialCompileRun.official_package_hash,
      );
      if (!allowed) {
        setError(
          "正式稿导出已锁定：需先通过针对当前正式稿的成稿会审。",
        );
        return;
      }
    }
    const projectName = selectedProject.name || "PatentAgent";
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

  async function handleCreateProject(event: FormEvent) {
    event.preventDefault();
    if (!projectName.trim() || !draftText.trim()) return;
    await withStatus("create", async () => {
      const project = await createProject(projectName.trim(), draftText.trim());
      const nextProjects = await listProjects();
      setProjects(nextProjects);
      setSelectedProjectId(project.id);
      setMessage(`已创建项目：${project.name}`);
      setActiveExpertTool("materials");
      setActiveSection("expert");
    });
  }

  async function handleCreateIdeaProject(payload: { name: string; idea: string; mode: PatentGoalMode; patentType: PatentType }) {
    await withStatus("guided-create", async () => {
      const prefix = projectGoalPrefix(payload.mode);
      const project = await createProject(payload.name, `${prefix}\n${payload.idea}`, payload.patentType);
      const nextProjects = await listProjects();
      setProjects(nextProjects);
      setSelectedProjectId(project.id);
      setProjectName("");
      setDraftText("");
      setMessage(`已创建项目：${project.name}`);
    });
  }

  async function handleUploadMaterial(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    const input = event.currentTarget.elements.namedItem("project-material-file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    await withStatus("material-upload", async () => {
      const material = await uploadProjectMaterial(projectId, file);
      const stillSelected = await loadMaterials(projectId);
      if (!stillSelected) return;
      setMessage(material.status === "processed" ? `已上传材料：${material.file_name}` : `材料解析失败：${material.warnings[0]}`);
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
      const run = await startProjectDeliberation(projectId, trace, selectedDeliberationProviders);
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
      const run = await startPostDraftReview(projectId, selectedDeliberationProviders);
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
    setSelectedDeliberationProviders((providers) => {
      const next = enabled ? [...providers, providerId] : providers.filter((id) => id !== providerId);
      return normalizeAgentSelection(agentDoctor, next, "deliberation");
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

  async function handleCreatePatentPoint(payload: PatentPointCreatePayload): Promise<boolean> {
    if (!selectedProject) return false;
    const projectId = selectedProject.id;
    let succeeded = false;
    await withStatus("patent-point-create", async () => {
      await createProjectPatentPoint(projectId, payload);
      const stillSelected = await loadPatentPoints(projectId);
      if (!stillSelected) return;
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
    setActiveSection("expert");
  }

  function handleStartChoice(choice: StartChoiceId) {
    setStartChoice(choice);
    setActiveSection("generate");
    if (choice === "external") {
      setActiveExpertTool("materials");
    }
  }

  function returnToStartChoices() {
    setStartChoice(null);
    setActiveSection("generate");
  }

  function renderExpertTool() {
    switch (activeExpertTool) {
      case "build":
        return (
          <CorpusBuildView
            form={corpusJobForm}
            job={corpusJob}
            versions={corpusVersions}
            stats={corpusStats}
            busy={busy}
            onFormChange={(patch) => setCorpusJobForm((current) => ({ ...current, ...patch }))}
            onCreateJob={handleCreateCorpusJob}
            onUploadFile={handleUploadCorpusJobFile}
            onRunJob={handleRunCorpusJob}
          />
        );
      case "corpus":
        return (
          <CorpusView
            documents={documents}
            searchText={searchText}
            searchSection={searchSection}
            searchResults={searchResults}
            busy={busy}
            onImport={handleImport}
            onSearch={handleSearch}
            onSearchText={setSearchText}
            onSearchSection={setSearchSection}
          />
        );
      case "moat":
        return (
          <MoatView
            project={selectedProject}
            points={visiblePatentPoints}
            busy={busy}
            onCreate={handleCreatePatentPoint}
            onSelect={handleSelectPatentPoint}
            onDelete={handleDeletePatentPoint}
            onEvaluateMoat={handleEvaluatePatentPointMoat}
          />
        );
      case "materials":
        return (
          <DisclosureView
            project={selectedProject}
            materials={projectMaterials}
            runs={disclosureRuns}
            busy={busy}
            onUpload={handleUploadMaterial}
            onStart={handleStartDisclosure}
            onRefresh={() => selectedProject && loadDisclosures(selectedProject.id)}
            onCancelRun={(runId) => void handleCancelDisclosureRun(runId)}
            onRetryRun={(runId) => void handleRetryDisclosureRun(runId)}
          />
        );
      case "deliberate":
        return (
          <DeliberationView
            project={selectedProject}
            doctor={agentDoctor}
            runs={deliberationRuns}
            disclosure={currentDisclosure}
            selectedProviders={selectedDeliberationProviders}
            busy={busy}
            onStart={handleStartDeliberation}
            onToggleProvider={handleToggleDeliberationProvider}
            onRefresh={() => selectedProject && loadDeliberations(selectedProject.id)}
            onCancelRun={(runId) => void handleCancelDeliberationRun(runId)}
            onRetryRun={(runId) => void handleRetryDeliberationRun(runId)}
          />
        );
      case "write":
        return (
          <WriteView
            project={selectedProject}
            deliberation={currentDeliberation}
            disclosure={currentDisclosure}
            formulaRequirement={formulaRequirement}
            formulaRun={currentFormulaRun}
            busy={busy}
            onGenerate={handleGenerate}
          />
        );
      case "readiness":
        return (
          <FilingReadinessView
            project={selectedProject}
            report={latestFilingReport}
            reports={filingReports}
            postDraftReview={latestPostDraftReview}
            officialCompileRun={latestOfficialCompileRun}
            currentDraftHash={currentDraftHash}
            currentSourceDraftHash={currentSourceDraftHash}
            busy={busy}
            onRun={handleRunFilingReadiness}
          />
        );
      case "grantability":
        return (
          <GrantabilityView
            project={selectedProject}
            report={latestGrantabilityReport}
            reports={grantabilityReports}
            busy={busy}
            onGenerate={handleCreateGrantabilityReport}
          />
        );
      case "claimDefense":
        return (
          <ClaimDefenseView
            project={selectedProject}
            worksheet={latestWorksheet}
            worksheets={worksheets}
            busy={busy}
            onGenerate={handleCreateWorksheet}
          />
        );
      case "completion":
        return (
          <DraftCompletionView
            project={selectedProject}
            run={latestCompletionRun}
            runs={completionRuns}
            busy={busy}
            onRun={handleRunDraftCompletion}
            onImprove={handleImproveScore}
            onPatch={handleCompletionPatch}
          />
        );
      case "review":
        return <ReviewView project={selectedProject} busy={busy} onReview={handleReview} />;
      case "export":
        return (
          <ExportView
            project={selectedProject}
            packageValue={currentPackage}
            postDraftReview={latestPostDraftReview}
            officialCompileRun={latestOfficialCompileRun}
            currentDraftHash={currentDraftHash}
            currentSourceDraftHash={currentSourceDraftHash}
            lastExport={lastExport}
            onNativeExport={(format) => {
              void triggerNativeExport(format);
            }}
            onOpenExportFolder={() => {
              void triggerOpenExportFolder();
            }}
            desktopDialogsAvailable={Boolean(
              (window as Window & DesktopMenuBridge).desktop?.dialogs?.saveOfficial &&
                (window as Window & DesktopMenuBridge).desktop?.dialogs?.openFolder,
            )}
          />
        );
    }
  }

  function handleKeySectionSelect(id: "idea" | "moat" | "deliberate") {
    if (id === "idea") {
      setActiveSection("generate");
      return;
    }
    setActiveSection("expert");
    setActiveExpertTool(id);
  }

  return (
    <div className="app-shell">
      <ShellSidebar
        mainSections={mainSections.map((section) => ({
          id: section.id,
          label: section.label,
          icon: <section.icon size={16} aria-hidden="true" />,
          description: section.description,
        }))}
        activeSectionId={activeSection}
        onSelectSection={(id) => setActiveSection(id as MainSectionId)}
        keySections={
          selectedProject
            ? [
                { id: "idea", label: "01 想法与材料", icon: <ClipboardList size={14} aria-hidden="true" /> },
                { id: "moat", label: "02 发明点确认", icon: <Search size={14} aria-hidden="true" /> },
                { id: "deliberate", label: "03 多智能体会审", icon: <UsersRound size={14} aria-hidden="true" /> },
              ]
            : undefined
        }
        onSelectKeySection={(id) => handleKeySectionSelect(id as "idea" | "moat" | "deliberate")}
        footer={
          <SystemStatusPanel
            selectedProject={selectedProject}
            health={health}
            agentDoctor={agentDoctor}
            agentRunModeLabel={agentRunModeLabel}
            onRefresh={refreshAll}
          />
        }
      />

      <main className="main-area">
        <ShellTopbar
          title={activeShellSection.label}
          subtitle={activeShellSection.description}
          onRefresh={refreshAll}
          statusLabel={busy ? "处理中" : "空闲"}
          statusVariant={busy ? "busy" : "idle"}
          projectSelector={
            <ProjectSelect
              projects={projects}
              selectedProjectId={selectedProject?.id ?? ""}
              onChange={setSelectedProjectId}
            />
          }
          actions={
            <>
              {!(activeSection === "generate" && !selectedProject && !startChoice) && (
                <>
                  {activeSection !== "expert" && (
                    <Button variant="outline" onClick={() => setActiveSection("expert")} type="button">
                      <Gauge size={16} />
                      <span>专家工具</span>
                    </Button>
                  )}
                  {activeSection === "expert" && (
                    <Button variant="outline" onClick={() => setActiveSection("generate")} type="button">
                      <Wand2 size={16} />
                      <span>返回向导</span>
                    </Button>
                  )}
                  {(startChoice || activeSection === "expert") && (
                    <Button variant="outline" onClick={returnToStartChoices} type="button">
                      <ClipboardList size={16} />
                      <span>返回三选一</span>
                    </Button>
                  )}
                </>
              )}
            </>
          }
        />

        {/* Mobile nav */}
        <nav className="mobile-nav" aria-label="移动主导航">
          {mainSections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                className={activeSection === section.id ? "is-active" : ""}
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                type="button"
                title={section.label}
              >
                <Icon size={16} />
                <span>{section.label}</span>
              </button>
            );
          })}
        </nav>

        {(busy || message || error) && (
          <div className={error ? "notice error" : "notice"}>
            {busy && <Loader2 className="animate-spin" size={16} />}
            <span>{error || message || guidedBusyLabel(busy) || "处理中"}</span>
            {!error && busy && <BusyOperationConsole log={guidedOperationLog(busy, busyTimer.elapsedSeconds)} />}
          </div>
        )}

        <div className="workspace">

        {(activeSection === "generate" || activeSection === "utility") && (
          <div className="px-4 md:px-8 py-4 md:py-6">
          {!selectedProject && !startChoice ? (
            <StartChoiceScreen onSelect={handleStartChoice} />
          ) : (
            <GuidedPatentFlowView
            project={selectedProject}
            materials={projectMaterials}
            disclosures={disclosureRuns}
            deliberations={deliberationRuns}
            patentPoints={visiblePatentPoints}
            formulaRequirement={formulaRequirement}
            formulaRuns={formulaRuns}
            officialCompileRuns={officialCompileRuns}
            currentSourceDraftHash={currentSourceDraftHash}
            postDraftReviews={postDraftReviews}
            currentDraftHash={currentDraftHash}
            currentPackage={currentPackage}
            agentDoctor={agentDoctor}
            selectedDeliberationProviders={selectedDeliberationProviders}
            selectedFormulaProviders={selectedFormulaProviders}
            filingReports={filingReports}
            worksheets={worksheets}
            completionRuns={completionRuns}
            externalDraftSources={externalDraftSources}
            externalDraftIntakeRuns={externalDraftIntakeRuns}
            busy={busy}
            busyElapsedSeconds={busyTimer.elapsedSeconds}
            fixedGoalMode={startChoice === "utility" || activeSection === "utility" ? "utility" : undefined}
            initialIntakeMode={startChoice === "external" ? "external" : "idea"}
            onCreateIdeaProject={handleCreateIdeaProject}
            onCreateExternalDraft={handleCreateExternalDraft}
            onUploadExternalDraft={handleUploadExternalDraft}
            onStartExternalDraftIntake={handleStartExternalDraftIntake}
            onConfirmExternalDraftIntake={handleConfirmExternalDraftIntake}
            onUploadMaterial={handleUploadMaterial}
            disclosureResearchMode={disclosureResearchMode}
            onChangeDisclosureResearchMode={setDisclosureResearchMode}
            onStartDisclosure={() => void handleStartDisclosure(false)}
            onCancelDisclosureRun={(runId) => void handleCancelDisclosureRun(runId)}
            onRetryDisclosureRun={(runId) => void handleRetryDisclosureRun(runId)}
            onSelectPatentPoint={(point, candidates) => void handleSelectPatentPoint(point, candidates)}
            onStartDeliberation={() => void handleStartDeliberation(false)}
            onCancelDeliberationRun={(runId) => void handleCancelDeliberationRun(runId)}
            onRetryDeliberationRun={(runId) => void handleRetryDeliberationRun(runId)}
            onStartFormula={() => void handleStartFormula()}
            onCancelFormulaRun={(runId) => void handleCancelFormulaRun(runId)}
            onRetryFormulaRun={(runId) => void handleRetryFormulaRun(runId)}
            onStartOfficialCompile={() => void handleStartOfficialCompile()}
            onStartKimiLanguagePolish={() => void handleStartKimiLanguagePolish()}
            onStartPostDraftReview={() => void handleStartPostDraftReview()}
            onApplyPostDraftSafePatches={(runId) => void handleApplyPostDraftSafePatches(runId)}
            onSaveDraftPackage={(payload) => void handleSaveDraftPackage(payload)}
            onCancelPostDraftReviewRun={(runId) => void handleCancelPostDraftReviewRun(runId)}
            onRetryPostDraftReviewRun={(runId) => void handleRetryPostDraftReviewRun(runId)}
            onToggleDeliberationProvider={handleToggleDeliberationProvider}
            onToggleFormulaProvider={handleToggleFormulaProvider}
            onGenerateDraft={() => void handleGenerate()}
            onRunQualityChecks={() => void handleRunGuidedQualityChecks()}
            onImproveScore={() => void handleImproveScore()}
            onAcceptPatch={(runId, patchId) => void handleCompletionPatch(runId, patchId, "accept")}
            onOpenExpertTool={openExpertTool}
            />
          )}
          </div>
        )}
        {activeSection === "projects" && (
          <div className="px-4 md:px-8 py-4 md:py-6">
            <ProjectsOverview
              projects={projects}
              selectedProjectId={selectedProject?.id ?? ""}
              onSelect={setSelectedProjectId}
              onDelete={(project) => void handleDeleteProject(project)}
              busy={busy}
            />
          </div>
        )}
        {activeSection === "settings" && (
          <div className="px-4 md:px-8 py-4 md:py-6">
            <SettingsPanel theme={theme} onThemeChange={setTheme} />
          </div>
        )}
        {activeSection === "expert" && (
          <div className="flex flex-col gap-4">
            <ExpertToolChooser activeToolId={activeExpertTool} onSelect={setActiveExpertTool} />
            {renderExpertTool()}
          </div>
        )}
      </div>
    </main>
  </div>
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
