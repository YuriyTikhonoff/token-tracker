# Token Tracker — Plan

Small local app that tracks Claude Code token usage (per prompt/session) and,
optionally, manually-typed terminal commands. Runs entirely on-machine, no
data leaves the laptop.

## Goals

1. Know how many tokens (input/output/cache) each Claude Code prompt/session
   costs, aggregated across all projects.
2. Optionally capture commands typed manually into a terminal (not run by
   Claude), for a fuller activity picture.
3. Cheap to build: reuse data Claude Code already writes; add only what's
   missing.

## What already exists (no new instrumentation needed)

Claude Code writes one JSONL transcript per session to:

```
~/.claude/projects/<project-slug>/<sessionId>.jsonl
```

Relevant line shapes (verified 2026-07-08):

- `type: "assistant"` lines contain `message.usage`:
  ```json
  {
    "input_tokens": 2,
    "cache_creation_input_tokens": 15757,
    "cache_read_input_tokens": 26516,
    "output_tokens": 974,
    "server_tool_use": { "web_search_requests": 0, "web_fetch_requests": 0 }
  }
  ```
- `type: "user"` lines contain `promptId`, `uuid`, `parentUuid`, `timestamp` —
  use these to group assistant usage back to the originating prompt.
- `type: "assistant"` lines also contain `tool_use` blocks (e.g. `Bash` with
  the exact `command` string) — so commands *Claude* runs are already fully
  logged. No live capture needed for that half.
- `<project-slug>` is the cwd path with `/` replaced by `-`.

So step 1 (token accounting per prompt/session) is a pure parse-and-aggregate
job over files that already exist on disk.

## What's missing

Commands **you** type manually into a terminal are not recorded anywhere by
Claude Code — only Claude's own tool calls are. If that data is wanted too,
it needs a separate capture path (see Option B below).

## Architecture

```
token-tracker/
  ingest/
    parse_transcripts.py   # tail/parse ~/.claude/projects/**/*.jsonl -> normalized rows
  store/
    tokens.db              # SQLite: sessions, prompts, usage rows
  shell-hook/
    capture.sh             # optional: zsh preexec/precmd hook -> commands.log
  dashboard/
    app.py or index.html   # small local viewer (CLI table first, web later)
```

### Step 1 — Ingest & store (core deliverable)

- Script walks `~/.claude/projects/*/*.jsonl`, parses each line as JSON,
  skips non-`assistant`/`user` types.
- For each `assistant` line: extract `sessionId` (from filename or session
  context), `uuid`, `parentUuid`, `timestamp`, `usage.*`.
- For each `user` line: extract `promptId`, `uuid`, `timestamp`, first ~80
  chars of the prompt text (for a human-readable label).
- Walk the `parentUuid` chain from each assistant usage row back to the
  nearest `user` message to attribute tokens to a specific prompt.
- Upsert into SQLite tables:
  - `sessions(session_id, project, started_at, last_seen_at)`
  - `prompts(prompt_id, session_id, preview_text, timestamp)`
  - `usage(assistant_uuid, prompt_id, session_id, input_tokens, output_tokens,
    cache_creation_tokens, cache_read_tokens, timestamp)`
- Idempotent: re-running just fills in new lines (track a byte offset or
  last-seen uuid per file so re-parsing is incremental, since transcripts can
  be large — one seen at 1170896 bytes for a single project already).
- Run as a cron-like background loop (e.g. every 60s) or a `watchdog`
  file-watcher on the projects directory.

### Step 2 — Reporting

- CLI report: totals per session, per project, per day; top N most
  expensive prompts.
