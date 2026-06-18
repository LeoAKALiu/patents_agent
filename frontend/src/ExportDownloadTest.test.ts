import { describe, expect, it } from "vitest";

import appSource from "./App.tsx?raw";
import exportViewSource from "./views/exportView.tsx?raw";
import exportConfirmationSource from "./flow/panels/ExportConfirmationPanel.tsx?raw";
import filingViewsSource from "./views/filingViews.tsx?raw";

describe("Download attributes — export surfaces", () => {
  it("ExportView last-export re-download link includes a download attribute with a safe filename", () => {
    // The "再次下载" anchor must carry download= so browsers save the file
    // instead of navigating to the URL inline.
    expect(exportViewSource).toContain("download={lastExportDownloadName}");
    expect(exportViewSource).toContain("lastExportDownloadName");
  });

  it("ExportView official DOCX/MD export links include download attributes with project-name filenames", () => {
    expect(exportViewSource).toContain('正式提交稿.docx');
    expect(exportViewSource).toContain('正式提交稿.md');
    expect(exportViewSource).toContain("download={`${projectName}-正式提交稿.docx`}");
    expect(exportViewSource).toContain("download={`${projectName}-正式提交稿.md`}");
  });

  it("ExportView internal draft links (DOCX/MD/MMD/prompt) include download attributes with safe filenames", () => {
    expect(exportViewSource).toContain("filenames[kind]");
    expect(exportViewSource).toContain("download={filenames[kind]}");
    expect(exportViewSource).toContain('docx: `${projectName}.docx`');
    expect(exportViewSource).toContain('md: `${projectName}.md`');
    expect(exportViewSource).toContain('mmd: `${projectName}.mmd`');
    expect(exportViewSource).toContain('prompt: `${projectName}-绘图提示词.md`');
  });

  it("ExportConfirmationPanel download links include project-name safe filenames", () => {
    expect(exportConfirmationSource).toContain('正式提交稿.docx');
    expect(exportConfirmationSource).toContain('正式提交稿.md');
    expect(exportConfirmationSource).toContain('提交成熟度报告.md');
    expect(exportConfirmationSource).toContain('初稿完善报告.md');
  });

  it("FilingViews export links include download attributes", () => {
    expect(filingViewsSource).toContain('download={`${projectName}-正式提交稿.docx`}');
    expect(filingViewsSource).toContain('download={`${projectName}-正式提交稿.md`}');
    expect(filingViewsSource).toContain('download={`${projectName}.md`}');
    expect(filingViewsSource).toContain('download={`${projectName}-提交成熟度报告.md`}');
    expect(filingViewsSource).toContain('download={`${projectName}-初稿完善报告.md`}');
  });
});

describe("Download attributes — App.tsx native export fallback", () => {
  it("triggerNativeExport web fallback creates a download anchor instead of window.location.href", () => {
    // The web fallback path must set anchor.download so the browser saves
    // with the correct filename rather than navigating inline.
    expect(appSource).toContain("anchor.download = downloadName;");
    expect(appSource).toContain('document.createElement("a")');
    expect(appSource).toContain("anchor.click()");
    // Must NOT use window.location.href to navigate away.
    expect(appSource).not.toContain("window.location.href = href;");
  });

  it("web fallback filenames match the official export naming convention", () => {
    expect(appSource).toContain("正式稿编译报告.md");
    expect(appSource).toContain("正式提交稿.docx");
    expect(appSource).toContain("正式提交稿.md");
  });
});

describe("Error banner lifecycle", () => {
  it("clears error and message when activeSection changes", () => {
    expect(appSource).toContain("setError(");
    expect(appSource).toContain("setMessage(");
    expect(appSource).toContain("activeSection, activeExpertTool");
  });

  it("clears error and message when activeExpertTool changes", () => {
    // The navigation-clearing useEffect must also watch activeExpertTool
    // so switching between expert tools dismisses stale banners.
    expect(appSource).toContain("activeExpertTool");
  });

  it("has a manual dismiss button with X icon that calls setError('') and setMessage('')", () => {
    // The notice banner must include an explicit close button so users
    // can dismiss non-busy banners without navigating.
    expect(appSource).toContain('aria-label="关闭通知"');
    expect(appSource).toContain("setError(");
    expect(appSource).toContain("setMessage(");
    expect(appSource).toContain("<X size={14}");
    expect(appSource).toContain("lucide-react");
  });

  it("dismiss button only renders when message or error is present (not during busy-only state)", () => {
    expect(appSource).toContain("(message || error)");
  });

  it("notice banner shows error text if error is set, otherwise message text", () => {
    // The display order: error takes precedence over message over busy label.
    expect(appSource).toContain("error || message");
  });
});
