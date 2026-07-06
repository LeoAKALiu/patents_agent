import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { IdeaIntakePanel } from "./IdeaIntakePanel";

function renderIdeaIntakePanel() {
  return render(
    <IdeaIntakePanel
      project={null}
      materials={[]}
      externalDraftSources={[]}
      externalDraftIntakeRuns={[]}
      busy=""
      busyElapsedSeconds={0}
      onCreateIdeaProject={vi.fn(async () => undefined)}
      onCreateExternalDraft={vi.fn(async () => undefined)}
      onUploadExternalDraft={vi.fn(async () => undefined)}
      onStartExternalDraftIntake={vi.fn(async () => undefined)}
      onConfirmExternalDraftIntake={vi.fn(async () => undefined)}
      onUploadMaterial={vi.fn()}
    />,
  );
}

describe("IdeaIntakePanel", () => {
  it("guides short and marketing-only idea inputs without blocking project creation", () => {
    renderIdeaIntakePanel();
    fireEvent.change(screen.getByLabelText("项目名称"), { target: { value: "智能仓储货位推荐" } });
    const ideaInput = screen.getByLabelText("一句话想法");

    fireEvent.change(ideaInput, { target: { value: "智能仓储" } });
    expect(screen.getByText(/当前想法较短/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /创建并继续/ })).not.toBeDisabled();

    fireEvent.change(ideaInput, { target: { value: "全球领先、成本最低、体验最好，能够显著提升市场客户增长" } });
    expect(screen.getByText(/当前描述偏效果或商业价值/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /创建并继续/ })).not.toBeDisabled();
  });
});
