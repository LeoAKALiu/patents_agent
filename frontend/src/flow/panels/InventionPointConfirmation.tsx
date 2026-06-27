import { useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";

import { Copy, FileText, Loader2, Search, ShieldCheck, Upload, Wand2 } from "@/lib/icons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  DisclosureRun,
  PatentPointCandidate,
  ProjectMaterial,
  ProjectRecord,
} from "@/api";
import { patentPointCandidatesFromDisclosureRun, evidenceStatusText } from "../inventionSelectors";
import {
  GuidedOperationConsole,
  GuidedRuntimeActions,
  GuidedRuntimeConsole,
  GuidedRuntimeFailures,
  guidedActiveRun,
} from "../runtimeWidgets";
import type { ExpertToolOpener } from "../parts";

export type DisclosureResearchMode = "standard" | "free_deep_research";

export interface InventionPointConfirmationProps {
  project: ProjectRecord | null;
  disclosure: DisclosureRun | null;
  disclosureRuns: DisclosureRun[];
  materials: ProjectMaterial[];
  patentPoints: PatentPointCandidate[];
  busy: string;
  busyElapsedSeconds: number;
  researchMode: DisclosureResearchMode;
  onChangeResearchMode: (mode: DisclosureResearchMode) => void;
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => void;
  onStartDisclosure: () => void;
  onCancelRun: (runId: string) => void;
  onRetryRun: (runId: string) => void;
  onSelectPatentPoint: (
    point: PatentPointCandidate,
    candidates: PatentPointCandidate[],
  ) => void;
  onOpenExpertTool: ExpertToolOpener;
}

