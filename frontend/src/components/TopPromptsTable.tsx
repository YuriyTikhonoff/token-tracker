import type { PromptTotal } from "../api/types";
import { CollapsibleSection } from "./shared/CollapsibleSection";
import { EmptyRow } from "./EmptyRow";
import { fmtCost, fmtTokens, stackedTime } from "../lib/format";

interface TopPromptsTableProps {
  prompts: PromptTotal[];
}

export function TopPromptsTable({ prompts }: TopPromptsTableProps) {
  return (
    <CollapsibleSection title="Top prompts by cost">
      <table className="w-full border-collapse text-[0.85rem]">
        <thead>
          <tr>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Prompt
            </th>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Timestamp
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
          {prompts.length === 0 ? (
            <EmptyRow colSpan={4} label="No data yet." />
          ) : (
            prompts.map((prompt) => {
              const timestamp = stackedTime(prompt.timestamp);
              return (
                <tr key={prompt.prompt_id}>
                  <td
                    className="max-w-[480px] overflow-hidden border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left text-ellipsis whitespace-nowrap text-[#c7cbd4]"
                    title={prompt.preview ?? ""}
                  >
                    {prompt.preview || "(no preview)"}
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left">
                    {timestamp && (
                      <>
                        <div>{timestamp.time}</div>
                        <div className="text-[0.75rem] text-[#8a8f98]">
                          {timestamp.date}
                        </div>
                      </>
                    )}
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right tabular-nums">
                    {fmtTokens(prompt.tokens)}
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right tabular-nums">
                    {fmtCost(prompt.cost)}
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
