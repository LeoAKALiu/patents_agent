import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  AgentProviderCards,
  DeliberationAgentSelector,
  normalizeAgentSelection,
  normalizeDeliberationExpertSelection,
  normalizeDeliberationParticipantSelection,
  providerListForRole,
} from "./AgentProviderCards";
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
  active_provider_ids: ["codex", "deepseek", "claude", "kimicode"],
  missing_required: [],
  missing_optional: [],
  unknown_required: [],
  commands: {
    codex: p({ id: "codex", label: "Codex", command: "codex", available: true, path: "/bin/codex", required: true, model_version: "codex-cli default", roles: ["deliberation", "formula", "chair"], installed: true, auth_status: "ready", selectable: true }),
    deepseek: p({ id: "deepseek", label: "DeepSeek", command: "reasonix", available: true, path: "/bin/reasonix", required: true, model_version: "reasonix deepseek-pro", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "ready", selectable: true }),
    claude: p({ id: "claude", label: "Claude", command: "claude", available: true, path: "/bin/claude", required: true, model_version: "claude-code default", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "ready", selectable: true }),
    gemini: p({ id: "gemini", label: "Gemini", command: "gemini", available: false, path: "/bin/gemini", required: false, model_version: "deprecated", roles: ["deprecated"], installed: true, auth_status: "unknown", selectable: true }),
    kimicode: p({ id: "kimicode", label: "KimiCode", command: "kimicode", available: true, path: "/bin/kimicode", required: false, model_version: "kimi-code local", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "ready", selectable: true }),
    mimo: p({ id: "mimo", label: "MimoCode", command: "mimo", available: false, path: "/Users/leo/.mimocode/bin/mimo", required: false, model_version: "mimo-code local", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "unknown", diagnostic: "命令已安装，但无法验证其可调用状态。", selectable: true }),
  },
};

const doctorBlocked: AgentDoctorReport = {
  status: "blocked",
  run_mode: "blocked",
  active_provider_ids: [],
  missing_required: ["deepseek"],
  missing_optional: ["kimicode"],
  unknown_required: [],
  commands: {
    codex: p({ id: "codex", label: "Codex", command: "codex", available: true, path: "/bin/codex", required: true, model_version: "codex-cli default", roles: ["deliberation", "formula", "chair"], installed: true, auth_status: "ready", selectable: true }),
    deepseek: p({ id: "deepseek", label: "DeepSeek", command: "reasonix", path: "/bin/reasonix", required: true, model_version: "reasonix deepseek-pro", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "not_authenticated", diagnostic: "Auth required", repair_suggestion: "Run reasonix setup", selectable: false }),
    claude: p({ id: "claude", label: "Claude", command: "claude", path: "/bin/claude", required: true, model_version: "claude-code default", roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "not_authenticated", diagnostic: "Auth required", repair_suggestion: "Run login", selectable: false }),
    gemini: p({ id: "gemini", label: "Gemini", command: "gemini", path: "/bin/gemini", required: false, model_version: "deprecated", roles: ["deprecated"], installed: true, auth_status: "unknown", selectable: true }),
    kimicode: p({ id: "kimicode", label: "KimiCode", command: "kimicode", required: false, model_version: "kimi-code local", roles: ["deliberation", "formula", "critic"], installed: false, auth_status: "unavailable", diagnostic: "未安装", repair_suggestion: "请安装 CLI", selectable: false }),
    mimo: p({ id: "mimo", label: "MimoCode", command: "mimo", required: false, model_version: "mimo-code local", roles: ["deliberation", "formula", "critic"], installed: false, auth_status: "unavailable", diagnostic: "未安装", repair_suggestion: "请安装 CLI", selectable: false }),
  },
};

