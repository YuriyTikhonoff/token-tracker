import { type ChildProcess, spawn } from "node:child_process";

import * as vscode from "vscode";

let child: ChildProcess | undefined;

// Only a backend on this machine can be started from here.
function localAddress(url: string): { host: string; port: string } | null {
  const parsed = new URL(url);
  if (!["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) return null;
  return { host: parsed.hostname === "localhost" ? "127.0.0.1" : parsed.hostname, port: parsed.port || "80" };
}

export function startBackend(cliPath: string, url: string, log: vscode.OutputChannel): boolean {
  if (child && child.exitCode === null) return true;
  const address = localAddress(url);
  if (!address) {
    log.appendLine(`not starting a backend: ${url} is not a local address`);
    return false;
  }
  log.appendLine(`starting: ${cliPath} serve --host ${address.host} --port ${address.port}`);
  const started = spawn(cliPath, ["serve", "--host", address.host, "--port", address.port], {
    stdio: ["ignore", "pipe", "pipe"],
  });
  started.stdout.on("data", (chunk: Buffer) => log.append(chunk.toString()));
  started.stderr.on("data", (chunk: Buffer) => log.append(chunk.toString()));
  started.on("error", (error) => {
    log.appendLine(`could not start ${cliPath}: ${error.message}`);
    child = undefined;
  });
  started.on("exit", (code) => {
    log.appendLine(`backend exited with code ${code}`);
    child = undefined;
  });
  child = started;
  return true;
}

// Stops only a backend this extension started itself.
export function stopStartedBackend(): void {
  if (child && child.exitCode === null) child.kill();
  child = undefined;
}
