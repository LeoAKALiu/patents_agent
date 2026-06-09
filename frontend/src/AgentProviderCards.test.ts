import { describe, expect, it } from "vitest";

import { normalizeAgentSelection, providerListForRole } from "./AgentProviderCards";
import type { AgentDoctorReport } from "./api";

// Helper to build a provider status with the new required fields.
function p(
  overrides: Partial<{
    id: string;
    label: string;
    command: string;
    available: boolean;
    path: string;
    required: boolean;
    model_version: string;
    roles: string[];
    installed: boolean;
    auth_status: string;
    diagnostic: string;
    repair_suggestion: string;
    selectable: boolean;
  }>,
) {
  return {
    id: overrides.id ?? "x",
    label: overrides.label ?? "X",
    command: overrides.command ?? "x",
    available: overrides.available ?? false,
    path: overrides.path ?? "",
    required: overrides.required ?? false,
    model_version: overrides.model_version ?? "",
    roles: overrides.roles ?? [],
    installed: overrides.installed ?? false,
    auth_status: (overrides.auth_status ?? "unknown") as AgentDoctorReport["commands"][string]["auth_status"],
    diagnostic: overrides.diagnostic ?? "",
    repair_suggestion: overrides.repair_suggestion ?? "",
    selectable: overrides.selectable ?? false,
  };
}

const doctor: AgentDoctorReport = {
  status: "ready",
  run_mode: "full",
  active_provider_ids: ["codex", "gemini", "claude", "kimicode"],
  missing_required: [],
  missing_optional: ["deepseek_pi"],
  unknown_required: [],
  commands: {
    codex: p({ id: "codex", label: "Codex", command: "codex", available: true, path: "/bin/codex", required: true, model_version: "codex-cli default", roles: ["deliberation", "formula", "chair"], installed: true, auth_status: "ready", selectable: true }),
    gemini: p({ id: "gemini", label: "Gemini", command: "gemini", available: true, path: "/bin/gemini", required: true, model_version: "gemini-cli default", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "ready", selectable: true }),
    claude: p({ id: "claude", label: "Claude", command: "claude", available: true, path: "/bin/claude", required: true, model_version: "claude-code default", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "ready", selectable: true }),
    kimicode: p({ id: "kimicode", label: "KimiCode", command: "kimicode", available: true, path: "/bin/kimicode", required: false, model_version: "kimi-code local", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "ready", selectable: true }),
    deepseek_pi: p({ id: "deepseek_pi", label: "DeepSeek + PI", command: "deepseek-pi", required: false, model_version: "deepseek-pi route", roles: ["formula", "critic"], installed: false, auth_status: "unavailable", diagnostic: "未安装", repair_suggestion: "请安装 CLI", selectable: false }),
  },
};

const doctorBlocked: AgentDoctorReport = {
  status: "blocked",
  run_mode: "blocked",
  active_provider_ids: [],
  missing_required: ["claude"],
  missing_optional: ["kimicode", "deepseek_pi"],
  unknown_required: [],
  commands: {
    codex: p({ id: "codex", label: "Codex", command: "codex", available: true, path: "/bin/codex", required: true, model_version: "codex-cli default", roles: ["deliberation", "formula", "chair"], installed: true, auth_status: "ready", selectable: true }),
    gemini: p({ id: "gemini", label: "Gemini", command: "gemini", available: true, path: "/bin/gemini", required: true, model_version: "gemini-cli default", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "ready", selectable: true }),
    claude: p({ id: "claude", label: "Claude", command: "claude", path: "/bin/claude", required: true, model_version: "claude-code default", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "not_authenticated", diagnostic: "Auth required", repair_suggestion: "Run login", selectable: false }),
    kimicode: p({ id: "kimicode", label: "KimiCode", command: "kimicode", required: false, model_version: "kimi-code local", roles: ["deliberation", "formula", "critic"], installed: false, auth_status: "unavailable", diagnostic: "未安装", repair_suggestion: "请安装 CLI", selectable: false }),
    deepseek_pi: p({ id: "deepseek_pi", label: "DeepSeek + PI", command: "deepseek-pi", required: false, model_version: "deepseek-pi route", roles: ["formula", "critic"], installed: false, auth_status: "unavailable", diagnostic: "未安装", repair_suggestion: "请安装 CLI", selectable: false }),
  },
};

describe("agent provider card helpers", () => {
  it("keeps required providers selected and removes unavailable optional providers", () => {
    const selected = normalizeAgentSelection(doctor, ["kimicode", "deepseek_pi"], "formula");
    expect(selected).toEqual(["codex", "gemini", "claude", "kimicode"]);
  });

  it("shows formula-specific optional providers separately from deliberation providers", () => {
    const formulaProviders = providerListForRole(doctor, "formula").map((p) => p.id);
    const deliberationProviders = providerListForRole(doctor, "deliberation").map((p) => p.id);
    expect(formulaProviders).toContain("deepseek_pi");
    expect(deliberationProviders).not.toContain("deepseek_pi");
  });

  it("does not select unavailable optional providers even if user selected them", () => {
    const selected = normalizeAgentSelection(doctor, ["deepseek_pi"], "formula");
    expect(selected).not.toContain("deepseek_pi");
  });

  it("blocks required provider that is installed but not authenticated", () => {
    const providers = providerListForRole(doctorBlocked, "deliberation");
    const claudeProvider = providers.find((p) => p.id === "claude");
    expect(claudeProvider).toBeDefined();
    expect(claudeProvider!.installed).toBe(true);
    expect(claudeProvider!.auth_status).toBe("not_authenticated");
    expect(claudeProvider!.available).toBe(false);
    expect(claudeProvider!.selectable).toBe(false);
  });

  it("allows toggling optional providers with auth_status=unknown when installed", () => {
    // P2: optional providers with installed=true, auth_status=unknown
    // should be selectable so users can toggle them on despite unverified auth.
    const doctorWithUnknown: AgentDoctorReport = {
      status: "blocked",
      run_mode: "blocked",
      active_provider_ids: [],
      missing_required: ["codex", "gemini", "claude"],
      missing_optional: [],
      unknown_required: [],
      commands: {
        codex: p({ id: "codex", label: "Codex", command: "codex", path: "/bin/codex", required: true, roles: ["deliberation", "formula", "chair"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        gemini: p({ id: "gemini", label: "Gemini", command: "gemini", path: "/bin/gemini", required: true, roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        claude: p({ id: "claude", label: "Claude", command: "claude", path: "/bin/claude", required: true, roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        kimicode: p({ id: "kimicode", label: "KimiCode", command: "kimicode", path: "/bin/kimicode", required: false, roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        deepseek_pi: p({ id: "deepseek_pi", label: "DeepSeek + PI", command: "deepseek-pi", required: false, roles: ["formula", "critic"], installed: false, auth_status: "unavailable", diagnostic: "未安装", repair_suggestion: "请安装 CLI", selectable: false }),
      },
    };

    const selected = normalizeAgentSelection(doctorWithUnknown, ["kimicode"], "formula");

    // kimicode is installed + auth_status=unknown → selectable, so user selection is kept
    expect(selected).toContain("kimicode");
    // deepseek_pi is not installed → excluded
    expect(selected).not.toContain("deepseek_pi");
    // Required providers with unknown auth are NOT in active_provider_ids
    expect(doctorWithUnknown.active_provider_ids).toEqual([]);
  });
});
