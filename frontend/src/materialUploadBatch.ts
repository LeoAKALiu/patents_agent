import type { ProjectMaterial } from "./api";

export type MaterialUploadFailure = {
  fileName: string;
  error: unknown;
};

export type MaterialUploadBatchResult = {
  uploadedMaterials: ProjectMaterial[];
  rejectedUploads: MaterialUploadFailure[];
  refreshed: boolean;
};

type MaterialUploadBatchDeps = {
  uploadProjectMaterial: (projectId: string, file: File) => Promise<ProjectMaterial>;
  loadMaterials: (projectId: string) => Promise<boolean>;
};

export async function uploadProjectMaterialBatch(
  projectId: string,
  files: File[],
  deps: MaterialUploadBatchDeps,
): Promise<MaterialUploadBatchResult> {
  const results = await Promise.all(
    files.map(async (file) => {
      try {
        return {
          status: "fulfilled" as const,
          fileName: file.name,
          material: await deps.uploadProjectMaterial(projectId, file),
        };
      } catch (error) {
        return {
          status: "rejected" as const,
          fileName: file.name,
          error,
        };
      }
    }),
  );

  const uploadedMaterials = results.flatMap((result) =>
    result.status === "fulfilled" ? [result.material] : [],
  );
  const rejectedUploads = results.flatMap((result) =>
    result.status === "rejected" ? [{ fileName: result.fileName, error: result.error }] : [],
  );

  if (uploadedMaterials.length === 0) {
    return { uploadedMaterials, rejectedUploads, refreshed: false };
  }

  const refreshed = await deps.loadMaterials(projectId);
  return { uploadedMaterials, rejectedUploads, refreshed };
}
