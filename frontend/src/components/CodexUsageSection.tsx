import type { CodexSectionData } from "../api/types";
import { CodexDailyTokensChart } from "./CodexDailyTokensChart";
import { CodexLimitsWidget } from "./CodexLimitsWidget";
import { CollapsibleSection } from "./shared/CollapsibleSection";
import { SectionLoader } from "./shared/SectionLoader";

export function CodexUsageSection() {
  return (
    <CollapsibleSection title="Codex usage">
      <SectionLoader<CodexSectionData> path="codex" account={null}>
        {(codex) => (
          <div className="flex flex-col gap-6 lg:flex-row [&>*]:min-w-0 [&>*]:flex-1">
            <CodexLimitsWidget snapshots={codex.codex_rate_limits} />
            <CodexDailyTokensChart days={codex.codex_daily_usage} />
          </div>
        )}
      </SectionLoader>
    </CollapsibleSection>
  );
}
