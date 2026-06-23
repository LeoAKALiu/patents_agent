import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DeliberationRun } from "@/api";
import { DeliberationPanel } from "./DeliberationPanel";

const failedRun: DeliberationRun = {
  id: "run-log-visible-1",
  project_id: "project-1",
  status: "failed",
  providers: ["codex", "claude"],
  run_mode: "full",
  round_depth: "standard",
  trace: false,
  run_dir: "/tmp/run-log-visible-1",
  stage_results: [],
  strategy_brief: null,
  failures: [
    {
      provider_id: "claude",
      phase: "deliberation",
      reason: "process_error",
      message: "claude attempt failed",
    },
  ],
  events: ["run started", "attempt failed"],
  logs: [
    {
      level: "error",
      phase: "deliberation",
      provider_id: "claude",
      attempt: 1,
      message: "attempt failed",
      detail: "stderr: auth token expired",
      repair_suggestion: "重新登录 Claude 后重试。",
      elapsed_ms: 7_000,
      created_at: "2026-06-23T13:40:00Z",
    },
  ],
  runtime_state: null,
  failure_details: [],
  cancel_requested: false,
  retry_of: null,
};

describe("DeliberationPanel", () => {
  it("renders run history, events, logs, and failures even without a strategy result", () => {
    render(
      <DeliberationPanel
        deliberation={null}
        runs={[failedRun]}
        doctor={null}
        selectedProviders={[]}
        participantProviders={[]}
        busy=""
        busyElapsedSeconds={0}
        onStartDeliberation={vi.fn()}
        onCancelRun={vi.fn()}
        onRetryRun={vi.fn()}
        onToggleProvider={vi.fn()}
        onToggleParticipantProvider={vi.fn()}
        onOpenExpertTool={vi.fn()}
      />,
    );

    expect(screen.getByRole("region", { name: "会审记录与日志" })).toBeInTheDocument();
    expect(screen.getByText(/run run-log-vi/)).toBeInTheDocument();
    expect(screen.getAllByText("attempt failed").length).toBeGreaterThan(0);
    expect(screen.getByText("stderr: auth token expired")).toBeInTheDocument();
    expect(screen.getByText(/claude \/ deliberation \/ process_error/)).toBeInTheDocument();
    expect(screen.queryByText("已有会审记录，但尚无已完成的策略结果。")).not.toBeInTheDocument();
  });
});
