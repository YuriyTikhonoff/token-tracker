#!/usr/bin/env bash
# Foreground loop: re-run ingest.py every N seconds. Ctrl+C to stop.
# For a real background service instead, see launchd/README.md.
set -euo pipefail

INTERVAL="${1:-60}"
USAGE_SNAPSHOT_INTERVAL=600      # seconds; fallback cadence even with no new prompts
USAGE_SNAPSHOT_MIN_INTERVAL=60   # seconds; floor between snapshots so a burst of new prompts doesn't spam the CLI
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/app"

echo "Refreshing token-tracker DB every ${INTERVAL}s from $APP_DIR (Ctrl+C to stop)"
last_usage_snapshot=0
while true; do
  ingest_output="$(python3 "$APP_DIR/ingest.py")"
  echo "$ingest_output"
  new_meaningful_prompts="$(echo "$ingest_output" | awk -F= '/^NEW_MEANINGFUL_PROMPTS=/{print $2}')"

  now="$SECONDS"
  elapsed=$(( now - last_usage_snapshot ))
  if (( elapsed >= USAGE_SNAPSHOT_INTERVAL )) || \
     { [[ "${new_meaningful_prompts:-0}" -gt 0 ]] && (( elapsed >= USAGE_SNAPSHOT_MIN_INTERVAL )); }; then
    python3 "$APP_DIR/usage_snapshot.py" || true
    last_usage_snapshot="$now"
  fi
  sleep "$INTERVAL"
done
