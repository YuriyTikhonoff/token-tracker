"""GET /api/overview -- the top of the dashboard: subscription limits, the
current session and the daily chart.

/api/data builds everything, including tables that sum the whole usage table.
The dashboard asks for this first, so the part people look at appears in about
a second, and for /api/data after that. Like /api/limits it needs no cache.
"""
import sqlite3

from fastapi import APIRouter, Depends, Request

from .. import config, queries
from ..db import DEFAULT_DB_PATH, get_db
from ..schemas import OverviewData

router = APIRouter()


@router.get("/api/overview", response_model=OverviewData)
def get_overview(
    request: Request,
    account: str | None = None,
    connection: sqlite3.Connection = Depends(get_db),
):
    # "all" (or no parameter) means every account combined, as in /api/data.
    account = None if account in (None, "", "all") else account
    timezone = config.timezone().key

    if not DEFAULT_DB_PATH.exists():
        return OverviewData(usage_snapshots=[], daily_usage=[], timezone=timezone)

    pricing = request.app.state.pricing
    return OverviewData(
        usage_snapshots=queries.get_usage_snapshots_trend(connection, account=account),
        daily_usage=queries.get_daily_usage(connection, pricing, account=account, by_account=account is None),
        accounts=queries.get_account_labels(connection),
        selected_account=account,
        timezone=timezone,
    )
