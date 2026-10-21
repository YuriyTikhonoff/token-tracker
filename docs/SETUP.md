# Setting up Token Tracker on another computer

[Українська](SETUP.uk.md)

Everything below runs on the machine whose Claude Code usage you want to see. Token Tracker reads
the logs on that machine's disk, so it cannot show usage from a different computer.

## 1. Prerequisites

| What | Version | Check | Needed for |
| --- | --- | --- | --- |
| Git | any | `git --version` | cloning |
| Python | 3.11 or newer | `python3 --version` | the backend |
| Node.js + npm | 22 (20.19+ also works) | `node -v` | building the dashboard once |
| Claude Code | any, already used on this machine | `ls ~/.claude/projects` | the data source |
| `claude` CLI on `PATH` | any | `claude --version` | optional: subscription limits |

macOS and Linux work. On Windows use WSL.

## 2. Install

```bash
git clone https://github.com/YuriyTikhonoff/token-tracker.git
cd token-tracker

python3 -m venv .venv
.venv/bin/pip install -e backend

cd frontend
npm ci
npm run build:package      # bundles the dashboard into the Python package
cd ..
```

Node.js is only needed for this build step. Once the bundle exists, the app runs on Python alone.

## 3. Load the data and open the dashboard

```bash
.venv/bin/token-tracker ingest     # reads ~/.claude/projects/**/*.jsonl into a local SQLite file
.venv/bin/token-tracker serve      # then open http://127.0.0.1:8765
```

The first `ingest` can take a while if you have a long history. Later runs read only what is new.
Press **Refresh** in the dashboard, or run `ingest` again, to pick up new activity.

## 4. Run it every day

```bash
.venv/bin/token-tracker run        # reads new activity, then starts the dashboard
```

To start it from any directory, add an alias (adjust the path to your checkout):

```bash
echo "alias token-tracker='$PWD/.venv/bin/token-tracker run'" >> ~/.zshrc
```

Or `source backend/aliases.sh` (see section 6), which gives `tt-open` with the same effect.

## 5. Verify

```bash
.venv/bin/token-tracker doctor
```

Every line should be `[ok]` or `[info]`. A `[FAIL]` line says what is missing, and the command
exits with a non-zero code. Typical fixes:

| Message | Fix |
| --- | --- |
| Claude Code transcripts: none found | Use Claude Code on this machine first, or set `CLAUDE_CONFIG_DIR` if your config is not in `~/.claude` |
| claude CLI on PATH (shown as `FAIL`) | Install Claude Code, or ignore: only the subscription-limit bars need it |
| web dashboard: not bundled in this checkout | Run `npm run build:package` in `frontend/` |
| database ... does not exist yet | Run `token-tracker ingest` |

## 6. Optional

- **Several accounts on one machine:** `.venv/bin/token-tracker install-hooks` (add `--dry-run` to
  preview). It edits `~/.claude/settings.json` and leaves a timestamped backup.
- **Keep it fresh automatically:** `backend/watch.sh` for a terminal loop, or the macOS agent in
  `backend/launchd/`.
- **Short shell commands:** `echo "source $PWD/backend/aliases.sh" >> ~/.zshrc`.
- **Codex CLI usage:** `.venv/bin/token-tracker codex`, see [CODEX.md](../CODEX.md).
- **Always-on-top desktop widget (macOS):** [widgets/hammerspoon](../widgets/hammerspoon/README.md).

## 7. Configuration

Set an environment variable, or put a key in `~/.token-tracker/config.toml`.

| What | Environment | Default |
| --- | --- | --- |
| Data directory | `TOKEN_TRACKER_HOME` | `~/.token-tracker` |
| Claude Code directory | `CLAUDE_CONFIG_DIR` | `~/.claude` |
| Time zone (IANA name, e.g. `Europe/Kyiv`) | `TOKEN_TRACKER_TZ` | system zone |
| Port | `serve --port N` | 8765 |

Restart `serve` after changing them. If you use a custom `CLAUDE_CONFIG_DIR`, export the same value
in every shell that runs `ingest` or `serve`.

## 8. Security notes

- The API has no login. Keep the default `127.0.0.1`; do not pass `--host 0.0.0.0` on a shared or
  public network.
- The database holds token counts, model names, project folder names, timestamps and the first 200
  characters of each prompt. Treat `~/.token-tracker/token_tracker.db` as private.

## 9. Move your existing history to the new machine

Only if you want the old numbers, not just fresh ones. Copy the database file
(`~/.token-tracker/token_tracker.db`) into the new machine's data directory before the first
`ingest`. Without it the new machine starts from whatever is in its own `~/.claude`.

## 10. Update or remove

```bash
git pull
.venv/bin/pip install -e backend
(cd frontend && npm ci && npm run build:package)
```

To remove: `.venv/bin/token-tracker uninstall-hooks` if you installed the hooks, then delete the
checkout and `~/.token-tracker`.

## Troubleshooting

- **Blank page or "dashboard not built":** the bundle is missing, run `npm run build:package`.
- **Port already in use:** `serve --port 8766`.
- **`npm ci` fails:** check `node -v`; use Node 22 (npm 10).
- **Empty dashboard:** run `ingest`, then check `doctor` for the transcripts line.
- **Times look wrong:** set `TOKEN_TRACKER_TZ`.
