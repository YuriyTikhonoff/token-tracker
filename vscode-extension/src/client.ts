import type { UsageData } from "./api";

// /api/limits answers in well under a second; this is only the ceiling for a busy backend.
const REQUEST_TIMEOUT_MS = 10_000;

// "all" (or no account) means every account combined, as in the dashboard.
export async function fetchUsage(baseUrl: string, account: string): Promise<UsageData> {
  const url = new URL("/api/limits", baseUrl);
  if (account && account !== "all") url.searchParams.set("account", account);
  const response = await fetch(url, { signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) });
  if (response.status === 404) {
    throw new Error(`${url.pathname} not found: this Token Tracker backend is too old, update it`);
  }
  if (!response.ok) throw new Error(`GET ${url.pathname} answered ${response.status}`);
  return (await response.json()) as UsageData;
}

// The only call that does more than read. The backend's refresh also asks
// Codex for a fresh rate-limit reading, which spends a few real Codex tokens,
// so it runs only when the user asks for it, never from the polling timer.
export async function requestRefresh(baseUrl: string): Promise<void> {
  const url = new URL("/api/refresh", baseUrl);
  const response = await fetch(url, { method: "POST", signal: AbortSignal.timeout(60_000) });
  if (!response.ok) throw new Error(`POST ${url.pathname} answered ${response.status}`);
}
