"""PATCH /api/accounts/{account_uuid} -- rename an account or mark it as the
default one (the owner of history from before the SessionStart hook existed)."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db
from .data import invalidate_data_cache
from ..schemas import AccountUpdate

router = APIRouter()


@router.patch("/api/accounts/{account_uuid}")
def patch_account(
    account_uuid: str,
    update: AccountUpdate,
    connection: sqlite3.Connection = Depends(get_db),
):
    if not connection.execute(
        "SELECT 1 FROM accounts WHERE account_uuid = ?", (account_uuid,)
    ).fetchone():
        raise HTTPException(status_code=404, detail="Unknown account")
    if update.label is not None:
        label = update.label.strip()
        if not label:
            raise HTTPException(status_code=422, detail="Label must not be empty")
        connection.execute(
            "UPDATE accounts SET label = ? WHERE account_uuid = ?", (label, account_uuid)
        )
    if update.is_default:
        connection.execute("UPDATE accounts SET is_default = (account_uuid = ?)", (account_uuid,))
    connection.commit()
    invalidate_data_cache()
    return {"ok": True}
