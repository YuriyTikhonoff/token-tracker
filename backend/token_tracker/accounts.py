"""Which Claude account produced which usage.

Claude Code transcripts carry no account identity, so a SessionStart hook
(hooks/record_account.py) appends `{ts, session_id, account_uuid, ...}` to an
events file every time a session starts or resumes, reading the account that is
logged in at that moment from ~/.claude.json. `sync_events` loads those events
into SQLite and `AccountResolver` attributes each usage row to the account that
was active in its session at the row's timestamp.

Anything with no event (history from before the hook was installed) belongs to
the default account -- the one that was logged in when this first ran.
"""
import json
from bisect import bisect_right

from . import config, schema

EVENTS_PATH = config.account_events_path()
CLAUDE_JSON_PATH = config.claude_json_path()
EVENTS_STATE_KEY = "account-events"


def read_current_account(claude_json_path=CLAUDE_JSON_PATH):
    """The account Claude Code is logged into right now, or None."""
    try:
        with open(claude_json_path, encoding="utf-8") as file_handle:
            oauth = json.load(file_handle).get("oauthAccount") or {}
    except (OSError, json.JSONDecodeError):
        return None
    if not oauth.get("accountUuid"):
        return None
    return {
        "account_uuid": oauth["accountUuid"],
        "email": oauth.get("emailAddress"),
        "display_name": oauth.get("displayName"),
    }


def _default_label(email, display_name, account_uuid):
    if display_name:
        return display_name
    if email:
        return email.split("@")[0]
    return account_uuid[:8]


def register_account(connection, account):
    """Insert the account if new, refresh its email/name if known. The first
    account ever registered becomes the default. A label the user edited is
    never overwritten."""
    if connection.execute(
        "SELECT 1 FROM accounts WHERE account_uuid = ?", (account["account_uuid"],)
    ).fetchone():
        connection.execute(
            "UPDATE accounts SET email = COALESCE(?, email), display_name = COALESCE(?, display_name) "
            "WHERE account_uuid = ?",
            (account.get("email"), account.get("display_name"), account["account_uuid"]),
        )
        return
    has_default = connection.execute(
        "SELECT 1 FROM accounts WHERE is_default = 1"
    ).fetchone()
    connection.execute(
        "INSERT INTO accounts (account_uuid, label, email, display_name, is_default) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            account["account_uuid"],
            _default_label(account.get("email"), account.get("display_name"), account["account_uuid"]),
            account.get("email"),
            account.get("display_name"),
            0 if has_default else 1,
        ),
    )


def get_default_account_uuid(connection):
    row = connection.execute("SELECT account_uuid FROM accounts WHERE is_default = 1").fetchone()
    return row[0] if row else None


def sync_events(connection, events_path=EVENTS_PATH):
    """Load new hook events, register accounts, and make sure a default exists.
    Must run before transcripts are ingested so rows resolve correctly."""
    schema.migrate(connection)

    # The logged-in account is registered even before the hook has fired, so
    # the very first ingest still has a default for existing history.
    current = read_current_account()
    if current:
        register_account(connection, current)

    state = connection.execute(
        "SELECT offset FROM file_state WHERE path = ?", (EVENTS_STATE_KEY,)
    ).fetchone()
    offset = state[0] if state else 0
    consumed = 0
    if events_path.exists():
        with open(events_path, "rb") as file_handle:
            file_handle.seek(offset)
            for raw_line in file_handle:
                if not raw_line.endswith(b"\n"):
                    break  # partially written line; pick it up next run
                consumed += len(raw_line)
                try:
                    event = json.loads(raw_line)
                    session_id, ts, account_uuid = event["session_id"], event["ts"], event["account_uuid"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                register_account(connection, {
                    "account_uuid": account_uuid,
                    "email": event.get("email"),
                    "display_name": event.get("display_name"),
                })
                connection.execute(
                    "INSERT INTO session_accounts (session_id, ts, account_uuid) VALUES (?, ?, ?) "
                    "ON CONFLICT(session_id, ts) DO UPDATE SET account_uuid = excluded.account_uuid",
                    (session_id, ts, account_uuid),
                )
    connection.execute(
        "INSERT INTO file_state (path, offset) VALUES (?, ?) "
        "ON CONFLICT(path) DO UPDATE SET offset = excluded.offset",
        (EVENTS_STATE_KEY, offset + consumed),
    )
    backfill_default(connection)


def backfill_default(connection):
    """Rows with no account (history, or ingested while no default existed)
    belong to the default account."""
    default_uuid = get_default_account_uuid(connection)
    if not default_uuid:
        return
    for table in ("usage", "prompts", "usage_snapshots"):
        connection.execute(
            f"UPDATE {table} SET account_uuid = ? WHERE account_uuid IS NULL", (default_uuid,)
        )


class AccountResolver:
    """session_id + timestamp -> account_uuid, from the loaded hook events."""

    def __init__(self, connection):
        self.default_uuid = get_default_account_uuid(connection)
        self._by_session = {}
        for session_id, ts, account_uuid in connection.execute(
            "SELECT session_id, ts, account_uuid FROM session_accounts ORDER BY session_id, ts"
        ):
            entry = self._by_session.setdefault(session_id, ([], []))
            entry[0].append(ts)
            entry[1].append(account_uuid)

    def resolve(self, session_id, timestamp):
        entry = self._by_session.get(session_id)
        if not entry or not timestamp:
            return self.default_uuid
        index = bisect_right(entry[0], timestamp) - 1
        # A row stamped just before the first event of its session (clock
        # skew between hook and harness) still belongs to that first account.
        return entry[1][max(index, 0)]
