# Token Tracker for VS Code

Shows your Claude Code subscription limits against an even pace, and today's tokens and cost, in
the status bar. It reads a [Token Tracker](https://github.com/YuriyTikhonoff/token-tracker#readme) backend running on your machine; it does
not read your Claude logs itself.

```
$(history) 106.6M · $36.77   5h ▲ +47m   wk ▼ −2.7d
```

- **`106.6M · $36.77`**: tokens and estimated cost today.
- **`5h` / `wk`**: the 5-hour and the weekly limit. The number is the *margin*: how long the limit
  lasts past its reset at the current rate (`+`), or how much earlier it runs out (`−`). It is
  the large number on the dashboard's limit rows, in a shorter form.
- **`▲` / `▼`**: against an even plan (the share of the window that has passed). `▲` means you
  are under it and your reserve is growing, `▼` means you are over it and the reserve is shrinking.
- **Colour** follows the margin: green text when the limit lasts past the reset; warning
  background when it runs out a little early (by at most 15% of the window: about 25 hours for the
  week, 45 minutes for the 5-hour window); error background when it runs out earlier than that.
- Hover any item for a table of used, plan, difference in percentage points and margin, the reset
  times, and today's and this week's totals.

## Use

The backend has to be running (`token-tracker serve`, or `token-tracker run`). If it is not, the
status bar says so, and "Token Tracker: Start Backend" starts it.

When the backend stops answering, the status bar keeps the last numbers. After two failed reads in
a row they get a "(stale)" mark and the tooltip says since when, and the extension retries after 5,
10, 20 and 30 seconds before it goes back to the regular interval. "Token Tracker offline" shows only
when there has never been a reading in this window. "Token Tracker: Show Status" lists what is
shown and why, and the log ("Token Tracker: Show Log") has a timestamp on every line.

### Install it in your everyday VS Code

```bash
npm run install:vscode       # from this folder; or `npm run install:token-tracker-vscode` from the repository root
```

This builds `token-tracker.vsix` (compiled code only, about 15 KB) and installs it with
`code --install-extension --force`; reload VS Code afterwards. Run it again after a change. The
extension then starts with VS Code and shows the status bar whenever the backend answers on the
configured address. Starting the backend is not its job: it is already part of the repository's
`npm run dev:*` scripts. To have the extension start it when it is not running, turn on
`tokenTracker.autoStart` and set `tokenTracker.cliPath` to the `token-tracker` in your virtualenv.

To uninstall: `code --uninstall-extension token-tracker.token-tracker-vscode`.

### Run it from source (development host)

Run it from a development host. Everything below is run from this folder
(`token-tracker/vscode-extension`), once `npm install` has been run in the repository root, or here.

### Try it without a real backend

```bash
npm run dev:host              # opens VS Code with the extension, in the "on" scenario
npm run dev:host -- ahead     # or: on, reserve, limit, idle
```

This builds the extension, starts a fake backend with canned data on port 8799 and opens a new
VS Code window that runs the extension against it. The window uses a throwaway workspace whose
settings point at the fake backend, so your own settings and your real backend are not touched, and
your colour theme still applies. Closing that window stops the fake backend.

It needs the `code` command in PATH (VS Code: Command Palette, "Shell Command: Install 'code'
command in PATH"). To use another port: `PORT=8797 npm run dev:host`.

While the window is open, switch the state from another terminal; the status bar follows within
10 seconds:

```bash
curl http://127.0.0.1:8799/scenario/ahead     # over the plan, running out early (red, amber)
curl http://127.0.0.1:8799/scenario/on        # on the plan, the limit lasts (green)
curl http://127.0.0.1:8799/scenario/reserve   # well under the plan (green, large margin)
curl http://127.0.0.1:8799/scenario/limit     # the 5-hour limit is used up
curl http://127.0.0.1:8799/scenario/idle      # no open 5-hour window
```

Things worth checking there, in a light and a dark theme: the green text is readable on the
status bar, the amber and red backgrounds show, and the tooltip fits on hover. For the offline
state, run `npm run build` and `code --extensionDevelopmentPath="$PWD"` with no backend running.

## Commands

| Command | What it does |
| --- | --- |
| Token Tracker: Open Dashboard | opens the web dashboard in the browser |
| Token Tracker: Refresh Now | asks the backend to read new activity, then updates; this also asks Codex for a fresh rate-limit reading, which spends a few real Codex tokens |
| Token Tracker: Switch Account | choose which account's numbers to show |
| Token Tracker: Start Backend | runs `token-tracker serve` for a local address |
| Token Tracker: Show Log | the extension's output channel |

The status bar updates on a timer (every 60 seconds while the window is focused) by reading the
backend only; the timer never triggers a refresh.

## Settings

| Setting | Default | |
| --- | --- | --- |
| `tokenTracker.url` | `http://127.0.0.1:8765` | address of the backend |
| `tokenTracker.refreshSeconds` | `60` | how often to read it, at least 10 |
| `tokenTracker.account` | `all` | an account id, or every account combined |
| `tokenTracker.statusBar.showToday` | `true` | the tokens-and-cost item |
| `tokenTracker.autoStart` | `false` | start the backend when it does not answer (local only) |
| `tokenTracker.cliPath` | `token-tracker` | the executable, for example the one in your virtualenv |

## Development

```bash
npm run typecheck && npm run lint
npm test            # tests of the pace logic (src/pace.ts)
npm run fixture -- ahead   # just the fake backend, without opening VS Code
```

`src/pace.ts` holds the calculations and has no `vscode` import. See
[the plan](https://github.com/YuriyTikhonoff/token-tracker/blob/main/docs/vscode-extension-plan.md) for what is built and what is next.
