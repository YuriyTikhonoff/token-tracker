import sqlite3

import pytest

from token_tracker import schema


def test_fresh_database_gets_every_table():
    connection = sqlite3.connect(":memory:")
    assert schema.migrate(connection) == schema.CURRENT_VERSION
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"usage", "prompts", "sessions", "usage_snapshots", "codex_usage", "accounts", "session_accounts"} <= tables
    assert "account_uuid" in [row[1] for row in connection.execute("PRAGMA table_info(usage)")]


def test_migrate_is_repeatable():
    connection = sqlite3.connect(":memory:")
    schema.migrate(connection)
    assert schema.migrate(connection) == schema.CURRENT_VERSION


def test_database_from_before_versioning_is_upgraded_and_keeps_its_rows():
    # Version 0 with the old tables already in place, as a pre-0.1 install has.
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE usage (assistant_uuid TEXT PRIMARY KEY, session_id TEXT NOT NULL, "
                       "prompt_id TEXT, model TEXT, input_tokens INTEGER NOT NULL DEFAULT 0, "
                       "output_tokens INTEGER NOT NULL DEFAULT 0, cache_creation_tokens INTEGER NOT NULL DEFAULT 0, "
                       "cache_read_tokens INTEGER NOT NULL DEFAULT 0, timestamp TEXT)")
    connection.execute("INSERT INTO usage (assistant_uuid, session_id, model, input_tokens) VALUES ('a','s','m',5)")
    connection.commit()
    assert schema.get_version(connection) == 0
    schema.migrate(connection)
    assert connection.execute("SELECT input_tokens, account_uuid FROM usage").fetchall() == [(5, None)]


def test_database_from_a_newer_release_is_refused():
    connection = sqlite3.connect(":memory:")
    connection.execute(f"PRAGMA user_version = {schema.CURRENT_VERSION + 1}")
    with pytest.raises(schema.SchemaTooNewError):
        schema.migrate(connection)


def test_version_3_keeps_one_row_of_each_group_of_copies():
    # A version-2 database: copies of one response are rows with equal session,
    # model and counts; rows that differ, and rows with no tokens, stay.
    connection = sqlite3.connect(":memory:")
    for number, migration in enumerate(schema.MIGRATIONS[:2], start=1):
        migration(connection)
        connection.execute(f"PRAGMA user_version = {number}")
    rows = [
        ("a1", "s", "m", 1, 2, 3, 4), ("a2", "s", "m", 1, 2, 3, 4), ("a3", "s", "m", 1, 2, 3, 4),
        ("b1", "s", "m", 1, 2, 3, 5),
        ("c1", "other", "m", 1, 2, 3, 4),
        ("z1", "s", "m", 0, 0, 0, 0), ("z2", "s", "m", 0, 0, 0, 0),
    ]
    connection.executemany(
        "INSERT INTO usage (assistant_uuid, session_id, model, input_tokens, output_tokens, "
        "cache_creation_tokens, cache_read_tokens) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    connection.commit()

    schema.migrate(connection)

    kept = [row[0] for row in connection.execute("SELECT assistant_uuid FROM usage ORDER BY assistant_uuid")]
    assert kept == ["a1", "b1", "c1", "z1", "z2"]
    assert {"cost_audits", "app_state"} <= {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
