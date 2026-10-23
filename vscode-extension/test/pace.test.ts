import assert from "node:assert/strict";
import { test } from "node:test";

import type { LimitSnapshot } from "../src/api";
import { arrow, computePace, formatMarginShort, limitKind, severityForMargin, statusText } from "../src/pace";

const NOW = new Date("2026-10-23T12:00:00Z");
const HOUR = 3_600_000;
const at = (hoursFromNow: number) => new Date(NOW.getTime() + hoursFromNow * HOUR).toISOString();

function weekly(over: Partial<LimitSnapshot> = {}): LimitSnapshot {
  // 3.5 days into the week: plan is 50%.
  return { scope: "Current week (all models)", pct_used: 50, resets_at: at(84), rate_per_hour: 0.3, hours_to_limit: null, ...over };
}

function session(over: Partial<LimitSnapshot> = {}): LimitSnapshot {
  // 2h into the 5h window: plan is 40%.
  return { scope: "Current session", pct_used: 40, resets_at: at(3), rate_per_hour: 20, hours_to_limit: null, ...over };
}

test("the plan is the share of the window that has passed", () => {
  assert.equal(computePace(weekly(), NOW)?.planPct, 50);
  assert.ok(Math.abs((computePace(session(), NOW)?.planPct ?? 0) - 40) < 1e-9);
});

test("a limit that lasts past the reset is ok and shows a positive margin", () => {
  const pace = computePace(weekly({ pct_used: 40, hours_to_limit: 100 }), NOW);
  assert.equal(pace?.severity, "ok");
  assert.equal(statusText(pace), "▲ +16h");
});

test("running out a little before the reset is a warning", () => {
  // 84h to reset, runs out in 70h: 14h short, under 15% of 168h (25.2h).
  const pace = computePace(weekly({ pct_used: 60, hours_to_limit: 70 }), NOW);
  assert.equal(pace?.severity, "warn");
  assert.equal(statusText(pace), "▼ −14h");
});

test("running out much earlier is an error", () => {
  const pace = computePace(weekly({ pct_used: 80, hours_to_limit: 20 }), NOW);
  assert.equal(pace?.severity, "danger");
  assert.equal(statusText(pace), "▼ −2.7d");
});

test("the arrow can disagree with the margin: over the plan but slowing down", () => {
  const pace = computePace(weekly({ pct_used: 60, hours_to_limit: 200 }), NOW);
  assert.equal(pace?.severity, "ok");
  assert.equal(statusText(pace), "▼ +4.8d");
});

test("a used-up limit says so, on the error colour", () => {
  const pace = computePace(session({ pct_used: 100 }), NOW);
  assert.equal(pace?.severity, "danger");
  assert.equal(statusText(pace), "limit hit");
});

test("no projection from the backend gives no margin and no colour", () => {
  const pace = computePace(session({ pct_used: 30 }), NOW);
  assert.equal(pace?.marginHours, null);
  assert.equal(pace?.severity, null);
  assert.equal(statusText(pace), "▲ —");
});

test("a window whose reset has passed, or has no reset time, has no pace", () => {
  assert.equal(computePace(session({ resets_at: at(-1) }), NOW), null);
  assert.equal(computePace(session({ resets_at: null }), NOW), null);
  assert.equal(statusText(null), "—");
});

test("a reset more than a window away does not push the plan below zero", () => {
  assert.equal(computePace(session({ resets_at: at(9) }), NOW)?.planPct, 0);
});

test("severity thresholds sit at 15% of the window", () => {
  assert.equal(severityForMargin(0, 168), "ok");
  assert.equal(severityForMargin(-25.2, 168), "warn");
  assert.equal(severityForMargin(-25.3, 168), "danger");
  assert.equal(severityForMargin(-0.75, 5), "warn");
  assert.equal(severityForMargin(-0.76, 5), "danger");
});

test("arrow points the way the reserve moves", () => {
  assert.equal(arrow(8), "▼");
  assert.equal(arrow(-8), "▲");
  assert.equal(arrow(0.3), "=");
  assert.equal(arrow(-0.3), "=");
});

test("margins use one unit", () => {
  assert.equal(formatMarginShort(0.78), "+47m");
  assert.equal(formatMarginShort(-0.62), "−37m");
  assert.equal(formatMarginShort(3.5), "+3.5h");
  assert.equal(formatMarginShort(12.4), "+12h");
  assert.equal(formatMarginShort(-65.3), "−2.7d");
  assert.equal(formatMarginShort(400), "+1w+");
});

test("limits are told apart by the word week, as in the dashboard", () => {
  assert.equal(limitKind("Current week (all models)"), "week");
  assert.equal(limitKind("Current session"), "session");
});
