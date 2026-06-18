import { FileText, Loader2 } from "@/lib/icons";
import { Badge } from "@/components/ui/badge";
import { officialCompileReportUrl, type OfficialCompileRun, type ProjectRecord } from "@/api";
import { pipelineRunStatusLabel } from "@/domain";
import type { GuidedActionGate } from "@/guidedFlow";
import {
  ActionDock,
  InfoCard,
  SettingsGroup,
  StatusStrip,
} from "@/ui/EnterpriseSurface";
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
    <section className="grid gap-4">
      <StatusStrip
        aria-label="正式稿编译状态"
        items={[
          { label: "编译状态", value: statusText },
          { label: "当前源稿", value: currentSourceDraftHash ? currentSourceDraftHash.slice(0, 12) : "未生成" },
          { label: "正式稿", value: run?.official_package_hash ? run.official_package_hash.slice(0, 12) : "未生成" },
          { label: "历史记录", value: `${runs.length} 次` },
        ]}
      />

      <SettingsGroup
        title="正式稿编译"
        description="去除内部痕迹、支撑缺口和过程文本，生成可提交的正式稿。"
      >
        <InfoCard
          icon={<FileText size={18} aria-hidden="true" />}
          tone={completed ? "success" : blocked || run?.status === "failed" ? "danger" : "warn"}
          title={completed ? "正式稿已生成" : blocked ? "正式稿编译已阻断" : "等待生成正式稿"}
          description={
            completed
              ? "正式稿已清理内部痕迹，可进入成稿会审。"
              : blocked
                ? "请查看编译报告并处理阻断项。"
                : "生成正式稿后，成稿会审会针对该正式稿哈希放行导出。"
          }
          meta={(
            <>
              <Badge variant={statusBadgeVariant as "success" | "destructive" | "warning"} className="text-xs">{statusText}</Badge>
              {run?.official_package_hash && <span className="hash-chip">{run.official_package_hash.slice(0, 12)}</span>}
            </>
          )}
        />
      {blocked && (
        <div className="callout callout-danger">
          <FileText size={18} aria-hidden="true" />
          <div>
            <strong>当前正式稿编译已阻断</strong>
            <p>请查看编译报告并处理阻断项。</p>
          </div>
        </div>
      )}
      <ActionGateHint gate={actionGate} />
      <ActionDock meta="正式稿编译会生成新的官方稿哈希，并作为后续成稿会审的输入。">
        <button
          className="btn btn-primary"
        disabled={!actionGate.allowed || busy === "official-compile"}
        onClick={onStartOfficialCompile}
        title={actionGate.reason || undefined}
        type="button"
      >
        {busy === "official-compile" ? <Loader2 className="spin" size={17} /> : <FileText size={17} />}
        <span>{run ? "重新生成正式稿" : "生成正式稿"}</span>
        </button>
      </ActionDock>
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
      </SettingsGroup>
    </section>
  );
}
