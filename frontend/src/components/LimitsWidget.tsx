import type { CurrentSessionStats, UsageSnapshotTrend } from "../api/types";
import { LimitRow } from "./LimitRow";
import { SessionStats } from "./SessionStats";

interface LimitsWidgetProps {
  snapshots: UsageSnapshotTrend[];
  sessionStats: CurrentSessionStats | null;
}

export function LimitsWidget({ snapshots, sessionStats }: LimitsWidgetProps) {
  const visibleSnapshots = snapshots.filter(
    (snapshot) => !snapshot.scope.toLowerCase().includes("fable"),
  );
  if (visibleSnapshots.length === 0) return null;

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[0.85rem] text-[#8a8f98]">Subscription limits</div>
        <div className="text-[0.85rem] text-[#8a8f98]">
          Approximate — from local <code>claude -p "/usage"</code> snapshots
        </div>
      </div>
      <div>
        {visibleSnapshots.map((snapshot) => (
          <LimitRow key={snapshot.scope} snapshot={snapshot} />
        ))}
      </div>
      {sessionStats && <SessionStats stats={sessionStats} />}
    </div>
  );
}
