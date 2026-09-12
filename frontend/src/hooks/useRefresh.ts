import { useMutation, useQueryClient } from "@tanstack/react-query";

import { fetchJson } from "../api/client";
import type { RefreshResult } from "../api/types";
import { DASHBOARD_DATA_QUERY_KEY } from "./useDashboardData";

export const REFRESH_MUTATION_KEY = ["refresh"] as const;

export function useRefresh() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: REFRESH_MUTATION_KEY,
    // triggerCodexUsageCheck spends real Codex tokens (a live `codex exec`
    // turn) to force a fresh rate-limit reading — only pass true from an
    // explicit user click, never from a passive/automatic refresh (e.g.
    // window-focus), so the cost stays opt-in.
    mutationFn: (triggerCodexUsageCheck: boolean = false) =>
      fetchJson<RefreshResult>(
        `/api/refresh?trigger_codex_usage_check=${triggerCodexUsageCheck}`,
        { method: "POST" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DASHBOARD_DATA_QUERY_KEY });
    },
  });
}
