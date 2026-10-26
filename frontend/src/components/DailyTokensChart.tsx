import type { AccountDailyUsage, AccountLabel, DailyUsage } from "../api/types";
import { fmtCost, fmtCostPerMillion, fmtTokens } from "../lib/format";
import { BreakdownToggle, SliceLegend } from "./shared/AccountSplitControls";
import {
  accountSlices,
  legendSlices,
  sliceLines,
  useBreakdown,
  type Breakdown,
  type Slice,
} from "./shared/accountSplit";

interface DailyTokensChartProps {
  days: DailyUsage[];
  accounts: AccountLabel[];
  /** The account the dashboard is limited to; null for all of them. */
  selectedAccount: string | null;
}

type TokenSegmentKey =
  | "input_tokens"
  | "output_tokens"
  | "cache_creation_tokens"
  | "cache_read_tokens";

const SEGMENTS: { key: TokenSegmentKey; label: string; className: string }[] = [
  { key: "input_tokens", label: "Input", className: "bg-[#5b8def]" },
  { key: "output_tokens", label: "Output", className: "bg-[#3ecf8e]" },
  {
    key: "cache_creation_tokens",
    label: "Cache write",
    className: "bg-[#e0a94e]",
  },
  {
    key: "cache_read_tokens",
    label: "Cache read",
    className: "bg-[#a78bfa]",
  },
];

function dayLabel(dateStr: string): string {
  const date = new Date(`${dateStr}T00:00:00`);
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function dayTooltip(day: DailyUsage, label: string, slices: Slice[]): string {
  return [`${label} — ${fmtTokens(day.total_tokens)} tokens`, ...sliceLines(slices, fmtTokens, fmtCost)].join("\n");
}

const AVG_KEY = "__avg__";

function averageOfCompletedDays(days: DailyUsage[]): DailyUsage | null {
  // Ignore the last day (today), which is still in progress, and average
  // the 9 completed days before it.
  const completed = days.slice(0, -1).slice(-9);
  if (completed.length === 0) return null;

  const sums = completed.reduce(
    (acc, day) => ({
      input_tokens: acc.input_tokens + day.input_tokens,
      output_tokens: acc.output_tokens + day.output_tokens,
      cache_creation_tokens: acc.cache_creation_tokens + day.cache_creation_tokens,
      cache_read_tokens: acc.cache_read_tokens + day.cache_read_tokens,
      total_tokens: acc.total_tokens + day.total_tokens,
      cost: acc.cost + day.cost,
    }),
    {
      input_tokens: 0,
      output_tokens: 0,
      cache_creation_tokens: 0,
      cache_read_tokens: 0,
      total_tokens: 0,
      cost: 0,
    },
  );
  const n = completed.length;

  const perAccount = new Map<string | null, AccountDailyUsage>();
  for (const day of completed) {
    for (const part of day.by_account ?? []) {
      const sum = perAccount.get(part.account_uuid) ?? { ...part, input_tokens: 0, output_tokens: 0, cache_creation_tokens: 0, cache_read_tokens: 0, total_tokens: 0, cost: 0 };
      sum.input_tokens += part.input_tokens;
      sum.output_tokens += part.output_tokens;
      sum.cache_creation_tokens += part.cache_creation_tokens;
      sum.cache_read_tokens += part.cache_read_tokens;
      sum.total_tokens += part.total_tokens;
      sum.cost += part.cost;
      perAccount.set(part.account_uuid, sum);
    }
  }

  return {
    by_account: [...perAccount.values()].map((part) => ({
      account_uuid: part.account_uuid,
      input_tokens: part.input_tokens / n,
      output_tokens: part.output_tokens / n,
      cache_creation_tokens: part.cache_creation_tokens / n,
      cache_read_tokens: part.cache_read_tokens / n,
      total_tokens: part.total_tokens / n,
      cost: part.cost / n,
    })),
    date: AVG_KEY,
    input_tokens: sums.input_tokens / n,
    output_tokens: sums.output_tokens / n,
    cache_creation_tokens: sums.cache_creation_tokens / n,
    cache_read_tokens: sums.cache_read_tokens / n,
    total_tokens: sums.total_tokens / n,
    cost: sums.cost / n,
  };
}

/** The slices of one bar, bottom to top, for the chosen breakdown. */
function slicesOf(day: DailyUsage, breakdown: Breakdown, accounts: AccountLabel[]): Slice[] {
  if (breakdown === "tokens") {
    return SEGMENTS.map(({ key, label, className }) => ({ id: key, label, className, amount: day[key] }));
  }
  return accountSlices(day.by_account, accounts);
}

export function DailyTokensChart({ days, accounts, selectedAccount }: DailyTokensChartProps) {
  const { breakdown, canSplit, setBreakdown } = useBreakdown(selectedAccount, accounts);
  const avgDay = averageOfCompletedDays(days);
  const bars = avgDay ? [avgDay, ...days] : days;
  const maxTotal = Math.max(1, ...bars.map((day) => day.total_tokens));
  const legend = legendSlices(bars.map((day) => slicesOf(day, breakdown, accounts)));

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[0.85rem] text-[#8a8f98]">
          Daily tokens (last {days.length} days)
        </div>
        <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1">
          {canSplit && <BreakdownToggle value={breakdown} onChange={setBreakdown} />}
          <SliceLegend slices={legend} />
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
          const slices = slicesOf(day, breakdown, accounts);
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
                  title={dayTooltip(day, isAvg ? "Avg (last 9 days)" : dayLabel(day.date), slices)}
                >
                  {slices.map(({ id, className, color, amount }) => (
                    <div
                      key={id}
                      className={`w-full ${className ?? ""} ${isAvg ? "opacity-[0.3]" : ""}`}
                      style={{ flex: amount || 0.0001, ...(color ? { backgroundColor: color } : {}) }}
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
              <div>{isAvg ? "avg" : dayLabel(day.date)}</div>
              <div className="mt-0.5 tabular-nums text-[#5b8def]">
                {fmtCost(day.cost)}
              </div>
              <div className="mt-2 text-[0.65rem] tabular-nums text-[#5c6068]">
                {fmtCostPerMillion(day.cost, day.total_tokens)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
