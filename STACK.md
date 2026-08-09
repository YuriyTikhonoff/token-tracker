# Token Tracker — Stack & Structure

_Generated: 2026-07-10. Updated: 2026-07-10 (Phase 1 of the FastAPI +
Vite/React + Tauri migration — repo restructured into `backend/`; stack
below still reflects the current, pre-FastAPI backend)._

## What it is

A local-only tool that parses Claude Code's own transcript logs
(`~/.claude/projects/**/*.jsonl`), stores token usage in SQLite, and
reports/visualizes it (CLI report + local web dashboard). Also polls
`claude -p "/usage"` periodically to track subscription session/weekly
limit consumption and project time-to-exhaustion.

A migration is in progress to a FastAPI + Vite/React (TS) + Tauri stack —
see [PLAN.md](PLAN.md) for the phased plan. The repo has been restructured
into `backend/`/`frontend/`/`desktop/` in anticipation of that (frontend/
desktop don't exist yet); everything described below still runs exactly as
before, just from `backend/app/` instead of the repo root.

## Stack

- **Language**: Python 3 (3.14.6 locally), currently standard library only
  at runtime — `backend/pyproject.toml` now declares `fastapi`/`uvicorn` as
  dependencies for the upcoming migration, but nothing imports them yet.
- **Storage**: SQLite (`backend/app/token_tracker.db`, gitignored, ~17MB
  locally). Accessed via the stdlib `sqlite3` module, raw SQL (no ORM —
  staying that way deliberately, see PLAN.md).
- **Web dashboard**: `http.server.ThreadingHTTPServer` +
  `BaseHTTPRequestHandler` (stdlib only) serving one self-contained HTML
  page with inline CSS and vanilla JS (no build step, no frontend
  framework, no external requests/CDNs). Being replaced by FastAPI +
  React per PLAN.md.
- **External process integration**: shells out to the `claude` CLI
  (`claude -p "/usage"`) via `subprocess` to snapshot subscription limits.
- **Automation**:
  - `backend/watch.sh` — foreground bash loop, re-runs ingest (and
    periodically usage snapshot) on an interval.
  - `backend/launchd/com.token-tracker.ingest.plist` — macOS launchd agent
    to run ingest in the background every 5 minutes. Not currently
    installed (verified via `launchctl list`).
  - `backend/shell-hook/capture.sh` — optional zsh `preexec` hook that
    appends typed terminal commands to `backend/commands.log` (not yet
    joined with usage data).
- **Distribution/UX**: `backend/aliases.sh` — shell aliases (`tt-refresh`,
  `tt-report`, `tt-dashboard`, `tt-watch`, `tt-open`) sourced from `.zshrc`.

## Project structure

```
token-tracker/
├── backend/
│   ├── app/
│   │   ├── ingest.py            # JSONL transcripts -> SQLite (incremental, byte-offset tracked)
│   │   ├── queries.py            # Shared SQL query/aggregation layer (used by report.py + dashboard.py)
│   │   ├── report.py              # CLI text report (totals/by-project/by-session/top-prompts)
│   │   ├── dashboard.py           # Local web server + embedded HTML/CSS/JS dashboard
│   │   ├── usage_snapshot.py      # Polls `claude -p "/usage"`, parses %, stores subscription-limit snapshots
│   │   ├── pricing.json            # $/1M-token rates per model, used for cost estimates
│   │   └── token_tracker.db        # SQLite DB (gitignored, created on first ingest run)
│   ├── pyproject.toml              # fastapi/uvicorn deps declared for the upcoming FastAPI backend
│   ├── watch.sh                     # Foreground refresh loop (ingest + periodic usage snapshot)
│   ├── aliases.sh                   # Shell shortcuts (tt-refresh, tt-report, tt-dashboard, tt-watch, tt-open)
│   ├── launchd/
│   │   ├── com.token-tracker.ingest.plist   # macOS background agent (ingest every 5 min)
│   │   └── README.md                          # install/uninstall instructions
│   ├── shell-hook/
│   │   └── capture.sh              # optional zsh preexec hook -> commands.log (manual command capture)
│   └── logs/                        # launchd stdout/stderr logs (gitignored)
├── README.md                 # usage docs
├── PLAN.md                    # design/roadmap notes, including the stack migration plan
└── STACK.md                    # this file
```

`frontend/` (Vite + React + TS) and `desktop/` (Tauri) will be added
alongside `backend/` as later migration phases land — see PLAN.md.

## Data flow

```
~/.claude/projects/**/*.jsonl (Claude Code transcripts)
        │  backend/app/ingest.py (incremental, offset-tracked per file)
        ▼
backend/app/token_tracker.db  ◄── usage_snapshot.py (claude -p "/usage", periodic)
        │
        │  queries.py (shared aggregation/query functions)
        ▼
report.py (CLI)        dashboard.py (HTTP server, /api/data + /api/refresh)
                              │
                              ▼
                     single-page HTML/JS UI (polls /api/data every 30s,
                     manual refresh button triggers ingest + usage_snapshot)
```

## Database schema (`token_tracker.db`)

| Table              | Purpose                                                                 | Rows (local) |
| ------------------ | ------------------------------------------------------------------------ | ------------ |
| `file_state`        | Byte offset per transcript file, for incremental ingest                  | 364          |
| `sessions`           | Session id → project, first/last seen timestamps                         | 364          |
| `prompts`             | User prompt id → session, preview text, timestamp                        | 2,516        |
| `uuid_prompt_map`     | Maps every transcript entry uuid to its resolved prompt id                | 54,943       |
| `usage`                | Per-assistant-turn token usage (input/output/cache write/cache read)      | 33,348       |
| `usage_snapshots`      | Subscription limit snapshots (scope, % used, resets_at) from `/usage`      | 612          |

## Code size

- `dashboard.py` — 541 lines (largest file; embeds the full frontend as a
  Python string template)
- `queries.py` — 414 lines
- `ingest.py` — 267 lines
- `usage_snapshot.py` — 135 lines
- `report.py` — 104 lines
- **Total**: ~1,461 lines of Python

## Notable design points

- No frontend build tooling at all — the dashboard's HTML/CSS/JS lives
  inline inside `dashboard.py` as a raw string (`PAGE_TEMPLATE`), served
  as-is. No React/Vue, no bundler, no npm.
- No web framework — the HTTP server is hand-rolled on top of
  `http.server` from the stdlib.
- No ORM — all SQL is written directly against `sqlite3`.
- Ingest is idempotent/incremental: re-running is always safe since each
  transcript file's read offset is persisted, and inserts use
  `ON CONFLICT ... DO NOTHING`/`DO UPDATE`.
- `queries.py` centralizes all read/aggregation logic so `report.py` (CLI)
  and `dashboard.py` (web) stay in sync rather than duplicating query
  logic.
- Not currently a git repo with a remote — local-only (`git remote -v`
  returns nothing).
