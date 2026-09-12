import type { CodexRateLimitTrend } from "../api/types";
import { CodexLimitRow } from "./CodexLimitRow";

interface CodexLimitsWidgetProps {
  snapshots: CodexRateLimitTrend[];
}

export function CodexLimitsWidget({ snapshots }: CodexLimitsWidgetProps) {
  if (snapshots.length === 0) return null;

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[0.85rem] text-[#8a8f98]">Codex limits</div>
        <div className="text-[0.85rem] text-[#8a8f98]">
          From local <code>~/.codex</code> session logs
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
