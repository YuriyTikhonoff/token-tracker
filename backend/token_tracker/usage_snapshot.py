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
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import accounts, queries, schema

DEFAULT_DB_PATH = queries.DEFAULT_DB_PATH
UTC_TZ = ZoneInfo("UTC")
STALE_RESET_WRAP_DAYS = 180
# `/usage` also analyses the local transcripts (what contributes to the limits),
# so it slows down as they grow: about 48 s with a week of heavy use, and it
# kept timing out at the old 30 s.
USAGE_TIMEOUT_SECONDS = 150


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
        timeout=USAGE_TIMEOUT_SECONDS,
        check=True,
    )
    return result.stdout


# A snapshot takes up to a minute, so the dashboard's refresh starts one in the
# background and does not wait. One at a time: a burst of refreshes (every
# window focus asks for one) must not pile up slow `claude` processes.
_background = threading.Lock()
_last_error = None


def last_background_error():
    """What went wrong in the latest background snapshot, or None when it worked."""
    return _last_error


def start_in_background(db_path):
    """Start a snapshot unless one is already running. Returns "started" or "running"."""
    if not _background.acquire(blocking=False):
        return "running"

    def work():
        global _last_error
        try:
            run(db_path)
            _last_error = None
        except Exception as error:  # a failed snapshot must not take the server down
            _last_error = f"{type(error).__name__}: {error}"
            print(f"usage snapshot failed: {_last_error}", file=sys.stderr)
        finally:
            _background.release()

    threading.Thread(target=work, name="usage-snapshot", daemon=True).start()
    return "started"


def run(db_path):
    now_local = datetime.now(queries.LOCAL_TZ)
    snapshots = parse_usage_output(capture_usage_output(), now_local)

    connection = queries.connect(db_path)
    schema.migrate(connection)
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args(argv)

    snapshots = run(args.db)
    if not snapshots:
        print("No usage lines parsed from `claude -p /usage` output.")
        return
    for snapshot in snapshots:
        suffix = f" (resets {snapshot['resets_at']})" if snapshot["resets_at"] else ""
        print(f"{snapshot['scope']}: {snapshot['pct_used']:.0f}% used{suffix}")


if __name__ == "__main__":
    main()
