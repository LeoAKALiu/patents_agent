import { useEffect, useState } from "react";

type RuntimeClockState = {
  elapsed_ms?: number | null;
  heartbeat_at?: string | null;
};

type RuntimeFailureLike = {
  stage?: string | null;
  provider?: string | null;
  reason?: string | null;
  message?: string | null;
  repair_suggestion?: string | null;
  retryable?: boolean | null;
};

export type UserFacingCopy = {
  title: string;
  message: string;
  detail?: string;
  tone: "info" | "warn" | "error";
};

export function runtimeDisplayElapsedMs(state: RuntimeClockState | null | undefined, nowMs = Date.now()): number {
  const baseElapsedMs = Math.max(0, Math.floor(state?.elapsed_ms ?? 0));
  const heartbeatAt = state?.heartbeat_at;
  if (!heartbeatAt) return baseElapsedMs;

  const heartbeatMs = Date.parse(heartbeatAt);
  if (!Number.isFinite(heartbeatMs)) return baseElapsedMs;

  return baseElapsedMs + Math.max(0, nowMs - heartbeatMs);
}

export function runtimeDisplayElapsedSeconds(state: RuntimeClockState | null | undefined, nowMs = Date.now()): number {
  return Math.floor(runtimeDisplayElapsedMs(state, nowMs) / 1000);
}

function normalizeErrorText(value: unknown): string {
  if (value instanceof Error) return value.message;
  if (typeof value === "string") return value;
  if (value == null) return "";
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function includesAny(haystack: string, needles: string[]): boolean {
  return needles.some((needle) => haystack.includes(needle));
}

export function userFacingErrorCopy(
  error: unknown,
  options: { statusCode?: number | null; fallbackTitle?: string; fallbackMessage?: string } = {},
): UserFacingCopy {
  const raw = normalizeErrorText(error).trim();
  const lower = raw.toLowerCase();
  const statusCode = options.statusCode ?? extractStatusCode(raw);
  const fallbackTitle = options.fallbackTitle ?? "操作失败";

  if (statusCode === 429 || includesAny(lower, ["ratelimit", "rate limit", "rate_limit", "429", "限流"])) {
    return {
      title: "LLM 服务触发限流",
      message: "请求被服务商限流，请稍后重试，或降低请求频率并确认当前 API Key 的额度。",
      detail: raw || undefined,
      tone: "warn",
    };
  }

  if (
    statusCode === 401
    || statusCode === 403
    || includesAny(lower, ["authentication", "unauthorized", "forbidden", "invalid api key", "api key"])
  ) {
    return {
      title: "LLM 认证失败",
      message: "请检查 API Key、服务商账号权限和当前模型是否可用，然后重新测试或重试。",
      detail: raw || undefined,
      tone: "error",
    };
  }

  if (
    statusCode === 500
    || statusCode === 502
    || statusCode === 503
    || statusCode === 504
    || includesAny(lower, ["internalservererror", "server_error", "service unavailable", "bad gateway", "gateway timeout"])
  ) {
    return {
      title: "LLM 服务暂时不可用",
      message: "服务端返回异常，请稍后重试，或检查 Base URL 指向的服务是否正常运行。",
      detail: raw || undefined,
      tone: "error",
    };
  }

  if (
    includesAny(lower, [
      "apiconnectionerror",
      "connection error",
      "failed to fetch",
      "networkerror",
      "econnrefused",
      "connection refused",
      "请求失败",
    ])
  ) {
    return {
      title: "无法连接到 LLM 服务",
      message: "请检查 Base URL、网络、代理配置或本机服务端口后重试。",
      detail: raw || undefined,
      tone: "error",
    };
  }

  if (includesAny(lower, ["timeout", "timed out", "超时"])) {
    return {
      title: "LLM 服务响应超时",
      message: "请检查网络连接，稍后重试；如果持续发生，请更换可用的 Base URL 或模型。",
      detail: raw || undefined,
      tone: "warn",
    };
  }

  return {
    title: fallbackTitle,
    message: options.fallbackMessage ?? "请检查配置或稍后重试；如果问题持续存在，请保留诊断详情用于排查。",
    detail: raw || undefined,
    tone: "error",
  };
}

export function userFacingErrorMessage(error: unknown, options: Parameters<typeof userFacingErrorCopy>[1] = {}): string {
  const copy = userFacingErrorCopy(error, options);
  return `${copy.title}：${copy.message}`;
}

export function runtimeFailureCopy(failure: RuntimeFailureLike): UserFacingCopy {
  const rawParts = [
    failure.reason,
    failure.stage,
    failure.provider,
    failure.message,
    failure.repair_suggestion,
  ].filter(Boolean);
  const raw = rawParts.join(" / ");
  const reason = (failure.reason ?? "").toLowerCase();
  const message = failure.message ?? "";
  const stage = failure.stage ?? "";
  const taskName = stage.includes("disclosure") ? "发明点提炼" : "本次运行";

  if (reason.includes("cancel") || message.toLowerCase().includes("cancel")) {
    return {
      title: "运行已取消",
      message: `已取消${taskName}，已保留可重试的中间结果。需要继续时可直接重试。`,
      detail: raw || undefined,
      tone: "info",
    };
  }

  const mapped = userFacingErrorCopy(message || raw, {
    fallbackTitle: `${taskName}失败`,
    fallbackMessage: "请检查 LLM 配置、网络或服务商状态后重试。",
  });
  return {
    ...mapped,
    title: mapped.title.startsWith("LLM") || mapped.title.startsWith("无法")
      ? `${taskName}失败`
      : mapped.title,
    detail: raw || mapped.detail,
  };
}

function extractStatusCode(text: string): number | null {
  const match = text.match(/\b(?:返回|code:|status(?:_code)?["': ]+)?\s*(4\d\d|5\d\d)\b/i);
  if (!match) return null;
  const parsed = Number.parseInt(match[1], 10);
  return Number.isFinite(parsed) ? parsed : null;
}

export function useRuntimeNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [active]);

  return now;
}
