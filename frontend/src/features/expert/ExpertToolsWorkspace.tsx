import { classifyExpertTool } from "@/app/routes";
import {
  CorpusWorkspace,
  type CorpusTool,
  type CorpusWorkspaceHandlers,
  type CorpusWorkspaceState,
} from "@/features/corpus/CorpusWorkspace";
import {
  PostDraftWorkspace,
  type PostDraftTool,
  type PostDraftWorkspaceHandlers,
  type PostDraftWorkspaceState,
} from "@/features/postDraft/PostDraftWorkspace";
import {
  QualityWorkspace,
  type QualityTool,
  type QualityWorkspaceHandlers,
  type QualityWorkspaceState,
} from "@/features/quality/QualityWorkspace";
import type { ExpertToolId } from "@/guidedFlow";
import { SectionHead } from "@/ui/EnterpriseSurface";
import { ExpertToolChooser } from "@/views/expertViews";

export interface ExpertToolsWorkspaceProps {
  activeExpertTool: ExpertToolId;
  onSelectExpertTool: (tool: ExpertToolId) => void;
  corpusState: CorpusWorkspaceState;
  corpusHandlers: CorpusWorkspaceHandlers;
  qualityState: QualityWorkspaceState;
  qualityHandlers: QualityWorkspaceHandlers;
  postDraftState: PostDraftWorkspaceState;
  postDraftHandlers: PostDraftWorkspaceHandlers;
}

export function ExpertToolsWorkspace({
  activeExpertTool,
  onSelectExpertTool,
  corpusState,
  corpusHandlers,
  qualityState,
  qualityHandlers,
  postDraftState,
  postDraftHandlers,
}: ExpertToolsWorkspaceProps) {
  const toolGroup = classifyExpertTool(activeExpertTool);

  return (
    <section className="workspace-stack expert-tools-workspace" data-testid="expert-tools-workspace">
      <SectionHead
        title="高级工具"
        description="这里集中放置高级工具与分阶段入口，不作为默认修复或导出路径。正常流程请优先使用文稿与修复、知识库与导出工作区。"
      />

      <section className="workspace-band">
        <div className="workspace-band-header">
          <div>
            <h3>专家工具</h3>
            <p>按既有 expertToolGroups 分组展示，保留原有工具行为，但降低它们在默认工作流中的优先级。</p>
          </div>
        </div>
        <ExpertToolChooser activeToolId={activeExpertTool} onSelect={onSelectExpertTool} />
      </section>

      {toolGroup === "corpus" && (
        <CorpusWorkspace
          tool={activeExpertTool as CorpusTool}
          state={corpusState}
          handlers={corpusHandlers}
        />
      )}
      {toolGroup === "quality" && (
        <QualityWorkspace
          tool={activeExpertTool as QualityTool}
          state={qualityState}
          handlers={qualityHandlers}
        />
      )}
      {toolGroup === "post-draft" && (
        <PostDraftWorkspace
          tool={activeExpertTool as PostDraftTool}
          state={postDraftState}
          handlers={postDraftHandlers}
        />
      )}
    </section>
  );
}
