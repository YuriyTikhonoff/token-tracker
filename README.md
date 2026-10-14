# Token Tracker

A local-only tool that parses Claude Code's own transcript logs
(`~/.claude/projects/**/*.jsonl`) into SQLite and reports/visualizes token
usage per project/session/prompt, with a rough cost estimate. Also polls
`claude -p "/usage"` periodically to track subscription session/weekly
limit consumption.

Stack: FastAPI backend (`backend/`) + Vite/React/TS frontend (`frontend/`),
both reading/writing the same SQLite database. See [STACK.md](STACK.md) for
file-by-file structure and [PLAN.md](PLAN.md) for design notes/roadmap.

Also tracks [Codex CLI](https://github.com/openai/codex) usage (tokens +
5h/weekly rate limits) in the same dashboard, parsed from
`~/.codex/sessions/**/*.jsonl` — see [CODEX.md](CODEX.md) for how that side
works.

A glanceable desktop view of the limits + daily-tokens chart lives in
[`widgets/hammerspoon/`](widgets/hammerspoon/README.md): an always-on-top
floating panel (via Hammerspoon) that loads the backend's `/widget` page
and floats over other windows. The dashboard's "Widget preview" section
renders that same page so you can tune its look/size before copying the
values into the Hammerspoon config.

## How it works

```
~/.claude/projects/**/*.jsonl (Claude Code transcripts)
        │  backend/token_tracker/ingest.py (incremental, byte-offset tracked per file)
        ▼
backend/token_tracker/token_tracker.db  ◄── usage_snapshot.py (claude -p "/usage", periodic)
        │
        │  queries.py (shared aggregation layer)
        ▼
backend/token_tracker/main.py (FastAPI: /api/data, /api/refresh)
        │
        ▼
frontend/ (React) — polls /api/data, Refresh button triggers ingest + usage_snapshot
```

- `ingest.py` reads new transcript lines since each file's last saved byte
  offset, resolves prompt/session/token-usage rows, and upserts them into
  `token_tracker.db` — safe to re-run any time.
- `usage_snapshot.py` shells out to `claude -p "/usage"` to record
  subscription session/weekly limit percentages over time.
- `queries.py` centralizes all read/aggregation SQL so the API and the CLI
  report stay in sync.
