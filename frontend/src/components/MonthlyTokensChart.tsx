import type { MonthlyUsage } from "../api/types";
import { fmtCost, fmtTokens } from "../lib/format";

interface MonthlyTokensChartProps {
  months: MonthlyUsage[];
}

type TokenSegmentKey =
  | "input_tokens"
  | "output_tokens"
  | "cache_creation_tokens"
  | "cache_read_tokens";

const SEGMENTS: { key: TokenSegmentKey; label: string; className: string }[] = [
  { key: "input_tokens", label: "Input", className: "bg-[#f472b6]" },
  { key: "output_tokens", label: "Output", className: "bg-[#2dd4bf]" },
  {
    key: "cache_creation_tokens",
    label: "Cache write",
    className: "bg-[#fbbf24]",
  },
  {
    key: "cache_read_tokens",
    label: "Cache read",
    className: "bg-[#818cf8]",
  },
];

function monthLabel(monthStart: string): string {
  const date = new Date(`${monthStart}T00:00:00`);
  return date.toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
}

function monthTooltip(month: MonthlyUsage): string {
  return [
    `${monthLabel(month.month_start)} — ${fmtTokens(month.total_tokens)} tokens, ${fmtCost(month.cost)}`,
    ...SEGMENTS.map(({ key, label }) => `${label}: ${fmtTokens(month[key])}`),
  ].join("\n");
}

export function MonthlyTokensChart({ months }: MonthlyTokensChartProps) {
  const maxTotal = Math.max(1, ...months.map((month) => month.total_tokens));

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[0.85rem] text-[#8a8f98]">
          Monthly tokens (last {months.length} months)
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
      <div className="flex h-[210px] items-end gap-3">
        {months.map((month) => (
          <div
            className="flex h-full min-w-0 flex-1 items-end"
            key={month.month_start}
          >
            <div
              className="flex w-full min-h-[20px] flex-col"
              style={{ height: `${(month.total_tokens / maxTotal) * 100}%` }}
            >
              <div className="mb-1 text-center text-[0.7rem] whitespace-nowrap text-[#c7cbd4] tabular-nums">
                {fmtTokens(month.total_tokens)}
              </div>
              <div
                className="flex min-h-[2px] w-full flex-1 flex-col-reverse overflow-hidden rounded-[3px]"
                title={monthTooltip(month)}
              >
                {SEGMENTS.map(({ key, className }) => (
                  <div
                    key={key}
                    className={`w-full ${className}`}
                    style={{ flex: month[key] || 0.0001 }}
                  />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-3">
        {months.map((month) => (
          <div
            className="min-w-0 flex-1 text-center text-[0.7rem] text-[#8a8f98]"
            key={month.month_start}
          >
            <div>{monthLabel(month.month_start)}</div>
            <div className="mt-0.5 tabular-nums text-[#2dd4bf]">
              {fmtCost(month.cost)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
