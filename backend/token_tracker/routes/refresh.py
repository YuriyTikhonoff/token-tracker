"""POST /api/refresh — direct port of dashboard.py's _send_refresh.

Keeps ingest and usage_snapshot independent: one failing must not block the
other from attempting, matching the original try/except-per-step structure.
"""
from fastapi import APIRouter

from .. import codex_ingest, codex_usage_check, ingest, usage_snapshot
from ..db import DEFAULT_DB_PATH
from ..schemas import RefreshResult
from .data import invalidate_data_cache

router = APIRouter()


@router.post("/api/refresh", response_model=RefreshResult)
def post_refresh(trigger_codex_usage_check: bool = False):
    errors = []
    new_prompt_count = 0
    usage_snapshot_count = None
    codex_new_usage_count = None
    codex_usage_check_triggered = False
    try:
        ingest_result = ingest.run(ingest.DEFAULT_PROJECTS_DIR, DEFAULT_DB_PATH)
        new_prompt_count = ingest_result["new_prompt_count"]
    except Exception as error:
        errors.append(f"ingest: {error}")
    try:
        usage_snapshot_count = len(usage_snapshot.run(DEFAULT_DB_PATH))
    except Exception as error:
        errors.append(f"usage_snapshot: {error}")
    # codex_usage_check burns real tokens (a live `codex exec` turn) to force
    # a fresh rate-limit reading, so it only runs when the caller explicitly
    # opts in (the manual Refresh button click) -- never on the passive
    # window-focus refresh, and never from watch.sh's timer loop.
    if trigger_codex_usage_check:
        try:
            codex_result = codex_usage_check.run(
                codex_ingest.DEFAULT_SESSIONS_DIR, DEFAULT_DB_PATH
            )
            codex_new_usage_count = codex_result["new_usage_count"]
            codex_usage_check_triggered = True
        except Exception as error:
            errors.append(f"codex_usage_check: {error}")
    else:
        try:
            codex_result = codex_ingest.run(codex_ingest.DEFAULT_SESSIONS_DIR, DEFAULT_DB_PATH)
            codex_new_usage_count = codex_result["new_usage_count"]
        except Exception as error:
            errors.append(f"codex_ingest: {error}")
    # New rows landed — force the next /api/data to recompute rather than serve
    # the pre-refresh cache.
    invalidate_data_cache()
    return RefreshResult(
        new_prompt_count=new_prompt_count,
        usage_snapshot_count=usage_snapshot_count,
        codex_new_usage_count=codex_new_usage_count,
        codex_usage_check_triggered=codex_usage_check_triggered,
        errors=errors,
    )
