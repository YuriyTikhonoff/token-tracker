import { useQuery } from "@tanstack/react-query";

import { fetchJson } from "../api/client";
import { DASHBOARD_DATA_QUERY_KEY } from "./useDashboardData";

// The data of one collapsed section (GET /api/sections/<path>). It is called
// from a component that only mounts once the section is open, so a section
// nobody opens costs nothing, and one that is closed again stops polling.
// The key starts with the dashboard-data key, so a refresh invalidates it too.
export function useSection<T>(path: string, account: string | null) {
  return useQuery({
    queryKey: [...DASHBOARD_DATA_QUERY_KEY, "section", path, account],
    queryFn: () =>
      fetchJson<T>(
        account
          ? `/api/sections/${path}?account=${encodeURIComponent(account)}`
          : `/api/sections/${path}`,
      ),
    refetchInterval: 30_000,
    // Keep the previous account's rows on screen while the next ones load.
    placeholderData: (previous) => previous,
  });
}
