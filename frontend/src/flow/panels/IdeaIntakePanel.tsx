import { useEffect, useState, type FormEvent } from "react";
import { FileText, Upload, Wand2 } from "@/lib/icons";
import { Button } from "@/components/ui/button";
import type {
  ExternalDraftIntakeRun,
  ExternalDraftSource,
  ProjectMaterial,
  ProjectRecord,
} from "@/api";
import { ideaPatentGoalModes, patentTypeOptions, type PatentGoalMode, type PatentType } from "@/guidedFlow";
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
  onCreateIdeaProject: (payload: { name: string; idea: string; mode: PatentGoalMode; patentType: PatentType }) => Promise<void>;
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
  const canSubmit = Boolean(name.trim() && idea.trim() && !project);
  const effectiveMode = fixedGoalMode ?? mode;
  const effectivePatentType: PatentType = fixedGoalMode === "utility" ? "utility_model" : patentType;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    await onCreateIdeaProject({ name: name.trim(), idea: idea.trim(), mode: effectiveMode, patentType: effectivePatentType });
  }

  useEffect(() => {
    setIntakeMode(initialIntakeMode ?? "idea");
  }, [initialIntakeMode]);

  return (
    <section className="grid gap-3.5 p-5 rounded-lg border border-app-border bg-app-surface">
      <div className="flex items-start justify-between gap-3.5">
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
      <div className="segmented-control" role="tablist" aria-label="专利生成入口">
        <button
          aria-selected={intakeMode === "idea"}
          className={intakeMode === "idea" ? "selected" : ""}
          onClick={() => setIntakeMode("idea")}
          role="tab"
          type="button"
        >
          从想法生成
        </button>
        <button
          aria-selected={intakeMode === "external"}
          className={intakeMode === "external" ? "selected" : ""}
          onClick={() => setIntakeMode("external")}
          role="tab"
          type="button"
        >
          导入外部初稿
        </button>
      </div>
      {intakeMode === "idea" ? (
        <>
          <form className="guided-intake" onSubmit={handleSubmit}>
            <label>
              <span>项目名称</span>
              <input value={name} onChange={(event) => setName(event.target.value)} disabled={Boolean(project)} />
            </label>
            <label>
              <span>一句话想法</span>
              <textarea
                className="idea-input"
                value={idea}
                onChange={(event) => setIdea(event.target.value)}
                disabled={Boolean(project)}
                placeholder="例如：通过点云和多视角影像自动生成外立面 IFC 模型，并回链工程量清单。"
              />
            </label>
            {fixedGoalMode !== "utility" && (
              <div className="mode-grid">
                {patentTypeOptions.map((item) => (
                  <button
                    className={patentType === item.id ? "mode-card selected" : "mode-card"}
                    key={item.id}
                    onClick={() => setPatentType(item.id)}
                    type="button"
                  >
                    <strong>{item.label}</strong>
                    <span>{item.description}</span>
                  </button>
                ))}
              </div>
            )}
            {!fixedGoalMode && (
              <div className="mode-grid">
                {ideaPatentGoalModes.map((item) => (
                  <button
                    className={mode === item.id ? "mode-card selected" : "mode-card"}
                    key={item.id}
                    onClick={() => setMode(item.id)}
                    type="button"
                  >
                    <strong>{item.label}</strong>
                    <span>{item.description}</span>
                  </button>
                ))}
              </div>
            )}
            <Button variant="glass-primary" disabled={!canSubmit || busy === "guided-create"} type="submit">
              <FileText size={17} />
              <span>{project ? "已创建想法" : "创建并继续"}</span>
            </Button>
            <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "guided-create"} />
          </form>
          {project && (
            <form className="guided-upload" onSubmit={onUploadMaterial}>
              <input
                id="project-material-file"
                name="project-material-file"
                type="file"
                accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
              />
              <Button variant="glass-primary" disabled={busy === "material-upload"} type="submit">
                <Upload size={17} />
                <span>上传补充材料</span>
              </Button>
              <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "material-upload"} />
            </form>
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
