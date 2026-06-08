import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
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

import { AgentProviderCards, normalizeAgentSelection, requiredAgentProviderIds } from "./AgentProviderCards";
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
  Health,
  OfficialCompileRun,
  PatentPointCandidate,
  PatentPointCreatePayload,
  PatentDocument,
  PostDraftReviewRun,
  ProjectMaterial,
  PatentStrategyBrief,
  ProjectRecord,
  SearchResult,
  SectionType,
  type DraftCompletionRun,
  acceptCompletionPatch,
  createClaimDefenseWorksheet,
  createCorpusJob,
  createDraftCompletionRun,
  createFilingReadinessReport,
  createProject,
  createProjectPatentPoint,
  deleteProject,
  deleteProjectPatentPoint,
  disclosureExportUrl,
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
  listFilingReadinessReports,
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
  runCorpusJob,
  searchCorpus,
  startProjectDisclosure,
  startProjectDeliberation,
  startFormulaRun,
  startOfficialCompileRun,
  startPostDraftReview,
  updateProjectPatentPoint,
  uploadCorpusJobFile,
  uploadProjectMaterial,
} from "./api";
import { GuidedPatentFlowView } from "./GuidedPatentFlow";
import {
  canExportPackage,
  completionCategoryLabel,
  completionTargetLabel,
  evidenceStatusLabel,
  featureClassificationLabel,
  latestCompletedDeliberation,
  moatScoreTotal,
  readinessStatusLabel,
  severityLabel,
  sourceTypeLabel,
} from "./domain";
import {
  defaultExpertToolId,
  defaultMainSectionId,
  buildPatentPointSelectionPayloads,
  expertToolGroups,
  guidedBusyLabel,
  guidedOperationLog,
  mainSections,
  selectCurrentOfficialCompileRun,
  selectLatestMatchingPostDraftReview,
  type ExpertToolId,
  type MainSectionId,
  type PatentGoalMode,
} from "./guidedFlow";


const sectionOptions: Array<{ value: SectionType | ""; label: string }> = [
  { value: "", label: "全部章节" },
  { value: "claims", label: "权利要求书" },
  { value: "abstract", label: "摘要" },
  { value: "summary", label: "发明内容" },
  { value: "embodiments", label: "具体实施方式" },
  { value: "drawings", label: "附图说明" },
];

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

