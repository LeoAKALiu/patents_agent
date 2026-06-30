import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GrantabilityReport, ProjectKnowledgeOverview, ProjectRecord } from "@/api";

import { GrantabilityView } from "./qualityViews";

const project: ProjectRecord = {
  id: "p-1",
  name: "授权前景项目",
  draft_text: "一种声学视觉融合巡检方法。",
  patent_type: "invention",
  package: {
    title: "声学视觉融合巡检方法",
    abstract: "通过声学异常窗口触发视觉局部复检。",
    claims: "1. 一种巡检方法。",
    description: "说明书",
    drawing_description: "",
    mermaid: "",
    image_prompt: "",
    review_findings: [],
    citations: [],
    generation_logs: [],
  },
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

const report: GrantabilityReport = {
  id: "report-1",
  project_id: "p-1",
  status: "uncertain",
  overall_assessment: "现有技术证据不足，无法给出授权前景结论。",
  closest_prior_art_summary: "CN100A",
  claim_chart: [],
  novelty_attacks: [],
  inventive_step_attacks: [],
  risk_summary: {},
  low_evidence_flags: ["项目语料库仅含合成或占位内容，不能支撑授权前景结论。"],
  fail_closed: true,
  recommendation: "补充检索。",
  source_ledger_citations: [],
  created_at: "2026-06-29T10:00:00Z",
};

describe("GrantabilityView knowledge gate copy", () => {
  it("keeps synthetic-only corpus in a gated state", () => {
    const knowledge: ProjectKnowledgeOverview = {
      state: {
        project_id: "p-1",
        status: "needs_supplemental_search",
        active_intent_id: "",
        active_plan_id: "",
        active_corpus_version_id: "version-1",
        last_search_at: "",
        last_indexed_at: "",
        staleness_reason: "",
        document_count: 2,
        candidate_count: 2,
        claim_coverage: 1,
        fulltext_coverage: 1,
        quality_flags: ["synthetic_evidence"],
      },
      latest_intent: null,
      latest_plan: null,
      candidates: [],
      latest_corpus_version: null,
    };

    render(
      <GrantabilityView
        project={project}
        projectKnowledge={knowledge}
        report={report}
        reports={[report]}
        busy=""
        onGenerate={vi.fn()}
      />,
    );

    expect(screen.getByText(/项目语料库仍受证据门控/)).toBeInTheDocument();
    expect(screen.getByText(/质量标记：synthetic_evidence/)).toBeInTheDocument();
    expect(screen.queryByText(/项目语料库已就绪：已入库 2 件文献/)).not.toBeInTheDocument();
  });

  it("shows analysis-ready copy only when ready, non-blocked, and at least two documents", () => {
    const knowledge: ProjectKnowledgeOverview = {
      state: {
        project_id: "p-1",
        status: "ready",
        active_intent_id: "",
        active_plan_id: "",
        active_corpus_version_id: "version-1",
        last_search_at: "",
        last_indexed_at: "",
        staleness_reason: "",
        document_count: 3,
        candidate_count: 3,
        claim_coverage: 1,
        fulltext_coverage: 1,
        quality_flags: [],
      },
      latest_intent: null,
      latest_plan: null,
      candidates: [],
      latest_corpus_version: null,
    };

    render(
      <GrantabilityView
        project={project}
        projectKnowledge={knowledge}
        report={null}
        reports={[]}
        busy=""
        onGenerate={vi.fn()}
      />,
    );

    expect(screen.getByText("项目语料库已就绪：已入库 3 件文献，可用于授权前景分析。")).toBeInTheDocument();
  });
});
