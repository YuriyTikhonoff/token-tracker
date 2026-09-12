import type { CodexDailyUsage } from "../api/types";
import { fmtTokens } from "../lib/format";

interface CodexDailyTokensChartProps {
  days: CodexDailyUsage[];
}

type CodexSegmentKey =
  | "input_tokens"
  | "cached_input_tokens"
  | "output_tokens"
  | "reasoning_output_tokens";

// Own palette, validated for CVD-safety/contrast on the app's dark card
// surface (see dataviz skill's validate_palette.js) -- distinct from the
// Claude chart's blue/green/amber/violet so the two sections read as
// separate sources at a glance.
const SEGMENTS: { key: CodexSegmentKey; label: string; className: string }[] = [
  { key: "input_tokens", label: "Input", className: "bg-[#d95926]" },
  { key: "cached_input_tokens", label: "Cached input", className: "bg-[#9085e9]" },
  { key: "output_tokens", label: "Output", className: "bg-[#c98500]" },
  { key: "reasoning_output_tokens", label: "Reasoning", className: "bg-[#199e70]" },
];

function dayLabel(dateStr: string): string {
  const date = new Date(`${dateStr}T00:00:00`);
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function dayTooltip(day: CodexDailyUsage, label: string): string {
  return [
    `${label} — ${fmtTokens(day.total_tokens)} tokens`,
    ...SEGMENTS.map(({ key, label: segLabel }) => `${segLabel}: ${fmtTokens(day[key])}`),
  ].join("\n");
}

const AVG_KEY = "__avg__";

function averageOfCompletedDays(days: CodexDailyUsage[]): CodexDailyUsage | null {
  // Ignore the last day (today), which is still in progress, and average
  // the 9 completed days before it.
  const completed = days.slice(0, -1).slice(-9);
  if (completed.length === 0) return null;

  const sums = completed.reduce(
    (acc, day) => ({
      input_tokens: acc.input_tokens + day.input_tokens,
      cached_input_tokens: acc.cached_input_tokens + day.cached_input_tokens,
      output_tokens: acc.output_tokens + day.output_tokens,
      reasoning_output_tokens: acc.reasoning_output_tokens + day.reasoning_output_tokens,
      total_tokens: acc.total_tokens + day.total_tokens,
    }),
    {
      input_tokens: 0,
      cached_input_tokens: 0,
      output_tokens: 0,
      reasoning_output_tokens: 0,
      total_tokens: 0,
    },
  );
  const n = completed.length;

  return {
    date: AVG_KEY,
    input_tokens: sums.input_tokens / n,
    cached_input_tokens: sums.cached_input_tokens / n,
    output_tokens: sums.output_tokens / n,
    reasoning_output_tokens: sums.reasoning_output_tokens / n,
    total_tokens: sums.total_tokens / n,
  };
}

export function CodexDailyTokensChart({ days }: CodexDailyTokensChartProps) {
  const avgDay = averageOfCompletedDays(days);
  const bars = avgDay ? [avgDay, ...days] : days;
  const maxTotal = Math.max(1, ...bars.map((day) => day.total_tokens));

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[0.85rem] text-[#8a8f98]">
          Codex daily tokens (last {days.length} days)
        </div>
        <div className="flex gap-4">
          {SEGMENTS.map(({ key, label, className }) => (
            <div
              className="flex items-center gap-[0.4rem] text-[0.75rem] text-[#8a8f98]"
              key={key}
            >
              <span
                className={`inline-block h-2.5 w-2.5 rounded-[2px] ${className}`}
              />
              {label}
            </div>
          ))}
        </div>
      </div>
      <div className="relative flex h-[210px] items-end gap-3">
        {avgDay && (
          <div
            className="pointer-events-none absolute right-0 left-0 border-t border-dashed border-white/35"
            style={{ bottom: `${((avgDay.total_tokens / maxTotal) * 100) - 8}%` }}
          />
        )}
        {bars.map((day) => {
          const isAvg = day.date === AVG_KEY;
          return (
            <div
              className="flex h-full min-w-0 flex-1 items-end"
              key={day.date}
            >
              <div
                className="flex w-full min-h-[20px] flex-col"
                style={{ height: `${(day.total_tokens / maxTotal) * 100}%` }}
              >
                <div className="mb-1 text-center text-[0.7rem] whitespace-nowrap text-[#c7cbd4] tabular-nums">
                  {fmtTokens(day.total_tokens)}
                </div>
                <div
                  className={`flex min-h-[2px] w-full flex-1 flex-col-reverse overflow-hidden rounded-[3px] ${isAvg ? "bg-white/[0.06]" : ""}`}
                  title={dayTooltip(day, isAvg ? "Avg (last 9 days)" : dayLabel(day.date))}
                >
                  {SEGMENTS.map(({ key, className }) => (
                    <div
                      key={key}
                      className={`w-full ${className} ${isAvg ? "opacity-[0.3]" : ""}`}
                      style={{ flex: day[key] || 0.0001 }}
                    />
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex gap-3">
        {bars.map((day) => {
          const isAvg = day.date === AVG_KEY;
          return (
            <div
              className="min-w-0 flex-1 text-center text-[0.7rem] text-[#8a8f98]"
              key={day.date}
            >
              {isAvg ? "avg" : dayLabel(day.date)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
