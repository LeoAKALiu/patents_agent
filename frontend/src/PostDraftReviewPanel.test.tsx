import { createElement } from "react";
import { render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PostDraftReviewPanel } from "./flow/panels/PostDraftReviewPanel";
import type { AgentDoctorReport, DraftPackage, OfficialCompileRun, PostDraftReviewRun, ProjectRecord } from "./api";

function provider(
  overrides: Partial<{
    id: string;
    label: string;
    command: string;
    available: boolean;
    required: boolean;
    roles: string[];
    installed: boolean;
    auth_status: string;
    selectable: boolean;
  }>,
) {
  return {
    id: overrides.id ?? "x",
    label: overrides.label ?? "X",
    command: overrides.command ?? "x",
    available: overrides.available ?? false,
    path: "",
    required: overrides.required ?? false,
    model_version: "",
    roles: overrides.roles ?? ["deliberation"],
    installed: overrides.installed ?? false,
    auth_status: (overrides.auth_status ?? "unknown") as AgentDoctorReport["commands"][string]["auth_status"],
    diagnostic: "",
    repair_suggestion: "",
    selectable: overrides.selectable ?? false,
  };
}

const deliberationDoctor: AgentDoctorReport = {
  status: "ready",
  run_mode: "full",
  active_provider_ids: ["codex", "deepseek", "kimicode", "mimo"],
  missing_required: [],
  missing_optional: [],
  unknown_required: [],
  commands: {
    codex: provider({ id: "codex", label: "Codex", command: "codex", available: true, required: true, roles: ["deliberation", "chair"], installed: true, auth_status: "ready", selectable: true }),
    deepseek: provider({ id: "deepseek", label: "DeepSeek", command: "reasonix", available: true, roles: ["deliberation"], installed: true, auth_status: "ready", selectable: true }),
    kimicode: provider({ id: "kimicode", label: "KimiCode", command: "kimicode", available: true, roles: ["deliberation"], installed: true, auth_status: "ready", selectable: true }),
    mimo: provider({ id: "mimo", label: "MimoCode", command: "mimo", available: true, roles: ["deliberation"], installed: true, auth_status: "ready", selectable: true }),
  },
};

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

const project: ProjectRecord = {
  id: "project-1",
  name: "基于城市体检指标置信度的无人机主动采集方法",
  draft_text: "",
  patent_type: "invention",
  package: draftPackage,
  created_at: "2026-06-19T00:00:00Z",
  updated_at: "2026-06-19T00:00:00Z",
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
        participantProviders: [],
        busy: "",
        busyElapsedSeconds: 0,
        onStartPostDraftReview: () => undefined,
        onStartKimiLanguagePolish: () => undefined,
        onApplySafePatches: () => undefined,
        onSaveDraftPackage: () => undefined,
        onCancelRun: () => undefined,
        onRetryRun: () => undefined,
        onToggleProvider: () => undefined,
        onToggleParticipantProvider: () => undefined,
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

  it("enables the annotated repair editor from a repairable historical review without treating it as export-current", () => {
    render(
      <PostDraftReviewPanel
        actionGate={{ allowed: true, reason: "" }}
        project={project}
        review={null}
        repairReview={blockedReview}
        runs={[blockedReview]}
        currentDraftHash="draft-hash-123456"
        currentPackage={draftPackage}
        officialCompileRun={null}
        doctor={null}
        selectedProviders={[]}
        participantProviders={[]}
        busy=""
        busyElapsedSeconds={0}
        onStartPostDraftReview={() => undefined}
        onStartKimiLanguagePolish={() => undefined}
        onApplySafePatches={() => undefined}
        onSaveDraftPackage={() => undefined}
        onCancelRun={() => undefined}
        onRetryRun={() => undefined}
        onToggleProvider={() => undefined}
        onToggleParticipantProvider={() => undefined}
      />,
    );

    const openButton = screen.getByRole("button", { name: "打开标注式修复编辑器" });
    expect((openButton as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByText("说明书包含内部注释。")).toBeTruthy();
    expect(screen.getByText(/已有历史会审记录/)).toBeTruthy();
  });

  it("uses Codex chair expert seats for post-draft review providers", () => {
    render(
      <PostDraftReviewPanel
        actionGate={{ allowed: true, reason: "" }}
        project={project}
        review={null}
        runs={[]}
        currentDraftHash="draft-hash-123456"
        currentPackage={draftPackage}
        officialCompileRun={officialCompileRun}
        doctor={deliberationDoctor}
        selectedProviders={["codex", "deepseek", "kimicode"]}
        participantProviders={["mimo"]}
        busy=""
        busyElapsedSeconds={0}
        onStartPostDraftReview={() => undefined}
        onStartKimiLanguagePolish={() => undefined}
        onApplySafePatches={() => undefined}
        onSaveDraftPackage={() => undefined}
        onCancelRun={() => undefined}
        onRetryRun={() => undefined}
        onToggleProvider={() => undefined}
        onToggleParticipantProvider={() => undefined}
      />,
    );

    expect(screen.getByRole("region", { name: "会审专家席位" })).toBeTruthy();
    expect(screen.getByText("主席 Codex 固定；另外 2 席由用户选择，参会专家仅供主席参考。")).toBeTruthy();
    expect(screen.getByText("决策专家 3/3")).toBeTruthy();
    expect(screen.getAllByText("主席固定").length).toBeGreaterThan(0);
    expect(screen.getByText("参会专家")).toBeTruthy();
  });

  it("keeps post-draft review disabled when three selected providers omit Codex chair", () => {
    render(
      <PostDraftReviewPanel
        actionGate={{ allowed: true, reason: "" }}
        project={project}
        review={null}
        runs={[]}
        currentDraftHash="draft-hash-123456"
        currentPackage={draftPackage}
        officialCompileRun={officialCompileRun}
        doctor={deliberationDoctor}
        selectedProviders={["deepseek", "kimicode", "mimo"]}
        participantProviders={[]}
        busy=""
        busyElapsedSeconds={0}
        onStartPostDraftReview={() => undefined}
        onStartKimiLanguagePolish={() => undefined}
        onApplySafePatches={() => undefined}
        onSaveDraftPackage={() => undefined}
        onCancelRun={() => undefined}
        onRetryRun={() => undefined}
        onToggleProvider={() => undefined}
        onToggleParticipantProvider={() => undefined}
      />,
    );

    const startButton = screen.getByRole("button", { name: "启动成稿会审" });
    expect((startButton as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("至少需要 Codex 主席 + 2 个可用专家才能启动成稿会审。")).toBeTruthy();
  });
});
