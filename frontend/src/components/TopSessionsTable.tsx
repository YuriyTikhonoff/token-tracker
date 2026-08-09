import type { SessionTotal } from "../api/types";
import { CollapsibleSection } from "./shared/CollapsibleSection";
import { EmptyRow } from "./EmptyRow";
import { fmtCost, fmtTokens, stackedTime } from "../lib/format";

interface TopSessionsTableProps {
  sessions: SessionTotal[];
}

export function TopSessionsTable({ sessions }: TopSessionsTableProps) {
  return (
    <CollapsibleSection title="Top sessions by cost">
      <table className="w-full border-collapse text-[0.85rem]">
        <thead>
          <tr>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Session
            </th>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Project
            </th>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Last activity
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
          {sessions.length === 0 ? (
            <EmptyRow colSpan={5} label="No data yet." />
          ) : (
            sessions.map((session) => {
              const lastSeen = stackedTime(session.last_seen);
              return (
                <tr key={session.session_id}>
                  <td
                    className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left"
                    title={session.session_id}
                  >
                    {session.session_id.slice(0, 8)}…
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left">
                    {session.project}
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left">
                    {lastSeen && (
                      <>
                        <div>{lastSeen.time}</div>
                        <div className="text-[0.75rem] text-[#8a8f98]">
                          {lastSeen.date}
                        </div>
                      </>
                    )}
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right tabular-nums">
                    {fmtTokens(session.tokens)}
                  </td>
                  <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right tabular-nums">
                    {fmtCost(session.cost)}
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
