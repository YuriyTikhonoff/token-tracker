"""Where token-tracker keeps its data and where it reads from.

Every setting resolves in the same order: environment variable, then
`config.toml` in the data directory, then a default. Nothing here depends on
where the repository is checked out.

    data directory   TOKEN_TRACKER_HOME            ~/.token-tracker
    database         TOKEN_TRACKER_DB      db      <data directory>/token_tracker.db
    Claude Code dir  CLAUDE_CONFIG_DIR     claude_dir  ~/.claude
    Codex dir        CODEX_HOME            codex_dir   ~/.codex
    time zone        TOKEN_TRACKER_TZ      timezone    TZ, then the system zone, else UTC

`config.toml` uses the lowercase names above as keys, e.g. `timezone = "Europe/Kyiv"`.
Values are read once at import, so restart the server after changing them.
"""
import json
import os
import sys
import tomllib
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

APP_DIR = Path(__file__).parent
SHIPPED_PRICING_PATH = APP_DIR / "pricing.json"
# Before the data directory existed the database lived in backend/app/, next to
# the code of that time.
LEGACY_DB_PATH = APP_DIR.parent / "app" / "token_tracker.db"


def data_dir() -> Path:
    return Path(os.environ.get("TOKEN_TRACKER_HOME") or Path.home() / ".token-tracker")


def _read_config_file() -> dict:
    path = data_dir() / "config.toml"
    try:
        with open(path, "rb") as file_handle:
            return tomllib.load(file_handle)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError) as error:
        print(f"token-tracker: ignoring unreadable {path}: {error}", file=sys.stderr)
        return {}


_FILE = _read_config_file()


def _setting(env_name, file_key):
    return os.environ.get(env_name) or _FILE.get(file_key) or None


_warned = set()


def _warn_once(message):
    if message not in _warned:
        _warned.add(message)
        print(f"token-tracker: {message}", file=sys.stderr)


def db_path() -> Path:
    explicit = _setting("TOKEN_TRACKER_DB", "db")
    if explicit:
        return Path(explicit).expanduser()
    default = data_dir() / "token_tracker.db"
    # Only when nothing was configured: an explicit TOKEN_TRACKER_HOME must
    # never silently land on the old in-tree database.
    if (
        not os.environ.get("TOKEN_TRACKER_HOME")
        and not default.exists()
        and LEGACY_DB_PATH.exists()
    ):
        _warn_once(
            f"using the database at its old location {LEGACY_DB_PATH}; "
            f"move it (with its -wal and -shm files) to {default} to silence this."
        )
        return LEGACY_DB_PATH
    return default


def _zone(name):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        _warn_once(f"unknown time zone {name!r}, ignoring it")
        return None


def _system_zone_name():
    """IANA name of the system zone: /etc/localtime points into the zoneinfo
    database on macOS and most Linux distributions."""
    try:
        target = os.path.realpath("/etc/localtime")
    except OSError:
        return None
    marker = "zoneinfo/"
    return target.split(marker, 1)[1] if marker in target else None


def timezone() -> ZoneInfo:
    """The zone "today", "this week" and "this month" are cut in, and the one
    times are shown in. Defaults to the system zone, else UTC."""
    for name in (_setting("TOKEN_TRACKER_TZ", "timezone"), os.environ.get("TZ"), _system_zone_name()):
        if name and (zone := _zone(name)):
            return zone
    return ZoneInfo("UTC")


def claude_dir() -> Path:
    return Path(_setting("CLAUDE_CONFIG_DIR", "claude_dir") or Path.home() / ".claude").expanduser()


def claude_projects_dir() -> Path:
    return claude_dir() / "projects"


def claude_json_path() -> Path:
    """The file holding the logged-in account. Claude Code keeps it beside the
    config directory by default and inside it when the directory is customised."""
    directory = claude_dir()
    if directory == Path.home() / ".claude":
        return Path.home() / ".claude.json"
    return directory / ".claude.json"


def account_events_path() -> Path:
    return claude_dir() / "token-tracker-account-events.jsonl"


def codex_sessions_dir() -> Path:
    return Path(_setting("CODEX_HOME", "codex_dir") or Path.home() / ".codex").expanduser() / "sessions"


def pricing_override_path() -> Path:
    return data_dir() / "pricing.json"


def load_pricing(path=None) -> dict:
    """Shipped prices, with per-model entries from the user's pricing.json laid
    over them. `path` loads that one file alone (used by the CLI's --pricing)."""
    if path is not None:
        with open(path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    with open(SHIPPED_PRICING_PATH, "r", encoding="utf-8") as file_handle:
        pricing = json.load(file_handle)
    try:
        with open(pricing_override_path(), "r", encoding="utf-8") as file_handle:
            pricing.update(json.load(file_handle))
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError) as error:
        print(f"token-tracker: ignoring unreadable {pricing_override_path()}: {error}", file=sys.stderr)
    return pricing
