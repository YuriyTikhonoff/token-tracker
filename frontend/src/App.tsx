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
import { LimitPaceCharts } from "./components/LimitPaceCharts";
import { LimitsWidget } from "./components/LimitsWidget";
import { LoadingBar } from "./components/LoadingBar";
import { MonthlyTokensChart } from "./components/MonthlyTokensChart";
import { PromptLogTable } from "./components/PromptLogTable";
import { RefreshButton } from "./components/RefreshButton";
import { CollapsibleSection } from "./components/shared/CollapsibleSection";
import { TopPromptsTable } from "./components/TopPromptsTable";
import { TopSessionsTable } from "./components/TopSessionsTable";
import { WidgetPreview } from "./components/WidgetPreview";
import { useDashboardData } from "./hooks/useDashboardData";
import { useOverview } from "./hooks/useOverview";
import { REFRESH_MUTATION_KEY } from "./hooks/useRefresh";
import { useSelectedAccount } from "./hooks/useSelectedAccount";

function App() {
  const [activePeriod, setActivePeriod] = useState<Period>("today");
  const [selectedAccount, setSelectedAccount] = useSelectedAccount();
  // The top of the page comes from the fast /api/overview; everything below it
  // from /api/data, which takes longer. Each part appears when its data is in.
  const { data: overview, isFetching: isFetchingOverview } =
    useOverview(selectedAccount);
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
      {(isFetching || isFetchingOverview || isRefreshing) && <LoadingBar />}
      <RefreshButton lastPrompt={lastMeaningfulPrompt} />
      {data && data.unknown_models.length > 0 && (
        <div className="mb-6 text-[0.8rem] text-[#d9a441]">
          No price for {data.unknown_models.join(", ")}: counted at the default
          rate, so costs are rough. Add them to pricing.json in your data
          directory.
        </div>
      )}
      {overview && (
        <>
          {overview.accounts.length > 0 && (
            <AccountSwitcher
              accounts={overview.accounts}
              selected={selectedAccount}
              onSelect={setSelectedAccount}
            />
          )}
          {data && data.accounts.length > 0 && (
            <AccountsOverview accounts={data.accounts} />
          )}
          <div className="flex flex-col gap-6 lg:flex-row [&>*]:min-w-0 [&>*]:flex-1">
            <LimitsWidget
              snapshots={overview.usage_snapshots}
              sessionStats={overview.current_session_stats}
            />
            <DailyTokensChart days={overview.daily_usage} />
          </div>
          <LimitPaceCharts snapshots={overview.usage_snapshots} />
        </>
      )}
      {!data && (
        <div className="mt-6 text-[0.8rem] text-[#8a8f98]">
          Loading the totals, tables and prompt log…
        </div>
      )}
      {data && (
        <>
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
