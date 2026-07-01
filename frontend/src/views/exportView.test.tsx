import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExportView } from "./exportView";

const packageValue = {
  title: "一种输入数据处理方法",
  abstract: "摘要",
  claims: "1. 一种方法。",
  description: "说明书",
  drawing_description: "图1为流程图。",
  mermaid: "flowchart TD",
  image_prompt: "黑白线稿",
  review_findings: [],
  citations: [],
  generation_logs: [],
};

describe("ExportView quality gate copy", () => {
  it("keeps formal and internal export actions in separate sections", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={packageValue}
        postDraftReview={{
          id: "review-1",
          project_id: "p-1",
          status: "completed",
          providers: [],
          prompt_pack_version: "post-draft-v1",
          draft_package_hash: "source-hash",
          official_compile_run_id: "compile-1",
          official_package_hash: "official-hash",
          role_results: [],
          chair_result: null,
          export_allowed: true,
          blocking_issues: [],
          contamination_hits: [],
          logs: [],
          created_at: "2026-06-28T00:00:00Z",
          updated_at: "2026-06-28T00:00:00Z",
        }}
        officialCompileRun={{
          id: "compile-1",
          project_id: "p-1",
          status: "completed",
          source_draft_hash: "source-hash",
          official_package_hash: "official-hash",
          official_package: {
            title: "一种输入数据处理方法",
            abstract: "摘要",
            claims: "1. 一种方法。",
            description: "说明书",
            drawing_description: "图1为流程图。",
            figure_plan: [],
            compile_warnings: [],
            source_draft_hash: "source-hash",
            official_package_hash: "official-hash",
          },
          contamination_removed: [],
          blocked_items: [],
          sidecar_notes: [],
          logs: [],
          created_at: "2026-06-28T00:00:00Z",
          updated_at: "2026-06-28T00:00:00Z",
        }}
        exportReadiness={{
          export_allowed: true,
          draft_required: false,
          quality_required: false,
          official_compile_required: false,
          post_draft_review_required: false,
          next_action: "export_ready",
          reason: "ready",
          quality_done: true,
          compile_status: "completed",
          review_gate_status: "passed",
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={true}
        qualityCheckStates={{
          filing_readiness: "current",
          claim_defense_worksheet: "current",
          draft_completion: "current",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={true}
      />,
    );

    const officialSection = screen.getByRole("heading", { level: 3, name: "正式提交稿" }).closest("section");
    const internalSection = screen.getByRole("heading", { level: 3, name: "内部复核材料" }).closest("section");
    const riskSection = screen.getByRole("heading", { level: 3, name: "风险说明与追溯" }).closest("section");

    expect(officialSection).toBeTruthy();
    expect(internalSection).toBeTruthy();
    expect(riskSection).toBeTruthy();

    expect(within(officialSection as HTMLElement).getByText("正式提交稿 DOCX")).toBeInTheDocument();
    expect(within(officialSection as HTMLElement).getByText("正式提交稿 MD")).toBeInTheDocument();
    expect(within(officialSection as HTMLElement).getByText("原生保存 DOCX…")).toBeInTheDocument();
    expect(within(officialSection as HTMLElement).getByText("原生保存 Markdown…")).toBeInTheDocument();
    expect(within(officialSection as HTMLElement).queryByText("Mermaid")).toBeNull();

    expect(within(internalSection as HTMLElement).getByText("DOCX")).toBeInTheDocument();
    expect(within(internalSection as HTMLElement).getByText("Markdown")).toBeInTheDocument();
    expect(within(internalSection as HTMLElement).getByText("Mermaid")).toBeInTheDocument();
    expect(within(internalSection as HTMLElement).getByText("绘图提示词")).toBeInTheDocument();
    expect(within(internalSection as HTMLElement).queryByText("正式提交稿 DOCX")).toBeNull();
    expect(within(internalSection as HTMLElement).queryByText("原生保存 DOCX…")).toBeNull();

    expect(within(riskSection as HTMLElement).getByText("导出风险说明…")).toBeInTheDocument();
  });

  it("names missing and stale quality checks when official export is locked", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={packageValue}
        postDraftReview={null}
        officialCompileRun={null}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={false}
        qualityCheckStates={{
          filing_readiness: "missing",
          claim_defense_worksheet: "stale",
          draft_completion: "failed",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.getAllByText("正式提交稿").length).toBeGreaterThan(0);
    expect(screen.getAllByText("内部复核材料").length).toBeGreaterThan(0);
    expect(screen.getAllByText("风险说明与追溯").length).toBeGreaterThan(0);
    expect(screen.getByText("质量检查未完成")).toBeInTheDocument();
    expect(screen.getByText("缺少：提交前质量检查")).toBeInTheDocument();
    expect(screen.getByText("已过期：权利要求防守工作表")).toBeInTheDocument();
    expect(screen.getByText("失败：成稿完整度检查")).toBeInTheDocument();
    expect(screen.queryByText("人工修正")).toBeNull();
    expect(screen.queryByText("一键AI修正")).toBeNull();
  });

  it("names unknown-hash quality checks when official export is locked", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={packageValue}
        postDraftReview={null}
        officialCompileRun={null}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={false}
        qualityCheckStates={{
          filing_readiness: "unknown",
          claim_defense_worksheet: "unknown",
          draft_completion: "current",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.getByText("质量检查未完成")).toBeInTheDocument();
    expect(screen.getByText("来源未知：提交前质量检查、权利要求防守工作表")).toBeInTheDocument();
  });

  it("names official compile blocking evidence after quality checks pass", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={packageValue}
        postDraftReview={null}
        officialCompileRun={{
          id: "compile-1",
          project_id: "p-1",
          status: "blocked",
          source_draft_hash: "source-hash",
          official_package_hash: "",
          official_package: null,
          contamination_removed: [],
          blocked_items: [{ category: "support_gap", message: "说明书缺少实验数据" }],
          sidecar_notes: [],
          logs: [],
          created_at: "2026-06-28T00:00:00Z",
          updated_at: "2026-06-28T00:00:00Z",
        }}
        exportReadiness={{
          export_allowed: false,
          draft_required: false,
          quality_required: false,
          official_compile_required: true,
          post_draft_review_required: true,
          next_action: "run_official_compile",
          reason: "official_compile_blocked",
          quality_done: true,
          compile_status: "blocked",
          compile_blocked_items: [{ category: "support_gap", message: "说明书缺少实验数据" }],
          review_gate_status: "missing",
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={true}
        qualityCheckStates={{
          filing_readiness: "current",
          claim_defense_worksheet: "current",
          draft_completion: "current",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.getByText("正式稿编译被阻断")).toBeInTheDocument();
    expect(screen.getByText("阻断项：support_gap；说明书缺少实验数据")).toBeInTheDocument();
  });

  it("names in-flight official compile status after quality checks pass", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={packageValue}
        postDraftReview={null}
        officialCompileRun={{
          id: "compile-1",
          project_id: "p-1",
          status: "running",
          source_draft_hash: "source-hash",
          official_package_hash: "",
          official_package: null,
          contamination_removed: [],
          blocked_items: [],
          sidecar_notes: [],
          logs: [],
          created_at: "2026-06-28T00:00:00Z",
          updated_at: "2026-06-28T00:00:00Z",
        }}
        exportReadiness={{
          export_allowed: false,
          draft_required: false,
          quality_required: false,
          official_compile_required: true,
          post_draft_review_required: false,
          next_action: "run_official_compile",
          reason: "official_compile_running",
          quality_done: true,
          compile_status: "running",
          compile_run_id: "compile-1",
          has_compile_run: true,
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={true}
        qualityCheckStates={{
          filing_readiness: "current",
          claim_defense_worksheet: "current",
          draft_completion: "current",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.getByText("正式稿编译运行中")).toBeInTheDocument();
  });

  it("names post-draft review blocking evidence after official compile passes", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={packageValue}
        postDraftReview={{
          id: "review-1",
          project_id: "p-1",
          status: "completed",
          providers: [],
          prompt_pack_version: "post-draft-v1",
          draft_package_hash: "source-hash",
          official_compile_run_id: "compile-1",
          official_package_hash: "official-hash",
          role_results: [],
          chair_result: null,
          export_allowed: false,
          blocking_issues: ["权利要求1仍含内部评审说明"],
          contamination_hits: [],
          logs: [],
          created_at: "2026-06-28T00:00:00Z",
          updated_at: "2026-06-28T00:00:00Z",
        }}
        officialCompileRun={{
          id: "compile-1",
          project_id: "p-1",
          status: "completed",
          source_draft_hash: "source-hash",
          official_package_hash: "official-hash",
          official_package: {
            title: "一种输入数据处理方法",
            abstract: "摘要",
            claims: "1. 一种方法。",
            description: "说明书",
            drawing_description: "图1为流程图。",
            figure_plan: [],
            compile_warnings: [],
            source_draft_hash: "source-hash",
            official_package_hash: "official-hash",
          },
          contamination_removed: [],
          blocked_items: [],
          sidecar_notes: [],
          logs: [],
          created_at: "2026-06-28T00:00:00Z",
          updated_at: "2026-06-28T00:00:00Z",
        }}
        exportReadiness={{
          export_allowed: false,
          draft_required: false,
          quality_required: false,
          official_compile_required: false,
          post_draft_review_required: true,
          next_action: "run_post_draft_review",
          reason: "post_draft_review_blocked",
          quality_done: true,
          compile_status: "completed",
          review_gate_status: "blocked",
          review_blocking_issues: ["权利要求1仍含内部评审说明"],
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={true}
        qualityCheckStates={{
          filing_readiness: "current",
          claim_defense_worksheet: "current",
          draft_completion: "current",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.getByText("成稿会审阻断导出")).toBeInTheDocument();
    expect(screen.getByText("阻断问题：权利要求1仍含内部评审说明")).toBeInTheDocument();
  });

  it("hides the long package preview while official export is locked", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={{
          ...packageValue,
          claims: "1. 一种方法。".repeat(80),
          description: "说明书长文本。".repeat(120),
        }}
        postDraftReview={null}
        officialCompileRun={null}
        exportReadiness={{
          export_allowed: false,
          draft_required: false,
          quality_required: true,
          official_compile_required: false,
          post_draft_review_required: false,
          next_action: "run_quality_checks",
          reason: "quality_required",
          quality_done: false,
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={false}
        qualityCheckStates={{
          filing_readiness: "current",
          claim_defense_worksheet: "unknown",
          draft_completion: "unknown",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.getByText("质量检查未完成")).toBeInTheDocument();
    expect(screen.getByText("导出解锁前隐藏申请文本预览")).toBeInTheDocument();
    expect(screen.queryByText(/说明书长文本。说明书长文本。/)).toBeNull();
  });

  it("hides the long package preview when backend readiness still locks export", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={{
          ...packageValue,
          description: "说明书长文本。".repeat(120),
        }}
        postDraftReview={{
          id: "review-1",
          project_id: "p-1",
          status: "completed",
          providers: [],
          prompt_pack_version: "post-draft-v1",
          draft_package_hash: "source-hash",
          official_compile_run_id: "compile-1",
          official_package_hash: "official-hash",
          role_results: [],
          chair_result: null,
          export_allowed: true,
          blocking_issues: [],
          contamination_hits: [],
          logs: [],
          created_at: "2026-06-28T00:00:00Z",
          updated_at: "2026-06-28T00:00:00Z",
        }}
        officialCompileRun={{
          id: "compile-1",
          project_id: "p-1",
          status: "completed",
          source_draft_hash: "source-hash",
          official_package_hash: "official-hash",
          official_package: {
            title: "一种输入数据处理方法",
            abstract: "摘要",
            claims: "1. 一种方法。",
            description: "说明书",
            drawing_description: "图1为流程图。",
            figure_plan: [],
            compile_warnings: [],
            source_draft_hash: "source-hash",
            official_package_hash: "official-hash",
          },
          contamination_removed: [],
          blocked_items: [],
          sidecar_notes: [],
          logs: [],
          created_at: "2026-06-28T00:00:00Z",
          updated_at: "2026-06-28T00:00:00Z",
        }}
        exportReadiness={{
          export_allowed: false,
          draft_required: false,
          quality_required: true,
          official_compile_required: false,
          post_draft_review_required: false,
          next_action: "run_quality_checks",
          reason: "quality_required",
          quality_done: false,
          compile_status: "completed",
          review_gate_status: "passed",
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={true}
        qualityCheckStates={{
          filing_readiness: "current",
          claim_defense_worksheet: "current",
          draft_completion: "current",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.getByText("导出解锁前隐藏申请文本预览")).toBeInTheDocument();
    expect(screen.queryByText(/说明书长文本。说明书长文本。/)).toBeNull();
  });

  it("shows the package preview when backend readiness marks export ready", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={{
          ...packageValue,
          claims: "1. 一种方法。".repeat(6),
        }}
        postDraftReview={null}
        officialCompileRun={null}
        exportReadiness={{
          export_allowed: true,
          draft_required: false,
          quality_required: false,
          official_compile_required: false,
          post_draft_review_required: false,
          next_action: "export_ready",
          reason: "ready",
          quality_done: true,
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={false}
        qualityCheckStates={{
          filing_readiness: "unknown",
          claim_defense_worksheet: "unknown",
          draft_completion: "unknown",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={false}
      />,
    );

    expect(screen.queryByText("导出解锁前隐藏申请文本预览")).toBeNull();
    expect(screen.getByText(/1\. 一种方法。1\. 一种方法。/)).toBeInTheDocument();
  });

  it("unlocks formal export actions from backend readiness even when local compile state is absent", () => {
    const View = ExportView as any;

    render(
      <View
        project={{ id: "p-1", name: "输入数据处理", draft_text: "draft", package: packageValue }}
        packageValue={packageValue}
        postDraftReview={null}
        officialCompileRun={null}
        exportReadiness={{
          export_allowed: true,
          draft_required: false,
          quality_required: false,
          official_compile_required: false,
          post_draft_review_required: false,
          next_action: "export_ready",
          reason: "ready",
          quality_done: true,
          compile_status: "missing",
          official_package_hash: "official-ready-hash",
          current_source_draft_hash: "source-hash",
          review_gate_status: "passed",
        }}
        currentDraftHash="draft-hash"
        currentSourceDraftHash="source-hash"
        currentQualityChecked={false}
        qualityCheckStates={{
          filing_readiness: "unknown",
          claim_defense_worksheet: "unknown",
          draft_completion: "unknown",
        }}
        lastExport={null}
        onNativeExport={vi.fn()}
        onOpenExportFolder={vi.fn()}
        desktopDialogsAvailable={true}
      />,
    );

    expect(screen.getByText("正式稿已通过质量检查和成稿会审")).toBeInTheDocument();

    const docxLink = screen.getByRole("link", { name: "正式提交稿 DOCX" });
    const mdLink = screen.getByRole("link", { name: "正式提交稿 MD" });
    expect(docxLink).toHaveAttribute("href", "/api/projects/p-1/official-export.docx");
    expect(docxLink).toHaveAttribute("aria-disabled", "false");
    expect(mdLink).toHaveAttribute("href", "/api/projects/p-1/official-export.md");
    expect(mdLink).toHaveAttribute("aria-disabled", "false");

    expect(screen.getByRole("button", { name: "原生保存 DOCX…" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "原生保存 Markdown…" })).toBeEnabled();
  });
});
