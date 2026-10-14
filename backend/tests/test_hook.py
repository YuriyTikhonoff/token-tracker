import json
import subprocess
import sys
from pathlib import Path

import token_tracker

HOOK = Path(token_tracker.__file__).with_name("hook.py")


def _run(config_dir, event, session="s1"):
    subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"session_id": session, "hook_event_name": event}),
        text=True, check=True, env={"CLAUDE_CONFIG_DIR": str(config_dir), "HOME": str(config_dir)},
    )


def _login(config_dir, uuid):
    (config_dir / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": uuid, "emailAddress": f"{uuid}@x.c"}}))


def _events(config_dir):
    path = config_dir / "token-tracker-account-events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_session_start_always_records_and_prompts_record_only_changes(tmp_path):
    _login(tmp_path, "me")
    _run(tmp_path, "SessionStart")
    _run(tmp_path, "UserPromptSubmit")
    _run(tmp_path, "UserPromptSubmit")
    assert [e["account_uuid"] for e in _events(tmp_path)] == ["me"]

    _login(tmp_path, "guest")
    _run(tmp_path, "UserPromptSubmit")
    _run(tmp_path, "UserPromptSubmit")
    _login(tmp_path, "me")
    _run(tmp_path, "UserPromptSubmit")

    events = _events(tmp_path)
    assert [(e["account_uuid"], e["source"]) for e in events] == [
        ("me", "SessionStart"), ("guest", "UserPromptSubmit"), ("me", "UserPromptSubmit"),
    ]


def test_sessions_are_tracked_separately(tmp_path):
    _login(tmp_path, "me")
    _run(tmp_path, "UserPromptSubmit", session="a")
    _run(tmp_path, "UserPromptSubmit", session="b")
    assert sorted(e["session_id"] for e in _events(tmp_path)) == ["a", "b"]


def test_the_hook_never_fails_the_session(tmp_path):
    # no .claude.json, garbage on stdin: still exit code 0, nothing written
    result = subprocess.run(
        [sys.executable, str(HOOK)], input="not json", text=True,
        env={"CLAUDE_CONFIG_DIR": str(tmp_path), "HOME": str(tmp_path)},
    )
    assert result.returncode == 0
    assert _events(tmp_path) == []
