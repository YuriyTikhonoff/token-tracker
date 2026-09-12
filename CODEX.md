# Codex CLI tracking

Token Tracker also tracks usage from the [Codex CLI](https://github.com/openai/codex),
alongside its original Claude Code tracking — same database, same dashboard,
web UI only (the Hammerspoon floating widget stays Claude-only for now).

## What it tracks

- **Token usage** — input / cached input / output / reasoning-output tokens
  per turn, aggregated into a daily chart (last 10 days).
- **Rate limits** — the account's 5h and weekly usage percentages, with the
  same reset/exhaustion projection the Claude "Subscription limits" widget
  does (pace bar, "reset in ~Xh", "exhaust in ~Xh", margin).

No cost/$ estimate is shown for Codex: the rollout logs identify models by
internal codename (e.g. `gpt-5.6-sol`), not their public names, so there's no
reliable price list to attach — only token counts are estimated to be
accurate here.

## Where the data comes from

Codex CLI writes one append-only JSONL rollout file per thread to
`~/.codex/sessions/<year>/<month>/<day>/rollout-*.jsonl`. Two line shapes
carry what's needed, both written once per turn:

- `{"type": "token_usage_record", "payload": {"usage": {...}, ...}}` — this
  turn's actual billed usage (input/cached_input/cache_write_input/output/
  reasoning_output/total tokens).
- `{"type": "event_msg", "payload": {"type": "token_count", ...,
  "rate_limits": {"primary": {...}, "secondary": {...}}}}` — the account's
  5h (`primary`) and weekly (`secondary`) rate-limit percentages, each with
  `used_percent`, `window_minutes`, and a `resets_at` unix timestamp.

Unlike Claude (where subscription-limit tracking has to shell out to
`claude -p "/usage"` and regex-parse its text output — see
`backend/app/usage_snapshot.py`), Codex logs its rate-limit snapshot
passively on every turn. No extra CLI call is needed; `codex_ingest.py`
only ever reads the rollout files already on disk.

## Backend

- `backend/app/codex_ingest.py` — parses the rollout JSONL files
  incrementally (byte-offset tracked per file, same pattern as
  `ingest.py`), upserting into two new tables:
  - `codex_usage` (`response_id` primary key, thread/session id, timestamp,
    the five token-count columns) — one row per turn.
  - `codex_rate_limits` (autoincrement id, captured_at, primary/secondary
    pct + window_minutes + resets_at, plan_type) — one row per `token_count`
    event, append-only like `usage_snapshots`.
- `queries.py` gained two functions, following the same shape as their
  Claude equivalents:
  - `get_codex_daily_usage()` — zero-filled per-day token totals, mirrors
    `get_daily_usage()`.
  - `get_codex_rate_limits_trend()` — latest pct/projection per scope
    ("Codex 5h limit", "Codex weekly limit"), reusing the existing
    `_extrapolate_pct_used`/`_trim_to_current_cycle` trend machinery
    verbatim (same reset-boundary-jitter handling Claude's weekly scope
    needs), rather than reimplementing it.
- `GET /api/data` now returns `codex_daily_usage` and `codex_rate_limits`
  alongside the existing Claude fields.
- `POST /api/refresh` now also runs `codex_ingest.run()` (wrapped in its own
  try/except, like the existing `ingest`/`usage_snapshot` calls, so one
  failing doesn't block the others).

## Frontend

Two new components, deliberate copies of the Claude widgets they sit next
to in `App.tsx`, with their own color palette so the two sources read as
visually distinct at a glance:

- `CodexLimitsWidget` / `CodexLimitRow` — copy of `LimitsWidget`/`LimitRow`.
  Reuses the shared severity/projection colors (status colors are meant to
  stay consistent app-wide) but swaps the "on pace" fill from Claude's blue
  to a Codex-orange (`#d95926`), and computes the pace bar from
  `window_minutes` directly (Codex gives this precisely; Claude's version
  has to guess "weekly vs session" from the scope's English text).
- `CodexDailyTokensChart` — copy of `DailyTokensChart`, with a 4-color
  palette for Codex's own token categories (Input, Cached input, Output,
  Reasoning) chosen and validated with the `dataviz` skill's
  `validate_palette.js` (CVD-safe adjacent pairs, contrast against the
  dark card surface): `#d95926` orange, `#9085e9` violet, `#c98500` gold,
  `#199e70` teal.

`format.ts` gained `codexPacePercent()` (window-minutes-based pace, see
above) and `projectionLines()` was generalized to accept either
`UsageSnapshotTrend` or `CodexRateLimitTrend` (it only ever reads
`resets_at`/`hours_to_limit`), so the projection-line logic isn't
duplicated between the two widgets.

## Backfilling / running it

Nothing extra to install — `codex_ingest.py` runs automatically as part of
`POST /api/refresh` (the dashboard's Refresh button), same as `ingest.py`
and `usage_snapshot.py`. To run it standalone:

```bash
python3 backend/app/codex_ingest.py
```

Safe to re-run any time; each rollout file's read offset is persisted in
`codex_file_state`, so only newly-appended lines are processed.

## Known limitations

- No cost estimate (see "What it tracks" above — no reliable per-model
  pricing for Codex's internal model codenames).
- The Hammerspoon floating widget (`widgets/hammerspoon/`, `backend/app/
  widget.html`) intentionally does **not** show Codex data yet — this
  pass was scoped to the web dashboard only.
- `codex_usage` sums every turn found in the rollout logs, including
  subagent/guardian-review calls (e.g. Codex's built-in safety-review
  passes) — these are real billed tokens on the account, so they're
  included rather than filtered out, matching how Claude's `usage` table
  also counts subagent/sidechain turns.
