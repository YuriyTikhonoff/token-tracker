#!/usr/bin/env python3
"""Parse Claude Code JSONL transcripts and load token usage into SQLite.

Incremental: tracks a byte offset per transcript file so re-running only
processes newly appended lines. Safe to run repeatedly (e.g. from cron or a
loop).
"""
import argparse
import json
import re
from pathlib import Path

from . import accounts, config, queries, schema

DEFAULT_PROJECTS_DIR = config.claude_projects_dir()
DEFAULT_DB_PATH = queries.DEFAULT_DB_PATH

# Harness-injected wrapper tags that arrive as role="user" text blocks but
# aren't something a human typed (task completion notices, slash-command
# plumbing, IDE context). Stripped out before building a prompt preview.
INJECTED_TAGS = (
    "task-notification",
    "command-name",
    "command-message",
    "command-args",
    "command-contents",
    "local-command-stdout",
    "local-command-stderr",
    "local-command-caveat",
    "user-prompt-submit-hook",
    "system-reminder",
    "ide_selection",
    "ide_opened_file",
    "ide_diagnostics",
)
INJECTED_TAG_PATTERN = re.compile(
    r"<({tags})\b[^>]*>.*?</\1>".format(tags="|".join(re.escape(tag) for tag in INJECTED_TAGS)),
    re.DOTALL,
)


def strip_injected_tags(text):
    return INJECTED_TAG_PATTERN.sub("", text)



