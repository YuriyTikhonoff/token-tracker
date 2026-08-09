import type { CurrentSessionStats } from "../api/types";
import { buildSessionStatsView } from "../lib/format";

interface SessionStatsProps {
  stats: CurrentSessionStats;
}

export function SessionStats({ stats }: SessionStatsProps) {
  const view = buildSessionStatsView(stats);

  return (
    <div className="mt-3 grid grid-cols-3 gap-4 border-t border-[#262b36] pt-3">
      <div>
        <div className="text-[0.7rem] tracking-[0.04em] text-[#8a8f98] uppercase">
          Session window
        </div>
        <div className="mt-0.5 text-[0.95rem]">{view.windowLabel}</div>
      </div>
      <div>
        <div className="text-[0.7rem] tracking-[0.04em] text-[#8a8f98] uppercase">
          Tokens used
        </div>
        <div className="mt-0.5 text-[0.95rem]">{view.tokensLabel}</div>
      </div>
      <div>
        <div className="text-[0.7rem] tracking-[0.04em] text-[#8a8f98] uppercase">
          Burn rate
        </div>
        <div className="mt-0.5 text-[0.95rem]">{view.burnRateLabel}</div>
      </div>
    </div>
  );
}
