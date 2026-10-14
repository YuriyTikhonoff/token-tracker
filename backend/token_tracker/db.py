"""SQLite connection helper for the FastAPI app — no ORM, plain sqlite3.

A fresh short-lived connection per request, matching what dashboard.py
already did in _send_json. Single-user, low-volume access (see PLAN.md) —
no pooling library needed.
"""
import sqlite3
from pathlib import Path

from . import queries

DEFAULT_DB_PATH = queries.DEFAULT_DB_PATH


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    return queries.connect(db_path, check_same_thread=False)


def get_db():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()
