import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from token_tracker import usage_snapshot as snapshot

KYIV = ZoneInfo("Europe/Kyiv")
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=KYIV)


def test_reset_time_is_read_in_the_zone_the_cli_names():
    # 4:49pm in Kyiv on Oct 14 is 13:49 UTC (UTC+3 in October)
    assert snapshot.parse_resets_at("resets Oct 14 at 4:49pm (Europe/Kiev)", NOW) == "2026-10-14T13:49:00Z"
    assert snapshot.parse_resets_at("resets Oct 14 at 4:49pm (America/New_York)", NOW) == "2026-10-14T20:49:00Z"


def test_without_a_zone_the_local_one_is_assumed():
    tokyo_now = datetime(2026, 10, 13, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    assert snapshot.parse_resets_at("resets Oct 14 at 4:49pm", tokyo_now) == "2026-10-14T07:49:00Z"
    assert snapshot.parse_resets_at("resets Oct 14 at 4:49pm (Mars/Base)", NOW) == "2026-10-14T13:49:00Z"


def test_midnight_and_noon_use_the_twelve_hour_clock_correctly():
    assert snapshot.parse_resets_at("resets Oct 14 at 12am (Europe/Kyiv)", NOW) == "2026-10-13T21:00:00Z"
    assert snapshot.parse_resets_at("resets Oct 14 at 12pm (Europe/Kyiv)", NOW) == "2026-10-14T09:00:00Z"


def test_no_reset_text_means_no_reset_time():
    assert snapshot.parse_resets_at(None, NOW) is None
    assert snapshot.parse_resets_at("soon", NOW) is None


def test_usage_output_lines_become_snapshots():
    output = (
        "Current session: 11% used · resets Oct 14 at 4:49pm (Europe/Kiev)\n"
        "Current week (all models): 25% used\n"
        "Some unrelated line\n"
    )
    parsed = snapshot.parse_usage_output(output, NOW)
    assert [(s["scope"], s["pct_used"]) for s in parsed] == [("Current session", 11.0), ("Current week (all models)", 25.0)]
    assert parsed[0]["resets_at"] == "2026-10-14T13:49:00Z"
    assert parsed[1]["resets_at"] is None


def test_only_one_background_snapshot_runs_at_a_time(monkeypatch, tmp_path):
    release, started = threading.Event(), threading.Event()

    def slow_run(db_path):
        started.set()
        release.wait(5)

    monkeypatch.setattr(snapshot, "run", slow_run)
    assert snapshot.start_in_background(tmp_path / "x.db") == "started"
    assert started.wait(5)
    assert snapshot.start_in_background(tmp_path / "x.db") == "running"  # a burst of refreshes starts no second one
    release.set()
    for _ in range(100):  # the worker frees the lock a moment after run() returns
        if snapshot.start_in_background(tmp_path / "x.db") == "started":
            break
        threading.Event().wait(0.05)
    else:
        raise AssertionError("the lock was never released")


def test_a_failed_background_snapshot_is_remembered_and_frees_the_lock(monkeypatch, tmp_path):
    done = threading.Event()

    def failing_run(db_path):
        try:
            raise TimeoutError("took too long")
        finally:
            done.set()

    monkeypatch.setattr(snapshot, "run", failing_run)
    assert snapshot.start_in_background(tmp_path / "x.db") == "started"
    assert done.wait(5)
    for _ in range(100):
        if "took too long" in (snapshot.last_background_error() or ""):
            break
        threading.Event().wait(0.05)
    assert "TimeoutError: took too long" == snapshot.last_background_error()

    monkeypatch.setattr(snapshot, "run", lambda db_path: None)
    for _ in range(100):
        if snapshot.start_in_background(tmp_path / "x.db") == "started":
            break
        threading.Event().wait(0.05)
    for _ in range(100):  # a later success clears the remembered failure
        if snapshot.last_background_error() is None:
            break
        threading.Event().wait(0.05)
    assert snapshot.last_background_error() is None


def test_the_cli_is_given_time_for_a_slow_usage_report():
    assert snapshot.USAGE_TIMEOUT_SECONDS >= 120
