import { useQuery } from "@tanstack/react-query";

import { fetchJson } from "../api/client";
import type { OverviewData } from "../api/types";
import { setDisplayTimeZone } from "../lib/format";
import { DASHBOARD_DATA_QUERY_KEY } from "./useDashboardData";

// The top of the dashboard (limits, the session, the daily chart). It answers
// in about a second, so it is asked for on its own and does not wait for
// /api/data, which takes much longer. Its key starts with the dashboard-data
// key, so a refresh invalidates both.
export function useOverview(account: string | null) {
  return useQuery({
    queryKey: [...DASHBOARD_DATA_QUERY_KEY, "overview", account],
    queryFn: async () => {
      const data = await fetchJson<OverviewData>(
        account
          ? `/api/overview?account=${encodeURIComponent(account)}`
          : "/api/overview",
      );
      setDisplayTimeZone(data.timezone);
      return data;
    },
    refetchInterval: 30_000,
    placeholderData: (previous) => previous,
  });
}
