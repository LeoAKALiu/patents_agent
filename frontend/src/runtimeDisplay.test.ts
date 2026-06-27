import { describe, expect, it } from "vitest";

import {
  runtimeDisplayElapsedMs,
  runtimeDisplayElapsedSeconds,
  runtimeFailureCopy,
  userFacingAppErrorCopy,
  userFacingErrorCopy,
} from "./runtimeDisplay";
import { guidedRuntimeSubtaskLabel } from "./flow/runtimeWidgets";

describe("runtime display clock", () => {
  it("interpolates elapsed time from the last backend heartbeat", () => {
    const state = {
      elapsed_ms: 75_000,
      heartbeat_at: "2026-06-16T04:00:00Z",
    };

    expect(runtimeDisplayElapsedMs(state, Date.parse("2026-06-16T04:00:05Z"))).toBe(80_000);
    expect(runtimeDisplayElapsedSeconds(state, Date.parse("2026-06-16T04:00:05Z"))).toBe(80);
  });

  it("never moves elapsed time backwards when local time precedes heartbeat", () => {
    const state = {
      elapsed_ms: 75_000,
      heartbeat_at: "2026-06-16T04:00:00Z",
    };

    expect(runtimeDisplayElapsedMs(state, Date.parse("2026-06-16T03:59:55Z"))).toBe(75_000);
  });

  it("falls back to backend elapsed time without a valid heartbeat", () => {
    expect(runtimeDisplayElapsedMs({ elapsed_ms: 12_345, heartbeat_at: "" }, 100)).toBe(12_345);
    expect(runtimeDisplayElapsedMs({ elapsed_ms: 12_345, heartbeat_at: "not-a-date" }, 100)).toBe(12_345);
  });
});

describe("user-facing runtime error copy", () => {
  it("maps connection errors to Chinese guidance without exposing SDK text as primary copy", () => {
    const copy = userFacingErrorCopy("APIConnectionError: Connection error.");

    expect(copy.title).toBe("无法连接到 LLM 服务");
    expect(copy.message).toContain("Base URL");
    expect(copy.message).not.toContain("APIConnectionError");
    expect(copy.detail).toContain("APIConnectionError");
  });

  it("maps provider rate limits and 5xx responses to actionable primary copy", () => {
    const rateLimit = userFacingErrorCopy("RateLimitError: Error code: 429 - {'error': {'type': 'rate_limit_error'}}");
    const serverError = userFacingErrorCopy("InternalServerError: Error code: 503 - {'error': {'code': 'qa_503'}}");

    expect(rateLimit.title).toBe("LLM 服务触发限流");
    expect(rateLimit.message).toContain("稍后重试");
    expect(rateLimit.message).not.toContain("rate_limit_error");
    expect(serverError.title).toBe("LLM 服务暂时不可用");
    expect(serverError.message).toContain("服务是否正常运行");
    expect(serverError.message).not.toContain("InternalServerError");
  });

  it("preserves backend detail for generic app errors instead of using LLM provider copy", () => {
    const stale = userFacingAppErrorCopy(
      new Error("POST /api/projects/p-1/official-compile-runs/r-1/cleanup 返回 409：源稿已变化，请刷新后重新质量检查。"),
    );
    const validation = userFacingAppErrorCopy("POST /api/projects/p-1/materials 返回 422：文件为空或没有可解析文本。");
    const backend = userFacingAppErrorCopy("POST /api/projects/p-1/reviews 返回 500：repair-session payload invalid");

    expect(stale.title).toBe("操作冲突");
    expect(stale.message).toBe("源稿已变化，请刷新后重新质量检查。");
    expect(stale.message).not.toContain("LLM");
    expect(validation.title).toBe("输入未通过校验");
    expect(validation.message).toBe("文件为空或没有可解析文本。");
    expect(backend.title).toBe("服务端操作失败");
    expect(backend.message).toBe("repair-session payload invalid");
  });

  it("maps cancellation runtime failures to non-alarming retry guidance", () => {
    const copy = runtimeFailureCopy({
      reason: "cancelled",
      stage: "disclosure_scan",
      provider: "llm",
      message: "Run was cancelled by request; partial artifacts were preserved for retry.",
      repair_suggestion: "Review partial stage_results, then retry the run when ready.",
      retryable: true,
    });

    expect(copy.tone).toBe("info");
    expect(copy.title).toBe("运行已取消");
    expect(copy.message).toContain("已取消发明点提炼");
    expect(copy.message).toContain("可直接重试");
    expect(copy.message).not.toContain("stage_results");
    expect(copy.detail).toContain("stage_results");
  });

  it("maps disclosure LLM failures to guided-flow user copy", () => {
    const copy = runtimeFailureCopy({
      reason: "exception",
      stage: "disclosure_scan",
      provider: "llm",
      message: "Connection error.",
      repair_suggestion: "Retry after fixing the disclosure provider or prompt/schema issue.",
      retryable: true,
    });

    expect(copy.title).toBe("发明点提炼失败");
    expect(copy.message).toContain("Base URL");
    expect(copy.message).not.toContain("prompt/schema");
    expect(copy.detail).toContain("prompt/schema");
  });
});

describe("guided runtime labels", () => {
  it("maps post-draft review LLM stage subtasks to readable labels", () => {
    expect(guidedRuntimeSubtaskLabel("post_draft_claims_reviewer")).toBe("权利要求复核");
    expect(guidedRuntimeSubtaskLabel("post-draft claims review")).toBe("权利要求复核");
    expect(guidedRuntimeSubtaskLabel("post_draft_spec_cleaner")).toBe("说明书清洁度复核");
    expect(guidedRuntimeSubtaskLabel("post-draft specification cleanup")).toBe("说明书清洁度复核");
    expect(guidedRuntimeSubtaskLabel("post_draft_technical_hardness")).toBe("技术硬度复核");
    expect(guidedRuntimeSubtaskLabel("post-draft technical hardness review")).toBe("技术硬度复核");
    expect(guidedRuntimeSubtaskLabel("post_draft_chair_synthesis")).toBe("会审主席综合");
    expect(guidedRuntimeSubtaskLabel("post-draft chair synthesis")).toBe("会审主席综合");
  });
});
