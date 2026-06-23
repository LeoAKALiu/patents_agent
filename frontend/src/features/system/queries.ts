import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";

export const systemQueryKeys = {
  health: ["system", "health"] as const,
};

export function useHealthQuery() {
  return useQuery({
    queryKey: systemQueryKeys.health,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/health");
      if (error) throw error;
      return data;
    },
  });
}
