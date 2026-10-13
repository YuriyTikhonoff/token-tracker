import { useState } from "react";

import type { AccountSummary } from "../api/types";
import { useUpdateAccount } from "../hooks/useUpdateAccount";
import { fmtCost, fmtTokens, stackedTime } from "../lib/format";
import { Bar } from "./Bar";
import { CollapsibleSection } from "./shared/CollapsibleSection";

interface AccountsOverviewProps {
  accounts: AccountSummary[];
}

const HEAD =
  "border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] font-medium text-[#8a8f98]";
const CELL = "border-b border-[#1d2129] px-[0.6rem] py-[0.4rem]";

function AccountLabel({ account }: { account: AccountSummary }) {
  const update = useUpdateAccount();
  const [draft, setDraft] = useState<string | null>(null);

  function commit() {
    const label = draft?.trim();
    setDraft(null);
    if (label && label !== account.label) {
      update.mutate({ accountUuid: account.account_uuid, label });
    }
  }

  if (draft !== null) {
    return (
      <input
        autoFocus
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") commit();
          if (event.key === "Escape") setDraft(null);
        }}
        className="w-40 rounded border border-[#262b36] bg-transparent px-1 text-[#c7cbd4]"
      />
    );
  }
  return (
    <button
      className="cursor-text bg-transparent p-0 text-left text-[#c7cbd4]"
      title="Click to rename"
      onClick={() => setDraft(account.label)}
    >
      {account.label}
    </button>
  );
}

export function AccountsOverview({ accounts }: AccountsOverviewProps) {
  const update = useUpdateAccount();
  const combined = accounts.reduce(
    (sum, account) => ({
      today: sum.today + account.today.total_tokens,
      month: sum.month + account.month.total_tokens,
      all: sum.all + account.all.total_tokens,
      cost: sum.cost + account.all.cost,
    }),
    { today: 0, month: 0, all: 0, cost: 0 },
  );

  return (
    <CollapsibleSection
      title="Accounts"
      subtitle={
        <span className="text-[0.8rem] text-[#8a8f98]">
          who used this machine
        </span>
      }
      defaultExpanded={true}
    >
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[0.85rem]">
          <thead>
            <tr>
              <th className={`${HEAD} text-left`}>Account</th>
              <th className={`${HEAD} text-right tabular-nums`}>Today</th>
              <th className={`${HEAD} text-right tabular-nums`}>Month</th>
              <th className={`${HEAD} text-right tabular-nums`}>All time</th>
              <th className={`${HEAD} text-right tabular-nums`}>Est. cost</th>
              <th className={`${HEAD} text-right`}>Last active</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((account) => {
              const lastActive = stackedTime(account.last_active);
              return (
                <tr key={account.account_uuid}>
                  <td className={`${CELL} text-left`}>
                    <AccountLabel account={account} />
                    {account.is_default ? (
                      <span
                        className="ml-2 text-[0.7rem] text-[#8a8f98]"
                        title="Owns usage from before accounts were tracked"
                      >
                        default
                      </span>
                    ) : (
                      <button
                        className="ml-2 cursor-pointer bg-transparent p-0 text-[0.7rem] text-[#8a8f98] underline"
                        onClick={() =>
                          update.mutate({
                            accountUuid: account.account_uuid,
                            isDefault: true,
                          })
                        }
                      >
                        make default
                      </button>
                    )}
                    <div className="text-[0.75rem] text-[#8a8f98]">
                      {account.email} · {account.session_count} session(s)
                    </div>
                    <Bar value={account.all.cost} max={combined.cost} />
                  </td>
                  <td className={`${CELL} text-right tabular-nums`}>
                    {fmtTokens(account.today.total_tokens)}
                  </td>
                  <td className={`${CELL} text-right tabular-nums`}>
                    {fmtTokens(account.month.total_tokens)}
                  </td>
                  <td className={`${CELL} text-right tabular-nums`}>
                    {fmtTokens(account.all.total_tokens)}
                  </td>
                  <td className={`${CELL} text-right tabular-nums`}>
                    {fmtCost(account.all.cost)}
                    <div className="text-[0.75rem] text-[#8a8f98]">
                      {Math.round(account.cost_share * 100)}%
                    </div>
                  </td>
                  <td className={`${CELL} text-right text-[#8a8f98]`}>
                    {lastActive ? `${lastActive.date} ${lastActive.time}` : "—"}
                  </td>
                </tr>
              );
            })}
            <tr>
              <td className={`${CELL} text-left font-medium`}>Combined</td>
              <td className={`${CELL} text-right tabular-nums`}>
                {fmtTokens(combined.today)}
              </td>
              <td className={`${CELL} text-right tabular-nums`}>
                {fmtTokens(combined.month)}
              </td>
              <td className={`${CELL} text-right tabular-nums`}>
                {fmtTokens(combined.all)}
              </td>
              <td className={`${CELL} text-right tabular-nums`}>
                {fmtCost(combined.cost)}
              </td>
              <td className={CELL} />
            </tr>
          </tbody>
        </table>
      </div>
    </CollapsibleSection>
  );
}
