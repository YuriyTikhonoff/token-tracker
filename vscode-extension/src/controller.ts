import * as vscode from "vscode";

import type { UsageData } from "./api";
import { fetchUsage, requestRefresh } from "./client";
import { readSettings } from "./settings";

export type State =
  | { kind: "loading" }
  | { kind: "ready"; data: UsageData; at: Date }
  | { kind: "offline"; reason: string };

// Owns the latest reading of the backend and when to take the next one. Views
// subscribe to `onDidChange` and render from `state`; they never fetch.
export class Controller implements vscode.Disposable {
  state: State = { kind: "loading" };

  private readonly emitter = new vscode.EventEmitter<State>();
  readonly onDidChange = this.emitter.event;
  private timer: NodeJS.Timeout | undefined;
  private polling = false;
  private readonly subscriptions: vscode.Disposable[] = [];

  constructor(private readonly log: vscode.OutputChannel) {
    this.subscriptions.push(
      // The status bar is only worth keeping fresh while someone is looking at it.
      vscode.window.onDidChangeWindowState((window) => {
        if (window.focused) void this.poll();
      }),
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("tokenTracker")) {
          this.schedule();
          void this.poll();
        }
      }),
    );
    this.schedule();
    void this.poll();
  }

  async poll(): Promise<void> {
    if (this.polling) return;
    this.polling = true;
    const settings = readSettings();
    try {
      const data = await fetchUsage(settings.url, settings.account);
      this.set({ kind: "ready", data, at: new Date() });
      this.log.appendLine(
        `read ${data.usage_snapshots.length} limit(s) and ${data.totals_by_period.today.total_tokens} tokens today ` +
          `from ${settings.url} (account: ${settings.account})`,
      );
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      this.set({ kind: "offline", reason });
      this.log.appendLine(`offline: ${settings.url}: ${reason}`);
    } finally {
      this.polling = false;
    }
  }

  async refreshNow(): Promise<void> {
    const settings = readSettings();
    await requestRefresh(settings.url);
    await this.poll();
  }

  private set(state: State): void {
    this.state = state;
    this.emitter.fire(state);
  }

  private schedule(): void {
    if (this.timer) clearInterval(this.timer);
    const { refreshSeconds } = readSettings();
    this.timer = setInterval(() => {
      if (vscode.window.state.focused) void this.poll();
    }, refreshSeconds * 1000);
  }

  dispose(): void {
    if (this.timer) clearInterval(this.timer);
    this.subscriptions.forEach((subscription) => subscription.dispose());
    this.emitter.dispose();
  }
}
