"""POST /api/refresh — direct port of dashboard.py's _send_refresh.

Keeps ingest and usage_snapshot independent: one failing must not block the
other from attempting, matching the original try/except-per-step structure.
"""
from fastapi import APIRouter

import codex_ingest
import ingest
import usage_snapshot
from db import DEFAULT_DB_PATH
from routes.data import invalidate_data_cache
from schemas import RefreshResult

router = APIRouter()


@router.post("/api/refresh", response_model=RefreshResult)
def post_refresh():
    errors = []
    new_prompt_count = 0
    usage_snapshot_count = None
    codex_new_usage_count = None
    try:
        ingest_result = ingest.run(ingest.DEFAULT_PROJECTS_DIR, DEFAULT_DB_PATH)
        new_prompt_count = ingest_result["new_prompt_count"]
    except Exception as error:
        errors.append(f"ingest: {error}")
    try:
        usage_snapshot_count = len(usage_snapshot.run(DEFAULT_DB_PATH))
    except Exception as error:
        errors.append(f"usage_snapshot: {error}")
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
        errors=errors,
    )
