#!/usr/bin/env python3
"""Parse Codex CLI rollout JSONL logs and load token usage + rate-limit
snapshots into SQLite.

Incremental: tracks a byte offset per rollout file (same pattern as
ingest.py), so re-running only processes newly appended lines. Safe to run
repeatedly.

Codex CLI writes ~/.codex/sessions/<year>/<month>/<day>/rollout-*.jsonl, one
line per event. Two shapes carry what we need, both written once per turn:

- A top-level `{"type": "token_usage_record", "payload": {...}}` line with
  this turn's actual billed usage (input/cached_input/cache_write_input/
  output/reasoning_output/total) -- summed the same way ingest.py sums
  Claude's per-call `usage` blocks.
- A `{"type": "event_msg", "payload": {"type": "token_count", ...,
  "rate_limits": {"primary": {...}, "secondary": {...}}}}` line carrying the
  account's 5h/weekly rate-limit percentages directly (no `codex /status`
  shell-out needed -- unlike Claude, Codex logs this on every turn already).
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import config
import queries

DEFAULT_SESSIONS_DIR = config.codex_sessions_dir()
DEFAULT_DB_PATH = queries.DEFAULT_DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS codex_file_state (
    path TEXT PRIMARY KEY,
    offset INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS codex_usage (
    response_id TEXT PRIMARY KEY,
    thread_id TEXT,
    session_id TEXT,
    timestamp TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_codex_usage_timestamp ON codex_usage(timestamp);

CREATE TABLE IF NOT EXISTS codex_rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    primary_pct REAL,
    primary_window_minutes INTEGER,
    primary_resets_at TEXT,
    secondary_pct REAL,
    secondary_window_minutes INTEGER,
    secondary_resets_at TEXT,
    plan_type TEXT
);
"""


def get_file_offset(connection, path):
    row = connection.execute(
        "SELECT offset FROM codex_file_state WHERE path = ?", (str(path),)
    ).fetchone()
    return row[0] if row else 0


def set_file_offset(connection, path, offset):
    connection.execute(
        "INSERT INTO codex_file_state (path, offset) VALUES (?, ?) "
        "ON CONFLICT(path) DO UPDATE SET offset = excluded.offset",
        (str(path), offset),
    )


def _truncate_to_seconds(iso_timestamp):
    """Codex timestamps carry milliseconds ("...T06:09:48.948Z"); normalize to
    whole-second precision so this lines up with usage_snapshots.captured_at's
    format and queries.py's shared trend-extrapolation helpers can consume
    both without modification."""
    parsed = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch_to_iso(epoch_seconds):
    if epoch_seconds is None:
        return None
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def process_file(connection, path):
    offset = get_file_offset(connection, path)
    new_usage_count = 0
    new_rate_limit_count = 0
    with open(path, "r", encoding="utf-8") as file_handle:
        file_handle.seek(offset)
        new_bytes_consumed = 0
        for raw_line in file_handle:
            line = raw_line.strip()
            new_bytes_consumed += len(raw_line.encode("utf-8"))
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            timestamp = entry.get("timestamp")

            if entry_type == "token_usage_record":
                payload = entry.get("payload") or {}
                usage = payload.get("usage") or {}
                response_id = payload.get("response_id")
                if not response_id:
                    continue
                cursor = connection.execute(
                    "INSERT INTO codex_usage (response_id, thread_id, session_id, timestamp, "
                    "input_tokens, cached_input_tokens, cache_write_input_tokens, "
                    "output_tokens, reasoning_output_tokens, total_tokens) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(response_id) DO NOTHING",
                    (
                        response_id,
                        payload.get("thread_id"),
                        payload.get("session_id"),
                        timestamp,
                        usage.get("input_tokens", 0),
                        usage.get("cached_input_tokens", 0),
                        usage.get("cache_write_input_tokens", 0),
                        usage.get("output_tokens", 0),
                        usage.get("reasoning_output_tokens", 0),
                        usage.get("total_tokens", 0),
                    ),
                )
                if cursor.rowcount:
                    new_usage_count += 1

            elif entry_type == "event_msg":
                inner = entry.get("payload") or {}
                if inner.get("type") != "token_count":
                    continue
                rate_limits = inner.get("rate_limits")
                if not rate_limits or not timestamp:
                    continue
                primary = rate_limits.get("primary") or {}
                secondary = rate_limits.get("secondary") or {}
                connection.execute(
                    "INSERT INTO codex_rate_limits (captured_at, primary_pct, "
                    "primary_window_minutes, primary_resets_at, secondary_pct, "
                    "secondary_window_minutes, secondary_resets_at, plan_type) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        _truncate_to_seconds(timestamp),
                        primary.get("used_percent"),
                        primary.get("window_minutes"),
                        _epoch_to_iso(primary.get("resets_at")),
                        secondary.get("used_percent"),
                        secondary.get("window_minutes"),
                        _epoch_to_iso(secondary.get("resets_at")),
                        rate_limits.get("plan_type"),
                    ),
                )
                new_rate_limit_count += 1

        set_file_offset(connection, path, offset + new_bytes_consumed)

    return new_usage_count, new_rate_limit_count


def run(sessions_dir=DEFAULT_SESSIONS_DIR, db_path=DEFAULT_DB_PATH):
    connection = queries.connect(db_path)
    connection.executescript(SCHEMA)

    rollout_files = sorted(sessions_dir.rglob("*.jsonl")) if sessions_dir.exists() else []
    new_usage_count = 0
    new_rate_limit_count = 0
    for path in rollout_files:
        file_usage_count, file_rate_limit_count = process_file(connection, path)
        new_usage_count += file_usage_count
        new_rate_limit_count += file_rate_limit_count

    connection.commit()
    connection.close()
    return {
        "file_count": len(rollout_files),
        "new_usage_count": new_usage_count,
        "new_rate_limit_count": new_rate_limit_count,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    result = run(args.sessions_dir, args.db)
    print(f"Processed {result['file_count']} rollout file(s) into {args.db}")
    print(f"NEW_CODEX_USAGE={result['new_usage_count']}")
    print(f"NEW_CODEX_RATE_LIMITS={result['new_rate_limit_count']}")


if __name__ == "__main__":
    main()
