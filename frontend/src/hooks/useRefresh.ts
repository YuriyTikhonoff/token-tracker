import { useMutation, useQueryClient } from "@tanstack/react-query";

import { fetchJson } from "../api/client";
import type { RefreshResult } from "../api/types";
import { DASHBOARD_DATA_QUERY_KEY } from "./useDashboardData";

export const REFRESH_MUTATION_KEY = ["refresh"] as const;

export function useRefresh() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: REFRESH_MUTATION_KEY,
    mutationFn: () =>
      fetchJson<RefreshResult>("/api/refresh", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DASHBOARD_DATA_QUERY_KEY });
    },
  });
}
