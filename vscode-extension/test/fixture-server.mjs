// A stand-in for the Token Tracker backend, to look at the extension's states
// without a real database: `npm run fixture -- ahead`, then point
// tokenTracker.url at it. Scenarios: ahead, on, reserve, limit, idle.
// GET /scenario/<name> switches the scenario while it runs.
import http from "node:http";

let scenario = process.argv[2] ?? "on";
const port = Number(process.env.PORT ?? 8765);
const HOUR = 3_600_000;

// Each limit: hours until the reset, % used, and the margin (hours the limit
// lasts past the reset; negative = runs out before it).
const SCENARIOS = {
  ahead: { session: [2, 68, -0.6], week: [84, 75, -65] },
  on: { session: [3, 38, 0.8], week: [84, 52, 2] },
  reserve: { session: [3, 20, 3.5], week: [84, 30, 58] },
  limit: { session: [2, 100, null], week: [84, 60, 10] },
  idle: { session: [-1, 12, null], week: [84, 52, 2] },
};

function snapshot(scope, [hoursToReset, pctUsed, margin]) {
  return {
    scope,
    pct_used: pctUsed,
    resets_at: new Date(Date.now() + hoursToReset * HOUR).toISOString(),
    rate_per_hour: margin === null ? 0 : 1,
    hours_to_limit: margin === null ? null : hoursToReset + margin,
  };
}

function payload() {
  const chosen = SCENARIOS[scenario];
  if (!chosen) throw new Error(`unknown scenario ${scenario}: ${Object.keys(SCENARIOS).join(", ")}`);
  return {
    usage_snapshots: [
      snapshot("Current session", chosen.session),
      snapshot("Current week (all models)", chosen.week),
      snapshot("Current week (Fable)", [84, 5, null]),
    ],
    today: { total_tokens: 106_600_000, cost: 36.77 },
    week: { total_tokens: 645_700_000, cost: 222.65 },
    accounts: [
      { account_uuid: "me", label: "personal", is_default: true },
      { account_uuid: "guest", label: "guest", is_default: false },
    ],
    timezone: "Europe/Kyiv",
  };
}

http
  .createServer((request, response) => {
    if (request.url?.startsWith("/api/limits")) {
      response.setHeader("content-type", "application/json");
      response.end(JSON.stringify(payload()));
    } else if (request.url?.startsWith("/scenario/")) {
      const name = request.url.slice("/scenario/".length);
      response.setHeader("content-type", "text/plain");
      if (name in SCENARIOS) {
        scenario = name;
        response.end(`scenario: ${scenario}\n`);
      } else {
        response.statusCode = 404;
        response.end(`unknown scenario ${name}: ${Object.keys(SCENARIOS).join(", ")}\n`);
      }
    } else if (request.url?.startsWith("/api/refresh")) {
      response.setHeader("content-type", "application/json");
      response.end("{}");
    } else {
      response.setHeader("content-type", "text/plain");
      response.end(`Token Tracker fixture (${scenario})\n`);
    }
  })
  .listen(port, "127.0.0.1", () => console.log(`fixture "${scenario}" on http://127.0.0.1:${port}`));
