import type { AccountLabel, Period, Totals, WeeklyUsage } from "../api/types";
import { PERIOD_LABELS, fmtCost, fmtTokens } from "../lib/format";
import { BreakdownToggle, SliceLegend } from "./shared/AccountSplitControls";
import {
  accountSlices,
  legendSlices,
  sliceLines,
  useBreakdown,
  type Breakdown,
  type Slice,
} from "./shared/accountSplit";

interface CostBreakdownProps {
  totals: Totals;
  activePeriod: Period;
  onPeriodChange: (period: Period) => void;
  weeks: WeeklyUsage[];
  accounts: AccountLabel[];
  /** The account the dashboard is limited to; null for all of them. */
  selectedAccount: string | null;
}

const PERIODS: Period[] = ["today", "month", "all"];

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

function weekRangeLabel(weekStart: string): string {
  const start = new Date(`${weekStart}T00:00:00`);
  const end = new Date(start);
  end.setDate(end.getDate() + 6);

  const startDay = start.toLocaleDateString("en-GB", { day: "numeric" });
  const endLabel = end.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
  if (start.getMonth() === end.getMonth()) {
    return `${startDay}–${endLabel}`;
  }
  const startLabel = start.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
  return `${startLabel}–${endLabel}`;
}

function weekTooltip(week: WeeklyUsage, slices: Slice[]): string {
  return [
    `Week of ${weekRangeLabel(week.week_start)} — ${fmtTokens(week.total_tokens)} tokens, ${fmtCost(week.cost)}`,
    ...sliceLines(slices, fmtTokens, fmtCost),
  ].join("\n");
}

/** The slices of one bar, bottom to top, for the chosen breakdown. */
function slicesOf(item: WeeklyUsage, breakdown: Breakdown, accounts: AccountLabel[]): Slice[] {
  if (breakdown === "tokens") {
    return SEGMENTS.map(({ key, label, className }) => ({ id: key, label, className, amount: item[key] }));
  }
  return accountSlices(item.by_account, accounts);
}

export function CostBreakdown({
  totals,
  activePeriod,
  onPeriodChange,
  weeks,
  accounts,
  selectedAccount,
}: CostBreakdownProps) {
  const { breakdown, canSplit, setBreakdown } = useBreakdown(selectedAccount, accounts);
  const legend = legendSlices(weeks.map((week) => slicesOf(week, breakdown, accounts)));
  const maxTotal = Math.max(1, ...weeks.map((week) => week.total_tokens));

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="text-[0.85rem] whitespace-nowrap text-[#8a8f98]">
          Estimated cost ({PERIOD_LABELS[activePeriod]}):{" "}
          <span className="font-semibold text-[#e6e6e6]">
            {fmtCost(totals.cost)}
          </span>
        </div>
        <div className="flex gap-2">
          {PERIODS.map((period) => (
            <button
              key={period}
              className={`cursor-pointer rounded-md border px-[0.8rem] py-[0.3rem] text-[0.8rem] ${
                period === activePeriod
                  ? "border-[#5b8def] bg-[#5b8def] text-white"
                  : "border-[#262b36] bg-transparent text-[#8a8f98]"
              }`}
              onClick={() => onPeriodChange(period)}
            >
              {period === "today"
                ? "Today"
                : period === "month"
                  ? "This month"
                  : "All time"}
            </button>
          ))}
        </div>
      </div>
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
        {canSplit && <BreakdownToggle value={breakdown} onChange={setBreakdown} />}
        <SliceLegend slices={legend} />
      </div>
      <div className="flex h-[210px] items-end gap-3">
        {weeks.map((week) => {
          const slices = slicesOf(week, breakdown, accounts);
          return (
          <div
            className="flex h-full min-w-0 flex-1 items-end"
            key={week.week_start}
          >
            <div
              className="flex w-full min-h-[20px] flex-col"
              style={{ height: `${(week.total_tokens / maxTotal) * 100}%` }}
            >
              <div className="mb-1 text-center text-[0.7rem] whitespace-nowrap text-[#c7cbd4] tabular-nums">
                {fmtTokens(week.total_tokens)}
              </div>
              <div
                className="flex min-h-[2px] w-full flex-1 flex-col-reverse overflow-hidden rounded-[3px]"
                title={weekTooltip(week, slices)}
              >
                {slices.map(({ id, className, color, amount }) => (
                  <div
                    key={id}
                    className={`w-full ${className ?? ""}`}
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
        {weeks.map((week) => (
          <div
            className="min-w-0 flex-1 text-center text-[0.7rem] text-[#8a8f98]"
            key={week.week_start}
          >
            <div>{weekRangeLabel(week.week_start)}</div>
            <div className="mt-0.5 tabular-nums text-[#2dd4bf]">
              {fmtCost(week.cost)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
