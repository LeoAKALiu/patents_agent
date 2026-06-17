/**
 * DraftGenerationPanel — guided step "生成初稿".
 *
 * Extracted from GuidedPatentFlow.tsx (M4) as the first step-panel module to
 * establish the panel-extraction pattern: explicit props only (no closure over
 * GuidedPatentFlowView), shared runtime widgets imported from ../runtimeWidgets,
 * icons from @/lib/icons, types from @/api. The remaining step panels follow
 * the same shape.
 */
import { FileText, Loader2, Wand2 } from "@/lib/icons";
import { Button } from "@/components/ui/button";
import type {
  DeliberationRun,
  DisclosureRun,
  FormulaNeedAssessment,
  FormulaRun,
  ProjectRecord,
} from "@/api";
import { GuidedOperationConsole } from "../runtimeWidgets";

export interface DraftGenerationPanelProps {
  project: ProjectRecord | null;
  disclosure: DisclosureRun | null;
  deliberation: DeliberationRun | null;
  formulaRequirement: FormulaNeedAssessment | null;
  formulaRun: FormulaRun | null;
  busy: string;
  busyElapsedSeconds: number;
  onGenerateDraft: () => void;
}

export function DraftGenerationPanel({
  project,
  disclosure,
  deliberation,
  formulaRequirement,
  formulaRun,
  busy,
  busyElapsedSeconds,
  onGenerateDraft,
}: DraftGenerationPanelProps) {
  const formulaReady = !formulaRequirement?.required || Boolean(formulaRun?.package);
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
        </div>
        <FileText size={24} />
      </div>
      <Button variant="glass-primary" disabled={!project || !deliberation || !formulaReady || busy === "generate"} onClick={onGenerateDraft} type="button">
        {busy === "generate" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
        <span>生成初稿</span>
      </Button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "generate"} />
      {project?.package && <pre className="guided-preview">{project.package.claims.slice(0, 1200)}</pre>}
    </section>
  );
}
