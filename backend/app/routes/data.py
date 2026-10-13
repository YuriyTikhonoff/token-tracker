"""GET /api/data — direct port of dashboard.py's _send_json.

The full payload is ~2–6 s of SQLite work on a grown DB, and several clients
(web app, the Hammerspoon overlay, the dashboard's widget-preview iframe) poll
it on a timer. A short TTL cache collapses overlapping/rapid polls into one
query so a single blocking worker doesn't make the API look dead. `/api/refresh`
calls `invalidate_data_cache()` so the frontend's Refresh button still gets
fresh numbers immediately.
"""
import sqlite3
import threading
import time

from fastapi import APIRouter, Depends, Request

import queries
from db import DEFAULT_DB_PATH, get_db
from schemas import DashboardData

router = APIRouter()

TOP_LIMIT = 25
PROMPT_LOG_LIMIT = 200
CACHE_TTL_SECONDS = 15

_EMPTY_TOTALS = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_tokens": 0,
    "cache_read_tokens": 0,
    "total_tokens": 0,
    "cost": 0.0,
}

_cache_lock = threading.Lock()
# Keyed by the selected account (None = everyone) so switching the dashboard's
# account filter never serves another account's numbers.
_cached_payloads: dict[str | None, tuple[float, DashboardData]] = {}


def invalidate_data_cache() -> None:
    """Drop the cached payload so the next /api/data call recomputes."""
    with _cache_lock:
        _cached_payloads.clear()


def _build_payload(
    request: Request, connection: sqlite3.Connection, account: str | None
) -> DashboardData:
    if not DEFAULT_DB_PATH.exists():
        return DashboardData(
            totals=_EMPTY_TOTALS,
            totals_by_period={"today": _EMPTY_TOTALS, "month": _EMPTY_TOTALS, "all": _EMPTY_TOTALS},
            daily_usage=[],
            weekly_usage=[],
            monthly_usage=[],
            usage_snapshots=[],
            current_session_stats=None,
            by_project=[],
            by_session=[],
            by_prompt=[],
            prompt_log=[],
            prompt_log_total=0,
            codex_daily_usage=[],
            codex_rate_limits=[],
        )

    pricing = request.app.state.pricing
    full_prompt_log = queries.get_prompt_log(connection, pricing, account=account)
    return DashboardData(
        totals=queries.get_totals(connection, pricing, account=account),
        totals_by_period=queries.get_totals_by_period(connection, pricing, account=account),
        daily_usage=queries.get_daily_usage(connection, pricing, account=account),
        weekly_usage=queries.get_weekly_usage(connection, pricing, account=account),
        monthly_usage=queries.get_monthly_usage(connection, pricing, account=account),
        usage_snapshots=queries.get_usage_snapshots_trend(connection, account=account),
        current_session_stats=queries.get_current_session_stats(connection, pricing, account=account),
        by_project=queries.get_by_project(connection, pricing, account=account),
        by_session=queries.get_by_session(connection, pricing, TOP_LIMIT, account=account),
        by_prompt=queries.get_by_prompt(connection, pricing, TOP_LIMIT, account=account),
        prompt_log=full_prompt_log[:PROMPT_LOG_LIMIT],
        prompt_log_total=len(full_prompt_log),
        codex_daily_usage=queries.get_codex_daily_usage(connection),
        codex_rate_limits=queries.get_codex_rate_limits_trend(connection),
        accounts=queries.get_accounts_summary(connection, pricing),
        selected_account=account,
    )


@router.get("/api/data", response_model=DashboardData)
def get_data(
    request: Request,
    account: str | None = None,
    connection: sqlite3.Connection = Depends(get_db),
):
    # "all" (or no parameter) means every account combined.
    account = None if account in (None, "", "all") else account

    # Serialize recompute: concurrent pollers that arrive during a rebuild wait
    # on the lock and then read the just-filled cache instead of each running
    # their own multi-second query.
    with _cache_lock:
        cached = _cached_payloads.get(account)
        if cached is not None and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]
        payload = _build_payload(request, connection, account)
        _cached_payloads[account] = (time.monotonic(), payload)
        return payload
