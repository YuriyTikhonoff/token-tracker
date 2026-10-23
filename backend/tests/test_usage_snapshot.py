import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from token_tracker import usage_snapshot as snapshot


@pytest.fixture(autouse=True)
def fresh_background_state():
    snapshot._last_ok_started = None
    snapshot._last_error = None
    yield
    snapshot._last_ok_started = None
    snapshot._last_error = None


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
        if snapshot.start_in_background(tmp_path / "x.db", force=True) == "started":
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
        if snapshot.start_in_background(tmp_path / "x.db", force=True) == "started":
            break
        threading.Event().wait(0.05)
    for _ in range(100):  # a later success clears the remembered failure
        if snapshot.last_background_error() is None:
            break
        threading.Event().wait(0.05)
    assert snapshot.last_background_error() is None


def test_the_cli_is_given_time_for_a_slow_usage_report():
    assert snapshot.USAGE_TIMEOUT_SECONDS >= 120


def _wait_until_idle():
    for _ in range(100):
        if snapshot._background.acquire(blocking=False):
            snapshot._background.release()
            return
        threading.Event().wait(0.05)
    raise AssertionError("the background snapshot never finished")


def test_a_reading_is_not_repeated_within_the_interval_unless_forced(monkeypatch, tmp_path):
    monkeypatch.setattr(snapshot, "run", lambda db_path: None)
    assert snapshot.start_in_background(tmp_path / "x.db") == "started"
    _wait_until_idle()
    assert snapshot.start_in_background(tmp_path / "x.db") == "recent"
    assert snapshot.start_in_background(tmp_path / "x.db", force=True) == "started"
    _wait_until_idle()
    # once the interval has passed a plain request starts one again
    snapshot._last_ok_started -= snapshot.MIN_BACKGROUND_INTERVAL_SECONDS + 1
    assert snapshot.start_in_background(tmp_path / "x.db") == "started"


def test_a_failed_reading_does_not_hold_back_the_next_one(monkeypatch, tmp_path):
    def failing(db_path):
        raise TimeoutError("slow")

    monkeypatch.setattr(snapshot, "run", failing)
    assert snapshot.start_in_background(tmp_path / "x.db") == "started"
    _wait_until_idle()
    monkeypatch.setattr(snapshot, "run", lambda db_path: None)
    assert snapshot.start_in_background(tmp_path / "x.db") == "started"


def test_a_fresh_reading_is_needed_when_there_is_none_or_its_window_closed(tmp_path):
    from datetime import UTC, timedelta

    from token_tracker import queries, schema

    db_path = tmp_path / "n.db"
    connection = queries.connect(db_path)
    schema.migrate(connection)
    assert snapshot.needs_fresh_reading(db_path) is True  # nothing recorded yet

    def add(resets_at):
        connection.execute(
            "INSERT INTO usage_snapshots (captured_at, scope, pct_used, resets_at) VALUES (?,?,?,?)",
            (datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "Current session", 10.0, resets_at),
        )
        connection.commit()

    stamp = lambda hours: (datetime.now(UTC) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    add(stamp(-1))
    assert snapshot.needs_fresh_reading(db_path) is True  # its window has closed
    add(stamp(2))
    assert snapshot.needs_fresh_reading(db_path) is False
    connection.close()


def test_a_reading_is_stamped_when_the_slow_report_comes_back(monkeypatch, tmp_path):
    import time

    from token_tracker import queries

    started = time.time()

    def slow_report():
        time.sleep(1.2)
        return "Current session: 11% used · resets Oct 14 at 4:49pm (Europe/Kiev)\n"

    monkeypatch.setattr(snapshot, "capture_usage_output", slow_report)
    snapshot.run(tmp_path / "s.db")
    connection = queries.connect(tmp_path / "s.db")
    (captured_at,) = connection.execute("SELECT captured_at FROM usage_snapshots").fetchone()
    connection.close()
    stamped = datetime.strptime(captured_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).timestamp()
    # stored to the whole second, so compare with the second the report was asked for: stamped when
    # it was asked for, this would equal int(started); stamped when it came back, it is a second later
    assert stamped >= int(started) + 1
