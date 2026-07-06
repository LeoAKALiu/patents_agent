import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ShellSidebar } from "./ShellSidebar";

describe("ShellSidebar brand", () => {
  afterEach(() => {
    cleanup();
  });

  it("uses the GrantAtlas brand without a subtitle", () => {
    render(
      <ShellSidebar
        mainSections={[{ id: "workbench", label: "工作台" }]}
        activeSectionId="workbench"
        onSelectSection={() => undefined}
      />,
    );

    const brand = screen.getByLabelText("权衡 GrantAtlas home");
    expect(within(brand).getByRole("img", { name: "权衡 GrantAtlas logo" })).toBeInTheDocument();
    expect(within(brand).getByText("权衡 GrantAtlas")).toBeInTheDocument();
    expect(within(brand).queryByText("国际专利授权工程系统")).not.toBeInTheDocument();
    expect(within(brand).queryByText("PatentAgent")).not.toBeInTheDocument();
    expect(within(brand).queryByText("PA")).not.toBeInTheDocument();
  });
});
