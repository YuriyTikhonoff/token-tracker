import type { ProjectTotal } from "../api/types";
import { Bar } from "./Bar";
import { EmptyRow } from "./EmptyRow";
import { fmtCost, fmtTokens } from "../lib/format";
import { CollapsibleSection } from "./shared/CollapsibleSection";

interface ByProjectTableProps {
  projects: ProjectTotal[];
}

export function ByProjectTable({ projects }: ByProjectTableProps) {
  const maxCost = Math.max(0, ...projects.map((project) => project.cost));

  return (
    <CollapsibleSection title="By project">
      <table className="w-full border-collapse text-[0.85rem]">
        <thead>
          <tr>
            <th className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left font-medium text-[#8a8f98]">
              Project
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
          {projects.length === 0 ? (
            <EmptyRow colSpan={3} label="No data yet — run ingest.py first." />
          ) : (
            projects.map((project) => (
              <tr key={project.project}>
                <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-left">
                  {project.project}
                  <Bar value={project.cost} max={maxCost} />
                </td>
                <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right tabular-nums">
                  {fmtTokens(project.tokens)}
                </td>
                <td className="border-b border-[#1d2129] px-[0.6rem] py-[0.4rem] text-right tabular-nums">
                  {fmtCost(project.cost)}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </CollapsibleSection>
  );
}
