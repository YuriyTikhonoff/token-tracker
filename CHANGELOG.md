# Changelog

## Unreleased

- Costs and token counts were about twice too high: Claude Code writes one response as several
  transcript entries, and each was counted. Each API response is now counted once (by message id
  and request id). An upgraded database keeps one row of each group of copies.
- Cache writes to the 1-hour cache, where Claude Code writes most of them, are priced at their own
  rate (2x input) instead of the 5-minute one.
- Prices updated to Anthropic's list of 2026-11-17: Fable 5.2 and the Mythos models added, Opus
  4.5, 4.1 and 4, Sonnet 4.5 and 4 added, cache reads of Sonnet 5.5 and Fable 5 corrected.
- Subagent transcripts are read.
- Audits of the cost calculation are recorded in the database (`token-tracker audit-costs`); the
  dashboard and `doctor` say when the last one is more than two weeks old.
- The top of the dashboard is one sticky toolbar: account switcher, notices, the time of the last
  refresh, a ⋯ menu with the Accounts table, and Refresh. The refresh status is a toast.

- The account Claude Code is logged into now is marked in the account switcher, and its weekly
  limit comes first while the other accounts' are shown in smaller, fainter text; all of it follows
  a switch of login.

## 0.1.0 (2026-10-14)

First public release.

- Dashboard of Claude Code tokens and estimated cost by day, week, month, project, session and
  prompt, read from Claude Code's own transcripts.
- Subscription limits (5-hour and weekly) with a projection of when they run out.
- Several Claude accounts on one machine: hooks record who is logged in, rows are tagged by
  account, the dashboard has an account switcher and an Accounts overview.
- Codex CLI usage and rate limits in the same dashboard.
- `token-tracker` command: `serve`, `ingest`, `snapshot`, `report`, `codex`, `install-hooks`,
  `uninstall-hooks`, `doctor`.
- Settings through environment variables or `~/.token-tracker/config.toml`: data directory,
  database, Claude and Codex directories, time zone. Prices can be overridden per model.
- Versioned database migrations; an older database is upgraded in place.
- Optional macOS desktop widget (Hammerspoon), background agent (launchd) and shell shortcuts.
