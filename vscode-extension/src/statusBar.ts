import * as vscode from "vscode";

import type { LimitSnapshot, UsageData } from "./api";
import type { Controller, State } from "./controller";
import { stamp, type ItemReport } from "./diagnostics";
import { fmtClock, fmtCost, fmtTokens, fmtWeekdayClock } from "./format";
import { type LimitPace, type Severity, arrow, computePace, isShownScope, limitKind, statusText } from "./pace";
import { readSettings } from "./settings";

// Right-aligned items sit left to right in order of falling priority. Other
// extensions and VS Code itself use values around 100, so these are set well
// above that to keep the three items together instead of scattered between them.
const PRIORITY = { today: 10_002, session: 10_001, week: 10_000 };

const COMMANDS = ["tokenTracker.openDashboard", "tokenTracker.refresh", "tokenTracker.switchAccount"];

// VS Code colours a whole item, so each limit is its own item. Only the
// warning and error backgrounds exist for status bar items; "ok" is a green
// text colour.
function applySeverity(item: vscode.StatusBarItem, severity: Severity | null): void {
  item.backgroundColor =
    severity === "danger"
      ? new vscode.ThemeColor("statusBarItem.errorBackground")
      : severity === "warn"
        ? new vscode.ThemeColor("statusBarItem.warningBackground")
        : undefined;
  item.color = severity === "ok" ? new vscode.ThemeColor("charts.green") : undefined;
}

function shownSnapshots(data: UsageData): LimitSnapshot[] {
  return data.usage_snapshots.filter((snapshot) => isShownScope(snapshot.scope));
}

function pp(value: number): string {
  return `${value >= 0 ? "+" : "−"}${Math.abs(Math.round(value))} pp`;
}

function limitRows(paces: LimitPace[]): string {
  const rows = paces.map(
    (pace) =>
      `| ${pace.kind === "week" ? "Weekly" : "5-hour"} | ${Math.round(pace.usedPct)}% | ${Math.round(pace.planPct)}% | ${arrow(pace.diffPp)} ${pp(pace.diffPp)} | ${statusText(pace).replace(/^[▲▼=] /, "")} |`,
  );
  return ["| | Used | Plan | Diff | Margin |", "| --- | ---: | ---: | ---: | ---: |", ...rows].join("\n");
}

function resetLines(paces: LimitPace[], timeZone: string): string {
  return paces
    .map((pace) => {
      const name = pace.kind === "week" ? "Weekly" : "5-hour";
      const reset = pace.kind === "week" ? fmtWeekdayClock(pace.resetsAt, timeZone) : fmtClock(pace.resetsAt, timeZone);
      const exhaust =
        pace.exhaustAt && pace.marginHours !== null && pace.marginHours < 0
          ? `, runs out ${pace.kind === "week" ? fmtWeekdayClock(pace.exhaustAt, timeZone) : fmtClock(pace.exhaustAt, timeZone)}`
          : "";
      return `${name}: resets ${reset}${exhaust}`;
    })
    .join("  \n");
}

function tooltip(data: UsageData, paces: LimitPace[], stale?: string): vscode.MarkdownString {
  const { today, week } = data;
  const markdown = new vscode.MarkdownString(undefined, true);
  markdown.isTrusted = { enabledCommands: COMMANDS };
  const parts = [
    "**Claude limits against an even pace**",
    stale ?? "",
    paces.length > 0 ? limitRows(paces) : "_No open limit window._",
    paces.length > 0 ? resetLines(paces, data.timezone) : "",
    `Today ${fmtTokens(today.total_tokens)} · ${fmtCost(today.cost)}` +
      `  \nThis week ${fmtTokens(week.total_tokens)} · ${fmtCost(week.cost)}`,
    "[Open dashboard](command:tokenTracker.openDashboard) · [Refresh](command:tokenTracker.refresh)" +
      (data.accounts.length > 1 ? " · [Switch account](command:tokenTracker.switchAccount)" : ""),
  ];
  markdown.appendMarkdown(parts.filter(Boolean).join("\n\n"));
  return markdown;
}

// An explicit id and name make each item separate in VS Code: its own entry in
// the status bar's right-click menu, instead of all three sharing the extension's id.
function createItem(id: string, name: string, priority: number): vscode.StatusBarItem {
  const item = vscode.window.createStatusBarItem(id, vscode.StatusBarAlignment.Right, priority);
  item.name = name;
  return item;
}

