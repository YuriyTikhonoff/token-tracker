import sqlite3

from helpers import assistant, attachment, user, write_lines

from token_tracker import ingest


def _rows(db_path, sql):
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


def test_tokens_are_stored_and_attributed_through_attachment_links(tmp_path, login):
    login("acct-1", "a@x.c", "Ann")
    projects = tmp_path / "projects"
    write_lines(projects / "-proj" / "s1.jsonl", [
        user("u1", "p1", None, "hello <system-reminder>noise</system-reminder>   world", "2026-10-13T09:00:00.000Z"),
        attachment("at1", "u1", "2026-10-13T09:00:01.000Z"),
        assistant("a1", "at1", "2026-10-13T09:00:05.000Z", inp=10, out=20, cc=100, cr=1000),
    ])
    db_path = tmp_path / "t.db"

    result = ingest.run(projects, db_path)

    assert result["new_prompt_count"] == 1
    assert _rows(db_path, "SELECT prompt_id, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens FROM usage") == [
        ("p1", 10, 20, 100, 1000)
    ]
    assert _rows(db_path, "SELECT preview FROM prompts") == [("hello world",)]
    assert _rows(db_path, "SELECT project FROM sessions") == [("-proj",)]


def test_rerunning_only_reads_new_lines(tmp_path, login):
    login("acct-1")
    projects = tmp_path / "projects"
    transcript = projects / "-p" / "s1.jsonl"
    write_lines(transcript, [
        user("u1", "p1", None, "first", "2026-10-13T09:00:00.000Z"),
        assistant("a1", "u1", "2026-10-13T09:00:05.000Z"),
    ])
    db_path = tmp_path / "t.db"
    ingest.run(projects, db_path)

    assert ingest.run(projects, db_path)["new_prompt_count"] == 0
    write_lines(transcript, [assistant("a2", "u1", "2026-10-13T09:01:00.000Z")], mode="a")
    ingest.run(projects, db_path)

    assert _rows(db_path, "SELECT assistant_uuid FROM usage ORDER BY assistant_uuid") == [("a1",), ("a2",)]


def test_duplicate_assistant_uuid_and_broken_lines_are_ignored(tmp_path, login):
    login("acct-1")
    projects = tmp_path / "projects"
    write_lines(projects / "-p" / "s1.jsonl", [
        user("u1", "p1", None, "hi", "2026-10-13T09:00:00.000Z"),
        "this is not json",
        assistant("a1", "u1", "2026-10-13T09:00:05.000Z"),
        assistant("a1", "u1", "2026-10-13T09:00:05.000Z"),
    ])
    db_path = tmp_path / "t.db"
    ingest.run(projects, db_path)
    ingest.run(projects, db_path)  # and again: nothing is counted twice
    # one row, and the tokens of one reply, not two
    assert _rows(db_path, "SELECT COUNT(*), SUM(input_tokens), SUM(output_tokens) FROM usage") == [(1, 1, 2)]


def test_prompt_stays_in_its_session_when_a_tool_result_is_not_a_new_prompt(tmp_path, login):
    login("acct-1")
    projects = tmp_path / "projects"
    tool_result = user("u2", None, "a1", "tool output", "2026-10-13T09:00:10.000Z")
    tool_result["promptId"] = None
    write_lines(projects / "-p" / "s1.jsonl", [
        user("u1", "p1", None, "do it", "2026-10-13T09:00:00.000Z"),
        assistant("a1", "u1", "2026-10-13T09:00:05.000Z"),
        tool_result,
        assistant("a2", "u2", "2026-10-13T09:00:15.000Z"),
    ])
    db_path = tmp_path / "t.db"
    ingest.run(projects, db_path)
    assert _rows(db_path, "SELECT assistant_uuid, prompt_id FROM usage ORDER BY assistant_uuid") == [("a1", "p1"), ("a2", "p1")]


def test_backfill_attributes_rows_whose_prompt_was_unknown_when_they_were_read(tmp_path, login):
    login("acct-1")
    projects = tmp_path / "projects"
    write_lines(projects / "-p" / "s1.jsonl", [
        user("u1", "p1", None, "go", "2026-10-13T09:00:00.000Z"),
        assistant("a1", "u1", "2026-10-13T09:00:05.000Z"),
    ])
    db_path = tmp_path / "t.db"
    ingest.run(projects, db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE usage SET prompt_id = NULL")
    connection.commit()

    assert ingest.backfill_prompt_ids(connection, projects) == 1
    assert connection.execute("SELECT prompt_id FROM usage").fetchall() == [("p1",)]
    connection.close()