def extract_preview(message_content, limit=200):
    if isinstance(message_content, str):
        text = message_content
    elif isinstance(message_content, list):
        text = " ".join(
            block.get("text", "")
            for block in message_content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    else:
        text = ""
    text = strip_injected_tags(text)
    text = " ".join(text.split())
    return text[:limit]


def get_file_offset(connection, path):
    row = connection.execute(
        "SELECT offset FROM file_state WHERE path = ?", (str(path),)
    ).fetchone()
    return row[0] if row else 0


def set_file_offset(connection, path, offset):
    connection.execute(
        "INSERT INTO file_state (path, offset) VALUES (?, ?) "
        "ON CONFLICT(path) DO UPDATE SET offset = excluded.offset",
        (str(path), offset),
    )


def lookup_prompt_id(connection, uuid, cache):
    if uuid in cache:
        return cache[uuid]
    row = connection.execute(
        "SELECT prompt_id FROM uuid_prompt_map WHERE uuid = ?", (uuid,)
    ).fetchone()
    result = row[0] if row else None
    cache[uuid] = result
    return result


def record_uuid_prompt(connection, cache, uuid, prompt_id, session_id):
    cache[uuid] = prompt_id
    connection.execute(
        "INSERT INTO uuid_prompt_map (uuid, prompt_id, session_id) VALUES (?, ?, ?) "
        "ON CONFLICT(uuid) DO UPDATE SET prompt_id = excluded.prompt_id",
        (uuid, prompt_id, session_id),
    )


def touch_session(connection, session_id, project, timestamp):
    connection.execute(
        "INSERT INTO sessions (session_id, project, first_seen, last_seen) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(session_id) DO UPDATE SET last_seen = excluded.last_seen",
        (session_id, project, timestamp, timestamp),
    )


def process_file(connection, path, project, prompt_cache, resolver):
    offset = get_file_offset(connection, path)
    new_prompt_count = 0
    new_meaningful_prompt_count = 0
    with open(path, encoding="utf-8") as file_handle:
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
            uuid = entry.get("uuid")
            parent_uuid = entry.get("parentUuid")
            timestamp = entry.get("timestamp")
            session_id = entry.get("sessionId") or path.stem

            # Any entry that can sit in the parentUuid chain between a user
            # prompt and the assistant reply needs a uuid -> prompt_id mapping,
            # or usage rows lose their attribution. The harness added
            # "attachment" entries as an intermediate link in Sept 2026.
            if entry_type in ("user", "assistant", "attachment") and uuid:
                own_prompt_id = entry.get("promptId")
                inherited_prompt_id = (
                    lookup_prompt_id(connection, parent_uuid, prompt_cache)
                    if parent_uuid
                    else None
                )
                prompt_id = own_prompt_id or inherited_prompt_id
                record_uuid_prompt(connection, prompt_cache, uuid, prompt_id, session_id)
                if entry_type in ("user", "assistant"):
                    touch_session(connection, session_id, project, timestamp)

            if entry_type == "user" and entry.get("promptId") and not entry.get("isMeta"):
                preview = extract_preview(entry.get("message", {}).get("content"))
                cursor = connection.execute(
                    "INSERT INTO prompts (prompt_id, session_id, preview, timestamp, account_uuid) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(prompt_id) DO NOTHING",
                    (entry["promptId"], session_id, preview, timestamp,
                     resolver.resolve(session_id, timestamp)),
                )
                if cursor.rowcount:
                    new_prompt_count += 1
                    if preview:
                        new_meaningful_prompt_count += 1

            if entry_type == "assistant":
                message = entry.get("message", {})
                usage = message.get("usage")
                if usage and uuid:
                    prompt_id = lookup_prompt_id(connection, uuid, prompt_cache)
                    connection.execute(
                        "INSERT INTO usage (assistant_uuid, session_id, prompt_id, model, "
                        "input_tokens, output_tokens, cache_creation_tokens, "
                        "cache_read_tokens, timestamp, account_uuid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                        "ON CONFLICT(assistant_uuid) DO NOTHING",
                        (
                            uuid,
                            session_id,
                            prompt_id,
                            message.get("model"),
                            usage.get("input_tokens", 0),
                            usage.get("output_tokens", 0),
                            usage.get("cache_creation_input_tokens", 0),
                            usage.get("cache_read_input_tokens", 0),
                            timestamp,
                            resolver.resolve(session_id, timestamp),
                        ),
                    )

        set_file_offset(connection, path, offset + new_bytes_consumed)

    return new_prompt_count, new_meaningful_prompt_count


def _resolve_prompt_id(entry, by_uuid, depth=0):
    """Walk the parentUuid chain from `entry` back to the promptId it started from."""
    if entry.get("promptId"):
        return entry["promptId"]
    parent = by_uuid.get(entry.get("parentUuid"))
    if parent is None or depth > 100:
        return None
    return _resolve_prompt_id(parent, by_uuid, depth + 1)


def backfill_prompt_ids(connection, projects_dir):
    """Re-attribute existing usage rows whose prompt_id is NULL by walking each
    transcript's parentUuid chain from the assistant entry back to a promptId.
    Idempotent; only touches rows that are currently unattributed."""
    updated = 0
    for path in sorted(projects_dir.glob("*/*.jsonl")):
        try:
            entries = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
        except (OSError, json.JSONDecodeError):
            continue
        by_uuid = {e["uuid"]: e for e in entries if e.get("uuid")}

        for entry in entries:
            if entry.get("type") != "assistant" or not entry.get("uuid"):
                continue
            if not entry.get("message", {}).get("usage"):
                continue
            prompt_id = _resolve_prompt_id(entry, by_uuid)
            if not prompt_id:
                continue
            cursor = connection.execute(
                "UPDATE usage SET prompt_id = ? "
                "WHERE assistant_uuid = ? AND (prompt_id IS NULL OR prompt_id = '')",
                (prompt_id, entry["uuid"]),
            )
            updated += cursor.rowcount
    connection.commit()
    return updated


def run(projects_dir, db_path):
    connection = queries.connect(db_path)
    schema.migrate(connection)
    # Events first: rows ingested below are attributed from them.
    accounts.sync_events(connection)
    resolver = accounts.AccountResolver(connection)
    prompt_cache = {}

    transcript_files = sorted(projects_dir.glob("*/*.jsonl"))
    new_prompt_count = 0
    new_meaningful_prompt_count = 0
    for path in transcript_files:
        project = path.parent.name
        file_new_prompt_count, file_new_meaningful_prompt_count = process_file(
            connection, path, project, prompt_cache, resolver
        )
        new_prompt_count += file_new_prompt_count
        new_meaningful_prompt_count += file_new_meaningful_prompt_count

    connection.commit()
    connection.close()
    return {
        "file_count": len(transcript_files),
        "new_prompt_count": new_prompt_count,
        "new_meaningful_prompt_count": new_meaningful_prompt_count,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=DEFAULT_PROJECTS_DIR,
        help="Directory containing Claude Code project transcripts",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Re-attribute existing usage rows with a missing prompt_id, then exit",
    )
    args = parser.parse_args(argv)

    if args.backfill:
        connection = queries.connect(args.db)
        updated = backfill_prompt_ids(connection, args.projects_dir)
        connection.close()
        print(f"Backfilled prompt_id on {updated} usage row(s)")
        return

    result = run(args.projects_dir, args.db)
    print(f"Processed {result['file_count']} transcript file(s) into {args.db}")
    print(f"NEW_PROMPTS={result['new_prompt_count']}")
    print(f"NEW_MEANINGFUL_PROMPTS={result['new_meaningful_prompt_count']}")


if __name__ == "__main__":
    main()