export class StatusBar implements vscode.Disposable {
  private readonly today = createItem("tokenTracker.today", "Token Tracker: today", PRIORITY.today);
  private readonly session = createItem("tokenTracker.session", "Token Tracker: 5-hour limit", PRIORITY.session);
  private readonly week = createItem("tokenTracker.week", "Token Tracker: weekly limit", PRIORITY.week);
  private readonly subscriptions: vscode.Disposable[];
  private readonly reports = new Map<string, ItemReport>();

  constructor(controller: Controller, private readonly log: vscode.OutputChannel) {
    for (const item of [this.today, this.session, this.week]) item.command = "tokenTracker.openDashboard";
    this.subscriptions = [
      controller.onDidChange((state) => this.render(state)),
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("tokenTracker.statusBar")) this.render(controller.state);
      }),
    ];
    this.render(controller.state);
  }

  /** What each item was last told to do, for the status report and the log. */
  itemReports(): ItemReport[] {
    return [...this.reports.values()];
  }

  // Every change of an item is logged, so the log says when and why one went away.
  private note(item: vscode.StatusBarItem, shown: boolean, why: string): void {
    const name = item.name ?? "";
    const previous = this.reports.get(name);
    const text = shown ? item.text : "";
    this.reports.set(name, { name, shown, text, why });
    if (!previous || previous.shown !== shown) this.log.appendLine(`${stamp()} ${name}: ${shown ? `shown "${text}"` : `hidden, ${why}`}`);
  }

  private render(state: State): void {
    if (state.kind === "loading") {
      for (const item of [this.today, this.session, this.week]) {
        item.hide();
        this.note(item, false, "first reading not back yet");
      }
      return;
    }
    if (state.kind === "offline") {
      this.session.hide();
      this.note(this.session, false, "backend offline");
      this.week.hide();
      this.note(this.week, false, "backend offline");
      this.today.text = "$(circle-slash) Token Tracker offline";
      const hover = new vscode.MarkdownString(
        `Could not read the Token Tracker backend: ${state.reason}\n\n[Start backend](command:tokenTracker.startBackend)`,
      );
      hover.isTrusted = { enabledCommands: ["tokenTracker.startBackend"] };
      this.today.tooltip = hover;
      this.today.command = "tokenTracker.startBackend";
      applySeverity(this.today, null);
      this.today.show();
      this.note(this.today, true, "offline notice");
      return;
    }

    const { data } = state;
    const snapshots = shownSnapshots(data);
    const sessionSnapshot = snapshots.find((snapshot) => limitKind(snapshot.scope) === "session");
    const weekSnapshot = snapshots.find((snapshot) => limitKind(snapshot.scope) === "week");
    const sessionPace = sessionSnapshot ? computePace(sessionSnapshot) : null;
    const weekPace = weekSnapshot ? computePace(weekSnapshot) : null;
    const paces = [sessionPace, weekPace].filter((pace): pace is LimitPace => pace !== null);
    const staleNote = state.staleReason
      ? `**Stale:** the backend is not answering (${state.staleReason}). These numbers are from ${fmtClock(state.at, data.timezone)}.`
      : undefined;
    const hover = tooltip(data, paces, staleNote);
    const mark = state.staleReason ? " (stale)" : "";

    const settings = readSettings();
    if (settings.showToday) {
      this.today.text = `$(history) ${fmtTokens(data.today.total_tokens)} · ${fmtCost(data.today.cost)}${mark}`;
      this.today.command = "tokenTracker.openDashboard";
      this.today.tooltip = hover;
      applySeverity(this.today, null);
      this.today.show();
      this.note(this.today, true, "");
    } else {
      this.today.hide();
      this.note(this.today, false, "turned off in settings");
    }

    this.show(this.session, "5h", sessionSnapshot, sessionPace, hover, mark);
    this.show(this.week, "wk", weekSnapshot, weekPace, hover, mark);
  }

  private show(
    item: vscode.StatusBarItem,
    name: string,
    snapshot: LimitSnapshot | undefined,
    pace: LimitPace | null,
    hover: vscode.MarkdownString,
    mark: string,
  ): void {
    // No snapshot at all: the scope has never been recorded, so show nothing
    // rather than a dash. A snapshot whose window has closed shows a dash.
    if (!snapshot) {
      item.hide();
      this.note(item, false, `no ${name === "5h" ? "5-hour" : "weekly"} reading in the data`);
      return;
    }
    item.text = `${name} ${statusText(pace)}${mark}`;
    item.tooltip = hover;
    applySeverity(item, pace?.severity ?? null);
    item.show();
    this.note(item, true, "");
  }

  dispose(): void {
    this.subscriptions.forEach((subscription) => subscription.dispose());
    for (const item of [this.today, this.session, this.week]) item.dispose();
  }
}