export function InventionPointConfirmation({
  project,
  disclosure,
  disclosureRuns,
  materials,
  patentPoints,
  busy,
  busyElapsedSeconds,
  researchMode,
  onChangeResearchMode,
  onUploadMaterial,
  onStartDisclosure,
  onCancelRun,
  onRetryRun,
  onSelectPatentPoint,
  onOpenExpertTool,
}: InventionPointConfirmationProps) {
  const activeRun = guidedActiveRun(disclosureRuns);
  const latestRun = disclosureRuns[0] ?? null;
  const processedMaterialCount = materials.filter((material) => material.status === "processed").length;
  const failedMaterialCount = materials.length - processedMaterialCount;
  const activeRunCandidates = patentPointCandidatesFromDisclosureRun(activeRun);
  const latestRunCandidates = patentPointCandidatesFromDisclosureRun(latestRun);
  const disclosureCandidates = activeRunCandidates.length
    ? activeRunCandidates
    : latestRunCandidates.length
      ? latestRunCandidates
      : disclosure?.package?.candidates ?? [];
  const candidates = disclosureCandidates.length ? disclosureCandidates : patentPoints;
  const needsGeneration = (!disclosure || candidates.length === 0) && !activeRun;
  const showingPartialCandidates = Boolean(activeRun && activeRunCandidates.length > 0 && !activeRun.package);

  return (
    <section className="grid gap-3.5 p-5 rounded-lg border border-app-border bg-app-surface">
      <div className="flex items-start justify-between gap-3.5">
        <div>
          <h3>确认发明点与护城河</h3>
          <p>确认主线后，才会进入初稿生成。</p>
        </div>
        <ShieldCheck size={24} />
      </div>
      <div className="button-row">
        <Button
          variant="glass-soft"
          className="max-w-full whitespace-normal"
          onClick={() => onOpenExpertTool("materials")}
          type="button"
        >
          查看前置材料详情
        </Button>
        <Button
          variant="glass-soft"
          className="max-w-full whitespace-normal"
          onClick={() => onOpenExpertTool("moat")}
          type="button"
        >
          查看护城河地图
        </Button>
      </div>
      <ExternalDeepResearchGuide
        busy={busy}
        busyElapsedSeconds={busyElapsedSeconds}
        materialCount={processedMaterialCount}
        failedMaterialCount={failedMaterialCount}
        onUploadMaterial={onUploadMaterial}
        project={project}
      />
      {needsGeneration && (
        <div className="guided-research-mode" data-testid="disclosure-research-mode">
          <label htmlFor="disclosure-research-mode-select" className="guided-research-mode-label">
            研究模式
          </label>
          <select
            id="disclosure-research-mode-select"
            value={researchMode}
            onChange={(event) =>
              onChangeResearchMode(event.target.value as "standard" | "free_deep_research")
            }
          >
            <option value="standard">标准（默认）</option>
            <option value="free_deep_research">免费 Deep Research（公开检索 + 多轮分析）</option>
          </select>
          <p className="guided-research-mode-hint">
            {researchMode === "free_deep_research"
              ? "免费 Deep Research 将在系统内执行公开专利、arXiv/OpenAlex 论文检索与多轮 LLM 分析；配置 Tavily、Exa、Semantic Scholar 等 API key 时会自动扩展检索源，未配置也会用免费公开源降级运行。它仅生成内部补充材料，不替代多智能体会审，不解锁正式稿导出。"
              : "标准模式只走常规交底书流水线；如希望系统在交底阶段做更深的公开检索调研，可切换为免费 Deep Research。"}
          </p>
        </div>
      )}
      {needsGeneration && (
        <Button variant="glass-primary" disabled={busy === "disclosure"} onClick={onStartDisclosure} type="button">
          {busy === "disclosure" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
          <span>{researchMode === "free_deep_research" ? "提炼发明点（免费 Deep Research）" : "提炼发明点"}</span>
        </Button>
      )}
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "disclosure"} />
      <GuidedRuntimeConsole run={activeRun} label="发明点提炼运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={disclosureRuns[0] ?? null} />
      <GuidedRuntimeActions run={disclosureRuns[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {showingPartialCandidates && (
        <p className="workflow-hint">
          候选发明点已返回，后台仍在整理交底包；可以先查看候选主线，完整包完成后会自动刷新。
        </p>
      )}
      <div className="guided-card-grid">
        {candidates.map((point) => (
          <article className={point.selected ? "guided-choice selected" : "guided-choice"} key={point.id}>
            <div className="result-meta">
              <Badge variant="success" className="text-xs">{evidenceStatusText(point.evidence_status)}</Badge>
              <span>{point.protection_focus.join(" / ") || "方法 / 系统"}</span>
            </div>
            <h4>{point.title}</h4>
            <p>{point.innovation || point.technical_solution}</p>
            {point.support_gaps.length > 0 && <p className="workflow-hint">支撑缺口：{point.support_gaps.join("；")}</p>}
            <Button
              variant="glass-soft"
              className="max-w-full justify-self-start whitespace-normal"
              onClick={() => onSelectPatentPoint(point, candidates)}
              type="button"
            >
              选为主线并保存后备路线
            </Button>
          </article>
        ))}
        {candidates.length === 0 && <p className="empty">点击“提炼发明点”后显示候选主线。</p>}
      </div>
    </section>
  );
}

function ExternalDeepResearchGuide({
  project,
  materialCount,
  failedMaterialCount,
  busy,
  busyElapsedSeconds,
  onUploadMaterial,
}: {
  project: ProjectRecord | null;
  materialCount: number;
  failedMaterialCount: number;
  busy: string;
  busyElapsedSeconds: number;
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const prompt = useMemo(() => buildExternalDeepResearchPrompt(project), [project]);
  const materialFormRef = useRef<HTMLFormElement>(null);
  const materialInputRef = useRef<HTMLInputElement>(null);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [promptOpen, setPromptOpen] = useState(materialCount === 0);
  const [selectedMaterialNames, setSelectedMaterialNames] = useState<string[]>([]);
  const materialStatusText =
    materialCount > 0 && failedMaterialCount > 0
      ? `当前已有 ${materialCount} 份可用材料，${failedMaterialCount} 份失败上传。`
      : materialCount > 0
        ? `当前已有 ${materialCount} 份可用材料。`
        : failedMaterialCount > 0
          ? `已有 ${failedMaterialCount} 份上传失败，请重新选择可读且支持的文件。`
          : "上传后再点击提炼发明点。";

  async function handleCopyPrompt() {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(prompt);
      setCopyStatus("copied");
      window.setTimeout(() => setCopyStatus("idle"), 2200);
    } catch {
      setCopyStatus("failed");
    }
  }

  function handleMaterialButtonClick() {
    if (busy === "material-upload") return;
    materialInputRef.current?.click();
  }

  function handleMaterialFileChange(event: ChangeEvent<HTMLInputElement>) {
    const fileNames = Array.from(event.currentTarget.files ?? []).map((file) => file.name);
    setSelectedMaterialNames(fileNames);
    if (fileNames.length > 0) {
      window.setTimeout(() => materialFormRef.current?.requestSubmit(), 0);
    }
  }

  async function handleMaterialSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!materialInputRef.current?.files?.[0]) {
      materialInputRef.current?.click();
      return;
    }
    await onUploadMaterial(event);
    setSelectedMaterialNames([]);
  }

  return (
    <section className="settings-group external-research-guide" data-testid="external-deep-research-guide">
      <div className="settings-group-header">
        <h3>外部 Deep Research 辅助</h3>
        <p>
          先复制提示词去外部 Deep Research，拿到报告后在这里上传；报告会进入补充材料，再参与发明点提炼。
        </p>
      </div>

      <div className="external-research-flow" aria-label="外部 Deep Research 导入流程">
        <div>
          <span>1</span>
          <strong>复制研究提示词</strong>
          <p>围绕现有技术、区别特征和可保护主线做检索。</p>
        </div>
        <div>
          <span>2</span>
          <strong>导出研究报告</strong>
          <p>建议保存为 Markdown、TXT、PDF 或 DOCX。</p>
        </div>
        <div>
          <span>3</span>
          <strong>上传后再提炼</strong>
          <p>{materialStatusText}</p>
        </div>
      </div>

      <div className="external-research-actions">
        <Button
          variant="glass-soft"
          className="max-w-full whitespace-normal"
          onClick={() => void handleCopyPrompt()}
          type="button"
        >
          <Copy size={17} />
          <span>{copyStatus === "copied" ? "已复制提示词" : "复制 Deep Research 提示词"}</span>
        </Button>
        <span className="external-research-copy-status" role="status">
          {copyStatus === "failed" ? "复制失败，可展开后手动复制。" : "上传后可在前置材料详情中查看。"}
        </span>
      </div>

      <details
        className="external-research-prompt"
        onToggle={(event) => setPromptOpen(event.currentTarget.open)}
        open={promptOpen}
      >
        <summary>
          <Search size={16} aria-hidden="true" />
          <span>查看完整提示词</span>
        </summary>
        <textarea aria-label="外部 Deep Research 提示词" readOnly value={prompt} />
      </details>

      <form className="guided-upload external-research-upload" onSubmit={handleMaterialSubmit} ref={materialFormRef}>
        <div className="external-research-upload-field">
          <label htmlFor="project-material-file-invention">
            <FileText size={16} aria-hidden="true" />
            <span>上传外部研究报告或补充材料</span>
          </label>
          <input
            id="project-material-file-invention"
            name="project-material-file"
            type="file"
            accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
            multiple
            onChange={handleMaterialFileChange}
            ref={materialInputRef}
          />
          <span className="external-research-upload-status">
            {selectedMaterialNames.length > 0
              ? `已选择 ${selectedMaterialNames.length} 个文件：${selectedMaterialNames.join("、")}`
              : "点击右侧按钮可一次选择多份文件，选择后会自动上传。"}
          </span>
          <span>支持多选 PDF、DOCX、PPT、Markdown 或 TXT。</span>
        </div>
        <Button
          variant="glass-primary"
          className="max-w-full whitespace-normal"
          disabled={busy === "material-upload"}
          onClick={handleMaterialButtonClick}
          type="button"
        >
          <Upload size={17} />
          <span>{busy === "material-upload" ? "正在上传材料" : "选择并上传多份报告/补充材料"}</span>
        </Button>
        <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "material-upload"} />
      </form>
    </section>
  );
}

