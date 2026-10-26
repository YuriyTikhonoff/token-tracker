import { useState } from "react";
import type { AccountDailyUsage, AccountLabel } from "../../api/types";

/** What a chart's bars are split by. */
export type Breakdown = "tokens" | "accounts";

/** One coloured slice of a bar, whatever the bar is split by. */
export interface Slice {
  id: string;
  label: string;
  /** Tailwind class (token types) or a CSS colour (accounts). */
  className?: string;
  color?: string;
  amount: number;
  cost?: number;
}

const ACCOUNT_COLORS = ["#56b4e9", "#e69f00", "#009e73", "#f0e442", "#cc79a7", "#d55e00"];
const UNKNOWN_COLOR = "#6b7280";
const UNKNOWN_ID = "__unknown__";

/** One slice per known account, plus "Unknown" for usage no known account owns. */
/** The colour of the account at this position in the account list, shared by every chart and bar. */
export function accountColor(index: number): string {
  return ACCOUNT_COLORS[index % ACCOUNT_COLORS.length];
}

export function accountSlices(parts: AccountDailyUsage[] | undefined, accounts: AccountLabel[]): Slice[] {
  const rows = parts ?? [];
  const slices: Slice[] = accounts.map((account, index) => {
    const part = rows.find((p) => p.account_uuid === account.account_uuid);
    return {
      id: account.account_uuid,
      label: account.label,
      color: accountColor(index),
      amount: part?.total_tokens ?? 0,
      cost: part?.cost ?? 0,
    };
  });
  const known = new Set(accounts.map((a) => a.account_uuid));
  const rest = rows.filter((p) => p.account_uuid === null || !known.has(p.account_uuid));
  if (rest.length > 0) {
    slices.push({
      id: UNKNOWN_ID,
      label: "Unknown",
      color: UNKNOWN_COLOR,
      amount: rest.reduce((sum, p) => sum + p.total_tokens, 0),
      cost: rest.reduce((sum, p) => sum + p.cost, 0),
    });
  }
  return slices;
}

export function shareLabel(amount: number, total: number): string {
  if (total <= 0 || amount <= 0) return "0%";
  const pct = (amount / total) * 100;
  return pct < 1 ? "<1%" : `${Math.round(pct)}%`;
}

/** Tooltip lines for a bar's slices: tokens, share of the bar, and cost when the slice has one. */
export function sliceLines(slices: Slice[], fmtTokens: (n: number) => string, fmtCost: (n: number) => string): string[] {
  const total = slices.reduce((sum, slice) => sum + slice.amount, 0);
  return slices.map((slice) => {
    const line = `${slice.label}: ${fmtTokens(slice.amount)} (${shareLabel(slice.amount, total)})`;
    return slice.cost === undefined ? line : `${line} · ${fmtCost(slice.cost)}`;
  });
}

/**
 * The chosen breakdown. Splitting by account only makes sense for the all-accounts
 * view with more than one account; with one account selected the chart stays as it is.
 */
export function useBreakdown(selectedAccount: string | null, accounts: AccountLabel[]) {
  const [chosen, setChosen] = useState<Breakdown>("accounts");
  const canSplit = selectedAccount === null && accounts.length > 1;
  return { breakdown: canSplit ? chosen : "tokens", canSplit, setBreakdown: setChosen } as const;
}

/** Slices to list in the legend: every one for token types, only those used somewhere for accounts. */
export function legendSlices(allBars: Slice[][]): Slice[] {
  const byId = new Map<string, Slice>();
  for (const bar of allBars) for (const slice of bar) if (!byId.has(slice.id)) byId.set(slice.id, slice);
  return [...byId.values()].filter(
    (slice) => slice.className !== undefined || allBars.some((bar) => bar.some((s) => s.id === slice.id && s.amount > 0)),
  );
}
