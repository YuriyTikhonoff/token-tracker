"""The database schema, as numbered migrations.

The applied version is kept in SQLite's `PRAGMA user_version`. `migrate` brings
any database, new or from an older release, up to the current version, one
migration per transaction. To change the schema, append a migration; never edit
an existing one, because databases in the wild have already run it.
"""
import sqlite3


class SchemaTooNewError(Exception):
    pass


def _columns(connection, table):
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def _v1_base(connection):
    """Claude transcripts, Codex sessions and /usage snapshots. Written with
    IF NOT EXISTS because databases from before versioning already have these."""
    statements = [
        "CREATE TABLE IF NOT EXISTS file_state (path TEXT PRIMARY KEY, offset INTEGER NOT NULL)",
        """CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY, project TEXT NOT NULL, first_seen TEXT, last_seen TEXT)""",
        """CREATE TABLE IF NOT EXISTS prompts (
            prompt_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, preview TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS uuid_prompt_map (
            uuid TEXT PRIMARY KEY, prompt_id TEXT, session_id TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS usage (
            assistant_uuid TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            prompt_id TEXT,
            model TEXT,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
            cache_read_tokens INTEGER NOT NULL DEFAULT 0,
            timestamp TEXT)""",
        "CREATE INDEX IF NOT EXISTS ix_usage_prompt_id ON usage(prompt_id)",
        "CREATE INDEX IF NOT EXISTS ix_usage_session_id ON usage(session_id)",
        """CREATE TABLE IF NOT EXISTS usage_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            scope TEXT NOT NULL,
            pct_used REAL NOT NULL,
            resets_at_raw TEXT,
            resets_at TEXT)""",
        "CREATE TABLE IF NOT EXISTS codex_file_state (path TEXT PRIMARY KEY, offset INTEGER NOT NULL)",
        """CREATE TABLE IF NOT EXISTS codex_usage (
            response_id TEXT PRIMARY KEY,
            thread_id TEXT,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            cached_input_tokens INTEGER NOT NULL DEFAULT 0,
            cache_write_input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0)""",
        "CREATE INDEX IF NOT EXISTS ix_codex_usage_timestamp ON codex_usage(timestamp)",
        """CREATE TABLE IF NOT EXISTS codex_rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            primary_pct REAL,
            primary_window_minutes INTEGER,
            primary_resets_at TEXT,
            secondary_pct REAL,
            secondary_window_minutes INTEGER,
            secondary_resets_at TEXT,
            plan_type TEXT)""",
    ]
    for statement in statements:
        connection.execute(statement)


def _v2_accounts(connection):
    """Which Claude account produced which rows (see accounts.py)."""
    connection.execute(
        """CREATE TABLE IF NOT EXISTS accounts (
            account_uuid TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            email TEXT,
            display_name TEXT,
            is_default INTEGER NOT NULL DEFAULT 0)"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS session_accounts (
            session_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            account_uuid TEXT NOT NULL,
            PRIMARY KEY (session_id, ts))"""
    )
    for table in ("usage", "prompts", "usage_snapshots"):
        if "account_uuid" not in _columns(connection, table):
            connection.execute(f"ALTER TABLE {table} ADD COLUMN account_uuid TEXT")
        connection.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_account_uuid ON {table}(account_uuid)"
        )


MIGRATIONS = [_v1_base, _v2_accounts]
CURRENT_VERSION = len(MIGRATIONS)


def get_version(connection) -> int:
    return connection.execute("PRAGMA user_version").fetchone()[0]


def migrate(connection) -> int:
    """Apply every migration the database has not seen. Returns its version."""
    version = get_version(connection)
    if version > CURRENT_VERSION:
        raise SchemaTooNewError(
            f"this database is at schema version {version}, newer than this release "
            f"understands ({CURRENT_VERSION}); upgrade token-tracker"
        )
    if connection.in_transaction:
        connection.commit()
    for number, migration in enumerate(MIGRATIONS, start=1):
        if number <= version:
            continue
        connection.execute("BEGIN IMMEDIATE")
        try:
            migration(connection)
            connection.execute(f"PRAGMA user_version = {number}")
            connection.execute("COMMIT")
        except sqlite3.Error:
            connection.execute("ROLLBACK")
            raise
    return CURRENT_VERSION
