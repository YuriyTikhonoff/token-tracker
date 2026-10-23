import { useId } from "react";

import type { UsageSnapshotTrend } from "../api/types";
import {
  SEVERITY_COLORS,
  formatSignedDuration,
  fmtWeekday,
  fmtWeekdayTime,
  limitWindowHours,
  localTime,
  projectionLines,
} from "../lib/format";
import { OVER_PACE_COLOR, UNDER_PACE_COLOR } from "./LimitRow";

interface LimitPaceChartProps {
  snapshot: UsageSnapshotTrend;
}

const HOUR_MS = 3_600_000;
const WIDTH = 600;
const HEIGHT = 210;
const PAD = { left: 38, right: 14, top: 16, bottom: 26 };

const ACTUAL_COLOR = "#5b8def";
const PLAN_COLOR = "#8a8f98";
const GRID_COLOR = "#1d2129";
const AXIS_TEXT_COLOR = "#5c6068";

const Y_TICKS = [0, 25, 50, 75, 100];

type Point = [ms: number, pct: number];

function linePath(points: Point[], x: (ms: number) => number, y: (pct: number) => number): string {
  return points
    .map(([ms, pct], index) => `${index ? "L" : "M"}${x(ms).toFixed(1)} ${y(pct).toFixed(1)}`)
    .join("");
}

