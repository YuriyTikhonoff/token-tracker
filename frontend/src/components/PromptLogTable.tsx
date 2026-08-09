import type { PromptLogEntry } from "../api/types";
import { CollapsibleSection } from "./shared/CollapsibleSection";
import { EmptyRow } from "./EmptyRow";
import { fmtCost, fmtTokens, stackedTime } from "../lib/format";

interface PromptLogTableProps {
  entries: PromptLogEntry[];
  total: number;
}

export function PromptLogTable({ entries, total }: PromptLogTableProps) {
  const subtitle =
    total > entries.length
      ? `(most recent ${entries.length} of ${total})`
      : `(${total} total, most recent first)`;

  return (
    <CollapsibleSection
      title="Prompt log"
      subtitle={
        <span className="text-[0.85rem] text-[#8a8f98]">{subtitle}</span>
      }
    >
      <table className="w-full border-collapse text-[0.85rem]">
        <thead>
          <tr>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Time
            </th>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Session
            </th>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Prompt
            </th>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right font-medium text-[#8a8f98] tabular-nums">
              Tokens
            </th>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right font-medium text-[#8a8f98] tabular-nums">
              Est. cost
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.length === 0 ? (
            <EmptyRow colSpan={5} label="No data yet." />
          ) : (
            entries.map((entry) => {
              const time = stackedTime(entry.timestamp);
              return (
                <tr
                  key={`${entry.session_id}-${entry.timestamp}-${entry.prompt_id}`}
                >
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left">
                    {time && (
                      <>
                        <div>{time.time}</div>
                        <div className="text-[0.75rem] text-[#8a8f98]">
                          {time.date}
                        </div>
                      </>
                    )}
                  </td>
                  <td
                    className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left"
                    title={entry.session_id}
                  >
                    {entry.session_id.slice(0, 8)}…
                  </td>
                  <td
                    className="max-w-[480px] overflow-hidden border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left text-ellipsis whitespace-nowrap text-[#c7cbd4]"
                    title={entry.preview ?? ""}
                  >
                    {entry.preview || "(no preview)"}
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right tabular-nums">
                    {fmtTokens(entry.tokens)}
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right tabular-nums">
                    {fmtCost(entry.cost)}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </CollapsibleSection>
  );
}
