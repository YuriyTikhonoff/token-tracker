// Fact against plan for one subscription limit. Pure functions, no `vscode`
// import, so they can be tested on their own. The plan is an even pace: the
// share of the window that has already passed. The margin is the same number
// the dashboard's limit row shows in large type.
import type { LimitSnapshot } from "./api";

export type Severity = "ok" | "warn" | "danger";
export type LimitKind = "session" | "week";

const HOUR_MS = 3_600_000;
const SESSION_WINDOW_HOURS = 5;
const WEEKLY_WINDOW_HOURS = 24 * 7;
// A limit that runs out within this share of the window before the reset is a
// warning; earlier than that is an error.
const WARN_SHARE_OF_WINDOW = 0.15;
const LIMIT_HIT_PCT = 99.95;
// Under half a percentage point is "on the plan".
const ON_PLAN_PP = 0.5;

export interface LimitPace {
  scope: string;
  kind: LimitKind;
  windowHours: number;
  usedPct: number;
  planPct: number;
  // used - plan, in percentage points; positive means ahead of the plan.
  diffPp: number;
  // Hours the limit lasts past the reset (positive) or runs out before it
  // (negative); null when the backend has no projection.
  marginHours: number | null;
  severity: Severity | null;
  limitHit: boolean;
  resetsAt: Date;
  exhaustAt: Date | null;
}

// Scope names come verbatim from `claude -p "/usage"`; the dashboard matches
// the weekly one by "week" in the name, so this does too.
export function limitKind(scope: string): LimitKind {
  return scope.toLowerCase().includes("week") ? "week" : "session";
}

// Model-specific weekly limits ("Current week (Fable)") are hidden, as in the
// dashboard's limits widget.
export function isShownScope(scope: string): boolean {
  return !scope.toLowerCase().includes("fable");
}

export function severityForMargin(marginHours: number, windowHours: number): Severity {
  if (marginHours >= 0) return "ok";
  return -marginHours <= windowHours * WARN_SHARE_OF_WINDOW ? "warn" : "danger";
}

// Null when the window is over (resets_at passed or unknown): the snapshot is
// then stale and there is nothing to compare against.
export function computePace(snapshot: LimitSnapshot, now: Date = new Date()): LimitPace | null {
  if (!snapshot.resets_at) return null;
  const resetsAt = new Date(snapshot.resets_at);
  if (Number.isNaN(resetsAt.getTime()) || resetsAt.getTime() <= now.getTime()) return null;

  const kind = limitKind(snapshot.scope);
  const windowHours = kind === "week" ? WEEKLY_WINDOW_HOURS : SESSION_WINDOW_HOURS;
  const startMs = resetsAt.getTime() - windowHours * HOUR_MS;
  const elapsedHours = Math.min(Math.max((now.getTime() - startMs) / HOUR_MS, 0), windowHours);
  const planPct = (elapsedHours / windowHours) * 100;
  const usedPct = Math.min(100, Math.max(0, snapshot.pct_used));
  const limitHit = usedPct >= LIMIT_HIT_PCT;

  let exhaustAt: Date | null = null;
  let marginHours: number | null = null;
  if (snapshot.hours_to_limit != null) {
    exhaustAt = new Date(now.getTime() + snapshot.hours_to_limit * HOUR_MS);
    marginHours = (exhaustAt.getTime() - resetsAt.getTime()) / HOUR_MS;
  }

  const severity = limitHit
    ? "danger"
    : marginHours === null
      ? null
      : severityForMargin(marginHours, windowHours);

  return {
    scope: snapshot.scope,
    kind,
    windowHours,
    usedPct,
    planPct,
    diffPp: usedPct - planPct,
    marginHours,
    severity,
    limitHit,
    resetsAt,
    exhaustAt,
  };
}

// The arrow follows the reserve: ▲ under the plan (it grows), ▼ over it (it
// shrinks).
export function arrow(diffPp: number): "▲" | "▼" | "=" {
  if (diffPp > ON_PLAN_PP) return "▼";
  if (diffPp < -ON_PLAN_PP) return "▲";
  return "=";
}

// One unit only, to stay short in the status bar: 47m, 3.5h, 12h, 2.7d.
export function formatMarginShort(marginHours: number): string {
  const sign = marginHours >= 0 ? "+" : "−";
  const hours = Math.abs(marginHours);
  if (hours >= WEEKLY_WINDOW_HOURS) return `${sign}1w+`;
  if (hours < 1) return `${sign}${Math.round(hours * 60)}m`;
  if (hours < 10) return `${sign}${hours.toFixed(1)}h`;
  if (hours < 24) return `${sign}${Math.round(hours)}h`;
  return `${sign}${(hours / 24).toFixed(1)}d`;
}

// The status bar text of one limit, without its name: "▲ +47m", "limit hit", "—".
export function statusText(pace: LimitPace | null): string {
  if (pace === null) return "—";
  if (pace.limitHit) return "limit hit";
  const margin = pace.marginHours === null ? "—" : formatMarginShort(pace.marginHours);
  return `${arrow(pace.diffPp)} ${margin}`;
}
