import type { AccountLabel, AccountWeeklyLimits, UsageSnapshotTrend } from "../api/types";
import { isWeeklyScope, visibleSnapshots } from "../lib/format";
import { LimitRow } from "./LimitRow";
import { accountColor } from "./shared/accountSplit";

interface LimitsWidgetProps {
  snapshots: UsageSnapshotTrend[];
  accounts: AccountLabel[];
  /** The account the dashboard is limited to; null for all of them. */
  selectedAccount: string | null;
  weeklyByAccount: AccountWeeklyLimits[];
}

/**
 * The weekly limit of each account, under one heading, in the accounts' chart colours. The account
 * Claude Code is logged into now comes first, and the others have smaller text, so the one being
 * spent stands out. When no account is known to be logged in, the order is the usual one and every
 * row has the usual size.
 */
function WeeklyByAccount({ scope, accounts, weeklyByAccount }: { scope: string; accounts: AccountLabel[]; weeklyByAccount: AccountWeeklyLimits[] }) {
  const anyCurrent = accounts.some((account) => account.is_current);
  const rows = accounts.flatMap((account, index) => {
    const own = weeklyByAccount.find((entry) => entry.account_uuid === account.account_uuid);
    const snapshot = visibleSnapshots(own?.snapshots ?? []).find((s) => isWeeklyScope(s.scope));
    // The colour follows the account's place in the list, as in the charts, before the current one moves up.
    return snapshot ? [{ account, snapshot, color: accountColor(index) }] : [];
  });
  rows.sort((a, b) => Number(b.account.is_current) - Number(a.account.is_current));
  return (
    <div className="border-b border-[#1d2129] py-2 last:border-b-0">
      <div className="text-[0.85rem] text-[#c7cbd4]">{scope}</div>
      <div className="mt-1 pl-3">
        {rows.map(({ account, snapshot, color }) => (
          <LimitRow
            key={account.account_uuid}
            snapshot={snapshot}
            account={{ label: account.label, color }}
            compact={anyCurrent && !account.is_current}
          />
        ))}
      </div>
    </div>
  );
}

export function LimitsWidget({ snapshots, accounts, selectedAccount, weeklyByAccount }: LimitsWidgetProps) {
  const visible = visibleSnapshots(snapshots);
  if (visible.length === 0) return null;

  // All accounts together: the combined weekly entry mixes the accounts' readings, so each account gets its own.
  const split = selectedAccount === null && accounts.length > 1 && weeklyByAccount.length > 0;

  return (
    <div className="mb-8 rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[0.85rem] text-[#8a8f98]">Subscription limits</div>
        <div className="text-[0.85rem] text-[#8a8f98]">
          Approximate — from local <code>claude -p "/usage"</code> snapshots
        </div>
      </div>
      <div>
        {visible.map((snapshot) =>
          split && isWeeklyScope(snapshot.scope) ? (
            <WeeklyByAccount key={snapshot.scope} scope={snapshot.scope} accounts={accounts} weeklyByAccount={weeklyByAccount} />
          ) : (
            <LimitRow key={snapshot.scope} snapshot={snapshot} />
          ),
        )}
      </div>
    </div>
  );
}
