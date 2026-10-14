#!/usr/bin/env python3
"""Snapshot Claude subscription usage (session/weekly % used) via the
`claude` CLI and store it in token_tracker.db.

Runs `claude -p "/usage"` (non-interactive), parses the percentage-used
lines, and inserts one row per scope (e.g. "Current session",
"Current week (all models)") into usage_snapshots. Intended to run
periodically (e.g. from watch.sh) so a trend accumulates over time.
"""
import argparse
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import accounts
from . import queries

DEFAULT_DB_PATH = queries.DEFAULT_DB_PATH
UTC_TZ = ZoneInfo("UTC")
STALE_RESET_WRAP_DAYS = 180

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    scope TEXT NOT NULL,
    pct_used REAL NOT NULL,
    resets_at_raw TEXT,
    resets_at TEXT
);
"""

# e.g. "Current session: 11% used · resets Jul 8 at 4:49pm (Europe/Kiev)"
# e.g. "Current week (Fable): 0% used"
LINE_PATTERN = re.compile(
    r"^(?P<scope>[^:]+):\s*(?P<pct>\d+)%\s*used"
    r"(?:\s*·\s*resets\s*(?P<resets>.+))?$"
)
RESETS_PATTERN = re.compile(
    r"(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+at\s+"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?(?P<ampm>am|pm)",
    re.IGNORECASE,
)
# The CLI prints the zone it used in parentheses, e.g. "(Europe/Kiev)".
ZONE_PATTERN = re.compile(r"\(([A-Za-z_]+(?:/[A-Za-z_+\-0-9]+)+)\)")
MONTH_NUMBERS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def zone_from_text(resets_text, default):
    """The zone the CLI said it formatted the time in, else `default`."""
    match = ZONE_PATTERN.search(resets_text or "")
    if match:
        try:
            return ZoneInfo(match.group(1))
        except (ZoneInfoNotFoundError, ValueError, OSError):
            pass
    return default


def parse_resets_at(resets_text, now_local):
    if not resets_text:
        return None
    now_local = now_local.astimezone(zone_from_text(resets_text, now_local.tzinfo))
    match = RESETS_PATTERN.search(resets_text)
    if not match:
        return None
    month = MONTH_NUMBERS.get(match.group("month").lower())
    if not month:
        return None
    day = int(match.group("day"))
    hour = int(match.group("hour")) % 12
    if match.group("ampm").lower() == "pm":
        hour += 12
    minute = int(match.group("minute") or 0)
    resets_local = now_local.replace(
        month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0
    )
    # The CLI omits the year. A time just behind us is a window that closed
    # (or a stale label), not next year; only wrap when it's far in the past.
    if resets_local < now_local - timedelta(days=STALE_RESET_WRAP_DAYS):
        resets_local = resets_local.replace(year=now_local.year + 1)
    return resets_local.astimezone(UTC_TZ).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_usage_output(output, now_local):
    snapshots = []
    for line in output.splitlines():
        match = LINE_PATTERN.match(line.strip())
        if not match:
            continue
        resets_raw = (match.group("resets") or "").strip() or None
        snapshots.append({
            "scope": match.group("scope").strip(),
            "pct_used": float(match.group("pct")),
            "resets_at_raw": resets_raw,
            "resets_at": parse_resets_at(resets_raw, now_local),
        })
    return snapshots


def capture_usage_output():
    result = subprocess.run(
        ["claude", "-p", "/usage"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout


def run(db_path):
    now_local = datetime.now(queries.LOCAL_TZ)
    snapshots = parse_usage_output(capture_usage_output(), now_local)

    connection = queries.connect(db_path)
    connection.executescript(SCHEMA)
    accounts.ensure_schema(connection)
    # /usage reports the limits of whoever is logged in right now.
    current = accounts.read_current_account()
    account_uuid = current["account_uuid"] if current else accounts.get_default_account_uuid(connection)
    captured_at = now_local.astimezone(UTC_TZ).strftime("%Y-%m-%dT%H:%M:%SZ")
    for snapshot in snapshots:
        connection.execute(
            "INSERT INTO usage_snapshots (captured_at, scope, pct_used, resets_at_raw, resets_at, account_uuid) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (captured_at, snapshot["scope"], snapshot["pct_used"],
             snapshot["resets_at_raw"], snapshot["resets_at"], account_uuid),
        )
    connection.commit()
    connection.close()
    return snapshots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    snapshots = run(args.db)
    if not snapshots:
        print("No usage lines parsed from `claude -p /usage` output.")
        return
    for snapshot in snapshots:
        suffix = f" (resets {snapshot['resets_at']})" if snapshot["resets_at"] else ""
        print(f"{snapshot['scope']}: {snapshot['pct_used']:.0f}% used{suffix}")


if __name__ == "__main__":
    main()