- The FastAPI app (`main.py` + `routes/`) serves that data as JSON and
  exposes `/api/refresh` to trigger a fresh ingest + usage snapshot on
  demand (the frontend's Refresh button).
- The React frontend renders the dashboard: token/cost charts (daily,
  monthly), subscription limits widget, by-project/by-session/top-prompts
  tables, and a prompt log.
- Both the API and the CLI report read the same `token_tracker.db` fresh on
  every request — no caching.

## Configuration

Nothing depends on where the repository lives. Each setting is read from an
environment variable, then from `~/.token-tracker/config.toml`, then falls
back to a default. Restart the backend after changing them.

| What | Environment | `config.toml` key | Default |
| --- | --- | --- | --- |
| Data directory | `TOKEN_TRACKER_HOME` | n/a | `~/.token-tracker` |
| Database | `TOKEN_TRACKER_DB` | `db` | `<data directory>/token_tracker.db` |
| Claude Code directory | `CLAUDE_CONFIG_DIR` | `claude_dir` | `~/.claude` |
| Codex directory | `CODEX_HOME` | `codex_dir` | `~/.codex` |
| Time zone | `TOKEN_TRACKER_TZ` | `timezone` | `TZ`, then the system zone, else UTC |

The time zone decides where "today", "this week" and "this month" start and
which clock the dashboard shows; use an IANA name such as `Europe/Kyiv`.

Prices live in `backend/token_tracker/pricing.json`. Put your own entries in
`<data directory>/pricing.json`; they replace the shipped entry for the same
model and add new models.

If you ran an older version, your database may still be at
`backend/token_tracker/token_tracker.db`. It keeps being used (with a notice) until you
move it, together with its `-wal` and `-shm` files, to the data directory.

If you use a custom `CLAUDE_CONFIG_DIR`, set the same value in the backend's
environment (or `claude_dir` in `config.toml`): the transcripts, the logged-in
account (`<dir>/.claude.json`) and the account events are all read from there.

## Several accounts on one machine

Claude Code transcripts do not say which account wrote them, so a hook records
the logged-in account (from `~/.claude.json`). `ingest.py` reads those events
and tags every prompt and usage row with the account that was active in its
session at that moment. A person who `/login`s on your machine shows up as a
separate account with no extra setup once the hooks are installed.

Install the hooks once:

```bash
token-tracker install-hooks      # add --dry-run to see what would change
```

It adds two entries to `~/.claude/settings.json` (or `$CLAUDE_CONFIG_DIR/settings.json`),
keeps everything else in the file and leaves a timestamped backup next to it.
`token-tracker uninstall-hooks` removes them again. Both run the same
script, `token_tracker/hook.py`:

- `SessionStart`: always records the account, so a new or resumed session
  (also after `/clear`) is tied to whoever is logged in.
- `UserPromptSubmit`: records only when the account differs from the last one
  seen for the session, so a `/login` in the middle of a conversation is
  caught at the next prompt. State lives in
  `~/.claude/token-tracker-account-state.json` (entries expire after 7 days).

- Usage from before the hook existed belongs to the **default** account: the
  one logged in the first time `ingest.py` ran after this change. Change it
  with "make default" in the dashboard's Accounts section if that was the
  wrong one.
- Accounts get a label from their Claude display name; click it in the
  Accounts section to rename (e.g. "Anna").
- The dashboard always shows an account switcher and an
  Accounts section (today / month / all-time per account, combined total,
  cost share). The switcher filters Claude usage, limits and the tables; Codex
  numbers are not per account. `report.py --account <uuid>` does the same for
  the CLI.
- `/usage` limits are snapshotted for whoever is logged in at that moment, so
  an account's limit widget only moves while that account is active.
- A session that is not covered by a hook event (hook not installed, or the
  hook failed) is attributed to the default account.

## Requirements

- Python 3.11 or newer
- Node.js 22 (20.19 or newer also works), to build the dashboard
- Claude Code, with its transcripts in `~/.claude`

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install -e backend
(cd frontend && npm ci && npm run build:package)   # builds the dashboard (needs Node.js)
.venv/bin/token-tracker serve                      # http://127.0.0.1:8765
.venv/bin/token-tracker install-hooks              # optional: tell accounts apart
```

`token-tracker` commands:

| Command | What it does |
| --- | --- |
| `serve [--host H] [--port P]` | the dashboard and API (127.0.0.1:8765 by default; the API has no login, so keep it on localhost) |
| `ingest` | read new Claude Code transcripts into the database |
| `snapshot` | record subscription limits (needs the `claude` CLI) |
| `report [--top N] [--account ID]` | text report |
| `codex` | read new Codex CLI sessions |
| `install-hooks` / `uninstall-hooks` | add or remove the account-tracking hooks |
| `doctor` | check the setup and say what is missing |

## Development

Two terminals, from the repo root:

```bash
# terminal 1: backend with auto-reload
cd backend
python3 -m venv .venv && .venv/bin/pip install -e .   # first time only
.venv/bin/uvicorn token_tracker.main:app --reload --port 8765

# terminal 2: frontend dev server
cd frontend
npm install   # first time only
npm run dev   # http://localhost:5177
```

Open the frontend URL Vite prints. It talks to the backend at
`http://127.0.0.1:8765` (see `frontend/.env` / `VITE_API_BASE_URL` if you
need to point it elsewhere — the backend's CORS allows any localhost port).

### CLI-only usage (no server)

```bash
# Parse/refresh the local database (safe to re-run; incremental)
token-tracker ingest

# Print totals, by-project, by-session, and top-prompt reports
token-tracker report --top 15
```

Re-run `token-tracker ingest` any time (cron, a loop, or manually) to pick up
new sessions/turns.

### Shortcuts (optional)

If you work from a checkout rather than an installed package, source
`backend/aliases.sh` once to get short commands usable from any directory
(they use the checkout's own `.venv` when it exists):

```bash
echo "source $PWD/backend/aliases.sh" >> ~/.zshrc   # run from the repo root
```

Then open a new terminal (or `source ~/.zshrc`) and use:

| Command        | What it does                                          |
| -------------- | ------------------------------------------------------ |
| `tt-refresh`   | pull latest Claude Code session data into the local DB |
| `tt-report`    | print the text report                                  |
| `tt-dashboard` | start the local web dashboard (http://127.0.0.1:8765)  |
| `tt-watch`     | foreground loop: refresh every 60s until Ctrl+C         |
| `tt-open`      | refresh, then start the dashboard — the one you'll use most |

To uninstall, remove that line from `~/.zshrc`.

### Keeping it fresh automatically (optional)

Two ways to auto-refresh instead of running the ingest by hand:

- `backend/watch.sh [interval_seconds]` — foreground loop in a terminal you
  keep open (default every 60s). Nothing left running once you close it.
- `backend/launchd/` — a macOS background agent that runs the ingest every
  5 minutes even after you close the terminal. Not installed automatically;
  see [backend/launchd/README.md](backend/launchd/README.md) for
  install/uninstall steps.

## Files

- `backend/token_tracker/main.py` — FastAPI app (CORS, router registration).
- `backend/token_tracker/routes/data.py` — `GET /api/data`, assembles the full
  dashboard payload via `queries.py`.
- `backend/token_tracker/routes/refresh.py` — `POST /api/refresh`, runs `ingest.py` +
  `usage_snapshot.py` on demand.
- `backend/token_tracker/ingest.py` — parses transcripts into `token_tracker.db`
  (SQLite, created on first run in `backend/token_tracker/`, gitignored).
- `backend/token_tracker/queries.py` — shared read/aggregation layer used by both
  `report.py` and the API routes.
- `backend/token_tracker/report.py` — CLI text report (totals/by-project/by-session/
  top-prompts).
- `backend/token_tracker/usage_snapshot.py` — polls `claude -p "/usage"` for
  subscription session/weekly limit tracking.
- `backend/token_tracker/codex_ingest.py` — parses Codex CLI's own rollout logs
  (`~/.codex/sessions/**/*.jsonl`) for token usage and rate limits — see
  [CODEX.md](CODEX.md).
- `backend/token_tracker/db.py` / `schemas.py` — SQLite connection helper and
  Pydantic response models for the API.
- `backend/token_tracker/pricing.json` — $/1M-token rates used for cost estimates,
  keyed by model name, with the date and source in `_meta`. Costs are
  estimates: the cache-write rate is the 5-minute one, and a model with no
  entry is counted at `_default` and listed in a notice on the dashboard.
  Token counts are exact. Add or override models in
  `<data directory>/pricing.json` rather than editing this file.
- `frontend/src/App.tsx` — top-level layout wiring the dashboard components
  together.
- `frontend/src/components/` — charts (`DailyTokensChart`,
  `MonthlyTokensChart`), `LimitsWidget` (subscription limits), tables
  (`ByProjectTable`, `TopSessionsTable`, `TopPromptsTable`,
  `PromptLogTable`), `CostBreakdown`, `RefreshButton`, and their Codex
  counterparts `CodexDailyTokensChart`/`CodexLimitsWidget` (own color
  palette — see [CODEX.md](CODEX.md)).
- `frontend/src/hooks/useDashboardData.ts` — React Query hook polling
  `/api/data`.
- `frontend/src/api/` — typed fetch client + response types for the
  backend API.

## Manual terminal command capture (optional, zsh only)

Not installed automatically — it edits your shell startup file, which is
your call to make. To enable:

```bash
echo "source $PWD/backend/shell-hook/capture.sh" >> ~/.zshrc   # run from the repo root
```

Then open a new terminal (or `source ~/.zshrc`). Every interactively typed
command gets appended to `backend/commands.log` as
`timestamp<TAB>cwd<TAB>command` — command text only, no output captured. To
uninstall, remove that line from `~/.zshrc`.

This log isn't wired into `ingest.py`/`report.py`/the API yet — it's just
being captured for now. Joining it with token usage by timestamp is a
possible v2 if it turns out to be useful.

## Known limitations

- Some usage rows can't be traced to a specific prompt (e.g. subagent/
  sidechain turns without a resolvable parent chain) — these are grouped
  per-session as "no prompt id" in the prompt-level report rather than
  dropped.
- Manual terminal commands are captured to `commands.log` but not yet
  cross-referenced with token usage in any report.
- No auto-refresh — reload the page after `ingest.py` runs, or use the
  Refresh button (see "Keeping it fresh automatically" above to automate
  the ingest side).
- No pruning/retention policy on `token_tracker.db` — it grows indefinitely.
  Not a problem yet, but revisit if it becomes one.
</content>

## License

[MIT](LICENSE)
