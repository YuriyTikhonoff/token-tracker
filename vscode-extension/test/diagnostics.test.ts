import assert from "node:assert/strict";
import { test } from "node:test";

import { ago, formatReport, type ReportInput } from "../src/diagnostics";

const now = new Date("2026-10-24T12:00:00Z");
const base: ReportInput = {
  now,
  backend: "ready",
  url: "http://127.0.0.1:8765",
  account: "all",
  lastOkAt: new Date("2026-10-24T11:59:30Z"),
  failures: 0,
  lastError: null,
  items: [
    { name: "Token Tracker: 5-hour limit", shown: true, text: "5h ▲ +47m", why: "" },
    { name: "Token Tracker: weekly limit", shown: false, text: "", why: "no weekly reading in the data" },
  ],
};

test("ago words short and long gaps", () => {
  assert.equal(ago(new Date("2026-10-24T11:59:30Z"), now), "30 s ago");
  assert.equal(ago(new Date("2026-10-24T11:50:00Z"), now), "10 min ago");
  assert.equal(ago(new Date("2026-10-24T08:00:00Z"), now), "4 h ago");
});

test("the report names shown and hidden items with the reason", () => {
  const lines = formatReport(base);
  assert.ok(lines.includes('Shown: Token Tracker: 5-hour limit "5h ▲ +47m"'));
  assert.ok(lines.includes("Hidden: Token Tracker: weekly limit (no weekly reading in the data)"));
  assert.ok(lines.some((line) => line.startsWith("If these are not on the status bar")));
});

test("failed reads are reported with the last error", () => {
  const lines = formatReport({ ...base, backend: "offline", failures: 3, lastError: "fetch failed" });
  assert.ok(lines.includes("Failed reads in a row: 3, last: fetch failed"));
});

test("an empty status bar is said plainly", () => {
  const lines = formatReport({ ...base, items: base.items.map((item) => ({ ...item, shown: false })) });
  assert.ok(lines.includes("The extension has nothing on the status bar right now."));
});
