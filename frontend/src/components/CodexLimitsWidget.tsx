import type { CodexRateLimitTrend } from "../api/types";
import { ageLabel } from "../lib/format";
import { CodexLimitRow } from "./CodexLimitRow";

interface CodexLimitsWidgetProps {
  snapshots: CodexRateLimitTrend[];
}

export function CodexLimitsWidget({ snapshots }: CodexLimitsWidgetProps) {
  if (snapshots.length === 0) return null;

  // The % shown is a live projection (extrapolated from the last real
  // reading at its observed rate/hour -- see queries.get_codex_rate_limits_trend),
  // recomputed on every poll even with zero new Codex activity. Unlike
  // Claude, Codex has no independent periodic snapshot poller, so this
  // baseline only refreshes when you actually use Codex -- surface how
  // stale it is rather than let a climbing % pass as a live reading.
  const latestCapturedAt = snapshots.reduce<string | null>(
    (latest, snapshot) => (!latest || snapshot.captured_at > latest ? snapshot.captured_at : latest),
    null,
  );

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[0.85rem] text-[#8a8f98]">Codex limits</div>
        <div className="text-[0.85rem] text-[#8a8f98]">
          Projected — last real reading{" "}
          {latestCapturedAt ? ageLabel(latestCapturedAt) : "unknown"} · from local{" "}
          <code>~/.codex</code> session logs
        </div>
      </div>
      <div>
        {snapshots.map((snapshot) => (
          <CodexLimitRow key={snapshot.scope} snapshot={snapshot} />
        ))}
      </div>
    </div>
  );
}
