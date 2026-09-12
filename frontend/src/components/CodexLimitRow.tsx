import type { CodexRateLimitTrend } from "../api/types";
import {
  SEVERITY_COLORS,
  codexPacePercent,
  formatSignedDuration,
  limitSeverity,
  projectionLines,
} from "../lib/format";

interface CodexLimitRowProps {
  snapshot: CodexRateLimitTrend;
}

// Codex's own accent (orange) stands in for LimitRow's blue "on pace" fill --
// warn/danger stay the app-wide severity colors (status colors are shared
// meaning, not per-source branding).
const BAR_FILL_COLORS: Record<ReturnType<typeof limitSeverity>, string> = {
  ok: "#d95926",
  warn: "#e0a94e",
  danger: "#e05a5a",
};

const OVER_PACE_COLOR = "#ffd23f";
const UNDER_PACE_COLOR = "#333947";

export function CodexLimitRow({ snapshot }: CodexLimitRowProps) {
  const severity = limitSeverity(snapshot.pct_used);
  const projection = projectionLines(snapshot);
  const pacePct = codexPacePercent(snapshot);

  const actualPct = Math.min(100, snapshot.pct_used);
  const onPaceFillPct = pacePct != null ? Math.min(actualPct, pacePct) : actualPct;
  const overPacePct = pacePct != null ? Math.max(0, actualPct - pacePct) : 0;
  const underPaceGapPct = pacePct != null ? Math.max(0, pacePct - actualPct) : 0;

  return (
    <div className="grid grid-cols-[340px_1fr] items-center gap-3 border-b border-[#1d2129] py-2 last:border-b-0">
      <div>
        <div className="text-[0.85rem] text-[#c7cbd4]">{snapshot.scope}</div>
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            {projection.resetLine && (
              <div className="mt-0.5 text-[0.75rem] text-[#e6e6e6]">
                {projection.resetLine}
              </div>
            )}
            {projection.exhaustionLine && (
              <div
                className="mt-0.5 text-[0.75rem]"
                style={
                  projection.severity
                    ? { color: SEVERITY_COLORS[projection.severity] }
                    : undefined
                }
              >
                {projection.exhaustionLine}
              </div>
            )}
          </div>
          {projection.marginHours != null && (
            <div
              className="text-[1.1rem] font-bold whitespace-nowrap tabular-nums"
              style={{
                color:
                  SEVERITY_COLORS[projection.marginHours < 0 ? "danger" : "ok"],
              }}
            >
              {formatSignedDuration(projection.marginHours)}
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="flex h-2 flex-1 overflow-hidden rounded-[3px] bg-[#1d2129]">
          <div
            className="h-full"
            style={{ width: `${onPaceFillPct}%`, background: BAR_FILL_COLORS[severity] }}
          />
          {overPacePct > 0 && (
            <div
              className="h-full"
              style={{ width: `${overPacePct}%`, background: OVER_PACE_COLOR }}
            />
          )}
          {underPaceGapPct > 0 && (
            <div
              className="h-full"
              style={{ width: `${underPaceGapPct}%`, background: UNDER_PACE_COLOR }}
            />
          )}
        </div>
        <div className="w-[38px] text-right font-semibold tabular-nums">
          {snapshot.pct_used.toFixed(0)}%
        </div>
      </div>
    </div>
  );
}
