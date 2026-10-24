// What the extension tells about itself, so a status bar that is not there can be
// traced without guessing. No `vscode` import: it is tested on its own.

export interface ItemReport {
  name: string;
  // What the extension asked VS Code to do. VS Code has no way to say whether the
  // item then fits on screen or was hidden from the status bar's own menu.
  shown: boolean;
  text: string;
  why: string;
}

export interface ReportInput {
  now: Date;
  backend: "loading" | "ready" | "stale" | "offline";
  url: string;
  account: string;
  lastOkAt: Date | null;
  failures: number;
  lastError: string | null;
  items: ItemReport[];
}

/** Clock time for a log line; the output channel adds none. */
export const stamp = () => new Date().toISOString().slice(11, 19);

export function ago(from: Date, now: Date): string {
  const seconds = Math.max(0, Math.round((now.getTime() - from.getTime()) / 1000));
  if (seconds < 90) return `${seconds} s ago`;
  const minutes = Math.round(seconds / 60);
  return minutes < 90 ? `${minutes} min ago` : `${Math.round(minutes / 60)} h ago`;
}

export function formatReport(input: ReportInput): string[] {
  const { now } = input;
  const lines = [
    `Backend: ${input.backend} (${input.url}, account: ${input.account})`,
    input.lastOkAt ? `Last good reading: ${ago(input.lastOkAt, now)}` : "Last good reading: none yet",
  ];
  if (input.failures > 0) lines.push(`Failed reads in a row: ${input.failures}${input.lastError ? `, last: ${input.lastError}` : ""}`);
  for (const item of input.items) {
    lines.push(`${item.shown ? "Shown" : "Hidden"}: ${item.name}${item.shown ? ` "${item.text}"` : ` (${item.why})`}`);
  }
  if (input.items.every((item) => !item.shown)) {
    lines.push("The extension has nothing on the status bar right now.");
  } else {
    lines.push("If these are not on the status bar, VS Code is hiding them: right-click the status bar and tick the Token Tracker entries, or widen the window.");
  }
  return lines;
}
