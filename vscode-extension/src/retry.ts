// How the extension behaves when the backend stops answering. Pure, so it can be
// tested without VS Code.

// Seconds to wait before each retry after a failed read; once the list runs out
// the regular polling interval takes over again.
const RETRY_SECONDS = [5, 10, 20, 30];

// Failed reads in a row before the status bar marks the last reading as stale.
// One miss is a busy backend or a restart in progress and is not worth a mark.
export const STALE_AFTER_FAILURES = 2;

/** Seconds until the next retry after `failures` failed reads in a row, or null to wait for the regular poll. */
export function retryDelaySeconds(failures: number): number | null {
  return RETRY_SECONDS[failures - 1] ?? null;
}

export function isStale(failures: number): boolean {
  return failures >= STALE_AFTER_FAILURES;
}
