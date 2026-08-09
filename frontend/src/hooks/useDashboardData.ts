import { useQuery } from "@tanstack/react-query";

import { fetchJson } from "../api/client";
import type { DashboardData } from "../api/types";

export const DASHBOARD_DATA_QUERY_KEY = ["dashboard-data"] as const;

export function useDashboardData() {
  return useQuery({
    queryKey: DASHBOARD_DATA_QUERY_KEY,
    queryFn: () => fetchJson<DashboardData>("/api/data"),
    refetchInterval: 30_000,
  });
}
