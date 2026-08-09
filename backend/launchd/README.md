# Background auto-refresh (launchd, optional)

Not installed automatically — loading a launchd agent starts a persistent
background process, which is your call to make.

`com.token-tracker.ingest.plist` runs `ingest.py` every 5 minutes (300s) and
once immediately on load, logging to `../logs/ingest.log` /
`../logs/ingest.error.log`.

## Install

Run from the `backend/` directory:

```bash
cp launchd/com.token-tracker.ingest.plist ~/Library/LaunchAgents/
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
