#!/usr/bin/env python3
"""Claude Code hook: record which account a session runs under.

Registered for two events (see README.md, "Several accounts"):
- SessionStart: always appends an event, so a new or resumed session is tied
  to the account logged in at that moment.
- UserPromptSubmit: appends an event only when the logged-in account differs
  from the one last recorded for the session, which catches a /login done in
  the middle of a conversation.

Appends JSON lines to the events file that ingest.py reads (accounts.py).
Stdlib only, importable and runnable as a plain script (`python3 hook.py`), and
never fails the session: any error is swallowed.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Same rules as config.py (this script stays stdlib-only and
# standalone): a custom CLAUDE_CONFIG_DIR holds its own .claude.json.
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()
EVENTS_PATH = CLAUDE_DIR / "token-tracker-account-events.jsonl"
STATE_PATH = CLAUDE_DIR / "token-tracker-account-state.json"
CLAUDE_JSON_PATH = (
    Path.home() / ".claude.json" if CLAUDE_DIR == Path.home() / ".claude" else CLAUDE_DIR / ".claude.json"
)
STATE_MAX_AGE_SECONDS = 7 * 24 * 3600


def load_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    now = time.time()
    state = {k: v for k, v in state.items() if now - v.get("seen", 0) < STATE_MAX_AGE_SECONDS}
    tmp_path = STATE_PATH.with_suffix(f".{os.getpid()}.tmp")
    tmp_path.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp_path, STATE_PATH)


def main():
    try:
        payload = json.load(sys.stdin)
        session_id = payload["session_id"]
        event_name = payload.get("hook_event_name", "SessionStart")
        oauth = json.loads(CLAUDE_JSON_PATH.read_text(encoding="utf-8")).get("oauthAccount") or {}
        account_uuid = oauth.get("accountUuid")
        if not account_uuid:
            return

        state = load_state()
        last = state.get(session_id)
        if event_name == "UserPromptSubmit" and last and last.get("account_uuid") == account_uuid:
            return

        now = datetime.now(timezone.utc)
        event = {
            "ts": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
            "session_id": session_id,
            "account_uuid": account_uuid,
            "email": oauth.get("emailAddress"),
            "display_name": oauth.get("displayName"),
            "source": event_name,
        }
        with open(EVENTS_PATH, "a", encoding="utf-8") as file_handle:
            file_handle.write(json.dumps(event) + "\n")
        state[session_id] = {"account_uuid": account_uuid, "seen": time.time()}
        save_state(state)
    except Exception:
        pass


if __name__ == "__main__":
    main()
