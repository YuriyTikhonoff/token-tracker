import json
import sqlite3

from helpers import assistant, user, write_lines

from token_tracker import accounts, ingest, queries


def test_resolver_follows_the_account_active_at_each_timestamp(db):
    db.execute("INSERT INTO accounts VALUES ('me', 'Me', NULL, NULL, 1)")
    db.executemany("INSERT INTO session_accounts VALUES (?, ?, ?)", [
        ("s", "2026-01-01T10:00:00.000Z", "me"),
        ("s", "2026-01-01T12:00:00.000Z", "guest"),
    ])
    resolver = accounts.AccountResolver(db)

    assert resolver.resolve("s", "2026-01-01T11:59:59.999Z") == "me"
    assert resolver.resolve("s", "2026-01-01T12:00:00.000Z") == "guest"
    assert resolver.resolve("s", "2026-01-02T00:00:00.000Z") == "guest"
    # a row stamped just before the first event still belongs to that first account
    assert resolver.resolve("s", "2026-01-01T09:59:00.000Z") == "me"
    # a session no hook ever saw belongs to the default account
    assert resolver.resolve("other", "2026-01-01T11:00:00.000Z") == "me"


def test_first_account_becomes_default_and_labels_are_never_overwritten(db, login):
    login("a1", "ann@x.c", "Ann")
    accounts.sync_events(db, db_events_path(db))
    assert db.execute("SELECT account_uuid, label, is_default FROM accounts").fetchall() == [("a1", "Ann", 1)]

    db.execute("UPDATE accounts SET label = 'Anna' WHERE account_uuid = 'a1'")
    login("a1", "ann@new.c", "Ann Changed")
    accounts.sync_events(db, db_events_path(db))
    assert db.execute("SELECT label, email FROM accounts").fetchall() == [("Anna", "ann@new.c")]


def db_events_path(db):
    # a path that does not exist: no hook events yet
    return accounts.EVENTS_PATH.with_name("none.jsonl")


def test_hook_events_register_accounts_and_partial_lines_wait_for_the_next_run(db, login, tmp_path):
    login("me", "me@x.c", "Me")
    events = tmp_path / "events.jsonl"
    line = {"ts": "2026-01-01T10:00:00.000Z", "session_id": "s", "account_uuid": "guest", "email": "g@x.c", "display_name": "Gus"}
    events.write_text(json.dumps(line) + "\n" + '{"ts": "2026-01-01T11:')  # second line is half written

    accounts.sync_events(db, events)

    assert db.execute("SELECT COUNT(*) FROM session_accounts").fetchone()[0] == 1
    assert {row[0] for row in db.execute("SELECT account_uuid FROM accounts")} == {"me", "guest"}
    assert db.execute("SELECT account_uuid FROM accounts WHERE is_default = 1").fetchone() == ("me",)

    accounts.sync_events(db, events)  # nothing new: no duplicates
    assert db.execute("SELECT COUNT(*) FROM session_accounts").fetchone()[0] == 1


def test_a_login_in_the_middle_of_a_session_splits_its_rows_between_accounts(tmp_path, login):
    login("me", "me@x.c", "Me")
    # the default events file is where ingest looks; each test gets a clean claude dir
    accounts.EVENTS_PATH.write_text("\n".join(json.dumps(e) for e in [
        {"ts": "2026-10-13T09:00:00.000Z", "session_id": "s1", "account_uuid": "me"},
        {"ts": "2026-10-13T10:00:00.000Z", "session_id": "s1", "account_uuid": "guest", "display_name": "Gus"},
    ]) + "\n")
    projects = tmp_path / "projects"
    write_lines(projects / "-p" / "s1.jsonl", [
        user("u1", "p1", None, "mine", "2026-10-13T09:00:00.000Z"),
        assistant("a1", "u1", "2026-10-13T09:30:00.000Z", inp=1, out=0, cc=0, cr=0),
        user("u2", "p2", "a1", "theirs", "2026-10-13T10:05:00.000Z"),
        assistant("a2", "u2", "2026-10-13T10:06:00.000Z", inp=100, out=0, cc=0, cr=0),
    ])
    db_path = tmp_path / "t.db"

    ingest.run(projects, db_path)

    connection = sqlite3.connect(db_path)
    assert dict(connection.execute("SELECT assistant_uuid, account_uuid FROM usage")) == {"a1": "me", "a2": "guest"}
    assert dict(connection.execute("SELECT prompt_id, account_uuid FROM prompts")) == {"p1": "me", "p2": "guest"}
    pricing = {"_default": {"input": 1, "output": 0, "cache_creation": 0, "cache_read": 0}}
    assert queries.get_totals(connection, pricing, account="guest")["input_tokens"] == 100
    assert queries.get_totals(connection, pricing, account="me")["input_tokens"] == 1
    assert queries.get_totals(connection, pricing)["input_tokens"] == 101
    connection.close()


def test_rows_without_an_account_are_backfilled_to_the_default(db, login):
    login("me")
    db.execute("INSERT INTO usage (assistant_uuid, session_id, model, timestamp) VALUES ('a', 's', 'm', 't')")
    accounts.sync_events(db, db_events_path(db))
    assert db.execute("SELECT account_uuid FROM usage").fetchone() == ("me",)
