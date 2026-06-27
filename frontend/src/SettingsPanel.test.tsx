import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPanel } from "./SettingsPanel";
import {
  checkDesktopConfigHealth,
  clearDesktopConfigKey,
  getDesktopConfig,
  updateDesktopConfig,
  type DesktopConfigView,
} from "./api";

vi.mock("./api", () => ({
  checkDesktopConfigHealth: vi.fn(),
  clearDesktopConfigKey: vi.fn(),
  getDesktopConfig: vi.fn(),
  updateDesktopConfig: vi.fn(),
}));

const configView: DesktopConfigView = {
  provider: "deepseek",
  base_url: "https://api.deepseek.com",
  model: "deepseek-chat",
  api_key_present: true,
  api_key_fingerprint: "********1234",
  api_key_source: "desktop_config",
  updated_at: "2026-06-27T00:00:00Z",
  version: 1,
};

describe("SettingsPanel error copy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getDesktopConfig).mockResolvedValue(configView);
    vi.mocked(updateDesktopConfig).mockResolvedValue(configView);
    vi.mocked(clearDesktopConfigKey).mockResolvedValue({
      ...configView,
      api_key_present: false,
      api_key_source: "none",
    });
    vi.mocked(checkDesktopConfigHealth).mockResolvedValue({
      ok: true,
      model: configView.model,
      api_key_source: "desktop_config",
      latency_ms: 12,
      status_code: 200,
      error: "",
    });
  });

  it("uses generic app copy for settings save validation errors", async () => {
    vi.mocked(updateDesktopConfig).mockRejectedValue(
      new Error("PATCH /api/desktop-config 返回 422：Base URL must start with http:// or https://."),
    );

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);
    await screen.findByTestId("settings-save");

    await userEvent.click(screen.getByTestId("settings-save"));

    const status = await screen.findByTestId("settings-save-status");
    await waitFor(() => {
      expect(status).toHaveTextContent("输入未通过校验");
      expect(status).toHaveTextContent("Base URL must start with http:// or https://.");
      expect(status).not.toHaveTextContent("LLM");
    });
  });

  it("uses generic app copy for settings load 404 errors", async () => {
    vi.mocked(getDesktopConfig).mockRejectedValue(
      new Error("GET /api/desktop-config 返回 404：Desktop config not found."),
    );

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);

    const panel = await screen.findByText(/加载失败：/);
    expect(panel).toHaveTextContent("资源不存在");
    expect(panel).toHaveTextContent("Desktop config not found.");
    expect(panel).not.toHaveTextContent("LLM");
  });

  it("uses generic app copy for settings clear conflict errors", async () => {
    vi.mocked(clearDesktopConfigKey).mockRejectedValue(
      new Error("DELETE /api/desktop-config/api-key 返回 409：Config was modified by another session."),
    );

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);
    await screen.findByTestId("settings-save");

    await userEvent.click(screen.getByRole("button", { name: /清除密钥/ }));

    const status = await screen.findByTestId("settings-save-status");
    await waitFor(() => {
      expect(status).toHaveTextContent("操作冲突");
      expect(status).toHaveTextContent("Config was modified by another session.");
      expect(status).not.toHaveTextContent("LLM");
    });
  });
});
