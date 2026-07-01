import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPanel } from "./SettingsPanel";
import {
  checkEvidenceSourceConfig,
  checkDesktopConfigHealth,
  clearDesktopConfigKey,
  getDesktopConfig,
  listEvidenceSources,
  updateDesktopConfig,
  updateEvidenceSourceConfig,
  type DesktopConfigView,
} from "./api";

vi.mock("./api", () => ({
  checkEvidenceSourceConfig: vi.fn(),
  checkDesktopConfigHealth: vi.fn(),
  clearDesktopConfigKey: vi.fn(),
  getDesktopConfig: vi.fn(),
  listEvidenceSources: vi.fn(),
  updateDesktopConfig: vi.fn(),
  updateEvidenceSourceConfig: vi.fn(),
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

const evidenceSources = [
  {
    source_id: "patsnap_api",
    display_name: "智慧芽 PatSnap",
    source_type: "patent",
    evidence_tier: "primary_patent",
    enabled: true,
    status: "not_configured",
    base_url: "https://connect.zhihuiya.com",
    api_key_present: false,
    api_key_masked: "",
    api_key_source: "none",
    last_checked_at: "",
    last_error: "",
    application_url: "https://open.zhihuiya.com/",
    docs_url: "https://open.zhihuiya.com/devportal",
    guidance: "配置智慧芽 API key 后可启用中文及全球专利主检索。",
    can_satisfy_patent_gate: true,
  },
  {
    source_id: "wanfang_api",
    display_name: "万方",
    source_type: "non_patent_literature",
    evidence_tier: "supplemental_literature",
    enabled: true,
    status: "not_configured",
    base_url: "https://apps.wanfangdata.com.cn/open",
    api_key_present: false,
    api_key_masked: "",
    api_key_source: "none",
    last_checked_at: "",
    last_error: "",
    application_url: "https://apps.wanfangdata.com.cn/open/market/apis",
    docs_url: "https://apps.wanfangdata.com.cn/open/docs",
    guidance: "配置万方 API key 后可补充论文、期刊、会议与科技文献。",
    can_satisfy_patent_gate: false,
  },
] as const;

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
    vi.mocked(listEvidenceSources).mockResolvedValue([]);
    vi.mocked(checkEvidenceSourceConfig).mockResolvedValue({
      source_id: "patsnap_api",
      ok: false,
      status: "not_configured",
      detail: "",
      live_search_available: false,
      last_checked_at: "",
    });
    vi.mocked(updateEvidenceSourceConfig).mockResolvedValue({
      ...evidenceSources[0],
      status: "configured",
      api_key_present: true,
      api_key_masked: "••••1234",
      api_key_source: "local",
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

  it("renders evidence source setup guidance", async () => {
    vi.mocked(getDesktopConfig).mockResolvedValue(configView);
    vi.mocked(listEvidenceSources).mockResolvedValue([...evidenceSources]);
    vi.mocked(checkDesktopConfigHealth).mockResolvedValue({
      ok: false,
      model: "deepseek-chat",
      api_key_source: "none",
      latency_ms: 0,
      status_code: 0,
      error: "no_api_key",
    });

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);

    expect(await screen.findByText("数据源")).toBeInTheDocument();
    expect(screen.getByText("智慧芽 PatSnap")).toBeInTheDocument();
    expect(screen.getByText("万方")).toBeInTheDocument();
    expect(screen.getByText(/不替代专利证据门控/)).toBeInTheDocument();
    const docLinks = screen.getAllByRole("link", { name: "文档" });
    expect(docLinks).toHaveLength(2);
    expect(docLinks[0]).toHaveAttribute("href", "https://open.zhihuiya.com/devportal");
    expect(docLinks[1]).toHaveAttribute("href", "https://apps.wanfangdata.com.cn/open/docs");
  });

  it("saves a PatSnap evidence source key", async () => {
    vi.mocked(getDesktopConfig).mockResolvedValue(configView);
    vi.mocked(listEvidenceSources).mockResolvedValue([...evidenceSources]);
    vi.mocked(updateEvidenceSourceConfig).mockResolvedValue({
      ...evidenceSources[0],
      status: "configured",
      api_key_present: true,
      api_key_masked: "••••1234",
      api_key_source: "local",
    });

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);
    await screen.findByText("智慧芽 PatSnap");
    await userEvent.type(screen.getByLabelText("智慧芽 PatSnap API Key"), "ps-secret-1234");
    await userEvent.click(screen.getByRole("button", { name: "保存智慧芽 PatSnap" }));

    expect(updateEvidenceSourceConfig).toHaveBeenCalledWith(
      "patsnap_api",
      expect.objectContaining({ api_key: "ps-secret-1234" }),
    );
    expect(await screen.findByText("••••1234")).toBeInTheDocument();
  });

  it("keeps desktop settings visible when evidence source loading fails", async () => {
    vi.mocked(listEvidenceSources).mockRejectedValue(
      new Error("GET /api/evidence-sources 返回 503：Evidence source service unavailable."),
    );

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);

    expect(await screen.findByTestId("settings-panel")).toBeInTheDocument();
    expect(screen.getByTestId("settings-provider")).toHaveValue("deepseek");
    const sourceError = await screen.findByTestId("evidence-source-load-error");
    expect(sourceError).toHaveTextContent("数据源配置加载失败");
    expect(sourceError).toHaveTextContent("服务端操作失败");
    expect(sourceError).toHaveTextContent("Evidence source service unavailable.");
    expect(screen.queryByText("智慧芽 PatSnap")).not.toBeInTheDocument();
  });

  it("shows user-facing feedback when saving an evidence source fails", async () => {
    vi.mocked(listEvidenceSources).mockResolvedValue([...evidenceSources]);
    vi.mocked(updateEvidenceSourceConfig).mockRejectedValue(
      new Error("PATCH /api/evidence-sources/patsnap_api/config 返回 409：Source config was modified by another session."),
    );

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);
    await screen.findByText("智慧芽 PatSnap");
    await userEvent.type(screen.getByLabelText("智慧芽 PatSnap API Key"), "ps-secret-1234");
    await userEvent.click(screen.getByRole("button", { name: "保存智慧芽 PatSnap" }));

    const feedback = await screen.findByTestId("evidence-source-feedback");
    expect(feedback).toHaveTextContent("智慧芽 PatSnap 保存失败");
    expect(feedback).toHaveTextContent("操作冲突");
    expect(feedback).toHaveTextContent("Source config was modified by another session.");
  });

  it("distinguishes evidence source check failure statuses", async () => {
    vi.mocked(listEvidenceSources).mockResolvedValue([...evidenceSources]);
    vi.mocked(checkEvidenceSourceConfig)
      .mockResolvedValueOnce({
        source_id: "patsnap_api",
        ok: false,
        status: "not_configured",
        detail: "Missing local API key.",
        live_search_available: false,
        last_checked_at: "",
      })
      .mockResolvedValueOnce({
        source_id: "patsnap_api",
        ok: false,
        status: "unavailable",
        detail: "Remote service returned 503.",
        live_search_available: false,
        last_checked_at: "",
      })
      .mockResolvedValueOnce({
        source_id: "patsnap_api",
        ok: false,
        status: "quota_limited",
        detail: "Monthly quota exhausted.",
        live_search_available: false,
        last_checked_at: "",
      })
      .mockResolvedValueOnce({
        source_id: "patsnap_api",
        ok: false,
        status: "configured",
        detail: "Unexpected validation failure.",
        live_search_available: false,
        last_checked_at: "",
      });

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);
    await screen.findByText("智慧芽 PatSnap");

    const checkButton = screen.getAllByRole("button", { name: "测试配置" })[0];

    await userEvent.click(checkButton);
    expect(await screen.findByTestId("evidence-source-feedback")).toHaveTextContent(
      "智慧芽 PatSnap 尚未配置 API key：Missing local API key.",
    );

    await userEvent.click(checkButton);
    expect(await screen.findByTestId("evidence-source-feedback")).toHaveTextContent(
      "智慧芽 PatSnap 当前不可用，请稍后重试：Remote service returned 503.",
    );

    await userEvent.click(checkButton);
    expect(await screen.findByTestId("evidence-source-feedback")).toHaveTextContent(
      "智慧芽 PatSnap 已触发额度限制，请检查套餐或稍后再试：Monthly quota exhausted.",
    );

    await userEvent.click(checkButton);
    expect(await screen.findByTestId("evidence-source-feedback")).toHaveTextContent(
      "智慧芽 PatSnap 检查失败，请稍后重试：Unexpected validation failure.",
    );
  });

  it("shows user-facing feedback when an evidence source check request throws", async () => {
    vi.mocked(listEvidenceSources).mockResolvedValue([...evidenceSources]);
    vi.mocked(checkEvidenceSourceConfig).mockRejectedValue(
      new Error("POST /api/evidence-sources/patsnap_api/check 返回 500：Upstream check crashed."),
    );

    render(<SettingsPanel theme="light" onThemeChange={() => undefined} />);
    await screen.findByText("智慧芽 PatSnap");
    await userEvent.click(screen.getAllByRole("button", { name: "测试配置" })[0]);

    const feedback = await screen.findByTestId("evidence-source-feedback");
    expect(feedback).toHaveTextContent("智慧芽 PatSnap 检查失败");
    expect(feedback).toHaveTextContent("服务端操作失败");
    expect(feedback).toHaveTextContent("Upstream check crashed.");
  });
});
