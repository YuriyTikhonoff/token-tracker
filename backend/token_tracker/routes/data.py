"""GET /api/data — the totals and the weekly and monthly charts. The top of the page
is /api/overview and the collapsed sections are in routes/sections.py.

The payload is still seconds of SQLite work on a grown DB, and several clients
(web app, the dashboard's widget-preview iframe) poll it on a timer. A short
TTL cache collapses overlapping/rapid polls into one query so a single blocking
worker doesn't make the API look dead. `/api/refresh`
calls `invalidate_data_cache()` so the frontend's Refresh button still gets
fresh numbers immediately.
"""
import sqlite3
import threading
import time

from fastapi import APIRouter, Depends, Request

from .. import config, queries
from ..db import DEFAULT_DB_PATH, get_db
from ..schemas import DashboardData

router = APIRouter()

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
            weekly_usage=[],
            monthly_usage=[],
            timezone=config.timezone().key,
        )

    pricing = request.app.state.pricing
    return DashboardData(
        totals=queries.get_totals(connection, pricing, account=account),
        totals_by_period=queries.get_totals_by_period(connection, pricing, account=account),
        weekly_usage=queries.get_weekly_usage(connection, pricing, account=account, by_account=account is None),
        monthly_usage=queries.get_monthly_usage(connection, pricing, account=account, by_account=account is None),
        unknown_models=queries.get_unknown_models(connection, pricing),
        selected_account=account,
        timezone=config.timezone().key,
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
