"""Shared data-access functions over token_tracker.db, used by both the CLI
report (report.py) and the local dashboard (dashboard.py).

Each function returns plain dicts/lists (JSON-serializable) rather than
printing, so both consumers can format the same underlying data.
"""
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config

DEFAULT_DB_PATH = config.db_path()
LOCAL_TZ = config.timezone()


def connect(db_path, **kwargs) -> sqlite3.Connection:
    """sqlite3.connect with WAL mode so readers (report/dashboard/FastAPI)
    don't get "database is locked" while ingest.py/usage_snapshot.py hold a
    write transaction, plus a busy_timeout for the remaining writer-vs-writer
    case."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    connection = sqlite3.connect(db_path, **kwargs)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    return connection


def _account_clause(account, column="account_uuid", joiner="AND"):
    """SQL fragment + params restricting rows to one account; empty for all."""
    if not account:
        return "", ()
    return f" {joiner} {column} = ?", (account,)


def load_pricing(pricing_path=None):
    return config.load_pricing(pricing_path)


def cost_for_row(pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens):
    rates = pricing.get(model) or pricing["_default"]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_creation_tokens * rates["cache_creation"]
        + cache_read_tokens * rates["cache_read"]
    ) / 1_000_000


def get_totals(connection, pricing, since_utc_iso=None, account=None):
    query = "SELECT model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens FROM usage"
    conditions, params = [], []
    if since_utc_iso:
        conditions.append("timestamp >= ?")
        params.append(since_utc_iso)
    if account:
        conditions.append("account_uuid = ?")
        params.append(account)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    rows = connection.execute(query, params).fetchall()

    totals = {"input_tokens": 0, "output_tokens": 0, "cache_creation_tokens": 0, "cache_read_tokens": 0, "cost": 0.0}
    for model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in rows:
        totals["input_tokens"] += input_tokens
        totals["output_tokens"] += output_tokens
        totals["cache_creation_tokens"] += cache_creation_tokens
        totals["cache_read_tokens"] += cache_read_tokens
        totals["cost"] += cost_for_row(
            pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )
    totals["total_tokens"] = (
        totals["input_tokens"] + totals["output_tokens"] + totals["cache_creation_tokens"] + totals["cache_read_tokens"]
    )
    return totals


def get_totals_by_period(connection, pricing, account=None):
    """Totals for all time, the current local month, and the current
    local day. Boundaries are computed in the configured time zone and converted to
    UTC (matching how timestamps are stored) before filtering."""
    now_local = datetime.now(LOCAL_TZ)
    start_of_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_month_local = start_of_today_local.replace(day=1)

    start_of_today_utc = start_of_today_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S")
    start_of_month_utc = start_of_month_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "today": get_totals(connection, pricing, start_of_today_utc, account),
        "month": get_totals(connection, pricing, start_of_month_utc, account),
        "all": get_totals(connection, pricing, account=account),
    }


def get_daily_usage(connection, pricing, days=10, account=None):
    """Per-day token/cost totals for the trailing `days` local days
    (oldest first, today last), zero-filled for days with no usage."""
    now_local = datetime.now(LOCAL_TZ)
    start_of_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_starts_local = [start_of_today_local - timedelta(days=offset) for offset in range(days - 1, -1, -1)]

    earliest_utc_iso = day_starts_local[0].astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S")
    account_sql, account_params = _account_clause(account)
    rows = connection.execute(
        "SELECT timestamp, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens "
        "FROM usage WHERE timestamp >= ?" + account_sql,
        (earliest_utc_iso, *account_params),
    ).fetchall()

    by_date = {
        day_start.strftime("%Y-%m-%d"): {
            "date": day_start.strftime("%Y-%m-%d"),
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
        }
        for day_start in day_starts_local
    }

    for timestamp, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in rows:
        local_date = _parse_usage_timestamp(timestamp).astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
        bucket = by_date.get(local_date)
        if bucket is None:
            continue
        bucket["input_tokens"] += input_tokens
        bucket["output_tokens"] += output_tokens
        bucket["cache_creation_tokens"] += cache_creation_tokens
        bucket["cache_read_tokens"] += cache_read_tokens
        bucket["total_tokens"] += input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        bucket["cost"] += cost_for_row(
            pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )

    return [by_date[day_start.strftime("%Y-%m-%d")] for day_start in day_starts_local]


def get_weekly_usage(connection, pricing, weeks=8, account=None):
    """Per-week token/cost totals for the trailing `weeks` local weeks
    (Monday-start, oldest first, current week last), zero-filled for weeks
    with no usage."""
    now_local = datetime.now(LOCAL_TZ)
    start_of_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_this_week_local = start_of_today_local - timedelta(days=start_of_today_local.weekday())
    week_starts_local = [start_of_this_week_local - timedelta(weeks=offset) for offset in range(weeks - 1, -1, -1)]

    earliest_utc_iso = week_starts_local[0].astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S")
    account_sql, account_params = _account_clause(account)
    rows = connection.execute(
        "SELECT timestamp, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens "
        "FROM usage WHERE timestamp >= ?" + account_sql,
        (earliest_utc_iso, *account_params),
    ).fetchall()

    by_week = {
        week_start.strftime("%Y-%m-%d"): {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
        }
        for week_start in week_starts_local
    }

    for timestamp, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in rows:
        local_dt = _parse_usage_timestamp(timestamp).astimezone(LOCAL_TZ)
        local_week_start = (local_dt - timedelta(days=local_dt.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        bucket = by_week.get(local_week_start.strftime("%Y-%m-%d"))
        if bucket is None:
            continue
        bucket["input_tokens"] += input_tokens
        bucket["output_tokens"] += output_tokens
        bucket["cache_creation_tokens"] += cache_creation_tokens
        bucket["cache_read_tokens"] += cache_read_tokens
        bucket["total_tokens"] += input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        bucket["cost"] += cost_for_row(
            pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )

    return [by_week[week_start.strftime("%Y-%m-%d")] for week_start in week_starts_local]


def _months_before(month_start_local, count):
    """month_start_local shifted back by `count` calendar months (day fixed at 1)."""
    zero_based_month = month_start_local.month - 1 - count
    year = month_start_local.year + zero_based_month // 12
    month = zero_based_month % 12 + 1
    return month_start_local.replace(year=year, month=month)


def get_monthly_usage(connection, pricing, months=8, account=None):
    """Per-month token/cost totals for the trailing `months` local
    calendar months (oldest first, current month last), zero-filled for
    months with no usage."""
    now_local = datetime.now(LOCAL_TZ)
    start_of_this_month_local = now_local.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    month_starts_local = [
        _months_before(start_of_this_month_local, offset) for offset in range(months - 1, -1, -1)
    ]

    earliest_utc_iso = month_starts_local[0].astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S")
    account_sql, account_params = _account_clause(account)
    rows = connection.execute(
        "SELECT timestamp, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens "
        "FROM usage WHERE timestamp >= ?" + account_sql,
        (earliest_utc_iso, *account_params),
    ).fetchall()

    by_month = {
        month_start.strftime("%Y-%m-%d"): {
            "month_start": month_start.strftime("%Y-%m-%d"),
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
        }
        for month_start in month_starts_local
    }

    for timestamp, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in rows:
        local_dt = _parse_usage_timestamp(timestamp).astimezone(LOCAL_TZ)
        local_month_start = local_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        bucket = by_month.get(local_month_start.strftime("%Y-%m-%d"))
        if bucket is None:
            continue
        bucket["input_tokens"] += input_tokens
        bucket["output_tokens"] += output_tokens
        bucket["cache_creation_tokens"] += cache_creation_tokens
        bucket["cache_read_tokens"] += cache_read_tokens
        bucket["total_tokens"] += input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        bucket["cost"] += cost_for_row(
            pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )

    return [by_month[month_start.strftime("%Y-%m-%d")] for month_start in month_starts_local]


def _parse_utc_iso(iso_timestamp):
    return datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))


def _parse_usage_timestamp(iso_timestamp):
    """usage.timestamp includes milliseconds (e.g. "...12:54:52.866Z"), unlike
    the whole-second timestamps _parse_utc_iso handles, so it needs its own
    parser."""
    return datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))


def _hours_between(earlier_iso, later_iso):
    return (_parse_utc_iso(later_iso) - _parse_utc_iso(earlier_iso)).total_seconds() / 3600


RESET_DROP_TOLERANCE_PCT = 5.0


def _trim_to_current_cycle(same_period_snapshots, drop_tolerance_pct=RESET_DROP_TOLERANCE_PCT):
    """resets_at can lag behind a real reset -- it's stayed put across an
    actual pct_used reset in practice (e.g. the weekly quota dropping from
    45% back to 0% with resets_at unchanged), so same_period_snapshots can
    still span a boundary resets_at didn't reveal. Walk backward from the
    latest sample and cut the window as soon as an older sample's pct_used
    is higher than everything seen so far by more than noise -- that jump
    means the samples before it belong to the previous cycle."""
    if not same_period_snapshots:
        return same_period_snapshots
    running_min = same_period_snapshots[-1]["pct_used"]
    start_index = len(same_period_snapshots) - 1
    for index in range(len(same_period_snapshots) - 2, -1, -1):
        pct_used = same_period_snapshots[index]["pct_used"]
        if pct_used > running_min + drop_tolerance_pct:
            break
        running_min = min(running_min, pct_used)
        start_index = index
    return same_period_snapshots[start_index:]


def _extrapolate_pct_used(snapshots, window_hours=6, now_iso=None, widen=False):
    """Given a scope's snapshots (ascending by captured_at), project pct_used
    forward to `now_iso` at the rate observed over the trailing
    `window_hours`. Snapshots only land when usage_snapshot.py runs (gated on
    new meaningful prompts, see watch.sh), so the raw latest row goes stale
    between captures; this keeps the value advancing on every backend poll
    instead of only jumping when a fresh CLI snapshot arrives.

    Scopes with a slow burn rate (e.g. the weekly limit) can sit flat for
    many hours at a time, so a fixed trailing window often contains no
    measurable movement even though the scope has been climbing steadily
    over a longer horizon. Passing `widen=True` progressively widens the
    window -- doubling each step, up to the full same-period history --
    until real movement is found. Callers for scopes that reset frequently
    (e.g. the 5h session) should leave this off: their windows are already
    short enough to reflect current pace, and a stall is meaningful signal
    rather than something to search past."""
    if now_iso is None:
        now_iso = datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    latest = snapshots[-1]
    # pct_used resets to ~0 at the start of each new session/week window, so a
    # trailing window that spans a reset boundary (different resets_at) would
    # mix a near-100% sample with a near-0% one and produce a nonsense (often
    # negative) rate. Restrict to samples from the same period as latest.
    # resets_at itself jitters by a minute or two between captures (the CLI's
    # text rounds to the minute and ticks over, e.g. "3:59pm" -> "4pm" for the
    # same underlying reset instant), so compare with a tolerance rather than
    # exact equality -- otherwise nearly every prior sample looks like a
    # "different period" and the window collapses to a single point.
    RESET_JITTER_TOLERANCE_HOURS = 1.0
    same_period_as_latest = (
        lambda snapshot: latest["resets_at"] is None
        or snapshot["resets_at"] is None
        or abs(_hours_between(snapshot["resets_at"], latest["resets_at"])) <= RESET_JITTER_TOLERANCE_HOURS
    )
    same_period_snapshots = [snapshot for snapshot in snapshots if same_period_as_latest(snapshot)]
    same_period_snapshots = _trim_to_current_cycle(same_period_snapshots)

    # Without a resets_at on the latest sample there's no way to tell a
    # period boundary apart from a normal sample, so widening could silently
    # mix snapshots from different cycles into one rate. Only widen when we
    # can actually bound the period.
    can_widen = widen and latest["resets_at"] is not None

    rate_per_hour = 0.0
    candidate_hours = window_hours
    while True:
        window = [
            snapshot for snapshot in same_period_snapshots
            if _hours_between(snapshot["captured_at"], latest["captured_at"]) <= candidate_hours
        ]
        if len(window) >= 2:
            elapsed_hours = _hours_between(window[0]["captured_at"], latest["captured_at"])
            if elapsed_hours > 0:
                rate_per_hour = (latest["pct_used"] - window[0]["pct_used"]) / elapsed_hours
                if rate_per_hour != 0:
                    break
        if not can_widen or len(window) >= len(same_period_snapshots):
            break
        candidate_hours = candidate_hours * 2 if candidate_hours > 0 else 1

    hours_since_latest = _hours_between(latest["captured_at"], now_iso)
    pct_used_now = latest["pct_used"] + rate_per_hour * hours_since_latest
    pct_used_now = max(0.0, min(100.0, pct_used_now))

    return latest, rate_per_hour, pct_used_now


WEEK_SCOPE_WINDOW_HOURS = 24


def _is_weekly_scope(scope):
    """Scope names come verbatim from `claude -p "/usage"` output (see
    usage_snapshot.py), not a stable identifier, so this is a best-effort
    match. If Anthropic changes that wording, weekly scopes will silently
    fall back to the short window/no-widening behavior below -- if the
    weekly projection ever stops widening past a flat window again, check
    here first."""
    return "week" in scope.lower()


def get_usage_snapshots_trend(connection, window_hours=6, account=None):
    """Latest subscription-usage snapshot per scope (session, weekly, ...),
    plus a projected hours-to-100% based on the pct_used rate of change over
    the trailing window. Requires usage_snapshot.py to have run at least
    once; returns [] if the table doesn't exist yet or is empty.

    Weekly scopes use a wider `WEEK_SCOPE_WINDOW_HOURS` base window and allow
    widening past it (see `_extrapolate_pct_used`'s `widen` param): usage has
    a daily on/off cycle (e.g. no usage overnight), so a short trailing
    window can land entirely in a quiet stretch and understate the real burn
    rate. Frequently-resetting scopes (e.g. the 5h session) keep the plain
    `window_hours` window with no widening -- a stall there is real signal,
    not a quiet stretch to search past.

    Returns both `pct_used` (the live projection at `now_iso`, which keeps
    climbing on every call even between real `/usage` snapshots) and
    `captured_pct_used` (the actual last-reported value, frozen at
    `captured_at`) -- see get_codex_rate_limits_trend for the Codex twin of
    this function, which needed the same split since it lacks an
    independent periodic poller and so drifts more visibly."""
    account_sql, account_params = _account_clause(account, joiner="WHERE")
    try:
        rows = connection.execute(
            "SELECT captured_at, scope, pct_used, resets_at FROM usage_snapshots"
            + account_sql + " ORDER BY captured_at ASC",
            account_params,
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    by_scope = {}
    for captured_at, scope, pct_used, resets_at in rows:
        by_scope.setdefault(scope, []).append(
            {"captured_at": captured_at, "pct_used": pct_used, "resets_at": resets_at}
        )

    now_iso = datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    results = []
    for scope, snapshots in by_scope.items():
        is_weekly = _is_weekly_scope(scope)
        scope_window_hours = WEEK_SCOPE_WINDOW_HOURS if is_weekly else window_hours
        latest, rate_per_hour, pct_used_now = _extrapolate_pct_used(
            snapshots, scope_window_hours, now_iso, widen=is_weekly
        )
        hours_to_limit = (100 - pct_used_now) / rate_per_hour if rate_per_hour > 0 else None
        # The CLI omits resets_at once a window has closed and no new usage has
        # landed to start the next one, so the latest snapshot can have no
        # resets_at even though a real (past) one is known. Fall back to the
        # most recent non-null resets_at from this scope's history so the
        # widget still has a timestamp to show, rather than nothing.
        resets_at = latest["resets_at"]
        if resets_at is None:
            resets_at = next(
                (snapshot["resets_at"] for snapshot in reversed(snapshots) if snapshot["resets_at"] is not None),
                None,
            )
        results.append({
            "scope": scope,
            "pct_used": pct_used_now,
            "captured_pct_used": latest["pct_used"],
            "captured_at": latest["captured_at"],
            "resets_at": resets_at,
            "rate_per_hour": rate_per_hour,
            "hours_to_limit": hours_to_limit,
        })

    return sorted(results, key=lambda entry: entry["scope"])


def get_current_session_stats(connection, pricing, scope="Current session", session_hours=5,
                                window_hours=6, account=None):
    """Derives the current 5h session window's start from the latest snapshot's
    resets_at, sums actual token usage logged within that window, and
    extrapolates: at the current token burn rate, when would the session's
    estimated token capacity (inferred from tokens-used / pct-used) be
    exhausted. Returns None if no snapshot with a resets_at exists yet."""
    account_sql, account_params = _account_clause(account)
    try:
        rows = connection.execute(
            "SELECT captured_at, pct_used, resets_at FROM usage_snapshots "
            "WHERE scope = ? AND resets_at IS NOT NULL" + account_sql + " ORDER BY captured_at ASC",
            (scope, *account_params),
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    if not rows:
        return None

    snapshots = [
        {"captured_at": captured_at, "pct_used": pct_used, "resets_at": resets_at}
        for captured_at, pct_used, resets_at in rows
    ]
    now = datetime.now(ZoneInfo("UTC"))
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    latest, _rate_per_hour, pct_used = _extrapolate_pct_used(snapshots, window_hours, now_iso)
    captured_at, resets_at = latest["captured_at"], latest["resets_at"]
    resets_dt = _parse_utc_iso(resets_at)
    session_started_dt = resets_dt - timedelta(hours=session_hours)
    session_started_at = session_started_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    usage_rows = connection.execute(
        "SELECT model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens "
        "FROM usage WHERE timestamp >= ?" + account_sql,
        (session_started_at, *account_params),
    ).fetchall()

    session_tokens = 0
    session_cost = 0.0
    for model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in usage_rows:
        session_tokens += input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        session_cost += cost_for_row(
            pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )

    elapsed_hours = max((now - session_started_dt).total_seconds() / 3600, 0)
    tokens_per_hour = session_tokens / elapsed_hours if elapsed_hours > 0 else 0.0

    projected_exhaustion_at = None
    if pct_used > 0 and tokens_per_hour > 0:
        estimated_capacity_tokens = session_tokens / pct_used * 100
        remaining_tokens = max(estimated_capacity_tokens - session_tokens, 0)
        hours_remaining = remaining_tokens / tokens_per_hour
        exhaustion_dt = now + timedelta(hours=hours_remaining)
        projected_exhaustion_at = exhaustion_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "session_started_at": session_started_at,
        "resets_at": resets_at,
        "pct_used": pct_used,
        "session_tokens": session_tokens,
        "session_cost": session_cost,
        "tokens_per_hour": tokens_per_hour,
        "projected_exhaustion_at": projected_exhaustion_at,
    }


def get_codex_daily_usage(connection, days=10):
    """Per-day Codex token totals for the trailing `days` local days
    (oldest first, today last), zero-filled for days with no usage. Same
    shape/window as get_daily_usage but over Codex's own token categories
    (see codex_ingest.py) rather than Claude's -- no cost, since Codex model
    names in the logs are internal codenames with no published $/MTok rates
    to attach."""
    now_local = datetime.now(LOCAL_TZ)
    start_of_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_starts_local = [start_of_today_local - timedelta(days=offset) for offset in range(days - 1, -1, -1)]

    earliest_utc_iso = day_starts_local[0].astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        rows = connection.execute(
            "SELECT timestamp, input_tokens, cached_input_tokens, output_tokens, "
            "reasoning_output_tokens, total_tokens FROM codex_usage WHERE timestamp >= ?",
            (earliest_utc_iso,),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    by_date = {
        day_start.strftime("%Y-%m-%d"): {
            "date": day_start.strftime("%Y-%m-%d"),
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_output_tokens": 0,
            "total_tokens": 0,
        }
        for day_start in day_starts_local
    }

    for timestamp, input_tokens, cached_input_tokens, output_tokens, reasoning_output_tokens, total_tokens in rows:
        local_date = _parse_usage_timestamp(timestamp).astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
        bucket = by_date.get(local_date)
        if bucket is None:
            continue
        bucket["input_tokens"] += input_tokens
        bucket["cached_input_tokens"] += cached_input_tokens
        bucket["output_tokens"] += output_tokens
        bucket["reasoning_output_tokens"] += reasoning_output_tokens
        bucket["total_tokens"] += total_tokens

    return [by_date[day_start.strftime("%Y-%m-%d")] for day_start in day_starts_local]


def get_codex_rate_limits_trend(connection, window_hours=6):
    """Latest Codex rate-limit snapshot for the 5h and weekly windows, plus a
    projected hours-to-100% -- reuses the same _extrapolate_pct_used/
    _trim_to_current_cycle machinery as get_usage_snapshots_trend, since
    Codex's rate_limits payload (captured passively on every turn -- see
    codex_ingest.py) has the same shape: a used_percent plus a resets_at that
    jumps forward at each window boundary. Unlike Claude's usage_snapshots
    (regex-parsed from `claude -p "/usage"` text), Codex gives window_minutes
    and resets_at directly and precisely, so no reset-boundary text parsing
    is needed here.

    Returns both `pct_used` (the live projection at `now_iso`, which keeps
    climbing on every call between real captures) and `captured_pct_used`
    (the actual last-reported value, frozen at `captured_at`) so callers can
    show the confirmed figure alongside the estimate rather than only the
    projection."""
    try:
        rows = connection.execute(
            "SELECT captured_at, primary_pct, primary_window_minutes, primary_resets_at, "
            "secondary_pct, secondary_window_minutes, secondary_resets_at "
            "FROM codex_rate_limits ORDER BY captured_at ASC"
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    if not rows:
        return []

    now_iso = datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = []
    for label, pct_idx, window_idx, resets_idx, is_weekly, default_window_minutes in (
        ("Codex 5h limit", 1, 2, 3, False, 300),
        ("Codex weekly limit", 4, 5, 6, True, 10080),
    ):
        snapshots = [
            {
                "captured_at": row[0],
                "pct_used": row[pct_idx],
                "resets_at": row[resets_idx],
                "window_minutes": row[window_idx],
            }
            for row in rows
            if row[pct_idx] is not None
        ]
        if not snapshots:
            continue

        scope_window_hours = WEEK_SCOPE_WINDOW_HOURS if is_weekly else window_hours
        latest, rate_per_hour, pct_used_now = _extrapolate_pct_used(
            snapshots, scope_window_hours, now_iso, widen=is_weekly
        )
        hours_to_limit = (100 - pct_used_now) / rate_per_hour if rate_per_hour > 0 else None
        resets_at = latest["resets_at"]
        if resets_at is None:
            resets_at = next(
                (snapshot["resets_at"] for snapshot in reversed(snapshots) if snapshot["resets_at"] is not None),
                None,
            )
        results.append({
            "scope": label,
            "pct_used": pct_used_now,
            "captured_pct_used": latest["pct_used"],
            "captured_at": latest["captured_at"],
            "resets_at": resets_at,
            "window_minutes": latest.get("window_minutes") or default_window_minutes,
            "rate_per_hour": rate_per_hour,
            "hours_to_limit": hours_to_limit,
        })

    return results


def get_by_project(connection, pricing, account=None):
    account_sql, account_params = _account_clause(account, "u.account_uuid", "WHERE")
    rows = connection.execute(
        "SELECT s.project, u.model, u.input_tokens, u.output_tokens, "
        "u.cache_creation_tokens, u.cache_read_tokens "
        "FROM usage u JOIN sessions s ON s.session_id = u.session_id" + account_sql,
        account_params,
    ).fetchall()

    by_project = {}
    for project, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in rows:
        cost = cost_for_row(
            pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )
        entry = by_project.setdefault(project, {"project": project, "tokens": 0, "cost": 0.0})
        entry["tokens"] += input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        entry["cost"] += cost

    return sorted(by_project.values(), key=lambda entry: -entry["cost"])


def get_by_session(connection, pricing, limit=None, account=None):
    account_sql, account_params = _account_clause(account, "u.account_uuid", "WHERE")
    rows = connection.execute(
        "SELECT s.session_id, s.project, s.first_seen, s.last_seen, "
        "u.model, u.input_tokens, u.output_tokens, u.cache_creation_tokens, u.cache_read_tokens "
        "FROM usage u JOIN sessions s ON s.session_id = u.session_id" + account_sql,
        account_params,
    ).fetchall()

    by_session = {}
    for session_id, project, first_seen, last_seen, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in rows:
        cost = cost_for_row(
            pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )
        entry = by_session.setdefault(
            session_id,
            {
                "session_id": session_id,
                "project": project,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "tokens": 0,
                "cost": 0.0,
            },
        )
        entry["tokens"] += input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        entry["cost"] += cost
        if last_seen and (not entry["last_seen"] or last_seen > entry["last_seen"]):
            entry["last_seen"] = last_seen

    ranked = sorted(by_session.values(), key=lambda entry: -entry["cost"])
    return ranked[:limit] if limit else ranked


def get_by_prompt(connection, pricing, limit=None, account=None):
    account_sql, account_params = _account_clause(account, "u.account_uuid", "WHERE")
    rows = connection.execute(
        "SELECT p.prompt_id, p.session_id, p.preview, p.timestamp, "
        "u.model, u.input_tokens, u.output_tokens, u.cache_creation_tokens, u.cache_read_tokens "
        "FROM usage u LEFT JOIN prompts p ON p.prompt_id = u.prompt_id" + account_sql,
        account_params,
    ).fetchall()

    by_prompt = {}
    for prompt_id, session_id, preview, timestamp, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in rows:
        key = prompt_id or f"(no-prompt-id in session {session_id})"
        cost = cost_for_row(
            pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )
        entry = by_prompt.setdefault(
            key, {"prompt_id": key, "preview": preview, "timestamp": timestamp, "tokens": 0, "cost": 0.0}
        )
        entry["tokens"] += input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        entry["cost"] += cost
        if preview and not entry["preview"]:
            entry["preview"] = preview

    ranked = sorted(by_prompt.values(), key=lambda entry: -entry["cost"])
    return ranked[:limit] if limit else ranked


def get_prompt_log(connection, pricing, limit=None, account=None):
    """All prompts in chronological order (most recent first), with token/cost
    totals attached. Starts from `prompts` rather than `usage` so a prompt with
    no attributable usage rows (e.g. interrupted before a response) still
    appears, with zero tokens/cost."""
    account_sql, account_params = _account_clause(account, "p.account_uuid", "WHERE")
    rows = connection.execute(
        "SELECT p.prompt_id, p.session_id, p.preview, p.timestamp, "
        "u.model, u.input_tokens, u.output_tokens, u.cache_creation_tokens, u.cache_read_tokens "
        "FROM prompts p LEFT JOIN usage u ON u.prompt_id = p.prompt_id" + account_sql,
        account_params,
    ).fetchall()

    by_prompt = {}
    for prompt_id, session_id, preview, timestamp, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens in rows:
        entry = by_prompt.setdefault(
            prompt_id,
            {"prompt_id": prompt_id, "session_id": session_id, "preview": preview, "timestamp": timestamp, "tokens": 0, "cost": 0.0},
        )
        if model is not None:
            entry["tokens"] += input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
            entry["cost"] += cost_for_row(
                pricing, model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
            )

    ranked = sorted(by_prompt.values(), key=lambda entry: entry["timestamp"] or "", reverse=True)
    return ranked[:limit] if limit else ranked


def get_unknown_models(connection, pricing):
    """Models that appear in the usage data but have no entry in the pricing
    table: their cost is counted at `_default`, so it is only a rough guess."""
    try:
        models = [row[0] for row in connection.execute("SELECT DISTINCT model FROM usage")]
    except sqlite3.OperationalError:
        return []
    return sorted(model for model in models if model and model not in pricing)


def get_accounts_summary(connection, pricing):
    """Every known account with its today/month/all totals and last activity,
    plus its share of the combined cost -- the "common stats" view. Independent
    of the account filter on the rest of the payload."""
    try:
        account_rows = connection.execute(
            "SELECT account_uuid, label, email, is_default FROM accounts ORDER BY is_default DESC, label"
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    now_local = datetime.now(LOCAL_TZ)
    start_of_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_today_utc = start_of_today_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S")
    start_of_month_utc = start_of_today_local.replace(day=1).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S")

    summaries = []
    for account_uuid, label, email, is_default in account_rows:
        last_active, session_count = connection.execute(
            "SELECT MAX(timestamp), COUNT(DISTINCT session_id) FROM usage WHERE account_uuid = ?",
            (account_uuid,),
        ).fetchone()
        summaries.append({
            "account_uuid": account_uuid,
            "label": label,
            "email": email,
            "is_default": bool(is_default),
            "today": get_totals(connection, pricing, start_of_today_utc, account_uuid),
            "month": get_totals(connection, pricing, start_of_month_utc, account_uuid),
            "all": get_totals(connection, pricing, account=account_uuid),
            "last_active": last_active,
            "session_count": session_count,
        })

    total_cost = sum(summary["all"]["cost"] for summary in summaries)
    for summary in summaries:
        summary["cost_share"] = summary["all"]["cost"] / total_cost if total_cost > 0 else 0.0
    return summaries
