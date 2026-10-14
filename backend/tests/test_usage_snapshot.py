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
