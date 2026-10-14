import json

from token_tracker import cli, hooks_install


def test_help_lists_the_commands(capsys):
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    for command in ("serve", "ingest", "report", "install-hooks", "doctor"):
        assert command in out


def test_install_and_uninstall_hooks_through_the_command(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert cli.main(["install-hooks", "--dry-run"]) == 0
    assert "Would add" in capsys.readouterr().out
    assert not (tmp_path / "settings.json").exists()

    assert cli.main(["install-hooks"]) == 0
    assert set(json.loads((tmp_path / "settings.json").read_text())["hooks"]) == set(hooks_install.EVENTS)
    assert cli.main(["install-hooks"]) == 0
    assert "already installed" in capsys.readouterr().out
    assert cli.main(["uninstall-hooks"]) == 0


def test_options_after_a_passthrough_command_reach_it(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TOKEN_TRACKER_DB", str(tmp_path / "missing.db"))
    # report.main takes --db; a missing database exits with its own message
    try:
        cli.main(["report", "--db", str(tmp_path / "nope.db")])
    except SystemExit as exit_info:
        assert "No database" in str(exit_info)
    else:
        raise AssertionError("report should have refused a missing database")


def test_doctor_runs_and_reports_missing_hooks(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    status = cli.main(["doctor"])
    out = capsys.readouterr().out
    assert status == 1  # no transcripts and no hooks in an empty setup
    assert "account hooks" in out and "install-hooks" in out
