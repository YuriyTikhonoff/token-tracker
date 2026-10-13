# Background auto-refresh (launchd, optional)

Not installed automatically — loading a launchd agent starts a persistent
background process, which is your call to make.

`com.token-tracker.ingest.plist` is a template (`__PYTHON3__` and
`__BACKEND_DIR__` are filled in on install) that runs `ingest.py` every 5 minutes (300s) and
once immediately on load, logging to `../logs/ingest.log` /
`../logs/ingest.error.log`.

## Install

Run from the `backend/` directory:

```bash
mkdir -p logs
sed -e "s|__PYTHON3__|$(command -v python3)|" -e "s|__BACKEND_DIR__|$PWD|" \
  launchd/com.token-tracker.ingest.plist > ~/Library/LaunchAgents/com.token-tracker.ingest.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.token-tracker.ingest.plist
```

## Check it's running

```bash
launchctl list | grep token-tracker
tail -f logs/ingest.log
```

## Uninstall

```bash
launchctl bootout gui/$(id -u)/com.token-tracker.ingest
rm ~/Library/LaunchAgents/com.token-tracker.ingest.plist
```

## Alternative: foreground loop

If you don't want a persistent background service, `../watch.sh [interval_seconds]`
does the same re-run-on-a-timer in a terminal you keep open (default every 60s,
Ctrl+C to stop) — no installation, nothing left running after you close the
terminal.
