import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CorpusWorkspace, type CorpusWorkspaceProps } from "./CorpusWorkspace";

function buildProps(): CorpusWorkspaceProps {
  return {
    tool: "build",
    state: {
      selectedProject: {
        id: "p-1",
        name: "城市体检智能体",
        draft_text: "任务编排和证据链复核。",
        patent_type: "invention",
        package: null,
        created_at: "",
        updated_at: "",
        applicant: "",
        inventors: "",
        technical_field: "",
        background: "",
        pain_point: "",
        technical_solution: "",
        innovation: "",
        embodiments: "",
        beneficial_effects: "",
      },
      projectKnowledge: {
        state: {
          project_id: "p-1",
          status: "search_plan_pending",
          active_intent_id: "intent-1",
          active_plan_id: "plan-1",
          active_corpus_version_id: "",
          last_search_at: "",
          last_indexed_at: "",
          staleness_reason: "",
          document_count: 0,
          candidate_count: 0,
          claim_coverage: 0,
          fulltext_coverage: 0,
          quality_flags: ["needs_search"],
        },
        latest_intent: {
          id: "intent-1",
          project_id: "p-1",
          source_project_hash: "hash",
          technical_object: "城市体检智能体",
          technical_problem: "任务复核不足",
          technical_means: "任务编排和证据链复核",
          technical_effect: "提高可信度",
          keywords_zh: ["城市体检"],
          keywords_en: ["urban health"],
          synonyms: [],
          negative_keywords: [],
          ipc_candidates: [],
          cpc_candidates: [],
          jurisdictions: ["CN"],
          date_range: "2016-2026",
          created_by: "agent",
          created_at: "",
        },
        latest_plan: {
          id: "plan-1",
          project_id: "p-1",
          intent_id: "intent-1",
          status: "draft",
          strategy_groups: [],
          target_sources: ["google_patents"],
          target_result_count: 20,
          filters: {},
          warnings: [],
          metadata: {},
          created_at: "",
          confirmed_at: "",
          run_started_at: "",
          run_finished_at: "",
        },
        candidates: [],
        latest_corpus_version: null,
      },
      cnipaQueryPack: {
        project_id: "p-1",
        plan_id: "plan-1",
        intent_id: "intent-1",
        source_id: "cnipa_official_export",
        technical_object: "城市体检智能体",
        technical_problem: "任务复核不足",
        technical_means: "任务编排和证据链复核",
        keywords_zh: ["城市体检"],
        negative_keywords: [],
        ipc_candidates: [],
        cpc_candidates: [],
        date_range: "2016-2026",
        strategies: [],
      },
      importLedgers: [],
      corpusJobForm: {
        source_type: "cnipa_export",
        source_name: "",
        query: "",
        domain: "ai_software",
        version_name: "ai-software-v1",
      },
      corpusJob: null,
      corpusVersions: [],
      corpusStats: null,
      documents: [],
      searchText: "",
      searchSection: "",
      searchResults: [],
      busy: "",
    },
    handlers: {
      onCorpusFormChange: vi.fn(),
      onCreateCorpusJob: vi.fn(),
      onUploadCorpusJobFile: vi.fn(),
      onRunCorpusJob: vi.fn(),
      onGenerateKnowledgePlan: vi.fn(),
      onRunKnowledgeSearch: vi.fn(),
      onCandidateDecision: vi.fn(),
      onBuildProjectCorpus: vi.fn(),
      onImportCnipaExport: vi.fn(),
      onImport: vi.fn(),
      onSearch: vi.fn(),
      onSearchText: vi.fn(),
      onSearchSection: vi.fn(),
    },
  };
}

describe("CorpusWorkspace", () => {
  it("defaults build tab to ProjectKnowledgeView and exposes the manual fallback", () => {
    render(<CorpusWorkspace {...buildProps()} />);

    expect(screen.getByText("项目现有技术库")).toBeInTheDocument();
    expect(screen.getByText("导入 CNIPA 官方导出物")).toBeInTheDocument();
    expect(screen.getByText("官方导出物批量建库")).not.toBeVisible();

    fireEvent.click(screen.getByText("从本地文件补充语料"));

    expect(screen.getByText("官方导出物批量建库")).toBeVisible();
  });
});