function App() {
  const [activeSection, setActiveSection] = useState<MainSectionId>(defaultMainSectionId);
  const [activeExpertTool, setActiveExpertTool] = useState<ExpertToolId>(defaultExpertToolId);
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
  const [filingReports, setFilingReports] = useState<FilingReadinessReport[]>([]);
  const [worksheets, setWorksheets] = useState<ClaimDefenseWorksheet[]>([]);
  const [completionRuns, setCompletionRuns] = useState<DraftCompletionRun[]>([]);
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
  const selectedProjectIdRef = useRef("");
  const busyTimer = useBusyTimer(busy);

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
  const latestWorksheet = worksheets[0] ?? null;
  const latestCompletionRun = completionRuns[0] ?? null;
  const latestOfficialCompileRun = selectCurrentOfficialCompileRun(officialCompileRuns, currentSourceDraftHash);
  const latestPostDraftReview = selectLatestMatchingPostDraftReview(postDraftReviews, latestOfficialCompileRun);
  const activeMainSection = mainSections.find((section) => section.id === activeSection) ?? mainSections[0];
  const activeExpertToolEntry = expertToolGroups
    .flatMap((group) => group.tools)
    .find((tool) => tool.id === activeExpertTool);
  selectedProjectIdRef.current = selectedProject?.id ?? "";

  useEffect(() => {
    void refreshAll();
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
    if (selectedProject?.id) {
      void loadDeliberations(selectedProject.id);
      void loadMaterials(selectedProject.id);
      void loadDisclosures(selectedProject.id);
      void loadFormulaState(selectedProject.id);
      void loadOfficialCompileRuns(selectedProject.id);
      void loadPostDraftReviews(selectedProject.id);
      setPatentPoints([]);
      setPatentPointsProjectId("");
      setFilingReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      void loadPatentPoints(selectedProject.id);
      void loadFilingReports(selectedProject.id);
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
      setWorksheets([]);
      setCompletionRuns([]);
      setPatentPointsProjectId("");
    }
  }, [selectedProject?.id]);

  useEffect(() => {
    const deliberating = deliberationRuns.some((run) => run.status === "queued" || run.status === "running");
    const disclosing = disclosureRuns.some((run) => run.status === "queued" || run.status === "running");
    const formulaRunning = formulaRuns.some((run) => run.status === "queued" || run.status === "running");
    const postDraftReviewing = postDraftReviews.some((run) => run.status === "queued" || run.status === "running");
    if (!selectedProject?.id || (!deliberating && !disclosing && !formulaRunning && !postDraftReviewing)) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadDeliberations(selectedProject.id);
      void loadDisclosures(selectedProject.id);
      void loadFormulaState(selectedProject.id);
      void loadOfficialCompileRuns(selectedProject.id);
      void loadPostDraftReviews(selectedProject.id);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [selectedProject?.id, deliberationRuns, disclosureRuns, formulaRuns, postDraftReviews]);

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
    try {
      const runs = await listProjectDeliberations(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setDeliberationRuns(runs);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setDeliberationRuns([]);
      }
      return false;
    }
  }

  async function loadMaterials(projectId: string): Promise<boolean> {
    try {
      const materials = await listProjectMaterials(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setProjectMaterials(materials);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setProjectMaterials([]);
      }
      return false;
    }
  }

  async function loadDisclosures(projectId: string): Promise<boolean> {
    try {
      const runs = await listProjectDisclosures(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setDisclosureRuns(runs);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setDisclosureRuns([]);
      }
      return false;
    }
  }

  async function loadFormulaState(projectId: string): Promise<boolean> {
    try {
      const [requirement, runs] = await Promise.all([getFormulaRequirement(projectId), listFormulaRuns(projectId)]);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setFormulaRequirement(requirement);
      setFormulaRuns(runs);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setFormulaRequirement(null);
        setFormulaRuns([]);
      }
      return false;
    }
  }

  async function loadPostDraftReviews(projectId: string): Promise<boolean> {
    try {
      const { runs, current_draft_hash } = await listPostDraftReviews(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setPostDraftReviews(runs);
      setCurrentDraftHash(current_draft_hash);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setPostDraftReviews([]);
        setCurrentDraftHash("");
      }
      return false;
    }
  }

  async function loadOfficialCompileRuns(projectId: string): Promise<boolean> {
    try {
      const { runs, current_source_draft_hash } = await listOfficialCompileRuns(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setOfficialCompileRuns(runs);
      setCurrentSourceDraftHash(current_source_draft_hash);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setOfficialCompileRuns([]);
        setCurrentSourceDraftHash("");
      }
      return false;
    }
  }

  async function loadPatentPoints(projectId: string): Promise<boolean> {
    try {
      const points = await listProjectPatentPoints(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setPatentPoints(points);
      setPatentPointsProjectId(projectId);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setPatentPoints([]);
        setPatentPointsProjectId("");
      }
      return false;
    }
  }

  async function loadFilingReports(projectId: string): Promise<boolean> {
    try {
      const reports = await listFilingReadinessReports(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setFilingReports(reports);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setFilingReports([]);
      }
      return false;
    }
  }

  async function loadWorksheets(projectId: string): Promise<boolean> {
    try {
      const nextWorksheets = await listClaimDefenseWorksheets(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setWorksheets(nextWorksheets);
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
      const runs = await listDraftCompletionRuns(projectId);
      if (selectedProjectIdRef.current !== projectId) {
        return false;
      }
      setCompletionRuns(runs);
      return true;
    } catch {
      if (selectedProjectIdRef.current === projectId) {
        setCompletionRuns([]);
      }
      return false;
    }
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

  async function handleCreateIdeaProject(payload: { name: string; idea: string; mode: PatentGoalMode }) {
    await withStatus("guided-create", async () => {
      const prefix =
        payload.mode === "stable"
          ? "目标模式：授权稳健。"
          : payload.mode === "broad"
            ? "目标模式：保护范围优先。"
            : payload.mode === "fast"
              ? "目标模式：快速初稿。"
              : "目标模式：专利护城河，允许可行未验证方案进入内部策略。";
      const project = await createProject(payload.name, `${prefix}\n${payload.idea}`);
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

  async function handleStartDisclosure(trace = false) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("disclosure", async () => {
      const run = await startProjectDisclosure(projectId, trace);
      const stillSelected = await loadDisclosures(projectId);
      if (!stillSelected) return;
      setMessage(`前置材料生成已${run.status === "completed" ? "完成" : "启动"}：${run.status}`);
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
      setMessage(`会审已${run.status === "completed" ? "完成" : "启动"}：${run.run_mode}`);
    });
  }

  async function handleStartFormula() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("formula", async () => {
      const run = await startFormulaRun(projectId, selectedFormulaProviders);
      const stillSelected = await loadFormulaState(projectId);
      if (!stillSelected) return;
      setMessage(`核心公式已${run.status === "completed" ? "完成" : "启动"}：${run.status}`);
    });
  }

  async function handleStartPostDraftReview() {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("post-draft-review", async () => {
      const run = await startPostDraftReview(projectId, selectedDeliberationProviders);
      const stillSelected = await loadPostDraftReviews(projectId);
      if (!stillSelected) return;
      setMessage(`成稿会审已${run.status === "completed" ? "完成" : "启动"}：${run.export_allowed ? "允许正式导出" : run.status}`);
    });
  }

  async function handleStartOfficialCompile() {
    if (!selectedProject?.package) return;
    const projectId = selectedProject.id;
    await withStatus("official-compile", async () => {
      const run = await startOfficialCompileRun(projectId);
      const stillSelected = await loadOfficialCompileRuns(projectId);
      if (!stillSelected) return;
      setMessage(run.status === "completed" ? "正式稿编译完成" : `正式稿编译${run.status}`);
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
      await reviewProject(projectId);
      const report = await createFilingReadinessReport(projectId);
      const worksheet = await createClaimDefenseWorksheet(projectId);
      const completion = await createDraftCompletionRun(projectId);
      const nextProjects = await listProjects();
      if (selectedProjectIdRef.current !== projectId) return;
      setProjects(nextProjects);
      setSelectedProjectId(projectId);
      setFilingReports((current) => [report, ...current.filter((item) => item.id !== report.id)]);
      setWorksheets((current) => [worksheet, ...current.filter((item) => item.id !== worksheet.id)]);
      setCompletionRuns((current) => [completion, ...current.filter((item) => item.id !== completion.id)]);
      await loadOfficialCompileRuns(projectId);
      await loadPostDraftReviews(projectId);
      setMessage(`质量检查完成：整体评分 ${completion.scorecard.overall}/100`);
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
          />
        );
    }
  }

  return (
    <main className="grid grid-cols-[minmax(220px,280px)_minmax(0,1fr)] min-h-screen">
      <aside className="bg-[#112a2d]/70 text-white p-6 flex flex-col gap-6 border-r border-white/20 shadow-[12px_0_42px_rgba(22,42,44,0.18)] backdrop-blur-xl saturate-125">
        <div className="flex gap-3 items-center">
          <img className="w-10 h-10 block rounded-2xl shadow-[inset_0_1px_0_rgba(255,255,255,0.82),0_12px_26px_rgba(0,0,0,0.16)]" src="/logo.svg" alt="" aria-hidden="true" />
          <div>
            <h1>PatentAgent</h1>
            <p>专利护城河工程系统</p>
          </div>
        </div>
        <nav className="tab-list" aria-label="主导航">
          {mainSections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                className={activeSection === section.id ? "flex items-center gap-3 px-4 py-3 rounded-xl bg-white/20 text-white font-medium" : "flex items-center gap-3 px-4 py-3 rounded-xl text-white/70 hover:bg-white/10 hover:text-white transition-colors"}
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                type="button"
                title={section.description}
              >
                <Icon size={18} />
                <span>{section.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="mt-auto flex flex-col gap-3 p-4 bg-black/20 rounded-2xl text-sm text-white/80">
          <div className={health?.llm_configured ? "flex items-center gap-2 text-emerald-400" : "flex items-center gap-2 text-amber-400"}>
            {health?.llm_configured ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <span>{health?.llm_configured ? "模型已配置" : "未配置 DEEPSEEK_API_KEY"}</span>
          </div>
          <div className={agentDoctor?.status === "blocked" ? "flex items-center gap-2 text-amber-400" : "flex items-center gap-2 text-emerald-400"}>
            {agentDoctor?.status === "blocked" ? <AlertTriangle size={16} /> : <UsersRound size={16} />}
            <span>Agent {agentDoctor?.run_mode ?? "unknown"}</span>
          </div>
          <p>生成时会向云端模型服务发送 draft 与检索片段。</p>
          <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-transparent hover:bg-white/10 text-white transition-colors disabled:opacity-50" onClick={refreshAll} type="button" title="刷新">
            <RefreshCw size={17} />
            <span>刷新</span>
          </button>
        </div>
      </aside>

      <section className="flex flex-col w-full min-h-screen bg-[#f3f5f5]">
        <header className="flex items-center gap-4 px-8 py-5 border-b border-white/40 shadow-sm backdrop-blur-md bg-white/40 sticky top-0 z-10">
          <div>
            <p className="text-sm font-semibold tracking-wider uppercase text-[#267a78]/80">Guided Patent Workbench</p>
            <h2>{activeSection === "expert" ? activeExpertToolEntry?.label ?? "专家工具" : activeMainSection.label}</h2>
            <p className="text-sm text-[#142424]/60 mt-1">
              {activeSection === "expert"
                ? activeExpertToolEntry?.description ?? "进入旧工作台和高级检查"
                : activeMainSection.description}
            </p>
          </div>
          <ProjectSelect
            projects={projects}
            selectedProjectId={selectedProject?.id ?? ""}
            onChange={setSelectedProjectId}
          />
        </header>

        {(busy || message || error) && (
          <div className={error ? "flex items-center gap-3 px-8 py-3 bg-red-50 text-red-700 font-medium border-b border-red-200" : "flex items-center gap-3 px-8 py-3 bg-[#e8f0f0] text-[#142424] font-medium border-b border-[#267a78]/20"}>
            {busy && <Loader2 className="animate-spin" size={16} />}
            <span>{error || message || guidedBusyLabel(busy) || "处理中"}</span>
            {!error && busy && <BusyOperationConsole log={guidedOperationLog(busy, busyTimer.elapsedSeconds)} />}
          </div>
        )}

        {activeSection === "generate" && (
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
            agentDoctor={agentDoctor}
            selectedDeliberationProviders={selectedDeliberationProviders}
            selectedFormulaProviders={selectedFormulaProviders}
            filingReports={filingReports}
            worksheets={worksheets}
            completionRuns={completionRuns}
            busy={busy}
            busyElapsedSeconds={busyTimer.elapsedSeconds}
            onCreateIdeaProject={handleCreateIdeaProject}
            onUploadMaterial={handleUploadMaterial}
            onStartDisclosure={() => void handleStartDisclosure(false)}
            onSelectPatentPoint={(point, candidates) => void handleSelectPatentPoint(point, candidates)}
            onStartDeliberation={() => void handleStartDeliberation(false)}
            onStartFormula={() => void handleStartFormula()}
            onStartOfficialCompile={() => void handleStartOfficialCompile()}
            onStartPostDraftReview={() => void handleStartPostDraftReview()}
            onToggleDeliberationProvider={handleToggleDeliberationProvider}
            onToggleFormulaProvider={handleToggleFormulaProvider}
            onGenerateDraft={() => void handleGenerate()}
            onRunQualityChecks={() => void handleRunGuidedQualityChecks()}
            onImproveScore={() => void handleImproveScore()}
            onAcceptPatch={(runId, patchId) => void handleCompletionPatch(runId, patchId, "accept")}
            onOpenExpertTool={openExpertTool}
          />
        )}
        {activeSection === "projects" && (
          <ProjectsOverview
            projects={projects}
            selectedProjectId={selectedProject?.id ?? ""}
            onSelect={setSelectedProjectId}
            onDelete={(project) => void handleDeleteProject(project)}
            busy={busy}
          />
        )}
        {activeSection === "expert" && (
          <div className="flex flex-col gap-4">
            <ExpertToolChooser activeToolId={activeExpertTool} onSelect={setActiveExpertTool} />
            {renderExpertTool()}
          </div>
        )}
      </section>
    </main>
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

function BusyOperationConsole({ log }: { log: ReturnType<typeof guidedOperationLog> }) {
  if (!log) return null;
  return (
    <div className="bg-black/80 text-white/90 p-4 rounded-xl font-mono text-xs overflow-auto max-h-32 mt-2 w-full" role="status" aria-label={log.label}>
      <pre>{log.lines.join("\n")}</pre>
    </div>
  );
}

function CorpusBuildView({
  form,
  job,
  versions,
  stats,
  busy,
  onFormChange,
  onCreateJob,
  onUploadFile,
  onRunJob,
}: {
  form: CorpusJobForm;
  job: CorpusImportJob | null;
  versions: CorpusVersion[];
  stats: CorpusStats | null;
  busy: string;
  onFormChange: (patch: Partial<CorpusJobForm>) => void;
  onCreateJob: (event: FormEvent) => void;
  onUploadFile: (event: FormEvent<HTMLFormElement>) => void;
  onRunJob: () => void;
}) {
  const report = job?.quality_report ?? versions[0]?.quality_report ?? null;
  const jobHint = !job
    ? "先创建导入任务，再上传官方导出物。"
    : job.input_paths.length === 0
      ? "任务已创建，下一步请选择 ZIP、CSV/XLSX 或全文文件并点击“上传批次文件”。"
      : job.status === "queued"
        ? "批次文件已上传，下一步点击右上角“运行导入”。"
        : job.status === "running"
          ? "导入正在运行，完成后会刷新入库、去重、过滤和失败数量。"
          : job.status === "completed"
            ? "导入已完成，可在语料统计和知识库检索中查看结果。"
            : "导入失败，请查看失败数量和质量报告。";
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>官方导出物批量建库</h3>
          <p>支持 ZIP、CSV/XLSX 元数据表和 PDF/XML/TXT/DOCX 全文配对导入；扫描版 PDF 会进入失败清单。</p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
          disabled={!job || job.input_paths.length === 0 || busy === "corpus-run"}
          onClick={onRunJob}
          type="button"
        >
          <FileArchive size={18} />
          <span>运行导入</span>
        </button>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>导入任务</h3>
          <form className="flex flex-col gap-4" onSubmit={onCreateJob}>
            <label>
              <span>来源类型</span>
              <select value={form.source_type} onChange={(event) => onFormChange({ source_type: event.target.value })}>
                <option value="cnipa_export">CNIPA 导出</option>
                <option value="local_export">地方系统导出</option>
                <option value="google_patents_export">Google Patents 导出</option>
                <option value="public_service_export">公共服务平台导出</option>
              </select>
            </label>
            <label>
              <span>来源名称</span>
              <input value={form.source_name} onChange={(event) => onFormChange({ source_name: event.target.value })} />
            </label>
            <label>
              <span>检索式 / 批次说明</span>
              <textarea
                className="w-full rounded-xl border border-white/60 bg-white/50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#267a78]/40 min-h-[80px]"
                value={form.query}
                onChange={(event) => onFormChange({ query: event.target.value })}
              />
            </label>
            <label>
              <span>语料版本</span>
              <input
                value={form.version_name}
                onChange={(event) => onFormChange({ version_name: event.target.value })}
              />
            </label>
            <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "corpus-job"} type="submit">
              <FileText size={17} />
              <span>创建任务</span>
            </button>
          </form>

          <form className="flex flex-col gap-4 p-4 border-2 border-dashed border-white/60 rounded-2xl bg-white/30" onSubmit={onUploadFile}>
            {job && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">{jobHint}</p>}
            <input
              id="corpus-batch-file"
              name="corpus-batch-file"
              type="file"
              accept=".zip,.csv,.xlsx,.xlsm,.pdf,.docx,.txt,.md,.markdown,.xml"
              disabled={!job}
            />
            <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" disabled={!job || busy === "corpus-upload"} type="submit">
              <Upload size={17} />
              <span>上传批次文件</span>
            </button>
          </form>
        </div>

        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>任务进度</h3>
          {job ? (
            <>
              <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">{jobHint}</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatusPill label="状态" value={job.status} />
                <StatusPill label="版本" value={job.version_name} />
                <StatusPill label="输入批次" value={String(job.input_paths.length)} />
                <StatusPill label="已处理" value={String(job.processed_files)} />
                <StatusPill label="入库" value={String(job.imported_documents)} />
                <StatusPill label="去重" value={String(job.duplicate_documents)} />
                <StatusPill label="过滤" value={String(job.filtered_documents)} />
                <StatusPill label="失败" value={String(job.failed_documents)} />
              </div>
            </>
          ) : (
            <p className="text-sm text-[#142424]/50 italic py-4">先创建导入任务，再上传官方导出物。</p>
          )}
          {report && <QualityReportView report={report} />}
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>语料统计</h3>
          {stats ? (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatusPill label="专利数" value={String(stats.document_count)} />
                <StatusPill label="片段数" value={String(stats.chunk_count)} />
                <StatusPill label="权利要求覆盖" value={percent(stats.section_coverage.claims)} />
                <StatusPill label="全文章节覆盖" value={percent(stats.section_coverage.embodiments)} />
              </div>
              <Distribution title="IPC 分布" values={stats.ipc_distribution} />
              <Distribution title="申请年份" values={stats.application_year_distribution} />
              <Distribution title="来源系统" values={stats.source_distribution} />
            </div>
          ) : (
            <p className="text-sm text-[#142424]/50 italic py-4">暂无统计</p>
          )}
        </div>

        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>语料版本</h3>
          <div className="flex flex-col gap-3">
            {versions.map((version) => (
              <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={version.id}>
                <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                  <span>{version.domain}</span>
                  <span>{version.document_count} 件 / {version.chunk_count} 片段</span>
                </div>
                <p><strong>{version.name}</strong></p>
                <p>{version.query || version.source_name || "未记录检索式"}</p>
              </article>
            ))}
            {versions.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无版本</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

function QualityReportView({ report }: { report: CorpusImportJob["quality_report"] }) {
  if (!report) return null;
  return (
    <div className="flex flex-col gap-4 mt-6 p-6 rounded-2xl bg-red-50/50 border border-red-100">
      <h4>质量报告</h4>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatusPill label="可抽取率" value={percent(report.fulltext_extractable_rate)} />
        <StatusPill label="索引片段" value={String(report.indexed_chunks)} />
        <StatusPill label="低质量样本" value={String(report.low_quality_documents.length)} />
        <StatusPill label="错误数" value={String(report.failures.length)} />
      </div>
      {report.failures.length > 0 && (
        <div className="flex flex-col gap-3">
          {report.failures.slice(0, 6).map((failure) => (
            <article className="flex gap-3 items-start p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={`${failure.file}-${failure.reason}`}>
              <AlertTriangle size={18} />
              <div>
                <strong>{failure.file}</strong>
                <span>{failure.reason}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values).slice(0, 8);
  return (
    <div className="flex flex-col gap-3 mt-4 p-5 rounded-2xl bg-white/40 border border-white/40">
      <div className="flex items-center gap-2 text-sm font-semibold text-[#142424]">
        <BarChart3 size={16} />
        <strong>{title}</strong>
      </div>
      {entries.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {entries.map(([key, value]) => (
            <span className="px-3 py-1 rounded-lg bg-white/60 border border-white/80 text-xs font-medium text-[#142424]" key={key}>{key}: {value}</span>
          ))}
        </div>
      ) : (
        <p className="text-sm text-[#142424]/50 italic py-4">暂无数据</p>
      )}
    </div>
  );
}

function percent(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function latestCompletedDisclosure(runs: DisclosureRun[]): DisclosureRun | null {
  return runs.find((run) => run.status === "completed" && run.package) ?? null;
}

function ExpertToolChooser({
  activeToolId,
  onSelect,
}: {
  activeToolId: ExpertToolId;
  onSelect: (id: ExpertToolId) => void;
}) {
  return (
    <section className="panel wide expert-tool-panel">
      <h3>专家工具</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {expertToolGroups.map((group) => (
          <div className="flex flex-col gap-3" key={group.id}>
            <p>{group.label}</p>
            <div className="flex flex-col gap-2">
              {group.tools.map((tool) => {
                const Icon = tool.icon;
                return (
                  <button
                    className={activeToolId === tool.id ? "flex items-center gap-3 px-4 py-3 rounded-xl bg-[#267a78]/10 border border-[#267a78]/30 text-[#267a78] font-semibold shadow-sm" : "flex items-center gap-3 px-4 py-3 rounded-xl bg-white/50 border border-white/60 text-sm font-medium hover:bg-white/80 transition-colors"}
                    key={tool.id}
                    onClick={() => onSelect(tool.id)}
                    type="button"
                    title={tool.description}
                  >
                    <Icon size={17} />
                    <span>{tool.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

type MoatForm = {
  title: string;
  technical_problem: string;
  innovation: string;
  technical_solution: string;
  feasibility_basis: string;
  evidence_status: EvidenceStatus;
};

const defaultMoatScores = {
  scope_width: 0.6,
  designaround_difficulty: 0.6,
  feasibility: 0.5,
  support_strength: 0.2,
  prior_art_distance: 0.4,
  strategic_value: 0.7,
};

function MoatView({
  project,
  points,
  busy,
  onCreate,
  onSelect,
  onDelete,
}: {
  project: ProjectRecord | null;
  points: PatentPointCandidate[];
  busy: string;
  onCreate: (payload: PatentPointCreatePayload) => Promise<boolean>;
  onSelect: (point: PatentPointCandidate) => Promise<void>;
  onDelete: (point: PatentPointCandidate) => Promise<void>;
}) {
  const [form, setForm] = useState<MoatForm>({
    title: "",
    technical_problem: "",
    innovation: "",
    technical_solution: "",
    feasibility_basis: "",
    evidence_status: "feasible_unverified",
  });
  const canSubmit = Boolean(
    project
      && form.title.trim()
      && form.technical_problem.trim()
      && form.innovation.trim()
      && form.technical_solution.trim(),
  );

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    const succeeded = await onCreate({
      title: form.title.trim(),
      technical_problem: form.technical_problem.trim(),
      innovation: form.innovation.trim(),
      technical_solution: form.technical_solution.trim(),
      beneficial_effects: [],
      protection_focus: ["方法", "系统", "介质"],
      evidence_status: form.evidence_status,
      source_type: "user",
      feasibility_basis: form.feasibility_basis.trim(),
      support_gaps: form.feasibility_basis.trim() ? [] : ["需补充可行性依据或实验记录"],
      experiment_needed: form.evidence_status === "needs_experiment" ? ["补充对比实验或工程验证记录"] : [],
      moat_scores: defaultMoatScores,
      selected: true,
      rationale: "用户指定的护城河专利点",
    });
    if (!succeeded) return;
    setForm({
      title: "",
      technical_problem: "",
      innovation: "",
      technical_solution: "",
      feasibility_basis: "",
      evidence_status: "feasible_unverified",
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>{project ? `${project.name} / 护城河专利点` : "护城河专利点"}</h3>
          <p>{project ? "把用户明确指定的可保护技术点登记成后续交底书、会审和撰写的输入。" : "先创建项目后再登记专利点。"}</p>
        </div>
        <ShieldCheck size={22} />
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>新增专利点</h3>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <label>
              <span>名称 / Title</span>
              <input
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>技术问题</span>
              <textarea
                className="w-full rounded-xl border border-white/60 bg-white/50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#267a78]/40 min-h-[80px]"
                value={form.technical_problem}
                onChange={(event) => setForm((current) => ({ ...current, technical_problem: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>创新点</span>
              <textarea
                className="w-full rounded-xl border border-white/60 bg-white/50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#267a78]/40 min-h-[80px]"
                value={form.innovation}
                onChange={(event) => setForm((current) => ({ ...current, innovation: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>技术方案</span>
              <textarea
                className="w-full rounded-xl border border-white/60 bg-white/50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#267a78]/40 min-h-[80px]"
                value={form.technical_solution}
                onChange={(event) => setForm((current) => ({ ...current, technical_solution: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>可行性依据</span>
              <textarea
                className="w-full rounded-xl border border-white/60 bg-white/50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#267a78]/40 min-h-[80px]"
                value={form.feasibility_basis}
                onChange={(event) => setForm((current) => ({ ...current, feasibility_basis: event.target.value }))}
                disabled={!project}
              />
            </label>
            <label>
              <span>证据状态</span>
              <select
                value={form.evidence_status}
                onChange={(event) => setForm((current) => ({ ...current, evidence_status: event.target.value as EvidenceStatus }))}
                disabled={!project}
              >
                <option value="feasible_unverified">可行未验证</option>
                <option value="verified">已验证</option>
                <option value="needs_experiment">需实验</option>
                <option value="model_generated">模型生成</option>
              </select>
            </label>
            <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!canSubmit || busy === "patent-point-create"} type="submit">
              <ShieldCheck size={17} />
              <span>加入护城河</span>
            </button>
          </form>
        </div>

        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>专利点列表</h3>
          <div className="flex flex-col gap-3">
            {points.map((point) => {
              const total = moatScoreTotal(point.moat_scores);
              return (
                <article className={point.selected ? "flex flex-col gap-2 p-4 bg-[#267a78]/5 border border-[#267a78]/30 rounded-2xl shadow-sm ring-1 ring-[#267a78]/20" : "flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm"} key={point.id}>
                  <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                    <span className="px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]">{evidenceStatusLabel(point.evidence_status)}</span>
                    <span className="px-2.5 py-0.5 rounded-md bg-white/40 border border-white/50 text-[#142424]/60">{sourceTypeLabel(point.source_type)}</span>
                    <span>{Math.round(total * 100)} 分</span>
                  </div>
                  <p><strong>{point.title}</strong></p>
                  <p>{point.innovation || point.technical_solution}</p>
                  <p className={point.support_gaps.length > 0 ? "text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2" : "text-sm text-[#142424]/50 italic py-4"}>
                    {point.support_gaps.length > 0 ? `支撑缺口：${point.support_gaps.join("；")}` : "支撑材料暂未标记缺口。"}
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <StatusPill label="范围" value={percent(point.moat_scores.scope_width)} />
                    <StatusPill label="绕开难度" value={percent(point.moat_scores.designaround_difficulty)} />
                    <StatusPill label="可行性" value={percent(point.moat_scores.feasibility)} />
                    <StatusPill label="支撑" value={percent(point.moat_scores.support_strength)} />
                    <StatusPill label="现有技术距离" value={percent(point.moat_scores.prior_art_distance)} />
                    <StatusPill label="战略价值" value={percent(point.moat_scores.strategic_value)} />
                  </div>
                  {point.claim_chart.length > 0 && (
                    <div className="flex flex-col gap-2 mt-2 p-3 bg-white/50 rounded-xl text-sm border border-white/50">
                      {point.claim_chart.slice(0, 2).map((item) => (
                        <p key={item.prior_art_id}>
                          <strong>{item.prior_art_title}</strong>：{item.claim_drafting_advice}
                        </p>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-3">
                    <button
                      className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors"
                      disabled={!project || busy === "patent-point-select" || point.selected}
                      onClick={() => void onSelect(point)}
                      type="button"
                      title="设为选中"
                    >
                      <ShieldCheck size={17} />
                      <span>{point.selected ? "已选中" : "选中"}</span>
                    </button>
                    <button
                      className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors"
                      disabled={!project || busy === "patent-point-delete"}
                      onClick={() => void onDelete(point)}
                      type="button"
                      title="删除"
                    >
                      <Trash2 size={17} />
                      <span>删除</span>
                    </button>
                  </div>
                </article>
              );
            })}
            {points.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无用户指定专利点。</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

function DeliberationView({
  project,
  doctor,
  runs,
  disclosure,
  selectedProviders,
  busy,
  onStart,
  onToggleProvider,
  onRefresh,
}: {
  project: ProjectRecord | null;
  doctor: AgentDoctorReport | null;
  runs: DeliberationRun[];
  disclosure: DisclosureRun | null;
  selectedProviders: string[];
  busy: string;
  onStart: (trace?: boolean) => void;
  onToggleProvider: (providerId: string, enabled: boolean) => void;
  onRefresh: () => void;
}) {
  const latest = runs[0] ?? null;
  const completed = latestCompletedDeliberation(runs);
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>多 Agent 会审</h3>
          <p>
            {project
              ? "会审会调用本机 Codex、Gemini、Claude，先讨论保护范围和写作策略，再注入生成流程。"
              : "先创建项目后再启动会审。"}
          </p>
          <p>{disclosure ? `将默认注入交底书 run：${disclosure.id}` : "暂无已完成交底书，会审仅使用 draft 与 RAG 片段。"}</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={onRefresh} type="button" title="刷新会审">
            <RefreshCw size={17} />
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
            disabled={!project || busy === "deliberate"}
            onClick={() => onStart(false)}
            type="button"
          >
            <UsersRound size={18} />
            <span>启动会审</span>
          </button>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>Provider Doctor</h3>
          <div className="doctor-grid">
            <StatusPill label="状态" value={doctor?.status ?? "unknown"} />
            <StatusPill label="运行级别" value={doctor?.run_mode ?? "unknown"} />
          </div>
          <AgentProviderCards
            doctor={doctor}
            role="deliberation"
            selectedProviders={selectedProviders}
            disabled={busy === "deliberate"}
            onToggleProvider={onToggleProvider}
          />
        </div>

        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>会审记录</h3>
          <div className="flex flex-col gap-3">
            {runs.map((run) => (
              <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={run.id}>
                <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                  <span>{run.status}</span>
                  <span>{run.run_mode}</span>
                </div>
                <p>{run.providers.join(" / ")}</p>
                <p>{run.events.at(-1) ?? "暂无事件"}</p>
                <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                  <span>{run.stage_results.length} 阶段</span>
                  <span>{run.failures.length} 失败</span>
                  <span>{run.logs.length} 日志</span>
                </div>
                {run.failures.length > 0 && (
                  <div className="flex flex-col gap-2">
                    {run.failures.map((failure) => (
                      <article className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-2xl" key={`${run.id}-${failure.phase}-${failure.provider_id}`}>
                        <span>{failure.phase}</span>
                        <div>
                          <strong>{failure.provider_id} / {failure.reason}</strong>
                          <p>{failure.message}</p>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
                {run.logs.length > 0 && (
                  <div className="flex flex-col gap-2 font-mono text-xs mt-3 bg-white/40 p-4 rounded-xl border border-white/50">
                    {run.logs.slice(-6).map((log, index) => (
                      <article className={`log-row ${log.level}`} key={`${run.id}-log-${index}`}>
                        <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                          <span>{log.level}</span>
                          <span>{log.phase || "phase"}</span>
                          <span>{log.provider_id || "system"}</span>
                          {log.attempt != null && <span>attempt {log.attempt}</span>}
                        </div>
                        <p>{log.message}</p>
                        {log.detail && <p>{log.detail}</p>}
                        {log.repair_suggestion && <p><strong>修复建议：</strong>{log.repair_suggestion}</p>}
                      </article>
                    ))}
                  </div>
                )}
              </article>
            ))}
            {runs.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无会审记录</p>}
          </div>
        </div>
      </section>

      <StrategyBriefView
        title={completed ? "可注入策略 Brief" : latest ? "最近会审尚未完成" : "策略 Brief"}
        strategy={completed?.strategy_brief ?? null}
      />
    </div>
  );
}

function DisclosureView({
  project,
  materials,
  runs,
  busy,
  onUpload,
  onStart,
  onRefresh,
}: {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  runs: DisclosureRun[];
  busy: string;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
  onStart: (trace?: boolean) => void;
  onRefresh: () => void;
}) {
  const latest = runs[0] ?? null;
  const completed = latestCompletedDisclosure(runs);
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>前置材料生成</h3>
          <p>
            {project
              ? "从 draft 和补充材料挖掘专利点，检索公开现有技术，并生成可交给代理人的技术交底书。"
              : "先创建项目后再上传材料。"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={onRefresh} type="button" title="刷新前置材料">
            <RefreshCw size={17} />
          </button>
          <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project || busy === "disclosure"} onClick={() => onStart(false)} type="button">
            <ClipboardList size={18} />
            <span>生成交底书</span>
          </button>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>补充材料</h3>
          <form className="flex flex-col gap-4 p-4 border-2 border-dashed border-white/60 rounded-2xl bg-white/30" onSubmit={onUpload}>
            <input
              id="project-material-file"
              name="project-material-file"
              type="file"
              accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
              disabled={!project}
            />
            <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project || busy === "material-upload"} type="submit">
              <Upload size={17} />
              <span>上传材料</span>
            </button>
          </form>
          <div className="flex flex-col gap-3">
            {materials.map((material) => (
              <article className="flex gap-3 items-start p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={material.id}>
                {material.status === "processed" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                <div>
                  <strong>{material.file_name}</strong>
                  <span>{material.status === "processed" ? `${material.file_type} / ${material.text.length} 字` : material.warnings.join("；")}</span>
                </div>
              </article>
            ))}
            {materials.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">未上传补充材料时，系统会仅基于 draft 生成。</p>}
          </div>
        </div>

        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>生成记录</h3>
          <div className="flex flex-col gap-3">
            {runs.map((run) => (
              <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={run.id}>
                <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                  <span>{run.status}</span>
                  <span>{run.package?.prior_art_hits.length ?? 0} 条现有技术</span>
                </div>
                <p>{run.package?.title ?? run.events.at(-1) ?? "等待生成"}</p>
                <p>{run.events.at(-1) ?? "暂无事件"}</p>
              </article>
            ))}
            {runs.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无交底书生成记录。</p>}
          </div>
        </div>
      </section>

      <DisclosurePreview project={project} run={completed ?? latest} />
    </div>
  );
}

function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 p-3 bg-white/50 border border-white/60 rounded-xl text-sm">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ProjectSelect({
  projects,
  selectedProjectId,
  onChange,
}: {
  projects: ProjectRecord[];
  selectedProjectId: string;
  onChange: (id: string) => void;
}) {
  return (
    <label className="flex flex-col md:flex-row items-start md:items-center gap-3">
      <span>当前项目</span>
      <select value={selectedProjectId} onChange={(event) => onChange(event.target.value)}>
        <option value="">{projects.length === 0 ? "暂无项目" : "新建项目"}</option>
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>
    </label>
  );
}

type ProjectMetadata = {
  created_at?: string;
  updated_at?: string;
};

function ProjectsOverview({
  projects,
  selectedProjectId,
  onSelect,
  onDelete,
  busy,
}: {
  projects: ProjectRecord[];
  selectedProjectId: string;
  onSelect: (id: string) => void;
  onDelete: (project: ProjectRecord) => void;
  busy: string;
}) {
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl col-span-full">
      <h3>项目</h3>
      <p className="section-copy">选择历史项目后，可以继续生成、质检或导出。</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project) => {
          const metadata = project as ProjectRecord & ProjectMetadata;
          const isSelected = project.id === selectedProjectId;
          return (
            <article className={isSelected ? "flex flex-col gap-4 p-5 bg-white/90 border border-[#267a78]/30 rounded-3xl shadow-[0_8px_30px_rgba(38,122,120,0.12)] ring-1 ring-[#267a78]/20" : "flex flex-col gap-4 p-5 bg-white/50 border border-white/60 rounded-3xl shadow-sm hover:shadow-md transition-shadow"} key={project.id}>
              <div>
                <strong>{project.name}</strong>
                <span>{project.package ? "已有初稿" : "仅有想法"}</span>
              </div>
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt>创建</dt>
                  <dd>{formatProjectDate(metadata.created_at)}</dd>
                </div>
                <div>
                  <dt>更新</dt>
                  <dd>{formatProjectDate(metadata.updated_at)}</dd>
                </div>
              </dl>
              <div className="flex items-center gap-3 mt-4 pt-4 border-t border-white/50">
                <button
                  className={isSelected ? "inline-flex items-center justify-center px-4 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-medium shadow-sm border border-emerald-200 disabled:opacity-50" : "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"}
                  disabled={isSelected}
                  onClick={() => onSelect(project.id)}
                  type="button"
                >
                  {isSelected ? "当前项目" : "选择项目"}
                </button>
                <button
                  className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-red-500 hover:text-white text-red-500 shadow-sm border border-white/50 disabled:opacity-50 transition-colors"
                  disabled={busy === "project-delete"}
                  onClick={() => onDelete(project)}
                  type="button"
                  title="删除项目"
                >
                  <Trash2 size={17} />
                  <span>删除项目</span>
                </button>
              </div>
            </article>
          );
        })}
        {projects.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无项目。进入“专利生成”输入想法即可创建。</p>}
      </div>
    </section>
  );
}

function formatProjectDate(value: string | undefined): string {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function CorpusView({
  documents,
  searchText,
  searchSection,
  searchResults,
  busy,
  onImport,
  onSearch,
  onSearchText,
  onSearchSection,
}: {
  documents: PatentDocument[];
  searchText: string;
  searchSection: SectionType | "";
  searchResults: SearchResult[];
  busy: string;
  onImport: (event: FormEvent<HTMLFormElement>) => void;
  onSearch: (event: FormEvent) => void;
  onSearchText: (value: string) => void;
  onSearchSection: (value: SectionType | "") => void;
}) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <h3>语料导入</h3>
        <form className="flex flex-col gap-4" onSubmit={onImport}>
          <input id="patent-file" name="patent-file" type="file" accept=".pdf,.docx,.txt,.md,.markdown" />
          <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "import"} type="submit" title="导入专利文件">
            <Upload size={17} />
            <span>导入</span>
          </button>
        </form>
        <div className="flex flex-col gap-3">
          {documents.map((document) => (
            <article className="flex gap-3 items-start p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={document.id}>
              <FileText size={18} />
              <div>
                <strong>{document.title}</strong>
                <span>{document.source_name}</span>
              </div>
            </article>
          ))}
          {documents.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无语料</p>}
        </div>
      </section>

      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <h3>片段检索</h3>
        <form className="flex items-center gap-3" onSubmit={onSearch}>
          <input value={searchText} onChange={(event) => onSearchText(event.target.value)} />
          <select value={searchSection} onChange={(event) => onSearchSection(event.target.value as SectionType | "")}>
            {sectionOptions.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" disabled={busy === "search"} type="submit" title="检索">
            <Search size={17} />
          </button>
        </form>
        <div className="results">
          {searchResults.map((result) => (
            <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={result.chunk.id}>
              <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                <span>{result.chunk.section_type}</span>
                <span>{result.score.toFixed(3)}</span>
              </div>
              <p>{result.chunk.text}</p>
            </article>
          ))}
          {searchResults.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无检索结果</p>}
        </div>
      </section>
    </div>
  );
}

function CreateProjectView({
  projectName,
  draftText,
  busy,
  onProjectName,
  onDraftText,
  onSubmit,
}: {
  projectName: string;
  draftText: string;
  busy: string;
  onProjectName: (value: string) => void;
  onDraftText: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl col-span-full">
      <h3>技术交底</h3>
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <label>
          <span>项目名称</span>
          <input value={projectName} onChange={(event) => onProjectName(event.target.value)} />
        </label>
        <label>
          <span>Draft</span>
          <textarea
            className="w-full rounded-2xl border border-white/60 bg-white/50 px-5 py-4 focus:outline-none focus:ring-2 focus:ring-[#267a78]/40 min-h-[200px]"
            value={draftText}
            onChange={(event) => onDraftText(event.target.value)}
          />
        </label>
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "create"} type="submit" title="创建项目">
          <FileText size={17} />
          <span>创建</span>
        </button>
      </form>
    </section>
  );
}

function WriteView({
  project,
  deliberation,
  disclosure,
  formulaRequirement,
  formulaRun,
  busy,
  onGenerate,
}: {
  project: ProjectRecord | null;
  deliberation: DeliberationRun | null;
  disclosure: DisclosureRun | null;
  formulaRequirement: FormulaNeedAssessment | null;
  formulaRun: FormulaRun | null;
  busy: string;
  onGenerate: () => void;
}) {
  const formulaReady = !formulaRequirement?.required || Boolean(formulaRun?.package);
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>{project?.name ?? "未选择项目"}</h3>
          <p>{project?.draft_text ?? "先创建项目后再生成申请文本。"}</p>
          <p>
            {deliberation
              ? `将注入会审 run：${deliberation.id}`
              : "未完成多 Agent 会审，仍可直接生成。"}
          </p>
          <p>{disclosure ? `将注入前置交底书 run：${disclosure.id}` : "未完成前置交底书，仍可直接生成。"}</p>
          <p>{formulaRun ? `将注入核心公式 run：${formulaRun.id}` : formulaRequirement?.required ? "核心公式包未完成，暂不能生成。" : "无需核心公式包。"}</p>
        </div>
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project || !deliberation || !formulaReady || busy === "generate"} onClick={onGenerate} type="button">
          <Wand2 size={18} />
          <span>生成</span>
        </button>
      </section>
      <StrategyBriefView title="当前会审策略" strategy={deliberation?.strategy_brief ?? project?.package?.strategy_brief ?? null} />
      <DisclosureSummaryView packageValue={disclosure?.package ?? null} />
      <PackagePreview packageValue={project?.package ?? null} />
    </div>
  );
}

function DisclosurePreview({
  project,
  run,
}: {
  project: ProjectRecord | null;
  run: DisclosureRun | null;
}) {
  const packageValue = run?.package ?? null;
  if (!run) {
    return <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl"><p className="text-sm text-[#142424]/50 italic py-4">暂无前置材料结果。</p></section>;
  }
  if (!packageValue) {
    return (
      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <h3>{run.status === "completed" ? "交底书" : "生成中"}</h3>
        <p className="text-sm text-[#142424]/50 italic py-4">{run.events.at(-1) ?? "等待后台任务更新。"}</p>
      </section>
    );
  }
  const selected = packageValue.candidates.find((candidate) => candidate.id === packageValue.selected_candidate_id)
    ?? packageValue.candidates[0]
    ?? null;
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>{packageValue.title}</h3>
          <p>{packageValue.summary}</p>
        </div>
        <div className="flex items-center gap-3">
          {project && (
            <>
              <a className="inline-flex items-center gap-2 text-sm text-[#267a78] hover:underline font-medium" href={disclosureExportUrl(project.id, run.id, "docx")}>
                <Download size={17} />
                <span>DOCX</span>
              </a>
              <a className="inline-flex items-center gap-2 text-sm text-[#267a78] hover:underline font-medium" href={disclosureExportUrl(project.id, run.id, "md")}>
                <Download size={17} />
                <span>MD</span>
              </a>
            </>
          )}
        </div>
      </section>

      <section className="flex flex-col gap-6">
        {selected && <PreviewBlock title="推荐专利点" text={`${selected.title}\n${selected.innovation}\n${selected.rationale}`} />}
        <PreviewBlock title="公开现有技术差异" text={packageValue.prior_art_differences} />
        <PreviewBlock
          title="公开现有技术"
          text={packageValue.prior_art_hits.map((hit) => `${hit.source} ${hit.title}\n${hit.url}\n${hit.relevance_summary}`).join("\n\n") || "暂无。"}
        />
        <PreviewBlock
          title="自检结果"
          text={packageValue.self_check_findings.map((finding) => `[${finding.severity}] ${finding.category}: ${finding.message}`).join("\n") || "暂无。"}
        />
        <PreviewBlock title="技术交底书" text={packageValue.body_markdown} />
        <PreviewBlock title="Mermaid" text={packageValue.mermaid} />
      </section>
    </div>
  );
}

function DisclosureSummaryView({ packageValue }: { packageValue: DisclosurePackage | null }) {
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <h3>当前前置交底书</h3>
      {packageValue ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <PreviewBlock title="摘要" text={packageValue.summary} />
          <PreviewBlock
            title="推荐专利点"
            text={(packageValue.candidates.find((candidate) => candidate.id === packageValue.selected_candidate_id) ?? packageValue.candidates[0])?.title ?? "暂无"}
          />
          <PreviewBlock title="现有技术差异" text={packageValue.prior_art_differences} />
        </div>
      ) : (
        <p className="text-sm text-[#142424]/50 italic py-4">暂无已完成前置交底书。</p>
      )}
    </section>
  );
}

function FilingReadinessView({
  project,
  report,
  reports,
  postDraftReview,
  officialCompileRun,
  currentDraftHash,
  currentSourceDraftHash,
  busy,
  onRun,
}: {
  project: ProjectRecord | null;
  report: FilingReadinessReport | null;
  reports: FilingReadinessReport[];
  postDraftReview: PostDraftReviewRun | null;
  officialCompileRun: OfficialCompileRun | null;
  currentDraftHash: string;
  currentSourceDraftHash: string;
  busy: string;
  onRun: () => void;
}) {
  const canExport = Boolean(project?.package);
  const officialAllowed = Boolean(
    canExport
      && postDraftReview?.status === "completed"
      && postDraftReview.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.draft_package_hash === currentSourceDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id
      && postDraftReview.official_package_hash === officialCompileRun?.official_package_hash,
  );
  const reportStatusClass = report?.status === "high_risk" ? "danger" : report?.status === "warning" ? "warn" : "";
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>提交成熟度</h3>
          <p>{project?.package ? "检查官方提交导出、内部策略稿和申请文本中的占位符、敏感表述与高风险命中项。" : "生成申请文本后可运行提交成熟度检查。"}</p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
          disabled={!project?.package || busy === "filing-readiness"}
          onClick={onRun}
          type="button"
        >
          <ClipboardList size={18} />
          <span>运行检查</span>
        </button>
      </section>

      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <h3>导出</h3>
        {project && canExport ? (
          <div className="flex flex-col gap-4">
            {report?.status === "high_risk" && (
              <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">高风险：请结合成稿会审报告处理命中项。</p>
            )}
            {!officialAllowed && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">正式稿入口已锁定：需先完成正式稿编译，并通过匹配 official hash 的成稿会审。</p>}
            {officialCompileRun?.official_package_hash && (
              <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">当前 official hash：{officialCompileRun.official_package_hash.slice(0, 12)}</p>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <a
                aria-disabled={!officialAllowed}
                className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/40 border border-white/50 text-[#142424]/40 font-medium cursor-not-allowed"}
                href={officialAllowed ? officialExportUrl(project.id, "docx") : undefined}
              >
                <Download size={18} />
                <span>官方 DOCX</span>
              </a>
              <a
                aria-disabled={!officialAllowed}
                className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/40 border border-white/50 text-[#142424]/40 font-medium cursor-not-allowed"}
                href={officialAllowed ? officialExportUrl(project.id, "md") : undefined}
              >
                <Download size={18} />
                <span>官方 MD</span>
              </a>
              <a className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" href={exportUrl(project.id, "md")}>
                <Download size={18} />
                <span>内部策略稿</span>
              </a>
              {report && (
                <a className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" href={filingReadinessReportUrl(project.id, report.id)}>
                  <Download size={18} />
                  <span>检查报告</span>
                </a>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-[#142424]/50 italic py-4">暂无可导出的申请文本。</p>
        )}
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>历史检查</h3>
          <div className="flex flex-col gap-3">
            {reports.map((item) => (
              <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={item.id}>
                <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                  <span className={`px-2.5 py-0.5 rounded-md border ${ item.status === "high_risk" ? "bg-red-100 border-red-200 text-red-700" : item.status === "warning" ? "bg-amber-100 border-amber-200 text-amber-700" : "bg-emerald-100 border-emerald-200 text-emerald-700" }`}>
                    {readinessStatusLabel(item.status)}
                  </span>
                  <span>{item.issues.length} 项命中</span>
                </div>
                <p>{item.created_at}</p>
                <p>{item.rules_version}</p>
              </article>
            ))}
            {reports.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无提交成熟度检查记录。</p>}
          </div>
        </div>

        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>命中项</h3>
          {report && (
            <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
              <span className={`px-2.5 py-0.5 rounded-md border ${ reportStatusClass === "danger" ? "bg-red-100 border-red-200 text-red-700" : reportStatusClass === "warn" ? "bg-amber-100 border-amber-200 text-amber-700" : "bg-white/80 border-white text-[#142424]" }`}>{readinessStatusLabel(report.status)}</span>
              <span>{report.issues.length} 项</span>
            </div>
          )}
          <div className="flex flex-col gap-3">
            {report?.issues.map((issue, index) => (
              <article className={`flex items-start gap-3 p-4 border rounded-2xl ${ issue.severity === "high" ? "bg-red-50 border-red-100" : issue.severity === "medium" ? "bg-amber-50 border-amber-100" : "bg-blue-50 border-blue-100" }`} key={`${issue.category}-${issue.target}-${index}`}>
                <span>{severityLabel(issue.severity)}</span>
                <div>
                  <strong>{issue.category} / {issue.target}</strong>
                  <p>{issue.matched_text || "未记录匹配文本"}</p>
                  <p>{issue.message}</p>
                  <p>{issue.suggestion}</p>
                </div>
              </article>
            ))}
            {!report && <p className="text-sm text-[#142424]/50 italic py-4">运行检查后显示命中项。</p>}
            {report && report.issues.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">最新报告没有命中项。</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

function ClaimDefenseView({
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
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>权利要求防线</h3>
          <p>{project ? "从当前草稿、交底书和已生成文本提取特征记录，标记区别特征、支撑缺口与从属兜底建议。" : "先创建项目后再生成防线工作表。"}</p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
          disabled={!project || busy === "claim-defense"}
          onClick={onGenerate}
          type="button"
        >
          <ShieldCheck size={18} />
          <span>生成工作表</span>
        </button>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>防线建议</h3>
          <div className="flex flex-col gap-3">
            {worksheet?.defense_recommendations.map((item, index) => (
              <article className="flex gap-3 items-start p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={`${item}-${index}`}>
                <ShieldCheck size={18} />
                <div>
                  <strong>建议 {index + 1}</strong>
                  <span>{item}</span>
                </div>
              </article>
            ))}
            {!worksheet && <p className="text-sm text-[#142424]/50 italic py-4">生成工作表后显示防线建议。</p>}
            {worksheet && worksheet.defense_recommendations.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无防线建议。</p>}
          </div>
        </div>

        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>历史版本</h3>
          <div className="flex flex-col gap-3">
            {worksheets.map((item) => (
              <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={item.id}>
                <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                  <span className="px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]">{item.status}</span>
                  <span>{item.source}</span>
                  <span>{item.feature_records.length} 个特征</span>
                </div>
                <p>{item.created_at}</p>
              </article>
            ))}
            {worksheets.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无工作表历史版本。</p>}
          </div>
        </div>
      </section>

      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <h3>特征记录</h3>
        <div className="flex flex-col gap-3">
          {worksheet?.feature_records.map((record) => (
            <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={record.feature_id}>
              <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                <span className="px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]">{featureClassificationLabel(record.classification)}</span>
                <span>{record.claim_refs.length > 0 ? record.claim_refs.join(" / ") : "未映射权利要求"}</span>
              </div>
              <p><strong>{record.text}</strong></p>
              <p>{record.risk_tags.length > 0 ? `风险标签：${record.risk_tags.join("；")}` : "暂无风险标签"}</p>
            </article>
          ))}
          {!worksheet && <p className="text-sm text-[#142424]/50 italic py-4">生成工作表后显示特征记录。</p>}
          {worksheet && worksheet.feature_records.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无特征记录。</p>}
        </div>
      </section>

      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <h3>支撑缺口</h3>
        <div className="flex flex-col gap-3">
          {worksheet?.support_gaps.map((gap, index) => (
            <article className="flex gap-3 items-start p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={`${gap}-${index}`}>
              <AlertTriangle size={18} />
              <div>
                <strong>缺口 {index + 1}</strong>
                <span>{gap}</span>
              </div>
            </article>
          ))}
          {!worksheet && <p className="text-sm text-[#142424]/50 italic py-4">生成工作表后显示支撑缺口。</p>}
          {worksheet && worksheet.support_gaps.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无支撑缺口。</p>}
        </div>
      </section>
    </div>
  );
}

function ReviewView({
  project,
  busy,
  onReview,
}: {
  project: ProjectRecord | null;
  busy: string;
  onReview: () => void;
}) {
  const findings = project?.package?.review_findings ?? [];
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>审查意见</h3>
          <p>{project?.package ? project.name : "生成申请文本后可审查。"}</p>
        </div>
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project?.package || busy === "review"} onClick={onReview} type="button">
          <Search size={18} />
          <span>审查</span>
        </button>
      </section>
      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex flex-col gap-3">
          {findings.map((finding, index) => (
            <article className={`flex items-start gap-3 p-4 border rounded-2xl ${ finding.severity === "high" ? "bg-red-50 border-red-100" : finding.severity === "medium" ? "bg-amber-50 border-amber-100" : "bg-blue-50 border-blue-100" }`} key={`${finding.category}-${index}`}>
              <span>{severityLabel(finding.severity)}</span>
              <div>
                <strong>{finding.category}</strong>
                <p>{finding.message}</p>
                <p>{finding.suggestion}</p>
              </div>
            </article>
          ))}
          {findings.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无审查意见</p>}
        </div>
      </section>
    </div>
  );
}

function DraftCompletionView({
  project,
  run,
  runs,
  busy,
  onRun,
  onImprove,
  onPatch,
}: {
  project: ProjectRecord | null;
  run: DraftCompletionRun | null;
  runs: DraftCompletionRun[];
  busy: string;
  onRun: () => void;
  onImprove: () => void;
  onPatch: (runId: string, patchId: string, action: "accept" | "reject") => void;
}) {
  const scoreItems: Array<[string, number]> = run
    ? [
        ["授权稳定性", run.scorecard.authorization_stability],
        ["保护范围", run.scorecard.protection_scope],
        ["支撑强度", run.scorecard.support_strength],
        ["现有技术区分", run.scorecard.prior_art_distinction],
        ["提交成熟度", run.scorecard.filing_maturity],
        ["官方洁净度", run.scorecard.official_hygiene],
        ["整体评分", run.scorecard.overall],
      ]
    : [];
  const priorityIssues = run?.issues.filter((issue) => issue.blocks_submission || issue.severity === "high") ?? [];
  const displayedIssues = priorityIssues.length > 0 ? priorityIssues : run?.issues.slice(0, 5) ?? [];
  const patchBusy = busy === "completion" || busy.startsWith("completion-");

  function taskStatusLabel(status: string): string {
    if (status === "open") return "待处理";
    if (status === "proposed") return "已提议";
    if (status === "accepted") return "已接受";
    if (status === "rejected") return "已拒绝";
    return "已替换";
  }

  function patchStatusClass(status: string): string {
    if (status === "accepted") return "";
    if (status === "rejected" || status === "superseded") return "muted";
    return "warn";
  }

  function completionStatusLabel(status: string): string {
    if (status === "supported") return "已支撑";
    if (status === "partial") return "部分支撑";
    return "缺支撑";
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>Draft Completion Harness / 初稿完善循环</h3>
          <p>
            Warning mode：发现缺口、生成任务和候选补丁，但不把风险判断包装成已验证事实；补丁需人工接受后才进入完善结果。
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
            disabled={!project?.package || Boolean(busy)}
            onClick={onRun}
            type="button"
          >
            <Gauge size={18} />
            <span>运行完善</span>
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
            disabled={!project?.package || Boolean(busy)}
            onClick={onImprove}
            type="button"
          >
            <Wand2 size={18} />
            <span>一键提升分数</span>
          </button>
        </div>
      </section>

      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
          <h3>评分</h3>
          {run && (
            <>
              <span className="px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]">{run.status}</span>
              <span>{run.created_at}</span>
              <span>{runs.length} 次运行</span>
            </>
          )}
        </div>
        {run ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {scoreItems.map(([label, value]) => (
              <article className="flex flex-col gap-2 p-4 bg-white/60 border border-white/70 rounded-2xl" key={label}>
                <span>{label}</span>
                <strong>{value}/100</strong>
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[#142424]/50 italic py-4">生成申请文本后可运行初稿完善循环。</p>
        )}
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>高优先级问题</h3>
          <div className="flex flex-col gap-3">
            {displayedIssues.map((issue) => (
              <article className={`flex items-start gap-3 p-4 border rounded-2xl ${ issue.severity === "high" ? "bg-red-50 border-red-100" : issue.severity === "medium" ? "bg-amber-50 border-amber-100" : "bg-blue-50 border-blue-100" }`} key={issue.id}>
                <span>{severityLabel(issue.severity)}</span>
                <div>
                  <strong>
                    {completionCategoryLabel(issue.category)} / {completionTargetLabel(issue.target)}
                  </strong>
                  <p>{issue.message}</p>
                  <p>{issue.why_it_matters}</p>
                  <p>{issue.suggested_action}</p>
                </div>
              </article>
            ))}
            {!run && <p className="text-sm text-[#142424]/50 italic py-4">运行后显示高优先级缺口。</p>}
            {run && displayedIssues.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无高优先级问题。</p>}
          </div>
        </div>

        <div className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
          <h3>完善任务</h3>
          <div className="flex flex-col gap-3">
            {run?.tasks.map((task) => (
              <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={task.id}>
                <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                  <span className="px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]">{taskStatusLabel(task.status)}</span>
                  <span>优先级 {task.priority}</span>
                  <span>{task.draft_section_target}</span>
                </div>
                <p><strong>{task.task_type}</strong></p>
                <p>{task.expected_output}</p>
              </article>
            ))}
            {!run && <p className="text-sm text-[#142424]/50 italic py-4">运行后显示待完善任务。</p>}
            {run && run.tasks.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无完善任务。</p>}
          </div>
        </div>
      </section>

      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <h3>Claim Support Matrix</h3>
        {run && run.support_matrix.length > 0 ? (
          <div className="w-full text-sm text-left border-collapse">
            <table>
              <thead>
                <tr>
                  <th>权利要求</th>
                  <th>特征</th>
                  <th>分类</th>
                  <th>支撑状态</th>
                  <th>证据</th>
                  <th>风险</th>
                </tr>
              </thead>
              <tbody>
                {run.support_matrix.map((row, index) => (
                  <tr key={`${row.claim_ref}-${index}`}>
                    <td>{row.claim_ref || "未映射"}</td>
                    <td>{row.feature_text}</td>
                    <td>{featureClassificationLabel(row.feature_classification)}</td>
                    <td>{completionStatusLabel(row.completion_status)}</td>
                    <td>
                      {[
                        ...row.description_refs,
                        ...row.figure_refs,
                        ...row.embodiment_refs,
                        ...row.formula_refs,
                        ...row.data_structure_refs,
                        ...row.pseudo_code_refs,
                        ...row.prior_art_refs,
                      ].join("；") || evidenceStatusLabel(row.evidence_status)}
                    </td>
                    <td>{row.risk_tags.join("；") || "暂无"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-[#142424]/50 italic py-4">{run ? "暂无支撑矩阵。" : "运行后显示权利要求支撑矩阵。"}</p>
        )}
      </section>

      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
          <h3>候选补丁</h3>
          {project && run && (
            <a className="inline-flex items-center gap-2 text-sm text-[#267a78] hover:underline font-medium" href={draftCompletionReportUrl(project.id, run.id)}>
              <Download size={17} />
              <span>报告 MD</span>
            </a>
          )}
        </div>
        <div className="flex flex-col gap-3">
          {run?.patches.map((patch) => (
            <article className="flex flex-col gap-2 p-4 bg-white/40 border border-white/40 rounded-2xl shadow-sm" key={patch.id}>
              <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
                <span className={`px-2.5 py-0.5 rounded-md border ${ patchStatusClass(patch.status) === "danger" ? "bg-red-100 border-red-200 text-red-700" : patchStatusClass(patch.status) === "warn" ? "bg-amber-100 border-amber-200 text-amber-700" : "bg-white/80 border-white text-[#142424]" }`}>{patch.status}</span>
                <span>{patch.patch_kind}</span>
                <span>{patch.target_section}</span>
                <span>{patch.can_enter_official_draft ? "可进入官方稿" : "仅内部侧车"}</span>
              </div>
              <p><strong>{patch.rationale}</strong></p>
              <p>{patch.risk_delta}</p>
              <pre className="p-4 bg-white/40 rounded-xl border border-white/50 font-mono text-sm whitespace-pre-wrap">{patch.after_text || "无 after_text"}</pre>
              <div className="flex items-center gap-3">
                <button
                  className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
                  disabled={patch.status !== "proposed" || patchBusy}
                  onClick={() => onPatch(run.id, patch.id, "accept")}
                  type="button"
                >
                  接受
                </button>
                <button
                  className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors"
                  disabled={patch.status !== "proposed" || patchBusy}
                  onClick={() => onPatch(run.id, patch.id, "reject")}
                  type="button"
                >
                  拒绝
                </button>
              </div>
            </article>
          ))}
          {!run && <p className="text-sm text-[#142424]/50 italic py-4">运行后显示候选补丁。</p>}
          {run && run.patches.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">暂无候选补丁。</p>}
        </div>
      </section>
    </div>
  );
}

function ExportView({
  project,
  packageValue,
  postDraftReview,
  officialCompileRun,
  currentDraftHash,
  currentSourceDraftHash,
}: {
  project: ProjectRecord | null;
  packageValue: DraftPackage | null;
  postDraftReview: PostDraftReviewRun | null;
  officialCompileRun: OfficialCompileRun | null;
  currentDraftHash: string;
  currentSourceDraftHash: string;
}) {
  const enabled = canExportPackage(packageValue);
  const officialAllowed = Boolean(
    enabled
      && postDraftReview?.status === "completed"
      && postDraftReview.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.draft_package_hash === currentSourceDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id
      && postDraftReview.official_package_hash === officialCompileRun?.official_package_hash,
  );
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl col-span-full">
      <h3>导出文件</h3>
      <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">
        {officialAllowed
          ? `正式稿已由成稿会审解锁：${officialCompileRun?.official_package_hash.slice(0, 12)}`
          : "正式稿需完成编译，并通过匹配当前 official hash 的成稿会审；内部稿和报告可继续导出。"}
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/40 border border-white/50 text-[#142424]/40 font-medium cursor-not-allowed"}
          href={officialAllowed && project ? officialExportUrl(project.id, "docx") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/40 border border-white/50 text-[#142424]/40 font-medium cursor-not-allowed"}
          href={officialAllowed && project ? officialExportUrl(project.id, "md") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 MD</span>
        </a>
        {[
          ["docx", "DOCX"],
          ["md", "Markdown"],
          ["mmd", "Mermaid"],
          ["prompt", "绘图提示词"],
        ].map(([kind, label]) => (
          <a
            aria-disabled={!enabled}
            className={enabled ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/40 border border-white/50 text-[#142424]/40 font-medium cursor-not-allowed"}
            href={enabled && project ? exportUrl(project.id, kind as "docx" | "md" | "mmd" | "prompt") : undefined}
            key={kind}
          >
            <Download size={18} />
            <span>{label}</span>
          </a>
        ))}
      </div>
      <PackagePreview packageValue={packageValue} compact />
    </section>
  );
}

function StrategyBriefView({
  title,
  strategy,
}: {
  title: string;
  strategy: PatentStrategyBrief | null;
}) {
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <h3>{title}</h3>
      {strategy ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <PreviewBlock title="摘要" text={strategy.summary} />
          <PreviewBlock title="权利要求策略" text={strategy.claim_strategy.join("\n")} />
          <PreviewBlock title="说明书策略" text={strategy.description_strategy.join("\n")} />
          <PreviewBlock title="风险控制" text={strategy.risk_controls.join("\n")} />
          <PreviewBlock title="Agent 共识" text={strategy.agent_consensus} />
        </div>
      ) : (
        <p className="text-sm text-[#142424]/50 italic py-4">暂无可注入策略</p>
      )}
    </section>
  );
}

function PackagePreview({
  packageValue,
  compact = false,
}: {
  packageValue: DraftPackage | null;
  compact?: boolean;
}) {
  if (!packageValue) {
    return <p className="text-sm text-[#142424]/50 italic py-4">暂无申请文本</p>;
  }
  return (
    <section className={compact ? "flex flex-col gap-4 text-sm" : "flex flex-col gap-6"}>
      <PreviewBlock title="摘要" text={packageValue.abstract} />
      <PreviewBlock title="权利要求书" text={packageValue.claims} />
      {!compact && <PreviewBlock title="说明书" text={packageValue.description} />}
      {!compact && <PreviewBlock title="附图说明" text={packageValue.drawing_description} />}
      <PreviewBlock title="Mermaid流程图" text={packageValue.mermaid} />
      <PreviewBlock title="绘图提示词" text={packageValue.image_prompt} />
      {packageValue.strategy_brief && <PreviewBlock title="多Agent会审策略" text={packageValue.strategy_brief.summary} />}
    </section>
  );
}

function PreviewBlock({ title, text }: { title: string; text: string }) {
  return (
    <article className="p-6 bg-white/80 border border-white rounded-3xl shadow-sm">
      <h4>{title}</h4>
      <pre>{text}</pre>
    </article>
  );
}

export default App;
