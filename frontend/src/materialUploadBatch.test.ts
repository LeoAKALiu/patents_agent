import { describe, expect, it, vi } from "vitest";

import type { ProjectMaterial } from "./api";
import { uploadProjectMaterialBatch } from "./materialUploadBatch";

const material = (fileName: string): ProjectMaterial => ({
  id: `m-${fileName}`,
  project_id: "project-1",
  file_name: fileName,
  path: `data/project-materials/project-1/${fileName}`,
  file_type: fileName.split(".").pop() ?? "txt",
  text: "有效材料",
  status: "processed",
  warnings: [],
  metadata: {},
});

describe("uploadProjectMaterialBatch", () => {
  it("refreshes materials when the first file is rejected but a later file succeeds", async () => {
    const badFile = new File(["bad"], "first-bad.xyz", { type: "application/octet-stream" });
    const goodFile = new File(["valid"], "valid-after-bad.md", { type: "text/markdown" });
    const uploadProjectMaterial = vi
      .fn()
      .mockRejectedValueOnce(new Error("材料上传失败：不支持的文件类型。"))
      .mockResolvedValueOnce(material("valid-after-bad.md"));
    const loadMaterials = vi.fn().mockResolvedValue(true);

    const result = await uploadProjectMaterialBatch("project-1", [badFile, goodFile], {
      uploadProjectMaterial,
      loadMaterials,
    });

    expect(uploadProjectMaterial).toHaveBeenCalledTimes(2);
    expect(loadMaterials).toHaveBeenCalledWith("project-1");
    expect(result.refreshed).toBe(true);
    expect(result.uploadedMaterials.map((item) => item.file_name)).toEqual(["valid-after-bad.md"]);
    expect(result.rejectedUploads).toHaveLength(1);
    expect(result.rejectedUploads[0]?.fileName).toBe("first-bad.xyz");
  });

  it("does not refresh materials when every file is rejected", async () => {
    const files = [
      new File(["bad"], "bad-1.xyz", { type: "application/octet-stream" }),
      new File(["empty"], "empty.md", { type: "text/markdown" }),
    ];
    const uploadProjectMaterial = vi
      .fn()
      .mockRejectedValueOnce(new Error("材料上传失败：不支持的文件类型。"))
      .mockRejectedValueOnce(new Error("材料上传失败：文件为空或没有可解析文本。"));
    const loadMaterials = vi.fn().mockResolvedValue(true);

    const result = await uploadProjectMaterialBatch("project-1", files, {
      uploadProjectMaterial,
      loadMaterials,
    });

    expect(uploadProjectMaterial).toHaveBeenCalledTimes(2);
    expect(loadMaterials).not.toHaveBeenCalled();
    expect(result.refreshed).toBe(false);
    expect(result.uploadedMaterials).toEqual([]);
    expect(result.rejectedUploads.map((item) => item.fileName)).toEqual(["bad-1.xyz", "empty.md"]);
  });
});
