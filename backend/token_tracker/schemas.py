"""Pydantic response models mirroring queries.py's existing dict shapes.

Pure additive typing over queries.py's return values — field names/nesting
match today's JSON exactly (snake_case, unchanged), so this is validation
and OpenAPI docs, not a rename. queries.py itself stays untyped/dict-based
so report.py (CLI) can keep calling it directly with no Pydantic involved.
"""

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


class UsagePoint(BaseModel):
    captured_at: str
    pct_used: float


class UsageSnapshotTrend(BaseModel):
    scope: str
    # The window of the last reading has closed: pct_used is that reading as it
    # was, with no projection, and a fresh snapshot is needed.
    stale: bool = False
    pct_used: float
    captured_pct_used: float
    captured_at: str
    resets_at: str | None = None
    rate_per_hour: float
    hours_to_limit: float | None = None
    # pct_used over the current window, oldest first, for the fact-vs-plan chart.
    history: list[UsagePoint] = []


class CurrentSessionStats(BaseModel):
    session_started_at: str
    resets_at: str
    pct_used: float
    session_tokens: int
    session_cost: float
    tokens_per_hour: float
    projected_exhaustion_at: str | None = None


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
    first_seen: str | None = None
    last_seen: str | None = None
    tokens: int
    cost: float


class PromptTotal(BaseModel):
    prompt_id: str
    preview: str | None = None
    timestamp: str | None = None
    tokens: int
    cost: float


class PromptLogEntry(BaseModel):
    prompt_id: str
    session_id: str
    preview: str | None = None
    timestamp: str | None = None
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
    resets_at: str | None = None
    window_minutes: int
    rate_per_hour: float
    hours_to_limit: float | None = None


class AccountSummary(BaseModel):
    account_uuid: str
    label: str
    email: str | None = None
    is_default: bool
    today: Totals
    month: Totals
    all: Totals
    last_active: str | None = None
    session_count: int
    cost_share: float


class AccountUpdate(BaseModel):
    label: str | None = None
    is_default: bool | None = None


class DashboardData(BaseModel):
    totals: Totals
    totals_by_period: TotalsByPeriod
    weekly_usage: list[WeeklyUsage]
    monthly_usage: list[MonthlyUsage]
    selected_account: str | None = None
    # IANA name of the zone the numbers are cut in and times should be shown in.
    timezone: str = "UTC"
    # Models whose cost is only a guess because pricing.json has no entry.
    unknown_models: list[str] = []


class AccountLabel(BaseModel):
    account_uuid: str
    label: str
    is_default: bool


class LimitsData(BaseModel):
    """The small payload of GET /api/limits: what a client that polls often
    needs, none of the heavy parts of DashboardData."""

    usage_snapshots: list[UsageSnapshotTrend]
    today: Totals
    week: Totals
    accounts: list[AccountLabel] = []
    selected_account: str | None = None
    timezone: str = "UTC"


class CodexSection(BaseModel):
    """GET /api/sections/codex: the Codex part of the dashboard, loaded when
    its section is opened."""

    codex_daily_usage: list[CodexDailyUsage] = []
    codex_rate_limits: list[CodexRateLimitTrend] = []


class OverviewData(BaseModel):
    """The payload of GET /api/overview: the top of the dashboard (limits and
    the daily chart), cheap enough to show before the rest of DashboardData."""

    usage_snapshots: list[UsageSnapshotTrend]
    current_session_stats: CurrentSessionStats | None = None
    daily_usage: list[DailyUsage]
    accounts: list[AccountLabel] = []
    selected_account: str | None = None
    timezone: str = "UTC"


class RefreshResult(BaseModel):
    new_prompt_count: int
    # "started": a reading of the limits was started in the background; "running": one already was;
    # "recent": the last one was a few minutes ago, so no new one was started.
    usage_snapshot: str | None = None
    codex_new_usage_count: int | None = None
    codex_usage_check_triggered: bool = False
    errors: list[str]
