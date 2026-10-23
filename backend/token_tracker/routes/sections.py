"""The tables and Codex charts that sit in collapsed sections of the dashboard.

GET /api/data used to carry them, and most of its time went on them although
they are closed on a normal visit. The dashboard now asks for each one only
when its section is opened, so these are separate endpoints. They need no
cache: the dashboard keeps what it fetched.
"""
import sqlite3

from fastapi import APIRouter, Depends, Request

from .. import queries
from ..db import get_db
from ..schemas import AccountSummary, CodexSection, ProjectTotal, PromptLogEntry, PromptTotal, SessionTotal

router = APIRouter(prefix="/api/sections")

TOP_LIMIT = 25
PROMPT_LOG_LIMIT = 200


def _account(account: str | None) -> str | None:
    # "all" (or no parameter) means every account combined, as in /api/data.
    return None if account in (None, "", "all") else account


@router.get("/codex", response_model=CodexSection)
def get_codex(connection: sqlite3.Connection = Depends(get_db)):
    return CodexSection(
        codex_daily_usage=queries.get_codex_daily_usage(connection),
        codex_rate_limits=queries.get_codex_rate_limits_trend(connection),
    )


@router.get("/accounts", response_model=list[AccountSummary])
def get_accounts(request: Request, connection: sqlite3.Connection = Depends(get_db)):
    # Every account with its totals, whatever account the dashboard has selected.
    return queries.get_accounts_summary(connection, request.app.state.pricing)


@router.get("/prompt-log", response_model=list[PromptLogEntry])
def get_prompt_log(
    request: Request, account: str | None = None, connection: sqlite3.Connection = Depends(get_db)
):
    return queries.get_prompt_log(
        connection, request.app.state.pricing, PROMPT_LOG_LIMIT, account=_account(account)
    )


@router.get("/by-project", response_model=list[ProjectTotal])
def get_by_project(
    request: Request, account: str | None = None, connection: sqlite3.Connection = Depends(get_db)
):
    return queries.get_by_project(connection, request.app.state.pricing, account=_account(account))


@router.get("/by-session", response_model=list[SessionTotal])
def get_by_session(
    request: Request, account: str | None = None, connection: sqlite3.Connection = Depends(get_db)
):
    return queries.get_by_session(
        connection, request.app.state.pricing, TOP_LIMIT, account=_account(account)
    )


@router.get("/by-prompt", response_model=list[PromptTotal])
def get_by_prompt(
    request: Request, account: str | None = None, connection: sqlite3.Connection = Depends(get_db)
):
    return queries.get_by_prompt(
        connection, request.app.state.pricing, TOP_LIMIT, account=_account(account)
    )
