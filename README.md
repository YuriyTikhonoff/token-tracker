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
        │  backend/app/ingest.py (incremental, byte-offset tracked per file)
        ▼
backend/app/token_tracker.db  ◄── usage_snapshot.py (claude -p "/usage", periodic)
        │
        │  queries.py (shared aggregation layer)
        ▼
backend/app/main.py (FastAPI: /api/data, /api/refresh)
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

## Several accounts on one machine

Claude Code transcripts do not say which account wrote them, so a hook records
the logged-in account (from `~/.claude.json`). `ingest.py` reads those events
and tags every prompt and usage row with the account that was active in its
session at that moment. A person who `/login`s on your machine shows up as a
separate account with no extra setup once the hooks are installed.

One script, `backend/hooks/record_account.py`, is registered for two events in
`~/.claude/settings.json`:

- `SessionStart`: always records the account, so a new or resumed session
  (also after `/clear`) is tied to whoever is logged in.
- `UserPromptSubmit`: records only when the account differs from the last one
  seen for the session, so a `/login` in the middle of a conversation is
  caught at the next prompt. State lives in
  `~/.claude/token-tracker-account-state.json` (entries expire after 7 days).

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "python3 <repo>/token-tracker/backend/hooks/record_account.py" }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "python3 <repo>/token-tracker/backend/hooks/record_account.py" }] }
    ]
  }
}
```

- Usage from before the hook existed belongs to the **default** account: the
  one logged in the first time `ingest.py` ran after this change. Change it
  with "make default" in the dashboard's Accounts section if that was the
  wrong one.
- Accounts get a label from their Claude display name; click it in the
  Accounts section to rename (e.g. "Anna").
- With two or more accounts the dashboard shows an account switcher and an
  Accounts section (today / month / all-time per account, combined total,
  cost share). The switcher filters Claude usage, limits and the tables; Codex
  numbers are not per account. `report.py --account <uuid>` does the same for
  the CLI.
- `/usage` limits are snapshotted for whoever is logged in at that moment, so
  an account's limit widget only moves while that account is active.
- A session that is not covered by a hook event (hook not installed, or the
  hook failed) is attributed to the default account.

## Running it

Two terminals, from the repo root:

```bash
# terminal 1 — backend
cd backend/app
source ../.venv/bin/activate   # first time: python3 -m venv ../.venv && pip install -e ..
uvicorn main:app --port 8765

# terminal 2 — frontend
cd frontend
npm install   # first time only
npm run dev   # http://localhost:5173 (or next free port)
```

Open the frontend URL Vite prints. It talks to the backend at
`http://127.0.0.1:8765` (see `frontend/.env` / `VITE_API_BASE_URL` if you
need to point it elsewhere — the backend's CORS allows any localhost port).

### CLI-only usage (no servers)

```bash
# Parse/refresh the local database (safe to re-run; incremental)
python3 backend/app/ingest.py

# Print totals, by-project, by-session, and top-prompt reports
python3 backend/app/report.py --top 15
```

Re-run `ingest.py` any time (cron, a loop, or manually) to pick up new
sessions/turns.

### Shortcuts (optional)

Instead of typing `python3 /full/path/to/backend/app/ingest.py` every time,
source `backend/aliases.sh` once to get short commands usable from any
directory:

```bash
echo 'source /Users/yuritykhonov/Documents/code/personal/token-tracker/backend/aliases.sh' >> ~/.zshrc
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

Two ways to auto-refresh instead of running `ingest.py` by hand:

- `backend/watch.sh [interval_seconds]` — foreground loop in a terminal you
  keep open (default every 60s). Nothing left running once you close it.
- `backend/launchd/` — a macOS background agent that runs `ingest.py` every
  5 minutes even after you close the terminal. Not installed automatically;
  see [backend/launchd/README.md](backend/launchd/README.md) for
  install/uninstall steps.

## Files

- `backend/app/main.py` — FastAPI app (CORS, router registration).
- `backend/app/routes/data.py` — `GET /api/data`, assembles the full
  dashboard payload via `queries.py`.
- `backend/app/routes/refresh.py` — `POST /api/refresh`, runs `ingest.py` +
  `usage_snapshot.py` on demand.
- `backend/app/ingest.py` — parses transcripts into `token_tracker.db`
  (SQLite, created on first run in `backend/app/`, gitignored).
- `backend/app/queries.py` — shared read/aggregation layer used by both
  `report.py` and the API routes.
- `backend/app/report.py` — CLI text report (totals/by-project/by-session/
  top-prompts).
- `backend/app/dashboard.py` — original stdlib-only (no FastAPI/React)
  dashboard; kept as a zero-dependency fallback (see below).
- `backend/app/usage_snapshot.py` — polls `claude -p "/usage"` for
  subscription session/weekly limit tracking.
- `backend/app/codex_ingest.py` — parses Codex CLI's own rollout logs
  (`~/.codex/sessions/**/*.jsonl`) for token usage and rate limits — see
  [CODEX.md](CODEX.md).
- `backend/app/db.py` / `schemas.py` — SQLite connection helper and
  Pydantic response models for the API.
- `backend/app/pricing.json` — $/1M-token rates used for cost estimates,
  keyed by model name. **These rates are placeholders — verify against
  current published Anthropic pricing before trusting the cost numbers;
  only the token counts are guaranteed accurate.** Edit this file when
  pricing changes or a new model appears (the report uses `_default` for
  any unlisted model).
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

## Fallback: stdlib-only dashboard (no npm/venv)

If you just want a quick check without installing anything beyond the
Python standard library:

```bash
python3 backend/app/dashboard.py      # http://127.0.0.1:8765
```

This is the original dashboard implementation (hand-rolled
`http.server` + inline HTML/CSS/JS) and reads the same `token_tracker.db`.
It has no auto-refresh — reload the page after `ingest.py` runs, or use the
in-app Refresh button.

## Manual terminal command capture (optional, zsh only)

Not installed automatically — it edits your shell startup file, which is
your call to make. To enable:

```bash
echo 'source /Users/yuritykhonov/Documents/code/personal/token-tracker/backend/shell-hook/capture.sh' >> ~/.zshrc
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
