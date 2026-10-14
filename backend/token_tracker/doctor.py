"""`token-tracker doctor`: what is set up, what is missing, in plain lines."""
import shutil
import sqlite3
import sys
from pathlib import Path

from . import accounts, config, hooks_install, queries

STATIC_DIR = Path(__file__).parent / "static"


def _line(ok, label, detail=""):
    mark = {True: "ok  ", False: "FAIL", None: "info"}[ok]
    print(f"[{mark}] {label}" + (f": {detail}" if detail else ""))
    return ok is not False


def run() -> int:
    healthy = True
    print(f"Python {sys.version.split()[0]}, time zone {config.timezone().key}")

    data_dir = config.data_dir()
    _line(None, "data directory", f"{data_dir}" + ("" if data_dir.exists() else " (created on first ingest)"))

    claude_dir = config.claude_dir()
    projects = config.claude_projects_dir()
    transcripts = len(list(projects.glob("*/*.jsonl"))) if projects.is_dir() else 0
    healthy &= _line(projects.is_dir() and transcripts > 0, "Claude Code transcripts",
                     f"{transcripts} file(s) in {projects}" if transcripts else f"none found in {projects}; set CLAUDE_CONFIG_DIR if yours is elsewhere")
    _line(shutil.which("claude") is not None, "claude CLI on PATH",
          "needed only for subscription-limit snapshots (/usage)" if not shutil.which("claude") else "")
    codex = config.codex_sessions_dir()
    _line(None, "Codex sessions", f"{codex}" + ("" if codex.is_dir() else " (not found, Codex tracking stays empty)"))

    db = config.db_path()
    if db.exists():
        try:
            connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            rows, latest = connection.execute("SELECT COUNT(*), MAX(timestamp) FROM usage").fetchone()
            _line(True, "database", f"{db} ({rows} usage rows, latest {latest})")
            try:
                account_rows = connection.execute("SELECT label FROM accounts ORDER BY is_default DESC").fetchall()
                _line(None, "accounts", ", ".join(row[0] for row in account_rows) or "none yet")
            except sqlite3.OperationalError:
                _line(None, "accounts", "none yet (run an ingest)")
            unknown = queries.get_unknown_models(connection, config.load_pricing())
            _line(not unknown, "prices", "every model has a price" if not unknown
                  else f"no price for {', '.join(unknown)}; add them to {config.pricing_override_path()}")
            connection.close()
        except sqlite3.Error as error:
            healthy &= _line(False, "database", f"{db}: {error}")
    else:
        _line(None, "database", f"{db} does not exist yet; run `token-tracker ingest`")

    try:
        settings = hooks_install.load_settings(hooks_install.settings_path())
        present = hooks_install.installed_events(settings)
        missing = [event for event in hooks_install.EVENTS if event not in present]
        healthy &= _line(not missing, "account hooks",
                         "installed" if not missing else f"missing {', '.join(missing)}; run `token-tracker install-hooks`")
    except hooks_install.SettingsError as error:
        healthy &= _line(False, "account hooks", str(error))

    events = accounts.EVENTS_PATH
    count = sum(1 for _ in open(events, encoding="utf-8")) if events.exists() else 0
    _line(None, "account events recorded", f"{count} in {events}")

    _line(None, "web dashboard", "bundled" if (STATIC_DIR / "index.html").exists()
          else "not bundled in this checkout (use `npm run dev` in frontend/, or `npm run build:package`)")
    return 0 if healthy else 1
