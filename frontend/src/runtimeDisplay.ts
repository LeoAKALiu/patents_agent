import { useEffect, useState } from "react";

type RuntimeClockState = {
  elapsed_ms?: number | null;
  heartbeat_at?: string | null;
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
