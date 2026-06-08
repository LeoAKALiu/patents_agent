import { describe, expect, it } from "vitest";

import { normalizeAgentSelection, providerListForRole } from "./AgentProviderCards";
import type { AgentDoctorReport } from "./api";

const doctor: AgentDoctorReport = {
  status: "ready",
  run_mode: "full",
  active_provider_ids: ["codex", "gemini", "claude", "kimicode"],
  missing_required: [],
  missing_optional: ["deepseek_pi"],
  commands: {
    codex: {
      id: "codex",
      label: "Codex",
      command: "codex",
      available: true,
      path: "/bin/codex",
      required: true,
      model_version: "codex-cli default",
      roles: ["deliberation", "formula", "chair"],
    },
    gemini: {
      id: "gemini",
      label: "Gemini",
      command: "gemini",
      available: true,
      path: "/bin/gemini",
      required: true,
      model_version: "gemini-cli default",
      roles: ["deliberation", "formula", "critic"],
    },
    claude: {
      id: "claude",
      label: "Claude",
      command: "claude",
      available: true,
      path: "/bin/claude",
      required: true,
      model_version: "claude-code default",
      roles: ["deliberation", "formula", "critic"],
    },
    kimicode: {
      id: "kimicode",
      label: "KimiCode",
      command: "kimicode",
      available: true,
      path: "/bin/kimicode",
      required: false,
      model_version: "kimi-code local",
      roles: ["deliberation", "formula", "critic"],
    },
    deepseek_pi: {
      id: "deepseek_pi",
      label: "DeepSeek + PI",
      command: "deepseek-pi",
      available: false,
      path: "",
      required: false,
      model_version: "deepseek-pi route",
      roles: ["formula", "critic"],
    },
  },
};

describe("agent provider card helpers", () => {
  it("keeps required providers selected and removes unavailable optional providers", () => {
    const selected = normalizeAgentSelection(doctor, ["kimicode", "deepseek_pi"], "formula");

    expect(selected).toEqual(["codex", "gemini", "claude", "kimicode"]);
  });

  it("shows formula-specific optional providers separately from deliberation providers", () => {
    const formulaProviders = providerListForRole(doctor, "formula").map((provider) => provider.id);
    const deliberationProviders = providerListForRole(doctor, "deliberation").map((provider) => provider.id);

    expect(formulaProviders).toContain("deepseek_pi");
    expect(deliberationProviders).not.toContain("deepseek_pi");
  });
});
