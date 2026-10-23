export function fmtTokens(tokenCount: number): string {
  if (tokenCount >= 1_000_000) return `${(tokenCount / 1_000_000).toFixed(1)}M`;
  if (tokenCount >= 1_000) return `${Math.round(tokenCount / 1_000)}k`;
  return String(Math.round(tokenCount));
}

export function fmtCost(cost: number): string {
  return `$${cost.toFixed(2)}`;
}

export function fmtClock(date: Date, timeZone?: string): string {
  return date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone });
}

// "Sat 19:00" for a time inside a week; just the clock for a time today.
export function fmtWeekdayClock(date: Date, timeZone?: string): string {
  const weekday = date.toLocaleDateString("en-GB", { weekday: "short", timeZone });
  return `${weekday} ${fmtClock(date, timeZone)}`;
}