function buildExternalDeepResearchPrompt(project: ProjectRecord | null): string {
  const field = (label: string, value?: string | null) => `- ${label}: ${value?.trim() || "（请补充）"}`;

  return [
    "你是一名专利情报研究员。请为 PatentAgent 第 2 步“发明点确认”准备外部 Deep Research 报告。",
    "",
    "重要边界：不要写专利申请初稿，不要直接撰写权利要求。请聚焦检索、对比、区别特征、可保护发明点和证据缺口。",
    "",
    "项目上下文：",
    field("项目名称", project?.name),
    field("一句话方案", project?.draft_text),
    field("技术领域", project?.technical_field),
    field("背景技术", project?.background),
    field("技术痛点", project?.pain_point),
    field("技术方案", project?.technical_solution),
    field("已知创新点", project?.innovation),
    field("实施方式", project?.embodiments),
    field("有益效果", project?.beneficial_effects),
    "",
    "请完成以下研究：",
    "1. 检索中英文公开专利、论文、技术博客、产品文档和开源项目，列出最接近现有技术。",
    "2. 对每个相关来源提取：标题、来源类型、链接/公开号、公开日期、关键技术特征、与本方案重合点、差异点。",
    "3. 反向归纳本方案可能真正可保护的区别特征，并说明这些区别特征解决了什么技术问题、带来什么技术效果。",
    "4. 输出 3-5 个候选发明点，每个候选包含：名称、核心技术问题、关键技术特征组合、区别于现有技术的点、证据强度、风险、需要补充的实验/材料。",
    "5. 标出会削弱新颖性或创造性的最危险现有技术，并给出规避或收窄建议。",
    "",
    "请按以下 Markdown 结构输出：",
    "# 外部 Deep Research 报告",
    "## 1. 研究范围与检索式",
    "## 2. 最接近现有技术",
    "| 来源 | 标题 | 链接/公开号 | 相关特征 | 重合点 | 差异点 | 风险等级 |",
    "| --- | --- | --- | --- | --- | --- | --- |",
    "## 3. 可保护发明点候选",
    "## 4. 支撑缺口与补充材料建议",
    "## 5. 推荐给 PatentAgent 的摘要",
    "",
    "最后一节请用 300-600 字总结：哪些发明点最值得作为主线、哪些只能作为后备路线、上传给 PatentAgent 后应重点关注哪些支撑缺口。",
  ].join("\n");
}
