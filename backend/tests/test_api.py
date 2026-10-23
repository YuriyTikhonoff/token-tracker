import json

import pytest
from fastapi.testclient import TestClient
from helpers import assistant, user, write_lines

from token_tracker import accounts, ingest
from token_tracker import db as db_module
from token_tracker.main import app
from token_tracker.routes import data as data_route


@pytest.fixture
def client(tmp_path, monkeypatch):
    # two accounts' worth of history, built through the real ingest path
    accounts.EVENTS_PATH.write_text("\n".join(json.dumps(e) for e in [
        {"ts": "2026-10-13T09:00:00.000Z", "session_id": "s1", "account_uuid": "me", "email": "me@x.c", "display_name": "Me"},
        {"ts": "2026-10-13T09:00:00.000Z", "session_id": "s2", "account_uuid": "guest", "email": "g@x.c", "display_name": "Gus"},
    ]) + "\n")
    (accounts.CLAUDE_JSON_PATH).write_text(json.dumps({"oauthAccount": {"accountUuid": "me", "displayName": "Me"}}))
    projects = tmp_path / "projects"
    for session, tokens in (("s1", 1000), ("s2", 300)):
        write_lines(projects / f"-{session}" / f"{session}.jsonl", [
            user(f"u-{session}", f"p-{session}", None, "hi", "2026-10-13T09:00:00.000Z", session),
            assistant(f"a-{session}", f"u-{session}", "2026-10-13T09:00:05.000Z", model="claude-opus-5-5",
                      inp=tokens, out=0, cc=0, cr=0, session=session),
        ])
    db_path = tmp_path / "api.db"
    ingest.run(projects, db_path)

    import sqlite3

    def override():
        connection = sqlite3.connect(db_path, check_same_thread=False)
        try:
            yield connection
        finally:
            connection.close()

    app.dependency_overrides[db_module.get_db] = override
    monkeypatch.setattr(data_route, "DEFAULT_DB_PATH", db_path)
    data_route.invalidate_data_cache()
    yield TestClient(app)
    app.dependency_overrides.clear()
    data_route.invalidate_data_cache()


def test_data_combines_accounts_and_reports_each(client):
    payload = client.get("/api/data").json()
    assert payload["totals"]["input_tokens"] == 1300
    assert payload["selected_account"] is None
    assert payload["timezone"] == "UTC"
    assert payload["unknown_models"] == []


def test_data_can_be_filtered_to_one_account_without_mixing_the_cache(client):
    mine = client.get("/api/data", params={"account": "me"}).json()
    theirs = client.get("/api/data", params={"account": "guest"}).json()
    everyone = client.get("/api/data", params={"account": "all"}).json()
    assert (mine["totals"]["input_tokens"], theirs["totals"]["input_tokens"], everyone["totals"]["input_tokens"]) == (1000, 300, 1300)
    assert mine["selected_account"] == "me"


def test_an_account_can_be_renamed_and_the_data_follows(client):
    assert client.patch("/api/accounts/guest", json={"label": "  Anna  "}).json() == {"ok": True}
    assert "Anna" in [a["label"] for a in client.get("/api/sections/accounts").json()]


def test_rename_validation(client):
    assert client.patch("/api/accounts/nobody", json={"label": "x"}).status_code == 404
    assert client.patch("/api/accounts/me", json={"label": "   "}).status_code == 422


def test_making_another_account_the_default_moves_the_flag(client):
    client.patch("/api/accounts/guest", json={"is_default": True})
    defaults = [a["label"] for a in client.get("/api/sections/accounts").json() if a["is_default"]]
    assert defaults == ["Gus"]


def test_root_answers_even_without_a_bundled_dashboard(client):
    assert client.get("/").status_code == 200


def test_a_first_run_without_a_database_answers_with_zeros_not_an_error():
    from token_tracker import config

    for leftover in config.db_path().parent.glob("token_tracker.db*"):
        leftover.unlink()
    data_route.invalidate_data_cache()
    with TestClient(app) as fresh:  # entering the context runs the startup hook
        response = fresh.get("/api/data")
        fresh_accounts = fresh.get("/api/sections/accounts").json()
    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"]["total_tokens"] == 0
    assert all(week["total_tokens"] == 0 for week in payload["weekly_usage"])
    assert fresh_accounts == []


def test_limits_is_a_small_payload_with_the_accounts_but_no_heavy_parts(client):
    payload = client.get("/api/limits").json()
    assert set(payload) == {"usage_snapshots", "today", "week", "accounts", "selected_account", "timezone"}
    assert {a["label"] for a in payload["accounts"]} == {"Me", "Gus"}
    assert all(set(a) == {"account_uuid", "label", "is_default"} for a in payload["accounts"])
    assert payload["selected_account"] is None
    assert payload["timezone"] == "UTC"


def test_overview_has_the_top_of_the_dashboard_and_none_of_the_tables(client):
    payload = client.get("/api/overview").json()
    assert set(payload) == {
        "usage_snapshots", "current_session_stats", "daily_usage", "accounts", "selected_account", "timezone",
    }
    assert len(payload["daily_usage"]) == 10
    assert {a["label"] for a in payload["accounts"]} == {"Me", "Gus"}
    assert client.get("/api/overview", params={"account": "me"}).json()["selected_account"] == "me"


def test_data_leaves_out_the_collapsed_sections(client):
    payload = client.get("/api/data").json()
    for key in ("by_project", "by_session", "by_prompt", "prompt_log", "prompt_log_total", "codex_daily_usage",
                "accounts", "daily_usage", "usage_snapshots"):
        assert key not in payload


def test_the_accounts_section_lists_everyone_with_their_totals_whatever_is_selected(client):
    accounts = client.get("/api/sections/accounts").json()
    by_label = {a["label"]: a for a in accounts}
    assert by_label["Me"]["all"]["input_tokens"] == 1000 and by_label["Me"]["is_default"] is True
    assert by_label["Gus"]["all"]["input_tokens"] == 300
    assert client.get("/api/sections/accounts", params={"account": "me"}).json() == accounts


def test_each_collapsed_section_has_its_own_endpoint_that_follows_the_account(client):
    assert [row["project"] for row in client.get("/api/sections/by-project").json()] != []
    sessions = client.get("/api/sections/by-session", params={"account": "guest"}).json()
    assert [row["session_id"] for row in sessions] == ["s2"]
    prompts = client.get("/api/sections/by-prompt", params={"account": "me"}).json()
    assert [row["prompt_id"] for row in prompts] == ["p-s1"]
    log = client.get("/api/sections/prompt-log").json()
    assert {row["prompt_id"] for row in log} == {"p-s1", "p-s2"}
    assert [row["prompt_id"] for row in client.get("/api/sections/prompt-log", params={"account": "all"}).json()] == [
        row["prompt_id"] for row in log
    ]
    codex = client.get("/api/sections/codex").json()
    assert set(codex) == {"codex_daily_usage", "codex_rate_limits"}
    assert len(codex["codex_daily_usage"]) == 10


def test_limits_can_be_filtered_to_one_account(client):
    payload = client.get("/api/limits", params={"account": "me"}).json()
    assert payload["selected_account"] == "me"
    assert len(payload["accounts"]) == 2  # the switcher still lists everyone
    assert client.get("/api/limits", params={"account": "all"}).json()["selected_account"] is None
