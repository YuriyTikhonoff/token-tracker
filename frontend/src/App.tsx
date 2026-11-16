import { useIsMutating } from "@tanstack/react-query";
import { useState } from "react";

import type { Period } from "./api/types";
import { AccountsPanel } from "./components/AccountsOverview";
import { ByProjectTable } from "./components/ByProjectTable";
import { CodexUsageSection } from "./components/CodexUsageSection";
import { CostBreakdown } from "./components/CostBreakdown";
import { DailyTokensChart } from "./components/DailyTokensChart";
import { LimitPaceCharts } from "./components/LimitPaceCharts";
import { LimitsWidget } from "./components/LimitsWidget";
import { LoadingBar } from "./components/LoadingBar";
import { MonthlyTokensChart } from "./components/MonthlyTokensChart";
import { PromptLogTable } from "./components/PromptLogTable";
import { TopPromptsTable } from "./components/TopPromptsTable";
import { Toolbar } from "./components/Toolbar";
import { TopSessionsTable } from "./components/TopSessionsTable";
import { WidgetPreview } from "./components/WidgetPreview";
import { useDashboardData } from "./hooks/useDashboardData";
import { useOverview } from "./hooks/useOverview";
import { REFRESH_MUTATION_KEY } from "./hooks/useRefresh";
import { useSelectedAccount } from "./hooks/useSelectedAccount";

function App() {
  const [activePeriod, setActivePeriod] = useState<Period>("today");
  const [selectedAccount, setSelectedAccount] = useSelectedAccount();
  const [accountsOpen, setAccountsOpen] = useState(false);
  // The top of the page comes from the fast /api/overview and the totals and
  // charts below it from /api/data. The collapsed sections load their own
  // data when they are opened.
  const { data: overview, isFetching: isFetchingOverview } =
    useOverview(selectedAccount);
  const { data, isFetching } = useDashboardData(selectedAccount);
  const isRefreshing = useIsMutating({ mutationKey: REFRESH_MUTATION_KEY }) > 0;
  const unknownModels = data?.unknown_models ?? [];

  return (
    <div>
      {(isFetching || isFetchingOverview || isRefreshing) && <LoadingBar />}
      <Toolbar
        accounts={overview?.accounts ?? []}
        selectedAccount={selectedAccount}
        onSelectAccount={setSelectedAccount}
        unknownModels={unknownModels}
        onOpenAccounts={() => {
          setAccountsOpen(true);
          // The panel opens at the top of the page, which may be scrolled away.
          const reduceMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)",
          ).matches;
          window.scrollTo({
            top: 0,
            behavior: reduceMotion ? "auto" : "smooth",
          });
        }}
      />
      {accountsOpen && <AccountsPanel onClose={() => setAccountsOpen(false)} />}
      {overview && (
        <>
          <div className="flex flex-col gap-6 lg:flex-row [&>*]:min-w-0 [&>*]:flex-1">
            <LimitsWidget
              snapshots={overview.usage_snapshots}
              accounts={overview.accounts}
              selectedAccount={selectedAccount}
              weeklyByAccount={overview.weekly_limits_by_account ?? []}
            />
            <DailyTokensChart
              days={overview.daily_usage}
              accounts={overview.accounts}
              selectedAccount={selectedAccount}
              approximateCosts={unknownModels.length > 0}
            />
          </div>
          <LimitPaceCharts snapshots={overview.usage_snapshots} />
        </>
      )}
      {!data && (
        <div className="mt-6 text-[0.8rem] text-[#8a8f98]">
          Loading the totals and charts…
        </div>
      )}
      {data && (
        <>
          <CodexUsageSection />
          <div className="flex flex-col gap-6 lg:flex-row [&>*]:min-w-0 [&>*]:flex-1">
            <CostBreakdown
              totals={data.totals_by_period[activePeriod]}
              activePeriod={activePeriod}
              onPeriodChange={setActivePeriod}
              weeks={data.weekly_usage}
              accounts={overview?.accounts ?? []}
              selectedAccount={selectedAccount}
            />
            <MonthlyTokensChart
              months={data.monthly_usage}
              accounts={overview?.accounts ?? []}
              selectedAccount={selectedAccount}
            />
          </div>
          <PromptLogTable account={selectedAccount} />
          <ByProjectTable account={selectedAccount} />
          <TopSessionsTable account={selectedAccount} />
          <TopPromptsTable account={selectedAccount} />
          <WidgetPreview />
        </>
      )}
    </div>
  );
}

export default App;
