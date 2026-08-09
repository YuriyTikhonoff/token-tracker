import { useCallback } from "react";

import { useRefresh } from "../hooks/useRefresh";
import { useRefreshOnWindowFocus } from "../hooks/useRefreshOnWindowFocus";
import type { PromptLogEntry } from "../api/types";
import { fmtCost, fmtTokens, stackedTime } from "../lib/format";

interface RefreshButtonProps {
  lastPrompt: PromptLogEntry | null;
}

export function RefreshButton({ lastPrompt }: RefreshButtonProps) {
  const refresh = useRefresh();
  const handleFocusRefresh = useCallback(() => {
    if (!refresh.isPending) {
      refresh.mutate();
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
            ? ", usage snapshot updated."
            : ".");
  }

  const lastPromptTime = lastPrompt ? stackedTime(lastPrompt.timestamp) : null;

  return (
    <>
      <div className="flex items-center gap-6">
        <h1 className="mb-1 text-[1.4rem] font-bold">Token Tracker </h1>
        <div>
          {lastPrompt && (
            <>
              <br />
              Last prompt:{" "}
              <span
                className="inline-block max-w-[420px] overflow-hidden text-ellipsis whitespace-nowrap text-[#c7cbd4] align-bottom"
                title={lastPrompt.preview ?? ""}
              >
                {lastPrompt.preview}
              </span>
              <span className="text-[#666]">
                {lastPromptTime &&
                  ` — ${lastPromptTime.date} ${lastPromptTime.time}`}
              </span>
              {" · "}
              {fmtTokens(lastPrompt.tokens)}
              {" · "}
              {fmtCost(lastPrompt.cost)}
            </>
          )}
        </div>
        <button
          className="ml-auto cursor-pointer rounded-md border border-[#262b36] bg-transparent px-[0.8rem] py-[0.3rem] text-[0.8rem] text-[#8a8f98]"
          disabled={refresh.isPending}
          onClick={() => refresh.mutate()}
        >
          {refresh.isPending ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <div className="mb-6 text-[0.85rem] text-[#8a8f98]">{statusText}</div>
    </>
  );
}
