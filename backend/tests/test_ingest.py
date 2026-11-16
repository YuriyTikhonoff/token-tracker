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


def test_a_response_written_as_several_entries_is_counted_once(tmp_path, login):
    # Claude Code writes thinking, text and each tool call of one response as
    # separate entries with their own uuid and the same message id and usage.
    login("acct-1")
    projects = tmp_path / "projects"
    copies = [
        assistant(uuid, "u1", "2026-10-13T09:00:05.000Z", inp=10, out=20, cc=100, cr=1000,
                  message_id="msg_1", cc_1h=80)
        for uuid in ("a1", "a2", "a3")
    ]
    write_lines(projects / "-p" / "s1.jsonl", [
        user("u1", "p1", None, "hi", "2026-10-13T09:00:00.000Z"),
        *copies,
        assistant("b1", "a3", "2026-10-13T09:00:09.000Z", inp=1, out=2, cc=0, cr=1100, message_id="msg_2"),
    ])
    db_path = tmp_path / "t.db"
    ingest.run(projects, db_path)

    assert _rows(db_path, "SELECT message_key, input_tokens, output_tokens, cache_creation_tokens, "
                          "cache_creation_1h_tokens, cache_read_tokens FROM usage ORDER BY message_key") == [
        ("msg_1:req-msg_1", 10, 20, 100, 80, 1000),
        ("msg_2:req-msg_2", 1, 2, 0, 0, 1100),
    ]


def test_an_early_copy_with_zero_usage_gives_way_to_the_full_one(tmp_path, login):
    login("acct-1")
    projects = tmp_path / "projects"
    write_lines(projects / "-p" / "s1.jsonl", [
        user("u1", "p1", None, "hi", "2026-10-13T09:00:00.000Z"),
        assistant("a1", "u1", "2026-10-13T09:00:05.000Z", inp=0, out=0, cc=0, cr=0, message_id="msg_1"),
        assistant("a2", "a1", "2026-10-13T09:00:05.000Z", inp=2, out=960, cc=1204, cr=486900, message_id="msg_1"),
    ])
    db_path = tmp_path / "t.db"
    ingest.run(projects, db_path)

    assert _rows(db_path, "SELECT COUNT(*), SUM(output_tokens), SUM(cache_read_tokens) FROM usage") == [(1, 960, 486900)]


def test_subagent_transcripts_are_read_into_their_parent_project(tmp_path, login):
    login("acct-1")
    projects = tmp_path / "projects"
    write_lines(projects / "-p" / "s1.jsonl", [user("u1", "p1", None, "hi", "2026-10-13T09:00:00.000Z")])
    write_lines(projects / "-p" / "s1" / "subagents" / "agent-1.jsonl", [
        assistant("x1", None, "2026-10-13T09:00:07.000Z", inp=5, message_id="msg_sub"),
    ])
    db_path = tmp_path / "t.db"
    ingest.run(projects, db_path)

    assert _rows(db_path, "SELECT u.input_tokens, s.project FROM usage u JOIN sessions s USING (session_id)") == [
        (5, "-p")
    ]


def test_rows_stored_before_response_keys_get_them_and_lose_their_copies(tmp_path, login):
    login("acct-1")
    projects = tmp_path / "projects"
    write_lines(projects / "-p" / "s1.jsonl", [
        user("u1", "p1", None, "hi", "2026-10-13T09:00:00.000Z"),
        assistant("a1", "u1", "2026-10-13T09:00:05.000Z", inp=0, out=0, cc=0, cr=0, message_id="msg_1"),
        assistant("a2", "a1", "2026-10-13T09:00:06.000Z", inp=3, out=9, cc=50, cr=700, message_id="msg_1", cc_1h=50),
    ])
    db_path = tmp_path / "t.db"
    ingest.run(projects, db_path)
    # As a database from before version 3 has them: no keys, no 1-hour split,
    # one row per entry, and the backfill not run yet.
    connection = sqlite3.connect(db_path)
    connection.execute("DELETE FROM usage")
    connection.execute("DELETE FROM app_state")
    for uuid, amounts in (("a1", (0, 0, 0, 0)), ("a2", (3, 9, 50, 700))):
        connection.execute(
            "INSERT INTO usage (assistant_uuid, session_id, model, input_tokens, output_tokens, "
            "cache_creation_tokens, cache_read_tokens, timestamp) VALUES (?, 's1', 'm', ?, ?, ?, ?, '2026-10-13T09:00:05Z')",
            (uuid, *amounts),
        )
    connection.commit()

    assert ingest.backfill_message_keys(connection, projects) == (1, 1)
    assert connection.execute(
        "SELECT assistant_uuid, message_key, output_tokens, cache_creation_1h_tokens FROM usage"
    ).fetchall() == [("a2", "msg_1:req-msg_1", 9, 50)]
    assert ingest.backfill_message_keys(connection, projects) == (0, 0)  # only once
    connection.close()
