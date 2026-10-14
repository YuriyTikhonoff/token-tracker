#!/usr/bin/env python3
"""Force a fresh Codex rate-limit reading by running a trivial `codex exec`
turn, then re-running codex_ingest.py so the new rollout line lands in the DB.

Unlike Claude (usage_snapshot.py's `claude -p "/usage"`), Codex has no
side-effect-free status check: every `codex exec` invocation is a real
billed turn (~15k tokens observed for a one-word reply). Codex's rate-limit
snapshot is otherwise only as fresh as the last real turn the user happened
to run (see codex_ingest.py / CODEX.md), so unlike usage_snapshot.py this is
deliberately NOT run on a timer (watch.sh never calls it) -- only from an
explicit user-triggered refresh, where spending the tokens is the user's own
informed call rather than a background cost that compounds unattended.
"""
import argparse
import subprocess
from pathlib import Path

from . import codex_ingest

DEFAULT_SESSIONS_DIR = codex_ingest.DEFAULT_SESSIONS_DIR
DEFAULT_DB_PATH = codex_ingest.DEFAULT_DB_PATH

# Kept short and side-effect-free (read-only sandbox, no repo needed) to
# minimize both the token cost and the chance of the model doing real work.
PROMPT = 'Reply with just the word "ok" and nothing else.'


def trigger_fresh_turn(timeout=60):
    subprocess.run(
        [
            "codex", "exec",
            "--skip-git-repo-check",
            "--sandbox", "read-only",
            PROMPT,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )


def run(sessions_dir=DEFAULT_SESSIONS_DIR, db_path=DEFAULT_DB_PATH):
    trigger_fresh_turn()
    return codex_ingest.run(sessions_dir, db_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args(argv)

    result = run(args.sessions_dir, args.db)
    print("Triggered a fresh Codex turn and re-ingested rollout logs")
    print(f"NEW_CODEX_USAGE={result['new_usage_count']}")
    print(f"NEW_CODEX_RATE_LIMITS={result['new_rate_limit_count']}")


if __name__ == "__main__":
    main()
