import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
        sources: ["google_patents"],
      },
    ],
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
  candidates: [
    {
      id: "c-1",
      project_id: "p-1",
      plan_id: "plan-1",
      source: "google_patents",
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
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders candidate recommendation and include/exclude decisions", () => {
    const onRunKnowledgeSearch = vi.fn();
    const onCandidateDecision = vi.fn();

    const { container } = render(
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

    fireEvent.click(screen.getByRole("button", { name: "运行候选检索" }));
    fireEvent.click(screen.getByRole("button", { name: "纳入建库" }));
    fireEvent.click(screen.getByRole("button", { name: "排除" }));

    expect(onRunKnowledgeSearch).toHaveBeenCalled();
    expect(onCandidateDecision).toHaveBeenCalledWith("c-1", "include");
    expect(onCandidateDecision).toHaveBeenCalledWith("c-1", "exclude");
    expect(screen.queryByText("开始官方源检索")).not.toBeInTheDocument();
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
        status: "needs_supplemental_search",
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
    expect(screen.getAllByText("需要补充检索").length).toBeGreaterThan(0);
    expect(screen.queryByText("已就绪")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "确认建库" })[0]);
    expect(onBuildProjectCorpus).toHaveBeenCalled();
  });

  it("disables the primary corpus build action until a candidate is included", () => {
    const onBuildProjectCorpus = vi.fn();
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      state: {
        ...baseOverview.state,
        status: "candidates_pending",
        quality_flags: ["candidates_need_confirmation"],
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

    const primaryBuildButton = screen.getByRole("button", { name: "确认建库" });
    expect(primaryBuildButton).toBeDisabled();

    fireEvent.click(primaryBuildButton);
    expect(onBuildProjectCorpus).not.toHaveBeenCalled();
  });

  it("renders non-patent source corpus flags as warning guidance", () => {
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      state: {
        ...baseOverview.state,
        status: "needs_supplemental_search",
        quality_flags: ["non_patent_source"],
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
        onBuildProjectCorpus={vi.fn()}
      />,
    );

    expect(screen.getByText(/包含非专利来源/)).toBeInTheDocument();
    expect(screen.getByText(/不能作为项目现有技术库就绪依据/)).toBeInTheDocument();
  });

  it("renders CNIPA official export workflow instead of helper configuration", () => {
    const { container } = render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={baseOverview}
        busy=""
        cnipaQueryPack={{
          project_id: "p-1",
          plan_id: "plan-1",
          intent_id: "intent-1",
          source_id: "cnipa_official_export",
          technical_object: "城市体检智能体",
          technical_problem: "任务编排缺少可信复核",
          technical_means: "多智能体任务编排",
          keywords_zh: ["城市体检", "智能体"],
          negative_keywords: ["医疗体检"],
          ipc_candidates: ["G06Q"],
          cpc_candidates: [],
          date_range: "2016-2026",
          strategies: [{ strategy_group_id: "broad", label: "宽召回检索", purpose: "找全相关专利", queries: ["城市体检 智能体"] }],
        }}
        importLedgers={[]}
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={vi.fn()}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={vi.fn()}
        onImportCnipaExport={vi.fn()}
      />,
    );

    expect(screen.getByText("导入 CNIPA 官方导出物")).toBeInTheDocument();
    expect(screen.getByText("城市体检 智能体")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "复制 CNIPA 检索式" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "复制该策略检索式" })).toBeInTheDocument();
    expect(container.querySelector('input[type="file"]')).toHaveAttribute("accept", ".csv,.xlsx,.zip");
    expect(screen.queryByText(/CNIPA_EPUB_SEARCH_SCRIPT/)).not.toBeInTheDocument();
  });

  it("copies CNIPA query text with clipboard support and falls back to manual guidance", async () => {
    const writeText = vi.fn(async () => {});
    Object.defineProperty(globalThis.navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    const { rerender } = render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={baseOverview}
        busy=""
        cnipaQueryPack={{
          project_id: "p-1",
          plan_id: "plan-1",
          intent_id: "intent-1",
          source_id: "cnipa_official_export",
          technical_object: "城市体检智能体",
          technical_problem: "任务编排缺少可信复核",
          technical_means: "多智能体任务编排",
          keywords_zh: ["城市体检", "智能体"],
          negative_keywords: ["医疗体检"],
          ipc_candidates: ["G06Q"],
          cpc_candidates: [],
          date_range: "2016-2026",
          strategies: [
            { strategy_group_id: "broad", label: "宽召回检索", purpose: "找全相关专利", queries: ["城市体检 智能体"] },
            { strategy_group_id: "focused", label: "精准检索", purpose: "聚焦复核链路", queries: ["任务编排 复核", "证据链 智能体"] },
          ],
        }}
        importLedgers={[]}
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={vi.fn()}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={vi.fn()}
        onImportCnipaExport={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "复制 CNIPA 检索式" }));

    expect(writeText).toHaveBeenCalledWith("城市体检 智能体\n\n任务编排 复核\n\n证据链 智能体");
    expect(await screen.findByText("已复制检索式。")).toBeInTheDocument();

    writeText.mockClear();
    fireEvent.click(screen.getAllByRole("button", { name: "复制该策略检索式" })[1]);

    expect(writeText).toHaveBeenCalledWith("任务编排 复核\n\n证据链 智能体");

    Object.defineProperty(globalThis.navigator, "clipboard", {
      configurable: true,
      value: undefined,
    });

    rerender(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={baseOverview}
        busy=""
        cnipaQueryPack={{
          project_id: "p-1",
          plan_id: "plan-1",
          intent_id: "intent-1",
          source_id: "cnipa_official_export",
          technical_object: "城市体检智能体",
          technical_problem: "任务编排缺少可信复核",
          technical_means: "多智能体任务编排",
          keywords_zh: ["城市体检", "智能体"],
          negative_keywords: ["医疗体检"],
          ipc_candidates: ["G06Q"],
          cpc_candidates: [],
          date_range: "2016-2026",
          strategies: [{ strategy_group_id: "broad", label: "宽召回检索", purpose: "找全相关专利", queries: ["城市体检 智能体"] }],
        }}
        importLedgers={[]}
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={vi.fn()}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={vi.fn()}
        onImportCnipaExport={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "复制该策略检索式" }));

    expect(await screen.findByText("当前环境不支持自动复制，请手动复制下方检索式。")).toBeInTheDocument();
    expect(screen.getByText("城市体检 智能体")).toBeInTheDocument();
  });

  it("labels imported CNIPA candidates as official export", () => {
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      candidates: [{ ...baseOverview.candidates[0], source: "cnipa_official_export" }],
    };

    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={knowledge}
        busy=""
        importLedgers={[]}
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={vi.fn()}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={vi.fn()}
        onImportCnipaExport={vi.fn()}
      />,
    );

    expect(screen.getByText("CN100A · CNIPA 官方导出")).toBeInTheDocument();
  });

  it("renders real provider warnings and source badges without fake success copy", () => {
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      latest_plan: {
        ...baseOverview.latest_plan!,
        warnings: ["Google Patents returned no parseable hits for query: 城市体检"],
      },
      candidates: [
        {
          ...baseOverview.candidates[0],
          source: "google_patents",
          publication_number: "CN112233445A",
          title: "城市体检智能体调度方法",
        },
      ],
    };

    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={knowledge}
        busy=""
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={vi.fn()}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={vi.fn()}
      />,
    );

    expect(screen.getByText(/Google Patents returned no parseable hits/)).toBeInTheDocument();
    expect(screen.getByText("CN112233445A · Google Patents")).toBeInTheDocument();
    expect(screen.queryByText(/fake/)).not.toBeInTheDocument();
  });

  it("explains no-hit provider failures instead of showing the raw quality flag", () => {
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      state: {
        ...baseOverview.state,
        status: "failed",
        candidate_count: 0,
        quality_flags: ["no_hits"],
      },
      latest_plan: {
        ...baseOverview.latest_plan!,
        warnings: [
          "CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.",
          "Google Patents search failed for query 城市体检: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]>",
        ],
      },
      candidates: [],
    };

    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={knowledge}
        busy=""
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={vi.fn()}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={vi.fn()}
      />,
    );

    expect(screen.getByText(/没有形成候选文献/)).toBeInTheDocument();
    expect(screen.getByText(/检查 Google Patents 网络\/证书状态，或直接改走 CNIPA 官方导出导入路径/)).toBeInTheDocument();
    expect(screen.getByText(/CERTIFICATE_VERIFY_FAILED/)).toBeInTheDocument();
    expect(screen.queryByText(/CNIPA_EPUB_SEARCH_SCRIPT/)).not.toBeInTheDocument();
    expect(screen.queryByText("质量信号：no_hits")).not.toBeInTheDocument();
  });

  it("shows import ledger diagnostics including warnings and row failures", () => {
    render(
      <ProjectKnowledgeView
        selectedProject={project}
        knowledge={baseOverview}
        busy=""
        cnipaQueryPack={{
          project_id: "p-1",
          plan_id: "plan-1",
          intent_id: "intent-1",
          source_id: "cnipa_official_export",
          technical_object: "城市体检智能体",
          technical_problem: "任务编排缺少可信复核",
          technical_means: "多智能体任务编排",
          keywords_zh: ["城市体检", "智能体"],
          negative_keywords: ["医疗体检"],
          ipc_candidates: ["G06Q"],
          cpc_candidates: [],
          date_range: "2016-2026",
          strategies: [{ strategy_group_id: "broad", label: "宽召回检索", purpose: "找全相关专利", queries: ["城市体检 智能体"] }],
        }}
        importLedgers={[
          {
            id: "ledger-1",
            project_id: "p-1",
            plan_id: "plan-1",
            source_id: "cnipa_official_export",
            source_file_name: "cnipa-export.csv",
            raw_file_hash: "hash-1",
            detected_schema: "cnipa_csv",
            row_count: 8,
            parsed_count: 5,
            retained_candidate_ids: ["c-1"],
            warnings: ["第 3 列摘要为空，已按题录导入。"],
            failures: [
              {
                source_file_name: "cnipa-export.csv",
                row_number: 6,
                code: "missing_publication_number",
                message: "公开公告号为空。",
              },
            ],
            created_at: "2026-07-01T08:00:00Z",
          },
        ]}
        onGenerateKnowledgePlan={vi.fn()}
        onRunKnowledgeSearch={vi.fn()}
        onCandidateDecision={vi.fn()}
        onBuildProjectCorpus={vi.fn()}
        onImportCnipaExport={vi.fn()}
      />,
    );

    expect(screen.getByText("导入文件：cnipa-export.csv")).toBeInTheDocument();
    expect(screen.getByText("原始行数")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("解析候选")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("跳过/重复")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("导入提醒")).toBeInTheDocument();
    expect(screen.getByText("第 3 列摘要为空，已按题录导入。")).toBeInTheDocument();
    expect(screen.getByText("失败明细")).toBeInTheDocument();
    expect(screen.getByText("cnipa-export.csv 第 6 行")).toBeInTheDocument();
    expect(screen.getByText("missing_publication_number · 公开公告号为空。")).toBeInTheDocument();
  });

  it("renders official-export quality flags with action-oriented copy", () => {
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      state: {
        ...baseOverview.state,
        status: "needs_supplemental_search",
        quality_flags: [
          "cnipa_export_missing_provenance",
          "cnipa_export_missing_claims",
          "cnipa_export_parse_warnings",
        ],
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
        onBuildProjectCorpus={vi.fn()}
      />,
    );

    expect(screen.getByText(/缺少原始导出链路/)).toBeInTheDocument();
    expect(screen.getByText(/缺少权利要求内容/)).toBeInTheDocument();
    expect(screen.getByText(/解析提醒/)).toBeInTheDocument();
    expect(screen.queryByText("质量信号：cnipa_export_missing_claims")).not.toBeInTheDocument();
  });

  it("regenerates a fresh plan for stale knowledge states", () => {
    const onRunKnowledgeSearch = vi.fn();
    const onGenerateKnowledgePlan = vi.fn();
    const onCandidateDecision = vi.fn();
    const knowledge: ProjectKnowledgeOverview = {
      ...baseOverview,
      candidates: [
        {
          ...baseOverview.candidates[0],
          user_decision: "include",
        },
      ],
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
        onCandidateDecision={onCandidateDecision}
        onBuildProjectCorpus={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "确认建库" })).not.toBeInTheDocument();
    expect(screen.getAllByText(/需要重新生成检索计划后才能再次建库/).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "纳入建库" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "排除" })).not.toBeInTheDocument();
    expect(screen.getByText("这些候选属于旧的项目快照，当前只能只读查看。请先重新生成检索计划，再对新候选执行纳入或排除。")).toBeInTheDocument();
    expect(screen.getByText("候选已过期，请重新生成检索计划。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重新生成检索计划" }));

    expect(onGenerateKnowledgePlan).toHaveBeenCalled();
    expect(onRunKnowledgeSearch).not.toHaveBeenCalled();
    expect(onCandidateDecision).not.toHaveBeenCalled();
  });
});
