import json

from token_tracker import config


def test_environment_beats_the_file_beats_the_default(monkeypatch):
    monkeypatch.setattr(config, "_FILE", {"claude_dir": "/from/file"})
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    assert str(config.claude_dir()) == "/from/file"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/from/env")
    assert str(config.claude_dir()) == "/from/env"
    monkeypatch.setattr(config, "_FILE", {})
    monkeypatch.delenv("CLAUDE_CONFIG_DIR")
    assert config.claude_dir() == config.Path.home() / ".claude"


def test_a_custom_claude_dir_holds_its_own_claude_json(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert config.claude_json_path() == tmp_path / ".claude.json"
    assert config.account_events_path() == tmp_path / "token-tracker-account-events.jsonl"
    assert config.claude_projects_dir() == tmp_path / "projects"


def test_the_default_claude_dir_uses_the_json_in_home(monkeypatch):
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setattr(config, "_FILE", {})
    assert config.claude_json_path() == config.Path.home() / ".claude.json"


def test_database_goes_in_the_data_dir_and_never_falls_back_when_the_home_is_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_TRACKER_HOME", str(tmp_path))
    monkeypatch.delenv("TOKEN_TRACKER_DB", raising=False)
    assert config.db_path() == tmp_path / "token_tracker.db"
    monkeypatch.setenv("TOKEN_TRACKER_DB", str(tmp_path / "elsewhere.db"))
    assert config.db_path() == tmp_path / "elsewhere.db"


def test_timezone_prefers_the_setting_and_survives_a_bad_name(monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_TZ", "Asia/Tokyo")
    assert config.timezone().key == "Asia/Tokyo"
    monkeypatch.setenv("TOKEN_TRACKER_TZ", "Not/AZone")
    assert config.timezone().key != "Not/AZone"  # falls through to TZ, the system zone or UTC


def test_user_prices_override_and_extend_the_shipped_ones(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_TRACKER_HOME", str(tmp_path))
    shipped = config.load_pricing()
    assert "claude-opus-5-5" in shipped and shipped["_meta"]["updated"]

    (tmp_path / "pricing.json").write_text(json.dumps({
        "claude-opus-5-5": {"input": 1, "output": 1, "cache_creation": 1, "cache_read": 1},
        "my-model": {"input": 9, "output": 9, "cache_creation": 9, "cache_read": 9},
    }))
    merged = config.load_pricing()
    assert merged["claude-opus-5-5"]["input"] == 1
    assert merged["my-model"]["input"] == 9
    assert merged["claude-sonnet-5-5"] == shipped["claude-sonnet-5-5"]


def test_a_broken_user_pricing_file_is_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_TRACKER_HOME", str(tmp_path))
    (tmp_path / "pricing.json").write_text("{ nope")
    assert "claude-opus-5-5" in config.load_pricing()


def test_every_shipped_price_is_complete():
    for model, rates in config.load_pricing(config.SHIPPED_PRICING_PATH).items():
        if model.startswith("_") and model != "_default":
            continue
        assert set(rates) == {"input", "output", "cache_creation", "cache_read"}, model
