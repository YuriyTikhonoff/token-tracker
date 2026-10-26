import type { AccountLabel, MonthlyUsage } from "../api/types";
import { BreakdownToggle, SliceLegend } from "./shared/AccountSplitControls";
import {
  accountSlices,
  legendSlices,
  useBreakdown,
  type Breakdown,
  type Slice,
} from "./shared/accountSplit";
import { useBarTip } from "./shared/barTip";
import { fmtCost, fmtTokens } from "../lib/format";

interface MonthlyTokensChartProps {
  months: MonthlyUsage[];
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

function monthHeading(month: MonthlyUsage): string {
  return `${monthLabel(month.month_start)} — ${fmtTokens(month.total_tokens)} tokens, ${fmtCost(month.cost)}`;
}

/** The slices of one bar, bottom to top, for the chosen breakdown. */
function slicesOf(item: MonthlyUsage, breakdown: Breakdown, accounts: AccountLabel[]): Slice[] {
  if (breakdown === "tokens") {
    return SEGMENTS.map(({ key, label, className }) => ({ id: key, label, className, amount: item[key] }));
  }
  return accountSlices(item.by_account, accounts);
}

export function MonthlyTokensChart({ months, accounts, selectedAccount }: MonthlyTokensChartProps) {
  const { breakdown, canSplit, setBreakdown } = useBreakdown(selectedAccount, accounts);
  const { bind, node } = useBarTip();
  const legend = legendSlices(months.map((month) => slicesOf(month, breakdown, accounts)));
  const maxTotal = Math.max(1, ...months.map((month) => month.total_tokens));

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      {node}
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[0.85rem] text-[#8a8f98]">
          Monthly tokens (last {months.length} months)
        </div>
        <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1">
          {canSplit && <BreakdownToggle value={breakdown} onChange={setBreakdown} />}
          <SliceLegend slices={legend} />
        </div>
      </div>
      <div className="flex h-[210px] items-end gap-3">
        {months.map((month) => {
          const slices = slicesOf(month, breakdown, accounts);
          return (
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
                {...bind(monthHeading(month), slices)}
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
