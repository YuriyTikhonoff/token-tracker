import { useMutation, useQueryClient } from "@tanstack/react-query";

import { fetchJson } from "../api/client";
import { DASHBOARD_DATA_QUERY_KEY } from "./useDashboardData";

interface AccountUpdate {
  accountUuid: string;
  label?: string;
  isDefault?: boolean;
}

export function useUpdateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ accountUuid, label, isDefault }: AccountUpdate) =>
      fetchJson<{ ok: boolean }>(
        `/api/accounts/${encodeURIComponent(accountUuid)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ label, is_default: isDefault }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DASHBOARD_DATA_QUERY_KEY });
    },
  });
}
