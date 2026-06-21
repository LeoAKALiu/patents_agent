import { ClipboardList, Loader2, ShieldCheck, Upload, Wand2 } from "@/lib/icons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  DisclosureRun,
  PatentPointCandidate,
  ProjectMaterial,
} from "@/api";
import { patentPointCandidatesFromDisclosureRun, evidenceStatusText } from "../inventionSelectors";
import {
  GuidedOperationConsole,
  GuidedRuntimeActions,
  GuidedRuntimeConsole,
  GuidedRuntimeFailures,
  guidedActiveRun,
} from "../runtimeWidgets";
import { MaterialSummary } from "./MaterialSummary";
import type { ExpertToolOpener } from "../parts";

export type DisclosureResearchMode = "standard" | "free_deep_research";

export interface InventionPointConfirmationProps {
  disclosure: DisclosureRun | null;
  disclosureRuns: DisclosureRun[];
  materials: ProjectMaterial[];
  patentPoints: PatentPointCandidate[];
  busy: string;
  busyElapsedSeconds: number;
  researchMode: DisclosureResearchMode;
  onChangeResearchMode: (mode: DisclosureResearchMode) => void;
  onUploadMaterial: (event: React.FormEvent<HTMLFormElement>) => void;
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
      <div className="guided-panel-actions">
        <Button className="guided-panel-action" variant="glass-soft" size="sm" onClick={() => onOpenExpertTool("materials")} type="button">
          <ClipboardList size={16} aria-hidden="true" />
          <span>查看前置材料详情</span>
        </Button>
        <Button className="guided-panel-action" variant="glass-soft" size="sm" onClick={() => onOpenExpertTool("moat")} type="button">
          <ShieldCheck size={16} aria-hidden="true" />
          <span>查看护城河地图</span>
        </Button>
      </div>
      <form className="guided-upload" onSubmit={onUploadMaterial}>
        <input
          id="project-material-file-invention"
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
      <MaterialSummary materials={materials} />
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
            <Button variant="glass-soft" size="icon" onClick={() => onSelectPatentPoint(point, candidates)} type="button">
              选为主线并保存后备路线
            </Button>
          </article>
        ))}
        {candidates.length === 0 && <p className="empty">点击“提炼发明点”后显示候选主线。</p>}
      </div>
    </section>
  );
}
