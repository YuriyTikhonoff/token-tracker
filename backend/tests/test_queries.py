from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from token_tracker import queries


def _usage(db, uuid, ts, model="m", inp=1, out=1, cc=1, cr=1, account=None, session="s"):
    db.execute(
        "INSERT INTO usage (assistant_uuid, session_id, model, input_tokens, output_tokens, "
        "cache_creation_tokens, cache_read_tokens, timestamp, account_uuid) VALUES (?,?,?,?,?,?,?,?,?)",
        (uuid, session, model, inp, out, cc, cr, ts, account),
    )


def _iso(moment):
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def test_cost_uses_the_rate_of_each_model_and_the_default_for_unknown_ones(db, pricing):
    _usage(db, "a", "2026-10-13T09:00:00.000Z", model="m", inp=1_000_000, out=0, cc=0, cr=0)
    _usage(db, "b", "2026-10-13T09:00:00.000Z", model="nope", inp=1_000_000, out=0, cc=0, cr=0)
    totals = queries.get_totals(db, pricing)
    assert totals["cost"] == 1 + 10  # $1/M for "m", $10/M default for "nope"
    assert totals["total_tokens"] == 2_000_000
    assert queries.get_unknown_models(db, pricing) == ["nope"]


def test_account_filter_restricts_every_total(db, pricing):
    _usage(db, "a", "2026-10-13T09:00:00.000Z", inp=10, out=0, cc=0, cr=0, account="me")
    _usage(db, "b", "2026-10-13T09:00:00.000Z", inp=5, out=0, cc=0, cr=0, account="guest")
    assert queries.get_totals(db, pricing)["input_tokens"] == 15
    assert queries.get_totals(db, pricing, account="me")["input_tokens"] == 10
    assert queries.get_totals(db, pricing, account="guest")["input_tokens"] == 5
    assert queries.get_totals(db, pricing, account="nobody")["input_tokens"] == 0


def test_summary_per_account_has_shares_that_add_up(db, pricing):
    db.executemany("INSERT INTO accounts VALUES (?,?,?,?,?)", [("me", "Me", None, None, 1), ("guest", "Guest", None, None, 0)])
    now = _iso(datetime.now(UTC))
    _usage(db, "a", now, inp=3_000_000, out=0, cc=0, cr=0, account="me")
    _usage(db, "b", now, inp=1_000_000, out=0, cc=0, cr=0, account="guest")
    summary = {entry["label"]: entry for entry in queries.get_accounts_summary(db, pricing)}
    assert summary["Me"]["cost_share"] == 0.75
    assert summary["Guest"]["cost_share"] == 0.25
    assert summary["Me"]["today"]["input_tokens"] == 3_000_000
    assert summary["Me"]["is_default"] is True


def test_day_buckets_follow_the_configured_time_zone(db, pricing, monkeypatch):
    zone = ZoneInfo("Pacific/Kiritimati")  # UTC+14, so its "today" starts well before UTC's
    monkeypatch.setattr(queries, "LOCAL_TZ", zone)
    local_noon = datetime.now(zone).replace(hour=12, minute=0, second=0, microsecond=0)
    _usage(db, "a", _iso(local_noon), inp=7, out=0, cc=0, cr=0)

    today = queries.get_daily_usage(db, pricing, days=3)[-1]

    assert today["date"] == local_noon.strftime("%Y-%m-%d")
    assert today["input_tokens"] == 7


