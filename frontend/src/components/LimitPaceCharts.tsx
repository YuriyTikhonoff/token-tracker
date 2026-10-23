import type { UsageSnapshotTrend } from "../api/types";
import { visibleSnapshots } from "../lib/format";
import { LimitPaceChart } from "./LimitPaceChart";

interface LimitPaceChartsProps {
  snapshots: UsageSnapshotTrend[];
}

// One section per limit (session, week), side by side; they stack on a narrow screen.
export function LimitPaceCharts({ snapshots }: LimitPaceChartsProps) {
  const visible = visibleSnapshots(snapshots);
  if (visible.length === 0) return null;

  return (
    <div className="mb-8 grid gap-6 lg:grid-cols-2 [&>*]:min-w-0">
      {visible.map((snapshot) => (
        <LimitPaceChart key={snapshot.scope} snapshot={snapshot} />
      ))}
    </div>
  );
}
