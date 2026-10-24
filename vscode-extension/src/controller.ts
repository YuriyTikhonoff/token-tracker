import * as vscode from "vscode";

import type { UsageData } from "./api";
import { fetchUsage, requestRefresh } from "./client";
import { stamp } from "./diagnostics";
import { isStale, retryDelaySeconds } from "./retry";
import { readSettings } from "./settings";

export type State =
  | { kind: "loading" }
  // `staleReason` is set when the latest reads failed and `data` is an older reading.
  | { kind: "ready"; data: UsageData; at: Date; staleReason?: string }
  | { kind: "offline"; reason: string };

// A failed read keeps showing the last good one; after a couple in a row it is
// marked stale instead of being replaced, and reads are retried within seconds.
// The status bar turns to "offline" only when there has never been a reading.
// The backend restarts when its code changes, or can be busy with an ingest;
// neither is worth losing the numbers over.

// Owns the latest reading of the backend and when to take the next one. Views
// subscribe to `onDidChange` and render from `state`; they never fetch.
export class Controller implements vscode.Disposable {
  state: State = { kind: "loading" };
  // For the status report: the last successful read and how the reads have been failing.
  lastOkAt: Date | null = null;
  failures = 0;
  lastError: string | null = null;

  private readonly emitter = new vscode.EventEmitter<State>();
  readonly onDidChange = this.emitter.event;
  private timer: NodeJS.Timeout | undefined;
  private retryTimer: NodeJS.Timeout | undefined;
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
      this.failures = 0;
      clearTimeout(this.retryTimer);
      this.lastError = null;
      this.lastOkAt = new Date();
      this.set({ kind: "ready", data, at: this.lastOkAt });
      this.log.appendLine(
        `${stamp()} read ${data.usage_snapshots.length} limit(s) and ${data.today.total_tokens} tokens today ` +
          `from ${settings.url} (account: ${settings.account})`,
      );
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      this.failures += 1;
      this.lastError = reason;
      if (this.state.kind === "ready") {
        this.log.appendLine(`${stamp()} read failed (${this.failures} in a row), keeping the last reading: ${reason}`);
        if (isStale(this.failures)) this.set({ ...this.state, staleReason: reason });
      } else {
        this.set({ kind: "offline", reason });
        this.log.appendLine(`${stamp()} offline: ${settings.url}: ${reason}`);
      }
      this.retrySoon();
    } finally {
      this.polling = false;
    }
  }

  async refreshNow(): Promise<void> {
    const settings = readSettings();
    await requestRefresh(settings.url);
    await this.poll();
  }

  // Retries run whatever the window focus: they stop at the first success or after a few tries.
  private retrySoon(): void {
    clearTimeout(this.retryTimer);
    const seconds = retryDelaySeconds(this.failures);
    if (seconds !== null) this.retryTimer = setTimeout(() => void this.poll(), seconds * 1000);
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
    clearTimeout(this.retryTimer);
    this.subscriptions.forEach((subscription) => subscription.dispose());
    this.emitter.dispose();
  }
}
