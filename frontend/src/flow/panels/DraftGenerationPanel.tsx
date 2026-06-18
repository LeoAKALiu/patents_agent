/**
 * DraftGenerationPanel — guided step "生成初稿".
 *
 * Extracted from GuidedPatentFlow.tsx (M4) as the first step-panel module to
 * establish the panel-extraction pattern: explicit props only (no closure over
 * GuidedPatentFlowView), shared runtime widgets imported from ../runtimeWidgets,
 * icons from @/lib/icons, types from @/api. The remaining step panels follow
 * the same shape.
 *
 * PR-11B: extended with generate-run polling support — the panel now accepts
 * GenerateRun[] and shows live status (queued/running/completed/failed) via the
 * shared GuidedRuntimeConsole/Actions widgets, with cancel/retry wired through.
 */
import { FileText, Loader2, Wand2 } from "@/lib/icons";
import { Button } from "@/components/ui/button";
import type {
  DeliberationRun,
  DisclosureRun,
  FormulaNeedAssessment,
  FormulaRun,
  GenerateRun,
  ProjectRecord,
} from "@/api";
import {
  GuidedOperationConsole,
  GuidedRuntimeActions,
  GuidedRuntimeConsole,
  GuidedRuntimeFailures,
  guidedActiveRun,
  guidedRuntimeStageLabel,
} from "../runtimeWidgets";
import { pipelineRunStatusLabel } from "@/domain";

export interface DraftGenerationPanelProps {
  project: ProjectRecord | null;
  disclosure: DisclosureRun | null;
  deliberation: DeliberationRun | null;
  formulaRequirement: FormulaNeedAssessment | null;
  formulaRun: FormulaRun | null;
  generateRuns: GenerateRun[];
  busy: string;
  busyElapsedSeconds: number;
  onGenerateDraft: () => void;
  onCancelGenerateRun: (runId: string) => void;
  onRetryGenerateRun: (runId: string) => void;
}

export function DraftGenerationPanel({
  project,
  disclosure,
  deliberation,
  formulaRequirement,
  formulaRun,
  generateRuns,
  busy,
  busyElapsedSeconds,
  onGenerateDraft,
  onCancelGenerateRun,
  onRetryGenerateRun,
}: DraftGenerationPanelProps) {
  const formulaReady = !formulaRequirement?.required || Boolean(formulaRun?.package);
  const activeRun = guidedActiveRun(generateRuns);
  const latestTerminalRun = generateRuns.find(
    (run) => run.status === "completed" || run.status === "failed" || run.status === "interrupted",
  ) ?? null;
  const isBusy = busy === "generate";
  const isGenerateDisabled = !project || !deliberation || !formulaReady || isBusy || Boolean(activeRun);

  const statusSummary = activeRun
    ? `生成运行 ${pipelineRunStatusLabel(activeRun.status)}`
    : latestTerminalRun
      ? `上一次运行：${pipelineRunStatusLabel(latestTerminalRun.status)}`
      : null;

  return (
    <section className="grid gap-3.5 p-5 rounded-lg border border-app-border bg-app-surface">
      <div className="flex items-start justify-between gap-3.5">
        <div>
          <h3>生成专利初稿</h3>
          <p>
            {deliberation
              ? "将结合会审结论生成。"
              : disclosure
                ? "将结合交底书生成。"
                : "将基于当前想法和已确认的发明点生成。"}
          </p>
          <p>{formulaRun ? "已注入核心公式。" : formulaRequirement?.required ? "等待核心公式。" : "本项目无需核心公式。"}</p>
          {statusSummary && <p>{statusSummary}</p>}
        </div>
        <FileText size={24} />
      </div>

      {/* Generate button — disabled while busy or an active run exists */}
      <Button
        variant="glass-primary"
        disabled={isGenerateDisabled}
        onClick={onGenerateDraft}
        type="button"
      >
        {isBusy ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
        <span>{activeRun ? "运行中..." : "生成初稿"}</span>
      </Button>

      {/* Busy operation console (legacy pattern, shown during withStatus("generate")) */}
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={isBusy} />

      {/* Live runtime console for the active/queued/terminal generate run */}
      {activeRun && (
        <GuidedRuntimeConsole
          run={activeRun}
          label="生成运行"
          busy={busy}
          onCancel={onCancelGenerateRun}
        />
      )}

      {/* Cancel/retry actions for active or retryable runs */}
      <GuidedRuntimeActions
        run={activeRun ?? latestTerminalRun}
        disabled={Boolean(busy)}
        onCancel={onCancelGenerateRun}
        onRetry={onRetryGenerateRun}
      />

      {/* Failure details for terminal failed/interrupted runs */}
      {latestTerminalRun && (
        <GuidedRuntimeFailures run={latestTerminalRun} />
      )}

      {/* Show the generated draft package preview */}
      {project?.package && (
        <pre className="guided-preview">{project.package.claims.slice(0, 1200)}</pre>
      )}
    </section>
  );
}
