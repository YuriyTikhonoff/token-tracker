import { useCallback } from "react";

import { useRefresh } from "../hooks/useRefresh";
import { useRefreshOnWindowFocus } from "../hooks/useRefreshOnWindowFocus";

export function RefreshButton() {
  const refresh = useRefresh();
  const handleFocusRefresh = useCallback(() => {
    if (!refresh.isPending) {
      // Passive refresh (tab regained focus) — never spend tokens on a live
      // Codex usage check the user didn't ask for.
      refresh.mutate(false);
    }
  }, [refresh]);
  useRefreshOnWindowFocus(handleFocusRefresh);

  let statusText =
    "Claude Code token usage, parsed from local session transcripts.";
  if (refresh.isPending) {
    statusText = "Refreshing…";
  } else if (refresh.isError) {
    statusText = `Refresh failed: ${refresh.error instanceof Error ? refresh.error.message : String(refresh.error)}`;
  } else if (refresh.data) {
    const result = refresh.data;
    statusText =
      result.errors.length > 0
        ? `Refresh completed with errors: ${result.errors.join("; ")}`
        : `Refreshed: ${result.new_prompt_count} new prompt(s) ingested` +
          (result.usage_snapshot_count != null
            ? ", usage snapshot updated"
            : "") +
          (result.codex_usage_check_triggered
            ? ", Codex rate limits re-checked."
            : ".");
  }

  return (
    <>
      <div className="flex items-center gap-6">
        <h1 className="mb-1 text-[1.4rem] font-bold">Token Tracker </h1>
        <button
          className="ml-auto cursor-pointer rounded-md border border-[#262b36] bg-transparent px-[0.8rem] py-[0.3rem] text-[0.8rem] text-[#8a8f98]"
          disabled={refresh.isPending}
          onClick={() => refresh.mutate(true)}
          title="Also forces a fresh Codex rate-limit reading (spends a small amount of real Codex tokens)"
        >
          {refresh.isPending ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <div className="mb-6 text-[0.85rem] text-[#8a8f98]">{statusText}</div>
    </>
  );
}
