import { describe, expect, it } from "vitest";

// PR-16A/B: Official export readiness gate — UI tests.
// After the backend API exposes machine-readable readiness (reason codes +
// required_actions), the frontend ExportView and ExportConfirmationPanel must:
//   1. Show a specific locked reason when post-draft review is required
//      (NOT just a generic "waiting for review").
//   2. Provide a clear CTA to run the post-draft review.
//   3. Show the export as enabled after the review passes.
//
// These guards inspect the view source because the app's UI regressions
// are pinned via source-string contracts (same pattern as
// GuidedPatentFlowView.test.ts and exportGateSafety.test.ts).

// ── Domain logic (deriveExportReadiness) ──────────────────────────────
import {
  deriveExportReadiness,
  type DerivedExportReadiness,
} from "./domain";

describe("deriveExportReadiness unit", () => {
  it("returns draft_required when no package exists", () => {
    const r = deriveExportReadiness({
      hasPackage: false,
      officialCompileCompleted: false,
      officialCompilePresent: false,
      postDraftReviewCompleted: false,
      postDraftReviewBlocked: false,
      postDraftReviewPresent: false,
    });
    expect(r.ready).toBe(false);
    expect(r.reason).toBe("draft_required");
    expect(r.required_actions).toContain("generate_draft");
  });

  it("returns official_compile_required when compile is missing", () => {
    const r = deriveExportReadiness({
      hasPackage: true,
      officialCompileCompleted: false,
      officialCompilePresent: false,
      postDraftReviewCompleted: false,
      postDraftReviewBlocked: false,
      postDraftReviewPresent: false,
    });
    expect(r.ready).toBe(false);
    expect(r.reason).toBe("official_compile_required");
    expect(r.required_actions).toContain("run_official_compile");
  });

  it("returns post_draft_review_required when compile is done but review missing", () => {
    const r = deriveExportReadiness({
      hasPackage: true,
      officialCompileCompleted: true,
      officialCompilePresent: true,
      postDraftReviewCompleted: false,
      postDraftReviewBlocked: false,
      postDraftReviewPresent: false,
    });
    expect(r.ready).toBe(false);
    expect(r.reason).toBe("post_draft_review_required");
    expect(r.required_actions).toContain("run_post_draft_review");
    // Core regression: a clean compile MUST NOT look export-ready.
    expect(r.detail).toContain("成稿会审");
  });

  it("returns post_draft_review_blocked when review completed but not allowed", () => {
    const r = deriveExportReadiness({
      hasPackage: true,
      officialCompileCompleted: true,
      officialCompilePresent: true,
      postDraftReviewCompleted: true,
      postDraftReviewBlocked: true,
      postDraftReviewPresent: true,
    });
    expect(r.ready).toBe(false);
    expect(r.reason).toBe("post_draft_review_blocked");
    expect(r.required_actions).toContain("rerun_post_draft_review");
  });

  it("returns ready when review passed", () => {
    const r = deriveExportReadiness({
      hasPackage: true,
      officialCompileCompleted: true,
      officialCompilePresent: true,
      postDraftReviewCompleted: true,
      postDraftReviewBlocked: false,
      postDraftReviewPresent: true,
    });
    expect(r.ready).toBe(true);
    expect(r.reason).toBe("ready");
    expect(r.required_actions).toEqual([]);
    expect(r.detail).toContain("可导出");
  });
});

// ── ExportView source-string contracts ─────────────────────────────────
import exportViewSource from "./views/exportView.tsx?raw";

function sliceBetween(
  source: string,
  startMarker: string,
  endMarker: string,
): string {
  const start = source.indexOf(startMarker);
  expect(
    start,
    `start marker "${startMarker}" should exist in source`,
  ).toBeGreaterThanOrEqual(0);
  const end = source.indexOf(endMarker, start + startMarker.length);
  expect(
    end,
    `end marker "${endMarker}" should exist after start marker`,
  ).toBeGreaterThan(start);
  return source.slice(start, end);
}

