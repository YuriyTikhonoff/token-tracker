# VS Code extension: implementation plan

A VS Code extension that shows Token Tracker's numbers inside the editor: whether you are using
your Claude subscription limits faster or slower than an even pace, how much time that leaves you
before each limit resets, and today's tokens and cost. The design was settled on an interactive
mockup; this document turns it into work.

## What it shows

### Status bar (always visible)

```
◷ 106.6M · $36.77   5h ▲ +47m   wk ▼ −2.7d
```

Three items, right-aligned, in this order:

| Item | Text | Colour |
| --- | --- | --- |
| Today | `◷ <tokens today> · <cost today>` | default, never coloured |
| 5-hour limit | `5h <arrow> <margin>` | from the margin, see below |
| Weekly limit | `wk <arrow> <margin>` | from the margin, see below |

- **Margin**: when the limit would run out at the current rate, minus when it resets. `+47m`
  means it lasts 47 minutes past the reset; `−2.7d` means it runs out 2.7 days before the reset.
  It is the same number the dashboard's limit row shows in large type, in a shorter format: one
  unit only (`45m`, `3.5h`, `12h`, `2.7d`).
- **Arrow**: where you are now against an even plan (the share of the window that has passed).
  `▲` means you are under the plan, so your reserve is growing; `▼` means you are over it, so the
  reserve is shrinking; `=` within half a percentage point. The arrow and the margin's sign
  usually agree, but they can differ: `▼ +5h` means you are over the plan but have slowed down
  enough that the limit still lasts.
- **Colour**, from the margin:
  - margin ≥ 0: green text (`charts.green`);
  - runs out before the reset by at most 15% of the window (about 25 h for the week, 45 min for
    the 5-hour window): warning background (`statusBarItem.warningBackground`);
  - runs out earlier than that: error background (`statusBarItem.errorBackground`).
  VS Code colours a whole item, which is why each limit is its own item.
- **Limit reached**: `wk limit hit` on the error background. **No window open** (5-hour only):
  `5h —`. **No snapshot yet / backend offline**: one item `◷ Token Tracker offline` that runs the
  start command on click.
- The difference in percentage points is not in the status bar; it is in the tooltip.

### Tooltip (hover on any of the three items)

A `MarkdownString` with:

| | Used | Plan | Diff | Margin |
| --- | --- | --- | --- | --- |
| 5-hour | 62% | 54% | +8 pp | −37m |
| Weekly | 47% | 52% | −5 pp | +2.0h |

then one line per limit with the reset time and, if it runs out first, the exhaust time; today's
and this week's tokens and cost; links: Open dashboard, Refresh, Switch account.

### Sidebar view (Activity Bar → Token Tracker)

A webview view, top to bottom:

1. Account selector (only when the backend reports more than one account).
2. One row per limit: name, margin in large type, used %, and a bar in the dashboard's style:
   blue up to the lower of usage and plan, then grey for unused plan or amber/red for usage over
   it. Under the bar: plan %, reset time, exhaust time when it comes first.
3. Today and this week: tokens and cost.
4. This workspace: cost and tokens of the project open in the editor this week, and its share.

### Dashboard

The command "Token Tracker: Open Dashboard" opens the existing web dashboard. The fact-vs-plan
chart already lives there (`LimitPaceChart`), so the extension does not reimplement it.

## Architecture

The extension is a thin client of the running backend. It reads `GET /api/limits` and calls
`POST /api/refresh`; it never reads `~/.claude` or the SQLite database itself. Pricing, ingest,
projections and account handling stay in one place, the backend.

`/api/limits` exists for this: `/api/data` takes 5 to 11 seconds to build on a grown database (it sums
the whole usage table several ways and builds the prompt log), which is too heavy for a client that
polls every minute. `/api/limits` returns only the limit snapshots, today's and this week's totals and
the account list, and answers in under half a second.

