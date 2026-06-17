import { FileText, Loader2 } from "@/lib/icons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { officialCompileReportUrl, type OfficialCompileRun, type ProjectRecord } from "@/api";
import { pipelineRunStatusLabel } from "@/domain";
import type { GuidedActionGate } from "@/guidedFlow";
import { GuidedOperationConsole } from "../runtimeWidgets";
import { ActionGateHint } from "../parts";

export interface OfficialCompilePanelProps {
  actionGate: GuidedActionGate;
  project: ProjectRecord | null;
  run: OfficialCompileRun | null;
  runs: OfficialCompileRun[];
  currentSourceDraftHash: string;
  busy: string;
  busyElapsedSeconds: number;
  onStartOfficialCompile: () => void;
}

export function OfficialCompilePanel({
  actionGate,
  project,
  run,
  runs,
  currentSourceDraftHash,
  busy,
  busyElapsedSeconds,
  onStartOfficialCompile,
}: OfficialCompilePanelProps) {
  const completed = Boolean(run?.status === "completed" && run.official_package);
  const blocked = Boolean(run?.status === "blocked");
  const statusText = completed ? "已完成" : blocked ? "已阻断" : run?.status === "failed" ? "失败" : "等待编译";
  const statusBadgeVariant = completed ? "success" : blocked || run?.status === "failed" ? "destructive" : "warning";

  return (
    <section className="grid gap-3.5 p-5 rounded-lg border border-app-border bg-app-surface">
      <div className="flex items-start justify-between gap-3.5">
        <div>
          <h3>正式稿编译</h3>
          <p>去除内部痕迹、支撑缺口和过程文本，生成可提交的正式稿。</p>
        </div>
        <FileText size={24} />
      </div>
      <div className="result-meta">
        <Badge variant={statusBadgeVariant as "success" | "destructive" | "warning"} className="text-xs">{statusText}</Badge>
        <span>当前源稿：{currentSourceDraftHash ? currentSourceDraftHash.slice(0, 12) : "未生成"}</span>
        {run?.official_package_hash && <span>正式稿：{run.official_package_hash.slice(0, 12)}</span>}
      </div>
      {blocked && (
        <p className="workflow-hint workflow-hint-danger">
          当前正式稿编译已阻断，请查看编译报告并处理阻断项。
        </p>
      )}
      <ActionGateHint gate={actionGate} />
      <Button
        variant="glass-primary"
        disabled={!actionGate.allowed || busy === "official-compile"}
        onClick={onStartOfficialCompile}
        title={actionGate.reason || undefined}
        type="button"
      >
        {busy === "official-compile" ? <Loader2 className="spin" size={17} /> : <FileText size={17} />}
        <span>{run ? "重新生成正式稿" : "生成正式稿"}</span>
      </Button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "official-compile"} />
      {run && (
        <article className={completed ? "guided-choice selected" : "guided-choice"}>
          <div className="result-meta">
            <Badge variant={statusBadgeVariant as "success" | "destructive" | "warning"} className="text-xs">{pipelineRunStatusLabel(run.status)}</Badge>
            <span>已清理内部痕迹 {run.contamination_removed.length} 项</span>
            <span>待处理阻断 {run.blocked_items.length} 项</span>
            {project && (
              <a href={officialCompileReportUrl(project.id, run.id)} rel="noreferrer" target="_blank">
                编译报告
              </a>
            )}
          </div>
          <h4>{completed ? "正式稿已生成" : "正式稿未放行"}</h4>
          {run.blocked_items.length > 0 && (
            <p>阻断项：{run.blocked_items.map((item) => item.message || item.category || "未命名阻断项").slice(0, 3).join("；")}</p>
          )}
        </article>
      )}
      {!run && runs.length > 0 && (
        <p className="workflow-hint">已有正式稿记录，但不属于当前源稿。请重新生成正式稿。</p>
      )}
    </section>
  );
}
