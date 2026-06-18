import { describe, expect, it } from "vitest";

// PR-2: Export gate unification and safe labels.
// The formal (正式提交稿) export gate must stay locked until official compile
// + post-draft review pass, and the legacy /export.* downloads must never pose
// as a formal submission draft. These guards inspect the view source because
// the app's UI regressions are pinned via source-string contracts (see
// GuidedPatentFlowView.test.ts) rather than rendered DOM.
import exportViewSource from "./views/exportView.tsx?raw";
import confirmationPanelSource from "./flow/panels/ExportConfirmationPanel.tsx?raw";

function sliceBetween(source: string, startMarker: string, endMarker: string): string {
  const start = source.indexOf(startMarker);
  expect(start, `start marker "${startMarker}" should exist in source`).toBeGreaterThanOrEqual(0);
  const end = source.indexOf(endMarker, start + startMarker.length);
  expect(end, `end marker "${endMarker}" should exist after start marker`).toBeGreaterThan(start);
  return source.slice(start, end);
}

describe("PR-2 export gate unification and safe labels", () => {
  it("routes official (formal) export controls through /official-export.* and keeps them disabled while locked", () => {
    // The official grid is the region between the formal grid marker and the
    // internal-working-draft notice that follows it.
    const officialGrid = sliceBetween(
      exportViewSource,
      'data-testid="official-export-grid"',
      'data-testid="internal-export-notice"',
    );

    // Formal DOCX/MD controls call the gated official endpoint.
    expect(officialGrid).toContain('officialExportUrl(project.id, "docx")');
    expect(officialGrid).toContain('officialExportUrl(project.id, "md")');
    // They stay disabled while the gate is locked: href only resolves once the
    // compile + post-draft review gate (officialAllowed) has passed.
    expect(officialGrid).toContain("officialAllowed && project");
    // The formal label lives only in this gated region.
    expect(officialGrid).toContain("正式提交稿 DOCX");
    expect(officialGrid).toContain("正式提交稿 MD");
    // No legacy/internal link must leak into the formal export grid.
    expect(officialGrid).not.toContain("exportUrl(");
  });

  it("labels every legacy export as 内部工作稿 and never as a formal submission draft", () => {
    const internalGrid = sliceBetween(
      exportViewSource,
      'data-testid="internal-export-grid"',
      "</SettingsGroup>",
    );

    // Legacy exports use the ungated internal endpoint.
    expect(internalGrid).toContain("exportUrl(");
    expect(internalGrid).not.toContain("officialExportUrl(");
    // Every legacy format carries the internal working-draft label. Labels are
    // rendered via the 内部工作稿 {label} template for each of the four formats.
    expect(internalGrid).toContain("内部工作稿 {label}");
    expect(internalGrid).toContain('["docx", "DOCX"]');
    expect(internalGrid).toContain('["md", "Markdown"]');
    expect(internalGrid).toContain('["mmd", "Mermaid"]');
    expect(internalGrid).toContain('["prompt", "绘图提示词"]');
    // The core invariant: a locked gate must never present the legacy export
    // under a formal submission label.
    expect(internalGrid).not.toContain("正式提交稿");
  });

  it("surfaces an explicit internal-working-draft warning above the legacy exports", () => {
    expect(exportViewSource).toContain('data-testid="internal-export-notice"');
    expect(exportViewSource).toContain("以下为内部工作稿");
    expect(exportViewSource).toContain("不可作为正式提交稿");
  });

  it("uses the unified 内部工作稿 label across every export surface", () => {
    // No surface may fall back to the older 内部策略稿 wording for exports.
    expect(exportViewSource).not.toContain("内部策略稿");
    expect(confirmationPanelSource).not.toContain("内部策略稿");
    // The confirmation panel still routes its legacy download to the internal
    // endpoint and labels it as an internal working draft.
    expect(confirmationPanelSource).toContain('exportUrl(project.id, "md")');
    expect(confirmationPanelSource).toContain("内部工作稿 MD");
  });
});
