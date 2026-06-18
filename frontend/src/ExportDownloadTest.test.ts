import { describe, expect, it } from "vitest";

import appSource from "./App.tsx?raw";
import exportViewSource from "./views/exportView.tsx?raw";
import exportConfirmationSource from "./flow/panels/ExportConfirmationPanel.tsx?raw";
import filingViewsSource from "./views/filingViews.tsx?raw";
import { safeProjectName } from "./lib/filename";

// --- Helper unit tests ---

describe("safeProjectName", () => {

  it("returns the project name unchanged when safe", () => {
    expect(safeProjectName("MyPatent")).toBe("MyPatent");
  });

  it("falls back to default when name is undefined", () => {
    expect(safeProjectName(undefined)).toBe("专利草稿");
  });

  it("falls back to default when name is null", () => {
    expect(safeProjectName(null)).toBe("专利草稿");
  });

  it("falls back to default when name is empty", () => {
    expect(safeProjectName("")).toBe("专利草稿");
  });

  it("replaces forward slash with underscore", () => {
    expect(safeProjectName("Name/with/slashes")).toBe("Name_with_slashes");
  });

  it("replaces backslash with underscore", () => {
    expect(safeProjectName("Name\\with\\backslashes")).toBe("Name_with_backslashes");
  });

  it("replaces mixed unsafe characters", () => {
    expect(safeProjectName("A:B*C?D\"E<F>G|H")).toBe("A_B_C_D_E_F_G_H");
  });

  it("trims whitespace", () => {
    expect(safeProjectName("  padded  ")).toBe("padded");
  });

  it("returns sanitized result even when all characters are replaced", () => {
    // All slashes become underscores; result is still a valid filename
    expect(safeProjectName("///")).toBe("___");
  });

  it("returns fallback when name is only whitespace after trim", () => {
    expect(safeProjectName("   ")).toBe("专利草稿");
  });
});

// --- Source guard tests ---

describe("Files import safeProjectName", () => {
  it("filingViews.tsx imports safeProjectName", () => {
    expect(filingViewsSource).toContain('import { safeProjectName } from "@/lib/filename"');
  });

  it("exportView.tsx imports safeProjectName", () => {
    expect(exportViewSource).toContain('import { safeProjectName } from "@/lib/filename"');
  });

  it("ExportConfirmationPanel.tsx imports safeProjectName", () => {
    expect(exportConfirmationSource).toContain('import { safeProjectName } from "@/lib/filename"');
  });

  it("App.tsx imports safeProjectName", () => {
    expect(appSource).toContain('import { safeProjectName } from "@/lib/filename"');
  });
});

describe("projectName defined via safeProjectName", () => {
  it("filingViews FilingReadinessView uses safeProjectName", () => {
    expect(filingViewsSource).toContain("const projectName = safeProjectName(project?.name);");
  });

  it("filingViews DraftCompletionView uses safeProjectName", () => {
    // Should appear twice — once per component
    const matches = filingViewsSource.match(/const projectName = safeProjectName\(project\?\.name\);/g);
    expect(matches).not.toBeNull();
    expect(matches!.length).toBeGreaterThanOrEqual(2);
  });

  it("exportView uses safeProjectName", () => {
    expect(exportViewSource).toContain("const projectName = safeProjectName(project?.name);");
  });

  it("ExportConfirmationPanel uses safeProjectName", () => {
    expect(exportConfirmationSource).toContain("const projectName = safeProjectName(project?.name);");
  });

  it("App triggerNativeExport uses safeProjectName", () => {
    expect(appSource).toContain("const projectName = safeProjectName(selectedProject?.name);");
  });
});

// --- Existing download attribute guards (should still pass) ---

describe("Download attributes — export surfaces", () => {
  it("ExportView last-export re-download link includes a download attribute with a safe filename", () => {
    expect(exportViewSource).toContain("download={lastExportDownloadName}");
    expect(exportViewSource).toContain("lastExportDownloadName");
  });

  it("ExportView official DOCX/MD export links include download attributes with project-name filenames", () => {
    expect(exportViewSource).toContain("正式提交稿.docx");
    expect(exportViewSource).toContain("正式提交稿.md");
    expect(exportViewSource).toContain("download={`${projectName}-正式提交稿.docx`}");
    expect(exportViewSource).toContain("download={`${projectName}-正式提交稿.md`}");
  });

  it("ExportView internal draft links (DOCX/MD/MMD/prompt) include download attributes with safe filenames", () => {
    expect(exportViewSource).toContain("filenames[kind]");
    expect(exportViewSource).toContain("download={filenames[kind]}");
    expect(exportViewSource).toContain("docx: `${projectName}.docx`");
    expect(exportViewSource).toContain("md: `${projectName}.md`");
    expect(exportViewSource).toContain("mmd: `${projectName}.mmd`");
    expect(exportViewSource).toContain("prompt: `${projectName}-绘图提示词.md`");
  });

  it("ExportConfirmationPanel download links include project-name safe filenames", () => {
    expect(exportConfirmationSource).toContain("正式提交稿.docx");
    expect(exportConfirmationSource).toContain("正式提交稿.md");
    expect(exportConfirmationSource).toContain("提交成熟度报告.md");
    expect(exportConfirmationSource).toContain("初稿完善报告.md");
  });

  it("FilingViews export links include download attributes", () => {
    expect(filingViewsSource).toContain("download={`${projectName}-正式提交稿.docx`}");
    expect(filingViewsSource).toContain("download={`${projectName}-正式提交稿.md`}");
    expect(filingViewsSource).toContain("download={`${projectName}.md`}");
    expect(filingViewsSource).toContain("download={`${projectName}-提交成熟度报告.md`}");
    expect(filingViewsSource).toContain("download={`${projectName}-初稿完善报告.md`}");
  });
});

describe("Download attributes — App.tsx native export fallback", () => {
  it("triggerNativeExport web fallback creates a download anchor instead of window.location.href", () => {
    expect(appSource).toContain("anchor.download = downloadName;");
    expect(appSource).toContain('document.createElement("a")');
    expect(appSource).toContain("anchor.click()");
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
    expect(appSource).toContain("activeExpertTool");
  });

  it("has a manual dismiss button with X icon that calls setError('') and setMessage('')", () => {
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
    expect(appSource).toContain("error || message");
  });
});

// --- Unsafe name test for the helper ---

describe("Unsafe characters in project names", () => {
  it("raw project.name is not used directly in download attributes", () => {
    // Should use safeProjectName helper, not raw project?.name
    expect(filingViewsSource).not.toContain("const projectName = project?.name");
    expect(filingViewsSource).not.toContain("const projectName = project.name");

    expect(exportViewSource).not.toContain("const projectName = project?.name");

    expect(exportConfirmationSource).not.toContain("const projectName = project.name");
  });

  it("download attributes still reference projectName variable (post-sanitization)", () => {
    // The download= attributes should still use the sanitized projectName var
    expect(filingViewsSource).toContain("download={`${projectName}");
    expect(exportViewSource).toContain("download={`${projectName}");
    expect(exportConfirmationSource).toContain("download={`${projectName}");
  });
});
