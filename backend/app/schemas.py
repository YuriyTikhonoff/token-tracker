"""Pydantic response models mirroring queries.py's existing dict shapes.

Pure additive typing over queries.py's return values — field names/nesting
match today's JSON exactly (snake_case, unchanged), so this is validation
and OpenAPI docs, not a rename. queries.py itself stays untyped/dict-based
so report.py (CLI) can keep calling it directly with no Pydantic involved.
"""
from typing import Optional

from pydantic import BaseModel


class Totals(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    cost: float
    total_tokens: int


class TotalsByPeriod(BaseModel):
    today: Totals
    month: Totals
    all: Totals


class UsageSnapshotTrend(BaseModel):
    scope: str
    pct_used: float
    captured_pct_used: float
    captured_at: str
    resets_at: Optional[str] = None
    rate_per_hour: float
    hours_to_limit: Optional[float] = None


class CurrentSessionStats(BaseModel):
    session_started_at: str
    resets_at: str
    pct_used: float
    session_tokens: int
    session_cost: float
    tokens_per_hour: float
    projected_exhaustion_at: Optional[str] = None


class DailyUsage(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    cost: float


class WeeklyUsage(BaseModel):
    week_start: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    cost: float


class MonthlyUsage(BaseModel):
    month_start: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    cost: float


class ProjectTotal(BaseModel):
    project: str
    tokens: int
    cost: float


class SessionTotal(BaseModel):
    session_id: str
    project: str
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    tokens: int
    cost: float


class PromptTotal(BaseModel):
    prompt_id: str
    preview: Optional[str] = None
    timestamp: Optional[str] = None
    tokens: int
    cost: float


class PromptLogEntry(BaseModel):
    prompt_id: str
    session_id: str
    preview: Optional[str] = None
    timestamp: Optional[str] = None
    tokens: int
    cost: float


class CodexDailyUsage(BaseModel):
    date: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int
    total_tokens: int


class CodexRateLimitTrend(BaseModel):
    scope: str
    pct_used: float
    captured_pct_used: float
    captured_at: str
    resets_at: Optional[str] = None
    window_minutes: int
    rate_per_hour: float
    hours_to_limit: Optional[float] = None


class AccountSummary(BaseModel):
    account_uuid: str
    label: str
    email: Optional[str] = None
    is_default: bool
    today: Totals
    month: Totals
    all: Totals
    last_active: Optional[str] = None
    session_count: int
    cost_share: float


class AccountUpdate(BaseModel):
    label: Optional[str] = None
    is_default: Optional[bool] = None


class DashboardData(BaseModel):
    totals: Totals
    totals_by_period: TotalsByPeriod
    daily_usage: list[DailyUsage]
    weekly_usage: list[WeeklyUsage]
    monthly_usage: list[MonthlyUsage]
    usage_snapshots: list[UsageSnapshotTrend]
    current_session_stats: Optional[CurrentSessionStats] = None
    by_project: list[ProjectTotal]
    by_session: list[SessionTotal]
    by_prompt: list[PromptTotal]
    prompt_log: list[PromptLogEntry]
    prompt_log_total: int
    codex_daily_usage: list[CodexDailyUsage] = []
    codex_rate_limits: list[CodexRateLimitTrend] = []
    accounts: list[AccountSummary] = []
    selected_account: Optional[str] = None
    # IANA name of the zone the numbers are cut in and times should be shown in.
    timezone: str = "UTC"


class RefreshResult(BaseModel):
    new_prompt_count: int
    usage_snapshot_count: Optional[int] = None
    codex_new_usage_count: Optional[int] = None
    codex_usage_check_triggered: bool = False
    errors: list[str]
