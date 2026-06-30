import { useQuery } from "@tanstack/react-query";
import type { ProjectRecord } from "@/api";
import { apiClient } from "@/lib/apiClient";

export const projectQueryKeys = {
  all: ["projects"] as const,
  list: () => [...projectQueryKeys.all, "list"] as const,
};

type ProjectsResponse = {
  projects?: ProjectRecord[];
};

export function useProjectsQuery() {
  return useQuery({
    queryKey: projectQueryKeys.list(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/projects");
      if (error) throw error;
      const projects = (data as ProjectsResponse | undefined)?.projects;
      if (!Array.isArray(projects)) {
        throw new Error("Invalid projects response.");
      }
      return projects;
    },
  });
}
