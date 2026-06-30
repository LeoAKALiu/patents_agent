import { useEffect, useState } from "react";

import {
  CorpusWorkspace,
  type CorpusTool,
  type CorpusWorkspaceHandlers,
  type CorpusWorkspaceState,
} from "@/features/corpus/CorpusWorkspace";
import type { ExpertToolId } from "@/guidedFlow";
import { SectionHead } from "@/ui/EnterpriseSurface";

function resolveKnowledgeTool(activeExpertTool: ExpertToolId): CorpusTool {
  return activeExpertTool === "build" || activeExpertTool === "corpus"
    ? activeExpertTool
    : "build";
}

const knowledgeModes: Array<{ id: CorpusTool; label: string; description: string }> = [
  { id: "build", label: "语料库建设", description: "导入与整理可复用语料" },
  { id: "corpus", label: "知识库检索", description: "检索片段与证据来源" },
];

export interface KnowledgeWorkspaceProps {
  activeExpertTool: ExpertToolId;
  state: CorpusWorkspaceState;
  handlers: CorpusWorkspaceHandlers;
  onSelectTool?: (tool: CorpusTool) => void;
}

export function KnowledgeWorkspace({
  activeExpertTool,
  state,
  handlers,
  onSelectTool,
}: KnowledgeWorkspaceProps) {
  const [activeTool, setActiveTool] = useState<CorpusTool>(() => resolveKnowledgeTool(activeExpertTool));

  useEffect(() => {
    setActiveTool(resolveKnowledgeTool(activeExpertTool));
  }, [activeExpertTool]);

  function handleSelect(tool: CorpusTool): void {
    setActiveTool(tool);
    onSelectTool?.(tool);
  }

  return (
    <section className="workspace-stack knowledge-workspace" data-testid="knowledge-workspace">
      <SectionHead
        title="知识库"
        description="在同一工作区内完成语料沉淀与检索，不把知识库作为专家工具的附属页面。"
      />

      <section className="workspace-band">
        <div className="workspace-band-header">
          <div>
            <h3>工作模式</h3>
            <p>在语料库建设与知识库检索之间切换，沿用现有语料工具与检索行为。</p>
          </div>
        </div>

        <div className="segmented-control" role="tablist" aria-label="知识库模式">
          {knowledgeModes.map((mode) => (
            <button
              aria-selected={activeTool === mode.id}
              className={activeTool === mode.id ? "selected" : ""}
              key={mode.id}
              onClick={() => handleSelect(mode.id)}
              role="tab"
              type="button"
              title={mode.description}
            >
              {mode.label}
            </button>
          ))}
        </div>
      </section>

      <CorpusWorkspace tool={activeTool} state={state} handlers={handlers} />
    </section>
  );
}