describe("agent provider card helpers", () => {
  it("keeps required providers selected and removes unavailable optional providers", () => {
    const selected = normalizeAgentSelection(doctor, ["kimicode", "mimo", "gemini"], "formula");
    expect(selected).toEqual(["codex", "deepseek", "claude", "kimicode", "mimo"]);
  });

  it("keeps deprecated Gemini out of formula and deliberation providers", () => {
    const formulaProviders = providerListForRole(doctor, "formula").map((p) => p.id);
    const deliberationProviders = providerListForRole(doctor, "deliberation").map((p) => p.id);
    expect(formulaProviders).toContain("deepseek");
    expect(formulaProviders).toContain("kimicode");
    expect(formulaProviders).toContain("mimo");
    expect(formulaProviders).not.toContain("gemini");
    expect(deliberationProviders).toContain("kimicode");
    expect(deliberationProviders).toContain("mimo");
    expect(deliberationProviders).not.toContain("gemini");
  });

  it("does not select unavailable optional providers even if user selected them", () => {
    const selected = normalizeAgentSelection(doctorBlocked, ["kimicode"], "formula");
    expect(selected).not.toContain("kimicode");
  });

  it("blocks required provider that is installed but not authenticated", () => {
    const providers = providerListForRole(doctorBlocked, "deliberation");
    const deepseekProvider = providers.find((p) => p.id === "deepseek");
    expect(deepseekProvider).toBeDefined();
    expect(deepseekProvider!.installed).toBe(true);
    expect(deepseekProvider!.command).toBe("reasonix");
    expect(deepseekProvider!.auth_status).toBe("not_authenticated");
    expect(deepseekProvider!.available).toBe(false);
    expect(deepseekProvider!.selectable).toBe(false);
  });

  it("allows toggling optional providers with auth_status=unknown when installed", () => {
    // P2: optional providers with installed=true, auth_status=unknown
    // should be selectable so users can toggle them on despite unverified auth.
    const doctorWithUnknown: AgentDoctorReport = {
      status: "blocked",
      run_mode: "blocked",
      active_provider_ids: [],
      missing_required: ["codex", "deepseek", "claude"],
      missing_optional: [],
      unknown_required: [],
      commands: {
        codex: p({ id: "codex", label: "Codex", command: "codex", path: "/bin/codex", required: true, roles: ["deliberation", "formula", "chair"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        deepseek: p({ id: "deepseek", label: "DeepSeek", command: "reasonix", path: "/bin/reasonix", required: true, roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        claude: p({ id: "claude", label: "Claude", command: "claude", path: "/bin/claude", required: true, roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        gemini: p({ id: "gemini", label: "Gemini", command: "gemini", path: "/bin/gemini", required: false, roles: ["deprecated"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        kimicode: p({ id: "kimicode", label: "KimiCode", command: "kimicode", path: "/bin/kimicode", required: false, roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
        mimo: p({ id: "mimo", label: "MimoCode", command: "mimo", path: "/Users/leo/.mimocode/bin/mimo", required: false, roles: ["deliberation", "formula", "critic"], installed: true, auth_status: "unknown", diagnostic: "无法验证", repair_suggestion: "请确保已登录", available: false, selectable: true }),
      },
    };

    const selected = normalizeAgentSelection(doctorWithUnknown, ["kimicode", "mimo", "gemini"], "formula");

    // kimicode is installed + auth_status=unknown → selectable, so user selection is kept
    expect(selected).toContain("kimicode");
    expect(selected).toContain("mimo");
    // Gemini is deprecated and no longer part of formula/deliberation roles.
    expect(selected).not.toContain("gemini");
    // Required providers with unknown auth are NOT in active_provider_ids
    expect(doctorWithUnknown.active_provider_ids).toEqual([]);
  });

  it("renders provider cards without exposing CLI paths", () => {
    const html = renderToStaticMarkup(
      createElement(AgentProviderCards, {
        doctor,
        selectedProviders: ["kimicode", "mimo"],
        role: "deliberation",
        onToggleProvider: () => undefined,
      }),
    );

    expect(html).toContain("KimiCode");
    expect(html).toContain("MimoCode");
    expect(html).toContain("加入本轮");
    expect(html).not.toContain("/bin");
    expect(html).not.toContain("/Users/leo");
    expect(html).not.toContain("未找到命令");
  });

  it("normalizes deliberation seats around a fixed Codex chair and two selected experts", () => {
    const deliberationDoctor: AgentDoctorReport = {
      status: "degraded",
      run_mode: "partial",
      active_provider_ids: ["codex", "deepseek", "kimicode", "mimo"],
      missing_required: ["claude"],
      missing_optional: [],
      unknown_required: [],
      commands: {
        codex: p({ id: "codex", label: "Codex", command: "codex", available: true, required: true, roles: ["deliberation", "chair"], installed: true, auth_status: "ready", selectable: true }),
        deepseek: p({ id: "deepseek", label: "DeepSeek", command: "reasonix", available: true, roles: ["deliberation"], installed: true, auth_status: "ready", selectable: true }),
        claude: p({ id: "claude", label: "Claude", command: "claude", available: false, roles: ["deliberation"], installed: true, auth_status: "not_authenticated", diagnostic: "claude -p 401", repair_suggestion: "setup-token", selectable: false }),
        kimicode: p({ id: "kimicode", label: "KimiCode", command: "kimicode", available: true, roles: ["deliberation"], installed: true, auth_status: "ready", selectable: true }),
        mimo: p({ id: "mimo", label: "MimoCode", command: "mimo", available: true, roles: ["deliberation"], installed: true, auth_status: "ready", selectable: true }),
      },
    };

    const experts = normalizeDeliberationExpertSelection(deliberationDoctor, ["claude", "deepseek", "kimicode", "mimo"]);
    const participants = normalizeDeliberationParticipantSelection(deliberationDoctor, experts, ["mimo", "claude", "deepseek"]);

    expect(experts).toEqual(["codex", "deepseek", "kimicode"]);
    expect(participants).toEqual(["mimo"]);
  });

  it("renders compact deliberation cards and moves long diagnostics out of provider tiles", () => {
    const longDiagnostic = `claude -p 探测失败：${"认证错误".repeat(80)}`;
    const compactDoctor: AgentDoctorReport = {
      status: "blocked",
      run_mode: "blocked",
      active_provider_ids: ["codex", "deepseek", "kimicode"],
      missing_required: ["claude"],
      missing_optional: [],
      unknown_required: [],
      commands: {
        codex: p({ id: "codex", label: "Codex", command: "codex", available: true, required: true, roles: ["deliberation", "chair"], installed: true, auth_status: "ready", selectable: true }),
        deepseek: p({ id: "deepseek", label: "DeepSeek", command: "reasonix", available: true, roles: ["deliberation"], installed: true, auth_status: "ready", selectable: true }),
        claude: p({ id: "claude", label: "Claude", command: "claude", available: false, roles: ["deliberation"], installed: true, auth_status: "not_authenticated", diagnostic: longDiagnostic, repair_suggestion: "运行 claude -p 验证。", selectable: false }),
        kimicode: p({ id: "kimicode", label: "KimiCode", command: "kimicode", available: true, roles: ["deliberation"], installed: true, auth_status: "ready", selectable: true }),
      },
    };

    const html = renderToStaticMarkup(
      createElement(DeliberationAgentSelector, {
        doctor: compactDoctor,
        expertProviders: ["codex", "deepseek", "kimicode"],
        participantProviders: [],
        disabled: false,
        onToggleExpert: () => undefined,
        onToggleParticipant: () => undefined,
      }),
    );

    expect(html).toContain("主席固定");
    expect(html).toContain("决策专家 3/3");
    expect(html).toContain("参会专家");
    expect(html).toContain("必选未就绪");
    expect(html).toContain("运行 claude -p 验证。");
    expect(html).not.toContain(longDiagnostic);
  });
});
