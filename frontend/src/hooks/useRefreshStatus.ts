import { useCallback, useEffect, useState } from "react";

import type { RefreshResult } from "../api/types";
import { useRefresh } from "./useRefresh";
import { useRefreshOnWindowFocus } from "./useRefreshOnWindowFocus";

const TOAST_MS = 4500;

export interface RefreshToast {
  text: string;
  /** An error stays until it is dismissed; a plain status hides by itself. */
  isError: boolean;
}

function refreshSummary(result: RefreshResult): string {
  return (
    `Refreshed: ${result.new_prompt_count} new prompt(s) ingested` +
    (result.usage_snapshot === "started"
      ? ", limits are being read (about a minute)"
      : result.usage_snapshot === "running"
        ? ", limits are still being read"
        : result.usage_snapshot === "recent"
          ? ", limits were read a few minutes ago"
          : "") +
    (result.codex_usage_check_triggered
      ? ", Codex rate limits re-checked."
      : ".")
  );
}

// Refreshes on a click and when the tab regains focus, and keeps what the
// toolbar shows about it: when the last refresh finished and a toast with its
// outcome. Only a click shows the outcome; a passive refresh speaks up only
// when it fails.
export function useRefreshStatus() {
  const refresh = useRefresh();
  const [refreshedAt, setRefreshedAt] = useState<number | null>(null);
  const [toast, setToast] = useState<RefreshToast | null>(null);

  useEffect(() => {
    if (!toast || toast.isError) return;
    const timer = setTimeout(() => setToast(null), TOAST_MS);
    return () => clearTimeout(timer);
  }, [toast]);

  const run = useCallback(
    (manual: boolean) => {
      // `manual` also forces a live Codex usage check, which spends real
      // Codex tokens, so it is true only for a click.
      refresh.mutate(manual, {
        onSuccess: (result) => {
          setRefreshedAt(Date.now());
          if (result.errors.length > 0) {
            setToast({
              text: `Refresh completed with errors: ${result.errors.join("; ")}`,
              isError: true,
            });
          } else if (manual) {
            setToast({ text: refreshSummary(result), isError: false });
          }
        },
        onError: (error) =>
          setToast({
            text: `Refresh failed: ${error instanceof Error ? error.message : String(error)}`,
            isError: true,
          }),
      });
    },
    [refresh],
  );

  const handleFocus = useCallback(() => {
    if (!refresh.isPending) run(false);
  }, [refresh.isPending, run]);
  useRefreshOnWindowFocus(handleFocus);

  const dismissToast = useCallback(() => setToast(null), []);

  return {
    isPending: refresh.isPending,
    run,
    refreshedAt,
    toast,
    dismissToast,
  };
}
