"""Every test runs against throwaway directories, never the real home.

The environment is set before token_tracker is imported, because several
modules read it once at import.
"""
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

_ROOT = Path(tempfile.mkdtemp(prefix="token-tracker-tests-"))
os.environ["TOKEN_TRACKER_HOME"] = str(_ROOT / "data")
os.environ["CLAUDE_CONFIG_DIR"] = str(_ROOT / "claude")
os.environ["CODEX_HOME"] = str(_ROOT / "codex")
os.environ["TOKEN_TRACKER_TZ"] = "UTC"

import pytest  # noqa: E402

from token_tracker import schema  # noqa: E402

CLAUDE_DIR = _ROOT / "claude"


@pytest.fixture(autouse=True)
def clean_claude_dir():
    shutil.rmtree(CLAUDE_DIR, ignore_errors=True)
    CLAUDE_DIR.mkdir(parents=True)
    yield


@pytest.fixture
def login():
    """Log an account in, the way Claude Code records it in .claude.json."""

    def _login(uuid, email=None, name=None):
        (CLAUDE_DIR / ".claude.json").write_text(
            json.dumps({"oauthAccount": {"accountUuid": uuid, "emailAddress": email, "displayName": name}})
        )

    return _login


@pytest.fixture
def db(tmp_path):
    connection = sqlite3.connect(tmp_path / "test.db", check_same_thread=False)
    schema.migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def pricing():
    return {
        "_default": {"input": 10, "output": 10, "cache_creation": 10, "cache_read": 10},
        "m": {"input": 1, "output": 2, "cache_creation": 3, "cache_read": 4},
    }
