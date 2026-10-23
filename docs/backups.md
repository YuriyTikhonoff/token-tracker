# Backups

Status: **proposal**. Nothing described here is implemented yet.

How Token Tracker protects its database, and how it checks on every run that the protection is
current.

## What is worth backing up

| Data | Where | If lost |
| --- | --- | --- |
| The database | `~/.token-tracker/token_tracker.db` (an older setup keeps it in `backend/app/`; `token-tracker doctor` says which) | Usage is rebuilt by `ingest` from the Claude Code transcripts, as long as those still exist. Limit snapshots, account names and the default-account choice are lost for good |
| Account events | `~/.claude/token-tracker-account-events.jsonl` (or `$CLAUDE_CONFIG_DIR`) | Which account used which session can no longer be told. Rows fall back to the default account |
| Codex data | in the same database | Rebuilt from `~/.codex` while it exists |

Not backed up: `config.toml` (a few lines, easy to recreate), the dashboard build, and anything under
`~/.claude/projects`, which belongs to Claude Code.

## Behaviour

```bash
token-tracker backup            # create a backup now
token-tracker backup --status   # when was the last one, is it fresh
token-tracker backup --verify   # re-check the newest one
token-tracker restore [FILE]    # restore the newest (or the named) backup
```

`token-tracker run` checks the age of the newest backup before it ingests. If the newest verified
backup is older than `max_age` (24 hours by default) or there is none, it makes a new one first,
then goes on. If the backup fails it prints a warning and goes on: a backup problem never stops the
dashboard from starting.

The check reads the newest **manifest**, not file times. A backup with a missing file or a failed
check does not count as a backup.

## Where they go

```
~/Backups/token-tracker/                # TOKEN_TRACKER_BACKUP_DIR or backup_dir in config.toml
  token-tracker-<UTC timestamp>.sqlite.gz
  token-tracker-<UTC timestamp>.events.tar.gz
  token-tracker-<UTC timestamp>.json    # manifest: source, size, sha256, checks passed
```

Keeping this folder inside something that is already copied off the machine (Time Machine, iCloud
Drive) is what gives an off-machine copy. Token Tracker uploads nothing.

## How a backup is made

- The database is copied with SQLite's online backup API, so it is safe while the dashboard runs
  and in WAL mode. A plain `cp` is not: it can miss committed writes.
- The copy is checked with `PRAGMA integrity_check` before it is compressed. A failed check deletes
  the copy and reports an error; nothing is pruned.
- Retention: the newest of each of the last 7 days and of the last 4 weeks, everything else
  removed, and only after a new verified backup exists. Change with `backup_keep_daily` and
  `backup_keep_weekly` in `config.toml`.
- A lock file in the backup folder stops two runs from backing up at once.

## Restore

`token-tracker restore` refuses while the dashboard answers on its port (override with `--force`),
first takes a safety copy of the current database (`...-pre-restore`), then replaces the database
and removes any stale `-wal` and `-shm` files. After a restore, run `token-tracker ingest`: it
picks up anything newer than the backup from the transcripts.

Restore drill, to try once on a scratch location without touching the real data:

```bash
TOKEN_TRACKER_HOME=/tmp/tt-restore-test token-tracker restore
TOKEN_TRACKER_HOME=/tmp/tt-restore-test token-tracker report --top 3
```

## Settings

| Setting | Variable | `config.toml` key | Default |
| --- | --- | --- | --- |
| Backup folder | `TOKEN_TRACKER_BACKUP_DIR` | `backup_dir` | `~/Backups/token-tracker` |
| Maximum age | `TOKEN_TRACKER_BACKUP_MAX_AGE` | `backup_max_age` | `24h` |
| Daily copies kept | | `backup_keep_daily` | `7` |
| Weekly copies kept | | `backup_keep_weekly` | `4` |

## Moving an older database

If `token-tracker doctor` reports the database at its old location (`backend/app/`), stop the
server, run `token-tracker backup`, copy `token_tracker.db` together with its `-wal` and `-shm`
files to `~/.token-tracker/`, start again, and delete the old files only after the dashboard shows
the data. Do not move the files while the server is running.
