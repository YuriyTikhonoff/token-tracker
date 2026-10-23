// The backend's GET /api/limits (LimitsData in schemas.py): the small payload
// meant for clients that poll often. /api/data holds the same numbers but takes
// several seconds to build.

export interface Totals {
  total_tokens: number;
  cost: number;
}

export interface LimitSnapshot {
  scope: string;
  pct_used: number;
  resets_at: string | null;
  rate_per_hour: number;
  hours_to_limit: number | null;
}

export interface AccountSummary {
  account_uuid: string;
  label: string;
  is_default: boolean;
}

export interface UsageData {
  usage_snapshots: LimitSnapshot[];
  today: Totals;
  week: Totals;
  accounts: AccountSummary[];
  timezone: string;
}
