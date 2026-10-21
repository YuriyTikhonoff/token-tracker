# Token Tracker — shell shortcuts.
#
# Install (edits your shell startup — your call):
#   echo "source $PWD/backend/aliases.sh" >> ~/.zshrc     # run from the repo root
# then open a new terminal (or `source ~/.zshrc`).
#
# Uninstall: remove that line from ~/.zshrc.
#
# Commands (work from any directory):
#   tt-refresh    pull latest Claude Code session data into the local DB
#   tt-report     print the text report in this terminal
#   tt-dashboard  start the local web dashboard (http://127.0.0.1:8765)
#   tt-watch      foreground loop: re-run tt-refresh every 60s until Ctrl+C
#   tt-open       refresh, then start the dashboard (the two-step you run most often)

# Resolved from this file's own location, so the repo can live anywhere.
# bash sets BASH_SOURCE; in zsh, $0 is the sourced file.
_token_tracker_source="${BASH_SOURCE[0]:-$0}"
_TOKEN_TRACKER_DIR="$(cd "$(dirname "$_token_tracker_source")" && pwd)"

# Runs a token_tracker module from this checkout, with the checkout's own
# virtualenv when there is one.
_tt() {
  # The README puts the virtualenv one level up (token-tracker/.venv); an older
  # layout kept it in backend/.venv.
  local python="$_TOKEN_TRACKER_DIR/../.venv/bin/python"
  [ -x "$python" ] || python="$_TOKEN_TRACKER_DIR/.venv/bin/python"
  [ -x "$python" ] || python="$(command -v python3)"
  PYTHONPATH="$_TOKEN_TRACKER_DIR${PYTHONPATH:+:$PYTHONPATH}" "$python" "$@"
}

tt-refresh() {
  _tt -m token_tracker.ingest "$@"
}

tt-report() {
  _tt -m token_tracker.report "$@"
}

tt-dashboard() {
  _tt -m uvicorn token_tracker.main:app --host 127.0.0.1 --port 8765 "$@"
}

tt-watch() {
  "$_TOKEN_TRACKER_DIR/watch.sh" "$@"
}

tt-open() {
  tt-refresh && tt-dashboard
}
