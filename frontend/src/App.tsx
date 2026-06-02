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
  Health,
  PatentPointCandidate,
  PatentPointCreatePayload,
  PatentDocument,
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
  deleteProjectPatentPoint,
  disclosureExportUrl,
  draftCompletionReportUrl,
  exportUrl,
  filingReadinessReportUrl,
  generateProject,
  getAgentDoctor,
  getCorpusStats,
  getHealth,
  importPatent,
  listClaimDefenseWorksheets,
  listCorpus,
  listCorpusVersions,
  listDraftCompletionRuns,
  listFilingReadinessReports,
  listProjectDisclosures,
  listProjectDeliberations,
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
  expertToolGroups,
  mainSections,
  type ExpertToolId,
  type MainSectionId,
  type PatentGoalMode,
} from "./guidedFlow";
import "./styles.css";

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

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? projects[0] ?? null,
    [projects, selectedProjectId],
  );
  const currentPackage: DraftPackage | null = selectedProject?.package ?? null;
  const currentDeliberation = latestCompletedDeliberation(deliberationRuns);
  const currentDisclosure = latestCompletedDisclosure(disclosureRuns);
  const visiblePatentPoints = patentPointsProjectId === selectedProject?.id ? patentPoints : [];
  const latestFilingReport = filingReports[0] ?? null;
  const latestWorksheet = worksheets[0] ?? null;
  const latestCompletionRun = completionRuns[0] ?? null;
  const activeMainSection = mainSections.find((section) => section.id === activeSection) ?? mainSections[0];
  const activeExpertToolEntry = expertToolGroups
    .flatMap((group) => group.tools)
    .find((tool) => tool.id === activeExpertTool);
  selectedProjectIdRef.current = selectedProject?.id ?? "";

  useEffect(() => {
    void refreshAll();
  }, []);

  useEffect(() => {
    if (selectedProject?.id) {
      void loadDeliberations(selectedProject.id);
      void loadMaterials(selectedProject.id);
      void loadDisclosures(selectedProject.id);
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
    if (!selectedProject?.id || (!deliberating && !disclosing)) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadDeliberations(selectedProject.id);
      void loadDisclosures(selectedProject.id);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [selectedProject?.id, deliberationRuns, disclosureRuns]);

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
      if (!selectedProjectId && projectsData[0]) {
        setSelectedProjectId(projectsData[0].id);
      }
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
      const run = await startProjectDeliberation(projectId, trace);
      const stillSelected = await loadDeliberations(projectId);
      if (!stillSelected) return;
      setMessage(`会审已${run.status === "completed" ? "完成" : "启动"}：${run.run_mode}`);
    });
  }

  async function handleGenerate() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("generate", async () => {
      await generateProject(projectId, currentDeliberation?.id ?? null);
      const nextProjects = await listProjects();
      if (selectedProjectIdRef.current !== projectId) return;
      setProjects(nextProjects);
      setSelectedProjectId(projectId);
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
    await handleRunFilingReadiness();
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

  async function handleSelectPatentPoint(point: PatentPointCandidate) {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    await withStatus("patent-point-select", async () => {
      const alreadySaved = visiblePatentPoints.some((candidate) => candidate.id === point.id);
      if (alreadySaved) {
        await updateProjectPatentPoint(projectId, point.id, { selected: true });
      } else {
        await createProjectPatentPoint(projectId, {
          title: point.title,
          technical_problem: point.technical_problem,
          innovation: point.innovation,
          technical_solution: point.technical_solution,
          beneficial_effects: point.beneficial_effects,
          protection_focus: point.protection_focus,
          evidence_status: point.evidence_status,
          source_type: point.source_type,
          feasibility_basis: point.feasibility_basis,
          support_gaps: point.support_gaps,
          experiment_needed: point.experiment_needed,
          moat_scores: point.moat_scores,
          selected: true,
          rationale: point.rationale,
        });
      }
      const stillSelected = await loadPatentPoints(projectId);
      if (!stillSelected) return;
      setMessage(`已选择专利点：${point.title}`);
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
            busy={busy}
            onStart={handleStartDeliberation}
            onRefresh={() => selectedProject && loadDeliberations(selectedProject.id)}
          />
        );
      case "write":
        return (
          <WriteView
            project={selectedProject}
            deliberation={currentDeliberation}
            disclosure={currentDisclosure}
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
            onPatch={handleCompletionPatch}
          />
        );
      case "review":
        return <ReviewView project={selectedProject} busy={busy} onReview={handleReview} />;
      case "export":
        return <ExportView project={selectedProject} packageValue={currentPackage} />;
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">PA</span>
          <div>
            <h1>专利写作 Agent</h1>
            <p>中国发明专利 / AI软件方法</p>
          </div>
        </div>
        <nav className="tab-list" aria-label="主导航">
          {mainSections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                className={activeSection === section.id ? "tab active" : "tab"}
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
        <div className="status-panel">
          <div className={health?.llm_configured ? "status ok" : "status warn"}>
            {health?.llm_configured ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <span>{health?.llm_configured ? "模型已配置" : "未配置 DEEPSEEK_API_KEY"}</span>
          </div>
          <div className={agentDoctor?.status === "blocked" ? "status warn" : "status ok"}>
            {agentDoctor?.status === "blocked" ? <AlertTriangle size={16} /> : <UsersRound size={16} />}
            <span>Agent {agentDoctor?.run_mode ?? "unknown"}</span>
          </div>
          <p>生成时会向云端模型服务发送 draft 与检索片段。</p>
          <button className="icon-button ghost" onClick={refreshAll} type="button" title="刷新">
            <RefreshCw size={17} />
            <span>刷新</span>
          </button>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Guided Patent Workbench</p>
            <h2>{activeSection === "expert" ? activeExpertToolEntry?.label ?? "专家工具" : activeMainSection.label}</h2>
            <p className="topbar-subtitle">
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
          <div className={error ? "notice error" : "notice"}>
            {busy && <Loader2 className="spin" size={16} />}
            <span>{error || message || "处理中"}</span>
          </div>
        )}

        {activeSection === "generate" && (
          <GuidedPatentFlowView
            project={selectedProject}
            materials={projectMaterials}
            disclosures={disclosureRuns}
            patentPoints={visiblePatentPoints}
            filingReports={filingReports}
            worksheets={worksheets}
            completionRuns={completionRuns}
            busy={busy}
            onCreateIdeaProject={handleCreateIdeaProject}
            onUploadMaterial={handleUploadMaterial}
            onStartDisclosure={() => void handleStartDisclosure(false)}
            onSelectPatentPoint={(point) => void handleSelectPatentPoint(point)}
            onGenerateDraft={() => void handleGenerate()}
            onRunQualityChecks={() => void handleRunGuidedQualityChecks()}
            onAcceptPatch={(runId, patchId) => void handleCompletionPatch(runId, patchId, "accept")}
          />
        )}
        {activeSection === "projects" && (
          <ProjectsOverview
            projects={projects}
            selectedProjectId={selectedProject?.id ?? ""}
            onSelect={setSelectedProjectId}
          />
        )}
        {activeSection === "expert" && (
          <div className="stack">
            <ExpertToolChooser activeToolId={activeExpertTool} onSelect={setActiveExpertTool} />
            {renderExpertTool()}
          </div>
        )}
      </section>
    </main>
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
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>官方导出物批量建库</h3>
          <p>支持 ZIP、CSV/XLSX 元数据表和 PDF/XML/TXT/DOCX 全文配对导入；扫描版 PDF 会进入失败清单。</p>
        </div>
        <button
          className="primary"
          disabled={!job || job.input_paths.length === 0 || busy === "corpus-run"}
          onClick={onRunJob}
          type="button"
        >
          <FileArchive size={18} />
          <span>运行导入</span>
        </button>
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>导入任务</h3>
          <form className="stack" onSubmit={onCreateJob}>
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
                className="small-textarea"
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
            <button className="primary" disabled={busy === "corpus-job"} type="submit">
              <FileText size={17} />
              <span>创建任务</span>
            </button>
          </form>

          <form className="stack upload-box" onSubmit={onUploadFile}>
            {job && <p className="workflow-hint">{jobHint}</p>}
            <input
              id="corpus-batch-file"
              name="corpus-batch-file"
              type="file"
              accept=".zip,.csv,.xlsx,.xlsm,.pdf,.docx,.txt,.md,.markdown,.xml"
              disabled={!job}
            />
            <button className="icon-button" disabled={!job || busy === "corpus-upload"} type="submit">
              <Upload size={17} />
              <span>上传批次文件</span>
            </button>
          </form>
        </div>

        <div className="panel">
          <h3>任务进度</h3>
          {job ? (
            <>
              <p className="workflow-hint">{jobHint}</p>
              <div className="metric-grid">
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
            <p className="empty">先创建导入任务，再上传官方导出物。</p>
          )}
          {report && <QualityReportView report={report} />}
        </div>
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>语料统计</h3>
          {stats ? (
            <div className="stack">
              <div className="metric-grid">
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
            <p className="empty">暂无统计</p>
          )}
        </div>

        <div className="panel">
          <h3>语料版本</h3>
          <div className="list">
            {versions.map((version) => (
              <article className="result-item" key={version.id}>
                <div className="result-meta">
                  <span>{version.domain}</span>
                  <span>{version.document_count} 件 / {version.chunk_count} 片段</span>
                </div>
                <p><strong>{version.name}</strong></p>
                <p>{version.query || version.source_name || "未记录检索式"}</p>
              </article>
            ))}
            {versions.length === 0 && <p className="empty">暂无版本</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

function QualityReportView({ report }: { report: CorpusImportJob["quality_report"] }) {
  if (!report) return null;
  return (
    <div className="quality-report">
      <h4>质量报告</h4>
      <div className="metric-grid">
        <StatusPill label="可抽取率" value={percent(report.fulltext_extractable_rate)} />
        <StatusPill label="索引片段" value={String(report.indexed_chunks)} />
        <StatusPill label="低质量样本" value={String(report.low_quality_documents.length)} />
        <StatusPill label="错误数" value={String(report.failures.length)} />
      </div>
      {report.failures.length > 0 && (
        <div className="list">
          {report.failures.slice(0, 6).map((failure) => (
            <article className="row-item" key={`${failure.file}-${failure.reason}`}>
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
    <div className="distribution">
      <div className="distribution-title">
        <BarChart3 size={16} />
        <strong>{title}</strong>
      </div>
      {entries.length > 0 ? (
        <div className="chip-row">
          {entries.map(([key, value]) => (
            <span className="chip" key={key}>{key}: {value}</span>
          ))}
        </div>
      ) : (
        <p className="empty">暂无数据</p>
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
      <div className="expert-tool-groups">
        {expertToolGroups.map((group) => (
          <div className="expert-tool-group" key={group.id}>
            <p>{group.label}</p>
            <div className="expert-tool-list">
              {group.tools.map((tool) => {
                const Icon = tool.icon;
                return (
                  <button
                    className={activeToolId === tool.id ? "expert-tool-button active" : "expert-tool-button"}
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
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>{project ? `${project.name} / 护城河专利点` : "护城河专利点"}</h3>
          <p>{project ? "把用户明确指定的可保护技术点登记成后续交底书、会审和撰写的输入。" : "先创建项目后再登记专利点。"}</p>
        </div>
        <ShieldCheck size={22} />
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>新增专利点</h3>
          <form className="stack" onSubmit={handleSubmit}>
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
                className="small-textarea"
                value={form.technical_problem}
                onChange={(event) => setForm((current) => ({ ...current, technical_problem: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>创新点</span>
              <textarea
                className="small-textarea"
                value={form.innovation}
                onChange={(event) => setForm((current) => ({ ...current, innovation: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>技术方案</span>
              <textarea
                className="small-textarea"
                value={form.technical_solution}
                onChange={(event) => setForm((current) => ({ ...current, technical_solution: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>可行性依据</span>
              <textarea
                className="small-textarea"
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
            <button className="primary" disabled={!canSubmit || busy === "patent-point-create"} type="submit">
              <ShieldCheck size={17} />
              <span>加入护城河</span>
            </button>
          </form>
        </div>

        <div className="panel">
          <h3>专利点列表</h3>
          <div className="list">
            {points.map((point) => {
              const total = moatScoreTotal(point.moat_scores);
              return (
                <article className={point.selected ? "result-item selected-point" : "result-item"} key={point.id}>
                  <div className="result-meta">
                    <span className="status-badge">{evidenceStatusLabel(point.evidence_status)}</span>
                    <span className="status-badge muted">{sourceTypeLabel(point.source_type)}</span>
                    <span>{Math.round(total * 100)} 分</span>
                  </div>
                  <p><strong>{point.title}</strong></p>
                  <p>{point.innovation || point.technical_solution}</p>
                  <p className={point.support_gaps.length > 0 ? "workflow-hint" : "empty"}>
                    {point.support_gaps.length > 0 ? `支撑缺口：${point.support_gaps.join("；")}` : "支撑材料暂未标记缺口。"}
                  </p>
                  <div className="score-grid">
                    <StatusPill label="范围" value={percent(point.moat_scores.scope_width)} />
                    <StatusPill label="绕开难度" value={percent(point.moat_scores.designaround_difficulty)} />
                    <StatusPill label="可行性" value={percent(point.moat_scores.feasibility)} />
                    <StatusPill label="支撑" value={percent(point.moat_scores.support_strength)} />
                    <StatusPill label="现有技术距离" value={percent(point.moat_scores.prior_art_distance)} />
                    <StatusPill label="战略价值" value={percent(point.moat_scores.strategic_value)} />
                  </div>
                  {point.claim_chart.length > 0 && (
                    <div className="claim-chart">
                      {point.claim_chart.slice(0, 2).map((item) => (
                        <p key={item.prior_art_id}>
                          <strong>{item.prior_art_title}</strong>：{item.claim_drafting_advice}
                        </p>
                      ))}
                    </div>
                  )}
                  <div className="button-row">
                    <button
                      className="icon-button"
                      disabled={!project || busy === "patent-point-select" || point.selected}
                      onClick={() => void onSelect(point)}
                      type="button"
                      title="设为选中"
                    >
                      <ShieldCheck size={17} />
                      <span>{point.selected ? "已选中" : "选中"}</span>
                    </button>
                    <button
                      className="icon-button"
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
            {points.length === 0 && <p className="empty">暂无用户指定专利点。</p>}
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
  busy,
  onStart,
  onRefresh,
}: {
  project: ProjectRecord | null;
  doctor: AgentDoctorReport | null;
  runs: DeliberationRun[];
  disclosure: DisclosureRun | null;
  busy: string;
  onStart: (trace?: boolean) => void;
  onRefresh: () => void;
}) {
  const latest = runs[0] ?? null;
  const completed = latestCompletedDeliberation(runs);
  return (
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>多 Agent 会审</h3>
          <p>
            {project
              ? "会审会调用本机 Codex、Gemini、Claude，先讨论保护范围和写作策略，再注入生成流程。"
              : "先创建项目后再启动会审。"}
          </p>
          <p>{disclosure ? `将默认注入交底书 run：${disclosure.id}` : "暂无已完成交底书，会审仅使用 draft 与 RAG 片段。"}</p>
        </div>
        <div className="button-row">
          <button className="icon-button" onClick={onRefresh} type="button" title="刷新会审">
            <RefreshCw size={17} />
          </button>
          <button
            className="primary"
            disabled={!project || doctor?.status === "blocked" || busy === "deliberate"}
            onClick={() => onStart(false)}
            type="button"
          >
            <UsersRound size={18} />
            <span>启动会审</span>
          </button>
        </div>
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>Provider Doctor</h3>
          <div className="doctor-grid">
            <StatusPill label="状态" value={doctor?.status ?? "unknown"} />
            <StatusPill label="运行级别" value={doctor?.run_mode ?? "unknown"} />
          </div>
          <div className="list">
            {Object.values(doctor?.commands ?? {}).map((provider) => (
              <article className="row-item" key={provider.id}>
                {provider.available ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                <div>
                  <strong>{provider.label}</strong>
                  <span>{provider.available ? provider.path : "missing"}</span>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="panel">
          <h3>会审记录</h3>
          <div className="list">
            {runs.map((run) => (
              <article className="result-item" key={run.id}>
                <div className="result-meta">
                  <span>{run.status}</span>
                  <span>{run.run_mode}</span>
                </div>
                <p>{run.providers.join(" / ")}</p>
                <p>{run.events.at(-1) ?? "暂无事件"}</p>
              </article>
            ))}
            {runs.length === 0 && <p className="empty">暂无会审记录</p>}
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
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>前置材料生成</h3>
          <p>
            {project
              ? "从 draft 和补充材料挖掘专利点，检索公开现有技术，并生成可交给代理人的技术交底书。"
              : "先创建项目后再上传材料。"}
          </p>
        </div>
        <div className="button-row">
          <button className="icon-button" onClick={onRefresh} type="button" title="刷新前置材料">
            <RefreshCw size={17} />
          </button>
          <button className="primary" disabled={!project || busy === "disclosure"} onClick={() => onStart(false)} type="button">
            <ClipboardList size={18} />
            <span>生成交底书</span>
          </button>
        </div>
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>补充材料</h3>
          <form className="stack upload-box" onSubmit={onUpload}>
            <input
              id="project-material-file"
              name="project-material-file"
              type="file"
              accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
              disabled={!project}
            />
            <button className="primary" disabled={!project || busy === "material-upload"} type="submit">
              <Upload size={17} />
              <span>上传材料</span>
            </button>
          </form>
          <div className="list">
            {materials.map((material) => (
              <article className="row-item" key={material.id}>
                {material.status === "processed" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                <div>
                  <strong>{material.file_name}</strong>
                  <span>{material.status === "processed" ? `${material.file_type} / ${material.text.length} 字` : material.warnings.join("；")}</span>
                </div>
              </article>
            ))}
            {materials.length === 0 && <p className="empty">未上传补充材料时，系统会仅基于 draft 生成。</p>}
          </div>
        </div>

        <div className="panel">
          <h3>生成记录</h3>
          <div className="list">
            {runs.map((run) => (
              <article className="result-item" key={run.id}>
                <div className="result-meta">
                  <span>{run.status}</span>
                  <span>{run.package?.prior_art_hits.length ?? 0} 条现有技术</span>
                </div>
                <p>{run.package?.title ?? run.events.at(-1) ?? "等待生成"}</p>
                <p>{run.events.at(-1) ?? "暂无事件"}</p>
              </article>
            ))}
            {runs.length === 0 && <p className="empty">暂无交底书生成记录。</p>}
          </div>
        </div>
      </section>

      <DisclosurePreview project={project} run={completed ?? latest} />
    </div>
  );
}

function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-pill">
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
    <label className="project-select">
      <span>当前项目</span>
      <select value={selectedProjectId} onChange={(event) => onChange(event.target.value)}>
        {projects.length === 0 && <option value="">暂无项目</option>}
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
}: {
  projects: ProjectRecord[];
  selectedProjectId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="panel wide">
      <h3>项目</h3>
      <p className="section-copy">选择历史项目后，可以继续生成、质检或导出。</p>
      <div className="project-grid">
        {projects.map((project) => {
          const metadata = project as ProjectRecord & ProjectMetadata;
          const isSelected = project.id === selectedProjectId;
          return (
            <article className={isSelected ? "project-card selected" : "project-card"} key={project.id}>
              <div>
                <strong>{project.name}</strong>
                <span>{project.package ? "已有初稿" : "仅有想法"}</span>
              </div>
              <dl className="project-meta">
                <div>
                  <dt>创建</dt>
                  <dd>{formatProjectDate(metadata.created_at)}</dd>
                </div>
                <div>
                  <dt>更新</dt>
                  <dd>{formatProjectDate(metadata.updated_at)}</dd>
                </div>
              </dl>
              <button
                className={isSelected ? "icon-button selected-project-button" : "primary"}
                disabled={isSelected}
                onClick={() => onSelect(project.id)}
                type="button"
              >
                {isSelected ? "当前项目" : "选择项目"}
              </button>
            </article>
          );
        })}
        {projects.length === 0 && <p className="empty">暂无项目。进入“专利生成”输入想法即可创建。</p>}
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
    <div className="two-column">
      <section className="panel">
        <h3>语料导入</h3>
        <form className="stack" onSubmit={onImport}>
          <input id="patent-file" name="patent-file" type="file" accept=".pdf,.docx,.txt,.md,.markdown" />
          <button className="primary" disabled={busy === "import"} type="submit" title="导入专利文件">
            <Upload size={17} />
            <span>导入</span>
          </button>
        </form>
        <div className="list">
          {documents.map((document) => (
            <article className="row-item" key={document.id}>
              <FileText size={18} />
              <div>
                <strong>{document.title}</strong>
                <span>{document.source_name}</span>
              </div>
            </article>
          ))}
          {documents.length === 0 && <p className="empty">暂无语料</p>}
        </div>
      </section>

      <section className="panel">
        <h3>片段检索</h3>
        <form className="search-form" onSubmit={onSearch}>
          <input value={searchText} onChange={(event) => onSearchText(event.target.value)} />
          <select value={searchSection} onChange={(event) => onSearchSection(event.target.value as SectionType | "")}>
            {sectionOptions.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button className="icon-button" disabled={busy === "search"} type="submit" title="检索">
            <Search size={17} />
          </button>
        </form>
        <div className="results">
          {searchResults.map((result) => (
            <article className="result-item" key={result.chunk.id}>
              <div className="result-meta">
                <span>{result.chunk.section_type}</span>
                <span>{result.score.toFixed(3)}</span>
              </div>
              <p>{result.chunk.text}</p>
            </article>
          ))}
          {searchResults.length === 0 && <p className="empty">暂无检索结果</p>}
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
    <section className="panel wide">
      <h3>技术交底</h3>
      <form className="stack" onSubmit={onSubmit}>
        <label>
          <span>项目名称</span>
          <input value={projectName} onChange={(event) => onProjectName(event.target.value)} />
        </label>
        <label>
          <span>Draft</span>
          <textarea
            className="draft-input"
            value={draftText}
            onChange={(event) => onDraftText(event.target.value)}
          />
        </label>
        <button className="primary" disabled={busy === "create"} type="submit" title="创建项目">
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
  busy,
  onGenerate,
}: {
  project: ProjectRecord | null;
  deliberation: DeliberationRun | null;
  disclosure: DisclosureRun | null;
  busy: string;
  onGenerate: () => void;
}) {
  return (
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>{project?.name ?? "未选择项目"}</h3>
          <p>{project?.draft_text ?? "先创建项目后再生成申请文本。"}</p>
          <p>
            {deliberation
              ? `将注入会审 run：${deliberation.id}`
              : "未完成多 Agent 会审，仍可直接生成。"}
          </p>
          <p>{disclosure ? `将注入前置交底书 run：${disclosure.id}` : "未完成前置交底书，仍可直接生成。"}</p>
        </div>
        <button className="primary" disabled={!project || busy === "generate"} onClick={onGenerate} type="button">
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
    return <section className="panel"><p className="empty">暂无前置材料结果。</p></section>;
  }
  if (!packageValue) {
    return (
      <section className="panel">
        <h3>{run.status === "completed" ? "交底书" : "生成中"}</h3>
        <p className="empty">{run.events.at(-1) ?? "等待后台任务更新。"}</p>
      </section>
    );
  }
  const selected = packageValue.candidates.find((candidate) => candidate.id === packageValue.selected_candidate_id)
    ?? packageValue.candidates[0]
    ?? null;
  return (
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>{packageValue.title}</h3>
          <p>{packageValue.summary}</p>
        </div>
        <div className="button-row">
          {project && (
            <>
              <a className="export-link compact-link" href={disclosureExportUrl(project.id, run.id, "docx")}>
                <Download size={17} />
                <span>DOCX</span>
              </a>
              <a className="export-link compact-link" href={disclosureExportUrl(project.id, run.id, "md")}>
                <Download size={17} />
                <span>MD</span>
              </a>
            </>
          )}
        </div>
      </section>

      <section className="preview">
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
    <section className="panel">
      <h3>当前前置交底书</h3>
      {packageValue ? (
        <div className="strategy-grid">
          <PreviewBlock title="摘要" text={packageValue.summary} />
          <PreviewBlock
            title="推荐专利点"
            text={(packageValue.candidates.find((candidate) => candidate.id === packageValue.selected_candidate_id) ?? packageValue.candidates[0])?.title ?? "暂无"}
          />
          <PreviewBlock title="现有技术差异" text={packageValue.prior_art_differences} />
        </div>
      ) : (
        <p className="empty">暂无已完成前置交底书。</p>
      )}
    </section>
  );
}

function FilingReadinessView({
  project,
  report,
  reports,
  busy,
  onRun,
}: {
  project: ProjectRecord | null;
  report: FilingReadinessReport | null;
  reports: FilingReadinessReport[];
  busy: string;
  onRun: () => void;
}) {
  const canExport = Boolean(project?.package);
  const reportStatusClass = report?.status === "high_risk" ? "danger" : report?.status === "warning" ? "warn" : "";
  return (
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>提交成熟度</h3>
          <p>{project?.package ? "检查官方提交导出、内部策略稿和申请文本中的占位符、敏感表述与高风险命中项。" : "生成申请文本后可运行提交成熟度检查。"}</p>
        </div>
        <button
          className="primary"
          disabled={!project?.package || busy === "filing-readiness"}
          onClick={onRun}
          type="button"
        >
          <ClipboardList size={18} />
          <span>运行检查</span>
        </button>
      </section>

      <section className="panel">
        <h3>导出</h3>
        {project && canExport ? (
          <div className="stack">
            {report?.status === "high_risk" && (
              <p className="workflow-hint">高风险：仍允许导出，但建议先处理报告中的命中项。</p>
            )}
            <div className="export-grid">
              <a className="export-link" href={officialExportUrl(project.id, "docx")}>
                <Download size={18} />
                <span>官方 DOCX</span>
              </a>
              <a className="export-link" href={officialExportUrl(project.id, "md")}>
                <Download size={18} />
                <span>官方 MD</span>
              </a>
              <a className="export-link" href={exportUrl(project.id, "md")}>
                <Download size={18} />
                <span>内部策略稿</span>
              </a>
              {report && (
                <a className="export-link" href={filingReadinessReportUrl(project.id, report.id)}>
                  <Download size={18} />
                  <span>检查报告</span>
                </a>
              )}
            </div>
          </div>
        ) : (
          <p className="empty">暂无可导出的申请文本。</p>
        )}
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>历史检查</h3>
          <div className="list">
            {reports.map((item) => (
              <article className="result-item" key={item.id}>
                <div className="result-meta">
                  <span className={`status-badge ${item.status === "high_risk" ? "danger" : item.status === "warning" ? "warn" : ""}`}>
                    {readinessStatusLabel(item.status)}
                  </span>
                  <span>{item.issues.length} 项命中</span>
                </div>
                <p>{item.created_at}</p>
                <p>{item.rules_version}</p>
              </article>
            ))}
            {reports.length === 0 && <p className="empty">暂无提交成熟度检查记录。</p>}
          </div>
        </div>

        <div className="panel">
          <h3>命中项</h3>
          {report && (
            <div className="result-meta">
              <span className={`status-badge ${reportStatusClass}`}>{readinessStatusLabel(report.status)}</span>
              <span>{report.issues.length} 项</span>
            </div>
          )}
          <div className="finding-list">
            {report?.issues.map((issue, index) => (
              <article className={`finding ${issue.severity}`} key={`${issue.category}-${issue.target}-${index}`}>
                <span>{severityLabel(issue.severity)}</span>
                <div>
                  <strong>{issue.category} / {issue.target}</strong>
                  <p>{issue.matched_text || "未记录匹配文本"}</p>
                  <p>{issue.message}</p>
                  <p>{issue.suggestion}</p>
                </div>
              </article>
            ))}
            {!report && <p className="empty">运行检查后显示命中项。</p>}
            {report && report.issues.length === 0 && <p className="empty">最新报告没有命中项。</p>}
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
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>权利要求防线</h3>
          <p>{project ? "从当前草稿、交底书和已生成文本提取特征记录，标记区别特征、支撑缺口与从属兜底建议。" : "先创建项目后再生成防线工作表。"}</p>
        </div>
        <button
          className="primary"
          disabled={!project || busy === "claim-defense"}
          onClick={onGenerate}
          type="button"
        >
          <ShieldCheck size={18} />
          <span>生成工作表</span>
        </button>
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>防线建议</h3>
          <div className="list">
            {worksheet?.defense_recommendations.map((item, index) => (
              <article className="row-item" key={`${item}-${index}`}>
                <ShieldCheck size={18} />
                <div>
                  <strong>建议 {index + 1}</strong>
                  <span>{item}</span>
                </div>
              </article>
            ))}
            {!worksheet && <p className="empty">生成工作表后显示防线建议。</p>}
            {worksheet && worksheet.defense_recommendations.length === 0 && <p className="empty">暂无防线建议。</p>}
          </div>
        </div>

        <div className="panel">
          <h3>历史版本</h3>
          <div className="list">
            {worksheets.map((item) => (
              <article className="result-item" key={item.id}>
                <div className="result-meta">
                  <span className="status-badge">{item.status}</span>
                  <span>{item.source}</span>
                  <span>{item.feature_records.length} 个特征</span>
                </div>
                <p>{item.created_at}</p>
              </article>
            ))}
            {worksheets.length === 0 && <p className="empty">暂无工作表历史版本。</p>}
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>特征记录</h3>
        <div className="feature-table">
          {worksheet?.feature_records.map((record) => (
            <article className="result-item" key={record.feature_id}>
              <div className="result-meta">
                <span className="status-badge">{featureClassificationLabel(record.classification)}</span>
                <span>{record.claim_refs.length > 0 ? record.claim_refs.join(" / ") : "未映射权利要求"}</span>
              </div>
              <p><strong>{record.text}</strong></p>
              <p>{record.risk_tags.length > 0 ? `风险标签：${record.risk_tags.join("；")}` : "暂无风险标签"}</p>
            </article>
          ))}
          {!worksheet && <p className="empty">生成工作表后显示特征记录。</p>}
          {worksheet && worksheet.feature_records.length === 0 && <p className="empty">暂无特征记录。</p>}
        </div>
      </section>

      <section className="panel">
        <h3>支撑缺口</h3>
        <div className="list">
          {worksheet?.support_gaps.map((gap, index) => (
            <article className="row-item" key={`${gap}-${index}`}>
              <AlertTriangle size={18} />
              <div>
                <strong>缺口 {index + 1}</strong>
                <span>{gap}</span>
              </div>
            </article>
          ))}
          {!worksheet && <p className="empty">生成工作表后显示支撑缺口。</p>}
          {worksheet && worksheet.support_gaps.length === 0 && <p className="empty">暂无支撑缺口。</p>}
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
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>审查意见</h3>
          <p>{project?.package ? project.name : "生成申请文本后可审查。"}</p>
        </div>
        <button className="primary" disabled={!project?.package || busy === "review"} onClick={onReview} type="button">
          <Search size={18} />
          <span>审查</span>
        </button>
      </section>
      <section className="panel">
        <div className="finding-list">
          {findings.map((finding, index) => (
            <article className={`finding ${finding.severity}`} key={`${finding.category}-${index}`}>
              <span>{severityLabel(finding.severity)}</span>
              <div>
                <strong>{finding.category}</strong>
                <p>{finding.message}</p>
                <p>{finding.suggestion}</p>
              </div>
            </article>
          ))}
          {findings.length === 0 && <p className="empty">暂无审查意见</p>}
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
  onPatch,
}: {
  project: ProjectRecord | null;
  run: DraftCompletionRun | null;
  runs: DraftCompletionRun[];
  busy: string;
  onRun: () => void;
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
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>Draft Completion Harness / 初稿完善循环</h3>
          <p>
            Warning mode：发现缺口、生成任务和候选补丁，但不把风险判断包装成已验证事实；补丁需人工接受后才进入完善结果。
          </p>
        </div>
        <button
          className="primary"
          disabled={!project?.package || Boolean(busy)}
          onClick={onRun}
          type="button"
        >
          <Gauge size={18} />
          <span>运行完善</span>
        </button>
      </section>

      <section className="panel">
        <div className="result-meta">
          <h3>评分</h3>
          {run && (
            <>
              <span className="status-badge">{run.status}</span>
              <span>{run.created_at}</span>
              <span>{runs.length} 次运行</span>
            </>
          )}
        </div>
        {run ? (
          <div className="score-grid">
            {scoreItems.map(([label, value]) => (
              <article className="score-card" key={label}>
                <span>{label}</span>
                <strong>{value}/100</strong>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty">生成申请文本后可运行初稿完善循环。</p>
        )}
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>高优先级问题</h3>
          <div className="finding-list">
            {displayedIssues.map((issue) => (
              <article className={`finding ${issue.severity}`} key={issue.id}>
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
            {!run && <p className="empty">运行后显示高优先级缺口。</p>}
            {run && displayedIssues.length === 0 && <p className="empty">暂无高优先级问题。</p>}
          </div>
        </div>

        <div className="panel">
          <h3>完善任务</h3>
          <div className="list">
            {run?.tasks.map((task) => (
              <article className="result-item" key={task.id}>
                <div className="result-meta">
                  <span className="status-badge">{taskStatusLabel(task.status)}</span>
                  <span>优先级 {task.priority}</span>
                  <span>{task.draft_section_target}</span>
                </div>
                <p><strong>{task.task_type}</strong></p>
                <p>{task.expected_output}</p>
              </article>
            ))}
            {!run && <p className="empty">运行后显示待完善任务。</p>}
            {run && run.tasks.length === 0 && <p className="empty">暂无完善任务。</p>}
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>Claim Support Matrix</h3>
        {run && run.support_matrix.length > 0 ? (
          <div className="matrix-table">
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
          <p className="empty">{run ? "暂无支撑矩阵。" : "运行后显示权利要求支撑矩阵。"}</p>
        )}
      </section>

      <section className="panel">
        <div className="result-meta">
          <h3>候选补丁</h3>
          {project && run && (
            <a className="export-link compact-link" href={draftCompletionReportUrl(project.id, run.id)}>
              <Download size={17} />
              <span>报告 MD</span>
            </a>
          )}
        </div>
        <div className="list">
          {run?.patches.map((patch) => (
            <article className="result-item" key={patch.id}>
              <div className="result-meta">
                <span className={`status-badge ${patchStatusClass(patch.status)}`}>{patch.status}</span>
                <span>{patch.patch_kind}</span>
                <span>{patch.target_section}</span>
                <span>{patch.can_enter_official_draft ? "可进入官方稿" : "仅内部侧车"}</span>
              </div>
              <p><strong>{patch.rationale}</strong></p>
              <p>{patch.risk_delta}</p>
              <pre className="patch-preview">{patch.after_text || "无 after_text"}</pre>
              <div className="button-row">
                <button
                  className="primary"
                  disabled={patch.status !== "proposed" || patchBusy}
                  onClick={() => onPatch(run.id, patch.id, "accept")}
                  type="button"
                >
                  接受
                </button>
                <button
                  className="icon-button"
                  disabled={patch.status !== "proposed" || patchBusy}
                  onClick={() => onPatch(run.id, patch.id, "reject")}
                  type="button"
                >
                  拒绝
                </button>
              </div>
            </article>
          ))}
          {!run && <p className="empty">运行后显示候选补丁。</p>}
          {run && run.patches.length === 0 && <p className="empty">暂无候选补丁。</p>}
        </div>
      </section>
    </div>
  );
}

function ExportView({
  project,
  packageValue,
}: {
  project: ProjectRecord | null;
  packageValue: DraftPackage | null;
}) {
  const enabled = canExportPackage(packageValue);
  return (
    <section className="panel wide">
      <h3>导出文件</h3>
      <div className="export-grid">
        {[
          ["docx", "DOCX"],
          ["md", "Markdown"],
          ["mmd", "Mermaid"],
          ["prompt", "绘图提示词"],
        ].map(([kind, label]) => (
          <a
            aria-disabled={!enabled}
            className={enabled ? "export-link" : "export-link disabled"}
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
    <section className="panel">
      <h3>{title}</h3>
      {strategy ? (
        <div className="strategy-grid">
          <PreviewBlock title="摘要" text={strategy.summary} />
          <PreviewBlock title="权利要求策略" text={strategy.claim_strategy.join("\n")} />
          <PreviewBlock title="说明书策略" text={strategy.description_strategy.join("\n")} />
          <PreviewBlock title="风险控制" text={strategy.risk_controls.join("\n")} />
          <PreviewBlock title="Agent 共识" text={strategy.agent_consensus} />
        </div>
      ) : (
        <p className="empty">暂无可注入策略</p>
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
    return <p className="empty">暂无申请文本</p>;
  }
  return (
    <section className={compact ? "preview compact" : "preview"}>
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
    <article className="preview-block">
      <h4>{title}</h4>
      <pre>{text}</pre>
    </article>
  );
}

export default App;
