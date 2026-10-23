import * as vscode from "vscode";

export interface Settings {
  url: string;
  refreshSeconds: number;
  account: string;
  showToday: boolean;
  autoStart: boolean;
  cliPath: string;
}

export function readSettings(): Settings {
  const config = vscode.workspace.getConfiguration("tokenTracker");
  return {
    url: config.get("url", "http://127.0.0.1:8765"),
    refreshSeconds: Math.max(10, config.get("refreshSeconds", 60)),
    account: config.get("account", "all"),
    showToday: config.get("statusBar.showToday", true),
    autoStart: config.get("autoStart", false),
    cliPath: config.get("cliPath", "token-tracker"),
  };
}
