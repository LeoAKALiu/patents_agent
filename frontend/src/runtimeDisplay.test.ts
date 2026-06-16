import { describe, expect, it } from "vitest";

import { runtimeDisplayElapsedMs, runtimeDisplayElapsedSeconds } from "./runtimeDisplay";

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
