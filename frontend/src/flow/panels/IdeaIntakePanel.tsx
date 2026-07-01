import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, FileText, ShieldCheck, Upload, Wand2 } from "@/lib/icons";
import type {
  ExternalDraftIntakeRun,
  ExternalDraftSource,
  ProjectMaterial,
  ProjectRecord,
} from "@/api";
import { ideaPatentGoalModes, patentTypeOptions, type PatentGoalMode, type PatentType } from "@/guidedFlow";
import { cn } from "@/lib/cn";
import { GuidedOperationConsole } from "../runtimeWidgets";
import { MaterialSummary } from "./MaterialSummary";
import { ExternalDraftIntakePanel } from "./ExternalDraftIntakePanel";

export interface IdeaIntakePanelProps {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  externalDraftSources: ExternalDraftSource[];
  externalDraftIntakeRuns: ExternalDraftIntakeRun[];
  busy: string;
  busyElapsedSeconds: number;
  fixedGoalMode?: PatentGoalMode;
  initialIntakeMode?: "idea" | "external";
  onCreateIdeaProject: (payload: {
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
  }) => Promise<void>;
  onCreateExternalDraft: (payload: { text: string; fileName: string }) => Promise<void>;
  onUploadExternalDraft: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onStartExternalDraftIntake: (sourceId: string) => Promise<void>;
  onConfirmExternalDraftIntake: (
    runId: string,
    payload: {
      title: string;
      abstract: string;
      claims: string;
      description: string;
      drawing_description: string;
    },
  ) => Promise<void>;
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => void;
}

