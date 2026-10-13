// Straight TS port of dashboard.py's inline formatting helpers — same
// names/logic as the original vanilla-JS version so behavior is easy to
// diff. projectionLines returns a typed object instead of building HTML
// strings, since React renders JSX rather than innerHTML.
import type {
  CodexRateLimitTrend,
  CurrentSessionStats,
  Period,
  UsageSnapshotTrend,
} from "../api/types";

// The zone times are shown in. It starts as the browser's own and is replaced
// by the backend's configured zone as soon as data arrives, so "today" in the
// charts and the clock times agree with how the backend cut the numbers.
let displayTimeZone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;

export function setDisplayTimeZone(timeZone: string): void {
  displayTimeZone = timeZone;
}

export const PERIOD_LABELS: Record<Period, string> = {
  today: "today",
  month: "this month",
  all: "all time",
};

export function fmtTokens(tokenCount: number): string {
  if (tokenCount > 1_000_000) {
    const millions = tokenCount / 1_000_000;
    const decimals = millions < 10 ? 2 : 1;
    return (
      millions.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }) + " mln"
    );
  }
  if (tokenCount >= 1000) {
    return (
      (tokenCount / 1000).toLocaleString(undefined, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }) + "k"
    );
  }
  return tokenCount.toLocaleString();
}