// Usage over the current limit window against an even plan (the same linear
// pace LimitRow's bar uses): grey between the lines is unused plan, yellow is
// usage over it, and the dotted line carries the current rate on to the limit
// or the reset.
export function LimitPaceChart({ snapshot }: LimitPaceChartProps) {
  const clipId = useId();
  if (!snapshot.resets_at) return null;

  const windowHours = limitWindowHours(snapshot.scope);
  const end = new Date(snapshot.resets_at).getTime();
  const start = end - windowHours * HOUR_MS;
  const now = Math.min(Math.max(Date.now(), start), end);

  const x = (ms: number) => PAD.left + ((ms - start) / (end - start)) * (WIDTH - PAD.left - PAD.right);
  const y = (pct: number) => PAD.top + (1 - pct / 100) * (HEIGHT - PAD.top - PAD.bottom);
  const planAt = (ms: number) => ((ms - start) / (end - start)) * 100;

  const actual: Point[] = [
    [start, 0],
    ...snapshot.history
      .map((point): Point => [new Date(point.captured_at).getTime(), point.pct_used])
      .filter(([ms]) => ms > start && ms < now),
    [now, Math.min(100, snapshot.pct_used)],
  ];
  const pctNow = Math.min(100, snapshot.pct_used);
  const planNow = planAt(now);
  // The gap to the plan in time, the way the limit rows show their margin:
  // plus (green) is spare time under the plan, minus (yellow) is time over it.
  const gapHours = ((planNow - pctNow) / 100) * windowHours;
  const actualPath = linePath(actual, x, y);
  const gapPath = `${actualPath}L${x(now)} ${y(planNow)}L${x(start)} ${y(0)}Z`;

  const projection = projectionLines(snapshot);
  const projectionColor = projection.severity ? SEVERITY_COLORS[projection.severity] : PLAN_COLOR;
  const rate = snapshot.rate_per_hour;
  const hitMs = rate > 0 ? now + ((100 - pctNow) / rate) * HOUR_MS : null;
  const projectionEnd = hitMs !== null ? Math.min(hitMs, end) : end;
  const projectionEndPct = Math.min(100, pctNow + (rate * (projectionEnd - now)) / HOUR_MS);
  const exhaustsBeforeReset = hitMs !== null && hitMs < end;

  const isWeekly = windowHours > 24;
  const tickStepMs = (isWeekly ? 24 : 1) * HOUR_MS;
  const xTicks: number[] = [];
  for (let ms = start; ms <= end + 1; ms += tickStepMs) xTicks.push(ms);
  const tickLabel = (ms: number, index: number) =>
    isWeekly ? (index === 0 ? fmtWeekdayTime(new Date(ms)) : fmtWeekday(new Date(ms))) : localTime(new Date(ms));

  const nowLabelOnLeft = x(now) > WIDTH - 120;
  const gapColor = gapHours >= 0 ? SEVERITY_COLORS.ok : OVER_PACE_COLOR;
  const gapX = x(now) + (nowLabelOnLeft ? -8 : 8);
  const gapY = Math.max(PAD.top + 10, (y(pctNow) + y(planNow)) / 2 + 2);

  return (
    <section className="rounded-lg border border-[#262b36] bg-[#161a23] px-6 py-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 text-[0.85rem]">
        <span className="text-[#c7cbd4]">{snapshot.scope}: fact vs plan</span>
        <span className="text-[#5c6068]">plan: even pace to the reset</span>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="block h-auto w-full"
        role="img"
        aria-label={`${snapshot.scope}: ${Math.round(pctNow)}% used, plan ${Math.round(planNow)}%`}
      >
        <defs>
          <clipPath id={`${clipId}-over`}>
            <polygon points={`${x(start)},${y(0)} ${x(end)},${y(100)} ${x(start)},${y(100)}`} />
          </clipPath>
          <clipPath id={`${clipId}-under`}>
            <polygon points={`${x(start)},${y(0)} ${x(end)},${y(100)} ${x(end)},${y(0)}`} />
          </clipPath>
        </defs>

        {Y_TICKS.map((pct) => (
          <g key={pct}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(pct)} y2={y(pct)} stroke={GRID_COLOR} />
            <text x={PAD.left - 6} y={y(pct) + 3.5} textAnchor="end" fontSize={10} fill={AXIS_TEXT_COLOR}>
              {pct}%
            </text>
          </g>
        ))}
        {xTicks.map((ms, index) => (
          <g key={ms}>
            <line x1={x(ms)} x2={x(ms)} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke={GRID_COLOR} strokeDasharray="2 3" />
            <text
              x={x(ms)}
              y={HEIGHT - PAD.bottom + 15}
              textAnchor={index === 0 ? "start" : ms >= end ? "end" : "middle"}
              fontSize={10}
              fill={AXIS_TEXT_COLOR}
            >
              {tickLabel(ms, index)}
            </text>
          </g>
        ))}
        <line
          x1={PAD.left}
          x2={WIDTH - PAD.right}
          y1={y(100)}
          y2={y(100)}
          stroke={SEVERITY_COLORS.danger}
          strokeOpacity={0.55}
          strokeDasharray="5 4"
        />

        <path d={gapPath} fill={OVER_PACE_COLOR} fillOpacity={0.22} clipPath={`url(#${clipId}-over)`} />
        <path d={gapPath} fill={UNDER_PACE_COLOR} fillOpacity={0.9} clipPath={`url(#${clipId}-under)`} />
        <line
          x1={x(start)}
          y1={y(0)}
          x2={x(end)}
          y2={y(100)}
          stroke={PLAN_COLOR}
          strokeWidth={1.5}
          strokeDasharray="6 4"
        />

        {rate > 0 && (
          <line
            x1={x(now)}
            y1={y(pctNow)}
            x2={x(projectionEnd)}
            y2={y(projectionEndPct)}
            stroke={projectionColor}
            strokeWidth={1.8}
            strokeDasharray="1.5 4"
            strokeLinecap="round"
          />
        )}
        {exhaustsBeforeReset && hitMs !== null && (
          <g>
            <circle cx={x(hitMs)} cy={y(100)} r={4} fill={projectionColor} />
            <text x={x(hitMs) - 6} y={y(100) - 6} textAnchor="end" fontSize={10.5} fill={projectionColor}>
              exhaust {isWeekly ? fmtWeekdayTime(new Date(hitMs)) : localTime(new Date(hitMs))}
            </text>
          </g>
        )}

        <path d={actualPath} fill="none" stroke={ACTUAL_COLOR} strokeWidth={2.2} strokeLinejoin="round" />
        <line x1={x(now)} x2={x(now)} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="#e6e6e6" strokeOpacity={0.35} />
        <circle cx={x(now)} cy={y(planNow)} r={3.4} fill="#161a23" stroke={PLAN_COLOR} strokeWidth={2} />
        <circle cx={x(now)} cy={y(pctNow)} r={4.2} fill={ACTUAL_COLOR} stroke="#161a23" strokeWidth={2} />
        <text
          x={gapX}
          y={gapY}
          textAnchor={nowLabelOnLeft ? "end" : "start"}
          fontSize={13}
          fontWeight={700}
          fill={gapColor}
        >
          {formatSignedDuration(gapHours)}
        </text>
        <text
          x={gapX}
          y={gapY + 13}
          textAnchor={nowLabelOnLeft ? "end" : "start"}
          fontSize={10}
          fill={AXIS_TEXT_COLOR}
        >
          {gapHours >= 0 ? "under plan" : "over plan"}
        </text>
      </svg>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[0.72rem] text-[#5c6068]">
        <LegendLine color={ACTUAL_COLOR} label="actual" />
        <LegendLine color={PLAN_COLOR} label="plan" dash="dashed" />
        <LegendLine color={projectionColor} label="at current rate" dash="dotted" />
        <LegendSwatch color={UNDER_PACE_COLOR} label="unused plan" />
        <LegendSwatch color={OVER_PACE_COLOR} label="over plan" />
      </div>
    </section>
  );
}

function LegendLine({ color, label, dash = "solid" }: { color: string; label: string; dash?: "solid" | "dashed" | "dotted" }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <i className="inline-block w-4 border-t-2" style={{ borderColor: color, borderTopStyle: dash }} />
      {label}
    </span>
  );
}

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <i className="inline-block h-2.5 w-2.5 rounded-[2px]" style={{ background: color }} />
      {label}
    </span>
  );
}
