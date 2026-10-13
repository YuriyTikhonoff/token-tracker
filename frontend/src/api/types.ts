// Mirrors backend/app/schemas.py 1:1 — same snake_case field names as the
// JSON the FastAPI backend returns.

export interface Totals {
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  cost: number;
  total_tokens: number;
}

export interface TotalsByPeriod {
  today: Totals;
  month: Totals;
  all: Totals;
}

export interface DailyUsage {
  date: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  cost: number;
}

export interface WeeklyUsage {
  week_start: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  cost: number;
}

export interface MonthlyUsage {
  month_start: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  cost: number;
}

export interface UsageSnapshotTrend {
  scope: string;
  pct_used: number;
  captured_pct_used: number;
  captured_at: string;
  resets_at: string | null;
  rate_per_hour: number;
  hours_to_limit: number | null;
}

export interface CurrentSessionStats {
  session_started_at: string;
  resets_at: string;
  pct_used: number;
  session_tokens: number;
  session_cost: number;
  tokens_per_hour: number;
  projected_exhaustion_at: string | null;
}

export interface ProjectTotal {
  project: string;
  tokens: number;
  cost: number;
}

export interface SessionTotal {
  session_id: string;
  project: string;
  first_seen: string | null;
  last_seen: string | null;
  tokens: number;
  cost: number;
}

export interface PromptTotal {
  prompt_id: string;
  preview: string | null;
  timestamp: string | null;
  tokens: number;
  cost: number;
}

export interface PromptLogEntry {
  prompt_id: string;
  session_id: string;
  preview: string | null;
  timestamp: string | null;
  tokens: number;
  cost: number;
}

export type Period = "today" | "month" | "all";

export interface CodexDailyUsage {
  date: string;
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
  reasoning_output_tokens: number;
  total_tokens: number;
}

export interface CodexRateLimitTrend {
  scope: string;
  pct_used: number;
  captured_pct_used: number;
  captured_at: string;
  resets_at: string | null;
  window_minutes: number;
  rate_per_hour: number;
  hours_to_limit: number | null;
}

export interface AccountSummary {
  account_uuid: string;
  label: string;
  email: string | null;
  is_default: boolean;
  today: Totals;
  month: Totals;
  all: Totals;
  last_active: string | null;
  session_count: number;
  cost_share: number;
}

export interface DashboardData {
  totals: Totals;
  totals_by_period: TotalsByPeriod;
  daily_usage: DailyUsage[];
  weekly_usage: WeeklyUsage[];
  monthly_usage: MonthlyUsage[];
  usage_snapshots: UsageSnapshotTrend[];
  current_session_stats: CurrentSessionStats | null;
  by_project: ProjectTotal[];
  by_session: SessionTotal[];
  by_prompt: PromptTotal[];
  prompt_log: PromptLogEntry[];
  prompt_log_total: number;
  codex_daily_usage: CodexDailyUsage[];
  codex_rate_limits: CodexRateLimitTrend[];
  accounts: AccountSummary[];
  selected_account: string | null;
  timezone: string;
}

export interface RefreshResult {
  new_prompt_count: number;
  usage_snapshot_count: number | null;
  codex_new_usage_count: number | null;
  codex_usage_check_triggered: boolean;
  errors: string[];
}