def test_chart_buckets_stay_exact_in_a_half_hour_zone_and_sum_rows_of_one_bucket(db, pricing, monkeypatch):
    zone = ZoneInfo("Asia/Kolkata")  # UTC+5:30: local midnight falls on a half hour in UTC
    monkeypatch.setattr(queries, "LOCAL_TZ", zone)
    midnight = datetime.now(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    _usage(db, "late-yesterday", _iso(midnight - timedelta(minutes=1)), inp=1, out=0, cc=0, cr=0)
    _usage(db, "early-today-1", _iso(midnight), inp=10, out=0, cc=0, cr=0)
    _usage(db, "early-today-2", _iso(midnight + timedelta(minutes=14)), inp=100, out=0, cc=0, cr=0)

    yesterday, today = queries.get_daily_usage(db, pricing, days=3)[-2:]

    assert yesterday["input_tokens"] == 1
    assert today["input_tokens"] == 110


def test_today_total_starts_at_local_midnight(db, pricing, monkeypatch):
    zone = ZoneInfo("Pacific/Kiritimati")
    monkeypatch.setattr(queries, "LOCAL_TZ", zone)
    midnight = datetime.now(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    _usage(db, "before", _iso(midnight - timedelta(minutes=1)), inp=100, out=0, cc=0, cr=0)
    _usage(db, "after", _iso(midnight + timedelta(minutes=1)), inp=1, out=0, cc=0, cr=0)
    totals = queries.get_totals_by_period(db, pricing)
    assert totals["today"]["input_tokens"] == 1
    assert totals["all"]["input_tokens"] == 101


def test_by_project_and_session_rank_by_cost(db, pricing):
    db.execute("INSERT INTO sessions VALUES ('s1', 'proj-a', 't', 't')")
    db.execute("INSERT INTO sessions VALUES ('s2', 'proj-b', 't', 't')")
    _usage(db, "a", "2026-10-13T09:00:00.000Z", inp=1_000_000, out=0, cc=0, cr=0, session="s1")
    _usage(db, "b", "2026-10-13T09:00:00.000Z", inp=3_000_000, out=0, cc=0, cr=0, session="s2")
    assert [row["project"] for row in queries.get_by_project(db, pricing)] == ["proj-b", "proj-a"]
    assert [row["session_id"] for row in queries.get_by_session(db, pricing)] == ["s2", "s1"]


def test_account_filter_also_restricts_tables_charts_and_prompts(db, pricing):
    db.executemany("INSERT INTO sessions VALUES (?,?,?,?)", [("s1", "proj-a", "t", "t"), ("s2", "proj-b", "t", "t")])
    db.executemany("INSERT INTO prompts (prompt_id, session_id, preview, timestamp, account_uuid) VALUES (?,?,?,?,?)", [
        ("p1", "s1", "mine", "2026-10-13T09:00:00.000Z", "me"),
        ("p2", "s2", "theirs", "2026-10-13T09:00:00.000Z", "guest"),
    ])
    now = _iso(datetime.now(UTC))
    _usage(db, "a", now, inp=1_000_000, out=0, cc=0, cr=0, account="me", session="s1")
    _usage(db, "b", now, inp=3_000_000, out=0, cc=0, cr=0, account="guest", session="s2")
    db.execute("UPDATE usage SET prompt_id = 'p1' WHERE assistant_uuid = 'a'")
    db.execute("UPDATE usage SET prompt_id = 'p2' WHERE assistant_uuid = 'b'")

    assert [row["project"] for row in queries.get_by_project(db, pricing, account="me")] == ["proj-a"]
    assert [row["session_id"] for row in queries.get_by_session(db, pricing, account="guest")] == ["s2"]
    assert [row["prompt_id"] for row in queries.get_by_prompt(db, pricing, account="me")] == ["p1"]
    assert [row["prompt_id"] for row in queries.get_prompt_log(db, pricing, account="guest")] == ["p2"]
    assert queries.get_daily_usage(db, pricing, days=2, account="me")[-1]["input_tokens"] == 1_000_000
    assert queries.get_weekly_usage(db, pricing, weeks=2, account="guest")[-1]["input_tokens"] == 3_000_000
    assert queries.get_monthly_usage(db, pricing, months=2, account="me")[-1]["input_tokens"] == 1_000_000


def test_limit_snapshots_are_kept_per_account(db):
    for account, pct in (("me", 10.0), ("guest", 90.0)):
        db.execute(
            "INSERT INTO usage_snapshots (captured_at, scope, pct_used, resets_at, account_uuid) VALUES (?,?,?,?,?)",
            ("2026-10-13T09:00:00Z", "Current session", pct, None, account),
        )
    assert [s["captured_pct_used"] for s in queries.get_usage_snapshots_trend(db, account="me")] == [10.0]
    assert [s["captured_pct_used"] for s in queries.get_usage_snapshots_trend(db, account="guest")] == [90.0]
    assert len(queries.get_usage_snapshots_trend(db)) == 1  # everyone: one entry per scope


def test_limit_history_covers_the_current_window_and_drops_flat_runs(db):
    samples = [
        ("2026-10-12T20:00:00Z", 90.0, "2026-10-13T15:00:00Z"),  # previous week
        ("2026-10-13T16:00:00Z", 0.0, "2026-10-20T15:00:00Z"),
        ("2026-10-13T17:00:00Z", 3.0, "2026-10-20T15:00:00Z"),
        ("2026-10-13T18:00:00Z", 3.0, "2026-10-20T15:00:00Z"),
        ("2026-10-13T19:00:00Z", 3.0, "2026-10-20T15:00:00Z"),
        ("2026-10-13T20:00:00Z", 3.0, "2026-10-20T15:00:00Z"),
        ("2026-10-14T09:00:00Z", 5.0, "2026-10-20T15:00:00Z"),
        ("2026-10-14T10:00:00Z", 5.0, "2026-10-20T15:00:00Z"),
    ]
    for captured_at, pct, resets_at in samples:
        db.execute(
            "INSERT INTO usage_snapshots (captured_at, scope, pct_used, resets_at) VALUES (?,?,?,?)",
            (captured_at, "Current week (all models)", pct, resets_at),
        )
    [trend] = queries.get_usage_snapshots_trend(db)
    assert [(point["captured_at"][11:13], point["pct_used"]) for point in trend["history"]] == [
        ("16", 0.0), ("17", 3.0), ("20", 3.0), ("09", 5.0), ("10", 5.0),
    ]


def test_today_and_week_totals_leave_out_older_usage(db, pricing):
    now = datetime.now(UTC)
    _usage(db, "now", _iso(now), model="m", inp=1_000_000, out=0, cc=0, cr=0)
    _usage(db, "old", _iso(now - timedelta(days=8)), model="m", inp=5_000_000, out=0, cc=0, cr=0)
    _usage(db, "other", _iso(now), model="m", inp=2_000_000, out=0, cc=0, cr=0, account="guest")
    totals = queries.get_today_and_week_totals(db, pricing)
    assert totals["today"]["input_tokens"] == 3_000_000  # both accounts, nothing from 8 days ago
    assert totals["week"]["input_tokens"] == 3_000_000
    assert totals["week"]["cost"] == 3  # $1/M for "m"
    only_guest = queries.get_today_and_week_totals(db, pricing, account="guest")
    assert only_guest["today"]["input_tokens"] == 2_000_000


def test_snapshot_trend_can_leave_out_the_history(db):
    for hour, pct in ((16, 0.0), (17, 3.0), (18, 5.0)):
        db.execute(
            "INSERT INTO usage_snapshots (captured_at, scope, pct_used, resets_at) VALUES (?,?,?,?)",
            (f"2026-10-13T{hour}:00:00Z", "Current session", pct, "2026-10-13T21:00:00Z"),
        )
    [full] = queries.get_usage_snapshots_trend(db)
    [light] = queries.get_usage_snapshots_trend(db, with_history=False)
    assert len(full["history"]) == 3
    assert light["history"] == []
    assert {k: v for k, v in light.items() if k != "history"} == {k: v for k, v in full.items() if k != "history"}


def test_account_labels_carry_no_totals(db):
    db.execute("INSERT INTO accounts (account_uuid, label, email, is_default) VALUES ('me', 'Me', 'me@x.c', 1)")
    db.execute("INSERT INTO accounts (account_uuid, label, email, is_default) VALUES ('g', 'Gus', NULL, 0)")
    assert queries.get_account_labels(db) == [
        {"account_uuid": "me", "label": "Me", "is_default": True},
        {"account_uuid": "g", "label": "Gus", "is_default": False},
    ]
