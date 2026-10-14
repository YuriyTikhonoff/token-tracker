# Changelog

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
