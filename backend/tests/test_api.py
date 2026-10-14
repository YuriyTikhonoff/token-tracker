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
    by_label = {a["label"]: a for a in payload["accounts"]}
    assert by_label["Me"]["all"]["input_tokens"] == 1000 and by_label["Me"]["is_default"] is True
    assert by_label["Gus"]["all"]["input_tokens"] == 300
    assert payload["timezone"] == "UTC"
    assert payload["unknown_models"] == []


def test_data_can_be_filtered_to_one_account_without_mixing_the_cache(client):
    mine = client.get("/api/data", params={"account": "me"}).json()
    theirs = client.get("/api/data", params={"account": "guest"}).json()
    everyone = client.get("/api/data", params={"account": "all"}).json()
    assert (mine["totals"]["input_tokens"], theirs["totals"]["input_tokens"], everyone["totals"]["input_tokens"]) == (1000, 300, 1300)
    assert mine["selected_account"] == "me"
    # the summary table always lists everyone, whatever is selected
    assert len(mine["accounts"]) == 2


def test_an_account_can_be_renamed_and_the_data_follows(client):
    assert client.patch("/api/accounts/guest", json={"label": "  Anna  "}).json() == {"ok": True}
    assert "Anna" in [a["label"] for a in client.get("/api/data").json()["accounts"]]


def test_rename_validation(client):
    assert client.patch("/api/accounts/nobody", json={"label": "x"}).status_code == 404
    assert client.patch("/api/accounts/me", json={"label": "   "}).status_code == 422


def test_making_another_account_the_default_moves_the_flag(client):
    client.patch("/api/accounts/guest", json={"is_default": True})
    defaults = [a["label"] for a in client.get("/api/data").json()["accounts"] if a["is_default"]]
    assert defaults == ["Gus"]


def test_root_answers_even_without_a_bundled_dashboard(client):
    assert client.get("/").status_code == 200
