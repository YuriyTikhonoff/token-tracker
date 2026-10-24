import * as vscode from "vscode";

import { startBackend, stopStartedBackend } from "./backend";
import { Controller } from "./controller";
import { formatReport, stamp } from "./diagnostics";
import { readSettings } from "./settings";
import { StatusBar } from "./statusBar";

export function activate(context: vscode.ExtensionContext): void {
  const log = vscode.window.createOutputChannel("Token Tracker");
  const controller = new Controller(log);
  const statusBar = new StatusBar(controller, log);
  const version = (context.extension.packageJSON as { version?: string }).version ?? "?";
  log.appendLine(`${stamp()} started, version ${version}, reading ${readSettings().url} every ${readSettings().refreshSeconds} s`);

  // With auto-start on, an offline backend is started once; the next poll
  // finds it. A backend this extension did not start is never touched.
  let triedAutoStart = false;
  const autoStart = controller.onDidChange((state) => {
    if (state.kind !== "offline" || triedAutoStart) return;
    const settings = readSettings();
    if (!settings.autoStart) return;
    triedAutoStart = true;
    if (startBackend(settings.cliPath, settings.url, log)) setTimeout(() => void controller.poll(), 3_000);
  });

  context.subscriptions.push(
    log,
    controller,
    statusBar,
    autoStart,
    { dispose: stopStartedBackend },
    vscode.commands.registerCommand("tokenTracker.openDashboard", () =>
      vscode.env.openExternal(vscode.Uri.parse(readSettings().url)),
    ),
    vscode.commands.registerCommand("tokenTracker.refresh", async () => {
      try {
        await controller.refreshNow();
      } catch (error) {
        const reason = error instanceof Error ? error.message : String(error);
        log.appendLine(`refresh failed: ${reason}`);
        void vscode.window.showWarningMessage(`Token Tracker refresh failed: ${reason}`);
      }
    }),
    vscode.commands.registerCommand("tokenTracker.startBackend", () => {
      const settings = readSettings();
      if (startBackend(settings.cliPath, settings.url, log)) setTimeout(() => void controller.poll(), 3_000);
      else void vscode.window.showWarningMessage(`${settings.url} is not a local address, so it cannot be started from here.`);
    }),
    vscode.commands.registerCommand("tokenTracker.switchAccount", async () => {
      const state = controller.state;
      if (state.kind !== "ready" || state.data.accounts.length === 0) {
        void vscode.window.showInformationMessage("Token Tracker has no accounts to switch between yet.");
        return;
      }
      const current = readSettings().account;
      const picked = await vscode.window.showQuickPick(
        [
          { label: "All accounts", description: current === "all" ? "current" : "", id: "all" },
          ...state.data.accounts.map((account) => ({
            label: account.label,
            description: current === account.account_uuid ? "current" : account.is_default ? "default" : "",
            id: account.account_uuid,
          })),
        ],
        { placeHolder: "Account to show in the status bar" },
      );
      if (picked) {
        await vscode.workspace.getConfiguration("tokenTracker").update("account", picked.id, vscode.ConfigurationTarget.Global);
      }
    }),
    vscode.commands.registerCommand("tokenTracker.showLog", () => log.show()),
    vscode.commands.registerCommand("tokenTracker.showStatus", async () => {
      const settings = readSettings();
      const lines = formatReport({
        now: new Date(),
        backend: controller.state.kind === "ready" && controller.state.staleReason ? "stale" : controller.state.kind,
        url: settings.url,
        account: settings.account,
        lastOkAt: controller.lastOkAt,
        failures: controller.failures,
        lastError: controller.lastError,
        items: statusBar.itemReports(),
      });
      log.appendLine(`${stamp()} status report:\n  ${lines.join("\n  ")}`);
      const picked = await vscode.window.showQuickPick(
        [...lines.map((label) => ({ label, id: "" })), { label: "$(output) Open the log", id: "log" }],
        { placeHolder: "Token Tracker status" },
      );
      if (picked?.id === "log") log.show();
    }),
  );
}

export function deactivate(): void {
  stopStartedBackend();
}
