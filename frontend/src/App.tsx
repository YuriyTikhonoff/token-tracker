import { useIsMutating } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import type { Period } from "./api/types";
import { AccountsOverview } from "./components/AccountsOverview";
import { AccountSwitcher } from "./components/AccountSwitcher";
import { ByProjectTable } from "./components/ByProjectTable";
import { CodexDailyTokensChart } from "./components/CodexDailyTokensChart";
import { CodexLimitsWidget } from "./components/CodexLimitsWidget";
import { CostBreakdown } from "./components/CostBreakdown";
import { DailyTokensChart } from "./components/DailyTokensChart";
import { LimitsWidget } from "./components/LimitsWidget";
import { LoadingOverlay } from "./components/LoadingOverlay";
import { MonthlyTokensChart } from "./components/MonthlyTokensChart";
import { PromptLogTable } from "./components/PromptLogTable";
import { RefreshButton } from "./components/RefreshButton";
import { CollapsibleSection } from "./components/shared/CollapsibleSection";
import { TopPromptsTable } from "./components/TopPromptsTable";
import { TopSessionsTable } from "./components/TopSessionsTable";
import { WidgetPreview } from "./components/WidgetPreview";
import { useDashboardData } from "./hooks/useDashboardData";
import { REFRESH_MUTATION_KEY } from "./hooks/useRefresh";
import { useSelectedAccount } from "./hooks/useSelectedAccount";

function App() {
  const [activePeriod, setActivePeriod] = useState<Period>("today");
  const [selectedAccount, setSelectedAccount] = useSelectedAccount();
  const { data, isFetching } = useDashboardData(selectedAccount);
  const isRefreshing = useIsMutating({ mutationKey: REFRESH_MUTATION_KEY }) > 0;

  // Most recent prompt with an actual preview — the prompt log also contains
  // entries with no preview (e.g. tool-only turns), which aren't worth surfacing here.
  const lastMeaningfulPrompt = useMemo(
    () =>
      data?.prompt_log.find(
        (entry) => entry.preview && entry.preview.trim().length > 0,
      ) ?? null,
    [data],
  );

  return (
    <div>
      {(isFetching || isRefreshing) && <LoadingOverlay />}
      <RefreshButton lastPrompt={lastMeaningfulPrompt} />
      {data && data.unknown_models.length > 0 && (
        <div className="mb-6 text-[0.8rem] text-[#d9a441]">
          No price for {data.unknown_models.join(", ")}: counted at the default
          rate, so costs are rough. Add them to pricing.json in your data
          directory.
        </div>
      )}
      {data && (
        <>
          {data.accounts.length > 0 && (
            <>
              <AccountSwitcher
                accounts={data.accounts}
                selected={selectedAccount}
                onSelect={setSelectedAccount}
              />
              <AccountsOverview accounts={data.accounts} />
            </>
          )}
          <div className="flex flex-col gap-6 lg:flex-row [&>*]:min-w-0 [&>*]:flex-1">
            <LimitsWidget
              snapshots={data.usage_snapshots}
              sessionStats={data.current_session_stats}
            />
            <DailyTokensChart days={data.daily_usage} />
          </div>
          <CollapsibleSection title="Codex usage">
            <div className="flex flex-col gap-6 lg:flex-row [&>*]:min-w-0 [&>*]:flex-1">
              <CodexLimitsWidget snapshots={data.codex_rate_limits} />
              <CodexDailyTokensChart days={data.codex_daily_usage} />
            </div>
          </CollapsibleSection>
          <div className="flex flex-col gap-6 lg:flex-row [&>*]:min-w-0 [&>*]:flex-1">
            <CostBreakdown
              totals={data.totals_by_period[activePeriod]}
              activePeriod={activePeriod}
              onPeriodChange={setActivePeriod}
              weeks={data.weekly_usage}
            />
            <MonthlyTokensChart months={data.monthly_usage} />
          </div>
          <PromptLogTable
            entries={data.prompt_log}
            total={data.prompt_log_total}
          />
          <ByProjectTable projects={data.by_project} />
          <TopSessionsTable sessions={data.by_session} />
          <TopPromptsTable prompts={data.by_prompt} />
          <WidgetPreview />
        </>
      )}
    </div>
  );
}

export default App;