```
VS Code extension ──HTTP──► token-tracker serve (127.0.0.1:8765) ──► SQLite
       │                              ▲
       └── starts it if not running ──┘   (optional, setting)
```

Fields used from `/api/limits`:

| Need | Field |
| --- | --- |
| Limits | `usage_snapshots[]`: `scope`, `pct_used`, `resets_at`, `rate_per_hour`, `hours_to_limit` |
| Today / this week | `today`, `week` (`total_tokens`, `cost`; the week starts on Monday, as in the dashboard) |
| Accounts | `accounts[]` (`account_uuid`, `label`, `is_default`), query parameter `?account=<id>` (`all` or none = combined) |
| Time zone | `timezone` |

The sidebar view (phase 5) additionally needs `by_project`, which only `/api/data` has; it should
get its own light endpoint rather than polling `/api/data`.

Scopes are matched by name the same way the dashboard does: `week` in the name is weekly (7 days),
anything else is the 5-hour session. Model-specific weekly scopes (for example "Current week
(Fable)") are hidden, as in `LimitsWidget`.

## Layout in the repository

```
token-tracker/vscode-extension/
  package.json          # extension manifest + scripts
  tsconfig.json
  src/
    extension.ts        # activate/deactivate, wiring
    client.ts           # fetch /api/limits and /api/refresh, timeouts, offline state
    backend.ts          # start `token-tracker serve` as a child process when allowed
    pace.ts             # pure: plan %, diff, margin, severity, arrow, formatting
    statusBar.ts        # the three items and the tooltip
    sidebar/            # WebviewViewProvider + its HTML/CSS/JS
    workspaceProject.ts # workspace folder → Claude Code project name
  test/
    pace.test.ts
  README.md
```

It sits inside `token-tracker/`, so it is part of the public subtree: no personal paths or data.
It needs no port.

## Phases

Each phase ends in something usable and is its own commit (or a few).

### Phase 0: prerequisites

- Commit the pending dashboard change (`history` on limit snapshots and `LimitPaceChart`) on its
  own: `feat(token-tracker): fact-vs-plan chart for subscription limits`.
- Decide the open questions below that affect `pace.ts` (colour thresholds).

### Phase 1: skeleton and data client

- Scaffold `vscode-extension/` (TypeScript, `@types/vscode`, `@vscode/vsce`; bundle with esbuild
  into `dist/extension.js`). `engines.vscode` at a version that supports `ThemeColor` on
  status bar backgrounds (1.53+), so anything recent.
- Add it to the root `package.json` `workspaces`, give it `build`, `typecheck` and `lint`
  scripts so `npx nx run-many -t typecheck` and `-t lint` cover it.
- `client.ts`: `fetchUsage(account)` against `/api/limits` with a timeout, and `requestRefresh()`. Settings:
  `tokenTracker.url` (default `http://127.0.0.1:8765`), `tokenTracker.refreshSeconds` (default
  60), `tokenTracker.account` (default `all`).
- Poll on an interval; also fetch when the window regains focus. Skip polling while the window
  is unfocused.
- `.vscode/launch.json` with an "Extension Development Host" config for manual runs.

Done when: in the development host, the Output channel "Token Tracker" logs one line per poll
with the parsed limits, and stopping the backend logs "offline" without errors.

### Phase 2: pace logic (`pace.ts`) with tests

Pure functions, no `vscode` import:

- `planPercent(snapshot, now)`: elapsed share of the window, as `pacePercent` in the dashboard.
- `diffPp = pct_used − plan`.
- `marginHours`: exhaust time (`now + hours_to_limit`) minus `resets_at`; null when there is no
  projection.
- `severity(marginHours, windowHours)`: `ok` / `warn` / `danger` per the colour rule.
- `arrow(diffPp)` and `formatMarginShort(hours)`.

Unit tests with `node --test` on the compiled output, covering: under plan, over plan but lasting,
over plan and running out, limit reached, no window, no `hours_to_limit`, a reset already in the
past.

Done when: tests pass in CI-equivalent `npm test` and the cases above give the texts in the
"What it shows" section.

### Phase 3: status bar and tooltip

- `statusBar.ts`: create three `StatusBarItem`s (right side, adjacent priorities), update them
  from the latest data, set `backgroundColor`/`color` per severity, `tooltip` as `MarkdownString`
  with `isTrusted` for the command links.
- Commands: `tokenTracker.openDashboard` (opens `tokenTracker.url` with `env.openExternal`),
  `tokenTracker.refresh` (calls `/api/refresh`, then polls), `tokenTracker.switchAccount`
  (quick pick from `accounts`).
- Setting `tokenTracker.statusBar.showToday` (default on) for the first item.

Done when: checked by hand in light and dark themes and in a narrow window; each state from the
table above appears with fake data served from a fixture (see Testing).

### Phase 4: starting the backend

- Setting `tokenTracker.autoStart` (default off) and `tokenTracker.cliPath` (path to the
  `token-tracker` executable in the user's venv).
- When the backend is offline and auto-start is on, run `<cliPath> serve` as a child process,
  log its output to the Output channel, and stop it on `deactivate` only if the extension started
  it. Never start a second one if the port answers.
- Offline item offers "Start Token Tracker" and "Open settings".

Done when: with the backend stopped, enabling auto-start brings the status bar up within one
poll, and closing VS Code leaves no orphan process.

### Phase 5: sidebar view

- `viewsContainers.activitybar` + `views` with a webview view.
- HTML/CSS in the webview using `--vscode-*` theme variables only (this view must work in light
  and dark, unlike the dark-only web dashboard). Semantic colours from
  `--vscode-charts-green/-yellow/-red`, bar base from `--vscode-charts-blue`, reserve grey from
  `--vscode-input-background` or similar.
- The extension posts data to the webview with `postMessage`; the webview has a strict CSP and no
  network access of its own.
- `workspaceProject.ts`: map each workspace folder's absolute path to Claude Code's project folder
  name (its encoding replaces path separators and other non-alphanumerics with `-`; confirm
  against real `by_project` names before relying on it) and show that project's numbers.

Done when: the view renders every state from Phase 3, at the sidebar's narrowest width, in light
and dark.

### Phase 6: packaging and docs

- `npm run package` → `token-tracker-<version>.vsix` via `vsce package`; install with
  "Extensions: Install from VSIX". No Marketplace publishing for now.
- `vscode-extension/README.md`: what it shows, settings, how to install from VSIX, that the
  backend must be running (or auto-start set).
- Main `README.md`: a short section linking to it. `CHANGELOG.md` entry. A screenshot from
  made-up data.

## Testing

- `pace.ts`: unit tests (Phase 2).
- Status bar and sidebar: a fixture server (a tiny Node script in `test/`) that serves canned
  `/api/limits` payloads for each state, so the UI can be checked without a real database. Never
  point tests at a real `token_tracker.db` or `~/.claude`.
- Manual pass before each release: light and dark theme, narrow window, backend stopped and
  restarted, account switch.

## Open questions

1. **One colour rule for both places.** The dashboard currently colours a negative margin red
   always (large number) and amber/red at a 24 h threshold (exhaust line), while the bar's first
   segment is coloured by absolute level (70% / 90%). The extension uses the 15%-of-window rule
   and a plain blue first segment. Either align the dashboard to the extension's rule or pick
   another rule for both; until then the two can disagree on the same snapshot.
2. **Plan shape.** The plan is even over the window. A plan based on your usual week (nights and
   weekends weigh less) would stop Thursday afternoons from always reading as "over plan". It
   needs a backend endpoint with an hour-of-week usage profile from the last few weeks; leave it
   for after Phase 6.
3. **Codex limits.** Not in the status bar for now. They could be a fourth item with the same
   rules, behind a setting.
4. **Thin margin on the positive side.** Whether a small positive margin (for example under 5% of
   the window) should already be amber, so that green means a comfortable reserve.