export function fmtCost(costValue: number): string {
  return (
    "$" +
    costValue.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

export function fmtCostPerMillion(cost: number, tokenCount: number): string {
  if (tokenCount <= 0) return "—";
  return fmtCost((cost / tokenCount) * 1_000_000) + "/mln";
}

export interface StackedTime {
  time: string;
  date: string;
}

export function stackedTime(iso: string | null): StackedTime | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (isNaN(date.getTime())) return { time: iso, date: "" };
  const time = date.toLocaleTimeString("en-GB", {
    timeZone: displayTimeZone,
    hour: "2-digit",
    minute: "2-digit",
  });
  const dateStr = date.toLocaleDateString("en-CA", {
    timeZone: displayTimeZone,
  });
  return { time, date: dateStr };
}

export function fmtResetsAt(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (isNaN(date.getTime())) return "";
  const dateStr = date.toLocaleDateString("en-GB", {
    timeZone: displayTimeZone,
    day: "numeric",
    month: "short",
  });
  const timeStr = date.toLocaleTimeString("en-GB", {
    timeZone: displayTimeZone,
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${dateStr} ${timeStr}`;
}

export function localDayLabel(date: Date): string {
  const dateStr = date.toLocaleDateString("en-CA", {
    timeZone: displayTimeZone,
  });
  const todayStr = new Date().toLocaleDateString("en-CA", {
    timeZone: displayTimeZone,
  });
  const yesterdayStr = new Date(Date.now() - 86_400_000).toLocaleDateString(
    "en-CA",
    { timeZone: displayTimeZone },
  );
  if (dateStr === todayStr) return "Today";
  if (dateStr === yesterdayStr) return "Yesterday";
  return date.toLocaleDateString("en-GB", {
    timeZone: displayTimeZone,
    day: "numeric",
    month: "short",
  });
}

export function localTime(date: Date): string {
  return date.toLocaleTimeString("en-GB", {
    timeZone: displayTimeZone,
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtDuration(minutesTotal: number): string {
  const sign = minutesTotal < 0 ? "-" : "";
  const absMinutes = Math.round(Math.abs(minutesTotal));
  const hours = Math.floor(absMinutes / 60);
  const minutes = absMinutes % 60;
  return `${sign}${hours} h ${String(minutes).padStart(2, "0")} min`;
}

export type Severity = "ok" | "warn" | "danger";

export function limitSeverity(pctUsed: number): Severity {
  if (pctUsed >= 90) return "danger";
  if (pctUsed >= 70) return "warn";
  return "ok";
}

export const SEVERITY_COLORS: Record<Severity, string> = {
  ok: "#3ecf8e",
  warn: "#e0a94e",
  danger: "#e05a5a",
};

const SESSION_WINDOW_HOURS = 5;
const WEEKLY_WINDOW_HOURS = 24 * 7;

// Scope names come verbatim from `claude -p "/usage"` (see usage_snapshot.py),
// not a stable identifier -- mirrors the backend's best-effort match in
// queries.py's _is_weekly_scope.
function isWeeklyScope(scope: string): boolean {
  return scope.toLowerCase().includes("week");
}

// % of the window's linear allowance elapsed so far, e.g. 1h into a 5h
// session window is 20 -- the "on-pace" reference point for LimitRow's bar.
// Null when there's no resets_at to anchor the window against.
export function pacePercent(snapshot: UsageSnapshotTrend): number | null {
  if (!snapshot.resets_at) return null;
  const windowHours = isWeeklyScope(snapshot.scope)
    ? WEEKLY_WINDOW_HOURS
    : SESSION_WINDOW_HOURS;
  const resetsAt = new Date(snapshot.resets_at).getTime();
  const windowStartMs = resetsAt - windowHours * 3_600_000;
  const elapsedHours = (Date.now() - windowStartMs) / 3_600_000;
  const clampedElapsedHours = Math.min(Math.max(elapsedHours, 0), windowHours);
  return (clampedElapsedHours / windowHours) * 100;
}

// Codex's rate-limit snapshots (see codex_ingest.py) carry window_minutes
// directly rather than needing a scope-name guess, so this is the same
// "elapsed fraction of the window" math as pacePercent above without the
// isWeeklyScope heuristic.
export function codexPacePercent(snapshot: CodexRateLimitTrend): number | null {
  if (!snapshot.resets_at) return null;
  const windowHours = snapshot.window_minutes / 60;
  const resetsAt = new Date(snapshot.resets_at).getTime();
  const windowStartMs = resetsAt - windowHours * 3_600_000;
  const elapsedHours = (Date.now() - windowStartMs) / 3_600_000;
  const clampedElapsedHours = Math.min(Math.max(elapsedHours, 0), windowHours);
  return (clampedElapsedHours / windowHours) * 100;
}

export function projectionSeverity(hoursToLimit: number): Severity {
  if (hoursToLimit < 24) return "danger";
  if (hoursToLimit < 72) return "warn";
  return "ok";
}

// For a negative margin (exhaustion lands before reset): the longer that stretch
// of being capped out, the worse — opposite direction from projectionSeverity,
// where a *smaller* number means more urgent.
export function marginOverrunSeverity(overrunHours: number): Severity {
  if (overrunHours > 24) return "danger";
  return "warn";
}

export function formatDurationLabel(hoursToLimit: number): string {
  if (hoursToLimit < 1) return `${Math.round(hoursToLimit * 60)}m`;
  if (hoursToLimit < 24) return `${hoursToLimit.toFixed(1)}h`;
  const days = Math.floor(hoursToLimit / 24);
  const remainingHours = hoursToLimit - days * 24;
  return `${days}d ${remainingHours.toFixed(1)}h`;
}

export function formatSignedDuration(hours: number): string {
  const sign = hours < 0 ? "-" : "+";
  return sign + formatDurationLabel(Math.abs(hours));
}

// How long ago a timestamp was, for labeling a *projected* value (e.g.
// Codex's rate-limit pct_used, which keeps climbing between polls via
// _extrapolate_pct_used even with zero new activity) so it isn't mistaken
// for a live reading.
export function ageLabel(iso: string): string {
  const elapsedMinutes = (Date.now() - new Date(iso).getTime()) / 60_000;
  if (elapsedMinutes < 1) return "just now";
  if (elapsedMinutes < 60) return `${Math.round(elapsedMinutes)}m ago`;
  const elapsedHours = elapsedMinutes / 60;
  if (elapsedHours < 24) return `${elapsedHours.toFixed(1)}h ago`;
  return `${Math.floor(elapsedHours / 24)}d ago`;
}

export interface ProjectionLines {
  resetLine: string | null;
  exhaustionLine: string | null;
  severity: Severity | null;
  marginHours: number | null;
}

// Shape shared by UsageSnapshotTrend (Claude) and CodexRateLimitTrend (Codex)
// -- projectionLines only ever reads these two fields, so either satisfies it.
interface ResetProjectable {
  resets_at: string | null;
  hours_to_limit: number | null;
}

export function projectionLines(snapshot: ResetProjectable): ProjectionLines {
  const resetsAt = snapshot.resets_at ? new Date(snapshot.resets_at) : null;
  const hoursToReset = resetsAt
    ? (resetsAt.getTime() - Date.now()) / 3_600_000
    : null;
  const resetLine = resetsAt
    ? hoursToReset !== null && hoursToReset <= 0
      ? `reset overdue (${fmtResetsAt(snapshot.resets_at)})`
      : `reset    in ~${formatDurationLabel(hoursToReset as number)} (${fmtResetsAt(snapshot.resets_at)})`
    : null;

  if (snapshot.hours_to_limit == null) {
    return {
      resetLine,
      exhaustionLine: resetLine ? null : "not enough data yet for a projection",
      severity: null,
      marginHours: null,
    };
  }

  const hoursToLimit = snapshot.hours_to_limit;
  const limitEta = new Date(Date.now() + hoursToLimit * 3_600 * 1000);
  const label = formatDurationLabel(hoursToLimit);
  const exhaustionLine = `exhaust in ~${label} (${fmtResetsAt(limitEta.toISOString())})`;
  const marginHours = resetsAt
    ? (limitEta.getTime() - resetsAt.getTime()) / 3_600_000
    : null;
  // Green only when exhaustion is projected to land at/after the reset (margin >= 0);
  // a negative margin means the limit will be hit before the window resets, which is
  // always bad regardless of how far off in absolute time that is.
  const severity =
    marginHours === null
      ? projectionSeverity(hoursToLimit)
      : marginHours >= 0
        ? "ok"
        : marginOverrunSeverity(-marginHours);

  return { resetLine, exhaustionLine, severity, marginHours };
}

export interface SessionStatsView {
  windowLabel: string;
  tokensLabel: string;
  burnRateLabel: string;
  exhaustionText: string;
  exhaustionClass: "" | "text-ok" | "text-warn" | "text-danger";
}

export function buildSessionStatsView(
  stats: CurrentSessionStats,
): SessionStatsView {
  const startDate = new Date(stats.session_started_at);
  const resetsDate = new Date(stats.resets_at);
  const remainingMinutes = (resetsDate.getTime() - Date.now()) / 60_000;
  const windowLabel =
    `${localTime(startDate)} → ${localTime(resetsDate)}` +
    ` (${remainingMinutes >= 0 ? fmtDuration(remainingMinutes) + " left" : "reset overdue"})`;

  let exhaustionText = "not enough data";
  let exhaustionClass: SessionStatsView["exhaustionClass"] = "";
  if (stats.projected_exhaustion_at) {
    const exhaustionDate = new Date(stats.projected_exhaustion_at);
    const marginMinutes =
      (exhaustionDate.getTime() - resetsDate.getTime()) / 60_000;
    const clockLabel = `${localDayLabel(exhaustionDate)} ${localTime(exhaustionDate)}`;
    if (marginMinutes < 0) {
      exhaustionClass = "text-danger";
      exhaustionText = `~${clockLabel} (before reset)`;
    } else if (marginMinutes < 30) {
      exhaustionClass = "text-warn";
      exhaustionText = `~${clockLabel} (${fmtDuration(marginMinutes)} after reset)`;
    } else {
      exhaustionClass = "text-ok";
      exhaustionText = `~${clockLabel} (${fmtDuration(marginMinutes)} after reset)`;
    }
  }

  const costPerHour =
    stats.session_tokens > 0
      ? (stats.session_cost / stats.session_tokens) * stats.tokens_per_hour
      : 0;

  return {
    windowLabel,
    tokensLabel: `${fmtTokens(stats.session_tokens)} (${fmtCost(stats.session_cost)})`,
    burnRateLabel: `${fmtTokens(stats.tokens_per_hour)} tokens/hr (${fmtCost(costPerHour)}/hr)`,
    exhaustionText,
    exhaustionClass,
  };
}
