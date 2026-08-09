"""GET /api/data — direct port of dashboard.py's _send_json."""
import sqlite3

from fastapi import APIRouter, Depends, Request

import queries
from db import DEFAULT_DB_PATH, get_db
from schemas import DashboardData

router = APIRouter()

TOP_LIMIT = 25
PROMPT_LOG_LIMIT = 200

_EMPTY_TOTALS = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_tokens": 0,
    "cache_read_tokens": 0,
    "total_tokens": 0,
    "cost": 0.0,
}


@router.get("/api/data", response_model=DashboardData)
def get_data(request: Request, connection: sqlite3.Connection = Depends(get_db)):
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
        )

    pricing = request.app.state.pricing
    full_prompt_log = queries.get_prompt_log(connection, pricing)
    return DashboardData(
        totals=queries.get_totals(connection, pricing),
        totals_by_period=queries.get_totals_by_period(connection, pricing),
        daily_usage=queries.get_daily_usage(connection, pricing),
        weekly_usage=queries.get_weekly_usage(connection, pricing),
        monthly_usage=queries.get_monthly_usage(connection, pricing),
        usage_snapshots=queries.get_usage_snapshots_trend(connection),
        current_session_stats=queries.get_current_session_stats(connection, pricing),
        by_project=queries.get_by_project(connection, pricing),
        by_session=queries.get_by_session(connection, pricing, TOP_LIMIT),
        by_prompt=queries.get_by_prompt(connection, pricing, TOP_LIMIT),
        prompt_log=full_prompt_log[:PROMPT_LOG_LIMIT],
        prompt_log_total=len(full_prompt_log),
    )
