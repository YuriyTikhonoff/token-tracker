// The slice of the backend's GET /api/data this extension reads. Field names
// are the backend's (schemas.py); the rest of the payload is ignored.

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
  totals_by_period: { today: Totals };
  weekly_usage: Totals[];
  accounts: AccountSummary[];
  timezone: string;
}
