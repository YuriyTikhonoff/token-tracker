import { useQuery } from "@tanstack/react-query";

import { fetchJson } from "../api/client";
import type { DashboardData } from "../api/types";

export const DASHBOARD_DATA_QUERY_KEY = ["dashboard-data"] as const;

// `account` is an account_uuid, or null for every account combined. It is part
// of the query key, so each account's payload is cached on its own.
export function useDashboardData(account: string | null) {
  return useQuery({
    queryKey: [...DASHBOARD_DATA_QUERY_KEY, account],
    queryFn: () =>
      fetchJson<DashboardData>(
        account ? `/api/data?account=${encodeURIComponent(account)}` : "/api/data",
      ),
    refetchInterval: 30_000,
    // Keep the previous account's numbers on screen while the next loads
    // instead of unmounting the whole dashboard.
    placeholderData: (previous) => previous,
  });
}
