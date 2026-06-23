import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";

export const projectQueryKeys = {
  all: ["projects"] as const,
  list: () => [...projectQueryKeys.all, "list"] as const,
};

export function useProjectsQuery() {
  return useQuery({
    queryKey: projectQueryKeys.list(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/projects");
      if (error) throw error;
      return data ?? [];
    },
  });
}