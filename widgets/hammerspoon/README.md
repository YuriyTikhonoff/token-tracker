# Token Tracker — floating macOS overlay (Hammerspoon)

An always-on-top panel showing the token-tracker **Subscription limits**
card + a **daily-tokens** bar chart, floating over your other windows and
visible on every Space. This is the "over my windows" version that
Übersicht can't do (Übersicht widgets are pinned to the desktop, behind
all windows).

## What it shows

- **Current session / Current week** rows — the on-pace vs over-pace usage
  bar, `%` used, and the signed margin-to-reset (`+2.5h` green = you'll
  hit the reset before the limit; `-1 day 9.9h` red = you'll cap out that
  long before the window resets).
- **Session window / tokens used / burn rate**.
- **Daily tokens (last 10 days)** — stacked by input / output / cache
  write / cache read, with the 9-day average as a dashed line and each
  day's cost.

The `Fable` weekly scope is hidden (matches the dashboard).

## How it works

```text
FastAPI backend  ──GET /widget──▶  a self-contained HTML page
(routes/widget.py)                 (backend/app/widget.html)
       ▲                                   │ fetch('/api/data') every 60s
       │                                   ▼
       └───────────  Hammerspoon hs.webview (floating, all-Spaces) ◀── you
                     token-tracker/widgets/hammerspoon/token-tracker.lua
```

The page is served **from the backend** so it's same-origin with
`/api/data` (no CORS entry needed). All rendering/polling lives in
`widget.html`; the Lua file is just the window frame — position, level,
Space behavior, hotkeys.

`widget.html`'s formatting/projection logic is a hand-port of
`frontend/src/lib/format.ts`. If you change the pace / exhaustion / margin
maths in one, change it in the other.

## Prerequisites

1. **The backend must be running** on `127.0.0.1:8765`:

   ```bash
   cd token-tracker/backend/app
   source ../.venv/bin/activate
   uvicorn main:app --port 8765
   ```

   (or the `tt-dashboard` alias). If it's down the panel shows
   "backend unreachable" until it's back.

   Keep the DB fresh with the launchd ingest agent (`backend/launchd/`),
   and keep `uvicorn` alive however you like (a login item, a `launchd`
   plist, a `tmux` pane…).

2. **Hammerspoon** — `brew install --cask hammerspoon`, launch it once,
   and grant **Accessibility** when prompted (needed for the global
   hotkeys; the panel itself renders without it).

## Install

Point your Hammerspoon config at the Lua file (it's kept in the repo so
edits stay tracked):

```bash
mkdir -p ~/.hammerspoon
cat >> ~/.hammerspoon/init.lua <<'EOF'
require("hs.ipc")  -- optional: enables the `hs` CLI
dofile("/path/to/token-tracker/widgets/hammerspoon/token-tracker.lua")  -- where you cloned the repo
EOF
```

Then **Reload Config** from the Hammerspoon menu-bar icon (or `⌘⌃⌥R` once
loaded). The panel appears top-right and starts polling.

## Hotkeys (⌘ + ⌥ + ⌃)

| Key | Action |
| --- | --- |
| `T` | toggle show / hide |
| `R` | refresh + reload now |
| `[` | snap to top-left corner |
| `]` | snap to top-right corner |

Drag it anywhere by its title bar. Close it with the red button (`⌘⌥⌃T`
brings it back).

## Tuning

Top of [`token-tracker.lua`](token-tracker.lua):

- **`SCALE`** — the one size knob. `1.0` = native, `0.85` = 85%, etc.
  Shrinks the window **and** the page content together (the window
  frame is `BASE_* × SCALE`, and the page gets `?scale=` and zooms
  itself). Reload the Hammerspoon config after changing it (menu-bar
  icon → **Reload Config**). Mirror the same value in
  `frontend/src/components/WidgetPreview.tsx` so the web preview matches.
- `BASE_WIDTH` / `BASE_HEIGHT` — native content size (px) before `SCALE`.
  The window's content area is `BASE_WIDTH × SCALE` by `BASE_HEIGHT ×
  SCALE`; macOS adds its ~28px title bar on top of that.
  - **Empty band at the bottom / too much side padding?** That's surplus
    `BASE_HEIGHT` / `BASE_WIDTH` — lower the offending value (try -40 to
    -80 at a time) and reload the config.
  - **Content clipped?** Raise it.
  - Floor for `BASE_HEIGHT` is whatever fits the daily chart's two-line
    x-axis labels (the `2 Sep` / `174` / `208` row) — going below that
    cuts them off. ~520 fits the current layout.
  - Tune it in the dashboard's **Widget preview** first: the panel has
    live **base-width** / **base-height** number inputs over real data,
    so you can see the exact fit, then copy the numbers into
    `token-tracker.lua` and reload. Keep the two in sync — the preview's
    `DEFAULTS` in `frontend/src/components/WidgetPreview.tsx` should match
    the Lua values.
- `REFRESH_MINUTES` — how often to pull genuinely fresh data (ingest +
  `claude -p "/usage"` via `POST /api/refresh`), default 3. Driven by an
  `hs.timer` in the Lua, **not** the page — WKWebView suspends the page's
  own JS timer whenever the window is in the background, which is why an
  unattended panel used to sit frozen until you opened the web app. Only
  fires while the panel is visible, so a hidden widget costs nothing;
  hiding it (`⌘⌥⌃T`) stops the loop, showing it refreshes once and
  restarts it.
- `POLL_SECONDS` — how often the *page* re-reads the DB while it's on
  screen (default 60) — cheap, catches `launchd`/CLI ingest updates
  between the full refreshes above.
- `BACKEND` — backend address/port
- `MARGIN` — gap from the screen edge on snap
- `HOTKEY_MODS` — the modifier combo for all four hotkeys

`POLL_SECONDS` and `SCALE` are passed to the page as `?poll=` / `?scale=`
— the dashboard's **Widget preview** drives the same params so you can
dial in the size against live data before copying `SCALE` into
`token-tracker.lua`.

Visual styling (colors, fonts, spacing) is in the `<style>` block of
`backend/app/widget.html`.

## Notes / limitations

- **Not a true widget** — it's a small always-on-top browser window. It
  won't appear in Notification Center or the widget gallery.
- Utility-panel styling was deliberately avoided: those panels vanish
  whenever Hammerspoon isn't the frontmost app.
- The window is draggable and closable but not resizable by hand —
  resize via `SCALE` (or `BASE_WIDTH`/`BASE_HEIGHT`) and reload the config.
- One backend, one port. If `8765` is taken, change it in both
  `token-tracker.lua` and however you launch `uvicorn`.

## Uninstall

Remove the `dofile(...)` line from `~/.hammerspoon/init.lua` and reload
the config (or quit Hammerspoon). Nothing else is left running.