describe("PR-16 ExportView official export readiness gate", () => {
  it("uses deriveExportReadiness to compute gate state", () => {
    expect(exportViewSource).toContain("deriveExportReadiness({");
  });

  it("shows a reason-specific status label instead of generic 'waiting for review'", () => {
    // The status strip must include at least three distinct gate states
    // beyond "已解锁" to prove reason-based labelling.
    expect(exportViewSource).toContain("gateStatusLabel");
    expect(exportViewSource).toContain("已解锁 — 可导出");
    expect(exportViewSource).toContain("需要成稿会审");
    expect(exportViewSource).toContain("成稿会审已阻断");
    // Generic "等待会审" only appears as a fallback, not the primary label.
  });

  it("shows a reason-specific gate title that names the exact blocker", () => {
    expect(exportViewSource).toContain("gateTitle");
    // After clean compile without review: name the required step.
    expect(exportViewSource).toContain("正式稿已编译 — 需完成成稿会审");
    // When blocked: name the block.
    expect(exportViewSource).toContain("成稿会审已阻断 — 需修订后重新会审");
    // When ready: confirm pass.
    expect(exportViewSource).toContain("正式稿已通过成稿会审");
  });

  it("provides a CTA callout when post-draft review is required", () => {
    // The "post_draft_review_required" branch must render a callout
    // with a clear next-step instruction.
    expect(exportViewSource).toContain(
      'data-testid="official-export-cta-review-required"',
    );
    const region = sliceBetween(
      exportViewSource,
      'data-testid="official-export-cta-review-required"',
      "</div>",
    );
    // CTA must name the action.
    expect(region).toContain("下一步：运行成稿会审");
    // CTA must explain concretely what to do.
    expect(region).toContain("请在流程中进入");
    expect(region).toContain("成稿会审");
  });

  it("provides a CTA callout when review is blocked", () => {
    expect(exportViewSource).toContain(
      'data-testid="official-export-cta-review-blocked"',
    );
    const region = sliceBetween(
      exportViewSource,
      'data-testid="official-export-cta-review-blocked"',
      "</div>",
    );
    expect(region).toContain("成稿会审已阻断，需要修订");
    expect(region).toContain("修改初稿后重新编译正式稿");
  });

  it("keeps the official-export dispatch links gated behind officialAllowed", () => {
    // The download hrefs must still require the strict officialAllowed
    // check (which includes hash matching) — not just readiness.ready.
    const officialGrid = sliceBetween(
      exportViewSource,
      'data-testid="official-export-grid"',
      'data-testid="internal-export-notice"',
    );
    expect(officialGrid).toContain("officialAllowed && project");
    expect(officialGrid).toContain('officialExportUrl(project.id, "docx")');
    expect(officialGrid).toContain('officialExportUrl(project.id, "md")');
  });

  it("shows the enabled state after review passes", () => {
    // The success path: gateTitle becomes "已通过成稿会审",
    // gateStatusLabel becomes "已解锁 — 可导出", and the InfoCard
    // uses tone "success".
    expect(exportViewSource).toContain("正式稿已通过成稿会审");
    expect(exportViewSource).toContain("已解锁 — 可导出");
    // The readiness reason "ready" produces the enabled detail text.
    expect(exportViewSource).toContain("可导出");
  });

  it("never shows a clean compile as export-ready without review", () => {
    // Core regression from PR-16A: the reason post_draft_review_required
    // must be rendered, proving a clean compile does not look export-ready.
    expect(exportViewSource).toContain("post_draft_review_required");
    expect(exportViewSource).toContain("正式稿已编译 — 需完成成稿会审");
  });
});

// ── ExportConfirmationPanel source-string contracts ────────────────────
import confirmationPanelSource from "./flow/panels/ExportConfirmationPanel.tsx?raw";

describe("PR-16 ExportConfirmationPanel official export readiness gate", () => {
  it("uses deriveExportReadiness for gate state", () => {
    expect(confirmationPanelSource).toContain("deriveExportReadiness({");
  });

  it("shows a reason-specific CTA when post-draft review is required", () => {
    expect(confirmationPanelSource).toContain(
      'data-testid="export-confirm-cta-review-required"',
    );
    const region = sliceBetween(
      confirmationPanelSource,
      'data-testid="export-confirm-cta-review-required"',
      "</div>",
    );
    expect(region).toContain("正式稿已编译 — 需完成成稿会审");
    expect(region).toContain("成稿会审");
  });

  it("shows a reason-specific CTA when review is blocked", () => {
    expect(confirmationPanelSource).toContain(
      'data-testid="export-confirm-cta-review-blocked"',
    );
    const region = sliceBetween(
      confirmationPanelSource,
      'data-testid="export-confirm-cta-review-blocked"',
      "</div>",
    );
    expect(region).toContain("成稿会审已阻断");
  });

  it("shows reason-specific BoundaryCard title", () => {
    // The BoundaryCard under the "official" tone must use gateTitle
    // instead of the static "正式稿".
    expect(confirmationPanelSource).toContain("gateTitle");
    expect(confirmationPanelSource).toContain("正式稿：需完成成稿会审");
    expect(confirmationPanelSource).toContain("正式稿：会审已阻断");
    expect(confirmationPanelSource).toContain("正式稿：已通过成稿会审");
  });

  it("still labels legacy exports as 内部工作稿", () => {
    // The existing safe-label invariants from PR-2 must still hold.
    expect(confirmationPanelSource).toContain('exportUrl(project.id, "md")');
    expect(confirmationPanelSource).toContain("内部工作稿 MD");
    // No "内部策略稿" regression.
    expect(confirmationPanelSource).not.toContain("内部策略稿");
  });
});
