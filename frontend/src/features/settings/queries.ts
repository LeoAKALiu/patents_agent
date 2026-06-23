import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";

export const settingsQueryKeys = {
  all: ["settings"] as const,
  desktopConfig: () => [...settingsQueryKeys.all, "desktop-config"] as const,
};

export function useDesktopConfigQuery(enabled = true) {
  return useQuery({
    queryKey: settingsQueryKeys.desktopConfig(),
    enabled,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/desktop-config");
      if (error) throw error;
      return data;
    },
  });
}
