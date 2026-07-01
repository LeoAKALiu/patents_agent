import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ProjectMaterial } from "@/api";
import { MaterialSummary } from "./MaterialSummary";

const processedMaterial: ProjectMaterial = {
  id: "m-processed",
  project_id: "project-1",
  file_name: "round18-long-chinese-material.md",
  path: "data/project-materials/project-1/round18-long-chinese-material.md",
  file_type: "md",
  text: "补充材料".repeat(5800),
  status: "processed",
  warnings: [],
  metadata: {},
};

const failedMaterial: ProjectMaterial = {
  id: "m-failed",
  project_id: "project-1",
  file_name: "unsupported-round5.xyz",
  path: "data/project-materials/project-1/unsupported-round5.xyz",
  file_type: "xyz",
  text: "",
  status: "failed",
  warnings: ["Unsupported project material file type: .xyz"],
  metadata: {},
};

describe("MaterialSummary", () => {
  it("separates processed materials from failed uploads and keeps metadata readable", () => {
    const { container } = render(<MaterialSummary materials={[failedMaterial, processedMaterial]} />);

    expect(screen.getByText("可用材料")).toBeTruthy();
    expect(screen.getByText("失败上传")).toBeTruthy();
    expect(screen.getByText("round18-long-chinese-material.md")).toBeTruthy();
    expect(screen.getByText("类型：md")).toBeTruthy();
    expect(screen.getByText(`${processedMaterial.text.length} 字`)).toBeTruthy();
    expect(screen.getByText("unsupported-round5.xyz")).toBeTruthy();
    expect(screen.getByText(/不参与后续发明点提炼/)).toBeTruthy();
    expect(container.textContent).not.toContain("round18-long-chinese-material.mdmd");
  });

  it("warns when uploaded materials reuse the same file name", () => {
    render(
      <MaterialSummary
        materials={[
          processedMaterial,
          {
            ...processedMaterial,
            id: "m-duplicate",
            path: "data/project-materials/project-1/copy/round18-long-chinese-material.md",
          },
        ]}
      />,
    );

    expect(screen.getByText("发现重复文件名")).toBeTruthy();
    expect(screen.getByText(/round18-long-chinese-material\.md 已出现多次/)).toBeTruthy();
  });
});
