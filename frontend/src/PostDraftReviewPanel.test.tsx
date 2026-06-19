import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PostDraftReviewPanel } from "./flow/panels/PostDraftReviewPanel";
import type { DraftPackage, OfficialCompileRun, PostDraftReviewRun } from "./api";

const draftPackage: DraftPackage = {
  title: "一种基于城市体检指标置信度的无人机主动采集方法",
  abstract: "本发明公开一种无人机主动采集方法。",
  claims: "1. 一种方法，包括基于置信度热力图生成采集任务。",
  description: "本发明涉及无人机主动采集技术领域。",
  drawing_description: "图1为方法流程图。",
  mermaid: "",
  image_prompt: "",
  review_findings: [],
  citations: [],
  generation_logs: [],
};

const blockedReview: PostDraftReviewRun = {
  id: "review-1",
  project_id: "project-1",
  status: "completed",
  providers: ["codex", "deepseek", "claude"],
  prompt_pack_version: "post-draft-review-v1",
  draft_package_hash: "draft-hash-123456",
  official_compile_run_id: "compile-1",
  official_package_hash: "official-hash-123456",
  role_results: [
    {
      role: "claims_reviewer",
      status: "blocked",
      blocking_issues: ["权利要求含内部引导语。"],
      contamination_hits: [],
      rewrite_suggestions: ["删除内部引导语。"],
      official_safe_patches: [],
      attorney_memo: [],
    },
  ],
  chair_result: {
    status: "blocked",
    export_allowed: false,
    blocking_issues: ["说明书包含内部注释。"],
    contamination_hits: ["注：内部标记"],
    claim_1_rewrite: "",
    system_claim_rewrite: "",
    abstract_rewrite: "",
    description_rewrite_tasks: ["删除内部注释。"],
    official_safe_patches: ['{"action":"replace","target":"title","content":"干净标题"}'],
    attorney_memo: [],
    next_actions: ["重新编译正式稿"],
  },
  export_allowed: false,
  blocking_issues: ["说明书包含内部注释。", "权利要求含内部引导语。"],
  contamination_hits: ["注：内部标记"],
  logs: [],
  created_at: "2026-06-19T00:00:00Z",
  updated_at: "2026-06-19T00:00:00Z",
};

const officialCompileRun: OfficialCompileRun = {
  id: "compile-1",
  project_id: "project-1",
  status: "completed",
  source_draft_hash: "draft-hash-123456",
  official_package_hash: "official-hash-123456",
  official_package: {
    title: "一种基于城市体检指标置信度的无人机主动采集方法",
    abstract: "本发明公开一种无人机主动采集方法。",
    claims: "1. 一种方法，包括基于置信度热力图生成采集任务。",
    description: "本发明涉及无人机主动采集技术领域。",
    drawing_description: "图1为方法流程图。",
    figure_plan: [],
    compile_warnings: [],
    source_draft_hash: "draft-hash-123456",
    official_package_hash: "official-hash-123456",
  },
  contamination_removed: [],
  blocked_items: [],
  sidecar_notes: [],
  logs: [],
  created_at: "2026-06-19T00:00:00Z",
  updated_at: "2026-06-19T00:00:00Z",
};

describe("PostDraftReviewPanel repair workbench", () => {
  it("renders a scrollable repair workbench and draft editor entry", () => {
    const html = renderToStaticMarkup(
      createElement(PostDraftReviewPanel, {
        actionGate: { allowed: true, reason: "" },
        project: null,
        review: blockedReview,
        runs: [blockedReview],
        currentDraftHash: "draft-hash-123456",
        currentPackage: draftPackage,
        officialCompileRun,
        doctor: null,
        selectedProviders: [],
        busy: "",
        busyElapsedSeconds: 0,
        onStartPostDraftReview: () => undefined,
        onStartKimiLanguagePolish: () => undefined,
        onApplySafePatches: () => undefined,
        onSaveDraftPackage: () => undefined,
        onCancelRun: () => undefined,
        onRetryRun: () => undefined,
        onToggleProvider: () => undefined,
      }),
    );

    expect(html).toContain("post-review-workbench");
    expect(html).toContain("review-issue-scroll");
    expect(html).toContain("打开大编辑器");
    expect(html).toContain("人工修正");
    expect(html).toContain("一键AI修正");
    expect(html).toContain("Kimi 成稿语言润色");
    expect(html).toContain("润色会生成新的正式稿版本");
  });
});
