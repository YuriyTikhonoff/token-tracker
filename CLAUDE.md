# CLAUDE.md

Token Tracker: Claude Code (and Codex) usage statistics read from local logs. A FastAPI backend
(`backend/token_tracker`, SQLite) serves a React dashboard (`frontend/`). See `README.md` for what
it does and how to run it.

This directory is mirrored to its own public repository, so keep it self-contained: no paths or
names from the monorepo around it, no personal data in code, docs or tests.

## Rules specific to this project

- The shared rules in the monorepo's root `CLAUDE.md` apply, with these exceptions:
  - The UI uses literal colors, not tokens, and is dark only. It predates the token rule and was
    kept as is.
  - The backend has no Alembic. The schema is numbered migrations in `backend/token_tracker/schema.py`
    (`PRAGMA user_version`); append a migration, never edit an existing one.
- Backend: `cd backend && ../.venv/bin/pytest` and `ruff check .`. Tests run on synthetic data in
  temporary directories, never on `~/.claude` or a real database.
- Frontend: `npm run typecheck`, `npm run lint`, `npm run build` in `frontend/`. Use the npm that
  ships with Node 22 (npm 10) when touching `package-lock.json`; a lockfile written by npm 11 breaks
  `npm ci` there.
- Port 8765 is the backend, 5177 the Vite dev server. Run dev servers in your own terminal.
- Do not touch a real `token_tracker.db` or `~/.claude/settings.json` from a test or experiment;
  use `TOKEN_TRACKER_HOME` and `CLAUDE_CONFIG_DIR` pointed at a temporary directory.
- Screenshots in `docs/` must come from made-up data.

## Publishing

The public repository is a `git subtree` of this directory:

```bash
git subtree push --prefix=token-tracker token-tracker main
```

Run it from the monorepo root after the tests pass, and check the remote tree hash matches
`git rev-parse HEAD:token-tracker`.
