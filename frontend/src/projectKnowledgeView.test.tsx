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

const overview: ProjectKnowledgeOverview = {
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
  it("renders plan, candidates, and calls handlers", () => {
    const onRunKnowledgeSearch = vi.fn();
    const onCandidateDecision = vi.fn();

    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={overview}
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

    fireEvent.click(screen.getByRole("button", { name: "开始官方源检索" }));
    fireEvent.click(screen.getByRole("button", { name: "入库" }));

    expect(onRunKnowledgeSearch).toHaveBeenCalled();
    expect(onCandidateDecision).toHaveBeenCalledWith("c-1", "include");
  });
});
