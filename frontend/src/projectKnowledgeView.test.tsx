import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ProjectKnowledgeOverview, ProjectRecord } from "./api";
import { ProjectKnowledgeView } from "./views/projectKnowledgeView";

const project: ProjectRecord = {
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
};

const baseOverview: ProjectKnowledgeOverview = {
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
    candidate_count: 1,
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
    keywords_zh: ["城市体检", "智能体", "任务编排"],
    keywords_en: ["urban health", "agent"],
    synonyms: ["城市诊断"],
    negative_keywords: ["医疗体检"],
    ipc_candidates: ["G06Q"],
    cpc_candidates: ["G06Q10/063"],
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
    strategy_groups: [
      {
        id: "broad-recall",
        label: "宽召回检索",
        purpose: "尽量找全相关专利",
        queries: ["城市体检 智能体 任务编排"],
        sources: ["fake"],
      },
    ],
    target_sources: ["fake"],
    target_result_count: 20,
    filters: {},
    warnings: [],
    created_at: "",
    confirmed_at: "",
    run_started_at: "",
    run_finished_at: "",
  },
  candidates: [
    {
      id: "c-1",
      project_id: "p-1",
      plan_id: "plan-1",
      source: "fake",
      title: "一种城市体检任务编排方法",
      publication_number: "CN100A",
      application_number: null,
      applicant: "示例申请人",
      publication_date: "2024-01-01",
      grant_date: "",
      abstract: "公开了城市体检任务编排。",
      url: "https://patents.google.com/patent/CN100A",
      relevance_score: 0.87,
      matched_terms: ["城市体检"],
      ipc: [],
      cpc: [],
      family_id: "",
      duplicate_of: "",
      fulltext_status: "available",
      recommended_action: "include",
      recommendation_reason: "命中核心技术对象",
      user_decision: "pending",
      metadata: {},
      created_at: "",
    },
  ],
  latest_corpus_version: null,
};

describe("ProjectKnowledgeView", () => {
  it("renders candidate recommendation and include/exclude decisions", () => {
    const onRunKnowledgeSearch = vi.fn();
    const onCandidateDecision = vi.fn();

    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={baseOverview}
        busy=""
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={onRunKnowledgeSearch}
        onCandidateDecision={onCandidateDecision}
        onBuildProjectCorpus={vi.fn()}
      />,
    );

    expect(screen.getByText("项目现有技术库")).toBeInTheDocument();
    expect(screen.getByText("检索计划待确认")).toBeInTheDocument();
    expect(screen.getByText("宽召回检索")).toBeInTheDocument();
    expect(screen.getByText("一种城市体检任务编排方法")).toBeInTheDocument();
    expect(screen.getByText("Agent 建议纳入")).toBeInTheDocument();
    expect(screen.getByText("待人工决策")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "开始官方源检索" }));
    fireEvent.click(screen.getByRole("button", { name: "纳入建库" }));
    fireEvent.click(screen.getByRole("button", { name: "排除" }));

    expect(onRunKnowledgeSearch).toHaveBeenCalled();
    expect(onCandidateDecision).toHaveBeenCalledWith("c-1", "include");
    expect(onCandidateDecision).toHaveBeenCalledWith("c-1", "exclude");
  });

  it("renders fail-closed quality guidance and builds corpus from included candidates", () => {
    const onBuildProjectCorpus = vi.fn();
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      state: {
        ...baseOverview.state,
        status: "needs_supplemental_search",
        active_corpus_version_id: "version-1",
        staleness_reason: "项目技术描述已变化，需要重新生成检索计划或补充检索。",
        document_count: 1,
        claim_coverage: 0,
        fulltext_coverage: 0,
        quality_flags: ["synthetic_evidence", "stale_project_snapshot", "empty_corpus"],
      },
      candidates: [
        {
          ...baseOverview.candidates[0],
          user_decision: "include",
        },
      ],
      latest_corpus_version: {
        id: "version-1",
        project_id: "p-1",
        name: "p-1-prior-art-v1",
        source_plan_id: "plan-1",
        candidate_set_id: "",
        status: "failed",
        document_count: 1,
        chunk_count: 3,
        claim_coverage: 0,
        fulltext_coverage: 0,
        quality_report: {
          total_files: 1,
          processed_files: 1,
          imported_documents: 1,
          duplicate_documents: 0,
          filtered_documents: 0,
          failed_documents: 1,
          indexed_chunks: 3,
          fulltext_extractable_rate: 0,
          section_coverage: { claims: 0, fulltext: 0 },
          low_quality_documents: ["c-1"],
          failures: [
            {
              code: "synthetic_evidence",
              message: "Corpus built from synthetic fake-source candidates only.",
            },
          ],
        },
        created_at: "2026-06-29T10:00:00Z",
        superseded_by: "",
      },
    };

    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={knowledge}
        busy=""
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={vi.fn()}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={onBuildProjectCorpus}
      />,
    );

    expect(screen.getAllByText(/授权判断仍然受证据门控/).length).toBeGreaterThan(0);
    expect(screen.getByText(/不能视为真实检索结论/)).toBeInTheDocument();
    expect(screen.getByText(/项目技术描述已变化/)).toBeInTheDocument();
    expect(screen.getByText("质量报告")).toBeInTheDocument();
    expect(screen.getByText("synthetic_evidence")).toBeInTheDocument();
    expect(screen.getByText("Corpus built from synthetic fake-source candidates only.")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "确认建库" })[0]);
    expect(onBuildProjectCorpus).toHaveBeenCalled();
  });

  it("reruns the latest plan for stale ready states instead of advertising a no-op plan generation", () => {
    const onRunKnowledgeSearch = vi.fn();
    const onGenerateKnowledgePlan = vi.fn();
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      state: {
        ...baseOverview.state,
        status: "stale",
        quality_flags: ["stale_project_snapshot"],
      },
    };

    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={knowledge}
        busy=""
        onGenerateKnowledgePlan={onGenerateKnowledgePlan}
        onRunKnowledgeSearch={onRunKnowledgeSearch}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "重新运行最新检索计划" }));

    expect(onRunKnowledgeSearch).toHaveBeenCalled();
    expect(onGenerateKnowledgePlan).not.toHaveBeenCalled();
  });
});