- Cost estimate: multiply by published per-model token pricing (check
  `claude-api` skill / Anthropic pricing page for current $/MTok rates —
  don't hardcode without a source, prices change).
- Optional: minimal local web dashboard (single static HTML + small
  Python/Node server reading SQLite) — deferred until CLI report is useful.

### Step 3 — Manual terminal command capture (optional, separate concern)

Two options, pick one:

- **Option A — shell hook (recommended, simplest):** zsh `preexec`/`precmd`
  functions appended to `~/.zshrc` (user is on zsh per environment) that
  append `timestamp | cwd | command` to `~/.token-tracker/commands.log`.
  Terminal-agnostic, no VS Code dependency, a few lines of shell script.
- **Option B — VS Code Terminal Shell Integration API:** a small VS Code
  extension using `vscode.window.onDidEndTerminalShellExecution` to capture
  command text + exit code + cwd for terminals VS Code manages. Only needed
  if commands run outside VS Code's integrated terminal don't matter and a
  VS Code-native UI is wanted. More setup (extension scaffolding, packaging)
  for no real capture advantage over Option A.

Decision: start with Option A; revisit Option B only if VS Code-specific
metadata (e.g. which panel/tab) turns out to matter.

## Open questions / decisions needed before building

1. Reporting surface: CLI output only, or a local web dashboard from day one?
2. Should manual command capture be in scope for v1, or defer to a v2 once
   token accounting is solid?
3. Historical backfill: process all existing transcripts across all
   projects, or only start tracking from now on?
4. Retention: keep raw JSONL forever (Claude Code already retains them) —
   does the SQLite store need its own pruning policy?
5. Pricing source for cost estimates: pull from a config file the user edits
   when rates change, rather than hardcoding.

## Suggested build order

1. ✅ `parse_transcripts.py` (shipped as `ingest.py`) — parses transcripts,
   prints/loads aggregated totals.
2. ✅ SQLite persistence + incremental re-parse (byte-offset tracking).
3. ✅ Background loop / file-watcher to keep it live — `watch.sh` (foreground
   loop) and `launchd/` (macOS background agent, opt-in).
4. ✅ Cost estimation via `pricing.json` (rates are placeholders — verify
   before trusting $ figures).
5. ✅ Shell-hook command capture — `shell-hook/capture.sh` (opt-in, zsh only,
   not yet joined with token data).
6. ✅ Minimal dashboard — `dashboard.py`, self-contained local web page.

Remaining / deferred:
- Join `commands.log` with token usage by timestamp (only if useful in
  practice).
- Retention/pruning policy for `token_tracker.db` (not a problem yet at
  ~16MB).

## Non-goals

- No cloud sync or multi-machine aggregation.
- No modification of Claude Code itself or its settings/hooks system.
- No capture of terminal command *output*, only the command line typed
  (keeps scope small, avoids accidentally logging secrets printed to
  stdout).

## Stack migration (in progress): FastAPI + Vite/React + Tauri

The stdlib-only Python app is being evolved into a real widget: a Tauri
desktop app plus a local-browser-tab web view, sharing one Vite+React (TS)
frontend, backed by a FastAPI service. Key decisions:

- Frontend: Vite + React + TS (not Next.js — no SSR/routing need, and
  Tauri wants a static build anyway).
- Desktop: Tauri, not Electron (smaller binary, native webview).
- Backend: FastAPI replacing `dashboard.py`'s `http.server` handler; **no
  ORM** — `queries.py`'s raw-SQL aggregation logic is reused as-is,
  especially the trend-projection functions (`_extrapolate_pct_used`,
  `_trim_to_current_cycle`) which encode real, iterated-on reset-boundary
  detection — these must be ported verbatim, not rewritten.
- "Web" = local browser tab only (the data is laptop-local; no internet
  hosting planned).
- Desktop's first version points at a separately-run backend (like
  today's `tt-dashboard`); a self-contained PyInstaller sidecar is a later
  pass once the rest is proven.

Status:
- ✅ **Phase 1 (repo restructuring)** — done. All backend code moved into
  `backend/` (`backend/app/` for the Python modules + DB, `backend/` for
  automation scripts), paths in `launchd`/`aliases.sh`/`shell-hook`
  updated, `backend/pyproject.toml` added declaring `fastapi`/`uvicorn` as
  future dependencies. No behavior change — `report.py`, `ingest.py`, and
  `dashboard.py` all verified working from the new location.
- ✅ **Phase 2 (FastAPI backend)** — done. `backend/app/main.py` (FastAPI +
  CORS), `db.py` (sync `sqlite3` dependency, no ORM), `schemas.py`
  (Pydantic models mirroring `queries.py`'s dict shapes 1:1), and
  `routes/data.py` + `routes/refresh.py` (direct ports of
  `dashboard.py`'s `_send_json`/`_send_refresh`). Diffed `/api/data` and
  `/api/refresh` against the running `dashboard.py` on live data — only
  differences were expected floating-point drift in time-sensitive
  projection fields. Runs on **port 8765** (not 8000 — that collides with
  Opora's dev backend on this machine).
- ✅ **Phase 3 (Vite+React frontend)** — done. `frontend/` (Vite + React +
  TS + `@tanstack/react-query`), `src/lib/format.ts` (straight port of the
  dashboard's formatting/projection helpers), one component per dashboard
  section (`LimitsWidget`, `CostBreakdown`, the four tables,
  `RefreshButton`). Verified against the live FastAPI backend with a
  headless-Chromium screenshot pass (Playwright) — layout, tab switching,
  and refresh mutation all confirmed working, zero console errors.
  `dashboard.py` still exists as a fallback but is no longer the primary
  UI.
- ⏸️ **Phase 4 (deferred)** — Tauri wrapper (`desktop/`) around the
  frontend build, backend run separately at first. Not needed right now;
  the React app running as a local browser tab against FastAPI (see
  "Running it" below) already covers the actual use case. Revisit if a
  real desktop-widget need shows up later — nothing in Phases 2/3 blocks
  picking this back up.

### Running it now (Phases 2+3, no Tauri)

```bash
# terminal 1 — backend
cd backend/app && source ../.venv/bin/activate && uvicorn main:app --port 8765

# terminal 2 — frontend
cd frontend && npm run dev   # http://localhost:5173
```

`dashboard.py` (the old stdlib-only page) still works too, as a fallback
— see the main README.

Full phase-by-phase plan (file layout, verification steps, what must not
change): see the plan captured during this migration's planning session
— ask Claude to re-derive or re-run it if the standalone plan file isn't
available; the phase summaries above and the "what must NOT change" list
below are the durable record.

### What must NOT change during the migration

- SQLite schema and `ingest.py`'s `ON CONFLICT` upsert semantics.
- `ingest.py`'s incremental byte-offset tracking (`file_state` table).
- `pricing.json` and `cost_for_row`'s `$/1M-token` lookup.
- `queries.py`'s trend-projection semantics verbatim (reset-jitter
  tolerance, weekly-scope window-widening, reset-boundary drop detection,
  session capacity-inference math) — port, don't "clean up."
- `launchd`'s role as the always-on ingest scheduler — no in-process
  APScheduler replacing it (that would only run while the app is open).
- `/api/data`'s JSON field names/nesting (snake_case, unchanged).
