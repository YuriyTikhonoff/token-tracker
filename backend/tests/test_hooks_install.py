import json

import pytest

from token_tracker import hooks_install


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    return tmp_path / "settings.json"


def test_installs_into_a_missing_file(settings):
    assert hooks_install.install() == ["SessionStart", "UserPromptSubmit"]
    data = json.loads(settings.read_text())
    assert set(data["hooks"]) == {"SessionStart", "UserPromptSubmit"}
    assert "hook.py" in data["hooks"]["SessionStart"][0]["hooks"][0]["command"]


def test_keeps_everything_else_and_backs_up(settings):
    original = {"permissions": {"allow": ["Bash(ls)"]}, "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}}
    settings.write_text(json.dumps(original))

    hooks_install.install()

    data = json.loads(settings.read_text())
    assert data["permissions"] == original["permissions"]
    commands = [h["command"] for entry in data["hooks"]["SessionStart"] for h in entry["hooks"]]
    assert commands[0] == "echo hi" and len(commands) == 2
    assert list(settings.parent.glob("settings.json.bak-token-tracker-*"))


def test_installing_twice_changes_nothing(settings):
    hooks_install.install()
    before = settings.read_text()
    assert hooks_install.install() == []
    assert settings.read_text() == before


def test_an_older_install_by_script_path_counts_as_installed(settings):
    legacy = {"hooks": {event: [{"hooks": [{"type": "command", "command": "python3 /old/backend/hooks/record_account.py"}]}]
                        for event in hooks_install.EVENTS}}
    settings.write_text(json.dumps(legacy))
    assert hooks_install.install() == []


def test_dry_run_writes_nothing(settings):
    assert hooks_install.install(dry_run=True) == ["SessionStart", "UserPromptSubmit"]
    assert not settings.exists()


def test_uninstall_removes_only_ours(settings):
    settings.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}}))
    hooks_install.install()

    assert hooks_install.uninstall() == ["SessionStart", "UserPromptSubmit"]

    data = json.loads(settings.read_text())
    assert data["hooks"] == {"SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}


def test_uninstall_drops_an_empty_hooks_key(settings):
    hooks_install.install()
    hooks_install.uninstall()
    assert "hooks" not in json.loads(settings.read_text())


def test_unreadable_settings_are_refused_not_overwritten(settings):
    settings.write_text("{ not json")
    with pytest.raises(hooks_install.SettingsError):
        hooks_install.install()
    assert settings.read_text() == "{ not json"
