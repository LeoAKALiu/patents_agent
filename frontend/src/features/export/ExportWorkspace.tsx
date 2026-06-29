import { ArrowRight, FileSearch, FolderOpen } from "lucide-react";
import type { ExportReadiness } from "@/api";
import {
  type PostDraftWorkspaceHandlers,
  type PostDraftWorkspaceState,
} from "@/features/postDraft/PostDraftWorkspace";
import { SectionHead } from "@/ui/EnterpriseSurface";
import { ExportView } from "@/views/exportView";

type DocumentsTarget = "overview" | "annotated";

const sectionCards = [
  {
    title: "正式提交稿",
    description: "面向正式提交的 DOCX 与 Markdown，继续由正式稿编译和成稿会审门禁控制。",
  },
  {
    title: "内部复核材料",
    description: "保留内部判断与复核上下文，便于团队继续检查，但不进入正式提交稿。",
  },
  {
    title: "风险说明与追溯",
    description: "集中呈现阻断原因、污染提示、哈希与导出记录，方便回到文稿修复链路。",
  },
];

function exportLocked(readiness: ExportReadiness | null | undefined): boolean {
  if (!readiness) return true;
  return !readiness.export_allowed;
}

export interface ExportWorkspaceProps {
  postDraftState: PostDraftWorkspaceState;
  postDraftHandlers: PostDraftWorkspaceHandlers;
  onNavigateDocuments: (target: DocumentsTarget) => void;
}

export function ExportWorkspace({
  postDraftState,
  postDraftHandlers,
  onNavigateDocuments,
}: ExportWorkspaceProps) {
  const locked = exportLocked(postDraftState.exportReadiness);

  return (
    <section className="workspace-stack export-workspace" data-testid="export-workspace">
      <SectionHead
        title="导出"
        description="把正式提交稿、内部复核材料与风险追溯拆开呈现，避免导出区承载修复操作。"
      />

      <div className="workspace-card-grid" aria-label="导出工作区分区">
        {sectionCards.map((card) => (
          <article className="workspace-overview-card" key={card.title}>
            <strong>{card.title}</strong>
            <p>{card.description}</p>
          </article>
        ))}
      </div>

      {locked && (
        <section className="workspace-band export-guidance" aria-label="导出锁定指引">
          <div className="workspace-band-header">
            <div>
              <h3>导出仍被锁定</h3>
              <p>请回到文稿与修复处理门禁或阻断问题；导出区只呈现文件与追溯信息，不承载正文修复面板。</p>
            </div>
          </div>
          <div className="workspace-action-row">
            <button className="btn btn-secondary" onClick={() => onNavigateDocuments("overview")} type="button">
              <FolderOpen size={16} aria-hidden="true" />
              <span>返回文稿与修复 / 总览</span>
            </button>
            <button className="btn btn-secondary" onClick={() => onNavigateDocuments("annotated")} type="button">
              <FileSearch size={16} aria-hidden="true" />
              <span>查看文稿与修复 / 标注修复</span>
            </button>
            <span className="workspace-inline-meta">
              进入文稿与修复后，可在对应标签中继续处理问题。
              <ArrowRight size={14} aria-hidden="true" />
            </span>
          </div>
        </section>
      )}

      <ExportView
        project={postDraftState.selectedProject}
        packageValue={postDraftState.currentPackage}
        postDraftReview={postDraftState.latestPostDraftReview}
        officialCompileRun={postDraftState.latestOfficialCompileRun}
        exportReadiness={postDraftState.exportReadiness}
        currentDraftHash={postDraftState.currentDraftHash}
        currentSourceDraftHash={postDraftState.currentSourceDraftHash}
        currentQualityChecked={postDraftState.currentQualityChecked}
        qualityCheckStates={postDraftState.qualityCheckStates}
        lastExport={postDraftState.lastExport}
        onNativeExport={(format) => void postDraftHandlers.onNativeExport(format)}
        onOpenExportFolder={() => void postDraftHandlers.onOpenExportFolder()}
        desktopDialogsAvailable={postDraftState.desktopDialogsAvailable}
      />
    </section>
  );
}
