"""GET /api/limits -- the subscription limits and today's and this week's totals.

A light companion to /api/data for clients that poll often (the VS Code status
bar). /api/data takes several seconds on a grown database because it sums the
whole usage table several ways; this reads only the limit snapshots and the
rows since Monday, so it needs no cache.
"""
import sqlite3

from fastapi import APIRouter, Depends, Request

from .. import config, queries
from ..db import DEFAULT_DB_PATH, get_db
from ..schemas import LimitsData

router = APIRouter()

_EMPTY_TOTALS = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_tokens": 0,
    "cache_read_tokens": 0,
    "total_tokens": 0,
    "cost": 0.0,
}


@router.get("/api/limits", response_model=LimitsData)
def get_limits(
    request: Request,
    account: str | None = None,
    connection: sqlite3.Connection = Depends(get_db),
):
    # "all" (or no parameter) means every account combined, as in /api/data.
    account = None if account in (None, "", "all") else account
    timezone = config.timezone().key

    if not DEFAULT_DB_PATH.exists():
        return LimitsData(
            usage_snapshots=[], today=_EMPTY_TOTALS, week=_EMPTY_TOTALS, timezone=timezone
        )

    totals = queries.get_today_and_week_totals(connection, request.app.state.pricing, account=account)
    return LimitsData(
        usage_snapshots=queries.get_usage_snapshots_trend(connection, account=account, with_history=False),
        today=totals["today"],
        week=totals["week"],
        accounts=queries.get_account_labels(connection),
        selected_account=account,
        timezone=timezone,
    )