export function IdeaIntakePanel({
  project,
  materials,
  externalDraftSources,
  externalDraftIntakeRuns,
  busy,
  busyElapsedSeconds,
  fixedGoalMode,
  initialIntakeMode,
  onCreateIdeaProject,
  onCreateExternalDraft,
  onUploadExternalDraft,
  onStartExternalDraftIntake,
  onConfirmExternalDraftIntake,
  onUploadMaterial,
}: IdeaIntakePanelProps) {
  const [name, setName] = useState(project?.name ?? "");
  const [idea, setIdea] = useState(project?.draft_text ?? "");
  const [mode, setMode] = useState<PatentGoalMode>("stable");
  const [patentType, setPatentType] = useState<PatentType>(fixedGoalMode === "utility" ? "utility_model" : "invention");
  const [intakeMode, setIntakeMode] = useState<"idea" | "external">(initialIntakeMode ?? "idea");
  const [showMetadata, setShowMetadata] = useState(false);
  const [applicant, setApplicant] = useState(project?.applicant ?? "");
  const [inventors, setInventors] = useState(project?.inventors ?? "");
  const [technicalField, setTechnicalField] = useState(project?.technical_field ?? "");
  const [background, setBackground] = useState(project?.background ?? "");
  const [painPoint, setPainPoint] = useState(project?.pain_point ?? "");
  const [technicalSolution, setTechnicalSolution] = useState(project?.technical_solution ?? "");
  const [innovation, setInnovation] = useState(project?.innovation ?? "");
  const [embodiments, setEmbodiments] = useState(project?.embodiments ?? "");
  const [beneficialEffects, setBeneficialEffects] = useState(project?.beneficial_effects ?? "");
  const nameError = !project && !name.trim() ? "项目名称不能为空" : "";
  const ideaError = !project && !idea.trim() ? "一句话想法不能为空" : "";
  const ideaGuidance = !project ? getIdeaInputGuidance(idea) : null;
  const ideaDescriptionIds = [ideaError ? "guided-project-idea-error" : "", ideaGuidance ? "guided-project-idea-guidance" : ""]
    .filter(Boolean)
    .join(" ") || undefined;
  const canSubmit = Boolean(!nameError && !ideaError && !project);
  const effectiveMode = fixedGoalMode ?? mode;
  const effectivePatentType: PatentType = fixedGoalMode === "utility" ? "utility_model" : patentType;
  const intakeModeLabel = intakeMode === "idea" ? "从想法生成" : "导入外部初稿";
  const patentTypeLabel = fixedGoalMode === "utility"
    ? "实用新型"
    : patentTypeOptions.find((item) => item.id === patentType)?.label ?? "发明专利";
  const goalModeLabel = fixedGoalMode === "utility"
    ? "实用新型轻量版"
    : ideaPatentGoalModes.find((item) => item.id === mode)?.label ?? "授权稳健";
  const latestExternalRun = externalDraftIntakeRuns[0] ?? null;
  const processedMaterialCount = materials.filter((material) => material.status === "processed").length;
  const failedMaterialCount = materials.length - processedMaterialCount;
  const externalQueueLabel = latestExternalRun
    ? latestExternalRun.status === "needs_review"
      ? "待确认章节"
      : `解析${latestExternalRun.status}`
    : externalDraftSources.length
      ? `${externalDraftSources.length} 份待解析`
      : "暂无外部稿";
  const materialSupportLabel =
    processedMaterialCount > 0 && failedMaterialCount > 0
      ? `${processedMaterialCount} 份可用，${failedMaterialCount} 份失败`
      : processedMaterialCount > 0
        ? `${processedMaterialCount} 份可用材料`
        : failedMaterialCount > 0
          ? `${failedMaterialCount} 份上传失败`
          : "材料可选";
  const intakeSupportLabel = intakeMode === "idea"
    ? materialSupportLabel
    : externalQueueLabel;
  const projectDisplayName = project?.name ?? (name.trim() || "待创建");
  const submitDisabledReason = project
    ? "项目已创建，可继续下一步。"
    : nameError || ideaError || "填写完成后可以创建项目。";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    await onCreateIdeaProject({
      name: name.trim(),
      idea: idea.trim(),
      mode: effectiveMode,
      patentType: effectivePatentType,
      applicant: applicant.trim() || undefined,
      inventors: inventors.trim() || undefined,
      technical_field: technicalField.trim() || undefined,
      background: background.trim() || undefined,
      pain_point: painPoint.trim() || undefined,
      technical_solution: technicalSolution.trim() || undefined,
      innovation: innovation.trim() || undefined,
      embodiments: embodiments.trim() || undefined,
      beneficial_effects: beneficialEffects.trim() || undefined,
    });
  }

  useEffect(() => {
    setIntakeMode(initialIntakeMode ?? "idea");
  }, [initialIntakeMode]);

  return (
    <section className="guided-panel guided-first-mile-panel">
      <div className="section-head">
        <div>
          <h3>{intakeMode === "idea" ? "把你的想法写成一段话" : "导入外部专利初稿"}</h3>
          <p>
            {intakeMode === "idea"
              ? "系统会基于这段想法提炼发明点、生成专利初稿、运行质检并准备导出文件。"
              : "保存外部稿原文，解析章节，并在人工确认后转为内部工作稿。"}
          </p>
        </div>
        {intakeMode === "idea" ? <Wand2 size={24} /> : <FileText size={24} />}
      </div>

      <div className="status-strip guided-intake-status" aria-label="首 Mile 摘要">
        <div className="status-tile">
          <span>入口方式</span>
          <strong>{intakeModeLabel}</strong>
        </div>
        <div className="status-tile">
          <span>项目</span>
          <strong title={projectDisplayName}>{projectDisplayName}</strong>
        </div>
        <div className="status-tile">
          <span>专利类型</span>
          <strong>{patentTypeLabel}</strong>
        </div>
        <div className="status-tile">
          <span>{intakeMode === "idea" ? "补充材料" : "外部稿队列"}</span>
          <strong>{intakeSupportLabel}</strong>
        </div>
      </div>

      <div className="settings-group">
        <div className="settings-group-header">
          <h3>起步配置</h3>
          <p>先确认入口，再填写项目内容。后续步骤会沿用这里选择的专利类型和目标模式。</p>
        </div>
        <div className="segmented" role="tablist" aria-label="专利生成入口">
          <button
            aria-selected={intakeMode === "idea"}
            className={cn("segment", intakeMode === "idea" && "is-active")}
            onClick={() => setIntakeMode("idea")}
            role="tab"
            type="button"
          >
            从想法生成
          </button>
          <button
            aria-selected={intakeMode === "external"}
            className={cn("segment", intakeMode === "external" && "is-active")}
            onClick={() => setIntakeMode("external")}
            role="tab"
            type="button"
          >
            导入外部初稿
          </button>
        </div>
      </div>

      {intakeMode === "idea" ? (
        <>
          <form className="guided-intake guided-intake-form" onSubmit={handleSubmit}>
            <div className="info-card guided-form-card">
              <div className="info-card-icon accent">
                <FileText size={18} aria-hidden="true" />
              </div>
              <div className="info-card-body">
                <strong>项目基础信息</strong>
                <p>创建项目后，项目名称和首段技术想法会作为后续发明点提炼的输入。</p>
                <div className="guided-field-grid">
                  <div className="field">
                    <label htmlFor="guided-project-name">项目名称</label>
                    <input
                      aria-describedby={nameError ? "guided-project-name-error" : undefined}
                      aria-invalid={Boolean(nameError)}
                      id="guided-project-name"
                      required
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      disabled={Boolean(project)}
                    />
                    {nameError && (
                      <small className="settings-hint warn" id="guided-project-name-error" role="alert">
                        {nameError}
                      </small>
                    )}
                  </div>
                  <div className="field field-wide">
                    <label htmlFor="guided-project-idea">一句话想法</label>
                    <textarea
                      aria-describedby={ideaDescriptionIds}
                      aria-invalid={Boolean(ideaError)}
                      className="idea-input"
                      id="guided-project-idea"
                      value={idea}
                      onChange={(event) => setIdea(event.target.value)}
                      disabled={Boolean(project)}
                      placeholder="例如：通过点云和多视角影像自动生成外立面 IFC 模型，并回链工程量清单。"
                      required
                    />
                    {ideaError && (
                      <small className="settings-hint warn" id="guided-project-idea-error" role="alert">
                        {ideaError}
                      </small>
                    )}
                    {ideaGuidance && (
                      <small className="settings-hint" id="guided-project-idea-guidance">
                        {ideaGuidance}
                      </small>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Structured metadata fields */}
            {!project && (
              <div className="settings-group">
                <div className="settings-group-header">
                  <h3>结构化元数据（可选）</h3>
                  <p>填写以下字段可提升后续发明点提炼精度和说明书生成质量。所有字段均为可选，可留空由系统自动生成。</p>
                </div>
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => setShowMetadata((v) => !v)}
                >
                  {showMetadata ? "收起元数据字段" : "展开元数据字段"}
                </button>
                {showMetadata && (
                  <div className="guided-field-grid" style={{ marginTop: "0.75rem" }}>
                    <label className="field">
                      <span>申请人</span>
                      <input
                        value={applicant}
                        onChange={(event) => setApplicant(event.target.value)}
                        placeholder="例如：焕城智慧科技（济南）有限公司"
                      />
                    </label>
                    <label className="field">
                      <span>发明人</span>
                      <input
                        value={inventors}
                        onChange={(event) => setInventors(event.target.value)}
                        placeholder="例如：刘博"
                      />
                    </label>
                    <label className="field field-wide">
                      <span>技术领域</span>
                      <input
                        value={technicalField}
                        onChange={(event) => setTechnicalField(event.target.value)}
                        placeholder="例如：计算机视觉、建筑信息建模"
                      />
                    </label>
                    <label className="field field-wide">
                      <span>背景技术</span>
                      <textarea
                        value={background}
                        onChange={(event) => setBackground(event.target.value)}
                        placeholder="描述现有技术的不足和行业痛点..."
                      />
                    </label>
                    <label className="field field-wide">
                      <span>技术痛点</span>
                      <textarea
                        value={painPoint}
                        onChange={(event) => setPainPoint(event.target.value)}
                        placeholder="本发明要解决的核心问题..."
                      />
                    </label>
                    <label className="field field-wide">
                      <span>技术方案</span>
                      <textarea
                        value={technicalSolution}
                        onChange={(event) => setTechnicalSolution(event.target.value)}
                        placeholder="描述技术方案的详细内容..."
                      />
                    </label>
                    <label className="field field-wide">
                      <span>创新点</span>
                      <textarea
                        value={innovation}
                        onChange={(event) => setInnovation(event.target.value)}
                        placeholder="与现有技术的区别和核心创新..."
                      />
                    </label>
                    <label className="field field-wide">
                      <span>实施例</span>
                      <textarea
                        value={embodiments}
                        onChange={(event) => setEmbodiments(event.target.value)}
                        placeholder="具体的实施方式示例..."
                      />
                    </label>
                    <label className="field field-wide">
                      <span>有益效果</span>
                      <textarea
                        value={beneficialEffects}
                        onChange={(event) => setBeneficialEffects(event.target.value)}
                        placeholder="本发明带来的技术效果和优势..."
                      />
                    </label>
                  </div>
                )}
              </div>
            )}

            {fixedGoalMode !== "utility" && (
              <div className="settings-group">
                <div className="settings-group-header">
                  <h3>专利类型</h3>
                  <p>影响流程深度、发明点提炼方式和后续正式稿边界。</p>
                </div>
                <div className="mode-grid">
                  {patentTypeOptions.map((item) => (
                    <button
                      className={cn("info-card guided-config-card", patentType === item.id && "selected")}
                      key={item.id}
                      onClick={() => setPatentType(item.id)}
                      type="button"
                    >
                      <div className={cn("info-card-icon", item.id === "utility_model" ? "success" : "info")}>
                        {item.id === "utility_model" ? <ShieldCheck size={18} aria-hidden="true" /> : <Wand2 size={18} aria-hidden="true" />}
                      </div>
                      <div className="info-card-body">
                        <strong>{item.label}</strong>
                        <p>{item.description}</p>
                      </div>
                      {patentType === item.id && <CheckCircle2 size={18} aria-hidden="true" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {fixedGoalMode === "utility" && (
              <div className="callout callout-success">
                <ShieldCheck size={18} aria-hidden="true" />
                <div>
                  <strong>已使用实用新型入口</strong>
                  <p>系统会优先关注结构组成、连接关系、安装位置和附图说明，减少发明专属重步骤。</p>
                </div>
              </div>
            )}
            {!fixedGoalMode && (
              <div className="settings-group">
                <div className="settings-group-header">
                  <h3>撰写目标</h3>
                  <p>目标模式只影响项目提示词和后续策略，不会跳过必要的质量门。</p>
                </div>
                <div className="mode-grid">
                  {ideaPatentGoalModes.map((item) => (
                    <button
                      className={cn("info-card guided-config-card", mode === item.id && "selected")}
                      key={item.id}
                      onClick={() => setMode(item.id)}
                      type="button"
                    >
                      <div className="info-card-icon accent">
                        <Wand2 size={18} aria-hidden="true" />
                      </div>
                      <div className="info-card-body">
                        <strong>{item.label}</strong>
                        <p>{item.description}</p>
                      </div>
                      {mode === item.id && <CheckCircle2 size={18} aria-hidden="true" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="action-dock">
              <span className="meta">
                当前目标：{goalModeLabel}；{canSubmit ? "创建后进入发明点/结构方案确认。" : submitDisabledReason}
              </span>
              <button
                aria-describedby={!canSubmit ? "guided-project-submit-reason" : undefined}
                className="btn btn-primary"
                disabled={!canSubmit || busy === "guided-create"}
                type="submit"
              >
                <FileText size={17} />
                <span>{project ? "已创建想法" : "创建并继续"}</span>
              </button>
              {!canSubmit && (
                <span className="sr-only" id="guided-project-submit-reason">
                  {submitDisabledReason}
                </span>
              )}
            </div>
            <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "guided-create"} />
          </form>
          {project && (
            <>
              <form className="info-card guided-upload guided-upload-card" onSubmit={onUploadMaterial}>
                <div className="info-card-icon info">
                  <Upload size={18} aria-hidden="true" />
                </div>
                <div className="info-card-body">
                  <strong>补充材料</strong>
                  <p>可一次上传多份 PDF、DOCX、PPT 或 Markdown，作为发明点提炼和说明书支撑材料。</p>
                  <input
                    id="project-material-file"
                    name="project-material-file"
                    type="file"
                    accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
                    multiple
                  />
                </div>
                <button className="btn btn-primary" disabled={busy === "material-upload"} type="submit">
                  <Upload size={17} />
                  <span>上传补充材料</span>
                </button>
              </form>
              <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "material-upload"} />
            </>
          )}
          <MaterialSummary materials={materials} />
        </>
      ) : (
        <ExternalDraftIntakePanel
          project={project}
          sources={externalDraftSources}
          runs={externalDraftIntakeRuns}
          busy={busy}
          busyElapsedSeconds={busyElapsedSeconds}
          onCreateExternalDraft={onCreateExternalDraft}
          onUploadExternalDraft={onUploadExternalDraft}
          onStartExternalDraftIntake={onStartExternalDraftIntake}
          onConfirmExternalDraftIntake={onConfirmExternalDraftIntake}
        />
      )}
    </section>
  );
}

export function getIdeaInputGuidance(text: string): string | null {
  const normalized = text.trim().replace(/\s+/g, "");
  if (!normalized) return null;

  const marketingSignals = ["全球领先", "成本最低", "体验最好", "商业模式", "市场", "盈利", "客户增长"];
  const technicalSignals = [
    "模块",
    "步骤",
    "算法",
    "传感器",
    "数据",
    "模型",
    "控制",
    "检测",
    "结构",
    "连接",
    "采集",
    "处理",
    "输出",
    "装置",
    "系统",
  ];
  const looksMarketingOnly =
    marketingSignals.some((signal) => normalized.includes(signal)) &&
    !technicalSignals.some((signal) => normalized.includes(signal));
  if (looksMarketingOnly) {
    return "当前描述偏效果或商业价值，建议补充可实现的技术方案、数据流或结构关系。";
  }
  if (normalized.length < 24) {
    return "当前想法较短，建议补充技术问题、关键步骤或模块、预期技术效果。";
  }
  return null;
}
